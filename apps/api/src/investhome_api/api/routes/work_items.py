"""Work item API routes."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.work_item import FollowUpRecord, MeetingRecord, WorkItem, WorkItemParticipant
from investhome_api.models.user_auth import User
from investhome_api.models.work_item import WorkItemPriority, WorkItemStatus, WorkItemType
from investhome_api.schemas.work_item import (
    CompleteWorkItemRequest,
    FollowUpCompleteRequest,
    FollowUpCreate,
    MeetingCompleteRequest,
    MeetingCreate,
    MeetingUpdate,
    RescheduleRequest,
    StatusChangeRequest,
    WorkDashboardKpisResponse,
    WorkItemCreate,
    WorkItemListResponse,
    WorkItemResponse,
    WorkItemUpdate,
    CalendarEventResponse,
)
from investhome_api.services.work import work_item_service as svc

router = APIRouter(prefix="/sales/work", tags=["work-items"])


def _handle_error(exc: svc.WorkItemError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.error_key)


def _enrich(db: Session, item: WorkItem) -> WorkItemResponse:
    meeting = db.scalar(select(MeetingRecord).where(MeetingRecord.work_item_id == item.id))
    follow_up = db.scalar(select(FollowUpRecord).where(FollowUpRecord.work_item_id == item.id))
    participants = list(
        db.scalars(select(WorkItemParticipant).where(WorkItemParticipant.work_item_id == item.id)).all()
    )
    response = WorkItemResponse.model_validate(item)
    response.effective_status = svc.derive_effective_status(item)
    if meeting:
        from investhome_api.schemas.work_item import MeetingRecordResponse

        response.meeting = MeetingRecordResponse.model_validate(meeting)
    if follow_up:
        from investhome_api.schemas.work_item import FollowUpRecordResponse

        response.follow_up = FollowUpRecordResponse.model_validate(follow_up)
    if participants:
        from investhome_api.schemas.work_item import WorkItemParticipantResponse

        response.participants = [WorkItemParticipantResponse.model_validate(p) for p in participants]
    return response


@router.get("/dashboard/kpis", response_model=WorkDashboardKpisResponse)
def get_dashboard_kpis(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("work", "view")),
) -> WorkDashboardKpisResponse:
    return WorkDashboardKpisResponse(**svc.build_dashboard_kpis(db, user))


@router.get("/views/{view_name}", response_model=WorkItemListResponse)
def get_view(
    view_name: str,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("work", "view")),
) -> WorkItemListResponse:
    try:
        items = svc.list_by_view(db, user, view_name, limit=limit)
    except svc.WorkItemError as exc:
        raise _handle_error(exc) from exc
    return WorkItemListResponse(
        items=[_enrich(db, item) for item in items],
        total=len(items),
        offset=0,
        limit=limit,
    )


@router.get("/calendar", response_model=list[CalendarEventResponse])
def get_calendar_events(
    from_at: datetime | None = Query(default=None),
    to_at: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("work", "view")),
) -> list[CalendarEventResponse]:
    items, _ = svc.list_work_items(
        db,
        user,
        due_from=from_at,
        due_to=to_at,
        limit=500,
        sort_by="start_at",
    )
    return [
        CalendarEventResponse(
            id=item.id,
            title=item.title,
            work_item_type=item.work_item_type,
            status=svc.derive_effective_status(item),
            start_at=item.start_at or item.due_at,
            due_at=item.due_at,
            assigned_user_id=item.assigned_user_id,
            is_private=item.is_private,
        )
        for item in items
    ]


@router.get("/items", response_model=WorkItemListResponse)
def list_items(
    search: str | None = Query(default=None, max_length=255),
    assigned_user_id: UUID | None = Query(default=None),
    created_by_user_id: UUID | None = Query(default=None),
    work_item_type: WorkItemType | None = Query(default=None),
    status: WorkItemStatus | None = Query(default=None),
    priority: WorkItemPriority | None = Query(default=None),
    due_from: datetime | None = Query(default=None),
    due_to: datetime | None = Query(default=None),
    lead_id: UUID | None = Query(default=None),
    opportunity_id: UUID | None = Query(default=None),
    party_id: UUID | None = Query(default=None),
    proposal_id: UUID | None = Query(default=None),
    is_private: bool | None = Query(default=None),
    include_archived: bool = Query(default=False),
    sort_by: str = Query(default="due_at", max_length=50),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("work", "view")),
) -> WorkItemListResponse:
    items, total = svc.list_work_items(
        db,
        user,
        search=search,
        assigned_user_id=assigned_user_id,
        created_by_user_id=created_by_user_id,
        work_item_type=work_item_type,
        status=status,
        priority=priority,
        due_from=due_from,
        due_to=due_to,
        lead_id=lead_id,
        opportunity_id=opportunity_id,
        party_id=party_id,
        proposal_id=proposal_id,
        is_private=is_private,
        include_archived=include_archived,
        sort_by=sort_by,
        sort_dir=sort_dir,
        offset=offset,
        limit=limit,
    )
    return WorkItemListResponse(
        items=[_enrich(db, item) for item in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/items/{work_item_id}", response_model=WorkItemResponse)
def get_item(
    work_item_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("work", "view")),
) -> WorkItemResponse:
    try:
        item = svc.get_work_item_or_raise(db, work_item_id, user=user)
    except svc.WorkItemError as exc:
        raise _handle_error(exc) from exc
    return _enrich(db, item)


@router.post("/items", response_model=WorkItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: WorkItemCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("work", "create")),
) -> WorkItemResponse:
    try:
        item = svc.create_work_item(db, payload.model_dump(), actor=actor, request=request)
        db.commit()
        db.refresh(item)
    except svc.WorkItemError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return _enrich(db, item)


@router.patch("/items/{work_item_id}", response_model=WorkItemResponse)
def update_item(
    work_item_id: UUID,
    payload: WorkItemUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("work", "update")),
) -> WorkItemResponse:
    try:
        item = svc.get_work_item_or_raise(db, work_item_id, user=actor)
        item = svc.update_work_item(
            db,
            item,
            payload.model_dump(exclude_unset=True),
            actor=actor,
            request=request,
        )
        db.commit()
        db.refresh(item)
    except svc.WorkItemError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return _enrich(db, item)


@router.post("/items/{work_item_id}/status", response_model=WorkItemResponse)
def change_status(
    work_item_id: UUID,
    payload: StatusChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("work", "update")),
) -> WorkItemResponse:
    try:
        item = svc.get_work_item_or_raise(db, work_item_id, user=actor)
        item = svc.change_status(
            db,
            item,
            payload.status,
            actor=actor,
            reason=payload.reason,
            request=request,
        )
        db.commit()
        db.refresh(item)
    except svc.WorkItemError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return _enrich(db, item)


@router.post("/items/{work_item_id}/complete", response_model=WorkItemResponse)
def complete_item(
    work_item_id: UUID,
    payload: CompleteWorkItemRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("work", "complete")),
) -> WorkItemResponse:
    try:
        item = svc.get_work_item_or_raise(db, work_item_id, user=actor)
        item = svc.complete_work_item(
            db,
            item,
            actor=actor,
            outcome=payload.outcome,
            next_follow_up=payload.next_follow_up,
            request=request,
        )
        db.commit()
        db.refresh(item)
    except svc.WorkItemError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return _enrich(db, item)


@router.post("/items/{work_item_id}/cancel", response_model=WorkItemResponse)
def cancel_item(
    work_item_id: UUID,
    payload: StatusChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("work", "cancel")),
) -> WorkItemResponse:
    try:
        item = svc.get_work_item_or_raise(db, work_item_id, user=actor)
        item = svc.cancel_work_item(db, item, actor=actor, reason=payload.reason, request=request)
        db.commit()
        db.refresh(item)
    except svc.WorkItemError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return _enrich(db, item)


@router.post("/items/{work_item_id}/reschedule", response_model=WorkItemResponse)
def reschedule_item(
    work_item_id: UUID,
    payload: RescheduleRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("work", "update")),
) -> WorkItemResponse:
    try:
        item = svc.get_work_item_or_raise(db, work_item_id, user=actor)
        item = svc.reschedule_work_item(db, item, due_at=payload.due_at, actor=actor, request=request)
        db.commit()
        db.refresh(item)
    except svc.WorkItemError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return _enrich(db, item)


@router.delete("/items/{work_item_id}", response_model=WorkItemResponse)
def archive_item(
    work_item_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("work", "archive")),
) -> WorkItemResponse:
    try:
        item = svc.get_work_item_or_raise(db, work_item_id, user=actor, include_archived=True)
        item = svc.archive_work_item(db, item, actor=actor, request=request)
        db.commit()
        db.refresh(item)
    except svc.WorkItemError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return _enrich(db, item)


@router.post("/items/{work_item_id}/restore", response_model=WorkItemResponse)
def restore_item(
    work_item_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("work", "archive")),
) -> WorkItemResponse:
    try:
        item = svc.get_work_item_or_raise(db, work_item_id, user=actor, include_archived=True)
        item = svc.restore_work_item(db, item, actor=actor, request=request)
        db.commit()
        db.refresh(item)
    except svc.WorkItemError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return _enrich(db, item)


@router.post("/meetings", response_model=WorkItemResponse, status_code=status.HTTP_201_CREATED)
def create_meeting(
    payload: MeetingCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("sales", "manage_meetings")),
) -> WorkItemResponse:
    try:
        item, _ = svc.create_meeting(db, payload.model_dump(), actor=actor, request=request)
        db.commit()
        db.refresh(item)
    except svc.WorkItemError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return _enrich(db, item)


@router.patch("/meetings/{work_item_id}", response_model=WorkItemResponse)
def update_meeting(
    work_item_id: UUID,
    payload: MeetingUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("sales", "manage_meetings")),
) -> WorkItemResponse:
    try:
        item = svc.get_work_item_or_raise(db, work_item_id, user=actor)
        meeting = db.scalar(select(MeetingRecord).where(MeetingRecord.work_item_id == work_item_id))
        if meeting is None:
            raise svc.WorkItemError("work.errors.meeting_not_found", status_code=404)
        svc.update_meeting(db, item, meeting, payload.model_dump(exclude_unset=True), actor=actor, request=request)
        db.commit()
        db.refresh(item)
    except svc.WorkItemError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return _enrich(db, item)


@router.post("/meetings/{work_item_id}/complete", response_model=WorkItemResponse)
def complete_meeting(
    work_item_id: UUID,
    payload: MeetingCompleteRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("sales", "manage_meetings")),
) -> WorkItemResponse:
    try:
        item = svc.get_work_item_or_raise(db, work_item_id, user=actor)
        meeting = db.scalar(select(MeetingRecord).where(MeetingRecord.work_item_id == work_item_id))
        if meeting is None:
            raise svc.WorkItemError("work.errors.meeting_not_found", status_code=404)
        svc.complete_meeting(
            db,
            item,
            meeting,
            actor=actor,
            data=payload.model_dump(exclude_unset=True),
            request=request,
        )
        db.commit()
        db.refresh(item)
    except svc.WorkItemError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return _enrich(db, item)


@router.post("/follow-ups", response_model=WorkItemResponse, status_code=status.HTTP_201_CREATED)
def create_follow_up(
    payload: FollowUpCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("sales", "manage_followups")),
) -> WorkItemResponse:
    try:
        item, _ = svc.create_follow_up(db, payload.model_dump(), actor=actor, request=request)
        db.commit()
        db.refresh(item)
    except svc.WorkItemError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return _enrich(db, item)


@router.post("/follow-ups/{work_item_id}/complete", response_model=WorkItemResponse)
def complete_follow_up(
    work_item_id: UUID,
    payload: FollowUpCompleteRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("sales", "manage_followups")),
) -> WorkItemResponse:
    try:
        item = svc.get_work_item_or_raise(db, work_item_id, user=actor)
        record = db.scalar(select(FollowUpRecord).where(FollowUpRecord.work_item_id == work_item_id))
        if record is None:
            raise svc.WorkItemError("work.errors.follow_up_not_found", status_code=404)
        svc.complete_follow_up(
            db,
            item,
            record,
            actor=actor,
            data=payload.model_dump(exclude_unset=True),
            request=request,
        )
        db.commit()
        db.refresh(item)
    except svc.WorkItemError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return _enrich(db, item)


@router.get("/leads/{lead_id}/items", response_model=WorkItemListResponse)
def list_lead_items(
    lead_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("work", "view")),
) -> WorkItemListResponse:
    items = svc.list_for_lead(db, lead_id, user)
    return WorkItemListResponse(
        items=[_enrich(db, item) for item in items],
        total=len(items),
        offset=0,
        limit=len(items),
    )


@router.get("/opportunities/{opportunity_id}/items", response_model=WorkItemListResponse)
def list_opportunity_items(
    opportunity_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("work", "view")),
) -> WorkItemListResponse:
    items = svc.list_for_opportunity(db, opportunity_id, user)
    return WorkItemListResponse(
        items=[_enrich(db, item) for item in items],
        total=len(items),
        offset=0,
        limit=len(items),
    )
