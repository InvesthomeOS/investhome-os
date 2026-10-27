"""Queue email after a new inbound Meta CRM communication is committed.

The webhook never sends SMTP. This module only receives a communication id.
"""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parseaddr
from html import escape
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.config.settings import get_settings
from investhome_api.core.logging_config import get_logger
from investhome_api.db import session as db_session
from investhome_api.models.crm_communication import CrmCommunication
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.lead import Lead
from investhome_api.models.user_auth import Role, User, UserRole, UserStatus
from investhome_api.services.notification_gateway import (
    GatewayMessage,
    NotificationChannel,
    get_notification_gateway,
)

logger = get_logger("investhome.crm.meta_inbound_email")

JOB_META_INBOUND_EMAIL = "meta_inbound_email_job"
LOCK_PREFIX = "crm:meta-inbound-email:"
LOCK_TTL_SECONDS = 15 * 60
ENQUEUE_WAIT_SECONDS = 5
PREVIEW_LIMIT = 240
NOTIFY_KEY = "inbound_email_notification"
SALES_ROLE_CODE = "sales"
FALLBACK_RECIPIENT_KEY = "fallback"

_INBOUND_CHANNELS = frozenset({"facebook", "instagram"})
_INBOUND_SOURCES = frozenset({"live_facebook", "live_instagram"})
_INBOUND_KINDS = frozenset({"dm", "comment"})
_REMOVAL_TOKENS = frozenset({"delete", "deleted", "remove", "removed", "hide", "hidden"})
_REMOVAL_KEYS = ("verb", "action", "event", "change_type")


class MetaInboundEmailRetry(Exception):
    """SMTP or lock backend failed. ARQ may retry. The CRM row stays committed."""


class NotifyLock(Protocol):
    def claim(self, key: str, ttl_seconds: int) -> bool:
        """Return True when this worker newly owns the key."""

    def release(self, key: str) -> None:
        """Drop the key so a failed send can be retried."""


class MemoryNotifyLock:
    def __init__(self) -> None:
        self._held: set[str] = set()

    def claim(self, key: str, ttl_seconds: int) -> bool:
        del ttl_seconds
        if key in self._held:
            return False
        self._held.add(key)
        return True

    def release(self, key: str) -> None:
        self._held.discard(key)


class RedisNotifyLock:
    def _client(self) -> Any:
        import redis

        settings = get_settings()
        return redis.Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=1.5,
            socket_timeout=1.5,
            decode_responses=True,
        )

    def claim(self, key: str, ttl_seconds: int) -> bool:
        client = self._client()
        try:
            created = client.set(key, "1", nx=True, ex=max(1, ttl_seconds))
            return bool(created)
        finally:
            client.close()

    def release(self, key: str) -> None:
        client = self._client()
        try:
            client.delete(key)
        finally:
            client.close()


def _notify_lock() -> NotifyLock:
    return RedisNotifyLock()


def enqueue_meta_inbound_email_notifications(communication_ids: list[UUID]) -> None:
    """Queue jobs after commit. Redis failure is logged and swallowed."""
    if not get_settings().crm_inbound_email_notifications_enabled:
        return
    unique: list[str] = []
    seen: set[str] = set()
    for item in communication_ids:
        if item is None:
            continue
        key = str(item)
        if key in seen:
            continue
        seen.add(key)
        unique.append(key)
    if not unique:
        return
    try:
        _enqueue_ids(unique)
    except Exception:
        logger.exception("meta_inbound_email_enqueue_failed count=%s", len(unique))
        return
    for communication_id in unique:
        logger.info("meta_inbound_email_enqueued communication_id=%s", communication_id)


def _enqueue_ids(communication_ids: list[str]) -> None:
    settings = get_settings()

    async def _run() -> None:
        from arq import create_pool
        from arq.connections import RedisSettings

        pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        try:
            for communication_id in communication_ids:
                await pool.enqueue_job(
                    JOB_META_INBOUND_EMAIL,
                    communication_id,
                    _job_id=f"crm-meta-inbound-email:{communication_id}",
                )
        finally:
            await pool.close()

    def _run_blocking() -> None:
        asyncio.run(_run())

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        _run_blocking()
        return

    done = threading.Event()
    error: list[BaseException] = []

    def _thread() -> None:
        try:
            _run_blocking()
        except Exception as exc:
            error.append(exc)
        finally:
            done.set()

    threading.Thread(target=_thread, daemon=True).start()
    if not done.wait(ENQUEUE_WAIT_SECONDS):
        raise TimeoutError("meta inbound email enqueue timed out")
    if error:
        raise error[0]


def _meta(comm: CrmCommunication) -> dict[str, Any]:
    raw = comm.metadata_json if isinstance(comm.metadata_json, dict) else {}
    return raw


