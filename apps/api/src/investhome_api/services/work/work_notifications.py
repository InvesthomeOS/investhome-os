"""Notifications for work items."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from investhome_api.models.notification import NotificationPriority, NotificationType
from investhome_api.models.user_auth import User
from investhome_api.models.work_item import WorkItem
from investhome_api.services.notification_hooks import notify_users_with_permission
from investhome_api.services.notification_service import create_notification


def _notify_user(
    db: Session,
    *,
    user_id: UUID,
    rule_key: str,
    title_key: str,
    message_key: str,
    item: WorkItem,
    priority: NotificationPriority = NotificationPriority.MEDIUM,
    ntype: NotificationType = NotificationType.SYSTEM,
    extra: dict | None = None,
    created_by: UUID | None = None,
) -> None:
    metadata = {
        "work_item_id": str(item.id),
        "title": item.title,
        "work_item_type": item.work_item_type.value,
        **(extra or {}),
    }
    create_notification(
        db,
        recipient_user_id=user_id,
        type=ntype,
        priority=priority,
        title_key=title_key,
        message_key=message_key,
        rule_key=rule_key,
        related_entity_type="work_item",
        related_entity_id=item.id,
        metadata=metadata,
        created_by=created_by,
    )


def notify_assigned(db: Session, item: WorkItem, *, actor: User | None = None) -> None:
    if not item.assigned_user_id:
        return
    _notify_user(
        db,
        user_id=item.assigned_user_id,
        rule_key="work.item.assigned",
        title_key="notifications.work.assigned.title",
        message_key="notifications.work.assigned.message",
        item=item,
        created_by=actor.id if actor else None,
    )


def notify_reassigned(db: Session, item: WorkItem, *, actor: User | None = None) -> None:
    if not item.assigned_user_id:
        return
    _notify_user(
        db,
        user_id=item.assigned_user_id,
        rule_key="work.item.reassigned",
        title_key="notifications.work.reassigned.title",
        message_key="notifications.work.reassigned.message",
        item=item,
        created_by=actor.id if actor else None,
    )


def notify_due_soon(db: Session, item: WorkItem) -> None:
    if not item.assigned_user_id:
        return
    _notify_user(
        db,
        user_id=item.assigned_user_id,
        rule_key=f"work.item.due_soon.{item.id}",
        title_key="notifications.work.due_soon.title",
        message_key="notifications.work.due_soon.message",
        item=item,
        priority=NotificationPriority.HIGH,
        ntype=NotificationType.WARNING,
    )


def notify_overdue(db: Session, item: WorkItem) -> None:
    if not item.assigned_user_id:
        return
    _notify_user(
        db,
        user_id=item.assigned_user_id,
        rule_key=f"work.item.overdue.{item.id}",
        title_key="notifications.work.overdue.title",
        message_key="notifications.work.overdue.message",
        item=item,
        priority=NotificationPriority.HIGH,
        ntype=NotificationType.WARNING,
    )


def notify_meeting_approaching(db: Session, item: WorkItem) -> None:
    if not item.assigned_user_id:
        return
    _notify_user(
        db,
        user_id=item.assigned_user_id,
        rule_key=f"work.item.meeting_approaching.{item.id}",
        title_key="notifications.work.meeting_approaching.title",
        message_key="notifications.work.meeting_approaching.message",
        item=item,
        priority=NotificationPriority.HIGH,
    )


def notify_follow_up_due(db: Session, item: WorkItem) -> None:
    if not item.assigned_user_id:
        return
    _notify_user(
        db,
        user_id=item.assigned_user_id,
        rule_key=f"work.item.follow_up_due.{item.id}",
        title_key="notifications.work.follow_up_due.title",
        message_key="notifications.work.follow_up_due.message",
        item=item,
    )


def notify_cancelled(db: Session, item: WorkItem, *, actor: User | None = None) -> None:
    if not item.assigned_user_id:
        return
    _notify_user(
        db,
        user_id=item.assigned_user_id,
        rule_key=f"work.item.cancelled.{item.id}",
        title_key="notifications.work.cancelled.title",
        message_key="notifications.work.cancelled.message",
        item=item,
        created_by=actor.id if actor else None,
    )


def notify_blocked(db: Session, item: WorkItem) -> None:
    if not item.assigned_user_id:
        return
    _notify_user(
        db,
        user_id=item.assigned_user_id,
        rule_key=f"work.item.blocked.{item.id}",
        title_key="notifications.work.blocked.title",
        message_key="notifications.work.blocked.message",
        item=item,
        ntype=NotificationType.WARNING,
    )


def notify_no_next_action_opportunity(db: Session, opportunity_id: UUID, opportunity_code: str) -> None:
    notify_users_with_permission(
        db,
        resource="sales",
        action="view",
        type=NotificationType.WARNING,
        priority=NotificationPriority.HIGH,
        title_key="notifications.sales.no_next_action.title",
        message_key="notifications.sales.no_next_action.message",
        rule_key=f"sales.opportunity.no_next_action.{opportunity_id}",
        related_entity_type="sales_opportunity",
        related_entity_id=opportunity_id,
        metadata={"opportunity_code": opportunity_code},
    )
