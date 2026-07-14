"""Event-driven notification hooks."""

from uuid import UUID

from sqlalchemy.orm import Session

from investhome_api.models.notification import NotificationPriority, NotificationSource, NotificationType
from investhome_api.services.notification_service import create_notification


def notify_user_invited(
    db: Session,
    *,
    recipient_user_id: UUID,
    actor_user_id: UUID | None,
    metadata: dict[str, object] | None = None,
) -> None:
    create_notification(
        db,
        recipient_user_id=recipient_user_id,
        type=NotificationType.SYSTEM,
        priority=NotificationPriority.INFO,
        title_key="notifications.user.invited.title",
        message_key="notifications.user.invited.message",
        rule_key="user.invited",
        related_entity_type="user",
        related_entity_id=recipient_user_id,
        metadata=metadata,
        source=NotificationSource.ACTIVITY,
        created_by=actor_user_id,
    )


def notify_user_deactivated(
    db: Session,
    *,
    recipient_user_id: UUID,
    actor_user_id: UUID | None,
) -> None:
    create_notification(
        db,
        recipient_user_id=recipient_user_id,
        type=NotificationType.SYSTEM,
        priority=NotificationPriority.HIGH,
        title_key="notifications.user.deactivated.title",
        message_key="notifications.user.deactivated.message",
        rule_key="user.deactivated",
        related_entity_type="user",
        related_entity_id=recipient_user_id,
        source=NotificationSource.ACTIVITY,
        created_by=actor_user_id,
    )


def notify_password_changed(
    db: Session,
    *,
    recipient_user_id: UUID,
) -> None:
    create_notification(
        db,
        recipient_user_id=recipient_user_id,
        type=NotificationType.SYSTEM,
        priority=NotificationPriority.MEDIUM,
        title_key="notifications.user.password_changed.title",
        message_key="notifications.user.password_changed.message",
        rule_key="user.password_changed",
        related_entity_type="user",
        related_entity_id=recipient_user_id,
        source=NotificationSource.ACTIVITY,
    )


def notify_permission_changed(
    db: Session,
    *,
    recipient_user_id: UUID,
    role_id: UUID,
    actor_user_id: UUID | None,
    metadata: dict[str, object] | None = None,
) -> None:
    create_notification(
        db,
        recipient_user_id=recipient_user_id,
        type=NotificationType.SYSTEM,
        priority=NotificationPriority.CRITICAL,
        title_key="notifications.activity.permission_changed.title",
        message_key="notifications.activity.permission_changed.message",
        rule_key="activity.permission_changed",
        related_entity_type="role",
        related_entity_id=role_id,
        metadata=metadata,
        source=NotificationSource.ACTIVITY,
        created_by=actor_user_id,
    )


def notify_funding_received(
    db: Session,
    *,
    recipient_user_id: UUID,
    transaction_id: UUID,
    metadata: dict[str, object],
    actor_user_id: UUID | None = None,
) -> None:
    create_notification(
        db,
        recipient_user_id=recipient_user_id,
        type=NotificationType.FINANCE,
        priority=NotificationPriority.MEDIUM,
        title_key="notifications.finance.funding_received.title",
        message_key="notifications.finance.funding_received.message",
        rule_key="finance.funding_received",
        related_entity_type="transaction",
        related_entity_id=transaction_id,
        metadata=metadata,
        source=NotificationSource.ACTIVITY,
        created_by=actor_user_id,
    )


def notify_investor_assigned(
    db: Session,
    *,
    investor_id: UUID,
    investor_name: str,
    assigned_to: str | None,
    actor_user_id: UUID | None = None,
) -> None:
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from investhome_api.models.user_auth import Role, User, UserStatus
    from investhome_api.services.permission_service import user_has_permission

    if not assigned_to:
        return

    users = list(
        db.scalars(
            select(User)
            .where(User.archived_at.is_(None), User.status == UserStatus.ACTIVE)
            .options(selectinload(User.roles).selectinload(Role.permissions))
        ).all()
    )
    for user in users:
        if user.full_name != assigned_to:
            continue
        if not user_has_permission(user, "investors", "view"):
            continue
        create_notification(
            db,
            recipient_user_id=user.id,
            type=NotificationType.INVESTOR,
            priority=NotificationPriority.MEDIUM,
            title_key="notifications.investor.assigned.title",
            message_key="notifications.investor.assigned.message",
            rule_key="investor.assigned",
            related_entity_type="investor",
            related_entity_id=investor_id,
            metadata={"name": investor_name, "assigned_to": assigned_to},
            source=NotificationSource.ACTIVITY,
            created_by=actor_user_id,
        )


def notify_payment_completed(
    db: Session,
    *,
    recipient_user_id: UUID,
    obligation_id: UUID,
    metadata: dict[str, object],
    actor_user_id: UUID | None = None,
) -> None:
    create_notification(
        db,
        recipient_user_id=recipient_user_id,
        type=NotificationType.PAYMENT,
        priority=NotificationPriority.INFO,
        title_key="notifications.finance.payment_completed.title",
        message_key="notifications.finance.payment_completed.message",
        rule_key="finance.payment_completed",
        related_entity_type="payment_obligation",
        related_entity_id=obligation_id,
        metadata=metadata,
        source=NotificationSource.ACTIVITY,
        created_by=actor_user_id,
    )


def notify_users_with_permission(
    db: Session,
    *,
    resource: str,
    action: str,
    type: NotificationType,
    priority: NotificationPriority,
    title_key: str,
    message_key: str,
    rule_key: str,
    related_entity_type: str,
    related_entity_id: UUID,
    metadata: dict[str, object] | None = None,
    source: NotificationSource = NotificationSource.ACTIVITY,
    created_by: UUID | None = None,
) -> None:
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from investhome_api.models.user_auth import Role, User, UserStatus
    from investhome_api.services.permission_service import user_has_permission

    users = list(
        db.scalars(
            select(User)
            .where(User.archived_at.is_(None), User.status == UserStatus.ACTIVE)
            .options(selectinload(User.roles).selectinload(Role.permissions))
        ).all()
    )
    for user in users:
        if user_has_permission(user, resource, action):
            create_notification(
                db,
                recipient_user_id=user.id,
                type=type,
                priority=priority,
                title_key=title_key,
                message_key=message_key,
                rule_key=rule_key,
                related_entity_type=related_entity_type,
                related_entity_id=related_entity_id,
                metadata=metadata,
                source=source,
                created_by=created_by,
            )
