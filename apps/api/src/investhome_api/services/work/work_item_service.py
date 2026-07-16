"""Work item business logic — tasks, meetings, follow-ups."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import Request
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.company_foundation import CompanyProfile
from investhome_api.models.inventory import InventoryAsset, InventoryReservation
from investhome_api.models.investor import Investor
from investhome_api.models.lead import Lead
from investhome_api.models.project import Project
from investhome_api.models.sales import (
    CLOSED_OPPORTUNITY_STAGES,
    OpportunityNextAction,
    SalesOpportunity,
)
from investhome_api.models.sales_proposal import SalesProposal
from investhome_api.models.user_auth import User
from investhome_api.models.work_item import (
    ACTIVE_WORK_ITEM_STATUSES,
    AttendanceStatus,
    ContactMethod,
    FollowUpOutcome,
    FollowUpRecord,
    MeetingRecord,
    MeetingType,
    ParticipantRole,
    RelatedEntityType,
    ResponseStatus,
    TERMINAL_WORK_ITEM_STATUSES,
    WorkItem,
    WorkItemParticipant,
    WorkItemPriority,
    WorkItemStatus,
    WorkItemStatusHistory,
    WorkItemType,
)
from investhome_api.services.activity_recorder import (
    log_entity_archived,
    log_entity_created,
    log_entity_restored,
    log_entity_updated,
)
from investhome_api.services.activity_service import snapshot_entity
from investhome_api.services.permission_service import user_has_permission
from investhome_api.services.sales import opportunity_service as opp_svc
from investhome_api.services.work.config import WORK_ITEM_ACTIVITY_FIELDS, WORK_TYPE_TO_OPPORTUNITY_ACTION


class WorkItemError(ValueError):
    def __init__(self, error_key: str, *, status_code: int = 422) -> None:
        self.error_key = error_key
        self.status_code = status_code
        super().__init__(error_key)


def _now() -> datetime:
    return datetime.now(UTC)


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _company_timezone(db: Session) -> ZoneInfo:
    profile = db.scalar(select(CompanyProfile).limit(1))
    tz_name = profile.default_timezone if profile else "Europe/Istanbul"
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("UTC")


def _day_bounds(db: Session, *, day: date | None = None) -> tuple[datetime, datetime]:
    tz = _company_timezone(db)
    target = day or datetime.now(tz).date()
    start = datetime.combine(target, time.min, tzinfo=tz).astimezone(UTC)
    end = datetime.combine(target, time.max, tzinfo=tz).astimezone(UTC)
    return start, end


def derive_effective_status(item: WorkItem, *, clock: datetime | None = None) -> WorkItemStatus:
    now = clock or _now()
    if item.status in TERMINAL_WORK_ITEM_STATUSES or item.archived_at is not None:
        return item.status
    if item.due_at is not None and _ensure_aware(item.due_at) < now and item.status in ACTIVE_WORK_ITEM_STATUSES:
        return WorkItemStatus.OVERDUE
    return item.status


def _append_status_history(
    db: Session,
    item: WorkItem,
    *,
    previous: WorkItemStatus | None,
    new: WorkItemStatus,
    actor: User | None,
    reason: str | None = None,
) -> None:
    db.add(
        WorkItemStatusHistory(
            work_item_id=item.id,
            previous_status=previous.value if previous else None,
            new_status=new.value,
            reason=reason,
            changed_by_user_id=actor.id if actor else None,
        )
    )


def _validate_archived_entities(db: Session, data: dict[str, Any]) -> None:
    lead_id = data.get("lead_id")
    if lead_id:
        lead = db.get(Lead, lead_id)
        if lead is None or lead.archived_at is not None:
            raise WorkItemError("work.errors.lead_not_found", status_code=404)
    opp_id = data.get("opportunity_id")
    if opp_id:
        opp = db.get(SalesOpportunity, opp_id)
        if opp is None or opp.archived_at is not None:
            raise WorkItemError("work.errors.opportunity_not_found", status_code=404)
    proposal_id = data.get("proposal_id")
    if proposal_id:
        proposal = db.get(SalesProposal, proposal_id)
        if proposal is None or proposal.archived_at is not None:
            raise WorkItemError("work.errors.proposal_not_found", status_code=404)
    asset_id = data.get("inventory_asset_id")
    if asset_id:
        asset = db.get(InventoryAsset, asset_id)
        if asset is None or asset.archived_at is not None:
            raise WorkItemError("work.errors.inventory_not_found", status_code=404)


def _can_view_item(user: User, item: WorkItem) -> bool:
    if item.is_private:
        if user_has_permission(user, "work", "view_private"):
            return True
        if item.assigned_user_id == user.id or item.created_by_user_id == user.id:
            return True
        return False
    if user_has_permission(user, "work", "view"):
        return True
    if user_has_permission(user, "work", "view_team"):
        return True
    return False


def _can_view_private(user: User) -> bool:
    return user_has_permission(user, "work", "view_private")


def _apply_visibility(query, user: User):
    if _can_view_private(user):
        return query
    return query.where(
        or_(
            WorkItem.is_private.is_(False),
            WorkItem.assigned_user_id == user.id,
            WorkItem.created_by_user_id == user.id,
        )
    )


def get_work_item_or_raise(
    db: Session,
    work_item_id: UUID,
    *,
    user: User,
    include_archived: bool = False,
) -> WorkItem:
    item = db.get(WorkItem, work_item_id)
    if item is None or (item.archived_at is not None and not include_archived):
        raise WorkItemError("work.errors.not_found", status_code=404)
    if not _can_view_item(user, item):
        raise WorkItemError("work.errors.forbidden", status_code=403)
    return item


def sync_opportunity_next_action(db: Session, opportunity_id: UUID, *, actor: User | None = None) -> None:
    opportunity = db.get(SalesOpportunity, opportunity_id)
    if opportunity is None or opportunity.stage in CLOSED_OPPORTUNITY_STAGES:
        return

    nearest = db.scalar(
        select(WorkItem)
        .where(
            WorkItem.opportunity_id == opportunity_id,
            WorkItem.archived_at.is_(None),
            WorkItem.status.in_(list(ACTIVE_WORK_ITEM_STATUSES)),
            WorkItem.due_at.is_not(None),
        )
        .order_by(WorkItem.due_at.asc())
        .limit(1)
    )
    if nearest is None:
        return

    action_key = WORK_TYPE_TO_OPPORTUNITY_ACTION.get(nearest.work_item_type.value)
    if action_key is None:
        return
    next_date = nearest.due_at.date() if nearest.due_at else None
    if next_date is None:
        return
    opportunity.next_action = OpportunityNextAction(action_key)
    opportunity.next_action_date = next_date
    opportunity.updated_at = _now()
    db.flush()


def create_work_item(
    db: Session,
    data: dict[str, Any],
    *,
    actor: User,
    request: Request | None = None,
) -> WorkItem:
    _validate_archived_entities(db, data)
    assigned = data.get("assigned_user_id")
    if assigned:
        user = db.get(User, assigned)
        if user is None:
            raise WorkItemError("work.errors.user_not_found", status_code=404)

    item = WorkItem(
        title=data["title"],
        description=data.get("description"),
        work_item_type=data.get("work_item_type", WorkItemType.TASK),
        status=data.get("status", WorkItemStatus.OPEN),
        priority=data.get("priority", WorkItemPriority.MEDIUM),
        assigned_user_id=assigned,
        created_by_user_id=actor.id,
        due_at=data.get("due_at"),
        start_at=data.get("start_at"),
        reminder_at=data.get("reminder_at"),
        related_entity_type=data.get("related_entity_type"),
        related_entity_id=data.get("related_entity_id"),
        project_id=data.get("project_id"),
        lead_id=data.get("lead_id"),
        opportunity_id=data.get("opportunity_id"),
        party_id=data.get("party_id"),
        inventory_asset_id=data.get("inventory_asset_id"),
        proposal_id=data.get("proposal_id"),
        is_private=data.get("is_private", False),
    )
    db.add(item)
    db.flush()
    _append_status_history(db, item, previous=None, new=item.status, actor=actor)

    log_entity_created(
        db,
        entity_type=ActivityEntityType.WORK_ITEM,
        entity_id=item.id,
        description_key="activity.work_item.created",
        actor=actor,
        metadata={"title": item.title, "work_item_type": item.work_item_type.value},
        request=request,
    )

    if item.opportunity_id:
        sync_opportunity_next_action(db, item.opportunity_id, actor=actor)

    from investhome_api.services.work import work_notifications as notify

    if item.assigned_user_id and item.assigned_user_id != actor.id:
        notify.notify_assigned(db, item, actor=actor)

    return item


def update_work_item(
    db: Session,
    item: WorkItem,
    data: dict[str, Any],
    *,
    actor: User,
    request: Request | None = None,
) -> WorkItem:
    if item.status == WorkItemStatus.COMPLETED:
        raise WorkItemError("work.errors.completed_immutable")
    _validate_archived_entities(db, {**data, "lead_id": data.get("lead_id", item.lead_id)})

    before = snapshot_entity(item, WORK_ITEM_ACTIVITY_FIELDS)
    old_assigned = item.assigned_user_id

    for field in (
        "title",
        "description",
        "work_item_type",
        "priority",
        "assigned_user_id",
        "due_at",
        "start_at",
        "reminder_at",
        "outcome",
        "is_private",
        "lead_id",
        "opportunity_id",
        "party_id",
        "project_id",
        "inventory_asset_id",
        "proposal_id",
    ):
        if field in data:
            setattr(item, field, data[field])
    item.updated_at = _now()
    db.flush()

    log_entity_updated(
        db,
        entity_type=ActivityEntityType.WORK_ITEM,
        entity_id=item.id,
        description_key="activity.work_item.updated",
        actor=actor,
        before=before,
        after=snapshot_entity(item, WORK_ITEM_ACTIVITY_FIELDS),
        request=request,
    )

    if item.opportunity_id:
        sync_opportunity_next_action(db, item.opportunity_id, actor=actor)

    if "assigned_user_id" in data and item.assigned_user_id != old_assigned and item.assigned_user_id:
        from investhome_api.services.work import work_notifications as notify

        notify.notify_reassigned(db, item, actor=actor)

    return item


def change_status(
    db: Session,
    item: WorkItem,
    new_status: WorkItemStatus,
    *,
    actor: User,
    reason: str | None = None,
    request: Request | None = None,
) -> WorkItem:
    if item.status in TERMINAL_WORK_ITEM_STATUSES:
        raise WorkItemError("work.errors.terminal_status")
    previous = item.status
    item.status = new_status
    item.updated_at = _now()
    if new_status == WorkItemStatus.BLOCKED:
        from investhome_api.services.work import work_notifications as notify

        notify.notify_blocked(db, item)
    _append_status_history(db, item, previous=previous, new=new_status, actor=actor, reason=reason)
    db.flush()

    log_entity_updated(
        db,
        entity_type=ActivityEntityType.WORK_ITEM,
        entity_id=item.id,
        description_key="activity.work_item.status_changed",
        actor=actor,
        before={"status": previous.value},
        after={"status": new_status.value},
        metadata={"reason": reason},
        request=request,
    )
    return item


def complete_work_item(
    db: Session,
    item: WorkItem,
    *,
    actor: User,
    outcome: str | None = None,
    next_follow_up: dict[str, Any] | None = None,
    request: Request | None = None,
) -> WorkItem:
    if item.status == WorkItemStatus.COMPLETED:
        raise WorkItemError("work.errors.already_completed")
    previous = item.status
    item.status = WorkItemStatus.COMPLETED
    item.completed_at = _now()
    if outcome:
        item.outcome = outcome
    item.updated_at = _now()
    _append_status_history(db, item, previous=previous, new=WorkItemStatus.COMPLETED, actor=actor)
    db.flush()

    log_entity_updated(
        db,
        entity_type=ActivityEntityType.WORK_ITEM,
        entity_id=item.id,
        description_key="activity.work_item.completed",
        actor=actor,
        before={"status": previous.value},
        after={"status": WorkItemStatus.COMPLETED.value},
        request=request,
    )

    if next_follow_up:
        create_next_follow_up(db, item, next_follow_up, actor=actor, request=request)

    if item.opportunity_id:
        sync_opportunity_next_action(db, item.opportunity_id, actor=actor)

    return item


def cancel_work_item(
    db: Session,
    item: WorkItem,
    *,
    actor: User,
    reason: str | None = None,
    request: Request | None = None,
) -> WorkItem:
    if item.status == WorkItemStatus.COMPLETED:
        raise WorkItemError("work.errors.completed_immutable")
    previous = item.status
    item.status = WorkItemStatus.CANCELLED
    item.cancelled_at = _now()
    item.updated_at = _now()
    _append_status_history(db, item, previous=previous, new=WorkItemStatus.CANCELLED, actor=actor, reason=reason)
    db.flush()

    from investhome_api.services.work import work_notifications as notify

    notify.notify_cancelled(db, item, actor=actor)

    log_entity_updated(
        db,
        entity_type=ActivityEntityType.WORK_ITEM,
        entity_id=item.id,
        description_key="activity.work_item.cancelled",
        actor=actor,
        before={"status": previous.value},
        after={"status": WorkItemStatus.CANCELLED.value},
        request=request,
    )
    if item.opportunity_id:
        sync_opportunity_next_action(db, item.opportunity_id, actor=actor)
    return item


def archive_work_item(
    db: Session,
    item: WorkItem,
    *,
    actor: User,
    request: Request | None = None,
) -> WorkItem:
    if item.status == WorkItemStatus.COMPLETED:
        raise WorkItemError("work.errors.completed_not_archivable")
    item.archived_at = _now()
    item.status = WorkItemStatus.ARCHIVED
    item.updated_at = _now()
    db.flush()
    log_entity_archived(
        db,
        entity_type=ActivityEntityType.WORK_ITEM,
        entity_id=item.id,
        description_key="activity.work_item.archived",
        actor=actor,
        request=request,
    )
    return item


def restore_work_item(
    db: Session,
    item: WorkItem,
    *,
    actor: User,
    request: Request | None = None,
) -> WorkItem:
    item.archived_at = None
    item.status = WorkItemStatus.OPEN
    item.updated_at = _now()
    db.flush()
    log_entity_restored(
        db,
        entity_type=ActivityEntityType.WORK_ITEM,
        entity_id=item.id,
        description_key="activity.work_item.restored",
        actor=actor,
        request=request,
    )
    return item


def reschedule_work_item(
    db: Session,
    item: WorkItem,
    *,
    due_at: datetime,
    actor: User,
    request: Request | None = None,
) -> WorkItem:
    before = {"due_at": item.due_at.isoformat() if item.due_at else None}
    item.due_at = due_at
    if item.status == WorkItemStatus.OVERDUE:
        item.status = WorkItemStatus.OPEN
    item.updated_at = _now()
    db.flush()
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.WORK_ITEM,
        entity_id=item.id,
        description_key="activity.work_item.rescheduled",
        actor=actor,
        before=before,
        after={"due_at": due_at.isoformat()},
        request=request,
    )
    if item.opportunity_id:
        sync_opportunity_next_action(db, item.opportunity_id, actor=actor)
    return item


def create_meeting(
    db: Session,
    data: dict[str, Any],
    *,
    actor: User,
    request: Request | None = None,
) -> tuple[WorkItem, MeetingRecord]:
    item_data = {
        **data,
        "work_item_type": WorkItemType.MEETING,
        "title": data.get("title") or "Meeting",
    }
    item = create_work_item(db, item_data, actor=actor, request=request)
    meeting = MeetingRecord(
        work_item_id=item.id,
        meeting_type=data.get("meeting_type", MeetingType.VIDEO),
        location=data.get("location"),
        meeting_url=data.get("meeting_url"),
        agenda=data.get("agenda"),
        started_at=data.get("started_at") or data.get("start_at"),
    )
    db.add(meeting)
    db.flush()
    for participant in data.get("participants") or []:
        db.add(
            WorkItemParticipant(
                work_item_id=item.id,
                party_id=participant.get("party_id"),
                user_id=participant.get("user_id"),
                participant_role=participant.get("participant_role", ParticipantRole.ATTENDEE),
                attendance_status=participant.get("attendance_status", AttendanceStatus.INVITED),
            )
        )
    db.flush()
    return item, meeting


def update_meeting(
    db: Session,
    item: WorkItem,
    meeting: MeetingRecord,
    data: dict[str, Any],
    *,
    actor: User,
    request: Request | None = None,
) -> MeetingRecord:
    item_fields = {k: v for k, v in data.items() if k in {"title", "description", "due_at", "start_at", "assigned_user_id"}}
    if item_fields:
        update_work_item(db, item, item_fields, actor=actor, request=request)
    for field in (
        "meeting_type",
        "location",
        "meeting_url",
        "agenda",
        "notes",
        "outcome",
        "decision_summary",
        "next_steps",
        "started_at",
        "ended_at",
    ):
        if field in data:
            setattr(meeting, field, data[field])
    meeting.updated_at = _now()
    db.flush()
    return meeting


def complete_meeting(
    db: Session,
    item: WorkItem,
    meeting: MeetingRecord,
    *,
    actor: User,
    data: dict[str, Any],
    request: Request | None = None,
) -> WorkItem:
    update_meeting(db, item, meeting, data, actor=actor, request=request)
    meeting.ended_at = data.get("ended_at") or _now()
    complete_work_item(
        db,
        item,
        actor=actor,
        outcome=data.get("outcome") or meeting.outcome,
        next_follow_up=data.get("next_follow_up"),
        request=request,
    )
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.WORK_ITEM,
        entity_id=item.id,
        description_key="activity.work_item.meeting_completed",
        actor=actor,
        before={},
        after={"meeting_id": str(meeting.id)},
        request=request,
    )
    return item


def create_follow_up(
    db: Session,
    data: dict[str, Any],
    *,
    actor: User,
    request: Request | None = None,
) -> tuple[WorkItem, FollowUpRecord]:
    wi_type = data.get("work_item_type", WorkItemType.FOLLOW_UP)
    item_data = {**data, "work_item_type": wi_type, "title": data.get("title") or "Follow-up"}
    item = create_work_item(db, item_data, actor=actor, request=request)
    record = FollowUpRecord(
        work_item_id=item.id,
        follow_up_type=wi_type,
        contact_method=data.get("contact_method", ContactMethod.CALL),
        notes=data.get("notes"),
    )
    db.add(record)
    db.flush()
    return item, record


def complete_follow_up(
    db: Session,
    item: WorkItem,
    record: FollowUpRecord,
    *,
    actor: User,
    data: dict[str, Any],
    request: Request | None = None,
) -> WorkItem:
    if "outcome" in data:
        record.outcome = data["outcome"]
    if "response_status" in data:
        record.response_status = data["response_status"]
    if "notes" in data:
        record.notes = data["notes"]
    record.updated_at = _now()
    complete_work_item(
        db,
        item,
        actor=actor,
        outcome=data.get("outcome"),
        next_follow_up=data.get("next_follow_up"),
        request=request,
    )
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.WORK_ITEM,
        entity_id=item.id,
        description_key="activity.work_item.follow_up_completed",
        actor=actor,
        before={},
        after={"follow_up_id": str(record.id)},
        request=request,
    )
    return item


def create_next_follow_up(
    db: Session,
    source: WorkItem,
    data: dict[str, Any],
    *,
    actor: User,
    request: Request | None = None,
) -> WorkItem:
    payload = {
        "title": data.get("title") or f"Follow-up: {source.title}",
        "work_item_type": data.get("work_item_type", source.work_item_type),
        "due_at": data.get("due_at"),
        "assigned_user_id": data.get("assigned_user_id", source.assigned_user_id),
        "lead_id": data.get("lead_id", source.lead_id),
        "opportunity_id": data.get("opportunity_id", source.opportunity_id),
        "party_id": data.get("party_id", source.party_id),
        "contact_method": data.get("contact_method", ContactMethod.CALL),
    }
    item, _ = create_follow_up(db, payload, actor=actor, request=request)
    log_entity_created(
        db,
        entity_type=ActivityEntityType.WORK_ITEM,
        entity_id=item.id,
        description_key="activity.work_item.next_follow_up_created",
        actor=actor,
        metadata={"source_work_item_id": str(source.id)},
        request=request,
    )
    return item


def _base_query(db: Session, user: User, *, include_archived: bool = False):
    query = select(WorkItem)
    if not include_archived:
        query = query.where(WorkItem.archived_at.is_(None))
    return _apply_visibility(query, user)


def list_work_items(
    db: Session,
    user: User,
    *,
    search: str | None = None,
    assigned_user_id: UUID | None = None,
    created_by_user_id: UUID | None = None,
    work_item_type: WorkItemType | None = None,
    status: WorkItemStatus | None = None,
    priority: WorkItemPriority | None = None,
    due_from: datetime | None = None,
    due_to: datetime | None = None,
    lead_id: UUID | None = None,
    opportunity_id: UUID | None = None,
    party_id: UUID | None = None,
    proposal_id: UUID | None = None,
    is_private: bool | None = None,
    include_archived: bool = False,
    sort_by: str = "due_at",
    sort_dir: str = "asc",
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[WorkItem], int]:
    query = _base_query(db, user, include_archived=include_archived)
    if search:
        query = query.where(or_(WorkItem.title.ilike(f"%{search}%"), WorkItem.description.ilike(f"%{search}%")))
    if assigned_user_id:
        query = query.where(WorkItem.assigned_user_id == assigned_user_id)
    if created_by_user_id:
        query = query.where(WorkItem.created_by_user_id == created_by_user_id)
    if work_item_type:
        query = query.where(WorkItem.work_item_type == work_item_type)
    if status:
        query = query.where(WorkItem.status == status)
    if priority:
        query = query.where(WorkItem.priority == priority)
    if due_from:
        query = query.where(WorkItem.due_at >= due_from)
    if due_to:
        query = query.where(WorkItem.due_at <= due_to)
    if lead_id:
        query = query.where(WorkItem.lead_id == lead_id)
    if opportunity_id:
        query = query.where(WorkItem.opportunity_id == opportunity_id)
    if party_id:
        query = query.where(WorkItem.party_id == party_id)
    if proposal_id:
        query = query.where(WorkItem.proposal_id == proposal_id)
    if is_private is not None:
        query = query.where(WorkItem.is_private == is_private)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    sort_col = getattr(WorkItem, sort_by, WorkItem.due_at)
    query = query.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())
    items = list(db.scalars(query.offset(offset).limit(limit)).all())
    return items, total


def _active_status_filter(query, now: datetime):
    return query.where(
        WorkItem.status.in_(list(ACTIVE_WORK_ITEM_STATUSES)),
        or_(WorkItem.status != WorkItemStatus.OVERDUE, WorkItem.due_at.is_not(None)),
    )


def list_today(db: Session, user: User, *, limit: int = 100) -> list[WorkItem]:
    start, end = _day_bounds(db)
    query = _base_query(db, user).where(WorkItem.due_at >= start, WorkItem.due_at <= end)
    query = _active_status_filter(query, _now())
    return list(db.scalars(query.order_by(WorkItem.due_at.asc()).limit(limit)).all())


def list_overdue(db: Session, user: User, *, limit: int = 100) -> list[WorkItem]:
    now = _now()
    query = _base_query(db, user).where(
        WorkItem.due_at.is_not(None),
        WorkItem.due_at < now,
        WorkItem.status.in_(list(ACTIVE_WORK_ITEM_STATUSES)),
    )
    items = list(db.scalars(query.order_by(WorkItem.due_at.asc()).limit(limit)).all())
    return [item for item in items if item.due_at and _ensure_aware(item.due_at) < now]


def list_upcoming(
    db: Session,
    user: User,
    *,
    days: int = 7,
    limit: int = 100,
) -> list[WorkItem]:
    _, end_today = _day_bounds(db)
    future = end_today + timedelta(days=days)
    query = _base_query(db, user).where(
        WorkItem.due_at > end_today,
        WorkItem.due_at <= future,
        WorkItem.status.in_(list(ACTIVE_WORK_ITEM_STATUSES)),
    )
    return list(db.scalars(query.order_by(WorkItem.due_at.asc()).limit(limit)).all())


def list_by_view(db: Session, user: User, view: str, *, limit: int = 100) -> list[WorkItem]:
    if view == "today":
        return list_today(db, user, limit=limit)
    if view == "overdue":
        return list_overdue(db, user, limit=limit)
    if view == "upcoming":
        return list_upcoming(db, user, limit=limit)
    if view == "meetings":
        return list(
            db.scalars(
                _base_query(db, user)
                .where(WorkItem.work_item_type == WorkItemType.MEETING)
                .order_by(WorkItem.due_at.asc())
                .limit(limit)
            ).all()
        )
    if view == "calls":
        return list(
            db.scalars(
                _base_query(db, user)
                .where(WorkItem.work_item_type == WorkItemType.CALL)
                .order_by(WorkItem.due_at.asc())
                .limit(limit)
            ).all()
        )
    if view == "follow_ups":
        return list(
            db.scalars(
                _base_query(db, user)
                .where(
                    WorkItem.work_item_type.in_(
                        [
                            WorkItemType.FOLLOW_UP,
                            WorkItemType.PROPOSAL_FOLLOW_UP,
                            WorkItemType.RESERVATION_FOLLOW_UP,
                            WorkItemType.DEPOSIT_FOLLOW_UP,
                            WorkItemType.CONTRACT_FOLLOW_UP,
                            WorkItemType.CLOSING_FOLLOW_UP,
                        ]
                    )
                )
                .order_by(WorkItem.due_at.asc())
                .limit(limit)
            ).all()
        )
    if view == "waiting":
        return list(
            db.scalars(
                _base_query(db, user)
                .where(WorkItem.status == WorkItemStatus.WAITING)
                .order_by(WorkItem.due_at.asc())
                .limit(limit)
            ).all()
        )
    if view == "blocked":
        return list(
            db.scalars(
                _base_query(db, user)
                .where(WorkItem.status == WorkItemStatus.BLOCKED)
                .order_by(WorkItem.due_at.asc())
                .limit(limit)
            ).all()
        )
    if view == "completed":
        return list(
            db.scalars(
                _base_query(db, user)
                .where(WorkItem.status == WorkItemStatus.COMPLETED)
                .order_by(WorkItem.completed_at.desc())
                .limit(limit)
            ).all()
        )
    if view == "my_work":
        return list(
            db.scalars(
                _base_query(db, user)
                .where(WorkItem.assigned_user_id == user.id)
                .order_by(WorkItem.due_at.asc())
                .limit(limit)
            ).all()
        )
    if view == "team_work":
        if not user_has_permission(user, "work", "view_team"):
            raise WorkItemError("work.errors.forbidden", status_code=403)
        return list(
            db.scalars(
                _base_query(db, user)
                .where(WorkItem.assigned_user_id.is_not(None))
                .order_by(WorkItem.due_at.asc())
                .limit(limit)
            ).all()
        )
    raise WorkItemError("work.errors.invalid_view", status_code=400)


def build_dashboard_kpis(db: Session, user: User) -> dict[str, int]:
    today_items = list_today(db, user, limit=500)
    overdue_items = list_overdue(db, user, limit=500)
    meetings_today = [i for i in today_items if i.work_item_type == WorkItemType.MEETING]
    blocked = list_by_view(db, user, "blocked", limit=500)
    waiting = list_by_view(db, user, "waiting", limit=500)
    my_work = list_by_view(db, user, "my_work", limit=500)

    no_next_action = 0
    if user_has_permission(user, "sales", "view"):
        today = datetime.now(_company_timezone(db)).date()
        no_next_action = db.scalar(
            select(func.count()).select_from(SalesOpportunity).where(
                SalesOpportunity.archived_at.is_(None),
                ~SalesOpportunity.stage.in_(list(CLOSED_OPPORTUNITY_STAGES)),
                or_(
                    SalesOpportunity.next_action.is_(None),
                    SalesOpportunity.next_action_date.is_(None),
                    SalesOpportunity.next_action_date < today,
                ),
            )
        ) or 0

    return {
        "today_count": len(today_items),
        "overdue_count": len(overdue_items),
        "meetings_today_count": len(meetings_today),
        "blocked_count": len(blocked),
        "waiting_count": len(waiting),
        "my_work_count": len(my_work),
        "no_next_action_count": no_next_action,
    }


def list_for_lead(db: Session, lead_id: UUID, user: User) -> list[WorkItem]:
    return list(
        db.scalars(
            _base_query(db, user)
            .where(WorkItem.lead_id == lead_id)
            .order_by(WorkItem.due_at.asc())
        ).all()
    )


def list_for_opportunity(db: Session, opportunity_id: UUID, user: User) -> list[WorkItem]:
    return list(
        db.scalars(
            _base_query(db, user)
            .where(WorkItem.opportunity_id == opportunity_id)
            .order_by(WorkItem.due_at.asc())
        ).all()
    )


def create_proposal_follow_up_template(
    db: Session,
    proposal: SalesProposal,
    *,
    actor: User,
    due_at: datetime | None = None,
) -> WorkItem:
    due = due_at or (_now() + timedelta(days=3))
    item, _ = create_follow_up(
        db,
        {
            "title": f"Proposal follow-up: {proposal.proposal_number}",
            "work_item_type": WorkItemType.PROPOSAL_FOLLOW_UP,
            "due_at": due,
            "opportunity_id": proposal.opportunity_id,
            "lead_id": proposal.lead_id,
            "party_id": proposal.party_id,
            "proposal_id": proposal.id,
            "assigned_user_id": proposal.assigned_sales_user_id,
        },
        actor=actor,
    )
    return item


def create_reservation_follow_up_template(
    db: Session,
    reservation: InventoryReservation,
    *,
    actor: User,
    follow_up_type: WorkItemType = WorkItemType.RESERVATION_FOLLOW_UP,
) -> WorkItem:
    due = reservation.expires_at or (_now() + timedelta(days=1))
    item, _ = create_follow_up(
        db,
        {
            "title": f"Reservation follow-up",
            "work_item_type": follow_up_type,
            "due_at": due,
            "lead_id": reservation.lead_id,
            "inventory_asset_id": reservation.inventory_asset_id,
            "assigned_user_id": reservation.reserved_by_user_id,
        },
        actor=actor,
    )
    return item
