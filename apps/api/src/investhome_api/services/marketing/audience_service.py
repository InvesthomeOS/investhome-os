"""Marketing audience management service."""

from __future__ import annotations

import math
from copy import deepcopy
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from investhome_api.models.marketing import (
    AudienceConsentRequirement,
    AudienceMembership,
    AudienceSavedView,
    MarketingAudience,
    MarketingAudienceMode,
    MarketingAudienceStatus,
    MarketingAudienceType,
    MembershipExclusionReason,
    MembershipInclusionSource,
)
from investhome_api.models.user_auth import User
from investhome_api.services.marketing.consent_eligibility_service import (
    resolve_membership_eligibility,
    validate_audience_consent,
)
from investhome_api.services.marketing.campaign_service import compute_pages


def _get_audience_or_404(db: Session, audience_id: UUID) -> MarketingAudience:
    audience = db.get(MarketingAudience, audience_id)
    if audience is None or audience.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audience not found")
    return audience


def list_audiences(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    mode: str | None = None,
    status_filter: str | None = None,
    include_archived: bool = False,
) -> tuple[list[MarketingAudience], int]:
    query = select(MarketingAudience)
    if not include_archived:
        query = query.where(MarketingAudience.archived_at.is_(None))
    if search:
        query = query.where(MarketingAudience.name.ilike(f"%{search}%"))
    if mode:
        query = query.where(MarketingAudience.mode == MarketingAudienceMode(mode))
    if status_filter:
        query = query.where(MarketingAudience.status == MarketingAudienceStatus(status_filter))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(MarketingAudience.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(rows), total


def get_audience_summary(db: Session) -> dict:
    active = db.scalar(
        select(func.count()).where(
            MarketingAudience.archived_at.is_(None),
            MarketingAudience.status == MarketingAudienceStatus.ACTIVE,
        )
    ) or 0
    draft = db.scalar(
        select(func.count()).where(
            MarketingAudience.archived_at.is_(None),
            MarketingAudience.status == MarketingAudienceStatus.DRAFT,
        )
    ) or 0
    total = db.scalar(select(func.count()).where(MarketingAudience.archived_at.is_(None))) or 0
    return {"active": active, "draft": draft, "total": total}


def create_audience(db: Session, user: User, payload: dict) -> MarketingAudience:
    audience = MarketingAudience(
        name=payload["name"],
        description=payload.get("description"),
        audience_type=MarketingAudienceType(payload["audience_type"]),
        mode=MarketingAudienceMode(payload.get("mode", "static")),
        status=MarketingAudienceStatus.DRAFT,
        source=payload.get("source"),
        contact_ids=payload.get("contact_ids"),
        company_ids=payload.get("company_ids"),
        segment_ids=payload.get("segment_ids"),
        inclusion_refs_json=payload.get("inclusion_refs_json"),
        exclusion_refs_json=payload.get("exclusion_refs_json"),
        consent_json=payload.get("consent_json"),
        consent_requirements_json=payload.get("consent_requirements_json"),
        channel_eligibility_json=payload.get("channel_eligibility_json"),
        geo_json=payload.get("geo_json"),
        refresh_policy_json=payload.get("refresh_policy_json"),
        channel_ids=payload.get("channel_ids"),
        language=payload.get("language"),
        created_by_user_id=user.id,
    )
    db.add(audience)
    db.flush()
    _sync_explicit_memberships(db, audience)
    return audience


def update_audience(db: Session, audience_id: UUID, user: User, payload: dict) -> MarketingAudience:
    audience = _get_audience_or_404(db, audience_id)
    for key in (
        "name", "description", "source", "contact_ids", "company_ids", "segment_ids",
        "inclusion_refs_json", "exclusion_refs_json", "consent_json", "consent_requirements_json",
        "channel_eligibility_json", "geo_json", "refresh_policy_json", "channel_ids", "language",
    ):
        if key in payload:
            setattr(audience, key, payload[key])
    if "audience_type" in payload:
        audience.audience_type = MarketingAudienceType(payload["audience_type"])
    if "mode" in payload:
        audience.mode = MarketingAudienceMode(payload["mode"])
    audience.updated_by_user_id = user.id
    db.flush()
    if "contact_ids" in payload or "company_ids" in payload:
        _sync_explicit_memberships(db, audience)
    return audience


def _sync_explicit_memberships(db: Session, audience: MarketingAudience) -> None:
    """Sync explicit contact/company refs to AudienceMembership."""
    contact_ids = audience.contact_ids or []
    company_ids = audience.company_ids or []
    existing = db.scalars(
        select(AudienceMembership).where(
            AudienceMembership.audience_id == audience.id,
            AudienceMembership.inclusion_source == MembershipInclusionSource.EXPLICIT,
        )
    ).all()
    existing_keys = {(str(m.contact_id), str(m.company_id)) for m in existing}
    new_keys: set[tuple[str | None, str | None]] = set()
    for cid in contact_ids:
        new_keys.add((str(cid), None))
    for cid in company_ids:
        new_keys.add((None, str(cid)))

    for m in existing:
        key = (str(m.contact_id) if m.contact_id else None, str(m.company_id) if m.company_id else None)
        if key not in new_keys:
            db.delete(m)

    channel = (audience.channel_eligibility_json or {}).get("primary_channel", "email")
    for contact_id in contact_ids:
        key = (str(contact_id), None)
        if key not in existing_keys:
            eligible, explain = resolve_membership_eligibility(
                db, contact_id=UUID(str(contact_id)), company_id=None, channel=channel
            )
            db.add(
                AudienceMembership(
                    audience_id=audience.id,
                    contact_id=UUID(str(contact_id)),
                    is_included=eligible,
                    inclusion_source=MembershipInclusionSource.EXPLICIT,
                    exclusion_reason=None if eligible else MembershipExclusionReason.CONSENT,
                    eligibility_json={"eligible": eligible},
                    explainability_json=explain,
                )
            )
    for company_id in company_ids:
        key = (None, str(company_id))
        if key not in existing_keys:
            eligible, explain = resolve_membership_eligibility(
                db, contact_id=None, company_id=UUID(str(company_id)), channel=channel
            )
            db.add(
                AudienceMembership(
                    audience_id=audience.id,
                    company_id=UUID(str(company_id)),
                    is_included=eligible,
                    inclusion_source=MembershipInclusionSource.EXPLICIT,
                    exclusion_reason=None if eligible else MembershipExclusionReason.CONSENT,
                    eligibility_json={"eligible": eligible},
                    explainability_json=explain,
                )
            )


def get_audience_members(
    db: Session,
    audience_id: UUID,
    *,
    page: int = 1,
    page_size: int = 25,
    included_only: bool | None = None,
) -> tuple[list[AudienceMembership], int]:
    _get_audience_or_404(db, audience_id)
    query = select(AudienceMembership).where(AudienceMembership.audience_id == audience_id)
    if included_only is True:
        query = query.where(AudienceMembership.is_included.is_(True))
    elif included_only is False:
        query = query.where(AudienceMembership.is_included.is_(False))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return list(rows), total


def add_audience_member(
    db: Session,
    audience_id: UUID,
    *,
    contact_id: UUID | None = None,
    company_id: UUID | None = None,
) -> AudienceMembership:
    audience = _get_audience_or_404(db, audience_id)
    if not contact_id and not company_id:
        raise HTTPException(status_code=400, detail="contact_id or company_id required")
    channel = (audience.channel_eligibility_json or {}).get("primary_channel", "email")
    eligible, explain = resolve_membership_eligibility(
        db, contact_id=contact_id, company_id=company_id, channel=channel
    )
    membership = AudienceMembership(
        audience_id=audience_id,
        contact_id=contact_id,
        company_id=company_id,
        is_included=eligible,
        inclusion_source=MembershipInclusionSource.EXPLICIT,
        exclusion_reason=None if eligible else MembershipExclusionReason.CONSENT,
        eligibility_json={"eligible": eligible},
        explainability_json=explain,
    )
    db.add(membership)
    db.flush()
    return membership


def exclude_audience_member(db: Session, audience_id: UUID, membership_id: UUID) -> AudienceMembership:
    _get_audience_or_404(db, audience_id)
    membership = db.get(AudienceMembership, membership_id)
    if membership is None or membership.audience_id != audience_id:
        raise HTTPException(status_code=404, detail="Membership not found")
    membership.is_included = False
    membership.exclusion_reason = MembershipExclusionReason.EXPLICIT
    membership.explainability_json = {
        **(membership.explainability_json or {}),
        "reason": "explicit_exclusion",
        "precedence_level": "explicit_exclusion",
    }
    return membership


def refresh_audience(db: Session, audience_id: UUID) -> MarketingAudience:
    audience = _get_audience_or_404(db, audience_id)
    _sync_explicit_memberships(db, audience)
    included_count = db.scalar(
        select(func.count()).where(
            AudienceMembership.audience_id == audience_id,
            AudienceMembership.is_included.is_(True),
        )
    )
    audience.calculated_size = included_count
    audience.last_refreshed_at = datetime.now(tz=UTC)
    return audience


def get_audience_readiness(db: Session, audience_id: UUID) -> dict:
    audience = _get_audience_or_404(db, audience_id)
    required_channels = []
    if audience.consent_requirements_json:
        required_channels = audience.consent_requirements_json.get("channels", ["email"])
    elif audience.channel_eligibility_json:
        ch = audience.channel_eligibility_json.get("primary_channel")
        if ch:
            required_channels = [ch]
    else:
        required_channels = ["email"]
    consent_check = validate_audience_consent(db, audience_id, required_channels)
    member_count = audience.calculated_size
    state = "ready"
    blockers: list[str] = []
    if member_count is None:
        state = "not_calculated"
        blockers.append("membership_not_calculated")
    elif member_count == 0:
        state = "warning"
        blockers.append("empty_audience")
    if not consent_check["ready"]:
        state = "blocked"
        if consent_check["unknown_consent_count"]:
            blockers.append("unknown_consent")
        if consent_check["blocked_count"]:
            blockers.append("consent_blocked")
    return {
        "audience_id": str(audience_id),
        "state": state,
        "blockers": blockers,
        "member_count": member_count,
        "consent_check": consent_check,
    }


def duplicate_audience(db: Session, audience_id: UUID, user: User, name: str | None = None) -> MarketingAudience:
    source = _get_audience_or_404(db, audience_id)
    clone = MarketingAudience(
        name=name or f"{source.name} (Copy)",
        description=source.description,
        audience_type=source.audience_type,
        mode=source.mode,
        status=MarketingAudienceStatus.DRAFT,
        source=source.source,
        contact_ids=deepcopy(source.contact_ids),
        company_ids=deepcopy(source.company_ids),
        segment_ids=deepcopy(source.segment_ids),
        inclusion_refs_json=deepcopy(source.inclusion_refs_json),
        exclusion_refs_json=deepcopy(source.exclusion_refs_json),
        consent_json=deepcopy(source.consent_json),
        consent_requirements_json=deepcopy(source.consent_requirements_json),
        channel_eligibility_json=deepcopy(source.channel_eligibility_json),
        geo_json=deepcopy(source.geo_json),
        refresh_policy_json=deepcopy(source.refresh_policy_json),
        channel_ids=deepcopy(source.channel_ids),
        language=source.language,
        created_by_user_id=user.id,
    )
    db.add(clone)
    db.flush()
    _sync_explicit_memberships(db, clone)
    return clone


def archive_audience(db: Session, audience_id: UUID) -> MarketingAudience:
    audience = _get_audience_or_404(db, audience_id)
    audience.status = MarketingAudienceStatus.ARCHIVED
    audience.archived_at = datetime.now(tz=UTC)
    return audience


def restore_audience(db: Session, audience_id: UUID) -> MarketingAudience:
    audience = db.get(MarketingAudience, audience_id)
    if audience is None:
        raise HTTPException(status_code=404, detail="Audience not found")
    audience.status = MarketingAudienceStatus.DRAFT
    audience.archived_at = None
    return audience


def list_saved_views(db: Session, user_id: UUID) -> list[AudienceSavedView]:
    return list(
        db.scalars(
            select(AudienceSavedView).where(
                or_(AudienceSavedView.user_id == user_id, AudienceSavedView.is_shared.is_(True))
            )
        ).all()
    )


def create_saved_view(db: Session, user: User, name: str, filters_json: dict | None) -> AudienceSavedView:
    view = AudienceSavedView(user_id=user.id, name=name, filters_json=filters_json)
    db.add(view)
    db.flush()
    return view
