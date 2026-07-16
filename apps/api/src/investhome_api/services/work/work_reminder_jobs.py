"""Background jobs for work item reminders."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from investhome_api.db import session as db_session
from investhome_api.models.sales import CLOSED_OPPORTUNITY_STAGES, SalesOpportunity
from investhome_api.models.work_item import ACTIVE_WORK_ITEM_STATUSES, WorkItem, WorkItemType
from investhome_api.services.work import work_item_service as svc
from investhome_api.services.work import work_notifications as notify


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


JOB_DUE_SOON = "work_due_soon"
JOB_OVERDUE = "work_overdue"
JOB_MEETING_APPROACHING = "work_meeting_approaching"
JOB_FOLLOW_UP_DUE = "work_follow_up_due"
JOB_NO_NEXT_ACTION = "work_no_next_action"
JOB_STALLED_OPPORTUNITY = "work_stalled_opportunity"

DUE_SOON_HOURS = 24
MEETING_APPROACHING_MINUTES = 60


def run_due_soon_reminders(*, clock: datetime | None = None) -> dict[str, int]:
    now = clock or datetime.now(UTC)
    window_end = now + timedelta(hours=DUE_SOON_HOURS)
    sent = 0
    with db_session.SessionLocal() as db:
        items = db.scalars(
            select(WorkItem).where(
                WorkItem.archived_at.is_(None),
                WorkItem.status.in_(list(ACTIVE_WORK_ITEM_STATUSES)),
                WorkItem.due_at.is_not(None),
                WorkItem.due_at > now,
                WorkItem.due_at <= window_end,
            )
        ).all()
        for item in items:
            notify.notify_due_soon(db, item)
            sent += 1
        db.commit()
    return {"reminders_sent": sent}


def run_overdue_reminders(*, clock: datetime | None = None) -> dict[str, int]:
    now = clock or datetime.now(UTC)
    sent = 0
    with db_session.SessionLocal() as db:
        items = db.scalars(
            select(WorkItem).where(
                WorkItem.archived_at.is_(None),
                WorkItem.status.in_(list(ACTIVE_WORK_ITEM_STATUSES)),
                WorkItem.due_at.is_not(None),
                WorkItem.due_at < now,
            )
        ).all()
        for item in items:
            notify.notify_overdue(db, item)
            sent += 1
        db.commit()
    return {"overdue_notified": sent}


def run_meeting_approaching(*, clock: datetime | None = None) -> dict[str, int]:
    now = clock or datetime.now(UTC)
    window_end = now + timedelta(minutes=MEETING_APPROACHING_MINUTES)
    sent = 0
    with db_session.SessionLocal() as db:
        items = db.scalars(
            select(WorkItem).where(
                WorkItem.archived_at.is_(None),
                WorkItem.work_item_type == WorkItemType.MEETING,
                WorkItem.status.in_(list(ACTIVE_WORK_ITEM_STATUSES)),
                WorkItem.start_at.is_not(None),
                WorkItem.start_at > now,
                WorkItem.start_at <= window_end,
            )
        ).all()
        for item in items:
            notify.notify_meeting_approaching(db, item)
            sent += 1
        db.commit()
    return {"meeting_reminders_sent": sent}


def run_follow_up_due(*, clock: datetime | None = None) -> dict[str, int]:
    now = clock or datetime.now(UTC)
    sent = 0
    with db_session.SessionLocal() as db:
        items = db.scalars(
            select(WorkItem).where(
                WorkItem.archived_at.is_(None),
                WorkItem.work_item_type.in_(
                    [
                        WorkItemType.FOLLOW_UP,
                        WorkItemType.PROPOSAL_FOLLOW_UP,
                        WorkItemType.RESERVATION_FOLLOW_UP,
                        WorkItemType.DEPOSIT_FOLLOW_UP,
                    ]
                ),
                WorkItem.status.in_(list(ACTIVE_WORK_ITEM_STATUSES)),
                WorkItem.due_at.is_not(None),
                WorkItem.due_at <= now,
            )
        ).all()
        for item in items:
            notify.notify_follow_up_due(db, item)
            sent += 1
        db.commit()
    return {"follow_up_reminders_sent": sent}


def run_no_next_action_check(*, clock: datetime | None = None) -> dict[str, int]:
    with db_session.SessionLocal() as db:
        company_tz = svc._company_timezone(db)
        today = datetime.now(company_tz).date()
        sent = 0
        opportunities = db.scalars(
            select(SalesOpportunity).where(
                SalesOpportunity.archived_at.is_(None),
                ~SalesOpportunity.stage.in_(list(CLOSED_OPPORTUNITY_STAGES)),
                or_(
                    SalesOpportunity.next_action.is_(None),
                    SalesOpportunity.next_action_date.is_(None),
                    SalesOpportunity.next_action_date < today,
                ),
            )
        ).all()
        for opp in opportunities:
            notify.notify_no_next_action_opportunity(db, opp.id, opp.opportunity_code)
            sent += 1
        db.commit()
    return {"no_next_action_notified": sent}


def run_stalled_opportunity_check(*, clock: datetime | None = None) -> dict[str, int]:
    now = clock or datetime.now(UTC)
    stale_before = now - timedelta(days=14)
    sent = 0
    with db_session.SessionLocal() as db:
        opportunities = db.scalars(
            select(SalesOpportunity).where(
                SalesOpportunity.archived_at.is_(None),
                ~SalesOpportunity.stage.in_(list(CLOSED_OPPORTUNITY_STAGES)),
                or_(
                    SalesOpportunity.last_contact_at.is_(None),
                    SalesOpportunity.last_contact_at < stale_before,
                ),
            )
        ).all()
        for opp in opportunities:
            notify.notify_no_next_action_opportunity(db, opp.id, opp.opportunity_code)
            sent += 1
        db.commit()
    return {"stalled_notified": sent}


async def due_soon_job(ctx: dict) -> dict[str, int]:
    return run_due_soon_reminders()


async def overdue_job(ctx: dict) -> dict[str, int]:
    return run_overdue_reminders()


async def meeting_approaching_job(ctx: dict) -> dict[str, int]:
    return run_meeting_approaching()


async def follow_up_due_job(ctx: dict) -> dict[str, int]:
    return run_follow_up_due()


async def no_next_action_job(ctx: dict) -> dict[str, int]:
    return run_no_next_action_check()


async def stalled_opportunity_job(ctx: dict) -> dict[str, int]:
    return run_stalled_opportunity_check()