def _notification_status(meta: dict[str, Any]) -> str:
    notice = meta.get(NOTIFY_KEY)
    if not isinstance(notice, dict):
        return ""
    return str(notice.get("status") or "").strip().lower()


def _removal_signal(meta: dict[str, Any]) -> bool:
    if meta.get("deleted_on_platform") or meta.get("deleted_at"):
        return True
    sources: list[dict[str, Any]] = [meta]
    context = meta.get("comment_context")
    if isinstance(context, dict):
        sources.append(context)
    for source in sources:
        for key in _REMOVAL_KEYS:
            value = str(source.get(key) or "").strip().lower()
            if value in _REMOVAL_TOKENS:
                return True
    return False


def _eligible(comm: CrmCommunication) -> bool:
    if comm.archived_at is not None:
        return False
    if comm.direction != "inbound":
        return False
    if comm.channel not in _INBOUND_CHANNELS:
        return False
    if comm.source not in _INBOUND_SOURCES:
        return False
    meta = _meta(comm)
    kind = str(meta.get("kind") or "").strip().lower()
    if kind not in _INBOUND_KINDS:
        return False
    if meta.get("outbound") is True or meta.get("page_owned") is True:
        return False
    context = meta.get("comment_context")
    if isinstance(context, dict) and context.get("page_owned") is True:
        return False
    return not _removal_signal(meta)


def _usable_email(value: str | None) -> str | None:
    text = (value or "").strip()
    if not text or any(char.isspace() for char in text):
        return None
    _name, addr = parseaddr(text)
    if "@" not in addr:
        return None
    local, _, domain = addr.partition("@")
    if not local or "." not in domain or addr.startswith("@") or addr.endswith("@"):
        return None
    return addr


@dataclass(frozen=True)
class NotifyRecipient:
    key: str
    email: str
    source: str


def _active_sales_users(db: Session) -> list[User]:
    """Users linked to the sales role through user_roles. Role code is the canonical key."""
    return list(
        db.scalars(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                Role.code == SALES_ROLE_CODE,
                User.status == UserStatus.ACTIVE,
                User.archived_at.is_(None),
            )
            .order_by(User.email.asc())
        )
        .unique()
        .all()
    )


def _append_user(
    recipients: list[NotifyRecipient],
    seen_ids: set[UUID],
    seen_emails: set[str],
    user: User | None,
    source: str,
) -> None:
    if user is None or user.archived_at is not None or user.status != UserStatus.ACTIVE:
        return
    email = _usable_email(user.email)
    if email is None or user.id in seen_ids or email.casefold() in seen_emails:
        return
    seen_ids.add(user.id)
    seen_emails.add(email.casefold())
    recipients.append(NotifyRecipient(key=str(user.id), email=email, source=source))


def resolve_recipients(db: Session, comm: CrmCommunication) -> list[NotifyRecipient]:
    """Active sales users, plus an assigned owner or lead manager who is not already included."""
    recipients: list[NotifyRecipient] = []
    seen_ids: set[UUID] = set()
    seen_emails: set[str] = set()
    for user in _active_sales_users(db):
        _append_user(recipients, seen_ids, seen_emails, user, "sales_role")
    contact = db.get(CrmContact, comm.contact_id) if comm.contact_id else None
    if contact is not None and contact.archived_at is None:
        if contact.owner_user_id is not None:
            _append_user(
                recipients,
                seen_ids,
                seen_emails,
                db.get(User, contact.owner_user_id),
                "contact_owner",
            )
        lead = db.get(Lead, contact.lead_id) if contact.lead_id else None
        if lead is not None and lead.archived_at is None and lead.assigned_manager_id is not None:
            _append_user(
                recipients,
                seen_ids,
                seen_emails,
                db.get(User, lead.assigned_manager_id),
                "lead_manager",
            )
    if recipients:
        return recipients
    fallback = _usable_email(get_settings().crm_inbound_notify_email)
    if fallback:
        return [NotifyRecipient(key=FALLBACK_RECIPIENT_KEY, email=fallback, source="fallback")]
    return []


def _display_name(comm: CrmCommunication, contact: CrmContact | None) -> str:
    if contact is not None:
        name = (contact.display_name or "").strip()
        if name:
            return name
    meta = _meta(comm)
    raw_context = meta.get("comment_context")
    context: dict[str, Any] = raw_context if isinstance(raw_context, dict) else {}
    for value in (context.get("commenter_name"), comm.sender_identity):
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _interested_project(db: Session, contact: CrmContact | None) -> str:
    if contact is None or contact.lead_id is None:
        return ""
    lead = db.get(Lead, contact.lead_id)
    if lead is None:
        return ""
    return (lead.interested_project or "").strip()


def _preview_text(comm: CrmCommunication) -> str:
    raw = (comm.body_text or comm.preview or "").strip()
    compact = " ".join(raw.split())
    if len(compact) <= PREVIEW_LIMIT:
        return compact
    return compact[:PREVIEW_LIMIT].rstrip() + "…"


