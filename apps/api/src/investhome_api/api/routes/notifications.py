"""Notification API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import get_current_user, require_permission
from investhome_api.db.session import get_db
from investhome_api.models.notification import NotificationPriority, NotificationStatus
from investhome_api.models.user_auth import User
from investhome_api.schemas.notification import (
    NotificationListResponse,
    NotificationMarkReadResponse,
    NotificationResponse,
    NotificationSummaryResponse,
    NotificationUnreadCountResponse,
)
from investhome_api.services.notification_generator import sync_notifications_for_user
from investhome_api.services.notification_service import (
    dismiss_notification,
    enrich_notification,
    get_notification,
    get_notification_summary,
    get_unread_count,
    list_notifications,
    mark_all_read,
    mark_read,
    pagination_meta,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
def list_user_notifications(
    notification_status: NotificationStatus | None = Query(default=None, alias="status"),
    priority: NotificationPriority | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sync: bool = Query(default=True),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("notifications", "view")),
) -> NotificationListResponse:
    if sync:
        sync_notifications_for_user(db, user)
        db.commit()
    items, total, unread = list_notifications(
        db,
        user,
        status=notification_status,
        priority=priority,
        page=page,
        page_size=page_size,
    )
    meta = pagination_meta(total, page, page_size)
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(enrich_notification(item)) for item in items],
        unread_count=unread,
        **meta,
    )


@router.get("/unread-count", response_model=NotificationUnreadCountResponse)
def unread_count(
    sync: bool = Query(default=True),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("notifications", "view")),
) -> NotificationUnreadCountResponse:
    if sync:
        sync_notifications_for_user(db, user)
        db.commit()
    count, highest = get_unread_count(db, user)
    return NotificationUnreadCountResponse(unread_count=count, highest_priority=highest)


@router.get("/summary", response_model=NotificationSummaryResponse)
def notification_summary(
    sync: bool = Query(default=True),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("notifications", "view")),
) -> NotificationSummaryResponse:
    if sync:
        sync_notifications_for_user(db, user)
        db.commit()
    summary = get_notification_summary(db, user)
    return NotificationSummaryResponse(**summary)


@router.get("/{notification_id}", response_model=NotificationResponse)
def get_notification_detail(
    notification_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("notifications", "view")),
) -> NotificationResponse:
    notification = get_notification(db, user, notification_id)
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return NotificationResponse.model_validate(enrich_notification(notification))


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("notifications", "view")),
) -> NotificationResponse:
    notification = mark_read(db, user, notification_id)
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    db.commit()
    return NotificationResponse.model_validate(enrich_notification(notification))


@router.post("/read-all", response_model=NotificationMarkReadResponse)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("notifications", "view")),
) -> NotificationMarkReadResponse:
    updated = mark_all_read(db, user)
    db.commit()
    return NotificationMarkReadResponse(updated=updated)


@router.post("/{notification_id}/dismiss", response_model=NotificationResponse)
def dismiss_user_notification(
    notification_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("notifications", "view")),
) -> NotificationResponse:
    notification = dismiss_notification(db, user, notification_id)
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    db.commit()
    return NotificationResponse.model_validate(enrich_notification(notification))
