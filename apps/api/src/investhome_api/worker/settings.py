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
from investhome_api.services.inventory.assignment_jobs import (
    JOB_APPLY_SCHEDULED_ASSIGNMENTS,
    apply_scheduled_assignments_job,
)
from investhome_api.services.inventory.ownership_jobs import (
    JOB_APPLY_SCHEDULED_TRANSFERS,
    apply_scheduled_transfers_job,
)
from investhome_api.services.inventory.reservation_jobs import (
    JOB_EXPIRE_SOFT_HOLDS,
    JOB_OVERDUE_DEPOSITS,
    JOB_RESERVATION_REMINDERS,
    expire_soft_holds_job,
    overdue_deposits_job,
    reservation_reminders_job,
)
from investhome_api.worker.redis_config import redis_settings_from_url

configure_logging()
logger = get_logger("investhome.worker")

_settings = get_settings()
redis_settings = redis_settings_from_url(_settings.redis_url)


class WorkerSettings:
    redis_settings = redis_settings
    functions = [
        process_document_job,
        process_drawing_job,
        expire_soft_holds_job,
        reservation_reminders_job,
        overdue_deposits_job,
        apply_scheduled_transfers_job,
        apply_scheduled_assignments_job,
    ]
    cron_jobs = [
        {"name": JOB_EXPIRE_SOFT_HOLDS, "coroutine": expire_soft_holds_job, "minute": {0, 15, 30, 45}},
        {"name": JOB_RESERVATION_REMINDERS, "coroutine": reservation_reminders_job, "minute": {5, 35}},
        {"name": JOB_OVERDUE_DEPOSITS, "coroutine": overdue_deposits_job, "minute": {10, 40}},
        {"name": JOB_APPLY_SCHEDULED_TRANSFERS, "coroutine": apply_scheduled_transfers_job, "minute": {0, 30}},
        {"name": JOB_APPLY_SCHEDULED_ASSIGNMENTS, "coroutine": apply_scheduled_assignments_job, "minute": {0, 30}},
    ]
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
        JOB_EXPIRE_SOFT_HOLDS: expire_soft_holds_job,
        JOB_RESERVATION_REMINDERS: reservation_reminders_job,
        JOB_OVERDUE_DEPOSITS: overdue_deposits_job,
        JOB_APPLY_SCHEDULED_TRANSFERS: apply_scheduled_transfers_job,
        JOB_APPLY_SCHEDULED_ASSIGNMENTS: apply_scheduled_assignments_job,
    }
    drawing_job_timeout = get_drawing_worker_timeout()
