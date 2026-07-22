"""Lead attribution CRUD and manual assignment — Sprint 8A3."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.lead import Lead
from investhome_api.models.marketing import MarketingCampaign, MarketingCampaignStatus
from investhome_api.models.marketing_lead_attribution import (
    MarketingAttributionSource,
    MarketingLeadAttribution,
    MarketingLeadAttributionAudit,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_performance import (
    LeadAttributionCreate,
    LeadAttributionFields,
    LeadAttributionResponse,
    LeadAttributionUpdate,
)
from investhome_api.services.marketing.lead_status_mapping import resolve_lead_attribution_status


def _validate_campaign_selectable(db: Session, campaign_id: UUID | None) -> MarketingCampaign | None:
    if campaign_id is None:
        return None
    campaign = db.get(MarketingCampaign, campaign_id)
    if campaign is None or campaign.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if campaign.status == MarketingCampaignStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Archived campaigns cannot be selected for attribution",
        )
    return campaign


def attribution_to_response(db: Session, row: MarketingLeadAttribution) -> LeadAttributionResponse:
    lead = db.get(Lead, row.lead_id)
    campaign = db.get(MarketingCampaign, row.campaign_id) if row.campaign_id else None
    source = row.attribution_source
    if hasattr(source, "value"):
        source = source.value
    return LeadAttributionResponse(
        id=row.id,
        lead_id=row.lead_id,
        campaign_id=row.campaign_id,
        company_id=row.company_id,
        attribution_source=str(source),
        utm_source=row.utm_source,
        utm_medium=row.utm_medium,
        utm_campaign=row.utm_campaign,
        utm_term=row.utm_term,
        utm_content=row.utm_content,
        first_touch_at=row.first_touch_at,
        converted_at=row.converted_at,
        attribution_reason=row.attribution_reason,
        campaign_name=campaign.name if campaign else None,
        campaign_type=campaign.campaign_type.value if campaign and campaign.campaign_type else None,
        project_id=campaign.target_project_id if campaign else None,
        lead_full_name=lead.full_name if lead else None,
        lead_status=lead.status.value if lead else None,
        attribution_status=resolve_lead_attribution_status(db, row.lead_id) if lead else None,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def get_attribution_by_lead(db: Session, lead_id: UUID) -> MarketingLeadAttribution | None:
    return db.scalars(
        select(MarketingLeadAttribution).where(MarketingLeadAttribution.lead_id == lead_id)
    ).first()


def list_attributions(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    campaign_id: UUID | None = None,
    company_id: UUID | None = None,
    lead_id: UUID | None = None,
) -> tuple[list[MarketingLeadAttribution], int]:
    query = select(MarketingLeadAttribution)
    if campaign_id:
        query = query.where(MarketingLeadAttribution.campaign_id == campaign_id)
    if company_id:
        query = query.where(MarketingLeadAttribution.company_id == company_id)
    if lead_id:
        query = query.where(MarketingLeadAttribution.lead_id == lead_id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(MarketingLeadAttribution.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(rows), total


def create_attribution(
    db: Session,
    payload: LeadAttributionCreate,
    *,
    actor: User,
) -> LeadAttributionResponse:
    lead = db.get(Lead, payload.lead_id)
    if lead is None or lead.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    existing = get_attribution_by_lead(db, payload.lead_id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lead already has primary attribution; use update instead",
        )
    _validate_campaign_selectable(db, payload.campaign_id)
    now = datetime.now(UTC)
    row = MarketingLeadAttribution(
        lead_id=payload.lead_id,
        campaign_id=payload.campaign_id,
        company_id=payload.company_id,
        attribution_source=MarketingAttributionSource(payload.attribution_source),
        utm_source=payload.utm_source,
        utm_medium=payload.utm_medium,
        utm_campaign=payload.utm_campaign,
        utm_term=payload.utm_term,
        utm_content=payload.utm_content,
        first_touch_at=payload.first_touch_at or now,
        converted_at=payload.converted_at,
        attribution_reason=payload.attribution_reason,
        created_by_user_id=actor.id,
        updated_by_user_id=actor.id,
    )
    db.add(row)
    db.flush()
    if payload.campaign_id:
        _record_audit(db, row, previous_campaign_id=None, new_campaign_id=payload.campaign_id, actor=actor, reason=payload.attribution_reason)
    return attribution_to_response(db, row)


def update_attribution(
    db: Session,
    attribution: MarketingLeadAttribution,
    payload: LeadAttributionUpdate,
    *,
    actor: User,
) -> LeadAttributionResponse:
    updates = payload.model_dump(exclude_unset=True)
    previous_campaign_id = attribution.campaign_id
    if "campaign_id" in updates:
        _validate_campaign_selectable(db, updates["campaign_id"])
    if "attribution_source" in updates and updates["attribution_source"] is not None:
        updates["attribution_source"] = MarketingAttributionSource(updates["attribution_source"])
    for field, value in updates.items():
        setattr(attribution, field, value)
    attribution.updated_by_user_id = actor.id
    db.flush()
    if "campaign_id" in updates and updates["campaign_id"] != previous_campaign_id:
        _record_audit(
            db,
            attribution,
            previous_campaign_id=previous_campaign_id,
            new_campaign_id=updates["campaign_id"],
            actor=actor,
            reason=updates.get("attribution_reason"),
        )
    return attribution_to_response(db, attribution)


def delete_attribution(
    db: Session,
    attribution: MarketingLeadAttribution,
    *,
    actor: User,
    reason: str | None = None,
) -> None:
    _record_audit(
        db,
        attribution,
        previous_campaign_id=attribution.campaign_id,
        new_campaign_id=None,
        actor=actor,
        reason=reason or "Attribution removed",
    )
    db.delete(attribution)


def upsert_lead_attribution(
    db: Session,
    lead_id: UUID,
    fields: LeadAttributionFields,
    *,
    actor: User | None = None,
    default_source: str = "crm",
) -> MarketingLeadAttribution | None:
    """Create or update attribution from lead create/edit optional fields."""
    has_data = any(
        [
            fields.campaign_id,
            fields.utm_source,
            fields.utm_medium,
            fields.utm_campaign,
            fields.utm_term,
            fields.utm_content,
        ]
    )
    if not has_data:
        return None

    existing = get_attribution_by_lead(db, lead_id)
    source = fields.attribution_source or default_source
    if fields.campaign_id:
        _validate_campaign_selectable(db, fields.campaign_id)

    if existing is None:
        row = MarketingLeadAttribution(
            lead_id=lead_id,
            campaign_id=fields.campaign_id,
            company_id=fields.company_id,
            attribution_source=MarketingAttributionSource(source),
            utm_source=fields.utm_source,
            utm_medium=fields.utm_medium,
            utm_campaign=fields.utm_campaign,
            utm_term=fields.utm_term,
            utm_content=fields.utm_content,
            first_touch_at=datetime.now(UTC),
            created_by_user_id=actor.id if actor else None,
            updated_by_user_id=actor.id if actor else None,
        )
        db.add(row)
        db.flush()
        return row

    if fields.campaign_id is not None:
        existing.campaign_id = fields.campaign_id
    if fields.company_id is not None:
        existing.company_id = fields.company_id
    if fields.attribution_source is not None:
        existing.attribution_source = MarketingAttributionSource(fields.attribution_source)
    for utm_field in ("utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"):
        value = getattr(fields, utm_field)
        if value is not None:
            setattr(existing, utm_field, value)
    if actor:
        existing.updated_by_user_id = actor.id
    db.flush()
    return existing


def resolve_campaign_by_name_or_id(db: Session, value: str) -> UUID | None:
    value = value.strip()
    if not value:
        return None
    try:
        campaign_id = UUID(value)
        campaign = _validate_campaign_selectable(db, campaign_id)
        return campaign.id if campaign else None
    except ValueError:
        pass
    campaign = db.scalars(
        select(MarketingCampaign).where(
            MarketingCampaign.name.ilike(value),
            MarketingCampaign.archived_at.is_(None),
            MarketingCampaign.status != MarketingCampaignStatus.ARCHIVED,
        )
    ).first()
    if campaign is None:
        raise ValueError(f"Campaign not found: {value}")
    return campaign.id


def _record_audit(
    db: Session,
    attribution: MarketingLeadAttribution,
    *,
    previous_campaign_id: UUID | None,
    new_campaign_id: UUID | None,
    actor: User,
    reason: str | None,
) -> None:
    audit = MarketingLeadAttributionAudit(
        attribution_id=attribution.id,
        lead_id=attribution.lead_id,
        previous_campaign_id=previous_campaign_id,
        new_campaign_id=new_campaign_id,
        changed_by_user_id=actor.id,
        change_reason=reason,
    )
    db.add(audit)
