"""Send a customer email through a connected Gmail account and store it in CRM.

SMTP is not used. A message is written to CRM only after Gmail accepts the send.
"""

from __future__ import annotations

import base64
import logging
from datetime import UTC, datetime
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from investhome_api.models.crm_communication import (
    CrmCommunication,
    CrmCommunicationChannel,
    CrmUserCommunicationAccount,
    CrmUserCommunicationAccountStatus,
)
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.lead import Lead
from investhome_api.models.user_auth import User
from investhome_api.services.crm.gmail_client import GmailApiError, GoogleGmailMailbox
from investhome_api.services.crm.gmail_oauth import (
    PILOT_CHANNEL,
    PILOT_PROVIDER,
    gmail_send_granted,
    mark_needs_reauth,
)
from investhome_api.services.crm.identity import normalize_email
from investhome_api.services.crm.live_ingest import ingest_live_message
from investhome_api.services.crm_communication_activity import record_communication_audit

logger = logging.getLogger(__name__)

_SENDABLE_STATUSES = frozenset(
    {
        CrmUserCommunicationAccountStatus.CONNECTED.value,
        CrmUserCommunicationAccountStatus.ERROR.value,
        CrmUserCommunicationAccountStatus.PENDING.value,
    }
)


class GmailCustomerEmailError(Exception):
    def __init__(
        self,
        code: str,
        status_code: int = 400,
        *,
        persist_account_state: bool = False,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code
        self.public_detail = code
        self.persist_account_state = persist_account_state


def _bracket(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    if not cleaned:
        return None
    if cleaned.startswith("<") and cleaned.endswith(">"):
        return cleaned
    return f"<{cleaned.strip('<>')}>"


def _rfc(comm: CrmCommunication) -> str | None:
    meta = comm.metadata_json if isinstance(comm.metadata_json, dict) else {}
    return _bracket(str(meta.get("rfc_message_id") or "") or None)


def _address_list(values: Any) -> list[str]:
    found: list[str] = []
    if not isinstance(values, list):
        return found
    for item in values:
        raw = item
        if isinstance(item, dict):
            raw = item.get("email") or item.get("identity") or item.get("address")
        normalized = normalize_email(str(raw or ""))
        if normalized and normalized not in found:
            found.append(normalized)
    return found


def _participants(comm: CrmCommunication, mailbox: str | None) -> list[str]:
    sender = normalize_email(comm.sender_identity)
    addresses = _address_list(comm.recipient_identities)
    addresses.extend(item for item in _address_list(comm.recipients) if item not in addresses)
    addresses.extend(item for item in _address_list(comm.cc_recipients) if item not in addresses)
    if sender and sender not in addresses:
        addresses.insert(0, sender)
    owned = normalize_email(mailbox)
    return [item for item in addresses if item != owned]


def _reply_targets(
    comm: CrmCommunication,
    mailbox: str | None,
    *,
    reply_all: bool,
) -> tuple[list[str], list[str]]:
    owned = normalize_email(mailbox)
    sender = normalize_email(comm.sender_identity)
    inbound = comm.direction in {"inbound", "incoming"}
    direct = _address_list(comm.recipient_identities) or _address_list(comm.recipients)
    copied = _address_list(comm.cc_recipients)
    if inbound and sender and sender != owned:
        to = [sender]
    else:
        to = [item for item in direct if item != owned]
    if not to:
        to = _participants(comm, mailbox)[:1]
    if not reply_all:
        return to, []
    pool = [*direct, *copied, *([sender] if sender else [])]
    others = [item for item in pool if item not in to and item != owned]
    cc: list[str] = []
    for item in others:
        if item not in cc:
            cc.append(item)
    return to, cc


def _load_communication(
    db: Session,
    *,
    communication_id: UUID | None,
    activity_id: UUID | None,
) -> CrmCommunication | None:
    if communication_id is not None:
        row = db.get(CrmCommunication, communication_id)
        email = CrmCommunicationChannel.EMAIL.value
        if row is not None and row.archived_at is None and row.channel == email:
            return row
        return None
    if activity_id is None:
        return None
    return db.scalar(
        select(CrmCommunication).where(
            CrmCommunication.activity_id == activity_id,
            CrmCommunication.channel == CrmCommunicationChannel.EMAIL.value,
            CrmCommunication.archived_at.is_(None),
        )
    )


def _thread_reference_ids(db: Session, comm: CrmCommunication) -> list[str]:
    key = (comm.conversation_key or comm.provider_thread_id or "").strip()
    rows: list[CrmCommunication]
    if not key:
        rows = [comm]
    else:
        rows = list(
            db.scalars(
                select(CrmCommunication)
                .where(
                    CrmCommunication.account_id == comm.account_id,
                    CrmCommunication.archived_at.is_(None),
                    CrmCommunication.channel == CrmCommunicationChannel.EMAIL.value,
                    or_(
                        CrmCommunication.conversation_key == key,
                        CrmCommunication.provider_thread_id == key,
                    ),
                )
                .order_by(CrmCommunication.occurred_at.asc())
            ).all()
        )
        if comm not in rows:
            rows.append(comm)
    refs: list[str] = []
    for row in rows:
        rfc = _rfc(row)
        if rfc and rfc not in refs:
            refs.append(rfc)
    target = _rfc(comm)
    if target and target not in refs:
        refs.append(target)
    return refs


def _user_gmail_accounts(db: Session, user_id: UUID) -> list[CrmUserCommunicationAccount]:
    return list(
        db.scalars(
            select(CrmUserCommunicationAccount)
            .where(
                CrmUserCommunicationAccount.user_id == user_id,
                CrmUserCommunicationAccount.provider == PILOT_PROVIDER,
                CrmUserCommunicationAccount.channel_type == PILOT_CHANNEL,
                CrmUserCommunicationAccount.archived_at.is_(None),
            )
            .order_by(CrmUserCommunicationAccount.updated_at.desc())
        ).all()
    )


def _ensure_can_send(account: CrmUserCommunicationAccount) -> None:
    if account.archived_at is not None or account.provider != PILOT_PROVIDER:
        raise GmailCustomerEmailError("gmail_account_missing", 409)
    needs_reconnect = account.status == CrmUserCommunicationAccountStatus.NEEDS_REAUTH.value
    if needs_reconnect or not gmail_send_granted(account):
        mark_needs_reauth(account, error="Yeniden yetkilendirme gerekli")
        raise GmailCustomerEmailError("gmail_reconnect_required", 409, persist_account_state=True)
    if account.status not in _SENDABLE_STATUSES:
        raise GmailCustomerEmailError("gmail_reconnect_required", 409, persist_account_state=True)


def _select_new_account(db: Session, actor: User) -> CrmUserCommunicationAccount:
    accounts = _user_gmail_accounts(db, actor.id)
    if not accounts:
        raise GmailCustomerEmailError("gmail_account_missing", 409)
    sendable = [
        item
        for item in accounts
        if item.status in _SENDABLE_STATUSES and gmail_send_granted(item)
    ]
    if sendable:
        return sendable[0]
    chosen = accounts[0]
    mark_needs_reauth(chosen, error="Yeniden yetkilendirme gerekli")
    raise GmailCustomerEmailError("gmail_reconnect_required", 409, persist_account_state=True)


def _contact_emails(contact: CrmContact | None, lead: Lead | None) -> list[str]:
    found: list[str] = []
    if contact is not None:
        primary = normalize_email(contact.primary_email)
        if primary:
            found.append(primary)
        found.extend(item for item in _address_list(contact.secondary_emails) if item not in found)
    if lead is not None:
        lead_email = normalize_email(lead.email)
        if lead_email and lead_email not in found:
            found.append(lead_email)
    return found


def _resolve_new_target(
    db: Session,
    *,
    contact_id: UUID | None,
    lead_id: UUID | None,
) -> tuple[CrmContact | None, Lead | None, list[str]]:
    if contact_id is None and lead_id is None:
        raise GmailCustomerEmailError("contact_email_missing", 400)
    contact: CrmContact | None = None
    lead: Lead | None = None
    if contact_id is not None:
        contact = db.get(CrmContact, contact_id)
        if contact is None or contact.archived_at is not None:
            raise GmailCustomerEmailError("contact_not_found", 404)
    if lead_id is not None:
        lead = db.get(Lead, lead_id)
        if lead is None:
            raise GmailCustomerEmailError("lead_not_found", 404)
        if contact is None:
            contact = db.scalar(
                select(CrmContact).where(
                    CrmContact.lead_id == lead.id,
                    CrmContact.archived_at.is_(None),
                )
            )
    allowed = _contact_emails(contact, lead)
    if not allowed:
        raise GmailCustomerEmailError("contact_email_missing", 400)
    return contact, lead, allowed


def _subset(requested: list[str], allowed: list[str]) -> list[str]:
    allowed_set = set(allowed)
    chosen = [item for item in requested if item in allowed_set]
    if requested and len(chosen) != len(requested):
        raise GmailCustomerEmailError("recipient_not_allowed", 400)
    return chosen


def build_customer_mime(
    *,
    from_email: str,
    to: list[str],
    cc: list[str],
    subject: str,
    body_text: str,
    body_html: str | None,
    in_reply_to: str | None,
    references: list[str],
) -> tuple[str, str]:
    domain = from_email.split("@", 1)[1] if "@" in from_email else "investhome.com.tr"
    message = EmailMessage()
    message["From"] = from_email
    message["To"] = ", ".join(to)
    if cc:
        message["Cc"] = ", ".join(cc)
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=False)
    rfc_message_id = make_msgid(domain=domain)
    message["Message-ID"] = rfc_message_id
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
        reply_refs = list(references)
        if in_reply_to not in reply_refs:
            reply_refs.append(in_reply_to)
        message["References"] = " ".join(reply_refs)
    if body_html:
        message.set_content(body_text or "")
        message.add_alternative(body_html, subtype="html")
    else:
        message.set_content(body_text or "")
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii").rstrip("=")
    return raw, rfc_message_id


def email_reply_context(
    db: Session,
    *,
    communication_id: UUID | None,
    activity_id: UUID | None,
) -> dict[str, Any]:
    comm = _load_communication(db, communication_id=communication_id, activity_id=activity_id)
    if comm is None:
        raise GmailCustomerEmailError("communication_not_found", 404)
    account = db.get(CrmUserCommunicationAccount, comm.account_id) if comm.account_id else None
    mailbox = account.identity if account is not None else None
    to, _cc = _reply_targets(comm, mailbox, reply_all=False)
    _all_to, all_cc = _reply_targets(comm, mailbox, reply_all=True)
    subject = (comm.subject or "").strip()
    if subject and not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    send_block = None
    if account is None or account.archived_at is not None:
        send_block = "gmail_account_missing"
    else:
        needs_reconnect = account.status == CrmUserCommunicationAccountStatus.NEEDS_REAUTH.value
        if needs_reconnect or not gmail_send_granted(account):
            send_block = "gmail_reconnect_required"
    return {
        "to": to,
        "cc": all_cc,
        "subject": subject or "Re:",
        "contact_id": comm.contact_id,
        "from_mailbox": mailbox,
        "can_reply_all": bool(all_cc),
        "send_block": send_block,
    }


def send_customer_email(
    db: Session,
    *,
    actor: User,
    mode: str,
    contact_id: UUID | None,
    lead_id: UUID | None,
    communication_id: UUID | None,
    activity_id: UUID | None,
    to: list[str],
    cc: list[str],
    subject: str,
    body_text: str,
    body_html: str | None,
    mailbox_factory: Any = None,
) -> tuple[CrmCommunication, bool]:
    reply = mode in {"reply", "reply_all"}
    parent: CrmCommunication | None = None
    lead: Lead | None = None
    contact: CrmContact | None = None
    account: CrmUserCommunicationAccount
    thread_id: str | None = None
    in_reply_to: str | None = None
    references: list[str] = []

    if reply:
        parent = _load_communication(db, communication_id=communication_id, activity_id=activity_id)
        if parent is None:
            raise GmailCustomerEmailError("communication_not_found", 404)
        if parent.account_id is None:
            raise GmailCustomerEmailError("gmail_account_missing", 409)
        loaded = db.get(CrmUserCommunicationAccount, parent.account_id)
        if loaded is None:
            raise GmailCustomerEmailError("gmail_account_missing", 409)
        account = loaded
        _ensure_can_send(account)
        default_to, default_cc = _reply_targets(
            parent,
            account.identity,
            reply_all=mode == "reply_all",
        )
        allowed = _participants(parent, account.identity)
        requested_to = _address_list(to)
        requested_cc = _address_list(cc) if mode == "reply_all" else []
        recipients = _subset(requested_to, allowed) if requested_to else default_to
        copied = _subset(requested_cc, allowed) if requested_cc else default_cc
        if not recipients:
            raise GmailCustomerEmailError("contact_email_missing", 400)
        contact = db.get(CrmContact, parent.contact_id) if parent.contact_id else None
        thread_id = (parent.provider_thread_id or parent.conversation_key or "").strip() or None
        references = _thread_reference_ids(db, parent)
        in_reply_to = _rfc(parent) or (references[-1] if references else None)
    else:
        contact, lead, allowed = _resolve_new_target(db, contact_id=contact_id, lead_id=lead_id)
        account = _select_new_account(db, actor)
        _ensure_can_send(account)
        requested_to = _address_list(to)
        recipients = _subset(requested_to, allowed) if requested_to else allowed[:1]
        copied = _subset(_address_list(cc), allowed)
        if not recipients:
            raise GmailCustomerEmailError("contact_email_missing", 400)

    raw, rfc_message_id = build_customer_mime(
        from_email=account.identity,
        to=recipients,
        cc=copied,
        subject=subject.strip(),
        body_text=body_text,
        body_html=body_html,
        in_reply_to=in_reply_to,
        references=references,
    )
    factory = mailbox_factory or GoogleGmailMailbox
    try:
        sent = factory(account).send_message(raw=raw, thread_id=thread_id)
    except GmailApiError as exc:
        if exc.needs_reauth:
            mark_needs_reauth(account, error="Yeniden yetkilendirme gerekli")
            raise GmailCustomerEmailError(
                "gmail_reconnect_required",
                409,
                persist_account_state=True,
            ) from exc
        logger.warning("gmail_customer_send_failed account=%s code=%s", account.id, exc.code)
        raise GmailCustomerEmailError("gmail_send_failed", 502) from exc
    except Exception as exc:
        logger.warning("gmail_customer_send_failed account=%s", account.id)
        raise GmailCustomerEmailError("gmail_send_failed", 502) from exc

    gmail_id = str(sent.get("id") or "").strip()
    returned_thread = str(sent.get("threadId") or thread_id or "").strip()
    if not gmail_id or not returned_thread:
        logger.error("gmail_customer_send_missing_id account=%s", account.id)
        raise GmailCustomerEmailError("gmail_send_failed", 502)

    metadata: dict[str, Any] = {
        "rfc_message_id": rfc_message_id,
        "gmail_send": True,
    }
    if in_reply_to:
        metadata["in_reply_to"] = in_reply_to
    if references:
        metadata["references"] = references
    if parent is not None:
        metadata["reply_to_communication_id"] = str(parent.id)
    if lead is not None:
        metadata["lead_id"] = str(lead.id)
    elif contact is not None and contact.lead_id is not None:
        metadata["lead_id"] = str(contact.lead_id)

    payload = {
        "channel": "email",
        "direction": "outgoing",
        "source": "live_email",
        "account_id": str(account.id),
        "contact_id": str(contact.id) if contact is not None else None,
        "subject": subject.strip(),
        "body_text": body_text,
        "body_html": body_html,
        "sender": account.identity,
        "sender_identity": account.identity,
        "recipients": recipients,
        "cc": copied,
        "occurred_at": datetime.now(UTC),
        "external_provider_id": gmail_id,
        "conversation_id": returned_thread,
        "rfc_message_id": rfc_message_id,
        "metadata_json": metadata,
    }
    try:
        comm, created = ingest_live_message(db, payload, actor=actor)
    except Exception:
        logger.exception(
            "gmail_send_crm_persist_failed account=%s gmail_id=%s thread=%s",
            account.id,
            gmail_id,
            returned_thread,
        )
        raise GmailCustomerEmailError("crm_persist_failed", 500) from None
    record_communication_audit(
        db,
        event_type="communication.email_sent",
        communication_id=comm.id,
        thread_id=comm.thread_id,
        actor=actor,
        details={
            "account_id": str(account.id),
            "gmail_message_id": gmail_id,
            "actor_user_id": str(actor.id),
        },
    )
    return comm, created
