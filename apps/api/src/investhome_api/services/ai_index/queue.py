"""Queue abstraction for AI Index jobs (ARQ + sync fallback)."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid
from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings

logger = logging.getLogger(__name__)

JOB_NAME = "process_ai_index_job"
JOB_NAME_PROJECT = "process_ai_index_project_job"

# Retry when ARQ races ahead of the Drive sync commit that created the asset.
_ASSET_MISSING_RETRIES = 4
_ASSET_MISSING_BASE_DELAY_SEC = 0.4

_PENDING_ASSETS_KEY = "ai_index_pending_assets"
_PENDING_PROJECTS_KEY = "ai_index_pending_projects"
_COMMIT_HOOK_KEY = "ai_index_after_commit_hook"


def _run_asset_sync(asset_id: uuid.UUID, *, force: bool = False) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_studio_media import CreativeStudioMediaAsset
    from investhome_api.services.ai_index.pipeline import index_asset

    for attempt in range(_ASSET_MISSING_RETRIES):
        db = SessionLocal()
        try:
            asset = db.get(CreativeStudioMediaAsset, asset_id)
            if asset is None:
                if attempt + 1 < _ASSET_MISSING_RETRIES:
                    delay = _ASSET_MISSING_BASE_DELAY_SEC * (attempt + 1)
                else:
                    logger.warning("ai_index_asset_missing", extra={"asset_id": str(asset_id)})
                    return
            else:
                index_asset(db, asset_id, force=force)
                db.commit()
                return
        except Exception:
            db.rollback()
            logger.warning("ai_index_job_failed", extra={"asset_id": str(asset_id)}, exc_info=True)
            raise
        finally:
            db.close()
        time.sleep(delay)


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


def _ensure_after_commit_hook(db: Session) -> None:
    """Register after_commit / after_rollback handlers once per session lifetime."""
    if db.info.get(_COMMIT_HOOK_KEY):
        return

    def _on_commit(session: Session) -> None:
        assets = dict(session.info.pop(_PENDING_ASSETS_KEY, {}))
        projects = dict(session.info.pop(_PENDING_PROJECTS_KEY, {}))
        for asset_id, force in assets.items():
            _dispatch_asset_enqueue(asset_id, force=force)
        for project_id, force in projects.items():
            _dispatch_project_enqueue(project_id, force=force)

    def _on_rollback(session: Session) -> None:
        session.info.pop(_PENDING_ASSETS_KEY, None)
        session.info.pop(_PENDING_PROJECTS_KEY, None)

    # Keep listeners for the session lifetime — do not remove inside callbacks
    # (SQLAlchemy iterates a deque; mutating it during after_commit raises).
    event.listen(db, "after_commit", _on_commit)
    event.listen(db, "after_rollback", _on_rollback)
    db.info[_COMMIT_HOOK_KEY] = True


def _schedule_asset_after_commit(db: Session, asset_id: uuid.UUID, *, force: bool) -> None:
    pending: dict[uuid.UUID, bool] = db.info.setdefault(_PENDING_ASSETS_KEY, {})
    pending[asset_id] = bool(pending.get(asset_id)) or force
    _ensure_after_commit_hook(db)


def _schedule_project_after_commit(db: Session, project_id: uuid.UUID, *, force: bool) -> None:
    pending: dict[uuid.UUID, bool] = db.info.setdefault(_PENDING_PROJECTS_KEY, {})
    pending[project_id] = bool(pending.get(project_id)) or force
    _ensure_after_commit_hook(db)


def _dispatch_asset_enqueue(asset_id: uuid.UUID, *, force: bool = False) -> None:
    """Actually enqueue / run (caller must ensure DB row is visible)."""
    try:
        asyncio.get_running_loop().create_task(_enqueue_asset_arq(asset_id, force=force))
    except RuntimeError:
        thread = threading.Thread(
            target=lambda: asyncio.run(_enqueue_asset_arq(asset_id, force=force)),
            daemon=True,
        )
        thread.start()


def _dispatch_project_enqueue(project_id: uuid.UUID, *, force: bool = False) -> None:
    try:
        asyncio.get_running_loop().create_task(_enqueue_project_arq(project_id, force=force))
    except RuntimeError:
        thread = threading.Thread(
            target=lambda: asyncio.run(_enqueue_project_arq(project_id, force=force)),
            daemon=True,
        )
        thread.start()


def enqueue_asset_ai_index(
    asset_id: uuid.UUID,
    *,
    force: bool = False,
    db: Session | None = None,
) -> None:
    """Enqueue AI indexing for one media asset (or run sync when enabled).

    When ``db`` is provided in async mode, the ARQ job is deferred until that
    session commits so workers never race an uncommitted Drive sync insert.
    """
    settings = get_settings()
    if settings.ai_index_processing_sync:
        _run_asset_sync(asset_id, force=force)
        return

    if db is not None:
        _schedule_asset_after_commit(db, asset_id, force=force)
        return

    _dispatch_asset_enqueue(asset_id, force=force)


def enqueue_project_ai_index(
    project_id: uuid.UUID,
    *,
    force: bool = False,
    db: Session | None = None,
) -> None:
    settings = get_settings()
    if settings.ai_index_processing_sync:
        _run_project_sync(project_id, force=force)
        return

    if db is not None:
        _schedule_project_after_commit(db, project_id, force=force)
        return

    _dispatch_project_enqueue(project_id, force=force)


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
