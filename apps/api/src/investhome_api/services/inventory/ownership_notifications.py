"""Ownership transfer notifications."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from investhome_api.models.inventory import OwnershipTransferRequest
from investhome_api.models.notification import NotificationPriority, NotificationSource, NotificationType
from investhome_api.models.user_auth import User
from investhome_api.services.notification_service import create_notification
from investhome_api.services.permission_service import user_has_permission


def _notify_users(
    db: Session,
    *,
    users: list[User],
    rule_key: str,
    title_key: str,
    message_key: str,
    request: OwnershipTransferRequest,
    metadata: dict | None = None,
    priority: NotificationPriority = NotificationPriority.MEDIUM,
    notification_type: NotificationType = NotificationType.SYSTEM,
) -> None:
    seen: set[str] = set()
    for user in users:
        if str(user.id) in seen:
            continue
        seen.add(str(user.id))
        create_notification(
            db,
            recipient_user_id=user.id,
            type=notification_type,
            priority=priority,
            title_key=title_key,
            message_key=message_key,
            rule_key=rule_key,
            related_entity_type="ownership_transfer_request",
            related_entity_id=request.id,
            metadata=metadata or {},
            source=NotificationSource.AUTOMATION,
            is_demo=request.is_demo,
        )


def collect_ownership_reviewers(db: Session) -> list[User]:
    from sqlalchemy import select

    from investhome_api.models.user_auth import Permission, Role, RolePermission, UserRole

    return list(
        db.scalars(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .join(RolePermission, RolePermission.role_id == Role.id)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .where(
                Permission.resource == "inventory",
                Permission.action == "review_ownership_change",
                User.archived_at.is_(None),
            )
            .distinct()
        ).all()
    )


def notify_transfer_submitted(
    db: Session,
    request: OwnershipTransferRequest,
    *,
    display_id: str,
    requester: User,
) -> None:
    reviewers = collect_ownership_reviewers(db)
    _notify_users(
        db,
        users=reviewers,
        rule_key="inventory.ownership_submitted",
        title_key="notifications.inventory.ownership_submitted.title",
        message_key="notifications.inventory.ownership_submitted.message",
        request=request,
        metadata={"display_id": display_id, "requester": requester.email or str(requester.id)},
    )


def notify_transfer_approved(
    db: Session,
    request: OwnershipTransferRequest,
    requester: User,
    *,
    display_id: str,
    scheduled: bool = False,
) -> None:
    rule = "inventory.ownership_scheduled" if scheduled else "inventory.ownership_approved"
    title = (
        "notifications.inventory.ownership_scheduled.title"
        if scheduled
        else "notifications.inventory.ownership_approved.title"
    )
    message = (
        "notifications.inventory.ownership_scheduled.message"
        if scheduled
        else "notifications.inventory.ownership_approved.message"
    )
    _notify_users(
        db,
        users=[requester],
        rule_key=rule,
        title_key=title,
        message_key=message,
        request=request,
        metadata={"display_id": display_id, "effective_date": request.effective_date.isoformat()},
    )


def notify_transfer_rejected(
    db: Session,
    request: OwnershipTransferRequest,
    requester: User,
    *,
    display_id: str,
) -> None:
    _notify_users(
        db,
        users=[requester],
        rule_key="inventory.ownership_rejected",
        title_key="notifications.inventory.ownership_rejected.title",
        message_key="notifications.inventory.ownership_rejected.message",
        request=request,
        metadata={"display_id": display_id},
    )


def notify_transfer_revision(
    db: Session,
    request: OwnershipTransferRequest,
    requester: User,
    *,
    display_id: str,
) -> None:
    _notify_users(
        db,
        users=[requester],
        rule_key="inventory.ownership_revision_requested",
        title_key="notifications.inventory.ownership_revision_requested.title",
        message_key="notifications.inventory.ownership_revision_requested.message",
        request=request,
        metadata={"display_id": display_id},
    )


def notify_stale_conflict(
    db: Session,
    request: OwnershipTransferRequest,
    users: list[User],
    *,
    display_id: str,
) -> None:
    _notify_users(
        db,
        users=users,
        rule_key="inventory.ownership_stale_conflict",
        title_key="notifications.inventory.ownership_stale_conflict.title",
        message_key="notifications.inventory.ownership_stale_conflict.message",
        request=request,
        metadata={"display_id": display_id},
    )


def notify_scheduled_applied(
    db: Session,
    request: OwnershipTransferRequest,
    users: list[User],
    *,
    display_id: str,
) -> None:
    _notify_users(
        db,
        users=users,
        rule_key="inventory.ownership_scheduled_applied",
        title_key="notifications.inventory.ownership_scheduled_applied.title",
        message_key="notifications.inventory.ownership_scheduled_applied.message",
        request=request,
        metadata={"display_id": display_id},
    )


def notify_scheduled_failed(
    db: Session,
    request: OwnershipTransferRequest,
    users: list[User],
    *,
    display_id: str,
) -> None:
    _notify_users(
        db,
        users=users,
        rule_key="inventory.ownership_scheduled_failed",
        title_key="notifications.inventory.ownership_scheduled_failed.title",
        message_key="notifications.inventory.ownership_scheduled_failed.message",
        request=request,
        metadata={"display_id": display_id},
    )


def notify_finance_reviewers_if_legal(
    db: Session,
    request: OwnershipTransferRequest,
    *,
    display_id: str,
) -> None:
    from investhome_api.services.inventory.ownership_config import transfer_affects_legal

    if not transfer_affects_legal(request.transfer_type):
        return
    reviewers = [
        u
        for u in collect_ownership_reviewers(db)
        if user_has_permission(u, "inventory", "approve_ownership_change")
    ]
    if not reviewers:
        return
    _notify_users(
        db,
        users=reviewers,
        rule_key="inventory.ownership_approval_required",
        title_key="notifications.inventory.ownership_approval_required.title",
        message_key="notifications.inventory.ownership_approval_required.message",
        request=request,
        metadata={"display_id": display_id},
    )
