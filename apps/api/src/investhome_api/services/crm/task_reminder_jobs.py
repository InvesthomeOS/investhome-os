"""Dispatch due CRM task reminders through the existing notification service."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.db import session as db_session
from investhome_api.models.crm_activity import (
    CrmActivity,
    CrmActivityReminder,
    CrmActivityStatus,
    CrmActivityType,
    CrmReminderChannel,
    CrmTaskStatus,
)
from investhome_api.models.notification import NotificationPriority, NotificationType
from investhome_api.services.notification_service import create_notification

JOB_CRM_TASK_DUE_REMINDERS = "crm_task_due_reminders"

_CLOSED_TASK = {CrmTaskStatus.COMPLETED, CrmTaskStatus.CANCELLED, CrmTaskStatus.DEFERRED}
_CLOSED_STATUS = {CrmActivityStatus.COMPLETED, CrmActivityStatus.CANCELLED, CrmActivityStatus.ARCHIVED}


def _task_is_active(activity: CrmActivity) -> bool:
    if activity.archived_at is not None:
        return False
    if activity.task_status in _CLOSED_TASK or activity.status in _CLOSED_STATUS:
        return False
    return True


def _lead_id_from_activity(activity: CrmActivity) -> str | None:
    meta = activity.metadata_json if isinstance(activity.metadata_json, dict) else {}
    links = meta.get("task_links") if isinstance(meta.get("task_links"), dict) else {}
    raw = links.get("lead_id") or meta.get("lead_id")
    return str(raw) if raw else None


def run_crm_task_due_reminders(*, clock: datetime | None = None, db: Session | None = None) -> dict[str, int]:
    now = clock or datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    sent = 0
    skipped = 0

    def _dispatch(session: Session) -> None:
        nonlocal sent, skipped
        rows = session.execute(
            select(CrmActivityReminder, CrmActivity)
            .join(CrmActivity, CrmActivity.id == CrmActivityReminder.activity_id)
            .where(
                CrmActivityReminder.is_sent.is_(False),
                CrmActivityReminder.channel == CrmReminderChannel.IN_APP,
                CrmActivityReminder.remind_at <= now,
                CrmActivity.archived_at.is_(None),
                CrmActivity.activity_type == CrmActivityType.TASK,
            )
        ).all()
        for reminder, activity in rows:
            if not _task_is_active(activity):
                skipped += 1
                continue
            recipient_id = activity.assigned_user_id or activity.owner_id
            if recipient_id is None:
                skipped += 1
                continue
            lead_id = _lead_id_from_activity(activity)
            related_id = activity.id
            related_type = "crm_activity"
            if lead_id:
                try:
                    related_id = UUID(lead_id)
                    related_type = "lead"
                except ValueError:
                    related_id = activity.id
                    related_type = "crm_activity"
            notification = create_notification(
                session,
                recipient_user_id=recipient_id,
                type=NotificationType.REMINDER,
                priority=NotificationPriority.MEDIUM,
                title_key="notifications.crm.task_due.title",
                message_key="notifications.crm.task_due.message",
                rule_key=f"crm.task.due.{activity.id}",
                related_entity_type=related_type,
                related_entity_id=related_id,
                metadata={
                    "title": activity.title,
                    "name": activity.title,
                    "activity_id": str(activity.id),
                    "lead_id": lead_id,
                    "source": (activity.metadata_json or {}).get("source")
                    if isinstance(activity.metadata_json, dict)
                    else None,
                    "link_module": "crm/leads" if lead_id else "crm/tasks",
                    "link_query": {"lead": lead_id} if lead_id else None,
                    "related_label": activity.title,
                },
            )
            if notification is None:
                continue
            reminder.is_sent = True
            reminder.sent_at = now
            sent += 1
        session.flush()

    if db is not None:
        _dispatch(db)
        return {"reminders_sent": sent, "reminders_skipped": skipped}

    with db_session.SessionLocal() as session:
        _dispatch(session)
        session.commit()
    return {"reminders_sent": sent, "reminders_skipped": skipped}


async def crm_task_due_reminders_job(ctx: dict) -> dict[str, int]:
    del ctx
    return run_crm_task_due_reminders()
