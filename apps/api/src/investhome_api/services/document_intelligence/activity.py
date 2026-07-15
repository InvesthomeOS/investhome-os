"""Activity and notification hooks for document intelligence."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from investhome_api.models.activity import (
    ActivityAction,
    ActivityActorType,
    ActivityEntityType,
    ActivitySource,
)
from investhome_api.models.document import Document
from investhome_api.models.notification import NotificationPriority, NotificationSource, NotificationType
from investhome_api.models.user_auth import User
from investhome_api.services.activity_service import log_activity
from investhome_api.services.document_intelligence.types import RiskItem
from investhome_api.services.notification_service import create_notification


def _log(
    db: Session,
    *,
    action: ActivityAction,
    description_key: str,
    document: Document,
    actor_user_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    actor = db.get(User, UUID(actor_user_id)) if actor_user_id else None
    log_activity(
        db,
        action=action,
        entity_type=ActivityEntityType.DOCUMENT,
        entity_id=document.id,
        description_key=description_key,
        actor_user=actor,
        actor_type=ActivityActorType.SYSTEM if actor is None else ActivityActorType.USER,
        source=ActivitySource.BACKGROUND_JOB if actor is None else ActivitySource.WEB,
        metadata=metadata or {"title": document.title, "document_id": str(document.id)},
        is_demo=document.is_demo,
    )


def record_processing_started(db: Session, document: Document, actor_user_id: str | None = None) -> None:
    _log(
        db,
        action=ActivityAction.OTHER,
        description_key="activity.document.processing_started",
        document=document,
        actor_user_id=actor_user_id,
    )


def record_processing_completed(db: Session, document: Document) -> None:
    _log(
        db,
        action=ActivityAction.OTHER,
        description_key="activity.document.processing_completed",
        document=document,
    )


def record_processing_failed(db: Session, document: Document, error: str) -> None:
    _log(
        db,
        action=ActivityAction.OTHER,
        description_key="activity.document.processing_failed",
        document=document,
        metadata={"title": document.title, "error": error[:200]},
    )


def record_reprocessed(db: Session, document: Document, actor_user_id: str) -> None:
    _log(
        db,
        action=ActivityAction.OTHER,
        description_key="activity.document.reprocessed",
        document=document,
        actor_user_id=actor_user_id,
    )


def record_classification_accepted(db: Session, document: Document, actor_user_id: str) -> None:
    _log(
        db,
        action=ActivityAction.APPROVED,
        description_key="activity.document.classification_accepted",
        document=document,
        actor_user_id=actor_user_id,
    )


def record_classification_rejected(db: Session, document: Document, actor_user_id: str) -> None:
    _log(
        db,
        action=ActivityAction.REJECTED,
        description_key="activity.document.classification_rejected",
        document=document,
        actor_user_id=actor_user_id,
    )


def record_question_asked(db: Session, document: Document, actor_user_id: str) -> None:
    _log(
        db,
        action=ActivityAction.OTHER,
        description_key="activity.document.question_asked",
        document=document,
        actor_user_id=actor_user_id,
    )


def notify_processing_failed(db: Session, document: Document) -> None:
    if document.uploaded_by_user_id is None:
        return
    create_notification(
        db,
        recipient_user_id=document.uploaded_by_user_id,
        type=NotificationType.DOCUMENT,
        title_key="notifications.document.processing_failed.title",
        message_key="notifications.document.processing_failed.message",
        rule_key="document.processing_failed",
        related_entity_type="document",
        related_entity_id=document.id,
        metadata={"document_id": str(document.id), "title": document.title},
        priority=NotificationPriority.HIGH,
        source=NotificationSource.SCHEDULED_JOB,
    )


def notify_processing_completed(db: Session, document: Document, risks: list[RiskItem]) -> None:
    if document.uploaded_by_user_id is None:
        return
    critical = [r for r in risks if r.severity in {"high", "critical"}]
    if critical:
        create_notification(
            db,
            recipient_user_id=document.uploaded_by_user_id,
            type=NotificationType.DOCUMENT,
            title_key="notifications.document.critical_risk.title",
            message_key="notifications.document.critical_risk.message",
            rule_key="document.critical_risk",
            related_entity_type="document",
            related_entity_id=document.id,
            metadata={
                "document_id": str(document.id),
                "title": document.title,
                "risk_count": len(critical),
            },
            priority=NotificationPriority.HIGH,
            source=NotificationSource.SCHEDULED_JOB,
        )
    if document.expiration_date:
        soon = document.expiration_date <= (datetime.now(UTC).date() + timedelta(days=30))
        if soon:
            create_notification(
                db,
                recipient_user_id=document.uploaded_by_user_id,
                type=NotificationType.DOCUMENT,
                title_key="notifications.document.expiration_soon.title",
                message_key="notifications.document.expiration_soon.message",
                rule_key="document.expiration_soon",
                related_entity_type="document",
                related_entity_id=document.id,
                metadata={
                    "document_id": str(document.id),
                    "title": document.title,
                    "expiration_date": document.expiration_date.isoformat(),
                },
                priority=NotificationPriority.MEDIUM,
                source=NotificationSource.SCHEDULED_JOB,
            )
