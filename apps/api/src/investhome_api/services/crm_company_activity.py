"""Activity hooks for CRM company entities."""

from __future__ import annotations

from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityAction, ActivityActorType, ActivityEntityType, ActivitySource
from investhome_api.models.crm_company import CrmCompany
from investhome_api.models.user_auth import User
from investhome_api.services.activity_recorder import (
    activity_context_from_request,
    log_entity_archived,
    log_entity_created,
    log_entity_updated,
)
from investhome_api.services.activity_service import log_activity, snapshot_entity


CRM_COMPANY_ACTIVITY_FIELDS = [
    "display_name",
    "legal_name",
    "company_type",
    "status",
    "lifecycle_stage",
    "primary_email",
    "domain",
    "industry",
    "owner_user_id",
    "parent_company_id",
]


def record_crm_company_created(
    db: Session,
    company: CrmCompany,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_entity_created(
        db,
        entity_type=ActivityEntityType.CRM_COMPANY,
        entity_id=company.id,
        description_key="activity.crm_company.entity_created",
        actor=actor,
        metadata={"display_name": company.display_name},
        request=request,
    )


def record_crm_company_updated(
    db: Session,
    company: CrmCompany,
    actor: User | None,
    before: dict,
    request: Request | None = None,
) -> None:
    after = snapshot_entity(company, CRM_COMPANY_ACTIVITY_FIELDS)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.CRM_COMPANY,
        entity_id=company.id,
        description_key="activity.crm_company.entity_updated",
        actor=actor,
        before=before,
        after=after,
        metadata={"display_name": company.display_name},
        request=request,
    )


def record_crm_company_archived(
    db: Session,
    company: CrmCompany,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_entity_archived(
        db,
        entity_type=ActivityEntityType.CRM_COMPANY,
        entity_id=company.id,
        description_key="activity.crm_company.entity_archived",
        actor=actor,
        metadata={"display_name": company.display_name},
        request=request,
    )


def record_crm_company_restored(
    db: Session,
    company: CrmCompany,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.RESTORED,
        entity_type=ActivityEntityType.CRM_COMPANY,
        entity_id=company.id,
        description_key="activity.crm_company.entity_restored",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=activity_context_from_request(request).source or ActivitySource.API,
        metadata={"display_name": company.display_name},
        request_context=activity_context_from_request(request),
    )


def record_crm_company_deleted(
    db: Session,
    company_id: UUID,
    display_name: str,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.DELETED,
        entity_type=ActivityEntityType.CRM_COMPANY,
        entity_id=company_id,
        description_key="activity.crm_company.entity_deleted",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=activity_context_from_request(request).source or ActivitySource.API,
        metadata={"display_name": display_name},
        request_context=activity_context_from_request(request),
    )


def record_crm_company_merged(
    db: Session,
    target: CrmCompany,
    source_id: UUID,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.CRM_COMPANY,
        entity_id=target.id,
        description_key="activity.crm_company.entity_merged",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=activity_context_from_request(request).source or ActivitySource.API,
        metadata={"display_name": target.display_name, "merged_from_id": str(source_id)},
        request_context=activity_context_from_request(request),
    )


def record_crm_company_ownership_changed(
    db: Session,
    company: CrmCompany,
    actor: User | None,
    previous_owner_id: UUID | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.CRM_COMPANY,
        entity_id=company.id,
        description_key="activity.crm_company.ownership_changed",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=activity_context_from_request(request).source or ActivitySource.API,
        metadata={
            "display_name": company.display_name,
            "previous_owner_id": str(previous_owner_id) if previous_owner_id else None,
            "new_owner_id": str(company.owner_user_id) if company.owner_user_id else None,
        },
        request_context=activity_context_from_request(request),
    )
