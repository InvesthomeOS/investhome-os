"""ARQ background job for Google Drive incremental sync."""

from __future__ import annotations

import logging
from typing import Any

from investhome_api.config.settings import get_settings
from investhome_api.services.google_drive.provider import get_google_drive_provider
from investhome_api.services.google_drive.sync_service import DriveSyncOrchestrator

logger = logging.getLogger(__name__)

JOB_DRIVE_BACKGROUND_SYNC = "google_drive_background_sync"


async def google_drive_background_sync_job(ctx: dict[str, Any]) -> dict[str, Any]:
    """Recurring ARQ cron — incremental Changes API sync for enabled projects."""
    from investhome_api.db.session import SessionLocal

    settings = get_settings()
    if not settings.google_drive_sync_enabled:
        logger.info("drive_background_job_skipped_disabled")
        return {"enabled": False, "skipped": True}

    db = SessionLocal()
    try:
        provider = get_google_drive_provider(settings)
        orchestrator = DriveSyncOrchestrator(db, provider, settings=settings)
        result = orchestrator.run_background_sync()
        db.commit()
        return result.to_dict()
    except Exception:
        db.rollback()
        logger.exception("drive_background_job_failed")
        raise
    finally:
        db.close()
