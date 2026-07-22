"""Activity hooks for managed company entities."""

from __future__ import annotations

from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.company import Company
from investhome_api.models.user_auth import User
from investhome_api.services.activity_recorder import (
    activity_context_from_request,
    log_entity_archived,
    log_entity_created,
    log_entity_updated,
)
from investhome_api.services.activity_service import log_activity, snapshot_entity
from investhome_api.models.activity import ActivityAction, ActivityActorType, ActivitySource


COMPANY_ACTIVITY_FIELDS = [
    "company_name",
    "legal_name",
    "entity_type",
    "registration_number",
    "tax_id",
    "country",
    "state",
    "city",
    "status",
    "industry",
    "owner_user_id",
]


def record_company_created(
    db: Session,
    company: Company,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_entity_created(
        db,
        entity_type=ActivityEntityType.COMPANY,
        entity_id=company.id,
        description_key="activity.company.entity_created",
        actor=actor,
        metadata={"company_name": company.company_name},
        request=request,
    )


def record_company_updated(
    db: Session,
    company: Company,
    actor: User | None,
    before: dict,
    request: Request | None = None,
) -> None:
    after = snapshot_entity(company, COMPANY_ACTIVITY_FIELDS)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.COMPANY,
        entity_id=company.id,
        description_key="activity.company.entity_updated",
        actor=actor,
        before=before,
        after=after,
        metadata={"company_name": company.company_name},
        request=request,
    )


def record_company_status_changed(
    db: Session,
    company: Company,
    actor: User | None,
    previous_status: str,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.COMPANY,
        entity_id=company.id,
        description_key="activity.company.status_changed",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=activity_context_from_request(request).source or ActivitySource.API,
        metadata={
            "company_name": company.company_name,
            "previous_status": previous_status,
            "new_status": company.status,
        },
        request_context=activity_context_from_request(request),
    )


def record_company_ownership_changed(
    db: Session,
    company: Company,
    actor: User | None,
    previous_owner_id: UUID | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.COMPANY,
        entity_id=company.id,
        description_key="activity.company.ownership_changed",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=activity_context_from_request(request).source or ActivitySource.API,
        metadata={
            "company_name": company.company_name,
            "previous_owner_id": str(previous_owner_id) if previous_owner_id else None,
            "new_owner_id": str(company.owner_user_id) if company.owner_user_id else None,
        },
        request_context=activity_context_from_request(request),
    )


def record_company_archived(
    db: Session,
    company: Company,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_entity_archived(
        db,
        entity_type=ActivityEntityType.COMPANY,
        entity_id=company.id,
        description_key="activity.company.entity_archived",
        actor=actor,
        metadata={"company_name": company.company_name},
        request=request,
    )


def record_company_document_added(
    db: Session,
    company: Company,
    actor: User | None,
    title: str,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.CREATED,
        entity_type=ActivityEntityType.COMPANY,
        entity_id=company.id,
        description_key="activity.company.document_added",
        actor_user=actor,
        metadata={"company_name": company.company_name, "document_title": title},
        request_context=activity_context_from_request(request),
    )


def record_company_document_removed(
    db: Session,
    company: Company,
    actor: User | None,
    title: str,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.DELETED,
        entity_type=ActivityEntityType.COMPANY,
        entity_id=company.id,
        description_key="activity.company.document_removed",
        actor_user=actor,
        metadata={"company_name": company.company_name, "document_title": title},
        request_context=activity_context_from_request(request),
    )
