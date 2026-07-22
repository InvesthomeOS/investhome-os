"""Activity logging helpers for route handlers."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from investhome_api.models.activity import (
    ActivityAction,
    ActivityActorType,
    ActivityEntityType,
    ActivitySource,
)
from investhome_api.models.user_auth import User
from investhome_api.services.activity_service import (
    ActivityRequestContext,
    compute_field_changes,
    log_activity,
)


def activity_context_from_request(request: Request | None) -> ActivityRequestContext:
    if request is None:
        return ActivityRequestContext(source=ActivitySource.API)
    forwarded = request.headers.get("x-forwarded-for")
    ip_address = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else None)
    request_id = request.headers.get("x-request-id")
    source_header = request.headers.get("x-activity-source", "").lower()
    source = ActivitySource.WEB
    if source_header == "api":
        source = ActivitySource.API
    elif source_header == "import":
        source = ActivitySource.IMPORT
    return ActivityRequestContext(
        source=source,
        ip_address=ip_address,
        user_agent=request.headers.get("user-agent"),
        request_id=request_id,
    )


def log_entity_created(
    db: Session,
    *,
    entity_type: ActivityEntityType,
    entity_id: UUID,
    description_key: str,
    actor: User | None,
    metadata: dict[str, Any] | None = None,
    request: Request | None = None,
    is_demo: bool = False,
) -> None:
    log_activity(
        db,
        action=ActivityAction.CREATED,
        entity_type=entity_type,
        entity_id=entity_id,
        description_key=description_key,
        actor_user=actor,
        metadata=metadata,
        request_context=activity_context_from_request(request),
        is_demo=is_demo,
    )


def log_entity_updated(
    db: Session,
    *,
    entity_type: ActivityEntityType,
    entity_id: UUID,
    description_key: str,
    actor: User | None,
    before: dict[str, Any],
    after: dict[str, Any],
    metadata: dict[str, Any] | None = None,
    request: Request | None = None,
    is_demo: bool = False,
) -> None:
    changed_fields, previous_values, new_values = compute_field_changes(before, after)
    if not changed_fields:
        return
    action = ActivityAction.STATUS_CHANGED if "status" in changed_fields else ActivityAction.UPDATED
    if action == ActivityAction.STATUS_CHANGED:
        description_key = description_key.replace(".updated", ".status_changed")
    log_activity(
        db,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description_key=description_key,
        actor_user=actor,
        metadata=metadata,
        changed_fields=changed_fields,
        previous_values=previous_values,
        new_values=new_values,
        request_context=activity_context_from_request(request),
        is_demo=is_demo,
    )


def log_entity_deleted(
    db: Session,
    *,
    entity_type: ActivityEntityType,
    entity_id: UUID,
    description_key: str,
    actor: User | None,
    metadata: dict[str, Any] | None = None,
    request: Request | None = None,
    is_demo: bool = False,
) -> None:
    log_activity(
        db,
        action=ActivityAction.DELETED,
        entity_type=entity_type,
        entity_id=entity_id,
        description_key=description_key,
        actor_user=actor,
        metadata=metadata,
        request_context=activity_context_from_request(request),
        is_demo=is_demo,
    )


def log_entity_archived(
    db: Session,
    *,
    entity_type: ActivityEntityType,
    entity_id: UUID,
    description_key: str,
    actor: User | None,
    metadata: dict[str, Any] | None = None,
    request: Request | None = None,
    is_demo: bool = False,
) -> None:
    log_activity(
        db,
        action=ActivityAction.ARCHIVED,
        entity_type=entity_type,
        entity_id=entity_id,
        description_key=description_key,
        actor_user=actor,
        metadata=metadata,
        request_context=activity_context_from_request(request),
        is_demo=is_demo,
    )


def log_entity_restored(
    db: Session,
    *,
    entity_type: ActivityEntityType,
    entity_id: UUID,
    description_key: str,
    actor: User | None,
    metadata: dict[str, Any] | None = None,
    request: Request | None = None,
    is_demo: bool = False,
) -> None:
    log_activity(
        db,
        action=ActivityAction.RESTORED,
        entity_type=entity_type,
        entity_id=entity_id,
        description_key=description_key,
        actor_user=actor,
        metadata=metadata,
        request_context=activity_context_from_request(request),
        is_demo=is_demo,
    )


def log_security_event(
    db: Session,
    *,
    action: ActivityAction,
    entity_type: ActivityEntityType,
    entity_id: UUID,
    description_key: str,
    actor: User | None = None,
    actor_name: str | None = None,
    actor_type: ActivityActorType = ActivityActorType.USER,
    metadata: dict[str, Any] | None = None,
    request: Request | None = None,
    commit: bool = False,
) -> None:
    log_activity(
        db,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description_key=description_key,
        actor_user=actor,
        actor_name=actor_name,
        actor_type=actor_type,
        metadata=metadata,
        request_context=activity_context_from_request(request),
        commit=commit,
    )


def log_finance_transaction_event(
    db: Session,
    *,
    transaction,
    actor: User | None,
    request: Request | None,
    previous_status=None,
) -> None:
    from investhome_api.models.finance import TransactionStatus

    if (
        transaction.status == TransactionStatus.COMPLETED
        and previous_status != TransactionStatus.COMPLETED
    ):
        log_activity(
            db,
            action=ActivityAction.PAYMENT_COMPLETED,
            entity_type=ActivityEntityType.TRANSACTION,
            entity_id=transaction.id,
            description_key="activity.transaction.completed",
            actor_user=actor,
            metadata={
                "amount": str(transaction.amount),
                "currency": transaction.currency,
                "description": transaction.description or "",
            },
            request_context=activity_context_from_request(request),
            is_demo=transaction.is_demo,
        )
        from investhome_api.services.notification_hooks import notify_users_with_permission
        from investhome_api.models.notification import NotificationPriority, NotificationSource, NotificationType

        meta = {
            "amount": str(transaction.amount),
            "currency": transaction.currency,
            "description": transaction.description or "",
        }
        notify_users_with_permission(
            db,
            resource="finance",
            action="view",
            type=NotificationType.FINANCE,
            priority=NotificationPriority.MEDIUM,
            title_key="notifications.finance.funding_received.title",
            message_key="notifications.finance.funding_received.message",
            rule_key="finance.funding_received",
            related_entity_type="transaction",
            related_entity_id=transaction.id,
            metadata=meta,
            source=NotificationSource.ACTIVITY,
            created_by=actor.id if actor is not None else None,
        )
    elif previous_status is None:
        log_entity_created(
            db,
            entity_type=ActivityEntityType.TRANSACTION,
            entity_id=transaction.id,
            description_key="activity.transaction.created",
            actor=actor,
            metadata={
                "amount": str(transaction.amount),
                "currency": transaction.currency,
                "description": transaction.description or "",
            },
            request=request,
            is_demo=transaction.is_demo,
        )


def log_payment_obligation_event(
    db: Session,
    *,
    obligation,
    actor: User | None,
    request: Request | None,
    previous_status=None,
) -> None:
    from investhome_api.models.finance import ObligationStatus

    if obligation.status == ObligationStatus.PAID and previous_status != ObligationStatus.PAID:
        log_activity(
            db,
            action=ActivityAction.PAYMENT_COMPLETED,
            entity_type=ActivityEntityType.PAYMENT_OBLIGATION,
            entity_id=obligation.id,
            description_key="activity.payment_obligation.paid",
            actor_user=actor,
            metadata={
                "payee": obligation.payee or "",
                "amount": str(obligation.amount),
                "currency": obligation.currency,
            },
            request_context=activity_context_from_request(request),
            is_demo=obligation.is_demo,
        )
        from investhome_api.services.notification_hooks import notify_users_with_permission
        from investhome_api.models.notification import NotificationPriority, NotificationSource, NotificationType

        notify_users_with_permission(
            db,
            resource="finance",
            action="view",
            type=NotificationType.PAYMENT,
            priority=NotificationPriority.INFO,
            title_key="notifications.finance.payment_completed.title",
            message_key="notifications.finance.payment_completed.message",
            rule_key="finance.payment_completed",
            related_entity_type="payment_obligation",
            related_entity_id=obligation.id,
            metadata={
                "payee": obligation.payee or "",
                "amount": str(obligation.amount),
                "currency": obligation.currency,
            },
            source=NotificationSource.ACTIVITY,
            created_by=actor.id if actor is not None else None,
        )
        from investhome_api.services.notification_hooks import notify_users_with_permission
        from investhome_api.models.notification import NotificationPriority, NotificationSource, NotificationType

        notify_users_with_permission(
            db,
            resource="finance",
            action="view",
            type=NotificationType.PAYMENT,
            priority=NotificationPriority.INFO,
            title_key="notifications.finance.payment_completed.title",
            message_key="notifications.finance.payment_completed.message",
            rule_key="finance.payment_completed",
            related_entity_type="payment_obligation",
            related_entity_id=obligation.id,
            metadata={
                "payee": obligation.payee or "",
                "amount": str(obligation.amount),
                "currency": obligation.currency,
            },
            source=NotificationSource.ACTIVITY,
            created_by=actor.id if actor is not None else None,
        )
