"""Marketing Brand Center service."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.marketing_content_studio import (
    ApprovedClaim,
    BrandComplianceResult,
    BrandTerminology,
    MarketingBrandProfile,
    ProhibitedClaim,
)
from investhome_api.models.user_auth import User
from investhome_api.services.marketing.campaign_service import compute_pages


def _profile_summary(profile: MarketingBrandProfile) -> dict:
    return {
        "id": profile.id,
        "name": profile.name,
        "description": profile.description,
        "status": profile.status,
        "is_default": profile.is_default,
        "company_brand_id": profile.company_brand_id,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }


def _profile_detail(profile: MarketingBrandProfile) -> dict:
    return {
        **_profile_summary(profile),
        "colors_json": profile.colors_json,
        "typography_json": profile.typography_json,
        "voice_json": profile.voice_json,
        "guidelines_json": profile.guidelines_json,
        "logo_asset_ids": profile.logo_asset_ids,
        "archived_at": profile.archived_at,
    }


def get_brand_profile(db: Session, profile_id: UUID) -> MarketingBrandProfile:
    profile = db.get(MarketingBrandProfile, profile_id)
    if profile is None or profile.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand profile not found")
    return profile


def get_default_brand_profile(db: Session) -> MarketingBrandProfile | None:
    return db.scalar(
        select(MarketingBrandProfile).where(
            MarketingBrandProfile.is_default.is_(True),
            MarketingBrandProfile.archived_at.is_(None),
        )
    )


def list_brand_profiles(db: Session) -> list[dict]:
    rows = db.scalars(
        select(MarketingBrandProfile)
        .where(MarketingBrandProfile.archived_at.is_(None))
        .order_by(MarketingBrandProfile.name)
    ).all()
    return [_profile_summary(row) for row in rows]


def create_brand_profile(db: Session, *, payload: dict, actor: User) -> MarketingBrandProfile:
    profile = MarketingBrandProfile(
        name=payload["name"],
        description=payload.get("description"),
        company_brand_id=payload.get("company_brand_id"),
        colors_json=payload.get("colors_json"),
        typography_json=payload.get("typography_json"),
        voice_json=payload.get("voice_json"),
        guidelines_json=payload.get("guidelines_json"),
        logo_asset_ids=payload.get("logo_asset_ids"),
        is_default=payload.get("is_default", False),
        created_by_user_id=actor.id,
        updated_by_user_id=actor.id,
    )
    if profile.is_default:
        for existing in db.scalars(select(MarketingBrandProfile)).all():
            existing.is_default = False
    db.add(profile)
    return profile


def update_brand_profile(db: Session, profile: MarketingBrandProfile, *, payload: dict, actor: User) -> MarketingBrandProfile:
    for field in (
        "name", "description", "company_brand_id", "colors_json", "typography_json",
        "voice_json", "guidelines_json", "logo_asset_ids", "status",
    ):
        if field in payload:
            setattr(profile, field, payload[field])
    if payload.get("is_default"):
        for existing in db.scalars(select(MarketingBrandProfile)).all():
            existing.is_default = existing.id == profile.id
    profile.updated_by_user_id = actor.id
    return profile


def list_terminology(db: Session, profile_id: UUID) -> list[BrandTerminology]:
    return list(
        db.scalars(
            select(BrandTerminology)
            .where(BrandTerminology.brand_profile_id == profile_id, BrandTerminology.is_active.is_(True))
            .order_by(BrandTerminology.term)
        ).all()
    )


def add_terminology(db: Session, profile_id: UUID, *, payload: dict) -> BrandTerminology:
    term = BrandTerminology(brand_profile_id=profile_id, **payload)
    db.add(term)
    return term


def list_approved_claims(db: Session, profile_id: UUID) -> list[ApprovedClaim]:
    rows = db.scalars(
        select(ApprovedClaim).where(ApprovedClaim.brand_profile_id == profile_id)
    ).all()
    return [row for row in rows if row.is_active]


def list_prohibited_claims(db: Session, profile_id: UUID) -> list[ProhibitedClaim]:
    rows = db.scalars(
        select(ProhibitedClaim).where(ProhibitedClaim.brand_profile_id == profile_id)
    ).all()
    return [row for row in rows if row.is_active]


def run_compliance_check(
    db: Session,
    *,
    content_id: UUID | None,
    version_id: UUID | None,
    brand_profile_id: UUID | None,
    body_text: str,
    actor: User,
) -> BrandComplianceResult:
    profile = get_brand_profile(db, brand_profile_id) if brand_profile_id else get_default_brand_profile(db)
    violations: list[dict] = []
    warnings: list[dict] = []
    if profile:
        prohibited = list_prohibited_claims(db, profile.id)
        for claim in prohibited:
            if claim.claim_text.lower() in body_text.lower():
                entry = {"claim": claim.claim_text, "severity": claim.severity, "reason": claim.reason}
                if claim.severity == "error":
                    violations.append(entry)
                else:
                    warnings.append(entry)
    result_status = "passed"
    if violations:
        result_status = "failed"
    elif warnings:
        result_status = "warning"
    result = BrandComplianceResult(
        content_id=content_id,
        version_id=version_id,
        brand_profile_id=profile.id if profile else None,
        status=result_status,
        violations_json=violations or None,
        warnings_json=warnings or None,
        checked_by_user_id=actor.id,
    )
    db.add(result)
    return result
