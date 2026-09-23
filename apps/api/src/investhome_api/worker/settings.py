"""ARQ worker configuration."""

from __future__ import annotations

from arq import cron

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
from investhome_api.services.sales.proposal_jobs import (
    JOB_EXPIRE_PROPOSALS,
    JOB_PROPOSAL_EXPIRING_REMINDERS,
    expire_proposals_job,
    proposal_expiring_reminders_job,
)
from investhome_api.services.work.work_reminder_jobs import (
    JOB_DUE_SOON,
    JOB_FOLLOW_UP_DUE,
    JOB_MEETING_APPROACHING,
    JOB_NO_NEXT_ACTION,
    JOB_OVERDUE,
    JOB_STALLED_OPPORTUNITY,
    due_soon_job,
    follow_up_due_job,
    meeting_approaching_job,
    no_next_action_job,
    overdue_job,
    stalled_opportunity_job,
)
from investhome_api.services.analytics_warehouse.ingestion import (
    JOB_NAME_FULL_REFRESH,
    JOB_NAME_INCREMENTAL,
    warehouse_ingestion_full_refresh_job,
    warehouse_ingestion_incremental_job,
)
from investhome_api.services.google_drive.jobs import (
    JOB_DRIVE_BACKGROUND_SYNC,
    google_drive_background_sync_job,
)
from investhome_api.services.crm.gmail_jobs import (
    JOB_GMAIL_ACCOUNT_SYNC,
    JOB_GMAIL_BACKGROUND_SYNC,
    gmail_account_sync_job,
    gmail_background_sync_job,
)
from investhome_api.services.ai_index.queue import (
    JOB_NAME as AI_INDEX_JOB_NAME,
    JOB_NAME_PROJECT as AI_INDEX_PROJECT_JOB_NAME,
    process_ai_index_job,
    process_ai_index_project_job,
)
from investhome_api.worker.redis_config import redis_settings_from_url

configure_logging()
logger = get_logger("investhome.worker")

_settings = get_settings()
redis_settings = redis_settings_from_url(_settings.redis_url)


def _gmail_sync_cron_minutes() -> set[int]:
    interval = max(1, min(60, int(_settings.gmail_sync_interval_minutes or 5)))
    if interval >= 60:
        return {0}
    return set(range(0, 60, interval))


def _drive_sync_cron_minutes() -> set[int]:
    """Build ARQ cron minute set from GOOGLE_DRIVE_SYNC_INTERVAL_MINUTES (default 5)."""
    interval = max(1, min(60, int(_settings.google_drive_sync_interval_minutes or 5)))
    if interval >= 60:
        return {0}
    return set(range(0, 60, interval))


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
        due_soon_job,
        overdue_job,
        meeting_approaching_job,
        follow_up_due_job,
        no_next_action_job,
        stalled_opportunity_job,
        expire_proposals_job,
        proposal_expiring_reminders_job,
        warehouse_ingestion_incremental_job,
        warehouse_ingestion_full_refresh_job,
        google_drive_background_sync_job,
        gmail_background_sync_job,
        gmail_account_sync_job,
        process_ai_index_job,
        process_ai_index_project_job,
    ]
    cron_jobs = [
        cron(expire_soft_holds_job, name=JOB_EXPIRE_SOFT_HOLDS, minute={0, 15, 30, 45}),
        cron(reservation_reminders_job, name=JOB_RESERVATION_REMINDERS, minute={5, 35}),
        cron(overdue_deposits_job, name=JOB_OVERDUE_DEPOSITS, minute={10, 40}),
        cron(apply_scheduled_transfers_job, name=JOB_APPLY_SCHEDULED_TRANSFERS, minute={0, 30}),
        cron(apply_scheduled_assignments_job, name=JOB_APPLY_SCHEDULED_ASSIGNMENTS, minute={0, 30}),
        cron(due_soon_job, name=JOB_DUE_SOON, minute={20, 50}),
        cron(overdue_job, name=JOB_OVERDUE, minute={25, 55}),
        cron(
            meeting_approaching_job,
            name=JOB_MEETING_APPROACHING,
            minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55},
        ),
        cron(follow_up_due_job, name=JOB_FOLLOW_UP_DUE, minute={30}),
        cron(no_next_action_job, name=JOB_NO_NEXT_ACTION, hour={8}, minute={0}),
        cron(stalled_opportunity_job, name=JOB_STALLED_OPPORTUNITY, hour={9}, minute={0}),
        cron(expire_proposals_job, name=JOB_EXPIRE_PROPOSALS, minute={50}),
        cron(proposal_expiring_reminders_job, name=JOB_PROPOSAL_EXPIRING_REMINDERS, hour={8}, minute={30}),
        # G14 warehouse — off-peak incremental; isolates analytics load from OLTP hot paths
        cron(
            warehouse_ingestion_incremental_job,
            name=JOB_NAME_INCREMENTAL,
            hour={2, 8, 14, 20},
            minute={15},
        ),
        # Google Drive Changes API background sync (interval from settings, default 5 min)
        cron(
            google_drive_background_sync_job,
            name=JOB_DRIVE_BACKGROUND_SYNC,
            minute=_drive_sync_cron_minutes(),
        ),
        cron(
            gmail_background_sync_job,
            name=JOB_GMAIL_BACKGROUND_SYNC,
            minute=_gmail_sync_cron_minutes(),
        ),
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
        JOB_DUE_SOON: due_soon_job,
        JOB_OVERDUE: overdue_job,
        JOB_MEETING_APPROACHING: meeting_approaching_job,
        JOB_FOLLOW_UP_DUE: follow_up_due_job,
        JOB_NO_NEXT_ACTION: no_next_action_job,
        JOB_STALLED_OPPORTUNITY: stalled_opportunity_job,
        JOB_EXPIRE_PROPOSALS: expire_proposals_job,
        JOB_PROPOSAL_EXPIRING_REMINDERS: proposal_expiring_reminders_job,
        JOB_NAME_INCREMENTAL: warehouse_ingestion_incremental_job,
        JOB_NAME_FULL_REFRESH: warehouse_ingestion_full_refresh_job,
        JOB_DRIVE_BACKGROUND_SYNC: google_drive_background_sync_job,
        JOB_GMAIL_BACKGROUND_SYNC: gmail_background_sync_job,
        JOB_GMAIL_ACCOUNT_SYNC: gmail_account_sync_job,
        AI_INDEX_JOB_NAME: process_ai_index_job,
        AI_INDEX_PROJECT_JOB_NAME: process_ai_index_project_job,
    }
    drawing_job_timeout = get_drawing_worker_timeout()
