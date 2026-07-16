"""Notification helpers for inventory pricing."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from investhome_api.models.inventory import InventoryAsset, PriceChangeRequest, PriceRequestStatus
from investhome_api.models.notification import NotificationPriority, NotificationSource, NotificationType
from investhome_api.models.user_auth import User
from investhome_api.services.notification_service import create_notification
from investhome_api.services.permission_service import user_has_permission


def _notify(
    db: Session,
    *,
    user_id: UUID,
    rule_key: str,
    title_key: str,
    message_key: str,
    request: PriceChangeRequest,
    metadata: dict | None = None,
    priority: NotificationPriority = NotificationPriority.MEDIUM,
    notification_type: NotificationType = NotificationType.SYSTEM,
) -> None:
    create_notification(
        db,
        recipient_user_id=user_id,
        type=notification_type,
        priority=priority,
        title_key=title_key,
        message_key=message_key,
        rule_key=rule_key,
        related_entity_type="price_change_request",
        related_entity_id=request.id,
        metadata=metadata or {},
        source=NotificationSource.AUTOMATION,
        is_demo=request.is_demo,
    )


def notify_price_draft_created(
    db: Session,
    request: PriceChangeRequest,
    *,
    display_id: str,
) -> None:
    _notify(
        db,
        user_id=request.requested_by_user_id,
        rule_key="inventory.price.draft_created",
        title_key="notifications.inventory.price_draft_created.title",
        message_key="notifications.inventory.price_draft_created.message",
        request=request,
        metadata={"display_id": display_id, "price_type": request.price_type.value},
    )


def notify_price_submitted(
    db: Session,
    request: PriceChangeRequest,
    users: list[User],
    *,
    display_id: str,
) -> None:
    for user in users:
        if not user_has_permission(user, "inventory", "review_price_change"):
            continue
        if user.id == request.requested_by_user_id:
            continue
        _notify(
            db,
            user_id=user.id,
            rule_key="inventory.price_pending",
            title_key="notifications.inventory.price_pending.title",
            message_key="notifications.inventory.price_pending.message",
            request=request,
            metadata={"display_id": display_id, "price_type": request.price_type.value},
            priority=NotificationPriority.HIGH,
            notification_type=NotificationType.APPROVAL,
        )


def notify_price_approved(
    db: Session,
    request: PriceChangeRequest,
    *,
    display_id: str,
) -> None:
    _notify(
        db,
        user_id=request.requested_by_user_id,
        rule_key="inventory.price_approved",
        title_key="notifications.inventory.price_approved.title",
        message_key="notifications.inventory.price_approved.message",
        request=request,
        metadata={"display_id": display_id, "price_type": request.price_type.value},
    )


def notify_price_rejected(
    db: Session,
    request: PriceChangeRequest,
    *,
    display_id: str,
) -> None:
    _notify(
        db,
        user_id=request.requested_by_user_id,
        rule_key="inventory.price_rejected",
        title_key="notifications.inventory.price_rejected.title",
        message_key="notifications.inventory.price_rejected.message",
        request=request,
        metadata={"display_id": display_id},
        notification_type=NotificationType.WARNING,
    )


def notify_revision_requested(
    db: Session,
    request: PriceChangeRequest,
    *,
    display_id: str,
) -> None:
    _notify(
        db,
        user_id=request.requested_by_user_id,
        rule_key="inventory.price_revision_requested",
        title_key="notifications.inventory.price_revision_requested.title",
        message_key="notifications.inventory.price_revision_requested.message",
        request=request,
        metadata={"display_id": display_id},
        notification_type=NotificationType.APPROVAL,
    )


def notify_price_withdrawn(
    db: Session,
    request: PriceChangeRequest,
    *,
    display_id: str,
    reviewer_id: UUID | None = None,
) -> None:
    if reviewer_id is None:
        return
    _notify(
        db,
        user_id=reviewer_id,
        rule_key="inventory.price_withdrawn",
        title_key="notifications.inventory.price_withdrawn.title",
        message_key="notifications.inventory.price_withdrawn.message",
        request=request,
        metadata={"display_id": display_id},
    )


def notify_stale_conflict(
    db: Session,
    request: PriceChangeRequest,
    *,
    display_id: str,
) -> None:
    _notify(
        db,
        user_id=request.requested_by_user_id,
        rule_key="inventory.price_stale_conflict",
        title_key="notifications.inventory.price_stale_conflict.title",
        message_key="notifications.inventory.price_stale_conflict.message",
        request=request,
        metadata={"display_id": display_id},
        priority=NotificationPriority.HIGH,
        notification_type=NotificationType.WARNING,
    )


def notify_price_activated(
    db: Session,
    request: PriceChangeRequest,
    users: list[User],
    *,
    display_id: str,
    asset: InventoryAsset,
) -> None:
    for user in users:
        if not user_has_permission(user, "inventory", "view_price"):
            continue
        if user.id == request.requested_by_user_id:
            continue
        _notify(
            db,
            user_id=user.id,
            rule_key="inventory.price_effective",
            title_key="notifications.inventory.price_effective.title",
            message_key="notifications.inventory.price_effective.message",
            request=request,
            metadata={
                "display_id": display_id,
                "price_type": request.price_type.value,
                "currency": asset.currency,
            },
        )


def collect_finance_reviewers(db: Session) -> list[User]:
    from sqlalchemy import select

    from investhome_api.models.user_auth import Role, UserRole

    rows = db.scalars(
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.code.in_(["finance", "executive", "operations"]))
    ).all()
    return list(rows)
