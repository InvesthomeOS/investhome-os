"""Lead capture — routing rules, handoff SLAs, sales handoff visibility."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.marketing import MarketingLeadContext, MarketingLeadHandoffStatus
from investhome_api.models.marketing_landing_conversion import (
    HandoffSLA,
    MarketingConversionEvent,
    MarketingFormSubmission,
    MarketingLeadRoutingRule,
    MarketingSalesHandoff,
    SubmissionReviewItem,
    SubmissionStatus,
    ReviewItemStatus,
)
from investhome_api.services.marketing.consent_eligibility_service import get_consent_status
from investhome_api.services.marketing.marketing_lead_service import get_handoff_readiness


def record_conversion_event(
    db: Session,
    event_type: str,
    *,
    submission_id: UUID | None = None,
    lead_context_id: UUID | None = None,
    landing_page_id: UUID | None = None,
    form_id: UUID | None = None,
    tracking_context_id: UUID | None = None,
    value_json: dict | None = None,
) -> MarketingConversionEvent:
    event = MarketingConversionEvent(
        event_type=event_type,
        submission_id=submission_id,
        lead_context_id=lead_context_id,
        landing_page_id=landing_page_id,
        form_id=form_id,
        tracking_context_id=tracking_context_id,
        value_json=value_json,
    )
    db.add(event)
    db.flush()
    return event


def ensure_default_sla(db: Session) -> HandoffSLA:
    sla = db.scalar(select(HandoffSLA).where(HandoffSLA.is_default.is_(True)))
    if not sla:
        sla = HandoffSLA(name="Default", target_minutes=60, is_default=True)
        db.add(sla)
        db.flush()
    return sla


def apply_routing_rules(db: Session, ctx: MarketingLeadContext, submission: MarketingFormSubmission) -> MarketingLeadRoutingRule | None:
    """Apply routing rules with fallback."""
    rules = db.scalars(
        select(MarketingLeadRoutingRule)
        .where(MarketingLeadRoutingRule.is_active.is_(True))
        .order_by(MarketingLeadRoutingRule.priority.desc())
    ).all()

    matched: MarketingLeadRoutingRule | None = None
    for rule in rules:
        if rule.is_fallback:
            continue
        conditions = rule.conditions_json or {}
        if rule.form_id and rule.form_id != submission.form_id:
            continue
        if rule.source_id and rule.source_id != ctx.source_id:
            continue
        if conditions.get("utm_source") and submission.tracking_context_id:
            from investhome_api.models.marketing_landing_conversion import MarketingTrackingContext

            tracking = db.get(MarketingTrackingContext, submission.tracking_context_id)
            if tracking and tracking.utm_source != conditions.get("utm_source"):
                continue
        matched = rule
        break

    if not matched:
        matched = db.scalar(select(MarketingLeadRoutingRule).where(MarketingLeadRoutingRule.is_fallback.is_(True)))

    if matched and matched.action_json:
        ctx.attribution_json = ctx.attribution_json or {}
        ctx.attribution_json["routing_rule_id"] = str(matched.id)
        ctx.attribution_json["routing_action"] = matched.action_json

    return matched


def list_routing_rules(db: Session) -> list[MarketingLeadRoutingRule]:
    return list(
        db.scalars(
            select(MarketingLeadRoutingRule).order_by(MarketingLeadRoutingRule.priority.desc())
        ).all()
    )


def create_routing_rule(db: Session, payload: dict) -> MarketingLeadRoutingRule:
    if payload.get("is_fallback"):
        existing = db.scalar(select(MarketingLeadRoutingRule).where(MarketingLeadRoutingRule.is_fallback.is_(True)))
        if existing:
            raise HTTPException(status_code=409, detail="Fallback rule already exists")
    rule = MarketingLeadRoutingRule(**payload)
    db.add(rule)
    db.flush()
    return rule


def get_lead_capture_dashboard(db: Session) -> dict:
    pending_review = db.scalar(
        select(func.count()).where(SubmissionReviewItem.status == ReviewItemStatus.PENDING)
    ) or 0
    pending_verification = db.scalar(
        select(func.count()).where(MarketingLeadContext.verification_status == "pending")
    ) or 0
    duplicates = db.scalar(
        select(func.count()).where(MarketingFormSubmission.status == SubmissionStatus.DUPLICATE_DETECTED)
    ) or 0
    ready = db.scalar(
        select(func.count()).where(MarketingLeadContext.handoff_status == MarketingLeadHandoffStatus.READY)
    ) or 0
    return {
        "pending_review": pending_review,
        "pending_verification": pending_verification,
        "duplicates_detected": duplicates,
        "ready_for_handoff": ready,
        "provider_status": "not_connected",
    }


def list_handoffs(db: Session, page: int = 1, page_size: int = 25) -> tuple[list[MarketingSalesHandoff], int]:
    query = select(MarketingSalesHandoff)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(MarketingSalesHandoff.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(rows), total


def create_handoff_record(db: Session, context_id: UUID, submission_id: UUID | None = None) -> MarketingSalesHandoff:
    ctx = db.get(MarketingLeadContext, context_id)
    if ctx is None:
        raise HTTPException(status_code=404, detail="Lead context not found")
    readiness = get_handoff_readiness(db, context_id)
    sla = ensure_default_sla(db)
    handoff = MarketingSalesHandoff(
        lead_context_id=context_id,
        submission_id=submission_id,
        status="ready" if readiness["ready"] else "blocked",
        sla_id=sla.id,
        due_at=datetime.now(tz=UTC) + timedelta(minutes=sla.target_minutes),
        blockers_json=readiness["blockers"] if not readiness["ready"] else None,
    )
    db.add(handoff)
    db.flush()
    return handoff


def list_slas(db: Session) -> list[HandoffSLA]:
    ensure_default_sla(db)
    return list(db.scalars(select(HandoffSLA).where(HandoffSLA.is_active.is_(True))).all())


def list_duplicates(db: Session, page: int = 1, page_size: int = 25) -> tuple[list[MarketingFormSubmission], int]:
    query = select(MarketingFormSubmission).where(
        MarketingFormSubmission.status == SubmissionStatus.DUPLICATE_DETECTED
    )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(MarketingFormSubmission.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(rows), total


def list_verification_queue(db: Session, page: int = 1, page_size: int = 25) -> tuple[list[MarketingLeadContext], int]:
    query = select(MarketingLeadContext).where(MarketingLeadContext.verification_status == "pending")
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(MarketingLeadContext.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(rows), total
