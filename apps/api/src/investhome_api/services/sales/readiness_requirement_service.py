"""Requirement-level operations — verify, reject, waive, reopen."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.sales_readiness import (
    ReadinessRequirementStatus,
    ReadinessSourceEntityType,
    SalesReadinessCase,
    SalesReadinessRequirement,
)
from investhome_api.models.user_auth import User
from investhome_api.services.activity_recorder import log_entity_updated
from investhome_api.services.permission_service import user_has_permission
from investhome_api.services.sales.readiness_config import FINANCE_REQUIREMENT_TYPES, LEGAL_REQUIREMENT_TYPES
from investhome_api.services.sales import readiness_notifications as notify


class ReadinessRequirementError(ValueError):
    def __init__(self, error_key: str, *, status_code: int = 422) -> None:
        self.error_key = error_key
        self.status_code = status_code
        super().__init__(error_key)


def _now() -> datetime:
    return datetime.now(UTC)


def get_requirement_or_raise(
    db: Session,
    requirement_id: UUID,
    *,
    case_id: UUID | None = None,
) -> SalesReadinessRequirement:
    req = db.get(SalesReadinessRequirement, requirement_id)
    if req is None:
        raise ReadinessRequirementError("sales.readiness.errors.requirement_not_found", status_code=404)
    if case_id and req.readiness_case_id != case_id:
        raise ReadinessRequirementError("sales.readiness.errors.requirement_not_found", status_code=404)
    return req


def can_waive_requirement(user: User, requirement: SalesReadinessRequirement) -> bool:
    if not user_has_permission(user, "sales", "waive_requirement"):
        return False
    if requirement.requirement_type in LEGAL_REQUIREMENT_TYPES:
        return user_has_permission(user, "sales", "verify_readiness") and (
            user_has_permission(user, "sales", "approve_handoff")
            or user_has_permission(user, "executive", "view")
        )
    if requirement.requirement_type in FINANCE_REQUIREMENT_TYPES:
        return user_has_permission(user, "sales", "view_deposit_status") and (
            user_has_permission(user, "finance", "approve")
            or user_has_permission(user, "sales", "approve_handoff")
        )
    return True


def verify_requirement(
    db: Session,
    requirement: SalesReadinessRequirement,
    *,
    actor: User,
    notes: str | None = None,
    request: Request | None = None,
) -> SalesReadinessRequirement:
    if not user_has_permission(actor, "sales", "verify_readiness"):
        raise ReadinessRequirementError("sales.readiness.errors.permission_denied", status_code=403)
    before = {"status": requirement.status.value}
    requirement.status = ReadinessRequirementStatus.VERIFIED
    requirement.verified_at = _now()
    requirement.verified_by_user_id = actor.id
    requirement.blocked_reason = None
    if notes:
        requirement.notes = notes
    requirement.updated_at = _now()
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_READINESS,
        entity_id=requirement.readiness_case_id,
        description_key="activity.sales.readiness.requirement_verified",
        actor=actor,
        before=before,
        after={"status": requirement.status.value, "requirement_type": requirement.requirement_type.value},
        metadata={"requirement_id": str(requirement.id)},
        request=request,
    )
    db.flush()
    return requirement


def reject_requirement(
    db: Session,
    requirement: SalesReadinessRequirement,
    *,
    actor: User,
    reason: str,
    request: Request | None = None,
) -> SalesReadinessRequirement:
    if not user_has_permission(actor, "sales", "verify_readiness"):
        raise ReadinessRequirementError("sales.readiness.errors.permission_denied", status_code=403)
    before = {"status": requirement.status.value}
    requirement.status = ReadinessRequirementStatus.REJECTED
    requirement.blocked_reason = reason
    requirement.verified_at = None
    requirement.verified_by_user_id = None
    requirement.updated_at = _now()
    case = db.get(SalesReadinessCase, requirement.readiness_case_id)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_READINESS,
        entity_id=requirement.readiness_case_id,
        description_key="activity.sales.readiness.requirement_rejected",
        actor=actor,
        before=before,
        after={"status": requirement.status.value, "reason": reason},
        metadata={"requirement_id": str(requirement.id)},
        request=request,
    )
    if case:
        notify.notify_requirement_rejected(db, case, requirement)
    db.flush()
    return requirement


def waive_requirement(
    db: Session,
    requirement: SalesReadinessRequirement,
    *,
    actor: User,
    reason: str,
    request: Request | None = None,
) -> SalesReadinessRequirement:
    if not can_waive_requirement(actor, requirement):
        raise ReadinessRequirementError("sales.readiness.errors.waiver_not_allowed", status_code=403)
    if not reason.strip():
        raise ReadinessRequirementError("sales.readiness.errors.waiver_reason_required")
    before = {"status": requirement.status.value}
    requirement.status = ReadinessRequirementStatus.WAIVED
    requirement.waiver_reason = reason
    requirement.waiver_by_user_id = actor.id
    requirement.waiver_at = _now()
    requirement.blocked_reason = None
    requirement.updated_at = _now()
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_READINESS,
        entity_id=requirement.readiness_case_id,
        description_key="activity.sales.readiness.requirement_waived",
        actor=actor,
        before=before,
        after={"status": requirement.status.value, "waiver_reason": reason},
        metadata={"requirement_id": str(requirement.id)},
        request=request,
    )
    db.flush()
    return requirement


def reopen_requirement(
    db: Session,
    requirement: SalesReadinessRequirement,
    *,
    actor: User,
    reason: str | None = None,
    request: Request | None = None,
) -> SalesReadinessRequirement:
    if not user_has_permission(actor, "sales", "update_readiness"):
        raise ReadinessRequirementError("sales.readiness.errors.permission_denied", status_code=403)
    before = {"status": requirement.status.value}
    requirement.status = ReadinessRequirementStatus.PENDING
    requirement.waiver_reason = None
    requirement.waiver_by_user_id = None
    requirement.waiver_at = None
    requirement.verified_at = None
    requirement.verified_by_user_id = None
    requirement.blocked_reason = reason
    requirement.updated_at = _now()
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_READINESS,
        entity_id=requirement.readiness_case_id,
        description_key="activity.sales.readiness.requirement_reopened",
        actor=actor,
        before=before,
        after={"status": requirement.status.value},
        metadata={"requirement_id": str(requirement.id)},
        request=request,
    )
    db.flush()
    return requirement


def link_source(
    db: Session,
    requirement: SalesReadinessRequirement,
    *,
    source_entity_type: ReadinessSourceEntityType,
    source_entity_id: UUID,
    actor: User,
    request: Request | None = None,
) -> SalesReadinessRequirement:
    if not user_has_permission(actor, "sales", "update_readiness"):
        raise ReadinessRequirementError("sales.readiness.errors.permission_denied", status_code=403)
    requirement.source_entity_type = source_entity_type
    requirement.source_entity_id = source_entity_id
    if requirement.status == ReadinessRequirementStatus.MISSING:
        requirement.status = ReadinessRequirementStatus.RECEIVED
    requirement.updated_at = _now()
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_READINESS,
        entity_id=requirement.readiness_case_id,
        description_key="activity.sales.readiness.source_linked",
        actor=actor,
        before={},
        after={
            "source_entity_type": source_entity_type.value,
            "source_entity_id": str(source_entity_id),
        },
        metadata={"requirement_id": str(requirement.id)},
        request=request,
    )
    db.flush()
    return requirement


def unlink_source(
    db: Session,
    requirement: SalesReadinessRequirement,
    *,
    actor: User,
    request: Request | None = None,
) -> SalesReadinessRequirement:
    if not user_has_permission(actor, "sales", "update_readiness"):
        raise ReadinessRequirementError("sales.readiness.errors.permission_denied", status_code=403)
    requirement.source_entity_type = None
    requirement.source_entity_id = None
    requirement.updated_at = _now()
    db.flush()
    return requirement


def list_requirements(db: Session, case_id: UUID) -> list[SalesReadinessRequirement]:
    return list(
        db.scalars(
            select(SalesReadinessRequirement)
            .where(SalesReadinessRequirement.readiness_case_id == case_id)
            .order_by(SalesReadinessRequirement.template_group, SalesReadinessRequirement.created_at)
        ).all()
    )


def add_manual_requirement(
    db: Session,
    case: SalesReadinessCase,
    data: dict[str, Any],
    *,
    actor: User,
) -> SalesReadinessRequirement:
    if not user_has_permission(actor, "sales", "update_readiness"):
        raise ReadinessRequirementError("sales.readiness.errors.permission_denied", status_code=403)
    req = SalesReadinessRequirement(
        readiness_case_id=case.id,
        requirement_type=data["requirement_type"],
        template_group=data.get("template_group"),
        title=data["title"],
        description=data.get("description"),
        is_mandatory=data.get("is_mandatory", False),
        status=ReadinessRequirementStatus.MISSING,
        due_at=data.get("due_at"),
    )
    db.add(req)
    db.flush()
    return req
