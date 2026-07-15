"""Queue abstraction for document processing jobs."""

from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from collections.abc import Callable
from typing import Any

from investhome_api.config.settings import get_settings

logger = logging.getLogger(__name__)

JOB_NAME = "process_document_job"


def _run_sync(document_id: uuid.UUID, *, force: bool = False) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.services.document_intelligence.pipeline import process_document

    db = SessionLocal()
    try:
        process_document(db, document_id, force=force)
    finally:
        db.close()


def enqueue_document_processing(document_id: uuid.UUID, *, force: bool = False) -> None:
    """Enqueue async processing or run synchronously when sync mode is enabled."""
    settings = get_settings()
    if settings.document_processing_sync:
        _run_sync(document_id, force=force)
        return

    try:
        asyncio.get_running_loop().create_task(_enqueue_arq(document_id, force=force))
    except RuntimeError:
        thread = threading.Thread(
            target=lambda: asyncio.run(_enqueue_arq(document_id, force=force)),
            daemon=True,
        )
        thread.start()


async def _enqueue_arq(document_id: uuid.UUID, *, force: bool = False) -> None:
    settings = get_settings()
    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        redis = RedisSettings.from_dsn(settings.redis_url)
        pool = await create_pool(redis)
        await pool.enqueue_job(JOB_NAME, str(document_id), force)
        await pool.close()
    except Exception:
        logger.warning("ARQ enqueue failed; falling back to sync thread", exc_info=True)
        thread = threading.Thread(
            target=_run_sync,
            args=(document_id,),
            kwargs={"force": force},
            daemon=True,
        )
        thread.start()


async def process_document_job(ctx: dict[str, Any], document_id: str, force: bool = False) -> None:
    """ARQ worker entrypoint."""
    _run_sync(uuid.UUID(document_id), force=force)


def get_worker_settings() -> Any:
    from arq.connections import RedisSettings

    settings = get_settings()
    from investhome_api.worker.settings import WorkerSettings

    WorkerSettings.redis_settings = RedisSettings.from_dsn(settings.redis_url)
    return WorkerSettings
