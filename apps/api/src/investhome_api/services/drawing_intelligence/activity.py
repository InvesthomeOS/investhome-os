"""Drawing intelligence activity and notification hooks."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityAction, ActivityActorType, ActivityEntityType, ActivitySource
from investhome_api.models.document import Document
from investhome_api.models.notification import NotificationPriority, NotificationSource, NotificationType
from investhome_api.models.user_auth import User
from investhome_api.services.activity_service import log_activity
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


def record_drawing_processing_started(db: Session, document: Document, actor_id: str | None = None) -> None:
    _log(
        db,
        action=ActivityAction.OTHER,
        description_key="activity.document.drawing_processing_started",
        document=document,
        actor_user_id=actor_id,
    )


def record_drawing_processing_completed(db: Session, document: Document, actor_id: str | None = None) -> None:
    _log(
        db,
        action=ActivityAction.OTHER,
        description_key="activity.document.drawing_processing_completed",
        document=document,
        actor_user_id=actor_id,
    )


def record_drawing_processing_failed(db: Session, document: Document, error: str) -> None:
    _log(
        db,
        action=ActivityAction.OTHER,
        description_key="activity.document.drawing_processing_failed",
        document=document,
        metadata={"title": document.title, "error": error[:200]},
    )
    if document.uploaded_by_user_id:
        create_notification(
            db,
            recipient_user_id=document.uploaded_by_user_id,
            type=NotificationType.DOCUMENT,
            title_key="notifications.document.drawing_processing_failed.title",
            message_key="notifications.document.drawing_processing_failed.message",
            rule_key="document.drawing_processing_failed",
            related_entity_type="document",
            related_entity_id=document.id,
            metadata={"title": document.title, "error": error[:200]},
            source=NotificationSource.SCHEDULED_JOB,
            priority=NotificationPriority.HIGH,
        )


def record_scale_corrected(db: Session, document: Document, user_id: UUID, scale: str) -> None:
    _log(
        db,
        action=ActivityAction.UPDATED,
        description_key="activity.document.drawing_scale_corrected",
        document=document,
        actor_user_id=str(user_id),
        metadata={"title": document.title, "scale": scale},
    )


def record_annotation_added(db: Session, document: Document, user_id: UUID, label: str | None) -> None:
    _log(
        db,
        action=ActivityAction.CREATED,
        description_key="activity.document.drawing_annotation_added",
        document=document,
        actor_user_id=str(user_id),
        metadata={"title": document.title, "label": label or ""},
    )


def record_version_compared(
    db: Session,
    document: Document,
    user_id: UUID,
    from_version_id: UUID,
    to_version_id: UUID,
    summary: str,
) -> None:
    _log(
        db,
        action=ActivityAction.OTHER,
        description_key="activity.document.drawing_version_compared",
        document=document,
        actor_user_id=str(user_id),
        metadata={
            "title": document.title,
            "from_version_id": str(from_version_id),
            "to_version_id": str(to_version_id),
            "summary": summary[:200],
        },
    )


def record_drawing_question_asked(db: Session, document: Document, user_id: UUID, question: str) -> None:
    _log(
        db,
        action=ActivityAction.OTHER,
        description_key="activity.document.drawing_question_asked",
        document=document,
        actor_user_id=str(user_id),
        metadata={"title": document.title, "question": question[:120]},
    )


def record_unit_proposal_created(db: Session, document: Document, unit_label: str) -> None:
    _log(
        db,
        action=ActivityAction.CREATED,
        description_key="activity.document.drawing_unit_proposed",
        document=document,
        metadata={"title": document.title, "unit_label": unit_label},
    )


def record_unit_approved(db: Session, document: Document, user_id: UUID, unit_label: str) -> None:
    _log(
        db,
        action=ActivityAction.UPDATED,
        description_key="activity.document.drawing_unit_approved",
        document=document,
        actor_user_id=str(user_id),
        metadata={"title": document.title, "unit_label": unit_label},
    )
