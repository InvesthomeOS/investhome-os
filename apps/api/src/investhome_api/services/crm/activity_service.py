"""CRM activity timeline, tasks, notes, and follow-up services."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import String, and_, cast, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from investhome_api.models.activity import ActivityEntityType, ActivityLog
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
    CrmCalendarResponse,
    CrmFollowUpCreate,
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
NOTE_TYPES = frozenset({CrmActivityType.NOTE, CrmActivityType.INTERNAL_DISCUSSION})
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
) -> tuple[list[CrmTimelineEntry], dict[str, int]]:
    activity_items, meta = list_activities(
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
        sort_by="created_at",
        sort_dir="desc",
    )
    entries = [
        CrmTimelineEntry(
            id=str(item.id),
            source="crm_activity",
            activity_type=item.activity_type.value,
            title=item.title,
            summary=item.summary,
            status=item.status.value,
            priority=item.priority.value,
            entity_type=item.entity_type.value,
            entity_id=item.entity_id,
            created_at=item.created_at,
            is_system_event=item.activity_type
            in {CrmActivityType.SYSTEM_EVENT, CrmActivityType.AUTOMATION_EVENT},
        )
        for item in activity_items
    ]

    crm_entity_map = {
        CrmActivityEntityType.CONTACT: ActivityEntityType.CRM_CONTACT,
        CrmActivityEntityType.COMPANY: ActivityEntityType.CRM_COMPANY,
        CrmActivityEntityType.RELATIONSHIP: ActivityEntityType.CRM_RELATIONSHIP,
    }
    if entity_type in crm_entity_map and entity_id is not None and page == 1:
        logs = db.scalars(
            select(ActivityLog)
            .where(
                ActivityLog.entity_type == crm_entity_map[entity_type],
                ActivityLog.entity_id == entity_id,
            )
            .order_by(ActivityLog.created_at.desc())
            .limit(10)
        ).all()
        for log in logs:
            entries.append(
                CrmTimelineEntry(
                    id=f"log-{log.id}",
                    source="audit_log",
                    activity_type="system_event",
                    title=log.description_key,
                    summary=None,
                    status=None,
                    priority=None,
                    entity_type=entity_type.value,
                    entity_id=entity_id,
                    actor_name=log.actor_name,
                    created_at=log.created_at,
                    is_system_event=True,
                    metadata_json=log.metadata_json,
                )
            )
        entries.sort(key=lambda e: e.created_at, reverse=True)
        entries = entries[:page_size]

    return entries, meta


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
) -> tuple[list[CrmActivitySummary], dict[str, int]]:
    del team_tasks
    if my_tasks:
        assigned_user_id = user.id
    return list_activities(
        db,
        user,
        activity_types=[CrmActivityType.TASK, CrmActivityType.REMINDER],
        assigned_user_id=assigned_user_id,
        entity_id=entity_id,
        search=search,
        task_status=status,
        status=None,
        page=page,
        page_size=page_size,
        sort_by="due_date",
        sort_dir="asc",
    )


def list_notes(
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
        activity_types=list(NOTE_TYPES),
        page=page,
        page_size=page_size,
    )


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


def get_calendar(
    db: Session,
    user: User,
    *,
    start: datetime,
    end: datetime,
    assigned_user_id: UUID | None = None,
) -> CrmCalendarResponse:
    query = select(CrmActivity).where(
        CrmActivity.archived_at.is_(None),
        _exclude_demo_clause(),
        or_(
            CrmActivity.start_date.between(start, end),
            CrmActivity.due_date.between(start, end),
        ),
    )
    vis = _visibility_filter(user)
    if vis is not None:
        query = query.where(vis)
    if assigned_user_id is not None:
        query = query.where(CrmActivity.assigned_user_id == assigned_user_id)
    rows = list(db.scalars(query.order_by(CrmActivity.start_date.asc().nullslast())).all())
    names = {
        item.id: item
        for item in _summaries_for_rows(db, rows)
    }
    events = [
        CrmCalendarEvent(
            id=row.id,
            title=row.title,
            activity_type=row.activity_type,
            status=row.status,
            start_date=row.start_date,
            end_date=row.end_date,
            due_date=row.due_date,
            all_day=row.start_date is not None and row.end_date is None,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            assigned_user_id=row.assigned_user_id,
            entity_name=names[row.id].entity_name if row.id in names else None,
            assigned_user_name=names[row.id].assigned_user_name if row.id in names else None,
        )
        for row in rows
    ]
    return CrmCalendarResponse(events=events, start=start, end=end)


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
