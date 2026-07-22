"""Marketing lead context service — acquisition view, scoring, sales handoff."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.models.marketing import MarketingLeadContext, MarketingLeadHandoffStatus
from investhome_api.models.user_auth import User
from investhome_api.services.marketing.consent_eligibility_service import get_consent_status


def _get_context_or_404(db: Session, context_id: UUID) -> MarketingLeadContext:
    ctx = db.get(MarketingLeadContext, context_id)
    if ctx is None:
        raise HTTPException(status_code=404, detail="Marketing lead context not found")
    return ctx


def list_marketing_leads(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    campaign_id: UUID | None = None,
    source_id: UUID | None = None,
    handoff_status: str | None = None,
) -> tuple[list[MarketingLeadContext], int]:
    query = select(MarketingLeadContext)
    if campaign_id:
        query = query.where(MarketingLeadContext.campaign_id == campaign_id)
    if source_id:
        query = query.where(MarketingLeadContext.source_id == source_id)
    if handoff_status:
        query = query.where(MarketingLeadContext.handoff_status == MarketingLeadHandoffStatus(handoff_status))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(MarketingLeadContext.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(rows), total


def get_marketing_lead_summary(db: Session) -> dict:
    total = db.scalar(select(func.count()).select_from(MarketingLeadContext)) or 0
    ready = db.scalar(
        select(func.count()).where(MarketingLeadContext.handoff_status == MarketingLeadHandoffStatus.READY)
    ) or 0
    blocked = db.scalar(
        select(func.count()).where(MarketingLeadContext.handoff_status == MarketingLeadHandoffStatus.BLOCKED)
    ) or 0
    return {"total": total, "ready_for_handoff": ready, "blocked": blocked}


def get_marketing_lead_detail(db: Session, context_id: UUID) -> dict:
    ctx = _get_context_or_404(db, context_id)
    consent = get_consent_status(db, ctx.contact_id, ctx.company_id)
    scores = ctx.scores_json or {}
    return {
        "context": ctx,
        "consent_status": consent,
        "scores": scores if scores else None,
        "attribution": ctx.attribution_json,
        "utm": ctx.utm_data_json,
    }


def get_handoff_readiness(db: Session, context_id: UUID) -> dict:
    ctx = _get_context_or_404(db, context_id)
    blockers: list[str] = []
    if not ctx.contact_id:
        blockers.append("contact_not_identified")
    consent = get_consent_status(db, ctx.contact_id, ctx.company_id)
    email_consent = consent.get("email", "unknown")
    if email_consent == "unknown":
        blockers.append("unknown_consent")
    elif email_consent in ("denied", "blocked"):
        blockers.append("consent_blocked")
    if ctx.suppression_json and ctx.suppression_json.get("active"):
        blockers.append("suppressed")
    if ctx.lead_id:
        blockers.append("already_linked_to_sales_lead")
    ready = len(blockers) == 0
    return {
        "context_id": str(context_id),
        "ready": ready,
        "blockers": blockers,
        "consent_status": consent,
    }


def hand_marketing_lead_to_sales(db: Session, context_id: UUID, user: User) -> dict:
    """Create/link Sales lead via authorized workflow — blocks when not ready."""
    readiness = get_handoff_readiness(db, context_id)
    if not readiness["ready"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Handoff blocked", "blockers": readiness["blockers"]},
        )
    ctx = _get_context_or_404(db, context_id)

    # Check for duplicate lead by contact
    if ctx.contact_id:
        from investhome_api.models.crm_contact import CrmContact

        contact = db.get(CrmContact, ctx.contact_id)
        if contact and contact.primary_email:
            existing = db.scalar(select(Lead).where(Lead.email == contact.primary_email))
            if existing:
                ctx.lead_id = existing.id
                ctx.handoff_status = MarketingLeadHandoffStatus.HANDED_OFF
                return {
                    "context_id": str(context_id),
                    "lead_id": str(existing.id),
                    "linked_existing": True,
                }

    # Create canonical Sales lead — NOT parallel identity
    from investhome_api.models.crm_contact import CrmContact

    contact = db.get(CrmContact, ctx.contact_id) if ctx.contact_id else None
    lead = Lead(
        full_name=contact.display_name if contact else "Unknown",
        email=contact.primary_email if contact else None,
        phone=contact.primary_phone if contact else None,
        source="marketing_handoff",
        status=LeadStatus.NEW,
        assigned_manager_id=user.id,
    )
    db.add(lead)
    db.flush()
    ctx.lead_id = lead.id
    ctx.handoff_status = MarketingLeadHandoffStatus.HANDED_OFF
    ctx.marketing_status = "handed_off"
    return {
        "context_id": str(context_id),
        "lead_id": str(lead.id),
        "linked_existing": False,
    }


def update_marketing_lead_scores(db: Session, context_id: UUID, scores: dict) -> MarketingLeadContext:
    ctx = _get_context_or_404(db, context_id)
    ctx.scores_json = scores
    return ctx


def verify_marketing_lead(db: Session, context_id: UUID, status: str) -> MarketingLeadContext:
    ctx = _get_context_or_404(db, context_id)
    ctx.verification_status = status
    if status == "verified":
        readiness = get_handoff_readiness(db, context_id)
        ctx.handoff_status = (
            MarketingLeadHandoffStatus.READY if readiness["ready"] else MarketingLeadHandoffStatus.BLOCKED
        )
    return ctx


def suppress_marketing_lead(db: Session, context_id: UUID, reason: str) -> MarketingLeadContext:
    ctx = _get_context_or_404(db, context_id)
    ctx.suppression_json = {"active": True, "reason": reason, "at": datetime.now(tz=UTC).isoformat()}
    ctx.handoff_status = MarketingLeadHandoffStatus.BLOCKED
    return ctx
