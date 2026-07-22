"""Marketing Brand Center API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_content_studio import (
    BrandProfileCreate,
    BrandProfileUpdate,
    ClaimCreate,
    ComplianceCheckRequest,
    TerminologyCreate,
)
from investhome_api.services.marketing.content_studio_serializers import brand_profile_dict, claim_dict, compliance_dict, terminology_dict
from investhome_api.services.marketing.brand_service import (
    add_terminology,
    create_brand_profile,
    get_brand_profile,
    get_default_brand_profile,
    list_approved_claims,
    list_brand_profiles,
    list_prohibited_claims,
    list_terminology,
    run_compliance_check,
    update_brand_profile,
)
from investhome_api.models.marketing_content_studio import ApprovedClaim, ProhibitedClaim

router = APIRouter(prefix="/marketing/brand", tags=["marketing-brand"])


@router.get("")
def brand_overview(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_brand")),
) -> dict:
    profiles = list_brand_profiles(db)
    default_profile = get_default_brand_profile(db)
    return {
        "profiles": profiles,
        "default_profile_id": str(default_profile.id) if default_profile else None,
        "profile_count": len(profiles),
    }


@router.get("/profiles")
def list_profiles(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_brand")),
) -> dict:
    return {"items": list_brand_profiles(db)}


@router.post("/profiles", status_code=status.HTTP_201_CREATED)
def create_profile(
    body: BrandProfileCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_brand")),
) -> dict:
    profile = create_brand_profile(db, payload=body.model_dump(), actor=user)
    db.commit()
    db.refresh(profile)
    return {"profile": brand_profile_dict(profile)}


@router.get("/profiles/{profile_id}")
def get_profile(
    profile_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_brand")),
) -> dict:
    return brand_profile_dict(get_brand_profile(db, profile_id))


@router.put("/profiles/{profile_id}")
def update_profile(
    profile_id: UUID,
    body: BrandProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_brand")),
) -> dict:
    profile = get_brand_profile(db, profile_id)
    update_brand_profile(db, profile, payload=body.model_dump(exclude_unset=True), actor=user)
    db.commit()
    db.refresh(profile)
    return {"profile": brand_profile_dict(profile)}


@router.get("/profiles/{profile_id}/guidelines")
def get_guidelines(
    profile_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_brand")),
) -> dict:
    profile = get_brand_profile(db, profile_id)
    return {
        "guidelines_json": profile.guidelines_json,
        "colors_json": profile.colors_json,
        "typography_json": profile.typography_json,
        "voice_json": profile.voice_json,
    }


@router.get("/profiles/{profile_id}/logos")
def get_logos(
    profile_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_brand")),
) -> dict:
    profile = get_brand_profile(db, profile_id)
    return {"logo_asset_ids": profile.logo_asset_ids or []}


@router.get("/profiles/{profile_id}/terminology")
def get_terminology(
    profile_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_brand")),
) -> dict:
    get_brand_profile(db, profile_id)
    return {"items": [terminology_dict(t) for t in list_terminology(db, profile_id)]}


@router.post("/profiles/{profile_id}/terminology", status_code=status.HTTP_201_CREATED)
def create_terminology(
    profile_id: UUID,
    body: TerminologyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_brand")),
) -> dict:
    get_brand_profile(db, profile_id)
    term = add_terminology(db, profile_id, payload=body.model_dump())
    db.commit()
    db.refresh(term)
    return {"terminology": terminology_dict(term)}


@router.get("/profiles/{profile_id}/claims/approved")
def approved_claims(
    profile_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_brand")),
) -> dict:
    get_brand_profile(db, profile_id)
    return {"items": [claim_dict(c) for c in list_approved_claims(db, profile_id)]}


@router.post("/profiles/{profile_id}/claims/approved", status_code=status.HTTP_201_CREATED)
def create_approved_claim(
    profile_id: UUID,
    body: ClaimCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_brand")),
) -> dict:
    get_brand_profile(db, profile_id)
    claim = ApprovedClaim(
        brand_profile_id=profile_id,
        claim_text=body.claim_text,
        category=body.category,
        evidence_ref=body.evidence_ref,
        valid_until=body.valid_until,
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return {"claim": claim_dict(claim)}


@router.get("/profiles/{profile_id}/claims/prohibited")
def prohibited_claims(
    profile_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_brand")),
) -> dict:
    get_brand_profile(db, profile_id)
    return {"items": [claim_dict(c) for c in list_prohibited_claims(db, profile_id)]}


@router.post("/profiles/{profile_id}/claims/prohibited", status_code=status.HTTP_201_CREATED)
def create_prohibited_claim(
    profile_id: UUID,
    body: ClaimCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_brand")),
) -> dict:
    get_brand_profile(db, profile_id)
    claim = ProhibitedClaim(
        brand_profile_id=profile_id,
        claim_text=body.claim_text,
        reason=body.reason,
        severity=body.severity,
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return {"claim": claim_dict(claim)}


@router.post("/compliance-check")
def compliance_check(
    body: ComplianceCheckRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_brand")),
) -> dict:
    result = run_compliance_check(
        db,
        content_id=body.content_id,
        version_id=body.version_id,
        brand_profile_id=body.brand_profile_id,
        body_text=body.body_text,
        actor=user,
    )
    db.commit()
    db.refresh(result)
    return {"result": compliance_dict(result)}
