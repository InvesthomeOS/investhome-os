"""CRM activity timeline, tasks, notes, and follow-up API routes."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
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
    ActivityValidationError,
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
    user_can_view_activity,
)

router = APIRouter(prefix="/crm", tags=["crm-activities"])


def _require_view_activities():
    return require_permission("crm", "view_activities")


def _get_activity_or_404(db: Session, activity_id: UUID):
    activity = get_activity_or_none(db, activity_id)
    if activity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="crm.activities.errors.not_found",
        )
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
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(_require_view_activities())],
    search: Annotated[str | None, Query(max_length=255)] = None,
    entity_type: Annotated[CrmActivityEntityType | None, Query()] = None,
    entity_id: Annotated[UUID | None, Query()] = None,
    contact_search: Annotated[str | None, Query(max_length=255)] = None,
    project_group: Annotated[str | None, Query(max_length=40)] = None,
    event_kind: Annotated[str | None, Query(max_length=40)] = None,
    owner_id: Annotated[UUID | None, Query()] = None,
    status_filter: Annotated[CrmActivityStatus | None, Query(alias="status")] = None,
    activity_type: Annotated[CrmActivityType | None, Query()] = None,
    activity_types: Annotated[str | None, Query()] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 30,
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
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(_require_view_activities())],
    search: Annotated[str | None, Query(max_length=255)] = None,
    entity_type: Annotated[CrmActivityEntityType | None, Query()] = None,
    entity_id: Annotated[UUID | None, Query()] = None,
    activity_type: Annotated[CrmActivityType | None, Query()] = None,
    activity_types: Annotated[str | None, Query()] = None,
    activity_category: Annotated[CrmActivityCategory | None, Query()] = None,
    status_filter: Annotated[CrmActivityStatus | None, Query(alias="status")] = None,
    priority: Annotated[CrmActivityPriority | None, Query()] = None,
    owner_id: Annotated[UUID | None, Query()] = None,
    assigned_user_id: Annotated[UUID | None, Query()] = None,
    created_by: Annotated[UUID | None, Query()] = None,
    responsible_user_id: Annotated[UUID | None, Query()] = None,
    visibility: Annotated[CrmActivityVisibility | None, Query()] = None,
    tags: Annotated[str | None, Query()] = None,
    has_attachments: Annotated[bool | None, Query()] = None,
    completed: Annotated[bool | None, Query()] = None,
    pending: Annotated[bool | None, Query()] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    include_archived: Annotated[bool, Query()] = False,
    sort_by: Annotated[str, Query(max_length=40)] = "created_at",
    sort_dir: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
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
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(_require_view_activities())],
) -> CrmActivityDashboardWidgets:
    return get_dashboard_widgets(db, user)


@router.get("/activities/saved-filters", response_model=list[CrmActivitySavedFilterResponse])
def get_saved_filters(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(_require_view_activities())],
) -> list[CrmActivitySavedFilterResponse]:
    return list_saved_filters(db, user)


@router.post(
    "/activities/saved-filters",
    response_model=CrmActivitySavedFilterResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_saved_filter(
    body: CrmActivitySavedFilterCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "update"))],
) -> CrmActivitySavedFilterResponse:
    return create_saved_filter(db, user, body)


@router.get("/activities/{activity_id}", response_model=CrmActivityDetail)
def get_activity(
    activity_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(_require_view_activities())],
) -> CrmActivityDetail:
    from investhome_api.services.crm.activity_service import _serialize_detail

    activity = get_activity_or_none(db, activity_id)
    if activity is None or not user_can_view_activity(user, activity):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="crm.activities.errors.not_found",
        )
    return _serialize_detail(activity)


@router.post(
    "/activities",
    response_model=CrmActivityMutationResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_activity(
    body: CrmActivityCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "create"))],
) -> CrmActivityMutationResponse:
    return CrmActivityMutationResponse(activity=create_activity(db, user, body))


@router.put("/activities/{activity_id}", response_model=CrmActivityMutationResponse)
def put_activity(
    activity_id: UUID,
    body: CrmActivityUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "update"))],
) -> CrmActivityMutationResponse:
    activity = _get_activity_or_404(db, activity_id)
    return CrmActivityMutationResponse(activity=update_activity(db, user, activity, body))


@router.post("/activities/{activity_id}/archive", response_model=CrmActivityMutationResponse)
def post_archive_activity(
    activity_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "archive"))],
) -> CrmActivityMutationResponse:
    activity = _get_activity_or_404(db, activity_id)
    return CrmActivityMutationResponse(activity=archive_activity(db, user, activity))


@router.post("/activities/{activity_id}/restore", response_model=CrmActivityMutationResponse)
def post_restore_activity(
    activity_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "restore"))],
) -> CrmActivityMutationResponse:
    activity = _get_activity_or_404(db, activity_id)
    return CrmActivityMutationResponse(activity=restore_activity(db, user, activity))


@router.delete("/activities/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_activity(
    activity_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "delete"))],
) -> Response:
    activity = _get_activity_or_404(db, activity_id)
    delete_activity(db, activity)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/activities/{activity_id}/duplicate", response_model=CrmActivityMutationResponse)
def post_duplicate_activity(
    activity_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "create"))],
) -> CrmActivityMutationResponse:
    activity = _get_activity_or_404(db, activity_id)
    return CrmActivityMutationResponse(activity=duplicate_activity(db, user, activity))


@router.post("/activities/{activity_id}/comments", response_model=CrmActivityMutationResponse)
def post_activity_comment(
    activity_id: UUID,
    body: CrmActivityCommentInput,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "update"))],
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
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "bulk_actions"))],
) -> CrmActivityBulkUpdateResponse:
    updated = bulk_update_activities(db, user, body)
    return CrmActivityBulkUpdateResponse(updated=updated)


@router.get("/tasks", response_model=CrmTaskListResponse)
def get_tasks(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(_require_view_activities())],
    assigned_user_id: Annotated[UUID | None, Query()] = None,
    my_tasks: Annotated[bool, Query()] = False,
    team_tasks: Annotated[bool, Query()] = False,
    task_status: Annotated[CrmTaskStatus | None, Query(alias="status")] = None,
    workspace_status: Annotated[str | None, Query(max_length=40)] = None,
    entity_id: Annotated[UUID | None, Query()] = None,
    contact_search: Annotated[str | None, Query(max_length=255)] = None,
    project_group: Annotated[str | None, Query(max_length=40)] = None,
    search: Annotated[str | None, Query(max_length=255)] = None,
    priority: Annotated[CrmActivityPriority | None, Query()] = None,
    due_from: Annotated[datetime | None, Query()] = None,
    due_to: Annotated[datetime | None, Query()] = None,
    due_bucket: Annotated[str | None, Query(max_length=20)] = None,
    lead_id: Annotated[UUID | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 25,
    sort_by: Annotated[str, Query(max_length=40)] = "due_date",
    sort_dir: Annotated[str, Query(max_length=4)] = "asc",
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
        lead_id=lead_id,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return CrmTaskListResponse(
        items=items,
        request_id=get_request_id() or "",
        counters=counters,
        **meta,
    )


@router.post(
    "/tasks",
    response_model=CrmActivityMutationResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_task(
    body: CrmTaskCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "manage_tasks"))],
) -> CrmActivityMutationResponse:
    try:
        return CrmActivityMutationResponse(activity=create_workspace_task(db, user, body))
    except ActivityValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/tasks/{activity_id}/complete", response_model=CrmActivityMutationResponse)
def post_complete_task(
    activity_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "manage_tasks"))],
) -> CrmActivityMutationResponse:
    activity = _get_activity_or_404(db, activity_id)
    try:
        return CrmActivityMutationResponse(activity=complete_task(db, user, activity))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/notes", response_model=CrmActivityListResponse)
def get_notes(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(_require_view_activities())],
    entity_type: Annotated[CrmActivityEntityType | None, Query()] = None,
    entity_id: Annotated[UUID | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=255)] = None,
    contact_search: Annotated[str | None, Query(max_length=255)] = None,
    project_group: Annotated[str | None, Query(max_length=40)] = None,
    assigned_user_id: Annotated[UUID | None, Query()] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
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


@router.post(
    "/notes",
    response_model=CrmActivityMutationResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_note(
    body: CrmNoteCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "create"))],
) -> CrmActivityMutationResponse:
    try:
        return CrmActivityMutationResponse(activity=create_workspace_note(db, user, body))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/meetings", response_model=CrmActivityListResponse)
def get_meetings(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(_require_view_activities())],
    entity_type: Annotated[CrmActivityEntityType | None, Query()] = None,
    entity_id: Annotated[UUID | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
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


@router.post(
    "/meetings",
    response_model=CrmActivityMutationResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_meeting(
    body: CrmActivityCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "manage_meetings"))],
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
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(_require_view_activities())],
    entity_type: Annotated[CrmActivityEntityType | None, Query()] = None,
    entity_id: Annotated[UUID | None, Query()] = None,
    reason: Annotated[CrmFollowUpReason | None, Query()] = None,
    pending: Annotated[bool, Query()] = True,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
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


@router.post(
    "/follow-ups",
    response_model=CrmActivityMutationResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_follow_up(
    body: CrmFollowUpCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "manage_followups"))],
) -> CrmActivityMutationResponse:
    return CrmActivityMutationResponse(activity=create_follow_up(db, user, body))


@router.post("/follow-ups/{activity_id}/complete", response_model=CrmActivityMutationResponse)
def post_complete_follow_up(
    activity_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "manage_followups"))],
) -> CrmActivityMutationResponse:
    activity = _get_activity_or_404(db, activity_id)
    return CrmActivityMutationResponse(activity=complete_follow_up(db, user, activity))


@router.get("/calendar", response_model=CrmCalendarResponse)
def get_crm_calendar(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(_require_view_activities())],
    start: Annotated[datetime, Query()],
    end: Annotated[datetime, Query()],
    assigned_user_id: Annotated[UUID | None, Query()] = None,
    contact_search: Annotated[str | None, Query(max_length=255)] = None,
    entity_id: Annotated[UUID | None, Query()] = None,
    project_group: Annotated[str | None, Query(max_length=40)] = None,
    event_kind: Annotated[str | None, Query(max_length=40)] = None,
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


@router.post(
    "/calendar/events",
    response_model=CrmActivityMutationResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_calendar_event(
    body: CrmCalendarEventCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "manage_tasks"))],
) -> CrmActivityMutationResponse:
    return CrmActivityMutationResponse(activity=create_workspace_event(db, user, body))
