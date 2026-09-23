"""CRM activity timeline, tasks, notes, and follow-up services."""

from __future__ import annotations

import hashlib
import math
import re
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo
from uuid import UUID

from sqlalchemy import String, and_, cast, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from investhome_api.models.activity import ActivityAction, ActivityEntityType, ActivityLog
from investhome_api.models.crm_activity import (
    CrmActivity,
    CrmActivityAttachment,
    CrmActivityCategory,
    CrmActivityChecklistItem,
    CrmActivityComment,
    CrmActivityEntityLink,
    CrmActivityEntityType,
    CrmActivityPriority,
    CrmActivityReminder,
    CrmActivitySavedFilter,
    CrmActivityStatus,
    CrmActivityType,
    CrmActivityVisibility,
    CrmFollowUpReason,
    CrmFollowUpRule,
    CrmTaskStatus,
)
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_activities import (
    CrmActivityBulkUpdateRequest,
    CrmActivityCreate,
    CrmActivityDashboardWidgets,
    CrmActivityDetail,
    CrmActivitySavedFilterCreate,
    CrmActivitySavedFilterResponse,
    CrmActivitySummary,
    CrmActivityUpdate,
    CrmCalendarEvent,
    CrmCalendarEventCreate,
    CrmCalendarResponse,
    CrmFollowUpCreate,
    CrmNoteCreate,
    CrmTaskCounters,
    CrmTaskCreate,
    CrmTimelineEntry,
)
from investhome_api.services.permission_service import user_has_permission

MEETING_TYPES = frozenset(
    {
        CrmActivityType.MEETING,
        CrmActivityType.ZOOM_MEETING,
        CrmActivityType.TEAMS_MEETING,
        CrmActivityType.INVESTOR_MEETING,
        CrmActivityType.CONSTRUCTION_MEETING,
        CrmActivityType.SITE_VISIT,
        CrmActivityType.PROPERTY_TOUR,
    }
)

TASK_TYPES = frozenset({CrmActivityType.TASK, CrmActivityType.REMINDER})
CALENDAR_ACTIVITY_TYPES = frozenset(
    {
        *MEETING_TYPES,
        *TASK_TYPES,
        CrmActivityType.FOLLOW_UP,
        CrmActivityType.PAYMENT,
        CrmActivityType.CLOSING,
        CrmActivityType.INSPECTION,
        CrmActivityType.CONTRACT_SIGNED,
        CrmActivityType.DOCUMENT_SENT,
        CrmActivityType.DOCUMENT_RECEIVED,
        CrmActivityType.PROPOSAL_SENT,
        CrmActivityType.PROPOSAL_RECEIVED,
        CrmActivityType.RESERVATION,
    }
)
CALENDAR_EVENT_LIMIT = 1500
NOTE_TYPES = frozenset({CrmActivityType.NOTE, CrmActivityType.INTERNAL_DISCUSSION})
NOTE_LIST_TYPES = frozenset({*NOTE_TYPES, CrmActivityType.COMMENT})
_NOTE_HTML_RE = re.compile(r"<[^>]+>")
_NOTE_GENERIC_TITLES = {
    "historical bitrix comment",
    "tarihsel bitrix yorumu",
    "comment",
    "yorum",
    "note",
    "not",
    "contact",
}
_NOTE_EMPTY_MARKERS = {
    "(bitrix yorum satırı — metin boş)",
    "(bitrix yorum satiri — metin bos)",
    "(bitrix yorum satırı - metin boş)",
}
FOLLOW_UP_TYPES = frozenset({CrmActivityType.FOLLOW_UP})
CONTACT_TOUCH_TYPES = frozenset(
    {
        CrmActivityType.PHONE_CALL,
        CrmActivityType.WHATSAPP,
        CrmActivityType.EMAIL,
        CrmActivityType.SMS,
        CrmActivityType.MEETING,
        CrmActivityType.ZOOM_MEETING,
        CrmActivityType.TEAMS_MEETING,
        CrmActivityType.NOTE,
        CrmActivityType.COMMENT,
        CrmActivityType.FOLLOW_UP,
    }
)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _touch_contact_last_activity(db: Session, activity: CrmActivity) -> None:
    if activity.entity_type != CrmActivityEntityType.CONTACT:
        return
    if activity.activity_type not in CONTACT_TOUCH_TYPES:
        return
    contact = db.get(CrmContact, activity.entity_id)
    if contact is None:
        return
    stamp = _as_utc(activity.start_date or datetime.now(tz=UTC))
    last = contact.last_contact_at
    if last is None or stamp >= _as_utc(last):
        contact.last_contact_at = stamp


def _can_view_private_notes(user: User) -> bool:
    return user_has_permission(user, "crm", "view_private_notes")


def _can_manage_tasks(user: User) -> bool:
    return user_has_permission(user, "crm", "manage_tasks") or user_has_permission(user, "crm", "update")


def _visibility_filter(user: User):
    if _can_view_private_notes(user):
        return None
    return or_(
        CrmActivity.visibility != CrmActivityVisibility.PRIVATE,
        CrmActivity.created_by == user.id,
        CrmActivity.owner_id == user.id,
        CrmActivity.assigned_user_id == user.id,
    )


def _default_category(activity_type: CrmActivityType) -> CrmActivityCategory:
    if activity_type in NOTE_TYPES:
        return CrmActivityCategory.NOTE
    if activity_type in TASK_TYPES:
        return CrmActivityCategory.TASK
    if activity_type in MEETING_TYPES:
        return CrmActivityCategory.MEETING
    if activity_type in FOLLOW_UP_TYPES:
        return CrmActivityCategory.FOLLOW_UP
    if activity_type in {
        CrmActivityType.PHONE_CALL,
        CrmActivityType.EMAIL,
        CrmActivityType.WHATSAPP,
        CrmActivityType.SMS,
    }:
        return CrmActivityCategory.COMMUNICATION
    if activity_type in {
        CrmActivityType.DOCUMENT_SENT,
        CrmActivityType.DOCUMENT_RECEIVED,
        CrmActivityType.PROPOSAL_SENT,
        CrmActivityType.PROPOSAL_RECEIVED,
    }:
        return CrmActivityCategory.DOCUMENT
    if activity_type in {CrmActivityType.SYSTEM_EVENT, CrmActivityType.AUTOMATION_EVENT}:
        return CrmActivityCategory.SYSTEM
    return CrmActivityCategory.OTHER


def _paginate(total: int, page: int, page_size: int) -> dict[str, int]:
    pages = max(1, math.ceil(total / page_size)) if total else 1
    return {"page": page, "page_size": page_size, "total": total, "pages": pages}


def _exclude_demo_clause():
    """Hide deterministically marked demo/seed rows without touching Bitrix data."""
    blob = func.lower(cast(CrmActivity.metadata_json, String))
    return or_(
        CrmActivity.metadata_json.is_(None),
        and_(
            ~blob.like('%"demo_seed": true%'),
            ~blob.like('%"demo_seed":true%'),
            ~blob.like('%"source": "integrated_demo_seed"%'),
            ~blob.like('%"source":"integrated_demo_seed"%'),
        ),
    )


def _serialize_summary(
    activity: CrmActivity,
    *,
    entity_name: str | None = None,
    assigned_user_name: str | None = None,
    owner_name: str | None = None,
    created_by_name: str | None = None,
    related_entity_name: str | None = None,
) -> CrmActivitySummary:
    return CrmActivitySummary(
        id=activity.id,
        entity_type=activity.entity_type,
        entity_id=activity.entity_id,
        related_entity_type=activity.related_entity_type,
        related_entity_id=activity.related_entity_id,
        activity_type=activity.activity_type,
        activity_category=activity.activity_category,
        title=activity.title,
        summary=activity.summary or (activity.description[:1000] if activity.description else None),
        status=activity.status,
        task_status=activity.task_status,
        priority=activity.priority,
        owner_id=activity.owner_id,
        assigned_user_id=activity.assigned_user_id,
        assigned_team_id=activity.assigned_team_id,
        start_date=activity.start_date,
        end_date=activity.end_date,
        due_date=activity.due_date,
        completed_at=activity.completed_at,
        reminder_date=activity.reminder_date,
        timezone=activity.timezone,
        location=activity.location,
        meeting_url=activity.meeting_url,
        tags=activity.tags,
        visibility=activity.visibility,
        is_pinned=activity.is_pinned,
        is_favorite=activity.is_favorite,
        follow_up_reason=activity.follow_up_reason,
        created_at=activity.created_at,
        updated_at=activity.updated_at,
        created_by=activity.created_by,
        archived_at=activity.archived_at,
        has_attachments=bool(activity.attachments),
        comment_count=len([c for c in activity.comments if c.deleted_at is None]),
        entity_name=entity_name,
        assigned_user_name=assigned_user_name,
        owner_name=owner_name,
        created_by_name=created_by_name,
        related_entity_name=related_entity_name,
    )


