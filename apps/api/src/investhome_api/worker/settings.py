"""ARQ worker configuration."""

from __future__ import annotations

from investhome_api.config.settings import get_settings
from investhome_api.core.logging_config import configure_logging, get_logger
from investhome_api.services.document_intelligence.queue import JOB_NAME, process_document_job
from investhome_api.services.drawing_intelligence.queue import (
    JOB_NAME as DRAWING_JOB_NAME,
    get_drawing_worker_timeout,
    process_drawing_job,
)
from investhome_api.worker.redis_config import redis_settings_from_url

configure_logging()
logger = get_logger("investhome.worker")

_settings = get_settings()
redis_settings = redis_settings_from_url(_settings.redis_url)


class WorkerSettings:
    redis_settings = redis_settings
    functions = [process_document_job, process_drawing_job]
    job_timeout = 600
    max_tries = 3
    retry_jobs = True

    @staticmethod
    async def on_startup(ctx: dict) -> None:  # noqa: ANN401
        ctx["started"] = True
        logger.info("Worker started redis=%s:%s", redis_settings.host, redis_settings.port)

    job_name_map = {
        JOB_NAME: process_document_job,
        DRAWING_JOB_NAME: process_drawing_job,
    }
    drawing_job_timeout = get_drawing_worker_timeout()
