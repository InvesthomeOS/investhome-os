"""Company workspace notification helpers — deduplicated automation rules."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from investhome_api.models.notification import NotificationPriority, NotificationSource, NotificationType
from investhome_api.models.user_auth import User
from investhome_api.services.notification_service import create_notification
from investhome_api.services.permission_service import user_has_permission


def _notify_company_user(
    db: Session,
    *,
    recipient_user_id: UUID,
    rule_key: str,
    title_key: str,
    message_key: str,
    related_entity_type: str,
    related_entity_id: UUID,
    metadata: dict | None = None,
    priority: NotificationPriority = NotificationPriority.MEDIUM,
) -> None:
    create_notification(
        db,
        recipient_user_id=recipient_user_id,
        type=NotificationType.SYSTEM,
        priority=priority,
        title_key=title_key,
        message_key=message_key,
        rule_key=rule_key,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        metadata=metadata or {},
        source=NotificationSource.AUTOMATION,
    )


def notify_company_owner_change(
    db: Session,
    *,
    owner_user_id: UUID | None,
    company_id: UUID,
    company_name: str,
    actor: User,
) -> None:
    if owner_user_id is None or owner_user_id == actor.id:
        return
    if not user_has_permission(db.get(User, owner_user_id) or actor, "company", "read"):
        return
    _notify_company_user(
        db,
        recipient_user_id=owner_user_id,
        rule_key="company.ownership_changed",
        title_key="notifications.company.ownership_changed.title",
        message_key="notifications.company.ownership_changed.message",
        related_entity_type="company",
        related_entity_id=company_id,
        metadata={"company_name": company_name, "actor_name": actor.full_name},
        priority=NotificationPriority.HIGH,
    )


def notify_branch_manager_assigned(
    db: Session,
    *,
    manager_user_id: UUID | None,
    branch_id: UUID,
    branch_name: str,
    actor: User,
) -> None:
    if manager_user_id is None or manager_user_id == actor.id:
        return
    _notify_company_user(
        db,
        recipient_user_id=manager_user_id,
        rule_key="branch.manager_assigned",
        title_key="notifications.company.branch_manager_assigned.title",
        message_key="notifications.company.branch_manager_assigned.message",
        related_entity_type="branch",
        related_entity_id=branch_id,
        metadata={"branch_name": branch_name, "actor_name": actor.full_name},
    )


def notify_department_head_assigned(
    db: Session,
    *,
    head_user_id: UUID | None,
    department_id: UUID,
    department_name: str,
    actor: User,
) -> None:
    if head_user_id is None or head_user_id == actor.id:
        return
    _notify_company_user(
        db,
        recipient_user_id=head_user_id,
        rule_key="department.head_assigned",
        title_key="notifications.company.department_head_assigned.title",
        message_key="notifications.company.department_head_assigned.message",
        related_entity_type="department",
        related_entity_id=department_id,
        metadata={"department_name": department_name, "actor_name": actor.full_name},
    )


def notify_document_expiring_soon(
    db: Session,
    *,
    recipient_user_id: UUID,
    document_id: UUID,
    document_title: str,
    days_remaining: int,
) -> None:
    _notify_company_user(
        db,
        recipient_user_id=recipient_user_id,
        rule_key=f"document.expiring.{document_id}",
        title_key="notifications.company.document_expiring.title",
        message_key="notifications.company.document_expiring.message",
        related_entity_type="document",
        related_entity_id=document_id,
        metadata={"document_title": document_title, "days_remaining": days_remaining},
        priority=NotificationPriority.HIGH if days_remaining <= 7 else NotificationPriority.MEDIUM,
    )
