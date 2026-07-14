"""Activity log API routes (read-only, append-only audit trail)."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import get_current_user, require_permission
from investhome_api.db.session import get_db
from investhome_api.models.activity import ActivityAction, ActivityEntityType, ActivitySource
from investhome_api.models.user_auth import User
from investhome_api.schemas.activity import ActivityListResponse, ActivityLogResponse
from investhome_api.services.activity_service import (
    ENTITY_LINK_MODULES,
    get_activity_entry,
    list_activities,
    list_entity_activity,
    pagination_meta,
    resolve_entity_label,
)

router = APIRouter(prefix="/activity", tags=["activity"])


def _serialize_entry(entry) -> ActivityLogResponse:
    metadata = entry.metadata_json or {}
    return ActivityLogResponse.model_validate(
        {
            **ActivityLogResponse.model_validate(entry).model_dump(),
            "entity_label": resolve_entity_label(metadata),
            "link_module": ENTITY_LINK_MODULES.get(entry.entity_type),
        }
    )


@router.get("", response_model=ActivityListResponse)
def list_activity_logs(
    search: str | None = Query(default=None, max_length=255),
    entity_type: ActivityEntityType | None = None,
    entity_id: UUID | None = None,
    actor_user_id: UUID | None = None,
    action: ActivityAction | None = None,
    source: ActivitySource | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("activity", "view")),
) -> ActivityListResponse:
    items, total = list_activities(
        db,
        user,
        search=search,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        action=action,
        source=source,
        date_from=date_from,
        date_to=_end_of_day(date_to) if date_to else None,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    meta = pagination_meta(total, page, page_size)
    return ActivityListResponse(
        items=[_serialize_entry(item) for item in items],
        **meta,
    )


@router.get("/entity/{entity_type}/{entity_id}", response_model=ActivityListResponse)
def list_activity_for_entity(
    entity_type: ActivityEntityType,
    entity_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ActivityListResponse:
    items = list_entity_activity(
        db,
        user,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
    )
    return ActivityListResponse(
        items=[_serialize_entry(item) for item in items],
        total=len(items),
        page=1,
        page_size=limit,
        pages=1 if items else 0,
    )


@router.get("/user/{user_id}", response_model=ActivityListResponse)
def list_activity_for_user(
    user_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("activity", "view")),
) -> ActivityListResponse:
    items, total = list_activities(
        db,
        user,
        actor_user_id=user_id,
        page=page,
        page_size=page_size,
    )
    meta = pagination_meta(total, page, page_size)
    return ActivityListResponse(
        items=[_serialize_entry(item) for item in items],
        **meta,
    )


@router.get("/{activity_id}", response_model=ActivityLogResponse)
def get_activity_log(
    activity_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("activity", "view")),
) -> ActivityLogResponse:
    entry = get_activity_entry(db, user, activity_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")
    return _serialize_entry(entry)


def _end_of_day(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.replace(hour=23, minute=59, second=59, microsecond=999999)
