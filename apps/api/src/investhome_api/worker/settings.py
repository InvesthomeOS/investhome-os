"""ARQ worker configuration."""

from __future__ import annotations

from arq.connections import RedisSettings

from investhome_api.services.document_intelligence.queue import JOB_NAME, process_document_job
from investhome_api.services.drawing_intelligence.queue import (
    JOB_NAME as DRAWING_JOB_NAME,
    get_drawing_worker_timeout,
    process_drawing_job,
)

redis_settings = RedisSettings(host="localhost")


class WorkerSettings:
    redis_settings = redis_settings
    functions = [process_document_job, process_drawing_job]
    job_timeout = 600
    max_tries = 3
    retry_jobs = True

    @staticmethod
    async def on_startup(ctx: dict) -> None:  # noqa: ANN401
        ctx["started"] = True

    job_name_map = {
        JOB_NAME: process_document_job,
        DRAWING_JOB_NAME: process_drawing_job,
    }
    drawing_job_timeout = get_drawing_worker_timeout()
