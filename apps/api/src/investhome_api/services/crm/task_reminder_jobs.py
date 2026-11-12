"""Dispatch due CRM task reminders through the existing notification and email gateway."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.db import session as db_session
from investhome_api.models.crm_activity import (
    CrmActivity,
    CrmActivityEntityType,
    CrmActivityReminder,
    CrmActivityStatus,
    CrmActivityType,
    CrmReminderChannel,
    CrmTaskStatus,
)
from investhome_api.models.notification import NotificationPriority, NotificationSource, NotificationType
from investhome_api.services.user_invitation import _frontend_base_url
from investhome_api.services.user_notifications import DispatchRequest, dispatch_user_event

_IN_APP_CHANNELS = frozenset({CrmReminderChannel.IN_APP, CrmReminderChannel.NOTIFICATION})
_EMAIL_CHANNELS = frozenset({CrmReminderChannel.EMAIL})
_IN_APP_DONE = frozenset({"sent", "duplicate", "disabled"})
_EMAIL_DONE = frozenset({"sent", "duplicate", "disabled", "missing"})
_MEETING_TYPES = frozenset(
    {
        CrmActivityType.MEETING,
        CrmActivityType.ZOOM_MEETING,
        CrmActivityType.TEAMS_MEETING,
        CrmActivityType.INVESTOR_MEETING,
        CrmActivityType.CONSTRUCTION_MEETING,
    }
)
_OVERDUE_GRACE = timedelta(minutes=15)
_MEETING_LOOKAHEAD = timedelta(minutes=15)
_MEETING_LOOKBACK = timedelta(minutes=5)

JOB_CRM_TASK_DUE_REMINDERS = "crm_task_due_reminders"

_CLOSED_TASK = {CrmTaskStatus.COMPLETED, CrmTaskStatus.CANCELLED, CrmTaskStatus.DEFERRED}
_CLOSED_STATUS = {CrmActivityStatus.COMPLETED, CrmActivityStatus.CANCELLED, CrmActivityStatus.ARCHIVED}


def _task_is_active(activity: CrmActivity) -> bool:
    if activity.archived_at is not None:
        return False
    if activity.task_status in _CLOSED_TASK or activity.status in _CLOSED_STATUS:
        return False
    return True


def _task_links(activity: CrmActivity) -> dict:
    meta = activity.metadata_json if isinstance(activity.metadata_json, dict) else {}
    links = meta.get("task_links") if isinstance(meta.get("task_links"), dict) else {}
    return links


def _lead_id_from_activity(activity: CrmActivity) -> str | None:
    links = _task_links(activity)
    meta = activity.metadata_json if isinstance(activity.metadata_json, dict) else {}
    raw = links.get("lead_id") or meta.get("lead_id")
    return str(raw) if raw else None


def _contact_id_from_activity(activity: CrmActivity) -> str | None:
    if activity.entity_type == CrmActivityEntityType.CONTACT and activity.entity_id is not None:
        return str(activity.entity_id)
    raw = _task_links(activity).get("contact_id")
    return str(raw) if raw else None


def _task_url(activity: CrmActivity) -> str:
    query = [f"task={activity.id}"]
    contact_id = _contact_id_from_activity(activity)
    lead_id = _lead_id_from_activity(activity)
    if contact_id:
        query.append(f"contact={contact_id}")
    if lead_id:
        query.append(f"lead={lead_id}")
    return f"{_frontend_base_url()}/workspaces/crm/tasks?{'&'.join(query)}"


def _contact_name(session: Session, activity: CrmActivity) -> str | None:
    raw = _contact_id_from_activity(activity)
    if not raw:
        return None
    try:
        contact_id = UUID(raw)
    except ValueError:
        return None
    from investhome_api.models.crm_contact import CrmContact

    contact = session.get(CrmContact, contact_id)
    if contact is None:
        return None
    name = (contact.display_name or "").strip()
    return name or None


def _due_label(activity: CrmActivity) -> str:
    if activity.due_date is None:
        return "—"
    due = activity.due_date if activity.due_date.tzinfo is not None else activity.due_date.replace(tzinfo=UTC)
    try:
        zone = ZoneInfo((activity.timezone or "").strip() or "Europe/Istanbul")
    except Exception:
        zone = ZoneInfo("Europe/Istanbul")
    return due.astimezone(zone).strftime("%d.%m.%Y %H:%M")


def _mark_sent(reminder: CrmActivityReminder, now: datetime) -> None:
    reminder.is_sent = True
    reminder.sent_at = now


def _task_link_query(activity: CrmActivity) -> dict[str, str]:
    link_query = {"task": str(activity.id)}
    contact_id = _contact_id_from_activity(activity)
    lead_id = _lead_id_from_activity(activity)
    if contact_id:
        link_query["contact"] = contact_id
    if lead_id:
        link_query["lead"] = lead_id
    return link_query


def _reminder_rule(activity: CrmActivity, reminder: CrmActivityReminder, channel: str) -> str:
    instant = reminder.remind_at if reminder.remind_at.tzinfo is not None else reminder.remind_at.replace(tzinfo=UTC)
    stamp = int(instant.timestamp())
    return f"crm.task.due.{activity.id}.{stamp}.{channel}"


def _dispatch_in_app(
    session: Session,
    reminder: CrmActivityReminder,
    activity: CrmActivity,
    recipient_id: UUID,
    now: datetime,
) -> bool:
    contact = _contact_name(session, activity)
    link_query = _task_link_query(activity)
    outcome = dispatch_user_event(
        session,
        DispatchRequest(
            event_key="task_reminder",
            recipient_user_id=recipient_id,
            title_key="notifications.crm.task_due.title",
            message_key="notifications.crm.task_due.message",
            rule_key=_reminder_rule(activity, reminder, "in_app"),
            related_entity_type="crm_activity",
            related_entity_id=activity.id,
            link_module="crm/tasks",
            link_query=link_query,
            destination_path=f"/workspaces/crm/tasks?task={activity.id}",
            notification_type=NotificationType.REMINDER,
            priority=NotificationPriority.MEDIUM,
            source=NotificationSource.SCHEDULED_JOB,
            allow_email=False,
            metadata={
                "title": activity.title,
                "name": contact or activity.title,
                "activity_id": str(activity.id),
                "related_label": activity.title,
            },
        ),
    )
    if outcome["in_app"] not in _IN_APP_DONE:
        return False
    _mark_sent(reminder, now)
    return True


def _dispatch_email(
    session: Session,
    reminder: CrmActivityReminder,
    activity: CrmActivity,
    recipient_id: UUID,
    now: datetime,
) -> bool:
    due = _due_label(activity)
    url = _task_url(activity)
    contact = _contact_name(session, activity)
    lines = [f"Görev: {activity.title}", f"Son tarih: {due}"]
    if contact:
        lines.append(f"Kişi: {contact}")
    lines.extend(["", f"Görevi aç: {url}"])
    outcome = dispatch_user_event(
        session,
        DispatchRequest(
            event_key="task_reminder",
            recipient_user_id=recipient_id,
            title_key="notifications.crm.task_due.title",
            message_key="notifications.crm.task_due.message",
            rule_key=_reminder_rule(activity, reminder, "email"),
            related_entity_type="crm_activity",
            related_entity_id=activity.id,
            link_module="crm/tasks",
            link_query=_task_link_query(activity),
            destination_path=f"/workspaces/crm/tasks?task={activity.id}",
            email_subject=f"Görev Hatırlatması: {activity.title}",
            email_body="\n".join(lines) + "\n",
            notification_type=NotificationType.REMINDER,
            priority=NotificationPriority.MEDIUM,
            source=NotificationSource.SCHEDULED_JOB,
            allow_in_app=False,
            retry_email=True,
            metadata={"title": activity.title, "name": contact or activity.title},
        ),
    )
    if outcome["email"] not in _EMAIL_DONE:
        return False
    _mark_sent(reminder, now)
    return True


def _notify_overdue_tasks(session: Session, now: datetime) -> int:
    sent = 0
    cutoff = now - _OVERDUE_GRACE
    rows = session.scalars(
        select(CrmActivity).where(
            CrmActivity.activity_type == CrmActivityType.TASK,
            CrmActivity.archived_at.is_(None),
            CrmActivity.due_date.is_not(None),
            CrmActivity.due_date <= cutoff,
        )
    ).all()
    for activity in rows:
        if not _task_is_active(activity):
            continue
        recipient_id = activity.assigned_user_id or activity.owner_id
        if recipient_id is None:
            continue
        outcome = dispatch_user_event(
            session,
            DispatchRequest(
                event_key="task_overdue",
                recipient_user_id=recipient_id,
                title_key="notifications.crm.task_overdue.title",
                message_key="notifications.crm.task_overdue.message",
                rule_key=f"crm.task.overdue.{activity.id}",
                related_entity_type="crm_activity",
                related_entity_id=activity.id,
                link_module="crm/tasks",
                link_query=_task_link_query(activity),
                destination_path=f"/workspaces/crm/tasks?task={activity.id}",
                email_subject=f"Görev süresi geçti: {activity.title}",
                email_body=f"Görev süresi geçti: {activity.title}\nSon tarih: {_due_label(activity)}\n",
                notification_type=NotificationType.WARNING,
                priority=NotificationPriority.HIGH,
                source=NotificationSource.SCHEDULED_JOB,
                metadata={"title": activity.title, "name": activity.title, "related_label": activity.title},
            ),
        )
        if outcome["in_app"] in _IN_APP_DONE or outcome["email"] in _EMAIL_DONE:
            sent += 1
    return sent


def _notify_upcoming_meetings(session: Session, now: datetime) -> int:
    sent = 0
    rows = session.scalars(
        select(CrmActivity).where(
            CrmActivity.activity_type.in_(tuple(_MEETING_TYPES)),
            CrmActivity.archived_at.is_(None),
            CrmActivity.start_date.is_not(None),
            CrmActivity.start_date <= now + _MEETING_LOOKAHEAD,
            CrmActivity.start_date >= now - _MEETING_LOOKBACK,
        )
    ).all()
    for activity in rows:
        if activity.status in _CLOSED_STATUS:
            continue
        recipient_id = activity.assigned_user_id or activity.owner_id
        if recipient_id is None:
            continue
        outcome = dispatch_user_event(
            session,
            DispatchRequest(
                event_key="meeting_reminder",
                recipient_user_id=recipient_id,
                title_key="notifications.crm.meeting_soon.title",
                message_key="notifications.crm.meeting_soon.message",
                rule_key=f"crm.meeting.soon.{activity.id}",
                related_entity_type="crm_activity",
                related_entity_id=activity.id,
                link_module="crm/communication/meetings",
                link_query={"activity": str(activity.id)},
                destination_path=f"/workspaces/crm/communication/meetings?activity={activity.id}",
                email_subject=f"Toplantı hatırlatması: {activity.title}",
                email_body=f"15 dakika sonra toplantınız var: {activity.title}\n",
                notification_type=NotificationType.REMINDER,
                priority=NotificationPriority.HIGH,
                source=NotificationSource.SCHEDULED_JOB,
                metadata={"title": activity.title, "name": activity.title, "minutes": "15", "related_label": activity.title},
            ),
        )
        if outcome["in_app"] in _IN_APP_DONE or outcome["email"] in _EMAIL_DONE:
            sent += 1
    return sent


def run_crm_task_due_reminders(*, clock: datetime | None = None, db: Session | None = None) -> dict[str, int]:
    now = clock or datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    sent = 0
    skipped = 0
    overdue = 0
    meetings = 0

    def _dispatch(session: Session) -> None:
        nonlocal sent, skipped, overdue, meetings
        rows = session.execute(
            select(CrmActivityReminder, CrmActivity)
            .join(CrmActivity, CrmActivity.id == CrmActivityReminder.activity_id)
            .where(
                CrmActivityReminder.is_sent.is_(False),
                CrmActivityReminder.channel.in_(tuple(_IN_APP_CHANNELS | _EMAIL_CHANNELS)),
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
            channel = reminder.channel
            if not isinstance(channel, CrmReminderChannel):
                try:
                    channel = CrmReminderChannel(str(channel))
                except ValueError:
                    skipped += 1
                    continue
            if channel in _IN_APP_CHANNELS:
                delivered = _dispatch_in_app(session, reminder, activity, recipient_id, now)
            elif channel in _EMAIL_CHANNELS:
                delivered = _dispatch_email(session, reminder, activity, recipient_id, now)
            else:
                skipped += 1
                continue
            if delivered:
                sent += 1
            else:
                skipped += 1
        overdue = _notify_overdue_tasks(session, now)
        meetings = _notify_upcoming_meetings(session, now)
        session.flush()

    if db is not None:
        _dispatch(db)
        return {
            "reminders_sent": sent,
            "reminders_skipped": skipped,
            "overdue_sent": overdue,
            "meetings_sent": meetings,
        }

    with db_session.SessionLocal() as session:
        _dispatch(session)
        session.commit()
    return {
        "reminders_sent": sent,
        "reminders_skipped": skipped,
        "overdue_sent": overdue,
        "meetings_sent": meetings,
    }


async def crm_task_due_reminders_job(ctx: dict) -> dict[str, int]:
    del ctx
    return run_crm_task_due_reminders()
