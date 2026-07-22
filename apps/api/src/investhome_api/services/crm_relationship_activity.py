"""Activity hooks for CRM relationship entities."""

from __future__ import annotations

from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.crm_relationship import CrmRelationship
from investhome_api.models.user_auth import User
from investhome_api.services.activity_recorder import (
    log_entity_archived,
    log_entity_created,
    log_entity_deleted,
    log_entity_restored,
    log_entity_updated,
)
from investhome_api.services.activity_service import snapshot_entity
from investhome_api.services.crm.relationship_service import CRM_RELATIONSHIP_ACTIVITY_FIELDS


def record_relationship_created(
    db: Session,
    relationship: CrmRelationship,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_entity_created(
        db,
        entity_type=ActivityEntityType.CRM_RELATIONSHIP,
        entity_id=relationship.id,
        description_key="activity.crm_relationship.entity_created",
        actor=actor,
        metadata={
            "relationship_type": relationship.relationship_type,
            "source": f"{relationship.source_entity_type.value}:{relationship.source_entity_id}",
            "target": f"{relationship.target_entity_type.value}:{relationship.target_entity_id}",
        },
        request=request,
    )


def record_relationship_updated(
    db: Session,
    relationship: CrmRelationship,
    actor: User | None,
    before: dict,
    request: Request | None = None,
) -> None:
    after = snapshot_entity(relationship, CRM_RELATIONSHIP_ACTIVITY_FIELDS)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.CRM_RELATIONSHIP,
        entity_id=relationship.id,
        description_key="activity.crm_relationship.entity_updated",
        actor=actor,
        before=before,
        after=after,
        metadata={"relationship_type": relationship.relationship_type},
        request=request,
    )


def record_relationship_archived(
    db: Session,
    relationship: CrmRelationship,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_entity_archived(
        db,
        entity_type=ActivityEntityType.CRM_RELATIONSHIP,
        entity_id=relationship.id,
        description_key="activity.crm_relationship.entity_archived",
        actor=actor,
        metadata={"relationship_type": relationship.relationship_type},
        request=request,
    )


def record_relationship_restored(
    db: Session,
    relationship: CrmRelationship,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_entity_restored(
        db,
        entity_type=ActivityEntityType.CRM_RELATIONSHIP,
        entity_id=relationship.id,
        description_key="activity.crm_relationship.entity_restored",
        actor=actor,
        metadata={"relationship_type": relationship.relationship_type},
        request=request,
    )


def record_relationship_deleted(
    db: Session,
    relationship_id: UUID,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_entity_deleted(
        db,
        entity_type=ActivityEntityType.CRM_RELATIONSHIP,
        entity_id=relationship_id,
        description_key="activity.crm_relationship.entity_deleted",
        actor=actor,
        request=request,
    )
