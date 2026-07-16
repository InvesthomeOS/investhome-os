"""Assignment workflow notifications."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.inventory import InventoryAssetAssignmentRequest
from investhome_api.models.notification import NotificationPriority, NotificationSource, NotificationType
from investhome_api.models.user_auth import Permission, Role, RolePermission, User, UserRole
from investhome_api.services.notification_service import create_notification


def _notify_users(
    db: Session,
    *,
    users: list[User],
    rule_key: str,
    title_key: str,
    message_key: str,
    entity_type: str,
    entity_id: str,
    metadata: dict | None = None,
) -> None:
    seen: set[str] = set()
    for user in users:
        if str(user.id) in seen:
            continue
        seen.add(str(user.id))
        create_notification(
            db,
            recipient_user_id=user.id,
            type=NotificationType.SYSTEM,
            priority=NotificationPriority.MEDIUM,
            rule_key=rule_key,
            title_key=title_key,
            message_key=message_key,
            related_entity_type=entity_type,
            related_entity_id=UUID(entity_id) if isinstance(entity_id, str) else entity_id,
            metadata=metadata or {},
            source=NotificationSource.AUTOMATION,
        )


def collect_assignment_reviewers(db: Session) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .join(RolePermission, RolePermission.role_id == Role.id)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .where(
                Permission.resource == "inventory",
                Permission.action == "review_assignment",
                User.archived_at.is_(None),
            )
            .distinct()
        ).all()
    )


def notify_assignment_submitted(
    db: Session,
    request: InventoryAssetAssignmentRequest,
    *,
    display_id: str,
    requester: User,
) -> None:
    reviewers = collect_assignment_reviewers(db)
    _notify_users(
        db,
        users=reviewers,
        rule_key="inventory.assignment_submitted",
        title_key="notifications.inventory.assignment_submitted.title",
        message_key="notifications.inventory.assignment_submitted.message",
        entity_type="inventory_asset_assignment_request",
        entity_id=str(request.id),
        metadata={"display_id": display_id, "requester": requester.email or str(requester.id)},
    )


def notify_assignment_approved(
    db: Session,
    request: InventoryAssetAssignmentRequest,
    requester: User,
    *,
    display_id: str,
    scheduled: bool = False,
) -> None:
    rule = "inventory.assignment_scheduled" if scheduled else "inventory.assignment_approved"
    title = (
        "notifications.inventory.assignment_scheduled.title"
        if scheduled
        else "notifications.inventory.assignment_approved.title"
    )
    message = (
        "notifications.inventory.assignment_scheduled.message"
        if scheduled
        else "notifications.inventory.assignment_approved.message"
    )
    _notify_users(
        db,
        users=[requester],
        rule_key=rule,
        title_key=title,
        message_key=message,
        entity_type="inventory_asset_assignment_request",
        entity_id=str(request.id),
        metadata={"display_id": display_id, "effective_date": request.effective_date.isoformat()},
    )


def notify_assignment_rejected(
    db: Session,
    request: InventoryAssetAssignmentRequest,
    requester: User,
    *,
    display_id: str,
) -> None:
    _notify_users(
        db,
        users=[requester],
        rule_key="inventory.assignment_rejected",
        title_key="notifications.inventory.assignment_rejected.title",
        message_key="notifications.inventory.assignment_rejected.message",
        entity_type="inventory_asset_assignment_request",
        entity_id=str(request.id),
        metadata={"display_id": display_id},
    )


def notify_assignment_revision(
    db: Session,
    request: InventoryAssetAssignmentRequest,
    requester: User,
    *,
    display_id: str,
) -> None:
    _notify_users(
        db,
        users=[requester],
        rule_key="inventory.assignment_revision_requested",
        title_key="notifications.inventory.assignment_revision_requested.title",
        message_key="notifications.inventory.assignment_revision_requested.message",
        entity_type="inventory_asset_assignment_request",
        entity_id=str(request.id),
        metadata={"display_id": display_id},
    )


def notify_stale_conflict(
    db: Session,
    request: InventoryAssetAssignmentRequest,
    users: list[User],
    *,
    display_id: str,
) -> None:
    _notify_users(
        db,
        users=users,
        rule_key="inventory.assignment_stale_conflict",
        title_key="notifications.inventory.assignment_stale_conflict.title",
        message_key="notifications.inventory.assignment_stale_conflict.message",
        entity_type="inventory_asset_assignment_request",
        entity_id=str(request.id),
        metadata={"display_id": display_id},
    )


def notify_scheduled_applied(
    db: Session,
    request: InventoryAssetAssignmentRequest,
    users: list[User],
    *,
    display_id: str,
) -> None:
    _notify_users(
        db,
        users=users,
        rule_key="inventory.assignment_scheduled_applied",
        title_key="notifications.inventory.assignment_scheduled_applied.title",
        message_key="notifications.inventory.assignment_scheduled_applied.message",
        entity_type="inventory_asset_assignment_request",
        entity_id=str(request.id),
        metadata={"display_id": display_id},
    )


def notify_scheduled_failed(
    db: Session,
    request: InventoryAssetAssignmentRequest,
    users: list[User],
    *,
    display_id: str,
) -> None:
    _notify_users(
        db,
        users=users,
        rule_key="inventory.assignment_scheduled_failed",
        title_key="notifications.inventory.assignment_scheduled_failed.title",
        message_key="notifications.inventory.assignment_scheduled_failed.message",
        entity_type="inventory_asset_assignment_request",
        entity_id=str(request.id),
        metadata={"display_id": display_id},
    )
