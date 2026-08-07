"""Queue abstraction for AI Index jobs (ARQ + sync fallback)."""

from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from typing import Any

from investhome_api.config.settings import get_settings

logger = logging.getLogger(__name__)

JOB_NAME = "process_ai_index_job"
JOB_NAME_PROJECT = "process_ai_index_project_job"


def _run_asset_sync(asset_id: uuid.UUID, *, force: bool = False) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.services.ai_index.pipeline import index_asset

    db = SessionLocal()
    try:
        index_asset(db, asset_id, force=force)
        db.commit()
    except Exception:
        db.rollback()
        logger.warning("ai_index_job_failed", extra={"asset_id": str(asset_id)}, exc_info=True)
        raise
    finally:
        db.close()


def _run_project_sync(project_id: uuid.UUID, *, force: bool = False) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.services.ai_index.pipeline import reindex_project
    from investhome_api.services.google_drive.provider import get_google_drive_provider

    db = SessionLocal()
    try:
        try:
            provider = get_google_drive_provider()
        except Exception:
            provider = None
        reindex_project(db, project_id, provider=provider, force=force)
        db.commit()
    except Exception:
        db.rollback()
        logger.warning("ai_index_project_job_failed", extra={"project_id": str(project_id)}, exc_info=True)
        raise
    finally:
        db.close()


def enqueue_asset_ai_index(asset_id: uuid.UUID, *, force: bool = False) -> None:
    """Enqueue AI indexing for one media asset (or run sync when enabled)."""
    settings = get_settings()
    if settings.ai_index_processing_sync:
        _run_asset_sync(asset_id, force=force)
        return

    try:
        asyncio.get_running_loop().create_task(_enqueue_asset_arq(asset_id, force=force))
    except RuntimeError:
        thread = threading.Thread(
            target=lambda: asyncio.run(_enqueue_asset_arq(asset_id, force=force)),
            daemon=True,
        )
        thread.start()


def enqueue_project_ai_index(project_id: uuid.UUID, *, force: bool = False) -> None:
    settings = get_settings()
    if settings.ai_index_processing_sync:
        _run_project_sync(project_id, force=force)
        return

    try:
        asyncio.get_running_loop().create_task(_enqueue_project_arq(project_id, force=force))
    except RuntimeError:
        thread = threading.Thread(
            target=lambda: asyncio.run(_enqueue_project_arq(project_id, force=force)),
            daemon=True,
        )
        thread.start()


async def _enqueue_asset_arq(asset_id: uuid.UUID, *, force: bool = False) -> None:
    settings = get_settings()
    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        redis = RedisSettings.from_dsn(settings.redis_url)
        pool = await create_pool(redis)
        await pool.enqueue_job(JOB_NAME, str(asset_id), force)
        await pool.close()
    except Exception:
        logger.warning("AI index ARQ enqueue failed; falling back to sync thread", exc_info=True)
        thread = threading.Thread(
            target=_run_asset_sync,
            args=(asset_id,),
            kwargs={"force": force},
            daemon=True,
        )
        thread.start()


async def _enqueue_project_arq(project_id: uuid.UUID, *, force: bool = False) -> None:
    settings = get_settings()
    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        redis = RedisSettings.from_dsn(settings.redis_url)
        pool = await create_pool(redis)
        await pool.enqueue_job(JOB_NAME_PROJECT, str(project_id), force)
        await pool.close()
    except Exception:
        logger.warning("AI index project ARQ enqueue failed; falling back to sync", exc_info=True)
        thread = threading.Thread(
            target=_run_project_sync,
            args=(project_id,),
            kwargs={"force": force},
            daemon=True,
        )
        thread.start()


async def process_ai_index_job(ctx: dict[str, Any], asset_id: str, force: bool = False) -> None:
    _run_asset_sync(uuid.UUID(asset_id), force=force)


async def process_ai_index_project_job(
    ctx: dict[str, Any], project_id: str, force: bool = False
) -> None:
    _run_project_sync(uuid.UUID(project_id), force=force)