def _public_base() -> str:
    settings = get_settings()
    public = (settings.app_public_url or "").strip().rstrip("/")
    if public:
        return public
    origins = settings.cors_origins or ["http://localhost:3000"]
    return str(origins[0]).rstrip("/")


def _crm_link(comm: CrmCommunication) -> str:
    base = _public_base()
    if comm.contact_id is not None:
        return f"{base}/workspaces/crm/contacts/{comm.contact_id}"
    return f"{base}/workspaces/crm/communication"


def _labels(comm: CrmCommunication) -> tuple[str, str, str]:
    meta = _meta(comm)
    kind = str(meta.get("kind") or "").strip().lower()
    platform = "Instagram" if comm.channel == "instagram" else "Facebook"
    type_label = "Yorum" if kind == "comment" else "Mesaj"
    subject_kind = "Yorumu" if kind == "comment" else "Mesajı"
    return platform, type_label, subject_kind


def _format_when(comm: CrmCommunication) -> str:
    moment = comm.occurred_at or comm.created_at
    if moment is None:
        return ""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def _build_message(
    comm: CrmCommunication,
    *,
    recipient: str,
    name: str,
    project: str,
) -> GatewayMessage:
    platform, type_label, subject_kind = _labels(comm)
    subject = f"[Investhome CRM] Yeni {platform} {subject_kind}"
    if name:
        subject = f"{subject} — {name}"
    preview = _preview_text(comm)
    when = _format_when(comm)
    link = _crm_link(comm)
    lines = [
        "Investhome CRM",
        "",
        f"Platform: {platform}",
        f"Tür: {type_label}",
    ]
    if name:
        lines.append(f"Gönderen: {name}")
    if preview:
        lines.append(f"Önizleme: {preview}")
    if project:
        lines.append(f"İlgili proje: {project}")
    if when:
        lines.append(f"Tarih: {when}")
    lines.extend(["", "Kaydı aç:", link])
    text_body = "\n".join(lines)
    html_body = _html_body(
        platform=platform,
        type_label=type_label,
        name=name,
        preview=preview,
        project=project,
        when=when,
        link=link,
    )
    return GatewayMessage(
        channel=NotificationChannel.EMAIL,
        recipient=recipient,
        subject=subject,
        body=text_body,
        html_body=html_body,
        locale="tr",
        metadata={"purpose": "meta_inbound_crm"},
    )


def _html_body(
    *,
    platform: str,
    type_label: str,
    name: str,
    preview: str,
    project: str,
    when: str,
    link: str,
) -> str:
    rows = [
        ("Platform", platform),
        ("Tür", type_label),
    ]
    if name:
        rows.append(("Gönderen", name))
    if preview:
        rows.append(("Önizleme", preview))
    if project:
        rows.append(("İlgili proje", project))
    if when:
        rows.append(("Tarih", when))
    rendered = "".join(
        "<tr><td style=\"padding:4px 12px 4px 0;font-weight:bold;vertical-align:top;\">"
        f"{escape(label)}</td><td style=\"padding:4px 0;\">{escape(value)}</td></tr>"
        for label, value in rows
    )
    href = escape(link, quote=True)
    return (
        "<!DOCTYPE html><html lang=\"tr\">"
        "<body style=\"font-family:Arial,sans-serif;color:#1A1A1A;\">"
        "<p>Investhome CRM</p>"
        f"<table role=\"presentation\" cellpadding=\"0\" cellspacing=\"0\">{rendered}</table>"
        "<p style=\"margin-top:20px;\">"
        f"<a href=\"{href}\" style=\"background:#C4A15A;color:#ffffff;padding:12px 18px;"
        "text-decoration:none;border-radius:4px;display:inline-block;\">Kaydı aç</a></p>"
        "</body></html>"
    )


def _notice(meta: dict[str, Any]) -> dict[str, Any]:
    raw = meta.get(NOTIFY_KEY)
    return dict(raw) if isinstance(raw, dict) else {}


def _recipient_state(meta: dict[str, Any]) -> dict[str, Any]:
    raw = _notice(meta).get("recipients")
    if not isinstance(raw, dict):
        return {}
    return {str(key): value for key, value in raw.items() if isinstance(value, dict)}


def _sent_keys(meta: dict[str, Any]) -> set[str]:
    return {
        key
        for key, row in _recipient_state(meta).items()
        if str(row.get("status") or "").strip().lower() == "sent"
    }


def _pending(recipients: list[NotifyRecipient], meta: dict[str, Any]) -> list[NotifyRecipient]:
    sent = _sent_keys(meta)
    return [item for item in recipients if item.key not in sent]


