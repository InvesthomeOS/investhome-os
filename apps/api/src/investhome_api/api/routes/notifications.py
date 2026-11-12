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
    NotificationPreferenceListResponse,
    NotificationPreferenceUpdate,
    NotificationResponse,
    NotificationSummaryResponse,
    NotificationUnreadCountResponse,
)
from investhome_api.services.user_notifications import list_preference_state, save_preference_state
from investhome_api.services.notification_service import (
    dismiss_all,
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


def _release_read(db: Session) -> None:
    """End a SELECT-only transaction before the response is sent."""
    if db.in_transaction():
        db.rollback()


@router.get("", response_model=NotificationListResponse)
def list_user_notifications(
    notification_status: NotificationStatus | None = Query(default=None, alias="status"),
    priority: NotificationPriority | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("notifications", "view")),
) -> NotificationListResponse:
    items, total, unread = list_notifications(
        db,
        user,
        status=notification_status,
        priority=priority,
        page=page,
        page_size=page_size,
    )
    meta = pagination_meta(total, page, page_size)
    payload = NotificationListResponse(
        items=[NotificationResponse.model_validate(enrich_notification(item)) for item in items],
        unread_count=unread,
        **meta,
    )
    _release_read(db)
    return payload


@router.get("/unread-count", response_model=NotificationUnreadCountResponse)
def unread_count(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("notifications", "view")),
) -> NotificationUnreadCountResponse:
    count, highest = get_unread_count(db, user)
    payload = NotificationUnreadCountResponse(unread_count=count, highest_priority=highest)
    _release_read(db)
    return payload


@router.get("/summary", response_model=NotificationSummaryResponse)
def notification_summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("notifications", "view")),
) -> NotificationSummaryResponse:
    summary = get_notification_summary(db, user)
    payload = NotificationSummaryResponse(**summary)
    _release_read(db)
    return payload


@router.get("/preferences", response_model=NotificationPreferenceListResponse)
def get_notification_preferences(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("notifications", "view")),
) -> NotificationPreferenceListResponse:
    return NotificationPreferenceListResponse(items=list_preference_state(db, user.id))


@router.put("/preferences", response_model=NotificationPreferenceListResponse)
def put_notification_preferences(
    body: NotificationPreferenceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("notifications", "view")),
) -> NotificationPreferenceListResponse:
    items = save_preference_state(db, user.id, [item.model_dump() for item in body.items])
    db.commit()
    return NotificationPreferenceListResponse(items=items)


@router.post("/dismiss-all", response_model=NotificationMarkReadResponse)
def dismiss_all_notifications(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("notifications", "view")),
) -> NotificationMarkReadResponse:
    updated = dismiss_all(db, user)
    db.commit()
    return NotificationMarkReadResponse(updated=updated)


@router.get("/push-config")
def get_push_config(
    user: User = Depends(require_permission("notifications", "view")),
) -> dict[str, object]:
    del user
    from investhome_api.services.web_push import push_configuration

    return push_configuration()


@router.post("/push-subscriptions")
def put_push_subscription(
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("notifications", "view")),
) -> dict[str, bool]:
    from investhome_api.services.web_push import save_push_subscription

    save_push_subscription(db, user, body)
    db.commit()
    return {"saved": True}


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
