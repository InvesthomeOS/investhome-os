"""Queue email after a new inbound Wazzup WhatsApp row is committed.

Eligibility stays on this module. Recipient selection reuses the sales,
owner, and lead-manager rule. SMTP failure does not delete the CRM row.
"""

from __future__ import annotations

import asyncio
import threading
from datetime import UTC, datetime
from html import escape
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.config.settings import get_settings
from investhome_api.core.logging_config import get_logger
from investhome_api.db import session as db_session
from investhome_api.models.crm_communication import CrmCommunication
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.lead import Lead
from investhome_api.services.crm.meta_inbound_notify import (
    MemoryNotifyLock,
    NotifyLock,
    NotifyRecipient,
    RedisNotifyLock,
    resolve_recipients,
)
from investhome_api.services.notification_gateway import (
    GatewayMessage,
    NotificationChannel,
    get_notification_gateway,
)

logger = get_logger("investhome.crm.wazzup_inbound_email")

JOB_WAZZUP_INBOUND_EMAIL = "wazzup_inbound_email_job"
LOCK_PREFIX = "crm:wazzup-inbound-email:"
LOCK_TTL_SECONDS = 15 * 60
ENQUEUE_WAIT_SECONDS = 5
PREVIEW_LIMIT = 240
NOTIFY_KEY = "wazzup_inbound_email_notification"


class WazzupInboundEmailRetry(Exception):
    """SMTP or lock backend failed. ARQ may retry. The CRM row stays committed."""


def _notify_lock() -> NotifyLock:
    return RedisNotifyLock()


def enqueue_wazzup_inbound_email_notifications(communication_ids: list[UUID]) -> None:
    """Queue jobs after commit. Redis failure is logged and swallowed."""
    if not get_settings().wazzup_inbound_email_notifications_enabled:
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
        logger.exception("wazzup_inbound_email_enqueue_failed count=%s", len(unique))
        return
    for communication_id in unique:
        logger.info("wazzup_inbound_email_enqueued communication_id=%s", communication_id)


def _enqueue_ids(communication_ids: list[str]) -> None:
    settings = get_settings()

    async def _run() -> None:
        from arq import create_pool
        from arq.connections import RedisSettings

        pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        try:
            for communication_id in communication_ids:
                await pool.enqueue_job(
                    JOB_WAZZUP_INBOUND_EMAIL,
                    communication_id,
                    _job_id=f"crm-wazzup-inbound-email:{communication_id}",
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
        raise TimeoutError("wazzup inbound email enqueue timed out")
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


def _eligible(comm: CrmCommunication) -> bool:
    if comm.archived_at is not None:
        return False
    if comm.direction != "inbound":
        return False
    if comm.channel != "whatsapp":
        return False
    return comm.source == "live_wazzup"


def _notice(meta: dict[str, Any]) -> dict[str, Any]:
    raw = meta.get(NOTIFY_KEY)
    return dict(raw) if isinstance(raw, dict) else {}


def _recipient_state(meta: dict[str, Any]) -> dict[str, Any]:
    raw = _notice(meta).get("recipients")
    if not isinstance(raw, dict):
        return {}
    return {str(key): value for key, value in raw.items() if isinstance(value, dict)}


def _pending(recipients: list[NotifyRecipient], meta: dict[str, Any]) -> list[NotifyRecipient]:
    sent = {
        key
        for key, row in _recipient_state(meta).items()
        if str(row.get("status") or "").strip().lower() == "sent"
    }
    return [item for item in recipients if item.key not in sent]


def _display_name(comm: CrmCommunication, contact: CrmContact | None) -> str:
    if contact is not None:
        name = (contact.display_name or "").strip()
        if name:
            return name
    meta = _meta(comm)
    text = str(meta.get("contact_name") or comm.sender_identity or "").strip()
    return text


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


def _crm_link(comm: CrmCommunication) -> str:
    settings = get_settings()
    public = (settings.app_public_url or "").strip().rstrip("/")
    if not public:
        origins = settings.cors_origins or ["http://localhost:3000"]
        public = str(origins[0]).rstrip("/")
    if comm.contact_id is not None:
        return f"{public}/workspaces/crm/contacts/{comm.contact_id}"
    return f"{public}/workspaces/crm/communication"


def _build_message(
    comm: CrmCommunication,
    *,
    recipient: str,
    name: str,
    project: str,
) -> GatewayMessage:
    preview = _preview_text(comm)
    when = ""
    moment = comm.occurred_at or comm.created_at
    if moment is not None:
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=UTC)
        when = moment.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")
    link = _crm_link(comm)
    lines = ["Investhome CRM", "", "Platform: WhatsApp", "Tür: Mesaj"]
    if name:
        lines.append(f"Gönderen: {name}")
    if preview:
        lines.append(f"Önizleme: {preview}")
    if project:
        lines.append(f"İlgili proje: {project}")
    if when:
        lines.append(f"Tarih: {when}")
    lines.extend(["", "Kaydı aç:", link])
    rows = [("Platform", "WhatsApp"), ("Tür", "Mesaj")]
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
    html_body = (
        "<!DOCTYPE html><html lang=\"tr\">"
        "<body style=\"font-family:Arial,sans-serif;color:#1A1A1A;\">"
        "<p>Investhome CRM</p>"
        f"<table role=\"presentation\" cellpadding=\"0\" cellspacing=\"0\">{rendered}</table>"
        "<p style=\"margin-top:20px;\">"
        f"<a href=\"{href}\" style=\"background:#C4A15A;color:#ffffff;padding:12px 18px;"
        "text-decoration:none;border-radius:4px;display:inline-block;\">Kaydı aç</a></p>"
        "</body></html>"
    )
    return GatewayMessage(
        channel=NotificationChannel.EMAIL,
        recipient=recipient,
        subject="Yeni WhatsApp Mesajı",
        body="\n".join(lines),
        html_body=html_body,
        locale="tr",
        metadata={"purpose": "wazzup_inbound_crm"},
    )


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
        "wazzup_inbound_email_skipped communication_id=%s reason=%s",
        communication_id,
        reason,
    )
    return "skipped"


