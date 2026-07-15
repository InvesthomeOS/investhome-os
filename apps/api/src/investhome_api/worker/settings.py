"""ARQ worker configuration."""

from __future__ import annotations

from arq.connections import RedisSettings

from investhome_api.services.document_intelligence.queue import JOB_NAME, process_document_job

redis_settings = RedisSettings(host="localhost")


class WorkerSettings:
    redis_settings = redis_settings
    functions = [process_document_job]
    job_timeout = 600
    max_tries = 3
    retry_jobs = True

    @staticmethod
    async def on_startup(ctx: dict) -> None:  # noqa: ANN401
        ctx["started"] = True

    job_name_map = {JOB_NAME: process_document_job}
