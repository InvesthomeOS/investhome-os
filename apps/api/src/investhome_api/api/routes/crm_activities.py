"""CRM activity timeline, tasks, notes, and follow-up API routes."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.core.request_context import get_request_id
from investhome_api.db.session import get_db
from investhome_api.models.crm_activity import (
    CrmActivityCategory,
    CrmActivityEntityType,
    CrmActivityPriority,
    CrmActivityStatus,
    CrmActivityType,
    CrmActivityVisibility,
    CrmFollowUpReason,
    CrmTaskStatus,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_activities import (
    CrmActivityBulkUpdateRequest,
    CrmActivityBulkUpdateResponse,
    CrmActivityCommentInput,
    CrmActivityCreate,
    CrmActivityDashboardWidgets,
    CrmActivityDetail,
    CrmActivityListResponse,
    CrmActivityMutationResponse,
    CrmActivitySavedFilterCreate,
    CrmActivitySavedFilterResponse,
    CrmActivitySummary,
    CrmActivityUpdate,
    CrmCalendarEventCreate,
    CrmCalendarResponse,
    CrmFollowUpCreate,
    CrmFollowUpListResponse,
    CrmNoteCreate,
    CrmTaskCreate,
    CrmTaskListResponse,
    CrmTimelineResponse,
)
from investhome_api.services.crm.activity_service import (
    add_comment,
    archive_activity,
    bulk_update_activities,
    complete_follow_up,
    complete_task,
    create_activity,
    create_follow_up,
    create_saved_filter,
    create_workspace_event,
    create_workspace_note,
    create_workspace_task,
    delete_activity,
    duplicate_activity,
    get_activity_or_none,
    get_calendar,
    get_dashboard_widgets,
    get_timeline,
    list_activities,
    list_follow_ups,
    list_meetings,
    list_notes,
    list_saved_filters,
    list_tasks,
    restore_activity,
    update_activity,
)
from investhome_api.services.permission_service import user_has_permission

router = APIRouter(prefix="/crm", tags=["crm-activities"])


def _require_view_activities():
    async def _dependency(user: User = Depends(require_permission("crm", "read"))) -> User:
        if not user_has_permission(user, "crm", "view_activities") and not user_has_permission(
            user, "crm", "read"
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return _dependency


def _get_activity_or_404(db: Session, activity_id: UUID):
    activity = get_activity_or_none(db, activity_id)
    if activity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="crm.activities.errors.not_found")
    return activity


def _parse_activity_types(raw: str | None) -> list[CrmActivityType] | None:
    if not raw:
        return None
    return [CrmActivityType(value.strip()) for value in raw.split(",") if value.strip()]


def _parse_tags(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    return [tag.strip() for tag in raw.split(",") if tag.strip()]


@router.get("/timeline", response_model=CrmTimelineResponse)
def get_crm_timeline(
    search: str | None = Query(default=None, max_length=255),
    entity_type: CrmActivityEntityType | None = Query(default=None),
    entity_id: UUID | None = Query(default=None),
    contact_search: str | None = Query(default=None, max_length=255),
    project_group: str | None = Query(default=None, max_length=40),
    event_kind: str | None = Query(default=None, max_length=40),
    owner_id: UUID | None = Query(default=None),
    status_filter: CrmActivityStatus | None = Query(default=None, alias="status"),
    activity_type: CrmActivityType | None = Query(default=None),
    activity_types: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(_require_view_activities()),
) -> CrmTimelineResponse:
    items, meta = get_timeline(
        db,
        user,
        search=search,
        entity_type=entity_type,
        entity_id=entity_id,
        activity_type=activity_type,
        activity_types=_parse_activity_types(activity_types),
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
        contact_search=contact_search,
        project_group=project_group,
        event_kind=event_kind,
        owner_id=owner_id,
        status=status_filter,
    )
    return CrmTimelineResponse(items=items, request_id=get_request_id() or "", **meta)


@router.get("/activities", response_model=CrmActivityListResponse)
def get_activities(
    search: str | None = Query(default=None, max_length=255),
    entity_type: CrmActivityEntityType | None = Query(default=None),
    entity_id: UUID | None = Query(default=None),
    activity_type: CrmActivityType | None = Query(default=None),
    activity_types: str | None = Query(default=None),
    activity_category: CrmActivityCategory | None = Query(default=None),
    status_filter: CrmActivityStatus | None = Query(default=None, alias="status"),
    priority: CrmActivityPriority | None = Query(default=None),
    owner_id: UUID | None = Query(default=None),
    assigned_user_id: UUID | None = Query(default=None),
    created_by: UUID | None = Query(default=None),
    responsible_user_id: UUID | None = Query(default=None),
    visibility: CrmActivityVisibility | None = Query(default=None),
    tags: str | None = Query(default=None),
    has_attachments: bool | None = Query(default=None),
    completed: bool | None = Query(default=None),
    pending: bool | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    include_archived: bool = Query(default=False),
    sort_by: str = Query(default="created_at", max_length=40),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(_require_view_activities()),
) -> CrmActivityListResponse:
    items, meta = list_activities(
        db,
        user,
        search=search,
        entity_type=entity_type,
        entity_id=entity_id,
        activity_type=activity_type,
        activity_types=_parse_activity_types(activity_types),
        activity_category=activity_category,
        status=status_filter,
        priority=priority,
        owner_id=owner_id,
        assigned_user_id=assigned_user_id,
        created_by=created_by,
        responsible_user_id=responsible_user_id,
        visibility=visibility,
        tags=_parse_tags(tags),
        has_attachments=has_attachments,
        completed=completed,
        pending=pending,
        date_from=date_from,
        date_to=date_to,
        include_archived=include_archived,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
    return CrmActivityListResponse(items=items, request_id=get_request_id() or "", **meta)


@router.get("/activities/widgets", response_model=CrmActivityDashboardWidgets)
def get_activity_widgets(
    db: Session = Depends(get_db),
    user: User = Depends(_require_view_activities()),
) -> CrmActivityDashboardWidgets:
    return get_dashboard_widgets(db, user)


@router.get("/activities/saved-filters", response_model=list[CrmActivitySavedFilterResponse])
def get_saved_filters(
    db: Session = Depends(get_db),
    user: User = Depends(_require_view_activities()),
) -> list[CrmActivitySavedFilterResponse]:
    return list_saved_filters(db, user)


@router.post(
    "/activities/saved-filters",
    response_model=CrmActivitySavedFilterResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_saved_filter(
    body: CrmActivitySavedFilterCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "update")),
) -> CrmActivitySavedFilterResponse:
    return create_saved_filter(db, user, body)


@router.get("/activities/{activity_id}", response_model=CrmActivityDetail)
def get_activity(
    activity_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(_require_view_activities()),
) -> CrmActivityDetail:
    del user
    activity = _get_activity_or_404(db, activity_id)
    from investhome_api.services.crm.activity_service import _serialize_detail

    return _serialize_detail(activity)


@router.post("/activities", response_model=CrmActivityMutationResponse, status_code=status.HTTP_201_CREATED)
def post_activity(
    body: CrmActivityCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "create")),
) -> CrmActivityMutationResponse:
    return CrmActivityMutationResponse(activity=create_activity(db, user, body))


@router.put("/activities/{activity_id}", response_model=CrmActivityMutationResponse)
def put_activity(
    activity_id: UUID,
    body: CrmActivityUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "update")),
) -> CrmActivityMutationResponse:
    activity = _get_activity_or_404(db, activity_id)
    return CrmActivityMutationResponse(activity=update_activity(db, user, activity, body))


@router.post("/activities/{activity_id}/archive", response_model=CrmActivityMutationResponse)
def post_archive_activity(
    activity_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "archive")),
) -> CrmActivityMutationResponse:
    activity = _get_activity_or_404(db, activity_id)
    return CrmActivityMutationResponse(activity=archive_activity(db, user, activity))


@router.post("/activities/{activity_id}/restore", response_model=CrmActivityMutationResponse)
def post_restore_activity(
    activity_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "restore")),
) -> CrmActivityMutationResponse:
    activity = _get_activity_or_404(db, activity_id)
    return CrmActivityMutationResponse(activity=restore_activity(db, user, activity))


@router.delete("/activities/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_activity(
    activity_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "delete")),
) -> Response:
    activity = _get_activity_or_404(db, activity_id)
    delete_activity(db, activity)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/activities/{activity_id}/duplicate", response_model=CrmActivityMutationResponse)
def post_duplicate_activity(
    activity_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "create")),
) -> CrmActivityMutationResponse:
    activity = _get_activity_or_404(db, activity_id)
    return CrmActivityMutationResponse(activity=duplicate_activity(db, user, activity))


@router.post("/activities/{activity_id}/comments", response_model=CrmActivityMutationResponse)
def post_activity_comment(
    activity_id: UUID,
    body: CrmActivityCommentInput,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "update")),
) -> CrmActivityMutationResponse:
    activity = _get_activity_or_404(db, activity_id)
    return CrmActivityMutationResponse(
        activity=add_comment(
            db,
            user,
            activity,
            body.body,
            parent_id=body.parent_id,
            mentions=body.mentions,
        )
    )


@router.post("/activities/bulk-update", response_model=CrmActivityBulkUpdateResponse)
def post_bulk_update(
    body: CrmActivityBulkUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "bulk_actions")),
) -> CrmActivityBulkUpdateResponse:
    updated = bulk_update_activities(db, user, body)
    return CrmActivityBulkUpdateResponse(updated=updated)


@router.get("/tasks", response_model=CrmTaskListResponse)
def get_tasks(
    assigned_user_id: UUID | None = Query(default=None),
    my_tasks: bool = Query(default=False),
    team_tasks: bool = Query(default=False),
    task_status: CrmTaskStatus | None = Query(default=None, alias="status"),
    workspace_status: str | None = Query(default=None, max_length=40),
    entity_id: UUID | None = Query(default=None),
    contact_search: str | None = Query(default=None, max_length=255),
    project_group: str | None = Query(default=None, max_length=40),
    search: str | None = Query(default=None, max_length=255),
    priority: CrmActivityPriority | None = Query(default=None),
    due_from: datetime | None = Query(default=None),
    due_to: datetime | None = Query(default=None),
    due_bucket: str | None = Query(default=None, max_length=20),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(_require_view_activities()),
) -> CrmTaskListResponse:
    del team_tasks
    items, meta, counters = list_tasks(
        db,
        user,
        assigned_user_id=assigned_user_id,
        my_tasks=my_tasks,
        status=task_status,
        entity_id=entity_id,
        search=search,
        page=page,
        page_size=page_size,
        contact_search=contact_search,
        project_group=project_group,
        priority=priority,
        due_from=due_from,
        due_to=due_to,
        due_bucket=due_bucket,
        workspace_status=workspace_status,
    )
    return CrmTaskListResponse(items=items, request_id=get_request_id() or "", counters=counters, **meta)


@router.post("/tasks", response_model=CrmActivityMutationResponse, status_code=status.HTTP_201_CREATED)
def post_task(
    body: CrmTaskCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "manage_tasks")),
) -> CrmActivityMutationResponse:
    return CrmActivityMutationResponse(activity=create_workspace_task(db, user, body))


@router.post("/tasks/{activity_id}/complete", response_model=CrmActivityMutationResponse)
def post_complete_task(
    activity_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "manage_tasks")),
) -> CrmActivityMutationResponse:
    activity = _get_activity_or_404(db, activity_id)
    try:
        return CrmActivityMutationResponse(activity=complete_task(db, user, activity))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/notes", response_model=CrmActivityListResponse)
def get_notes(
    entity_type: CrmActivityEntityType | None = Query(default=None),
    entity_id: UUID | None = Query(default=None),
    search: str | None = Query(default=None, max_length=255),
    contact_search: str | None = Query(default=None, max_length=255),
    project_group: str | None = Query(default=None, max_length=40),
    assigned_user_id: UUID | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(_require_view_activities()),
) -> CrmActivityListResponse:
    del entity_type
    items, meta = list_notes(
        db,
        user,
        entity_id=entity_id,
        search=search,
        contact_search=contact_search,
        project_group=project_group,
        assigned_user_id=assigned_user_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return CrmActivityListResponse(items=items, request_id=get_request_id() or "", **meta)


@router.post("/notes", response_model=CrmActivityMutationResponse, status_code=status.HTTP_201_CREATED)
def post_note(
    body: CrmNoteCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "create")),
) -> CrmActivityMutationResponse:
    try:
        return CrmActivityMutationResponse(activity=create_workspace_note(db, user, body))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/meetings", response_model=CrmActivityListResponse)
def get_meetings(
    entity_type: CrmActivityEntityType | None = Query(default=None),
    entity_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(_require_view_activities()),
) -> CrmActivityListResponse:
    items, meta = list_meetings(
        db,
        user,
        entity_type=entity_type,
        entity_id=entity_id,
        page=page,
        page_size=page_size,
    )
    return CrmActivityListResponse(items=items, request_id=get_request_id() or "", **meta)


@router.post("/meetings", response_model=CrmActivityMutationResponse, status_code=status.HTTP_201_CREATED)
def post_meeting(
    body: CrmActivityCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "manage_meetings")),
) -> CrmActivityMutationResponse:
    activity_type = body.activity_type if body.activity_type in {
        CrmActivityType.MEETING,
        CrmActivityType.ZOOM_MEETING,
        CrmActivityType.TEAMS_MEETING,
    } else CrmActivityType.MEETING
    payload = body.model_copy(update={"activity_type": activity_type})
    return CrmActivityMutationResponse(activity=create_activity(db, user, payload))


@router.get("/follow-ups", response_model=CrmFollowUpListResponse)
def get_follow_ups(
    entity_type: CrmActivityEntityType | None = Query(default=None),
    entity_id: UUID | None = Query(default=None),
    reason: CrmFollowUpReason | None = Query(default=None),
    pending: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(_require_view_activities()),
) -> CrmFollowUpListResponse:
    items, meta = list_follow_ups(
        db,
        user,
        entity_type=entity_type,
        entity_id=entity_id,
        reason=reason,
        pending=pending,
        page=page,
        page_size=page_size,
    )
    return CrmFollowUpListResponse(items=items, **meta)


@router.post("/follow-ups", response_model=CrmActivityMutationResponse, status_code=status.HTTP_201_CREATED)
def post_follow_up(
    body: CrmFollowUpCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "manage_followups")),
) -> CrmActivityMutationResponse:
    return CrmActivityMutationResponse(activity=create_follow_up(db, user, body))


@router.post("/follow-ups/{activity_id}/complete", response_model=CrmActivityMutationResponse)
def post_complete_follow_up(
    activity_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "manage_followups")),
) -> CrmActivityMutationResponse:
    activity = _get_activity_or_404(db, activity_id)
    return CrmActivityMutationResponse(activity=complete_follow_up(db, user, activity))


@router.get("/calendar", response_model=CrmCalendarResponse)
def get_crm_calendar(
    start: datetime = Query(...),
    end: datetime = Query(...),
    assigned_user_id: UUID | None = Query(default=None),
    contact_search: str | None = Query(default=None, max_length=255),
    entity_id: UUID | None = Query(default=None),
    project_group: str | None = Query(default=None, max_length=40),
    event_kind: str | None = Query(default=None, max_length=40),
    db: Session = Depends(get_db),
    user: User = Depends(_require_view_activities()),
) -> CrmCalendarResponse:
    return get_calendar(
        db,
        user,
        start=start,
        end=end,
        assigned_user_id=assigned_user_id,
        contact_search=contact_search,
        entity_id=entity_id,
        project_group=project_group,
        event_kind=event_kind,
    )


@router.post("/calendar/events", response_model=CrmActivityMutationResponse, status_code=status.HTTP_201_CREATED)
def post_calendar_event(
    body: CrmCalendarEventCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "manage_tasks")),
) -> CrmActivityMutationResponse:
    return CrmActivityMutationResponse(activity=create_workspace_event(db, user, body))
