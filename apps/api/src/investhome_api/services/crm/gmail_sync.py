"""Pilot Gmail sync: 30-day Inbox+Sent backfill, then incremental history."""

from __future__ import annotations

import base64
import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.crm_communication import (
    CrmUserCommunicationAccount,
    CrmUserCommunicationAccountHealth,
    CrmUserCommunicationAccountStatus,
)
from investhome_api.models.user_auth import User
from investhome_api.services.crm.gmail_client import GmailApiError, GmailMailbox, GoogleGmailMailbox
from investhome_api.services.crm.gmail_oauth import mark_needs_reauth
from investhome_api.services.crm.gmail_parse import parse_gmail_message, parsed_to_ingest_payload
from investhome_api.services.crm.live_ingest import ingest_live_message

logger = logging.getLogger(__name__)


def _backfill_queries(days: int) -> list[str]:
    start = datetime.now(UTC) - timedelta(days=max(1, days))
    after = start.strftime("%Y/%m/%d")
    return [
        f"in:inbox -in:spam -in:trash after:{after}",
        f"in:sent -in:spam -in:trash after:{after}",
    ]


def _attachment_payloads(mailbox: GmailMailbox, parsed, *, max_bytes: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for part in parsed.attachments:
        content = part.inline_data
        if content is None and part.attachment_id:
            content = mailbox.get_attachment(parsed.gmail_id, part.attachment_id)
        if not content:
            continue
        if len(content) > max_bytes:
            logger.warning("gmail_attachment_skipped_too_large message=%s", parsed.gmail_id)
            continue
        items.append(
            {
                "file_name": part.file_name,
                "mime_type": part.mime_type,
                "file_size": len(content),
                "content_base64": base64.b64encode(content).decode("ascii"),
            }
        )
    return items


def _ingest_ids(
    db: Session,
    account: CrmUserCommunicationAccount,
    mailbox: GmailMailbox,
    message_ids: list[str],
    *,
    actor: User | None,
    max_bytes: int,
) -> dict[str, int]:
    ingested = 0
    skipped = 0
    duplicates = 0
    seen: set[str] = set()
    for message_id in message_ids:
        if not message_id or message_id in seen:
            continue
        seen.add(message_id)
        try:
            raw = mailbox.get_message(message_id)
            parsed = parse_gmail_message(raw, account_email=account.identity)
            if parsed.skip or not parsed.gmail_id:
                skipped += 1
                continue
            attachments = _attachment_payloads(mailbox, parsed, max_bytes=max_bytes)
            payload = parsed_to_ingest_payload(
                parsed,
                account_id=str(account.id),
                attachments=attachments,
            )
            _, created = ingest_live_message(db, payload, actor=actor)
            if created:
                ingested += 1
            else:
                duplicates += 1
        except GmailApiError:
            raise
        except Exception:
            logger.exception("gmail_message_ingest_failed id=%s", message_id)
            skipped += 1
    return {"ingested": ingested, "skipped": skipped, "duplicates": duplicates}


def sync_gmail_account(
    db: Session,
    account: CrmUserCommunicationAccount,
    *,
    mailbox: GmailMailbox | None = None,
    actor: User | None = None,
    force_backfill: bool = False,
) -> dict[str, Any]:
    if account.provider != "gmail" or account.archived_at is not None:
        raise ValueError("not_gmail_account")
    settings = get_settings()
    days = max(1, int(settings.gmail_backfill_days or 30))
    max_bytes = int(settings.document_max_upload_bytes or 52_428_800)
    box = mailbox or GoogleGmailMailbox(account)
    meta = dict(account.metadata_json or {})
    history_id = None if force_backfill else str(meta.get("gmail_history_id") or "").strip() or None
    totals = {"ingested": 0, "skipped": 0, "duplicates": 0, "mode": "incremental"}
    try:
        if history_id:
            try:
                ids, latest = box.list_history_message_ids(history_id)
                counts = _ingest_ids(db, account, box, ids, actor=actor, max_bytes=max_bytes)
                for key in ("ingested", "skipped", "duplicates"):
                    totals[key] += counts[key]
                if latest:
                    meta["gmail_history_id"] = latest
            except GmailApiError as exc:
                if exc.code != "history_expired":
                    raise
                history_id = None
                totals["mode"] = "backfill"
        if not history_id:
            totals["mode"] = "backfill"
            ids: list[str] = []
            for query in _backfill_queries(days):
                ids.extend(list(box.list_message_ids(query)))
            counts = _ingest_ids(db, account, box, ids, actor=actor, max_bytes=max_bytes)
            for key in ("ingested", "skipped", "duplicates"):
                totals[key] += counts[key]
            profile_history = box.get_profile_history_id()
            if profile_history:
                meta["gmail_history_id"] = profile_history
            meta["backfill_complete"] = True
            meta["backfill_days"] = days
        meta["sync_pending"] = False
        account.metadata_json = meta
        account.last_sync_at = datetime.now(UTC)
        account.last_error = None
        account.status = CrmUserCommunicationAccountStatus.CONNECTED.value
        account.health = CrmUserCommunicationAccountHealth.HEALTHY.value
        db.flush()
        logger.info(
            "gmail_sync_complete account=%s mode=%s ingested=%s duplicates=%s",
            account.id,
            totals["mode"],
            totals["ingested"],
            totals["duplicates"],
        )
        return {"account_id": str(account.id), "ok": True, **totals}
    except GmailApiError as exc:
        if exc.needs_reauth:
            mark_needs_reauth(account, error="Yeniden yetkilendirme gerekli")
        else:
            account.status = CrmUserCommunicationAccountStatus.ERROR.value
            account.health = CrmUserCommunicationAccountHealth.ERROR.value
            account.last_error = str(exc.code)[:500]
        logger.warning("gmail_sync_failed account=%s code=%s", account.id, exc.code)
        return {"account_id": str(account.id), "ok": False, "error": exc.code, **totals}
    except Exception:
        account.status = CrmUserCommunicationAccountStatus.ERROR.value
        account.health = CrmUserCommunicationAccountHealth.ERROR.value
        account.last_error = "Senkronizasyon hatası"
        logger.exception("gmail_sync_failed account=%s", account.id)
        return {"account_id": str(account.id), "ok": False, "error": "gmail_sync_failed", **totals}


def sync_connected_gmail_accounts(db: Session) -> dict[str, Any]:
    from investhome_api.services.crm.gmail_oauth import connected_gmail_accounts

    results = []
    for account in connected_gmail_accounts(db):
        if account.status == CrmUserCommunicationAccountStatus.NEEDS_REAUTH.value:
            continue
        actor = db.get(User, account.user_id)
        results.append(sync_gmail_account(db, account, actor=actor))
    return {"ok": True, "accounts": results}


def enqueue_gmail_sync(account_id: UUID, *, force_backfill: bool = False) -> None:
    settings = get_settings()
    if not settings.gmail_sync_enabled:
        return
    try:
        import asyncio

        from arq import create_pool

        from investhome_api.services.crm.gmail_jobs import JOB_GMAIL_ACCOUNT_SYNC
        from investhome_api.worker.redis_config import redis_settings_from_url

        async def _enqueue() -> None:
            pool = await create_pool(redis_settings_from_url(settings.redis_url))
            try:
                await pool.enqueue_job(JOB_GMAIL_ACCOUNT_SYNC, str(account_id), force_backfill)
            finally:
                closer = getattr(pool, "aclose", None) or getattr(pool, "close")
                await closer()

        try:
            asyncio.get_running_loop().create_task(_enqueue())
        except RuntimeError:
            asyncio.run(_enqueue())
    except Exception:
        logger.debug("gmail_sync_enqueue_failed", exc_info=True)