def deliver_wazzup_inbound_email(
    communication_id: UUID,
    *,
    db: Session | None = None,
    lock: NotifyLock | None = None,
) -> str:
    """Send at most one email per recipient. Raise to retry. Do not delete the row."""
    owns_session = db is None
    session = db or db_session.SessionLocal()
    active_lock = lock or _notify_lock()
    lock_key = f"{LOCK_PREFIX}{communication_id}"
    claimed = False
    try:
        if not get_settings().wazzup_inbound_email_notifications_enabled:
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
                "wazzup_inbound_email_send_failed communication_id=%s reason=lock",
                communication_id,
            )
            raise WazzupInboundEmailRetry("notify lock unavailable") from exc
        if not claimed:
            return _skip(communication_id, "locked")
        session.refresh(comm)
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
                    "wazzup_inbound_email_send_failed communication_id=%s reason=gateway",
                    communication_id,
                )
                continue
            if not result.ok:
                failures += 1
                logger.warning(
                    "wazzup_inbound_email_send_failed communication_id=%s reason=%s",
                    communication_id,
                    result.status,
                )
                continue
            try:
                _record_recipient_sent(session, comm, recipient, expected)
            except Exception as exc:
                logger.warning(
                    "wazzup_inbound_email_send_failed communication_id=%s reason=status_commit",
                    communication_id,
                )
                raise WazzupInboundEmailRetry("notification status commit failed") from exc
            logger.info(
                "wazzup_inbound_email_sent communication_id=%s recipient_source=%s",
                communication_id,
                recipient.source,
            )
        if failures:
            raise WazzupInboundEmailRetry("smtp gateway returned failure")
        claimed = False
        return "sent"
    finally:
        if claimed:
            try:
                active_lock.release(lock_key)
            except Exception:
                logger.warning(
                    "wazzup_inbound_email_send_failed communication_id=%s reason=lock_release",
                    communication_id,
                )
        if owns_session:
            session.close()


async def wazzup_inbound_email_job(ctx: dict[str, Any], communication_id: str) -> dict[str, str]:
    del ctx
    status = deliver_wazzup_inbound_email(UUID(str(communication_id)))
    return {"status": status}


__all__ = [
    "JOB_WAZZUP_INBOUND_EMAIL",
    "MemoryNotifyLock",
    "WazzupInboundEmailRetry",
    "deliver_wazzup_inbound_email",
    "enqueue_wazzup_inbound_email_notifications",
    "wazzup_inbound_email_job",
]
