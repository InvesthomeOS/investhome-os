"""Normalize and ingest live Email / WhatsApp / call / comment / task / meeting records.

Does not send messages. Does not connect external providers.
Duplicates are skipped. Matched records project into the existing person timeline.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.crm_activity import (
    CrmActivity,
    CrmActivityCategory,
    CrmActivityEntityType,
    CrmActivityStatus,
    CrmActivityType,
    CrmActivityVisibility,
)
from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_communication import (
    CrmCommunication,
    CrmCommunicationAttachment,
    CrmCommunicationChannel,
    CrmCommunicationDirection,
    CrmCommunicationMatchStatus,
    CrmCommunicationSource,
    CrmCommunicationStatus,
    CrmCommunicationThread,
    CrmUserCommunicationAccount,
)
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.document import (
    Document,
    DocumentLink,
    DocumentStatus,
    DocumentType,
    DocumentVisibility,
    DocumentWorkspaceFolder,
    ProcessingStatus,
)
from investhome_api.models.user_auth import User
from investhome_api.services.crm.identity import normalize_email, parse_phone
from investhome_api.services.crm.live_matching import MatchDecision, match_identities
from investhome_api.services.crm_communication_activity import record_communication_audit
from investhome_api.services.document_validation import compute_checksum, content_stream, generate_storage_key
from investhome_api.services.storage import get_storage_provider, provider_enum

logger = logging.getLogger(__name__)

CHANNEL_ALIASES = {
    "email": CrmCommunicationChannel.EMAIL.value,
    "whatsapp": CrmCommunicationChannel.WHATSAPP.value,
    "call": CrmCommunicationChannel.PHONE.value,
    "phone": CrmCommunicationChannel.PHONE.value,
    "comment": CrmCommunicationChannel.NOTE.value,
    "note": CrmCommunicationChannel.NOTE.value,
    "task": CrmCommunicationChannel.TASK.value,
    "meeting": CrmCommunicationChannel.MEETING.value,
    "sms": CrmCommunicationChannel.SMS.value,
}

DIRECTION_ALIASES = {
    "incoming": CrmCommunicationDirection.INBOUND.value,
    "inbound": CrmCommunicationDirection.INBOUND.value,
    "outgoing": CrmCommunicationDirection.OUTBOUND.value,
    "outbound": CrmCommunicationDirection.OUTBOUND.value,
    "internal": CrmCommunicationDirection.INTERNAL.value,
    "system": CrmCommunicationDirection.SYSTEM.value,
}

SOURCE_ALIASES = {
    "bitrix": CrmCommunicationSource.BITRIX.value,
    "live_email": CrmCommunicationSource.LIVE_EMAIL.value,
    "live_whatsapp": CrmCommunicationSource.LIVE_WHATSAPP.value,
    "manual": CrmCommunicationSource.MANUAL.value,
}

ACTIVITY_TYPE_MAP = {
    CrmCommunicationChannel.EMAIL.value: CrmActivityType.EMAIL,
    CrmCommunicationChannel.WHATSAPP.value: CrmActivityType.WHATSAPP,
    CrmCommunicationChannel.PHONE.value: CrmActivityType.PHONE_CALL,
    CrmCommunicationChannel.SMS.value: CrmActivityType.SMS,
    CrmCommunicationChannel.MEETING.value: CrmActivityType.MEETING,
    CrmCommunicationChannel.TASK.value: CrmActivityType.TASK,
    CrmCommunicationChannel.NOTE.value: CrmActivityType.COMMENT,
}


class DuplicateLiveMessage(Exception):
    def __init__(self, existing: CrmCommunication) -> None:
        super().__init__("duplicate")
        self.existing = existing


def _now() -> datetime:
    return datetime.now(UTC)


def _normalize_identity(channel: str, value: str | None) -> str | None:
    if channel in {CrmCommunicationChannel.EMAIL.value}:
        return normalize_email(value)
    parsed = parse_phone(value)
    if parsed and parsed.e164:
        return parsed.e164
    if parsed:
        return parsed.match_key
    text = (value or "").strip()
    return text or None


def infer_source(channel: str, source: str | None) -> str:
    if source:
        return SOURCE_ALIASES.get(source.strip().lower(), CrmCommunicationSource.MANUAL.value)
    if channel == CrmCommunicationChannel.EMAIL.value:
        return CrmCommunicationSource.LIVE_EMAIL.value
    if channel == CrmCommunicationChannel.WHATSAPP.value:
        return CrmCommunicationSource.LIVE_WHATSAPP.value
    return CrmCommunicationSource.MANUAL.value


def content_hash_for(
    *,
    channel: str,
    account_id: UUID | None,
    occurred_at: datetime,
    sender_identity: str | None,
    body: str | None,
) -> str:
    stamp = occurred_at.astimezone(UTC).replace(microsecond=0).isoformat()
    raw = "|".join(
        [
            channel,
            str(account_id or ""),
            stamp,
            sender_identity or "",
            (body or "").strip(),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _norm_subject(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def _rfc_message_id(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    if cleaned.startswith("<") and cleaned.endswith(">"):
        cleaned = cleaned[1:-1]
    return cleaned.casefold() or None


def find_rfc_duplicate(db: Session, rfc_message_id: str | None) -> CrmCommunication | None:
    rfc = _rfc_message_id(rfc_message_id)
    if not rfc:
        return None
    rows = list(
        db.scalars(
            select(CrmCommunication).where(
                CrmCommunication.channel == CrmCommunicationChannel.EMAIL.value,
                CrmCommunication.archived_at.is_(None),
            )
        ).all()
    )
    for row in rows:
        meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        if _rfc_message_id(str(meta.get("rfc_message_id") or "")) == rfc:
            return row
    return None


def find_bitrix_email_activity(
    db: Session,
    *,
    rfc_message_id: str | None,
    subject: str | None,
    occurred_at: datetime,
    sender_identity: str | None,
) -> CrmActivity | None:
    """Locate an existing Bitrix/historical EMAIL activity. Never mutates it."""
    rfc = _rfc_message_id(rfc_message_id)
    subject_key = _norm_subject(subject)
    window_start = occurred_at.astimezone(UTC) - timedelta(minutes=5)
    window_end = occurred_at.astimezone(UTC) + timedelta(minutes=5)
    rows = list(
        db.scalars(
            select(CrmActivity).where(
                CrmActivity.activity_type == CrmActivityType.EMAIL,
                CrmActivity.start_date.is_not(None),
                CrmActivity.start_date >= window_start,
                CrmActivity.start_date <= window_end,
            )
        ).all()
    )
    sender = (sender_identity or "").casefold()
    for activity in rows:
        meta = activity.metadata_json if isinstance(activity.metadata_json, dict) else {}
        if meta.get("live_communication"):
            continue
        history = meta.get("bitrix_history") if isinstance(meta.get("bitrix_history"), dict) else {}
        stored_rfc = _rfc_message_id(
            str(meta.get("rfc_message_id") or history.get("rfc_message_id") or history.get("message_id") or "")
        )
        if rfc and stored_rfc and rfc == stored_rfc:
            return activity
        activity_subject = _norm_subject(activity.title)
        if subject_key and subject_key and subject_key in activity_subject:
            blob = f"{activity.title or ''} {activity.description or ''} {activity.summary or ''}".casefold()
            if sender and sender in blob:
                return activity
            if activity_subject.endswith(subject_key):
                return activity
    return None


def find_duplicate(
    db: Session,
    *,
    source: str,
    external_provider_id: str | None,
    account_id: UUID | None,
    content_hash: str,
    occurred_at: datetime,
    sender_identity: str | None,
    rfc_message_id: str | None = None,
) -> CrmCommunication | None:
    if external_provider_id:
        existing = db.scalar(
            select(CrmCommunication).where(
                CrmCommunication.source == source,
                CrmCommunication.external_provider_id == external_provider_id,
                CrmCommunication.archived_at.is_(None),
            )
        )
        if existing:
            return existing
    rfc_hit = find_rfc_duplicate(db, rfc_message_id)
    if rfc_hit:
        return rfc_hit
    window_start = occurred_at.astimezone(UTC).replace(microsecond=0)
    return db.scalar(
        select(CrmCommunication).where(
            CrmCommunication.content_hash == content_hash,
            CrmCommunication.account_id == account_id,
            CrmCommunication.sender_identity == sender_identity,
            CrmCommunication.occurred_at == window_start,
            CrmCommunication.archived_at.is_(None),
        )
    )


def _ensure_thread(
    db: Session,
    *,
    channel: str,
    conversation_key: str | None,
    subject: str | None,
    owner_id: UUID | None,
) -> CrmCommunicationThread | None:
    if not conversation_key:
        return None
    prior = db.scalar(
        select(CrmCommunication).where(
            CrmCommunication.conversation_key == conversation_key,
            CrmCommunication.channel == channel,
            CrmCommunication.thread_id.is_not(None),
            CrmCommunication.archived_at.is_(None),
        )
    )
    if prior and prior.thread_id:
        thread = db.get(CrmCommunicationThread, prior.thread_id)
        if thread:
            return thread
    thread = CrmCommunicationThread(
        subject=subject or "",
        channel=channel,
        channels=[channel],
        owner_id=owner_id,
        tags=[f"conversation:{conversation_key}"],
    )
    db.add(thread)
    db.flush()
    return thread


def _preview(text: str | None) -> str | None:
    if not text:
        return None
    stripped = " ".join(text.split())
    return stripped[:220] + ("…" if len(stripped) > 220 else "")


def _activity_title(channel: str, subject: str | None, preview: str | None) -> str:
    if channel == CrmCommunicationChannel.EMAIL.value:
        return f"E-posta: {subject or preview or 'E-posta'}"
    if channel == CrmCommunicationChannel.WHATSAPP.value:
        return f"WhatsApp: {preview or subject or 'WhatsApp'}"
    if channel == CrmCommunicationChannel.PHONE.value:
        return f"Arama: {subject or preview or 'Arama'}"
    if channel == CrmCommunicationChannel.TASK.value:
        return f"Görev: {subject or preview or 'Görev'}"
    if channel == CrmCommunicationChannel.MEETING.value:
        return f"Toplantı: {subject or preview or 'Toplantı'}"
    if channel == CrmCommunicationChannel.NOTE.value:
        return f"Yorum: {preview or subject or 'Yorum'}"
    return subject or preview or channel


def project_to_person_timeline(
    db: Session,
    comm: CrmCommunication,
    *,
    actor: User | None,
) -> None:
    if not comm.contact_id or comm.activity_id:
        return
    meta = comm.metadata_json if isinstance(comm.metadata_json, dict) else {}
    if meta.get("skip_timeline"):
        return
    activity_type = ACTIVITY_TYPE_MAP.get(comm.channel, CrmActivityType.OTHER)
    direction = "incoming" if comm.direction == CrmCommunicationDirection.INBOUND.value else "outgoing"
    if comm.direction == CrmCommunicationDirection.SYSTEM.value:
        direction = "system"
    live_thread = {
        "kind": comm.channel,
        "chat_id": comm.conversation_key,
        "direction": direction,
        "source": comm.source,
        "message_id": comm.external_provider_id,
        "author_name": comm.sender_identity,
    }
    activity = CrmActivity(
        entity_type=CrmActivityEntityType.CONTACT,
        entity_id=comm.contact_id,
        activity_type=activity_type,
        activity_category=CrmActivityCategory.COMMUNICATION
        if activity_type
        in {CrmActivityType.EMAIL, CrmActivityType.WHATSAPP, CrmActivityType.PHONE_CALL, CrmActivityType.SMS}
        else CrmActivityCategory.OTHER,
        title=_activity_title(comm.channel, comm.subject, comm.preview),
        summary=(comm.preview or "")[:1000] or None,
        description=comm.body_html or comm.body_text or comm.body or comm.raw_source,
        status=CrmActivityStatus.COMPLETED,
        owner_id=comm.owner_id or (actor.id if actor else None),
        assigned_user_id=comm.assigned_user_id,
        visibility=CrmActivityVisibility.ORGANIZATION,
        start_date=comm.occurred_at or comm.sent_at or comm.created_at,
        metadata_json={
            "communication_id": str(comm.id),
            "source": comm.source,
            "live_communication": True,
            "channel": comm.channel,
            "direction": direction,
            "account_id": str(comm.account_id) if comm.account_id else None,
            "agreement_id": str(comm.agreement_id) if comm.agreement_id else None,
            "live_thread": live_thread,
        },
        created_by=actor.id if actor else comm.owner_id,
    )
    db.add(activity)
    db.flush()
    comm.activity_id = activity.id


def _store_attachment_bytes(
    db: Session,
    *,
    file_name: str,
    mime_type: str | None,
    content: bytes,
    actor_id: UUID | None,
    communication_id: UUID,
    contact_id: UUID | None,
    agreement_id: UUID | None,
) -> tuple[Document, str]:
    checksum = compute_checksum(content)
    existing = db.scalar(select(Document).where(Document.checksum == checksum, Document.is_latest_version.is_(True)))
    if existing:
        document = existing
    else:
        ext = ""
        if "." in file_name:
            ext = file_name.rsplit(".", 1)[-1].lower()[:20]
        stored_name, storage_key = generate_storage_key(ext or "bin")
        storage = get_storage_provider()
        storage.save(storage_key, content_stream(content), content_length=len(content))
        document = Document(
            title=file_name.rsplit(".", 1)[0][:500],
            original_file_name=file_name[:500],
            stored_file_name=stored_name,
            file_extension=ext or "bin",
            mime_type=mime_type or "application/octet-stream",
            file_size=len(content),
            storage_provider=provider_enum(),
            storage_key=storage_key,
            checksum=checksum,
            document_type=DocumentType.CORRESPONDENCE,
            category="communication",
            folder=DocumentWorkspaceFolder.GENERAL,
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.ORGANIZATION,
            processing_status=ProcessingStatus.UPLOADED,
            uploaded_by_user_id=actor_id,
            owner_user_id=actor_id,
            description="Live communication attachment — not an agreement document.",
        )
        db.add(document)
        db.flush()
    _link_document(db, document.id, "crm_communication", communication_id, "attachment")
    if contact_id:
        _link_document(db, document.id, "crm_contact", contact_id, "communication_attachment")
    if agreement_id:
        _link_document(db, document.id, "crm_agreement", agreement_id, "communication_attachment")
    return document, checksum


def _link_document(db: Session, document_id: UUID, entity_type: str, entity_id: UUID, relationship_type: str) -> None:
    existing = db.scalar(
        select(DocumentLink).where(
            DocumentLink.document_id == document_id,
            DocumentLink.entity_type == entity_type,
            DocumentLink.entity_id == entity_id,
        )
    )
    if existing:
        return
    db.add(
        DocumentLink(
            document_id=document_id,
            entity_type=entity_type,
            entity_id=entity_id,
            relationship_type=relationship_type,
        )
    )


def _identity_value(item: Any) -> str | None:
    if item is None:
        return None
    if isinstance(item, dict):
        value = item.get("email") or item.get("phone") or item.get("address") or item.get("identity")
        return str(value).strip() or None
    text = str(item).strip()
    return text or None


def _collect_match_inputs(
    channel: str,
    payload: dict[str, Any],
    *,
    direction: str,
    account_identity: str | None,
) -> tuple[list[str], list[str]]:
    sender = _identity_value(payload.get("sender_identity") or payload.get("sender"))
    recipients = payload.get("recipients") or payload.get("recipient_identities") or []
    cc = payload.get("cc") or payload.get("cc_recipients") or []
    others = [value for item in [*recipients, *cc] if (value := _identity_value(item))]
    if direction == CrmCommunicationDirection.INBOUND.value:
        candidates = [sender] if sender else []
    else:
        candidates = others
        if account_identity:
            owned = _normalize_identity(channel, account_identity)
            candidates = [item for item in candidates if _normalize_identity(channel, item) != owned]
        if not candidates and sender:
            candidates = [sender]
    emails: list[str] = []
    phones: list[str] = []
    bucket = emails if channel == CrmCommunicationChannel.EMAIL.value else phones
    for value in candidates:
        if value:
            bucket.append(value)
    return emails, phones


def ingest_live_message(
    db: Session,
    payload: dict[str, Any],
    *,
    actor: User | None = None,
) -> tuple[CrmCommunication, bool]:
    """Insert or return existing duplicate. Second value is True when newly created."""
    channel = CHANNEL_ALIASES.get(str(payload.get("channel") or "").strip().lower())
    if not channel:
        raise ValueError("unsupported_channel")
    direction = DIRECTION_ALIASES.get(str(payload.get("direction") or "incoming").strip().lower())
    if not direction:
        raise ValueError("unsupported_direction")
    source = infer_source(channel, payload.get("source"))
    account_id = payload.get("account_id")
    account: CrmUserCommunicationAccount | None = None
    if account_id:
        account = db.get(CrmUserCommunicationAccount, UUID(str(account_id)))
        if account is None or account.archived_at is not None:
            raise ValueError("unknown_account")
    occurred_at = payload.get("occurred_at")
    if isinstance(occurred_at, str):
        occurred_at = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
    if occurred_at is None:
        occurred_at = _now()
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=UTC)
    occurred_at = occurred_at.astimezone(UTC).replace(microsecond=0)

    sender_identity = _normalize_identity(channel, payload.get("sender_identity") or payload.get("sender"))
    raw_recipients = payload.get("recipients") or payload.get("recipient_identities") or []
    recipient_identities: list[str] = []
    for item in raw_recipients:
        value = item.get("email") or item.get("phone") or item.get("identity") if isinstance(item, dict) else item
        normalized = _normalize_identity(channel, str(value) if value else None)
        if normalized:
            recipient_identities.append(normalized)

    body_html = payload.get("body_html") or payload.get("html")
    body_text = payload.get("body_text") or payload.get("text") or payload.get("body")
    raw_source = payload.get("raw_source") or body_html or body_text
    subject = (payload.get("subject") or "")[:500] or None
    preview = _preview(body_text or subject)
    external_id = str(payload.get("external_provider_id") or payload.get("external_id") or "").strip() or None
    conversation_key = str(payload.get("conversation_id") or payload.get("thread_id") or payload.get("conversation_key") or "").strip() or None
    digest = content_hash_for(
        channel=channel,
        account_id=account.id if account else None,
        occurred_at=occurred_at,
        sender_identity=sender_identity,
        body=body_text or body_html or "",
    )
    rfc_message_id = str(payload.get("rfc_message_id") or "").strip() or None
    duplicate = find_duplicate(
        db,
        source=source,
        external_provider_id=external_id,
        account_id=account.id if account else None,
        content_hash=digest,
        occurred_at=occurred_at,
        sender_identity=sender_identity,
        rfc_message_id=rfc_message_id,
    )
    if duplicate:
        logger.info("live_comm_dedupe_hit id=%s source=%s", duplicate.id, source)
        return duplicate, False

    bitrix_hit = find_bitrix_email_activity(
        db,
        rfc_message_id=rfc_message_id,
        subject=subject,
        occurred_at=occurred_at,
        sender_identity=sender_identity,
    )
    skip_timeline = False
    bitrix_contact_id: UUID | None = None
    if bitrix_hit is not None:
        skip_timeline = True
        if bitrix_hit.entity_type == CrmActivityEntityType.CONTACT:
            bitrix_contact_id = bitrix_hit.entity_id

    explicit_contact = payload.get("contact_id")
    contact_id = UUID(str(explicit_contact)) if explicit_contact else None
    if contact_id and db.get(CrmContact, contact_id) is None:
        raise ValueError("unknown_contact")
    agreement_id = payload.get("agreement_id")
    if agreement_id:
        agreement_id = UUID(str(agreement_id))
        if db.get(CrmAgreement, agreement_id) is None:
            raise ValueError("unknown_agreement")
    else:
        agreement_id = None

    decision: MatchDecision
    if contact_id:
        decision = MatchDecision(status="matched", contact_id=contact_id)
    else:
        emails, phones = _collect_match_inputs(
            channel,
            payload,
            direction=direction,
            account_identity=account.identity if account else None,
        )
        decision = match_identities(db, emails=emails, phones=phones)
        contact_id = decision.contact_id
    if contact_id is None and bitrix_contact_id is not None and decision.status == "unmatched":
        contact_id = bitrix_contact_id
        decision = MatchDecision(status="matched", contact_id=contact_id)

    owner_id = account.user_id if account else (actor.id if actor else None)
    thread = _ensure_thread(
        db,
        channel=channel,
        conversation_key=conversation_key,
        subject=subject,
        owner_id=owner_id,
    )
    comm = CrmCommunication(
        channel=channel,
        direction=direction,
        status=CrmCommunicationStatus.DELIVERED.value,
        subject=subject,
        preview=preview,
        body=body_text,
        body_html=body_html,
        body_text=body_text,
        raw_source=raw_source,
        recipients=raw_recipients if isinstance(raw_recipients, list) else None,
        cc_recipients=payload.get("cc") or payload.get("cc_recipients"),
        thread_id=thread.id if thread else None,
        parent_communication_id=None,
        external_provider_id=external_id,
        provider_thread_id=conversation_key,
        sent_at=occurred_at,
        occurred_at=occurred_at,
        owner_id=owner_id,
        assigned_user_id=owner_id,
        account_id=account.id if account else None,
        source=source,
        match_status=decision.status,
        contact_id=contact_id,
        agreement_id=agreement_id,
        sender_identity=sender_identity,
        recipient_identities=recipient_identities or None,
        content_hash=digest,
        conversation_key=conversation_key,
        suggested_matches=[item.as_dict() for item in decision.suggestions],
        recipient_entity_type="contact" if contact_id else None,
        recipient_entity_id=contact_id,
        created_by=actor.id if actor else owner_id,
        metadata_json={
            "live_ingest": True,
            "source": source,
            "rfc_message_id": rfc_message_id,
            "skip_timeline": skip_timeline,
            "bitrix_activity_id": str(bitrix_hit.id) if bitrix_hit is not None else None,
        },
    )
    db.add(comm)
    db.flush()

    for item in payload.get("attachments") or []:
        file_name = str(item.get("file_name") or item.get("filename") or "attachment")
        mime_type = item.get("mime_type")
        document_id = item.get("document_id")
        content_b64 = item.get("content_base64")
        checksum = item.get("checksum")
        document = None
        if document_id:
            document = db.get(Document, UUID(str(document_id)))
        elif content_b64:
            import base64

            content = base64.b64decode(content_b64)
            document, checksum = _store_attachment_bytes(
                db,
                file_name=file_name,
                mime_type=mime_type,
                content=content,
                actor_id=owner_id,
                communication_id=comm.id,
                contact_id=contact_id,
                agreement_id=agreement_id,
            )
        if document and contact_id:
            _link_document(db, document.id, "crm_contact", contact_id, "communication_attachment")
        if document and agreement_id:
            _link_document(db, document.id, "crm_agreement", agreement_id, "communication_attachment")
        db.add(
            CrmCommunicationAttachment(
                communication_id=comm.id,
                file_name=file_name,
                file_size=item.get("file_size") or (document.file_size if document else None),
                mime_type=mime_type or (document.mime_type if document else None),
                storage_key=document.storage_key if document else None,
                document_id=document.id if document else None,
                checksum=checksum or (document.checksum if document else None),
            )
        )

    if comm.match_status == CrmCommunicationMatchStatus.MATCHED.value and comm.contact_id:
        project_to_person_timeline(db, comm, actor=actor)

    record_communication_audit(
        db,
        event_type="live.ingested",
        communication_id=comm.id,
        thread_id=comm.thread_id,
        actor=actor,
        details={
            "source": source,
            "channel": channel,
            "match_status": comm.match_status,
            "duplicate": False,
        },
    )
    logger.info(
        "live_comm_ingested id=%s channel=%s source=%s match=%s",
        comm.id,
        channel,
        source,
        comm.match_status,
    )
    return comm, True


def confirm_match(
    db: Session,
    communication_id: UUID,
    *,
    contact_id: UUID,
    agreement_id: UUID | None,
    actor: User,
) -> CrmCommunication:
    comm = db.get(CrmCommunication, communication_id)
    if comm is None or comm.archived_at is not None:
        raise ValueError("not_found")
    if db.get(CrmContact, contact_id) is None:
        raise ValueError("unknown_contact")
    if agreement_id and db.get(CrmAgreement, agreement_id) is None:
        raise ValueError("unknown_agreement")
    comm.contact_id = contact_id
    comm.agreement_id = agreement_id
    comm.match_status = CrmCommunicationMatchStatus.MATCHED.value
    comm.recipient_entity_type = "contact"
    comm.recipient_entity_id = contact_id
    for attachment in comm.attachments or []:
        if attachment.document_id:
            _link_document(db, attachment.document_id, "crm_contact", contact_id, "communication_attachment")
            if agreement_id:
                _link_document(db, attachment.document_id, "crm_agreement", agreement_id, "communication_attachment")
    project_to_person_timeline(db, comm, actor=actor)
    record_communication_audit(
        db,
        event_type="live.matched",
        communication_id=comm.id,
        actor=actor,
        details={"contact_id": str(contact_id), "agreement_id": str(agreement_id) if agreement_id else None},
    )
    return comm


def ignore_unmatched(db: Session, communication_id: UUID, *, actor: User) -> CrmCommunication:
    comm = db.get(CrmCommunication, communication_id)
    if comm is None:
        raise ValueError("not_found")
    comm.match_status = CrmCommunicationMatchStatus.IGNORED.value
    record_communication_audit(
        db,
        event_type="live.ignored",
        communication_id=comm.id,
        actor=actor,
    )
    return comm
