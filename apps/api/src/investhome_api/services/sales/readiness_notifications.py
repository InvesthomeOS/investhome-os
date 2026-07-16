"""Sales readiness notifications — deduplicated by rule_key."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from investhome_api.models.notification import NotificationPriority, NotificationType
from investhome_api.models.sales_readiness import SalesReadinessCase, SalesReadinessRequirement
from investhome_api.services.notification_hooks import notify_user, notify_users_with_permission


def _case_metadata(case: SalesReadinessCase) -> dict:
    return {
        "readiness_case_id": str(case.id),
        "case_code": case.case_code,
        "opportunity_id": str(case.opportunity_id),
        "status": case.status.value,
    }


def notify_case_assigned(db: Session, case: SalesReadinessCase) -> None:
    if case.assigned_sales_user_id is None:
        return
    notify_user(
        db,
        user_id=case.assigned_sales_user_id,
        type=NotificationType.SYSTEM,
        priority=NotificationPriority.MEDIUM,
        title_key="notifications.sales.readiness.assigned.title",
        message_key="notifications.sales.readiness.assigned.message",
        rule_key=f"sales.readiness.assigned.{case.id}",
        related_entity_type="sales_readiness_case",
        related_entity_id=case.id,
        metadata=_case_metadata(case),
    )


def notify_blocked(db: Session, case: SalesReadinessCase, *, reason: str | None = None) -> None:
    meta = {**_case_metadata(case), "blocker": reason or case.blocker_summary or ""}
    notify_users_with_permission(
        db,
        resource="sales",
        action="view_readiness",
        type=NotificationType.SYSTEM,
        priority=NotificationPriority.HIGH,
        title_key="notifications.sales.readiness.blocked.title",
        message_key="notifications.sales.readiness.blocked.message",
        rule_key=f"sales.readiness.blocked.{case.id}",
        related_entity_type="sales_readiness_case",
        related_entity_id=case.id,
        metadata=meta,
    )


def notify_deposit_due(db: Session, case: SalesReadinessCase) -> None:
    notify_users_with_permission(
        db,
        resource="sales",
        action="view_deposit_status",
        type=NotificationType.SYSTEM,
        priority=NotificationPriority.MEDIUM,
        title_key="notifications.sales.readiness.deposit_due.title",
        message_key="notifications.sales.readiness.deposit_due.message",
        rule_key=f"sales.readiness.deposit_due.{case.id}",
        related_entity_type="sales_readiness_case",
        related_entity_id=case.id,
        metadata=_case_metadata(case),
    )


def notify_deposit_overdue(db: Session, case: SalesReadinessCase) -> None:
    notify_users_with_permission(
        db,
        resource="sales",
        action="view_deposit_status",
        type=NotificationType.SYSTEM,
        priority=NotificationPriority.HIGH,
        title_key="notifications.sales.readiness.deposit_overdue.title",
        message_key="notifications.sales.readiness.deposit_overdue.message",
        rule_key=f"sales.readiness.deposit_overdue.{case.id}",
        related_entity_type="sales_readiness_case",
        related_entity_id=case.id,
        metadata=_case_metadata(case),
    )


def notify_document_missing(db: Session, case: SalesReadinessCase, requirement: SalesReadinessRequirement) -> None:
    notify_users_with_permission(
        db,
        resource="sales",
        action="view_contract_documents",
        type=NotificationType.SYSTEM,
        priority=NotificationPriority.MEDIUM,
        title_key="notifications.sales.readiness.document_missing.title",
        message_key="notifications.sales.readiness.document_missing.message",
        rule_key=f"sales.readiness.document_missing.{case.id}.{requirement.requirement_type.value}",
        related_entity_type="sales_readiness_case",
        related_entity_id=case.id,
        metadata={**_case_metadata(case), "requirement_type": requirement.requirement_type.value},
    )


def notify_signature_pending(db: Session, case: SalesReadinessCase) -> None:
    notify_users_with_permission(
        db,
        resource="sales",
        action="view_readiness",
        type=NotificationType.SYSTEM,
        priority=NotificationPriority.MEDIUM,
        title_key="notifications.sales.readiness.signature_pending.title",
        message_key="notifications.sales.readiness.signature_pending.message",
        rule_key=f"sales.readiness.signature_pending.{case.id}",
        related_entity_type="sales_readiness_case",
        related_entity_id=case.id,
        metadata=_case_metadata(case),
    )


def notify_handoff_ready(db: Session, case: SalesReadinessCase) -> None:
    notify_users_with_permission(
        db,
        resource="sales",
        action="approve_handoff",
        type=NotificationType.SYSTEM,
        priority=NotificationPriority.HIGH,
        title_key="notifications.sales.readiness.handoff_ready.title",
        message_key="notifications.sales.readiness.handoff_ready.message",
        rule_key=f"sales.readiness.handoff_ready.{case.id}",
        related_entity_type="sales_readiness_case",
        related_entity_id=case.id,
        metadata=_case_metadata(case),
    )


def notify_handoff_requested(db: Session, case: SalesReadinessCase) -> None:
    notify_users_with_permission(
        db,
        resource="sales",
        action="approve_handoff",
        type=NotificationType.SYSTEM,
        priority=NotificationPriority.HIGH,
        title_key="notifications.sales.readiness.handoff_requested.title",
        message_key="notifications.sales.readiness.handoff_requested.message",
        rule_key=f"sales.readiness.handoff_requested.{case.id}",
        related_entity_type="sales_readiness_case",
        related_entity_id=case.id,
        metadata=_case_metadata(case),
    )


def notify_handoff_returned(db: Session, case: SalesReadinessCase, *, reason: str) -> None:
    if case.assigned_sales_user_id:
        notify_user(
            db,
            user_id=case.assigned_sales_user_id,
            type=NotificationType.SYSTEM,
            priority=NotificationPriority.HIGH,
            title_key="notifications.sales.readiness.handoff_returned.title",
            message_key="notifications.sales.readiness.handoff_returned.message",
            rule_key=f"sales.readiness.handoff_returned.{case.id}",
            related_entity_type="sales_readiness_case",
            related_entity_id=case.id,
            metadata={**_case_metadata(case), "reason": reason},
        )


def notify_requirement_rejected(db: Session, case: SalesReadinessCase, requirement: SalesReadinessRequirement) -> None:
    notify_users_with_permission(
        db,
        resource="sales",
        action="view_readiness",
        type=NotificationType.SYSTEM,
        priority=NotificationPriority.MEDIUM,
        title_key="notifications.sales.readiness.document_rejected.title",
        message_key="notifications.sales.readiness.document_rejected.message",
        rule_key=f"sales.readiness.rejected.{case.id}.{requirement.id}",
        related_entity_type="sales_readiness_case",
        related_entity_id=case.id,
        metadata={**_case_metadata(case), "requirement_id": str(requirement.id)},
    )