def _summaries_for_rows(db: Session, rows: list[CrmActivity]) -> list[CrmActivitySummary]:
    if not rows:
        return []
    contact_ids = {
        row.entity_id
        for row in rows
        if row.entity_type == CrmActivityEntityType.CONTACT
    }
    contact_ids.update(
        row.related_entity_id
        for row in rows
        if row.related_entity_type == CrmActivityEntityType.CONTACT and row.related_entity_id
    )
    user_ids = {
        user_id
        for row in rows
        for user_id in (row.assigned_user_id, row.owner_id, row.created_by)
        if user_id
    }
    project_ids = {
        row.related_entity_id
        for row in rows
        if row.related_entity_type == CrmActivityEntityType.PROJECT and row.related_entity_id
    }
    project_ids.update(
        row.entity_id for row in rows if row.entity_type == CrmActivityEntityType.PROJECT
    )
    contacts = (
        {
            contact.id: contact.display_name
            for contact in db.scalars(select(CrmContact).where(CrmContact.id.in_(contact_ids))).all()
        }
        if contact_ids
        else {}
    )
    users = (
        {
            user.id: user.full_name
            for user in db.scalars(select(User).where(User.id.in_(user_ids))).all()
        }
        if user_ids
        else {}
    )
    projects: dict = {}
    if project_ids:
        from investhome_api.models.project import Project

        projects = {
            project.id: project.name
            for project in db.scalars(select(Project).where(Project.id.in_(project_ids))).all()
        }

    summaries: list[CrmActivitySummary] = []
    for row in rows:
        entity_name = None
        if row.entity_type == CrmActivityEntityType.CONTACT:
            entity_name = contacts.get(row.entity_id)
        elif row.entity_type == CrmActivityEntityType.PROJECT:
            entity_name = projects.get(row.entity_id)
        related_name = None
        if row.related_entity_id:
            if row.related_entity_type == CrmActivityEntityType.PROJECT:
                related_name = projects.get(row.related_entity_id)
            elif row.related_entity_type == CrmActivityEntityType.CONTACT:
                related_name = contacts.get(row.related_entity_id)
        summaries.append(
            _serialize_summary(
                row,
                entity_name=entity_name,
                assigned_user_name=users.get(row.assigned_user_id) if row.assigned_user_id else None,
                owner_name=users.get(row.owner_id) if row.owner_id else None,
                created_by_name=users.get(row.created_by) if row.created_by else None,
                related_entity_name=related_name,
            )
        )
    return summaries


def _serialize_detail(activity: CrmActivity) -> CrmActivityDetail:
    summary = _serialize_summary(activity)
    return CrmActivityDetail(
        **summary.model_dump(),
        description=activity.description,
        outcome=activity.outcome,
        duration_minutes=activity.duration_minutes,
        estimated_duration_minutes=activity.estimated_duration_minutes,
        actual_duration_minutes=activity.actual_duration_minutes,
        recurrence_frequency=activity.recurrence_frequency,
        recurrence_rule=activity.recurrence_rule,
        metadata_json=activity.metadata_json,
        entity_links=[
            {
                "entity_type": link.entity_type,
                "entity_id": link.entity_id,
                "is_primary": link.is_primary,
            }
            for link in activity.entity_links
        ],
        checklist_items=activity.checklist_items,
        attachments=activity.attachments,
        reminders=activity.reminders,
        comments=[c for c in activity.comments if c.deleted_at is None],
    )


def get_activity_or_none(db: Session, activity_id: UUID) -> CrmActivity | None:
    return db.scalar(
        select(CrmActivity)
        .where(CrmActivity.id == activity_id)
        .options(
            selectinload(CrmActivity.entity_links),
            selectinload(CrmActivity.checklist_items),
            selectinload(CrmActivity.attachments),
            selectinload(CrmActivity.reminders),
            selectinload(CrmActivity.comments),
        )
    )


def _apply_activity_filters(
    query,
    *,
    search: str | None = None,
    entity_type: CrmActivityEntityType | None = None,
    entity_id: UUID | None = None,
    activity_type: CrmActivityType | None = None,
    activity_types: list[CrmActivityType] | None = None,
    activity_category: CrmActivityCategory | None = None,
    status: CrmActivityStatus | None = None,
    priority: CrmActivityPriority | None = None,
    owner_id: UUID | None = None,
    assigned_user_id: UUID | None = None,
    created_by: UUID | None = None,
    visibility: CrmActivityVisibility | None = None,
    tags: list[str] | None = None,
    has_attachments: bool | None = None,
    completed: bool | None = None,
    pending: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    include_archived: bool = False,
    task_status: CrmTaskStatus | None = None,
    responsible_user_id: UUID | None = None,
):
    if not include_archived:
        query = query.where(CrmActivity.archived_at.is_(None))
    query = query.where(_exclude_demo_clause())
    if entity_type is not None:
        query = query.where(CrmActivity.entity_type == entity_type)
    if entity_id is not None:
        query = query.where(CrmActivity.entity_id == entity_id)
    if activity_type is not None:
        query = query.where(CrmActivity.activity_type == activity_type)
    if activity_types:
        query = query.where(CrmActivity.activity_type.in_(activity_types))
    if activity_category is not None:
        query = query.where(CrmActivity.activity_category == activity_category)
    if status is not None:
        query = query.where(CrmActivity.status == status)
    if priority is not None:
        query = query.where(CrmActivity.priority == priority)
    if owner_id is not None:
        query = query.where(CrmActivity.owner_id == owner_id)
    if assigned_user_id is not None:
        query = query.where(CrmActivity.assigned_user_id == assigned_user_id)
    if created_by is not None:
        query = query.where(CrmActivity.created_by == created_by)
    if visibility is not None:
        query = query.where(CrmActivity.visibility == visibility)
    if tags:
        for tag in tags:
            query = query.where(CrmActivity.tags.contains([tag]))
    if has_attachments is True:
        query = query.where(CrmActivity.attachments.any())
    if completed is True:
        query = query.where(CrmActivity.status == CrmActivityStatus.COMPLETED)
    if pending is True:
        query = query.where(CrmActivity.status.not_in([CrmActivityStatus.COMPLETED, CrmActivityStatus.CANCELLED]))
    if task_status is not None:
        query = query.where(CrmActivity.task_status == task_status)
    if responsible_user_id is not None:
        query = query.where(
            or_(
                CrmActivity.assigned_user_id == responsible_user_id,
                CrmActivity.created_by == responsible_user_id,
                CrmActivity.owner_id == responsible_user_id,
            )
        )
    if date_from is not None:
        query = query.where(CrmActivity.created_at >= date_from)
    if date_to is not None:
        query = query.where(CrmActivity.created_at <= date_to)
    if search:
        pattern = f"%{search.strip()}%"
        contact_name_match = exists().where(
            CrmContact.id == CrmActivity.entity_id,
            CrmActivity.entity_type == CrmActivityEntityType.CONTACT,
            CrmContact.display_name.ilike(pattern),
        )
        query = query.where(
            or_(
                CrmActivity.title.ilike(pattern),
                CrmActivity.summary.ilike(pattern),
                CrmActivity.description.ilike(pattern),
                contact_name_match,
            )
        )
    return query