def _record_recipient_sent(
    db: Session,
    comm: CrmCommunication,
    recipient: NotifyRecipient,
    expected_keys: set[str],
) -> None:
    meta = dict(_meta(comm))
    notice = _notice(meta)
    recipients = _recipient_state(meta)
    sent_at = datetime.now(UTC).isoformat()
    recipients[recipient.key] = {
        "status": "sent",
        "sent_at": sent_at,
        "source": recipient.source,
    }
    sent_now = {
        key
        for key, row in recipients.items()
        if str(row.get("status") or "").strip().lower() == "sent"
    }
    complete = bool(expected_keys) and expected_keys <= sent_now
    notice_out: dict[str, Any] = {
        "status": "sent" if complete else "partial",
        "recipients": recipients,
    }
    if complete:
        notice_out["sent_at"] = sent_at
    elif notice.get("sent_at"):
        notice_out["sent_at"] = notice.get("sent_at")
    meta[NOTIFY_KEY] = notice_out
    comm.metadata_json = meta
    flag_modified(comm, "metadata_json")
    db.commit()


def _skip(communication_id: UUID, reason: str) -> str:
    logger.info(
        "meta_inbound_email_skipped communication_id=%s reason=%s",
        communication_id,
        reason,
    )
    return "skipped"


def deliver_meta_inbound_email(
    communication_id: UUID,
    *,
    db: Session | None = None,
    lock: NotifyLock | None = None,
) -> str:
    """Send at most one email per recipient. Raise to ask the worker to retry failures."""
    owns_session = db is None
    session = db or db_session.SessionLocal()
    active_lock = lock or _notify_lock()
    lock_key = f"{LOCK_PREFIX}{communication_id}"
    claimed = False
    try:
        if not get_settings().crm_inbound_email_notifications_enabled:
            return _skip(communication_id, "disabled")
        comm = session.get(CrmCommunication, communication_id)
        if comm is None:
            return _skip(communication_id, "missing")
        if _notification_status(_meta(comm)) == "sent":
            return _skip(communication_id, "already_sent")
        if not _eligible(comm):
            return _skip(communication_id, "ineligible")
        recipients = resolve_recipients(session, comm)
        if not recipients:
            return _skip(communication_id, "no_recipient")
        if not _pending(recipients, _meta(comm)):
            return _skip(communication_id, "already_sent")
        try:
            claimed = active_lock.claim(lock_key, LOCK_TTL_SECONDS)
        except Exception as exc:
            logger.warning(
                "meta_inbound_email_send_failed communication_id=%s reason=lock",
                communication_id,
            )
            raise MetaInboundEmailRetry("notify lock unavailable") from exc
        if not claimed:
            return _skip(communication_id, "locked")
        session.refresh(comm)
        if _notification_status(_meta(comm)) == "sent":
            return _skip(communication_id, "already_sent")
        recipients = resolve_recipients(session, comm)
        pending = _pending(recipients, _meta(comm))
        if not pending:
            return _skip(communication_id, "already_sent")
        contact = session.get(CrmContact, comm.contact_id) if comm.contact_id else None
        name = _display_name(comm, contact)
        project = _interested_project(session, contact)
        expected = {item.key for item in recipients}
        failures = 0
        for recipient in pending:
            message = _build_message(comm, recipient=recipient.email, name=name, project=project)
            try:
                result = get_notification_gateway().dispatch(message, provider_id="email_smtp")
            except Exception:
                failures += 1
                logger.warning(
                    "meta_inbound_email_send_failed communication_id=%s reason=gateway source=%s",
                    communication_id,
                    recipient.source,
                )
                continue
            if not result.ok:
                failures += 1
                logger.warning(
                    "meta_inbound_email_send_failed communication_id=%s reason=%s source=%s",
                    communication_id,
                    result.status,
                    recipient.source,
                )
                continue
            try:
                _record_recipient_sent(session, comm, recipient, expected)
            except Exception as exc:
                logger.warning(
                    "meta_inbound_email_send_failed communication_id=%s reason=status_commit",
                    communication_id,
                )
                raise MetaInboundEmailRetry("notification status commit failed") from exc
            logger.info(
                "meta_inbound_email_sent communication_id=%s recipient_source=%s",
                communication_id,
                recipient.source,
            )
        if failures:
            raise MetaInboundEmailRetry("smtp gateway returned failure")
        claimed = False
        return "sent"
    finally:
        if claimed:
            try:
                active_lock.release(lock_key)
            except Exception:
                logger.warning(
                    "meta_inbound_email_send_failed communication_id=%s reason=lock_release",
                    communication_id,
                )
        if owns_session:
            session.close()


async def meta_inbound_email_job(ctx: dict[str, Any], communication_id: str) -> dict[str, str]:
    del ctx
    status = deliver_meta_inbound_email(UUID(str(communication_id)))
    return {"status": status}
