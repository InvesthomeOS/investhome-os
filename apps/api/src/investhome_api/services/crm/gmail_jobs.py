"""ARQ jobs for Gmail mailbox sync."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from investhome_api.config.settings import get_settings

logger = logging.getLogger(__name__)

JOB_GMAIL_BACKGROUND_SYNC = "gmail_background_sync"
JOB_GMAIL_ACCOUNT_SYNC = "gmail_account_sync"


async def gmail_background_sync_job(ctx: dict[str, Any]) -> dict[str, Any]:
    from investhome_api.db.session import SessionLocal
    from investhome_api.services.crm.gmail_sync import sync_connected_gmail_accounts

    settings = get_settings()
    if not settings.gmail_sync_enabled:
        return {"enabled": False, "skipped": True}
    db = SessionLocal()
    try:
        result = sync_connected_gmail_accounts(db)
        db.commit()
        return result
    except Exception:
        db.rollback()
        logger.exception("gmail_background_job_failed")
        raise
    finally:
        db.close()


async def gmail_account_sync_job(
    ctx: dict[str, Any],
    account_id: str,
    force_backfill: bool = False,
) -> dict[str, Any]:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.crm_communication import CrmUserCommunicationAccount
    from investhome_api.models.user_auth import User
    from investhome_api.services.crm.gmail_sync import sync_gmail_account

    db = SessionLocal()
    try:
        account = db.get(CrmUserCommunicationAccount, UUID(account_id))
        if account is None:
            return {"ok": False, "error": "not_found"}
        actor = db.get(User, account.user_id)
        result = sync_gmail_account(db, account, actor=actor, force_backfill=force_backfill)
        db.commit()
        return result
    except Exception:
        db.rollback()
        logger.exception("gmail_account_job_failed")
        raise
    finally:
        db.close()
