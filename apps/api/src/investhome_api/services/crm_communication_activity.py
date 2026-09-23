"""CRM communication audit hooks."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.crm_communication import CrmCommunicationAuditLog
from investhome_api.models.user_auth import User
from investhome_api.services.activity_recorder import (
    activity_context_from_request,
    log_entity_archived,
    log_entity_created,
    log_entity_deleted,
    log_entity_restored,
    log_entity_updated,
)
from investhome_api.services.crypto_seal import redact_secret_fields

COMMUNICATION_AUDIT_FIELDS = (
    "channel",
    "direction",
    "status",
    "subject",
    "recipient_entity_type",
    "recipient_entity_id",
    "thread_id",
    "scheduled_at",
    "visibility",
)


def record_communication_audit(
    db: Session,
    *,
    event_type: str,
    communication_id: UUID | None = None,
    thread_id: UUID | None = None,
    actor: User | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    db.add(
        CrmCommunicationAuditLog(
            communication_id=communication_id,
            thread_id=thread_id,
            event_type=event_type,
            actor_user_id=actor.id if actor else None,
            details_json=redact_secret_fields(details) if details else None,
        )
    )


def record_communication_created(
    db: Session,
    communication_id: UUID,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_entity_created(
        db,
        entity_type=ActivityEntityType.CRM_COMMUNICATION,
        entity_id=communication_id,
        description_key="activity.crm_communication.created",
        actor=actor,
        request=request,
    )
    record_communication_audit(
        db,
        event_type="communication.created",
        communication_id=communication_id,
        actor=actor,
    )


def record_communication_updated(
    db: Session,
    communication_id: UUID,
    actor: User | None,
    before: dict[str, Any],
    after: dict[str, Any],
    request: Request | None = None,
) -> None:
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.CRM_COMMUNICATION,
        entity_id=communication_id,
        description_key="activity.crm_communication.updated",
        actor=actor,
        before=before,
        after=after,
        request=request,
    )
    record_communication_audit(
        db,
        event_type="communication.updated",
        communication_id=communication_id,
        actor=actor,
        details={"before": before, "after": after},
    )


def record_communication_archived(
    db: Session,
    communication_id: UUID,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_entity_archived(
        db,
        entity_type=ActivityEntityType.CRM_COMMUNICATION,
        entity_id=communication_id,
        description_key="activity.crm_communication.archived",
        actor=actor,
        request=request,
    )
    record_communication_audit(
        db,
        event_type="communication.archived",
        communication_id=communication_id,
        actor=actor,
    )


def record_communication_restored(
    db: Session,
    communication_id: UUID,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_entity_restored(
        db,
        entity_type=ActivityEntityType.CRM_COMMUNICATION,
        entity_id=communication_id,
        description_key="activity.crm_communication.restored",
        actor=actor,
        request=request,
    )
    record_communication_audit(
        db,
        event_type="communication.restored",
        communication_id=communication_id,
        actor=actor,
    )


def record_communication_deleted(
    db: Session,
    communication_id: UUID,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_entity_deleted(
        db,
        entity_type=ActivityEntityType.CRM_COMMUNICATION,
        entity_id=communication_id,
        description_key="activity.crm_communication.deleted",
        actor=actor,
        request=request,
    )
    record_communication_audit(
        db,
        event_type="communication.deleted",
        communication_id=communication_id,
        actor=actor,
    )


def snapshot_communication(entity: Any) -> dict[str, Any]:
    return snapshot_entity(entity, COMMUNICATION_AUDIT_FIELDS)