def list_activities(
    db: Session,
    user: User,
    *,
    search: str | None = None,
    entity_type: CrmActivityEntityType | None = None,
    entity_id: UUID | None = None,
    activity_type: CrmActivityType | None = None,
    activity_types: list[CrmActivityType] | None = None,
    activity_category: CrmActivityCategory | None = None,
    status: CrmActivityStatus | None = None,
    priority: CrmActivityPriority | None = None,
    owner_id: UUID | None = None,
    assigned_user_id: UUID | None = None,
    created_by: UUID | None = None,
    visibility: CrmActivityVisibility | None = None,
    tags: list[str] | None = None,
    has_attachments: bool | None = None,
    completed: bool | None = None,
    pending: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    include_archived: bool = False,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = 25,
    task_status: CrmTaskStatus | None = None,
    responsible_user_id: UUID | None = None,
) -> tuple[list[CrmActivitySummary], dict[str, int]]:
    query = select(CrmActivity).options(
        selectinload(CrmActivity.attachments),
        selectinload(CrmActivity.comments),
    )
    vis = _visibility_filter(user)
    if vis is not None:
        query = query.where(vis)
    query = _apply_activity_filters(
        query,
        search=search,
        entity_type=entity_type,
        entity_id=entity_id,
        activity_type=activity_type,
        activity_types=activity_types,
        activity_category=activity_category,
        status=status,
        priority=priority,
        owner_id=owner_id,
        assigned_user_id=assigned_user_id,
        created_by=created_by,
        visibility=visibility,
        tags=tags,
        has_attachments=has_attachments,
        completed=completed,
        pending=pending,
        date_from=date_from,
        date_to=date_to,
        include_archived=include_archived,
        task_status=task_status,
        responsible_user_id=responsible_user_id,
    )
    count_query = select(func.count()).select_from(CrmActivity)
    if vis is not None:
        count_query = count_query.where(vis)
    count_query = _apply_activity_filters(
        count_query,
        search=search,
        entity_type=entity_type,
        entity_id=entity_id,
        activity_type=activity_type,
        activity_types=activity_types,
        activity_category=activity_category,
        status=status,
        priority=priority,
        owner_id=owner_id,
        assigned_user_id=assigned_user_id,
        created_by=created_by,
        visibility=visibility,
        tags=tags,
        has_attachments=has_attachments,
        completed=completed,
        pending=pending,
        date_from=date_from,
        date_to=date_to,
        include_archived=include_archived,
        task_status=task_status,
        responsible_user_id=responsible_user_id,
    )
    total = db.scalar(count_query) or 0
    sort_column = {
        "created_at": CrmActivity.created_at,
        "updated_at": CrmActivity.updated_at,
        "due_date": CrmActivity.due_date,
        "start_date": CrmActivity.start_date,
        "title": CrmActivity.title,
        "priority": CrmActivity.priority,
    }.get(sort_by, CrmActivity.created_at)
    order = sort_column.desc() if sort_dir == "desc" else sort_column.asc()
    rows = db.scalars(
        query.order_by(order).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return _summaries_for_rows(db, list(rows)), _paginate(total, page, page_size)


def _attach_children(db: Session, activity: CrmActivity, payload: CrmActivityCreate) -> None:
    if payload.entity_links:
        for link in payload.entity_links:
            db.add(
                CrmActivityEntityLink(
                    activity_id=activity.id,
                    entity_type=link.entity_type,
                    entity_id=link.entity_id,
                    is_primary=link.is_primary,
                )
            )
    else:
        db.add(
            CrmActivityEntityLink(
                activity_id=activity.id,
                entity_type=payload.entity_type,
                entity_id=payload.entity_id,
                is_primary=True,
            )
        )
    if payload.checklist_items:
        for idx, item in enumerate(payload.checklist_items):
            db.add(
                CrmActivityChecklistItem(
                    activity_id=activity.id,
                    title=item.title,
                    sort_order=item.sort_order or idx,
                    is_completed=item.is_completed,
                )
            )
    if payload.attachments:
        for attachment in payload.attachments:
            db.add(
                CrmActivityAttachment(
                    activity_id=activity.id,
                    file_name=attachment.file_name,
                    file_url=attachment.file_url,
                    mime_type=attachment.mime_type,
                    file_size_bytes=attachment.file_size_bytes,
                    document_id=attachment.document_id,
                )
            )
    if payload.reminders:
        for reminder in payload.reminders:
            db.add(
                CrmActivityReminder(
                    activity_id=activity.id,
                    channel=reminder.channel,
                    remind_at=reminder.remind_at,
                    offset_minutes=reminder.offset_minutes,
                )
            )


def _apply_follow_up_rules(db: Session, activity: CrmActivity) -> CrmActivity | None:
    if activity.status != CrmActivityStatus.COMPLETED:
        return None
    rules = db.scalars(
        select(CrmFollowUpRule).where(
            CrmFollowUpRule.is_active.is_(True),
            CrmFollowUpRule.trigger_activity_type == activity.activity_type,
        )
    ).all()
    created: CrmActivity | None = None
    for rule in rules:
        if rule.trigger_status is not None and rule.trigger_status != activity.status:
            continue
        due = datetime.now(tz=UTC) + timedelta(days=rule.delay_days)
        follow_up = CrmActivity(
            entity_type=activity.entity_type,
            entity_id=activity.entity_id,
            related_entity_type=activity.related_entity_type,
            related_entity_id=activity.related_entity_id,
            activity_type=CrmActivityType.FOLLOW_UP,
            activity_category=CrmActivityCategory.FOLLOW_UP,
            title=f"Follow-up: {activity.title}",
            summary=f"Auto-created from {activity.activity_type.value}",
            status=CrmActivityStatus.PLANNED,
            priority=activity.priority,
            owner_id=activity.owner_id,
            assigned_user_id=activity.assigned_user_id,
            due_date=due,
            follow_up_reason=rule.follow_up_reason,
            visibility=activity.visibility,
            created_by=activity.updated_by or activity.created_by,
            metadata_json={"source_activity_id": str(activity.id), "rule_id": str(rule.id)},
        )
        db.add(follow_up)
        db.flush()
        db.add(
            CrmActivityEntityLink(
                activity_id=follow_up.id,
                entity_type=activity.entity_type,
                entity_id=activity.entity_id,
                is_primary=True,
            )
        )
        created = follow_up
    return created


def create_activity(db: Session, user: User, payload: CrmActivityCreate) -> CrmActivityDetail:
    category = payload.activity_category or _default_category(payload.activity_type)
    task_status = payload.task_status
    if payload.activity_type == CrmActivityType.TASK and task_status is None:
        task_status = CrmTaskStatus.NOT_STARTED

    activity = CrmActivity(
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        related_entity_type=payload.related_entity_type,
        related_entity_id=payload.related_entity_id,
        activity_type=payload.activity_type,
        activity_category=category,
        title=payload.title,
        summary=payload.summary,
        description=payload.description,
        outcome=payload.outcome,
        status=payload.status,
        task_status=task_status,
        priority=payload.priority,
        owner_id=payload.owner_id or user.id,
        assigned_user_id=payload.assigned_user_id,
        assigned_team_id=payload.assigned_team_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        duration_minutes=payload.duration_minutes,
        due_date=payload.due_date,
        reminder_date=payload.reminder_date,
        timezone=payload.timezone,
        location=payload.location,
        meeting_url=payload.meeting_url,
        tags=payload.tags,
        visibility=payload.visibility,
        follow_up_reason=payload.follow_up_reason,
        recurrence_frequency=payload.recurrence_frequency,
        recurrence_rule=payload.recurrence_rule,
        estimated_duration_minutes=payload.estimated_duration_minutes,
        metadata_json=payload.metadata_json,
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(activity)
    db.flush()
    _attach_children(db, activity, payload)
    _apply_follow_up_rules(db, activity)
    _touch_contact_last_activity(db, activity)
    db.commit()
    db.refresh(activity)
    loaded = get_activity_or_none(db, activity.id)
    assert loaded is not None
    return _serialize_detail(loaded)


def update_activity(
    db: Session,
    user: User,
    activity: CrmActivity,
    payload: CrmActivityUpdate,
) -> CrmActivityDetail:
    data = payload.model_dump(exclude_unset=True)
    incoming_meta = data.get("metadata_json")
    if incoming_meta is not None:
        current_meta = activity.metadata_json if isinstance(activity.metadata_json, dict) else {}
        merged = dict(current_meta)
        incoming = incoming_meta if isinstance(incoming_meta, dict) else {}
        history = current_meta.get("bitrix_history")
        links = dict(current_meta.get("task_links") or {})
        links.update(incoming.get("task_links") or {})
        merged.update(incoming)
        if history is not None and "bitrix_history" not in incoming:
            merged["bitrix_history"] = history
        if links:
            merged["task_links"] = {
                key: value for key, value in links.items() if value not in {None, ""}
            }
        data["metadata_json"] = merged
    for key, value in data.items():
        setattr(activity, key, value)
    activity.updated_by = user.id
    if payload.task_status is not None and payload.task_status != CrmTaskStatus.COMPLETED:
        activity.completed_at = None
        if payload.status is None:
            activity.status = CrmActivityStatus.PLANNED
    if payload.status == CrmActivityStatus.COMPLETED and activity.completed_at is None:
        activity.completed_at = datetime.now(tz=UTC)
    if payload.task_status == CrmTaskStatus.COMPLETED and activity.completed_at is None:
        activity.completed_at = datetime.now(tz=UTC)
        activity.status = CrmActivityStatus.COMPLETED
    _apply_follow_up_rules(db, activity)
    db.commit()
    loaded = get_activity_or_none(db, activity.id)
    assert loaded is not None
    return _serialize_detail(loaded)


def archive_activity(db: Session, user: User, activity: CrmActivity) -> CrmActivityDetail:
    del user
    activity.archived_at = datetime.now(tz=UTC)
    activity.status = CrmActivityStatus.ARCHIVED
    db.commit()
    loaded = get_activity_or_none(db, activity.id)
    assert loaded is not None
    return _serialize_detail(loaded)


def restore_activity(db: Session, user: User, activity: CrmActivity) -> CrmActivityDetail:
    del user
    activity.archived_at = None
    if activity.status == CrmActivityStatus.ARCHIVED:
        activity.status = CrmActivityStatus.PLANNED
    db.commit()
    loaded = get_activity_or_none(db, activity.id)
    assert loaded is not None
    return _serialize_detail(loaded)


def delete_activity(db: Session, activity: CrmActivity) -> None:
    db.delete(activity)
    db.commit()


def duplicate_activity(db: Session, user: User, activity: CrmActivity) -> CrmActivityDetail:
    payload = CrmActivityCreate(
        entity_type=activity.entity_type,
        entity_id=activity.entity_id,
        related_entity_type=activity.related_entity_type,
        related_entity_id=activity.related_entity_id,
        activity_type=activity.activity_type,
        activity_category=activity.activity_category,
        title=f"{activity.title} (copy)",
        summary=activity.summary,
        description=activity.description,
        status=CrmActivityStatus.PLANNED,
        task_status=CrmTaskStatus.NOT_STARTED if activity.task_status else None,
        priority=activity.priority,
        owner_id=activity.owner_id,
        assigned_user_id=activity.assigned_user_id,
        due_date=activity.due_date,
        tags=activity.tags,
        visibility=activity.visibility,
        metadata_json=activity.metadata_json,
        entity_links=[
            {"entity_type": link.entity_type, "entity_id": link.entity_id, "is_primary": link.is_primary}
            for link in activity.entity_links
        ],
        checklist_items=[
            {"title": item.title, "sort_order": item.sort_order, "is_completed": False}
            for item in activity.checklist_items
        ],
    )
    return create_activity(db, user, payload)


def complete_task(db: Session, user: User, activity: CrmActivity) -> CrmActivityDetail:
    if not _can_manage_tasks(user):
        raise ValueError("crm.activities.errors.manage_tasks_required")
    activity.task_status = CrmTaskStatus.COMPLETED
    activity.status = CrmActivityStatus.COMPLETED
    activity.completed_at = datetime.now(tz=UTC)
    activity.updated_by = user.id
    _apply_follow_up_rules(db, activity)
    if activity.entity_type == CrmActivityEntityType.CONTACT:
        db.add(
            CrmActivity(
                entity_type=activity.entity_type,
                entity_id=activity.entity_id,
                activity_type=CrmActivityType.SYSTEM_EVENT,
                activity_category=CrmActivityCategory.SYSTEM,
                title=f"Görev tamamlandı: {activity.title}",
                description=activity.description,
                status=CrmActivityStatus.COMPLETED,
                created_by=user.id,
                updated_by=user.id,
                owner_id=user.id,
                metadata_json={"event": "task_completed", "task_id": str(activity.id)},
            )
        )
    db.commit()
    loaded = get_activity_or_none(db, activity.id)
    assert loaded is not None
    return _serialize_detail(loaded)


def bulk_update_activities(
    db: Session,
    user: User,
    payload: CrmActivityBulkUpdateRequest,
) -> int:
    rows = db.scalars(
        select(CrmActivity).where(CrmActivity.id.in_(payload.activity_ids))
    ).all()
    updated = 0
    for activity in rows:
        if payload.assigned_user_id is not None:
            activity.assigned_user_id = payload.assigned_user_id
        if payload.status is not None:
            activity.status = payload.status
        if payload.priority is not None:
            activity.priority = payload.priority
        if payload.archive:
            activity.archived_at = datetime.now(tz=UTC)
            activity.status = CrmActivityStatus.ARCHIVED
        if payload.restore:
            activity.archived_at = None
        activity.updated_by = user.id
        updated += 1
    db.commit()
    return updated


def get_timeline(
    db: Session,
    user: User,
    *,
    search: str | None = None,
    entity_type: CrmActivityEntityType | None = None,
    entity_id: UUID | None = None,
    activity_type: CrmActivityType | None = None,
    activity_types: list[CrmActivityType] | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    page_size: int = 30,
    contact_search: str | None = None,
    project_group: str | None = None,
    event_kind: str | None = None,
    owner_id: UUID | None = None,
    status: CrmActivityStatus | None = None,
) -> tuple[list[CrmTimelineEntry], dict[str, int]]:
    from investhome_api.services.crm.operational_timeline import build_operational_timeline

    return build_operational_timeline(
        db,
        user,
        search=search,
        entity_type=entity_type,
        entity_id=entity_id,
        activity_type=activity_type,
        activity_types=activity_types,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
        contact_search=contact_search,
        project_group=project_group,
        event_kind=event_kind,
        owner_id=owner_id,
        status=status,
    )


_TASK_TZ = ZoneInfo("Europe/Istanbul")
_GENERIC_TASK_NAMES = {"contact", "company", "investor", "project", "lead", "crm", "kişiler", "unknown person", "unknown"}


def _istanbul_day_bounds(now: datetime | None = None) -> tuple[datetime, datetime]:
    current = (now or datetime.now(tz=UTC)).astimezone(_TASK_TZ)
    start = current.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start.astimezone(UTC), end.astimezone(UTC)


def _task_workspace_status(task_status: CrmTaskStatus | None, status: CrmActivityStatus | None) -> str:
    status_value = status.value if status else ""
    task_value = task_status.value if task_status else ""
    if task_value == CrmTaskStatus.COMPLETED.value or status_value == CrmActivityStatus.COMPLETED.value:
        return "completed"
    if task_value == CrmTaskStatus.CANCELLED.value or status_value == CrmActivityStatus.CANCELLED.value:
        return "cancelled"
    if task_value == CrmTaskStatus.IN_PROGRESS.value or status_value == CrmActivityStatus.IN_PROGRESS.value:
        return "in_progress"
    return "open"


def _task_is_active_clause():
    return and_(
        CrmActivity.task_status.is_distinct_from(CrmTaskStatus.COMPLETED),
        CrmActivity.task_status.is_distinct_from(CrmTaskStatus.CANCELLED),
        CrmActivity.status.not_in(
            [CrmActivityStatus.COMPLETED, CrmActivityStatus.CANCELLED, CrmActivityStatus.ARCHIVED]
        ),
    )


def _task_workspace_status_clause(workspace_status: str):
    kind = workspace_status.strip().casefold()
    if kind == "completed":
        return or_(
            CrmActivity.task_status == CrmTaskStatus.COMPLETED,
            CrmActivity.status == CrmActivityStatus.COMPLETED,
        )
    if kind == "cancelled":
        return or_(
            CrmActivity.task_status == CrmTaskStatus.CANCELLED,
            CrmActivity.status == CrmActivityStatus.CANCELLED,
        )
    if kind == "in_progress":
        return and_(
            _task_is_active_clause(),
            or_(
                CrmActivity.task_status == CrmTaskStatus.IN_PROGRESS,
                CrmActivity.status == CrmActivityStatus.IN_PROGRESS,
            ),
        )
    if kind == "open":
        return and_(
            _task_is_active_clause(),
            CrmActivity.task_status.is_distinct_from(CrmTaskStatus.IN_PROGRESS),
            CrmActivity.status.is_distinct_from(CrmActivityStatus.IN_PROGRESS),
        )
    if kind == "active":
        return _task_is_active_clause()
    return None


def _task_source(metadata: dict | None) -> str:
    payload = metadata if isinstance(metadata, dict) else {}
    history = payload.get("bitrix_history") if isinstance(payload.get("bitrix_history"), dict) else {}
    if history:
        record_id = history.get("bitrix_record_id") or history.get("bitrix_entity_id")
        if record_id:
            return f"Bitrix · {record_id}"
        return "Bitrix"
    source = str(payload.get("source") or "").strip()
    return source or "CRM"


def _clean_task_person_name(value: str | None) -> str | None:
    name = (value or "").strip()
    if not name or name.casefold() in _GENERIC_TASK_NAMES:
        return None
    return name


def _activity_links(meta: dict) -> dict:
    for key in ("note_links", "task_links"):
        links = meta.get(key)
        if isinstance(links, dict):
            return links
    return {}


def _attach_task_context(
    db: Session,
    summaries: list[CrmActivitySummary],
    rows: list[CrmActivity],
    *,
    fallback_contact_agreement: bool = True,
) -> list[CrmActivitySummary]:
    from investhome_api.models.crm_agreement import CrmAgreement
    from investhome_api.services.crm.operational_timeline import (
        _agreement_context_by_contact,
        _timeline_project_label,
    )

    by_id = {row.id: row for row in rows}
    contact_ids = {
        row.entity_id
        for row in rows
        if row.entity_type == CrmActivityEntityType.CONTACT
    }
    agreement_ids: set[UUID] = set()
    for row in rows:
        meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        links = _activity_links(meta)
        raw_agreement = links.get("agreement_id") or meta.get("agreement_id")
        if raw_agreement:
            try:
                agreement_ids.add(UUID(str(raw_agreement)))
            except ValueError:
                continue
        if row.related_entity_id and row.related_entity_type == CrmActivityEntityType.TRANSACTION:
            agreement_ids.add(row.related_entity_id)
    agreements = (
        {
            row.id: row
            for row in db.scalars(select(CrmAgreement).where(CrmAgreement.id.in_(agreement_ids))).all()
        }
        if agreement_ids
        else {}
    )
    for agreement in agreements.values():
        contact_ids.add(agreement.contact_id)
    agreement_ctx = _agreement_context_by_contact(db, contact_ids)
    enriched: list[CrmActivitySummary] = []
    for summary in summaries:
        row = by_id.get(summary.id)
        meta = row.metadata_json if row and isinstance(row.metadata_json, dict) else {}
        links = _activity_links(meta)
        person = _clean_task_person_name(summary.entity_name or summary.person_name)
        agreement = None
        raw_agreement = links.get("agreement_id") or meta.get("agreement_id")
        if raw_agreement:
            try:
                agreement = agreements.get(UUID(str(raw_agreement)))
            except ValueError:
                agreement = None
        if agreement is None and row and row.related_entity_id:
            agreement = agreements.get(row.related_entity_id)
        if (
            agreement is None
            and fallback_contact_agreement
            and row
            and row.entity_type == CrmActivityEntityType.CONTACT
        ):
            ctx = agreement_ctx.get(row.entity_id)
            agreement = ctx[0] if ctx else None
        project_group = str(links.get("project_group") or "").strip() or None
        project_label = None
        unit_number = None
        agreement_id = None
        if agreement is not None:
            project_label = _timeline_project_label(agreement.project_group, agreement.metadata_json)
            unit_number = agreement.unit_number
            agreement_id = agreement.id
            project_group = project_group or agreement.project_group
            if not person:
                person = _clean_task_person_name(summary.entity_name)
        elif project_group:
            project_label = _timeline_project_label(project_group, None)
        workspace_status = _task_workspace_status(summary.task_status, summary.status)
        enriched.append(
            summary.model_copy(
                update={
                    "person_name": person,
                    "project_label": project_label,
                    "project_group": project_group,
                    "unit_number": unit_number,
                    "agreement_id": agreement_id,
                    "source": _task_source(meta),
                    "source_task_status": summary.task_status.value if summary.task_status else (
                        summary.status.value if summary.status else None
                    ),
                    "source_priority": summary.priority.value if summary.priority else None,
                    "workspace_status": workspace_status,
                }
            )
        )
    return enriched


def _apply_task_scope(
    query,
    *,
    contact_ids: set[UUID] | None,
    due_from: datetime | None,
    due_to: datetime | None,
    due_bucket: str | None,
    workspace_status: str | None,
):
    if contact_ids is not None:
        query = query.where(
            CrmActivity.entity_type == CrmActivityEntityType.CONTACT,
            CrmActivity.entity_id.in_(contact_ids),
        )
    if due_from is not None:
        query = query.where(CrmActivity.due_date >= due_from)
    if due_to is not None:
        query = query.where(CrmActivity.due_date <= due_to)
    today_start, today_end = _istanbul_day_bounds()
    bucket = (due_bucket or "").strip().casefold()
    if bucket == "today":
        query = query.where(
            _task_is_active_clause(),
            CrmActivity.due_date >= today_start,
            CrmActivity.due_date < today_end,
        )
    elif bucket == "overdue":
        query = query.where(_task_is_active_clause(), CrmActivity.due_date < today_start)
    status_clause = _task_workspace_status_clause(workspace_status or "")
    if status_clause is not None:
        query = query.where(status_clause)
    return query


def create_workspace_task(db: Session, user: User, payload: CrmTaskCreate) -> CrmActivityDetail:
    from investhome_api.models.crm_agreement import CrmAgreement

    contact_id = payload.contact_id
    project_group = (payload.project_group or "").strip() or None
    agreement_id = payload.agreement_id
    if agreement_id is not None:
        agreement = db.get(CrmAgreement, agreement_id)
        if agreement is not None:
            contact_id = contact_id or agreement.contact_id
            project_group = project_group or agreement.project_group
    entity_type = payload.entity_type
    entity_id = payload.entity_id
    if contact_id is not None:
        entity_type = CrmActivityEntityType.CONTACT
        entity_id = contact_id
    elif entity_type is None or entity_id is None:
        entity_type = CrmActivityEntityType.INTERNAL_USER
        entity_id = user.id
    links = {
        "contact_id": str(contact_id) if contact_id else None,
        "project_group": project_group,
        "agreement_id": str(agreement_id) if agreement_id else None,
    }
    metadata = dict(payload.metadata_json or {})
    metadata["task_links"] = {key: value for key, value in links.items() if value}
    related_type = CrmActivityEntityType.TRANSACTION if agreement_id else None
    create_payload = CrmActivityCreate(
        entity_type=entity_type,
        entity_id=entity_id,
        related_entity_type=related_type,
        related_entity_id=agreement_id,
        activity_type=CrmActivityType.TASK,
        title=payload.title,
        summary=payload.summary,
        description=payload.description,
        status=CrmActivityStatus.PLANNED,
        task_status=payload.task_status or CrmTaskStatus.NOT_STARTED,
        priority=payload.priority,
        owner_id=user.id,
        assigned_user_id=payload.assigned_user_id,
        due_date=payload.due_date,
        visibility=payload.visibility,
        metadata_json=metadata,
    )
    return create_activity(db, user, create_payload)


def create_workspace_note(db: Session, user: User, payload: CrmNoteCreate) -> CrmActivityDetail:
    from investhome_api.models.crm_agreement import CrmAgreement

    contact_id = payload.contact_id
    project_group = (payload.project_group or "").strip() or None
    agreement_id = payload.agreement_id
    if agreement_id is not None:
        agreement = db.get(CrmAgreement, agreement_id)
        if agreement is not None:
            contact_id = contact_id or agreement.contact_id
            project_group = project_group or agreement.project_group
    entity_type = payload.entity_type
    entity_id = payload.entity_id
    if contact_id is not None:
        entity_type = CrmActivityEntityType.CONTACT
        entity_id = contact_id
    elif entity_type == CrmActivityEntityType.CONTACT and entity_id is not None:
        contact_id = entity_id
    if entity_type is None or entity_id is None:
        raise ValueError("A person is required to create a note")
    body = (payload.description or payload.summary or payload.title or "").strip()
    if not body:
        raise ValueError("Note text is required")
    title = (payload.title or "").strip() or body.splitlines()[0][:120]
    if title.casefold() in _NOTE_GENERIC_TITLES:
        title = body.splitlines()[0][:120]
    summary = (payload.summary or body)[:1000]
    links = {
        "contact_id": str(contact_id) if contact_id else None,
        "project_group": project_group,
        "agreement_id": str(agreement_id) if agreement_id else None,
    }
    metadata = dict(payload.metadata_json or {})
    metadata["note_links"] = {key: value for key, value in links.items() if value}
    metadata.setdefault("source", "CRM")
    related_type = CrmActivityEntityType.TRANSACTION if agreement_id else None
    create_payload = CrmActivityCreate(
        entity_type=entity_type,
        entity_id=entity_id,
        related_entity_type=related_type,
        related_entity_id=agreement_id,
        activity_type=CrmActivityType.NOTE,
        title=title[:500],
        summary=summary,
        description=body,
        status=CrmActivityStatus.COMPLETED,
        owner_id=user.id,
        assigned_user_id=user.id,
        visibility=payload.visibility,
        metadata_json=metadata,
        start_date=datetime.now(tz=UTC),
    )
    return create_activity(db, user, create_payload)


def list_tasks(
    db: Session,
    user: User,
    *,
    assigned_user_id: UUID | None = None,
    my_tasks: bool = False,
    team_tasks: bool = False,
    status: CrmTaskStatus | None = None,
    entity_id: UUID | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 25,
    contact_search: str | None = None,
    project_group: str | None = None,
    priority: CrmActivityPriority | None = None,
    due_from: datetime | None = None,
    due_to: datetime | None = None,
    due_bucket: str | None = None,
    workspace_status: str | None = None,
) -> tuple[list[CrmActivitySummary], dict[str, int], CrmTaskCounters]:
    del team_tasks
    from investhome_api.services.crm.operational_timeline import _resolve_timeline_contact_ids

    if my_tasks:
        assigned_user_id = user.id
    vis = _visibility_filter(user)
    contact_ids = _resolve_timeline_contact_ids(
        db,
        entity_type=CrmActivityEntityType.CONTACT if entity_id else None,
        entity_id=entity_id,
        contact_search=contact_search,
        project_group=project_group,
    )
    if contact_ids is not None and len(contact_ids) == 0:
        empty = _paginate(0, page, page_size)
        return [], empty, CrmTaskCounters()

    def _base():
        query = select(CrmActivity)
        if vis is not None:
            query = query.where(vis)
        query = _apply_activity_filters(
            query,
            search=search,
            entity_id=entity_id if contact_search is None and not project_group else None,
            activity_types=list(TASK_TYPES),
            task_status=status,
            priority=priority,
            responsible_user_id=assigned_user_id,
        )
        return _apply_task_scope(
            query,
            contact_ids=contact_ids,
            due_from=due_from,
            due_to=due_to,
            due_bucket=due_bucket,
            workspace_status=workspace_status,
        )

    def _count(query) -> int:
        count_query = select(func.count()).select_from(query.subquery())
        return db.scalar(count_query) or 0

    query = _base()
    total = _count(query)
    rows = list(
        db.scalars(
            query.options(selectinload(CrmActivity.attachments), selectinload(CrmActivity.comments))
            .order_by(CrmActivity.due_date.asc().nulls_last(), CrmActivity.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    summaries = _attach_task_context(db, _summaries_for_rows(db, rows), rows)

    counter_base = select(CrmActivity)
    if vis is not None:
        counter_base = counter_base.where(vis)
    counter_base = _apply_activity_filters(
        counter_base,
        search=search,
        entity_id=entity_id if contact_search is None and not project_group else None,
        activity_types=list(TASK_TYPES),
        priority=priority,
        responsible_user_id=assigned_user_id,
    )
    counter_base = _apply_task_scope(
        counter_base,
        contact_ids=contact_ids,
        due_from=due_from,
        due_to=due_to,
        due_bucket=None,
        workspace_status=None,
    )
    today_start, today_end = _istanbul_day_bounds()
    open_q = counter_base.where(_task_is_active_clause())
    today_q = counter_base.where(
        _task_is_active_clause(),
        CrmActivity.due_date >= today_start,
        CrmActivity.due_date < today_end,
    )
    overdue_q = counter_base.where(_task_is_active_clause(), CrmActivity.due_date < today_start)
    completed_q = counter_base.where(
        or_(
            CrmActivity.task_status == CrmTaskStatus.COMPLETED,
            CrmActivity.status == CrmActivityStatus.COMPLETED,
        )
    )
    counters = CrmTaskCounters(
        open=_count(open_q),
        today=_count(today_q),
        overdue=_count(overdue_q),
        completed=_count(completed_q),
        total=_count(counter_base),
    )
    return summaries, _paginate(total, page, page_size), counters



def _plain_note_text(activity: CrmActivity) -> str:
    title = (activity.title or "").strip()
    body = (activity.description or activity.summary or "").strip()
    raw = body if title.casefold() in _NOTE_GENERIC_TITLES else (body or title)
    text = _NOTE_HTML_RE.sub(" ", raw)
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&#39;", "'")
        .replace("&quot;", '"')
    )
    return re.sub(r"\s+", " ", text).strip()


def _looks_like_note_dump(text: str) -> bool:
    blob = (text or "").strip()
    if not blob:
        return True
    if blob.casefold() in _NOTE_EMPTY_MARKERS:
        return True
    if (blob.startswith("{") or blob.startswith("[")) and re.search(
        r'"(ID|AUTHOR_ID|COMMENT|UF_|fields|result|bitrix)"', blob, re.I
    ):
        return True
    lowered = blob.casefold()
    if "bitrix24" in lowered and "webhook" in lowered:
        return True
    if blob.startswith("<?xml"):
        return True
    return False


def _note_workspace_source(meta: dict) -> str:
    if isinstance(meta.get("bitrix_historical_comment"), dict):
        return "Bitrix"
    history = meta.get("bitrix_history")
    if isinstance(history, dict):
        return "Bitrix"
    source = str(meta.get("source") or "").strip()
    if source.casefold().startswith("bitrix"):
        return "Bitrix"
    return source or "CRM"


def _note_author_name(meta: dict) -> str | None:
    history = meta.get("bitrix_history") if isinstance(meta.get("bitrix_history"), dict) else {}
    comment = (
        meta.get("bitrix_historical_comment")
        if isinstance(meta.get("bitrix_historical_comment"), dict)
        else {}
    )
    name = str(history.get("author_name") or comment.get("author_name") or "").strip()
    if name and name.casefold() not in _GENERIC_TASK_NAMES:
        return name
    return None


def list_notes(
    db: Session,
    user: User,
    *,
    entity_type: CrmActivityEntityType | None = None,
    entity_id: UUID | None = None,
    search: str | None = None,
    contact_search: str | None = None,
    project_group: str | None = None,
    assigned_user_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[CrmActivitySummary], dict[str, int]]:
    from investhome_api.services.crm.operational_timeline import _resolve_timeline_contact_ids

    del entity_type
    vis = _visibility_filter(user)
    contact_ids = _resolve_timeline_contact_ids(
        db,
        entity_type=CrmActivityEntityType.CONTACT if entity_id else None,
        entity_id=entity_id,
        contact_search=contact_search,
        project_group=project_group,
    )
    if contact_ids is not None and len(contact_ids) == 0:
        return [], _paginate(0, page, page_size)

    query = select(CrmActivity)
    if vis is not None:
        query = query.where(vis)
    query = _apply_activity_filters(
        query,
        search=search,
        entity_id=entity_id if contact_search is None and not project_group else None,
        activity_types=list(NOTE_LIST_TYPES),
        responsible_user_id=assigned_user_id,
        date_from=date_from,
        date_to=date_to,
    )
    if contact_ids is not None:
        query = query.where(
            CrmActivity.entity_type == CrmActivityEntityType.CONTACT,
            CrmActivity.entity_id.in_(contact_ids),
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0
    rows = list(
        db.scalars(
            query.options(selectinload(CrmActivity.attachments), selectinload(CrmActivity.comments))
            .order_by(CrmActivity.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    visible_rows = [
        row for row in rows if (text := _plain_note_text(row)) and not _looks_like_note_dump(text)
    ]
    summaries = _attach_task_context(
        db,
        _summaries_for_rows(db, visible_rows),
        visible_rows,
        fallback_contact_agreement=False,
    )
    enriched: list[CrmActivitySummary] = []
    for summary, row in zip(summaries, visible_rows, strict=False):
        meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        updates: dict[str, object] = {"source": _note_workspace_source(meta)}
        author = _note_author_name(meta)
        if author:
            updates["created_by_name"] = author
        preview = _plain_note_text(row)
        if preview:
            updates["summary"] = preview[:1000]
        enriched.append(summary.model_copy(update=updates))
    return enriched, _paginate(total, page, page_size)


def list_meetings(
    db: Session,
    user: User,
    *,
    entity_type: CrmActivityEntityType | None = None,
    entity_id: UUID | None = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[CrmActivitySummary], dict[str, int]]:
    return list_activities(
        db,
        user,
        entity_type=entity_type,
        entity_id=entity_id,
        activity_types=list(MEETING_TYPES),
        page=page,
        page_size=page_size,
        sort_by="start_date",
        sort_dir="asc",
    )


def list_follow_ups(
    db: Session,
    user: User,
    *,
    entity_type: CrmActivityEntityType | None = None,
    entity_id: UUID | None = None,
    reason: CrmFollowUpReason | None = None,
    pending: bool = True,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[CrmActivitySummary], dict[str, int]]:
    query_types = list(FOLLOW_UP_TYPES)
    items, meta = list_activities(
        db,
        user,
        entity_type=entity_type,
        entity_id=entity_id,
        activity_types=query_types,
        pending=pending,
        page=page,
        page_size=page_size,
        sort_by="due_date",
        sort_dir="asc",
    )
    if reason is not None:
        items = [item for item in items if item.follow_up_reason == reason]
    return items, meta


def create_follow_up(db: Session, user: User, payload: CrmFollowUpCreate) -> CrmActivityDetail:
    title = payload.title or f"Follow-up: {payload.reason.value.replace('_', ' ').title()}"
    create_payload = CrmActivityCreate(
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        activity_type=CrmActivityType.FOLLOW_UP,
        title=title,
        description=payload.notes,
        status=CrmActivityStatus.PLANNED,
        due_date=payload.due_date,
        reminder_date=payload.reminder_date,
        follow_up_reason=payload.reason,
        owner_id=payload.owner_id or user.id,
        assigned_user_id=payload.assigned_user_id,
    )
    detail = create_activity(db, user, create_payload)
    if payload.entity_type == CrmActivityEntityType.CONTACT:
        from investhome_api.models.crm_contact import CrmContact

        contact = db.get(CrmContact, payload.entity_id)
        if contact is not None:
            contact.next_follow_up_at = payload.due_date
            db.commit()
    return detail


def complete_follow_up(db: Session, user: User, activity: CrmActivity) -> CrmActivityDetail:
    activity.status = CrmActivityStatus.COMPLETED
    activity.completed_at = datetime.now(tz=UTC)
    activity.updated_by = user.id
    db.commit()
    loaded = get_activity_or_none(db, activity.id)
    assert loaded is not None
    return _serialize_detail(loaded)


def _calendar_kind(activity_type: CrmActivityType) -> str:
    if activity_type == CrmActivityType.TASK:
        return "task"
    if activity_type in {CrmActivityType.REMINDER, CrmActivityType.FOLLOW_UP}:
        return "reminder"
    if activity_type in MEETING_TYPES:
        return "meeting"
    if activity_type == CrmActivityType.PAYMENT:
        return "payment"
    if activity_type == CrmActivityType.CLOSING:
        return "closing"
    if activity_type in {
        CrmActivityType.CONTRACT_SIGNED,
        CrmActivityType.DOCUMENT_SENT,
        CrmActivityType.DOCUMENT_RECEIVED,
        CrmActivityType.PROPOSAL_SENT,
        CrmActivityType.PROPOSAL_RECEIVED,
    }:
        return "document"
    if activity_type in {CrmActivityType.INSPECTION, CrmActivityType.RESERVATION}:
        return "delivery"
    return "other"


def _calendar_stamp(*values: datetime | None) -> datetime | None:
    for value in values:
        if value is not None:
            return value
    return None


def _calendar_in_range(value: datetime | None, start: datetime, end: datetime) -> bool:
    if value is None:
        return False
    stamp = _as_utc(value)
    return start <= stamp < end


def _date_at_istanbul(value: date) -> datetime:
    return datetime(value.year, value.month, value.day, tzinfo=_TASK_TZ).astimezone(UTC)


def _is_all_day(stamp: datetime | None, start_date: datetime | None) -> bool:
    if start_date is None:
        return True
    local = _as_utc(start_date).astimezone(_TASK_TZ)
    return local.hour == 0 and local.minute == 0 and local.second == 0


def create_workspace_event(db: Session, user: User, payload: CrmCalendarEventCreate) -> CrmActivityDetail:
    kind = (payload.event_kind or "task").strip().casefold()
    if kind not in {"task", "meeting", "reminder"}:
        kind = "task"
    if kind == "meeting":
        activity_type = CrmActivityType.MEETING
        create_payload = CrmTaskCreate(
            title=payload.title,
            description=payload.description,
            contact_id=payload.contact_id,
            project_group=payload.project_group,
            agreement_id=payload.agreement_id,
            assigned_user_id=payload.assigned_user_id,
            due_date=None,
        )
        detail_source = create_workspace_task(db, user, create_payload)
        loaded = get_activity_or_none(db, detail_source.id)
        assert loaded is not None
        loaded.activity_type = activity_type
        loaded.activity_category = CrmActivityCategory.MEETING
        loaded.status = CrmActivityStatus.SCHEDULED
        loaded.task_status = None
        loaded.start_date = payload.occurs_at
        loaded.due_date = None
        loaded.updated_by = user.id
        db.commit()
        refreshed = get_activity_or_none(db, loaded.id)
        assert refreshed is not None
        return _serialize_detail(refreshed)
    task_payload = CrmTaskCreate(
        title=payload.title,
        description=payload.description,
        contact_id=payload.contact_id,
        project_group=payload.project_group,
        agreement_id=payload.agreement_id,
        assigned_user_id=payload.assigned_user_id,
        due_date=payload.occurs_at,
        task_status=CrmTaskStatus.NOT_STARTED,
    )
    detail = create_workspace_task(db, user, task_payload)
    if kind == "reminder":
        loaded = get_activity_or_none(db, detail.id)
        assert loaded is not None
        loaded.activity_type = CrmActivityType.REMINDER
        loaded.reminder_date = payload.occurs_at
        loaded.updated_by = user.id
        db.commit()
        refreshed = get_activity_or_none(db, loaded.id)
        assert refreshed is not None
        return _serialize_detail(refreshed)
    return detail


def get_calendar(
    db: Session,
    user: User,
    *,
    start: datetime,
    end: datetime,
    assigned_user_id: UUID | None = None,
    contact_search: str | None = None,
    entity_id: UUID | None = None,
    project_group: str | None = None,
    event_kind: str | None = None,
) -> CrmCalendarResponse:
    from investhome_api.models.crm_agreement import CrmAgreement
    from investhome_api.models.crm_contact import CrmContact
    from investhome_api.models.document import Document, DocumentLink
    from investhome_api.services.crm.operational_timeline import (
        _resolve_timeline_contact_ids,
        _timeline_project_label,
    )

    range_start = _as_utc(start)
    range_end = _as_utc(end)
    if range_end <= range_start:
        range_end = range_start + timedelta(days=1)
    today_start, _today_end = _istanbul_day_bounds()
    kind_filter = (event_kind or "").strip().casefold()
    vis = _visibility_filter(user)
    contact_ids = _resolve_timeline_contact_ids(
        db,
        entity_type=CrmActivityEntityType.CONTACT if entity_id else None,
        entity_id=entity_id,
        contact_search=contact_search,
        project_group=project_group,
    )
    if contact_ids is not None and len(contact_ids) == 0:
        return CrmCalendarResponse(events=[], start=range_start, end=range_end, total=0)

    query = select(CrmActivity).where(
        CrmActivity.archived_at.is_(None),
        _exclude_demo_clause(),
        CrmActivity.activity_type.in_(CALENDAR_ACTIVITY_TYPES),
        or_(
            and_(CrmActivity.start_date.is_not(None), CrmActivity.start_date >= range_start, CrmActivity.start_date < range_end),
            and_(CrmActivity.due_date.is_not(None), CrmActivity.due_date >= range_start, CrmActivity.due_date < range_end),
            and_(CrmActivity.reminder_date.is_not(None), CrmActivity.reminder_date >= range_start, CrmActivity.reminder_date < range_end),
        ),
    )
    if vis is not None:
        query = query.where(vis)
    if assigned_user_id is not None:
        query = query.where(
            or_(CrmActivity.assigned_user_id == assigned_user_id, CrmActivity.owner_id == assigned_user_id)
        )
    if contact_ids is not None:
        query = query.where(
            CrmActivity.entity_type == CrmActivityEntityType.CONTACT,
            CrmActivity.entity_id.in_(contact_ids),
        )
    rows = list(
        db.scalars(query.order_by(CrmActivity.start_date.asc().nulls_last(), CrmActivity.due_date.asc().nulls_last()).limit(CALENDAR_EVENT_LIMIT)).all()
    )
    summaries = {
        item.id: item
        for item in _attach_task_context(db, _summaries_for_rows(db, rows), rows)
    }
    events: list[CrmCalendarEvent] = []
    for row in rows:
        summary = summaries.get(row.id)
        event_at = None
        for candidate in (row.start_date, row.due_date, row.reminder_date):
            if _calendar_in_range(candidate, range_start, range_end):
                event_at = _as_utc(candidate)
                break
        if event_at is None:
            continue
        kind = _calendar_kind(row.activity_type)
        if kind_filter and kind != kind_filter:
            continue
        completed = _task_workspace_status(row.task_status, row.status) in {"completed", "cancelled"}
        overdue = (not completed) and event_at < today_start
        events.append(
            CrmCalendarEvent(
                id=str(row.id),
                title=row.title,
                activity_type=row.activity_type.value,
                event_kind=kind,
                record_kind="activity",
                status=row.status.value if row.status else None,
                start_date=row.start_date,
                end_date=row.end_date,
                due_date=row.due_date,
                event_at=event_at,
                all_day=_is_all_day(event_at, row.start_date),
                entity_type=row.entity_type.value if row.entity_type else None,
                entity_id=row.entity_id,
                assigned_user_id=row.assigned_user_id,
                entity_name=summary.entity_name if summary else None,
                assigned_user_name=(summary.assigned_user_name or summary.owner_name) if summary else None,
                person_name=summary.person_name if summary else None,
                project_label=summary.project_label if summary else None,
                project_group=summary.project_group if summary else None,
                unit_number=summary.unit_number if summary else None,
                agreement_id=summary.agreement_id if summary else None,
                source=_task_source(row.metadata_json if isinstance(row.metadata_json, dict) else None),
                summary=row.summary or row.description,
                is_overdue=overdue,
                is_completed=completed,
            )
        )

    include_purchases = kind_filter in {"", "purchase"}
    include_documents = kind_filter in {"", "document"}
    start_day = range_start.astimezone(_TASK_TZ).date()
    end_day = (range_end.astimezone(_TASK_TZ) - timedelta(seconds=1)).date()
    if include_purchases and assigned_user_id is None:
        agreement_query = select(CrmAgreement).where(
            CrmAgreement.agreement_date.is_not(None),
            CrmAgreement.agreement_date >= start_day,
            CrmAgreement.agreement_date <= end_day,
        )
        if project_group:
            agreement_query = agreement_query.where(CrmAgreement.project_group == project_group)
        if contact_ids is not None:
            agreement_query = agreement_query.where(CrmAgreement.contact_id.in_(contact_ids))
        elif entity_id is not None:
            agreement_query = agreement_query.where(CrmAgreement.contact_id == entity_id)
        agreements = list(db.scalars(agreement_query.limit(CALENDAR_EVENT_LIMIT)).all())
        contact_map = {
            contact.id: contact
            for contact in db.scalars(
                select(CrmContact).where(CrmContact.id.in_({row.contact_id for row in agreements}))
            ).all()
        } if agreements else {}
        for row in agreements:
            if row.agreement_date is None:
                continue
            event_at = _date_at_istanbul(row.agreement_date)
            contact = contact_map.get(row.contact_id)
            person = _clean_task_person_name(contact.display_name if contact else None)
            events.append(
                CrmCalendarEvent(
                    id=f"purchase:{row.id}",
                    title=f"Satın Alma · {person or _timeline_project_label(row.project_group, row.metadata_json)}",
                    activity_type="purchase",
                    event_kind="purchase",
                    record_kind="purchase",
                    status=row.status.value if row.status else None,
                    event_at=event_at,
                    all_day=True,
                    entity_type="contact",
                    entity_id=row.contact_id,
                    person_name=person,
                    entity_name=person,
                    project_label=_timeline_project_label(row.project_group, row.metadata_json),
                    project_group=row.project_group,
                    unit_number=row.unit_number,
                    agreement_id=row.id,
                    source="CRM satın alma",
                    is_overdue=False,
                    is_completed=row.status.value == "completed" if row.status else False,
                )
            )

    if include_documents and assigned_user_id is None:
        doc_query = (
            select(Document, DocumentLink)
            .join(DocumentLink, DocumentLink.document_id == Document.id)
            .where(
                Document.expiration_date.is_not(None),
                Document.expiration_date >= start_day,
                Document.expiration_date <= end_day,
                Document.is_latest_version.is_(True),
                DocumentLink.entity_type.in_(("crm_contact", "contact", "crm_agreement")),
            )
            .limit(CALENDAR_EVENT_LIMIT)
        )
        doc_rows = list(db.execute(doc_query).all())
        doc_contact_ids = {link.entity_id for _doc, link in doc_rows if link.entity_type in {"crm_contact", "contact"}}
        doc_agreement_ids = {link.entity_id for _doc, link in doc_rows if link.entity_type == "crm_agreement"}
        doc_agreements = {
            row.id: row
            for row in db.scalars(select(CrmAgreement).where(CrmAgreement.id.in_(doc_agreement_ids))).all()
        } if doc_agreement_ids else {}
        for agreement in doc_agreements.values():
            if agreement.contact_id:
                doc_contact_ids.add(agreement.contact_id)
        doc_contacts = {
            contact.id: contact
            for contact in db.scalars(select(CrmContact).where(CrmContact.id.in_(doc_contact_ids))).all()
        } if doc_contact_ids else {}
        seen_docs: set[str] = set()
        for document, link in doc_rows:
            if document.expiration_date is None:
                continue
            key = str(document.id)
            if key in seen_docs:
                continue
            person = None
            contact_id = None
            agreement_id = None
            project_label = None
            project_group_value = None
            unit_number = None
            if link.entity_type in {"crm_contact", "contact"}:
                if contact_ids is not None and link.entity_id not in contact_ids:
                    continue
                contact_id = link.entity_id
                person = _clean_task_person_name(doc_contacts.get(link.entity_id).display_name if doc_contacts.get(link.entity_id) else None)
            elif link.entity_type == "crm_agreement":
                agreement = doc_agreements.get(link.entity_id)
                agreement_id = link.entity_id
                if agreement is not None:
                    if project_group and agreement.project_group != project_group:
                        continue
                    if contact_ids is not None and agreement.contact_id not in contact_ids:
                        continue
                    contact_id = agreement.contact_id
                    contact = doc_contacts.get(agreement.contact_id) if agreement.contact_id else None
                    person = _clean_task_person_name(contact.display_name if contact else None)
                    project_label = _timeline_project_label(agreement.project_group, agreement.metadata_json)
                    project_group_value = agreement.project_group
                    unit_number = agreement.unit_number
            seen_docs.add(key)
            events.append(
                CrmCalendarEvent(
                    id=f"document:{document.id}",
                    title=document.title,
                    activity_type="document",
                    event_kind="document",
                    record_kind="document",
                    event_at=_date_at_istanbul(document.expiration_date),
                    all_day=True,
                    entity_type="contact" if contact_id else None,
                    entity_id=contact_id,
                    person_name=person,
                    entity_name=person,
                    project_label=project_label,
                    project_group=project_group_value,
                    unit_number=unit_number,
                    agreement_id=agreement_id,
                    source="CRM belge",
                    summary=document.description,
                    is_overdue=_date_at_istanbul(document.expiration_date) < today_start,
                    is_completed=False,
                )
            )

    events.sort(key=lambda item: (item.event_at, item.title))
    if len(events) > CALENDAR_EVENT_LIMIT:
        events = events[:CALENDAR_EVENT_LIMIT]
    return CrmCalendarResponse(events=events, start=range_start, end=range_end, total=len(events))


def get_dashboard_widgets(db: Session, user: User) -> CrmActivityDashboardWidgets:
    now = datetime.now(tz=UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    def _fetch(**kwargs) -> list[CrmActivitySummary]:
        items, _ = list_activities(db, user, page_size=10, **kwargs)
        return items

    return CrmActivityDashboardWidgets(
        todays_tasks=_fetch(
            activity_types=list(TASK_TYPES),
            date_from=today_start,
            date_to=today_end,
            pending=True,
        ),
        overdue_tasks=_fetch(
            activity_types=list(TASK_TYPES),
            pending=True,
            date_to=now,
        ),
        upcoming_meetings=_fetch(
            activity_types=list(MEETING_TYPES),
            date_from=now,
            date_to=now + timedelta(days=7),
        ),
        follow_ups_due=_fetch(
            activity_types=list(FOLLOW_UP_TYPES),
            pending=True,
            date_to=now + timedelta(days=7),
        ),
        recent_notes=_fetch(activity_types=list(NOTE_TYPES)),
        recent_activities=_fetch(),
        missed_activities=_fetch(status=CrmActivityStatus.MISSED),
    )


def create_saved_filter(
    db: Session,
    user: User,
    payload: CrmActivitySavedFilterCreate,
) -> CrmActivitySavedFilterResponse:
    row = CrmActivitySavedFilter(
        name=payload.name,
        owner_user_id=user.id,
        filters_json=payload.filters_json,
        filter_logic=payload.filter_logic,
        is_shared=payload.is_shared,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return CrmActivitySavedFilterResponse.model_validate(row)


def list_saved_filters(db: Session, user: User) -> list[CrmActivitySavedFilterResponse]:
    rows = db.scalars(
        select(CrmActivitySavedFilter).where(
            or_(
                CrmActivitySavedFilter.owner_user_id == user.id,
                CrmActivitySavedFilter.is_shared.is_(True),
            )
        )
    ).all()
    return [CrmActivitySavedFilterResponse.model_validate(row) for row in rows]


def add_comment(
    db: Session,
    user: User,
    activity: CrmActivity,
    body: str,
    *,
    parent_id: UUID | None = None,
    mentions: list[str] | None = None,
) -> CrmActivityDetail:
    db.add(
        CrmActivityComment(
            activity_id=activity.id,
            parent_id=parent_id,
            body=body,
            mentions=mentions,
            created_by=user.id,
        )
    )
    db.commit()
    loaded = get_activity_or_none(db, activity.id)
    assert loaded is not None
    return _serialize_detail(loaded)
