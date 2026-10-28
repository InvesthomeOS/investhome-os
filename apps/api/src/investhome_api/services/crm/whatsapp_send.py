"""Send a customer WhatsApp text through Meta Cloud API and store it in CRM.

A CRM row is written only after Meta accepts the message. SMTP and wa.me are not used.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.config.settings import get_settings
from investhome_api.core.logging_config import get_logger
from investhome_api.models.crm_activity import CrmActivity
from investhome_api.models.crm_communication import (
    CrmCommunication,
    CrmCommunicationChannel,
    CrmCommunicationDirection,
    CrmCommunicationStatus,
)
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.lead import Lead
from investhome_api.models.user_auth import User
from investhome_api.services.crm.identity import NormalizedPhone, parse_phone, phones_match
from investhome_api.services.crm.live_ingest import ingest_live_message
from investhome_api.services.crm.whatsapp_cloud import WhatsAppCloudClient, WhatsAppCloudError
from investhome_api.services.crm.whatsapp_graph_version import (
    WhatsAppGraphVersionError,
    normalize_graph_api_version,
)
from investhome_api.services.crm_communication_activity import record_communication_audit

logger = get_logger("investhome.whatsapp.send")

_WHATSAPP = CrmCommunicationChannel.WHATSAPP.value
_OUTBOUND = CrmCommunicationDirection.OUTBOUND.value


class WhatsAppCustomerSendError(Exception):
    def __init__(
        self,
        code: str,
        status_code: int = 400,
        *,
        provider_code: str | None = None,
        provider_message: str | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code
        self.provider_code = provider_code
        self.provider_message = provider_message

    def as_detail(self) -> str | dict[str, str]:
        if not self.provider_code and not self.provider_message:
            return self.code
        detail: dict[str, str] = {"message": self.code, "code": self.code}
        if self.provider_code:
            detail["provider_code"] = self.provider_code
        if self.provider_message:
            detail["provider_message"] = self.provider_message
        return detail


def whatsapp_delivery_label(comm: CrmCommunication) -> str | None:
    if comm.direction != _OUTBOUND:
        return None
    meta = comm.metadata_json if isinstance(comm.metadata_json, dict) else {}
    label = str(meta.get("whatsapp_status") or "").strip().lower()
    if label in {"sent", "delivered", "read", "failed"}:
        return label
    if comm.opened_at is not None:
        return "read"
    if comm.delivered_at is not None:
        return "delivered"
    if comm.failed_at is not None and comm.status == CrmCommunicationStatus.FAILED.value:
        return "failed"
    if comm.sent_at is not None or comm.status == CrmCommunicationStatus.SENT.value:
        return "sent"
    return None


def _valid_phone(value: str | None) -> NormalizedPhone | None:
    parsed = parse_phone(value)
    if parsed is None or not parsed.e164 or parsed.suspicious:
        return None
    return parsed


def _digits(phone: NormalizedPhone) -> str:
    return phone.e164.lstrip("+") if phone.e164 else ""


def _stored_phones(contact: CrmContact | None, lead: Lead | None) -> list[NormalizedPhone]:
    values: list[str | None] = []
    if contact is not None:
        values.append(contact.primary_phone)
        values.append(contact.whatsapp)
        for item in contact.secondary_phones or []:
            values.append(str(item) if item else None)
    if lead is not None:
        values.append(lead.phone)
    unique: list[NormalizedPhone] = []
    seen: set[str] = set()
    for value in values:
        parsed = _valid_phone(value)
        if parsed is None or parsed.match_key in seen:
            continue
        seen.add(parsed.match_key)
        unique.append(parsed)
    return unique


def _require_cloud_credentials() -> tuple[str, str, str]:
    settings = get_settings()
    token = (settings.whatsapp_access_token or "").strip()
    phone_number_id = (settings.whatsapp_phone_number_id or "").strip()
    if not token or not phone_number_id or not phone_number_id.isdigit():
        logger.warning(
            "whatsapp_send_missing_credentials token_set=%s phone_number_id_set=%s",
            bool(token),
            bool(phone_number_id),
        )
        raise WhatsAppCustomerSendError("whatsapp_not_configured", 503)
    try:
        version = normalize_graph_api_version(settings.whatsapp_graph_api_version)
    except WhatsAppGraphVersionError:
        logger.warning("whatsapp_graph_version_invalid")
        raise WhatsAppCustomerSendError("whatsapp_graph_version_invalid", 503) from None
    return token, phone_number_id, version


def _load_contact(db: Session, contact_id: UUID | None) -> CrmContact | None:
    if contact_id is None:
        return None
    contact = db.get(CrmContact, contact_id)
    if contact is None or contact.archived_at is not None:
        raise WhatsAppCustomerSendError("contact_not_found", 404)
    return contact


def _load_lead(db: Session, lead_id: UUID | None) -> Lead | None:
    if lead_id is None:
        return None
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise WhatsAppCustomerSendError("lead_not_found", 404)
    return lead


def _load_reply(
    db: Session,
    *,
    communication_id: UUID | None,
    activity_id: UUID | None,
) -> CrmCommunication | None:
    if communication_id is None and activity_id is None:
        return None
    if communication_id is not None:
        comm = db.get(CrmCommunication, communication_id)
        if (
            comm is None
            or comm.archived_at is not None
            or comm.channel != _WHATSAPP
        ):
            raise WhatsAppCustomerSendError("communication_not_found", 404)
        return comm
    comm = db.scalar(
        select(CrmCommunication).where(
            CrmCommunication.activity_id == activity_id,
            CrmCommunication.channel == _WHATSAPP,
            CrmCommunication.archived_at.is_(None),
        )
    )
    if comm is not None:
        return comm
    activity = db.get(CrmActivity, activity_id)
    raw = None
    if activity is not None and isinstance(activity.metadata_json, dict):
        raw = activity.metadata_json.get("communication_id")
    if raw:
        try:
            linked = db.get(CrmCommunication, UUID(str(raw)))
        except ValueError:
            linked = None
        if linked is not None and linked.archived_at is None and linked.channel == _WHATSAPP:
            return linked
    raise WhatsAppCustomerSendError("communication_not_found", 404)


def _thread_phone(comm: CrmCommunication) -> NormalizedPhone:
    candidates: list[str | None] = [comm.conversation_key]
    if comm.direction == _OUTBOUND:
        candidates.extend(str(item) for item in (comm.recipient_identities or []) if item)
    else:
        candidates.append(comm.sender_identity)
        candidates.extend(str(item) for item in (comm.recipient_identities or []) if item)
    for value in candidates:
        parsed = _valid_phone(value)
        if parsed is not None:
            return parsed
    raise WhatsAppCustomerSendError("whatsapp_phone_invalid", 400)


def _choose_new_phone(
    stored: list[NormalizedPhone],
    explicit: str | None,
) -> NormalizedPhone:
    if not stored:
        raise WhatsAppCustomerSendError("whatsapp_phone_missing", 400)
    text = (explicit or "").strip()
    if not text:
        if len(stored) == 1:
            return stored[0]
        raise WhatsAppCustomerSendError("whatsapp_phone_ambiguous", 400)
    parsed = parse_phone(text)
    if parsed is None or not parsed.e164 or parsed.suspicious:
        raise WhatsAppCustomerSendError("whatsapp_phone_invalid", 400)
    for item in stored:
        if phones_match(item.e164, parsed.e164):
            return item
    raise WhatsAppCustomerSendError("recipient_not_allowed", 400)


def _reuse_conversation_key(
    db: Session,
    *,
    contact_id: UUID | None,
    phone: NormalizedPhone,
) -> str:
    digits = _digits(phone)
    if contact_id is None:
        return digits
    rows = db.scalars(
        select(CrmCommunication).where(
            CrmCommunication.channel == _WHATSAPP,
            CrmCommunication.contact_id == contact_id,
            CrmCommunication.archived_at.is_(None),
            CrmCommunication.conversation_key.is_not(None),
        )
    ).all()
    for row in rows:
        if phones_match(row.conversation_key, phone.e164):
            return str(row.conversation_key)
    return digits


def _idempotent_row(db: Session, actor_id: UUID, key: str | None) -> CrmCommunication | None:
    cleaned = (key or "").strip()
    if not cleaned:
        return None
    rows = db.scalars(
        select(CrmCommunication).where(
            CrmCommunication.channel == _WHATSAPP,
            CrmCommunication.direction == _OUTBOUND,
            CrmCommunication.created_by == actor_id,
            CrmCommunication.archived_at.is_(None),
        )
    ).all()
    for row in rows:
        meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        if str(meta.get("whatsapp_idempotency_key") or "") == cleaned:
            return row
    return None


def _mirror_delivery(db: Session, comm: CrmCommunication) -> None:
    if comm.activity_id is None:
        return
    activity = db.get(CrmActivity, comm.activity_id)
    if activity is None or not isinstance(activity.metadata_json, dict):
        return
    meta = dict(activity.metadata_json)
    live = dict(meta.get("live_thread") or {}) if isinstance(meta.get("live_thread"), dict) else {}
    label = whatsapp_delivery_label(comm)
    if label:
        live["delivery_status"] = label
    if comm.failure_reason:
        live["failure_reason"] = comm.failure_reason
    meta["live_thread"] = live
    activity.metadata_json = meta
    flag_modified(activity, "metadata_json")


def send_customer_whatsapp(
    db: Session,
    *,
    actor: User,
    contact_id: UUID | None,
    lead_id: UUID | None,
    communication_id: UUID | None,
    activity_id: UUID | None,
    to: str | None,
    body_text: str,
    idempotency_key: str | None = None,
    client_factory: type[WhatsAppCloudClient] | None = None,
) -> tuple[CrmCommunication, bool]:
    text = (body_text or "").strip()
    if not text:
        raise WhatsAppCustomerSendError("whatsapp_body_missing", 400)
    if len(text) > 4096:
        raise WhatsAppCustomerSendError("whatsapp_body_too_long", 400)

    existing = _idempotent_row(db, actor.id, idempotency_key)
    if existing is not None:
        return existing, False

    reply = _load_reply(db, communication_id=communication_id, activity_id=activity_id)
    contact = _load_contact(db, contact_id)
    lead = _load_lead(db, lead_id)
    if reply is not None and reply.contact_id is not None:
        if contact is not None and contact.id != reply.contact_id:
            raise WhatsAppCustomerSendError("recipient_not_allowed", 400)
        if contact is None:
            contact = _load_contact(db, reply.contact_id)
    elif contact is None and lead is not None and lead.converted_contact_id is not None:
        contact = _load_contact(db, lead.converted_contact_id)

    if reply is None and contact is None and lead is None:
        raise WhatsAppCustomerSendError("whatsapp_target_missing", 400)

    if reply is not None:
        phone = _thread_phone(reply)
        if (to or "").strip() and not phones_match(to, phone.e164):
            raise WhatsAppCustomerSendError("recipient_not_allowed", 400)
        conversation_key = str(reply.conversation_key or _digits(phone))
    else:
        phone = _choose_new_phone(_stored_phones(contact, lead), to)
        conversation_key = _reuse_conversation_key(
            db,
            contact_id=contact.id if contact else None,
            phone=phone,
        )

    token, phone_number_id, graph_api_version = _require_cloud_credentials()
    factory = client_factory or WhatsAppCloudClient
    try:
        client = factory(
            access_token=token,
            phone_number_id=phone_number_id,
            graph_api_version=graph_api_version,
        )
        wamid = client.send_text(to=_digits(phone), body=text)
    except WhatsAppGraphVersionError:
        raise WhatsAppCustomerSendError("whatsapp_graph_version_invalid", 503) from None
    except WhatsAppCloudError as exc:
        if exc.template_required:
            raise WhatsAppCustomerSendError(
                "whatsapp_template_required",
                409,
                provider_code=exc.provider_code,
                provider_message=exc.provider_message,
            ) from None
        raise WhatsAppCustomerSendError(
            "whatsapp_send_failed",
            502,
            provider_code=exc.provider_code,
            provider_message=exc.provider_message,
        ) from None

    metadata: dict[str, Any] = {
        "whatsapp_send": True,
        "wamid": wamid,
        "whatsapp_status": "sent",
        "whatsapp_delivery_rank": 1,
        "phone_number_id": phone_number_id,
        "reply_to_communication_id": str(reply.id) if reply is not None else None,
        "lead_id": str(lead.id) if lead is not None else None,
    }
    cleaned_key = (idempotency_key or "").strip()
    if cleaned_key:
        metadata["whatsapp_idempotency_key"] = cleaned_key
    occurred = datetime.now(UTC).replace(microsecond=0)
    metadata["whatsapp_delivery_at"] = int(occurred.timestamp())
    try:
        comm, created = ingest_live_message(
            db,
            {
                "channel": "whatsapp",
                "direction": "outgoing",
                "source": "live_whatsapp",
                "sender": None,
                "recipients": [_digits(phone)],
                "body_text": text,
                "external_provider_id": wamid,
                "conversation_key": conversation_key,
                "contact_id": str(contact.id) if contact is not None else None,
                "occurred_at": occurred,
                "metadata_json": metadata,
            },
            actor=actor,
        )
    except Exception:
        logger.exception("whatsapp_send_crm_persist_failed wamid=%s", wamid)
        raise WhatsAppCustomerSendError("crm_persist_failed", 500) from None

    if created:
        comm.status = CrmCommunicationStatus.SENT.value
        comm.sent_at = comm.sent_at or occurred
        meta = dict(comm.metadata_json) if isinstance(comm.metadata_json, dict) else {}
        meta.update(metadata)
        comm.metadata_json = meta
        flag_modified(comm, "metadata_json")
        _mirror_delivery(db, comm)
        record_communication_audit(
            db,
            event_type="communication.whatsapp_sent",
            communication_id=comm.id,
            thread_id=comm.thread_id,
            actor=actor,
            details={
                "wamid": wamid,
                "actor_user_id": str(actor.id),
                "phone_number_id": phone_number_id,
            },
        )
    return comm, created
