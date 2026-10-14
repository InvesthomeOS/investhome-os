"""Enqueue location refresh. Never calls Google from the web request."""

from __future__ import annotations

import asyncio
import logging
import threading
from uuid import UUID

from investhome_api.config.settings import get_settings

logger = logging.getLogger(__name__)

JOB_REFRESH_GEOCODE = "refresh_project_geocode_job"
JOB_REFRESH_PLACES = "refresh_project_nearby_places_job"
JOB_REFRESH_LOCATION = "refresh_project_location_intelligence_job"
LOCK_SECONDS = 60


def enqueue_location_refresh(project_id: UUID) -> str:
    """Return queued or already_queued. Redis or ARQ failure does not raise."""
    if not _acquire_lock(project_id):
        return "already_queued"
    try:
        asyncio.get_running_loop().create_task(_enqueue(project_id))
    except RuntimeError:
        thread = threading.Thread(target=lambda: asyncio.run(_enqueue(project_id)), daemon=True)
        thread.start()
    return "queued"


def _acquire_lock(project_id: UUID) -> bool:
    settings = get_settings()
    try:
        import redis

        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=0.3, socket_timeout=0.3)
        acquired = client.set(f"location-intel-lock:{project_id}", "1", nx=True, ex=LOCK_SECONDS)
        client.close()
        return bool(acquired)
    except Exception:
        logger.warning("location refresh lock unavailable project=%s", project_id)
        return True


async def _enqueue(project_id: UUID) -> None:
    settings = get_settings()
    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        await pool.enqueue_job(JOB_REFRESH_LOCATION, str(project_id), _job_id=f"location-intel:{project_id}")
        await pool.close()
    except Exception:
        logger.warning("location refresh enqueue failed project=%s", project_id, exc_info=True)
