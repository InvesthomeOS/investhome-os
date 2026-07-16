"""Notification helpers for inventory reservations."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from investhome_api.models.inventory import InventoryReservation, ReservationRecordStatus
from investhome_api.models.notification import NotificationPriority, NotificationSource, NotificationType
from investhome_api.models.user_auth import User
from investhome_api.services.notification_service import NotificationCandidate, create_notification
from investhome_api.services.permission_service import user_has_permission


def _notify_user(
    db: Session,
    *,
    user_id: UUID,
    rule_key: str,
    title_key: str,
    message_key: str,
    reservation: InventoryReservation,
    metadata: dict | None = None,
    priority: NotificationPriority = NotificationPriority.MEDIUM,
    notification_type: NotificationType = NotificationType.SYSTEM,
) -> None:
    meta = {
        "display_id": metadata.get("display_id") if metadata else None,
        "party_name": metadata.get("party_name") if metadata else None,
        **(metadata or {}),
    }
    create_notification(
        db,
        recipient_user_id=user_id,
        type=notification_type,
        priority=priority,
        title_key=title_key,
        message_key=message_key,
        rule_key=rule_key,
        related_entity_type="inventory_reservation",
        related_entity_id=reservation.id,
        metadata={k: v for k, v in meta.items() if v is not None},
        source=NotificationSource.AUTOMATION,
        is_demo=reservation.is_demo,
    )


def notify_soft_hold_created(
    db: Session,
    reservation: InventoryReservation,
    *,
    display_id: str,
    party_name: str,
) -> None:
    if reservation.reserved_by_user_id:
        _notify_user(
            db,
            user_id=reservation.reserved_by_user_id,
            rule_key="inventory.reservation.soft_hold_created",
            title_key="notifications.inventory.soft_hold_created.title",
            message_key="notifications.inventory.soft_hold_created.message",
            reservation=reservation,
            metadata={"display_id": display_id, "party_name": party_name},
        )


def notify_reservation_expiring(
    db: Session,
    reservation: InventoryReservation,
    users: list[User],
    *,
    display_id: str,
    hours_remaining: int,
) -> None:
    priority = NotificationPriority.HIGH if hours_remaining <= 4 else NotificationPriority.MEDIUM
    for user in users:
        if not user_has_permission(user, "inventory", "view"):
            continue
        _notify_user(
            db,
            user_id=user.id,
            rule_key="inventory.reservation_expiring",
            title_key="notifications.inventory.reservation_expiring.title",
            message_key="notifications.inventory.reservation_expiring.message",
            reservation=reservation,
            metadata={"display_id": display_id, "hours": hours_remaining},
            priority=priority,
            notification_type=NotificationType.REMINDER,
        )


def notify_reservation_expired(
    db: Session,
    reservation: InventoryReservation,
    users: list[User],
    *,
    display_id: str,
) -> None:
    for user in users:
        if not user_has_permission(user, "inventory", "view"):
            continue
        _notify_user(
            db,
            user_id=user.id,
            rule_key="inventory.reservation_expired",
            title_key="notifications.inventory.reservation_expired.title",
            message_key="notifications.inventory.reservation_expired.message",
            reservation=reservation,
            metadata={"display_id": display_id},
            priority=NotificationPriority.HIGH,
            notification_type=NotificationType.WARNING,
        )


def notify_reservation_approved(
    db: Session,
    reservation: InventoryReservation,
    *,
    display_id: str,
) -> None:
    if reservation.reserved_by_user_id:
        _notify_user(
            db,
            user_id=reservation.reserved_by_user_id,
            rule_key="inventory.reservation.approved",
            title_key="notifications.inventory.reservation_approved.title",
            message_key="notifications.inventory.reservation_approved.message",
            reservation=reservation,
            metadata={"display_id": display_id},
        )


def notify_deposit_overdue(
    db: Session,
    reservation: InventoryReservation,
    users: list[User],
    *,
    display_id: str,
    days_overdue: int,
) -> None:
    for user in users:
        if not user_has_permission(user, "inventory", "view"):
            continue
        _notify_user(
            db,
            user_id=user.id,
            rule_key="inventory.reservation.deposit_overdue",
            title_key="notifications.inventory.deposit_overdue.title",
            message_key="notifications.inventory.deposit_overdue.message",
            reservation=reservation,
            metadata={"display_id": display_id, "days": days_overdue},
            priority=NotificationPriority.HIGH,
            notification_type=NotificationType.WARNING,
        )


def collect_expiring_reservation_candidates(
    db: Session,
    reservation: InventoryReservation,
    *,
    display_id: str,
    hours_remaining: int,
) -> list[NotificationCandidate]:
    from investhome_api.services.notification_service import NotificationCandidate

    return [
        NotificationCandidate(
            rule_key="inventory.reservation_expiring",
            type=NotificationType.REMINDER,
            priority=NotificationPriority.HIGH if hours_remaining <= 4 else NotificationPriority.MEDIUM,
            title_key="notifications.inventory.reservation_expiring.title",
            message_key="notifications.inventory.reservation_expiring.message",
            metadata={"display_id": display_id, "hours": hours_remaining},
            related_entity_type="inventory_reservation",
            related_entity_id=reservation.id,
            is_demo=reservation.is_demo,
            link_module="inventory",
            related_label=display_id,
        )
    ]
