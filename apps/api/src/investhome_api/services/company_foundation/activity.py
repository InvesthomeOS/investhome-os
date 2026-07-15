"""Company foundation activity hooks."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityAction, ActivityActorType, ActivityEntityType, ActivitySource
from investhome_api.models.company_foundation import CompanyProfile
from investhome_api.models.user_auth import User
from investhome_api.services.activity_service import log_activity


def _log(
    db: Session,
    *,
    action: ActivityAction,
    description_key: str,
    entity_id: UUID,
    actor: User | None = None,
    metadata: dict | None = None,
) -> None:
    log_activity(
        db,
        action=action,
        entity_type=ActivityEntityType.COMPANY,
        entity_id=entity_id,
        description_key=description_key,
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=ActivitySource.WEB if actor else ActivitySource.BACKGROUND_JOB,
        metadata=metadata or {},
    )


def record_company_updated(db: Session, company: CompanyProfile, actor: User, changed_fields: list[str]) -> None:
    _log(
        db,
        action=ActivityAction.UPDATED,
        description_key="activity.company.profile_updated",
        entity_id=company.id,
        actor=actor,
        metadata={"company_name": company.company_name, "changed_fields": changed_fields[:20]},
    )


def record_office_created(db: Session, company: CompanyProfile, actor: User, office_name: str) -> None:
    _log(
        db,
        action=ActivityAction.CREATED,
        description_key="activity.company.office_created",
        entity_id=company.id,
        actor=actor,
        metadata={"office_name": office_name},
    )


def record_office_updated(db: Session, company: CompanyProfile, actor: User, office_name: str) -> None:
    _log(
        db,
        action=ActivityAction.UPDATED,
        description_key="activity.company.office_updated",
        entity_id=company.id,
        actor=actor,
        metadata={"office_name": office_name},
    )


def record_office_archived(db: Session, company: CompanyProfile, actor: User, office_name: str) -> None:
    _log(
        db,
        action=ActivityAction.ARCHIVED,
        description_key="activity.company.office_archived",
        entity_id=company.id,
        actor=actor,
        metadata={"office_name": office_name},
    )


def record_brand_created(db: Session, company: CompanyProfile, actor: User, brand_name: str) -> None:
    _log(
        db,
        action=ActivityAction.CREATED,
        description_key="activity.company.brand_created",
        entity_id=company.id,
        actor=actor,
        metadata={"brand_name": brand_name},
    )


def record_brand_updated(db: Session, company: CompanyProfile, actor: User, brand_name: str) -> None:
    _log(
        db,
        action=ActivityAction.UPDATED,
        description_key="activity.company.brand_updated",
        entity_id=company.id,
        actor=actor,
        metadata={"brand_name": brand_name},
    )


def record_default_brand_changed(db: Session, company: CompanyProfile, actor: User, brand_name: str) -> None:
    _log(
        db,
        action=ActivityAction.UPDATED,
        description_key="activity.company.default_brand_changed",
        entity_id=company.id,
        actor=actor,
        metadata={"brand_name": brand_name},
    )


def record_brand_asset_linked(db: Session, company: CompanyProfile, actor: User, title: str | None) -> None:
    _log(
        db,
        action=ActivityAction.CREATED,
        description_key="activity.company.brand_asset_linked",
        entity_id=company.id,
        actor=actor,
        metadata={"title": title or ""},
    )


def record_preferences_updated(db: Session, company: CompanyProfile, actor: User, keys: list[str]) -> None:
    safe_keys = [k for k in keys if not k.endswith("_secret") and not k.endswith("_api_key")]
    _log(
        db,
        action=ActivityAction.UPDATED,
        description_key="activity.company.preferences_updated",
        entity_id=company.id,
        actor=actor,
        metadata={"keys": safe_keys[:20]},
    )


def record_department_created(db: Session, company: CompanyProfile, actor: User, name: str) -> None:
    _log(
        db,
        action=ActivityAction.CREATED,
        description_key="activity.company.department_created",
        entity_id=company.id,
        actor=actor,
        metadata={"department_name": name},
    )


def record_team_created(db: Session, company: CompanyProfile, actor: User, name: str) -> None:
    _log(
        db,
        action=ActivityAction.CREATED,
        description_key="activity.company.team_created",
        entity_id=company.id,
        actor=actor,
        metadata={"team_name": name},
    )


def record_user_org_assignment(db: Session, company: CompanyProfile, actor: User, user_id: UUID) -> None:
    _log(
        db,
        action=ActivityAction.UPDATED,
        description_key="activity.company.user_org_assignment_changed",
        entity_id=company.id,
        actor=actor,
        metadata={"user_id": str(user_id)},
    )
