"""Build touchpoints and journeys from existing marketing data — never invent touches."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.marketing import MarketingLeadContext, MarketingLeadHandoffStatus
from investhome_api.models.marketing_attribution import (
    AttributionHealthIssueType,
    AttributionHealthSeverity,
    JourneyStatus,
    MarketingAttributionHealth,
    MarketingAttributionJourney,
    MarketingTouchpoint,
    TouchType,
    TouchVerificationStatus,
)
from investhome_api.models.marketing_landing_conversion import (
    MarketingConversionEvent,
    MarketingFormSubmission,
    MarketingSalesHandoff,
    MarketingTrackingContext,
)


def _infer_touch_type_from_tracking(ctx: MarketingTrackingContext) -> TouchType:
    medium = (ctx.utm_medium or "").lower()
    if medium in {"cpc", "ppc", "paid", "paidsearch", "display", "retargeting"}:
        return TouchType.AD_CLICK
    if medium in {"organic", "seo"}:
        return TouchType.ORGANIC_VISIT
    if ctx.landing_url:
        return TouchType.LANDING_PAGE_VIEW
    return TouchType.OTHER


def _infer_touch_type_from_conversion(event_type: str) -> TouchType:
    normalized = event_type.lower()
    if "form" in normalized and "start" in normalized:
        return TouchType.FORM_START
    if "form" in normalized or "submit" in normalized or "lead" in normalized:
        return TouchType.FORM_SUBMIT
    if "reservation" in normalized:
        return TouchType.RESERVATION
    if "sale" in normalized:
        return TouchType.SALE
    if "meeting" in normalized:
        return TouchType.MEETING
    return TouchType.OTHER


def _verification_from_source(has_campaign: bool, has_source: bool) -> TouchVerificationStatus:
    if has_campaign and has_source:
        return TouchVerificationStatus.VERIFIED
    if has_campaign or has_source:
        return TouchVerificationStatus.PARTIAL
    return TouchVerificationStatus.UNKNOWN


def sync_touchpoint_from_tracking(
    db: Session,
    ctx: MarketingTrackingContext,
    *,
    contact_id: UUID | None = None,
    lead_context_id: UUID | None = None,
    submission_id: UUID | None = None,
) -> MarketingTouchpoint | None:
    """Create or return existing touchpoint from tracking context."""
    existing = db.scalar(
        select(MarketingTouchpoint).where(
            MarketingTouchpoint.source_entity_type == "tracking_context",
            MarketingTouchpoint.source_entity_id == ctx.id,
        )
    )
    if existing:
        return existing

    touch = MarketingTouchpoint(
        contact_id=contact_id,
        anonymous_visitor_id=ctx.session_id,
        campaign_id=ctx.campaign_id,
        source_id=ctx.source_id,
        tracking_context_id=ctx.id,
        submission_id=submission_id,
        lead_context_id=lead_context_id,
        touch_type=_infer_touch_type_from_tracking(ctx),
        touch_timestamp=ctx.created_at,
        utm_source=ctx.utm_source,
        utm_medium=ctx.utm_medium,
        utm_campaign=ctx.utm_campaign,
        utm_term=ctx.utm_term,
        utm_content=ctx.utm_content,
        verification_status=_verification_from_source(bool(ctx.campaign_id), bool(ctx.source_id)),
        source_entity_type="tracking_context",
        source_entity_id=ctx.id,
        metadata_json={"referrer": ctx.referrer, "landing_url": ctx.landing_url},
    )
    db.add(touch)
    return touch


def sync_touchpoint_from_conversion(
    db: Session,
    event: MarketingConversionEvent,
) -> MarketingTouchpoint | None:
    existing = db.scalar(
        select(MarketingTouchpoint).where(
            MarketingTouchpoint.source_entity_type == "conversion_event",
            MarketingTouchpoint.source_entity_id == event.id,
        )
    )
    if existing:
        return existing

    contact_id = None
    if event.lead_context_id:
        ctx = db.get(MarketingLeadContext, event.lead_context_id)
        if ctx:
            contact_id = ctx.contact_id

    tracking_touch = None
    if event.tracking_context_id:
        tracking = db.get(MarketingTrackingContext, event.tracking_context_id)
        if tracking:
            tracking_touch = sync_touchpoint_from_tracking(
                db,
                tracking,
                contact_id=contact_id,
                lead_context_id=event.lead_context_id,
                submission_id=event.submission_id,
            )

    touch = MarketingTouchpoint(
        contact_id=contact_id,
        campaign_id=tracking_touch.campaign_id if tracking_touch else None,
        channel_id=None,
        source_id=tracking_touch.source_id if tracking_touch else None,
        landing_page_id=event.landing_page_id,
        form_id=event.form_id,
        conversion_event_id=event.id,
        tracking_context_id=event.tracking_context_id,
        submission_id=event.submission_id,
        lead_context_id=event.lead_context_id,
        touch_type=_infer_touch_type_from_conversion(event.event_type),
        touch_timestamp=event.created_at,
        utm_source=tracking_touch.utm_source if tracking_touch else None,
        utm_medium=tracking_touch.utm_medium if tracking_touch else None,
        utm_campaign=tracking_touch.utm_campaign if tracking_touch else None,
        verification_status=TouchVerificationStatus.VERIFIED if event.submission_id else TouchVerificationStatus.PARTIAL,
        source_entity_type="conversion_event",
        source_entity_id=event.id,
    )
    db.add(touch)
    return touch


def sync_touchpoint_from_submission(
    db: Session,
    submission: MarketingFormSubmission,
) -> MarketingTouchpoint | None:
    existing = db.scalar(
        select(MarketingTouchpoint).where(
            MarketingTouchpoint.source_entity_type == "form_submission",
            MarketingTouchpoint.source_entity_id == submission.id,
        )
    )
    if existing:
        return existing

    tracking_touch = None
    if submission.tracking_context_id:
        tracking = db.get(MarketingTrackingContext, submission.tracking_context_id)
        if tracking:
            tracking_touch = sync_touchpoint_from_tracking(
                db,
                tracking,
                contact_id=submission.contact_id,
                lead_context_id=submission.lead_context_id,
                submission_id=submission.id,
            )

    touch = MarketingTouchpoint(
        contact_id=submission.contact_id,
        landing_page_id=submission.landing_page_id,
        form_id=submission.form_id,
        submission_id=submission.id,
        lead_context_id=submission.lead_context_id,
        tracking_context_id=submission.tracking_context_id,
        campaign_id=tracking_touch.campaign_id if tracking_touch else None,
        source_id=tracking_touch.source_id if tracking_touch else None,
        touch_type=TouchType.FORM_SUBMIT,
        touch_timestamp=submission.created_at,
        utm_source=tracking_touch.utm_source if tracking_touch else None,
        utm_medium=tracking_touch.utm_medium if tracking_touch else None,
        utm_campaign=tracking_touch.utm_campaign if tracking_touch else None,
        verification_status=TouchVerificationStatus.VERIFIED,
        source_entity_type="form_submission",
        source_entity_id=submission.id,
    )
    db.add(touch)
    return touch


def sync_touchpoint_from_handoff(
    db: Session,
    handoff: MarketingSalesHandoff,
) -> MarketingTouchpoint | None:
    existing = db.scalar(
        select(MarketingTouchpoint).where(
            MarketingTouchpoint.source_entity_type == "sales_handoff",
            MarketingTouchpoint.source_entity_id == handoff.id,
        )
    )
    if existing:
        return existing

    lead_ctx = db.get(MarketingLeadContext, handoff.lead_context_id)
    touch = MarketingTouchpoint(
        contact_id=lead_ctx.contact_id if lead_ctx else None,
        lead_context_id=handoff.lead_context_id,
        sales_lead_id=handoff.sales_lead_id,
        submission_id=handoff.submission_id,
        campaign_id=lead_ctx.campaign_id if lead_ctx else None,
        channel_id=lead_ctx.channel_id if lead_ctx else None,
        source_id=lead_ctx.source_id if lead_ctx else None,
        touch_type=TouchType.MANUAL_ENTRY,
        touch_timestamp=handoff.completed_at or handoff.created_at,
        verification_status=TouchVerificationStatus.VERIFIED if handoff.sales_lead_id else TouchVerificationStatus.PARTIAL,
        source_entity_type="sales_handoff",
        source_entity_id=handoff.id,
    )
    db.add(touch)
    return touch


def rebuild_all_touchpoints(db: Session) -> int:
    """Sync touchpoints from all known source entities."""
    count = 0
    for ctx in db.scalars(select(MarketingTrackingContext)).all():
        if sync_touchpoint_from_tracking(db, ctx):
            count += 1
    for sub in db.scalars(select(MarketingFormSubmission)).all():
        if sync_touchpoint_from_submission(db, sub):
            count += 1
    for event in db.scalars(select(MarketingConversionEvent)).all():
        if sync_touchpoint_from_conversion(db, event):
            count += 1
    for handoff in db.scalars(select(MarketingSalesHandoff)).all():
        if sync_touchpoint_from_handoff(db, handoff):
            count += 1
    db.flush()
    return count


def _group_key_for_touch(touch: MarketingTouchpoint) -> tuple[UUID | None, UUID | None]:
    return touch.contact_id, touch.lead_context_id


def build_journey_for_group(
    db: Session,
    *,
    contact_id: UUID | None,
    lead_context_id: UUID | None,
) -> MarketingAttributionJourney | None:
    """Build journey from real touchpoints only."""
    query = select(MarketingTouchpoint)
    if contact_id:
        query = query.where(MarketingTouchpoint.contact_id == contact_id)
    elif lead_context_id:
        query = query.where(MarketingTouchpoint.lead_context_id == lead_context_id)
    else:
        return None

    touches = list(db.scalars(query.order_by(MarketingTouchpoint.touch_timestamp.asc())).all())
    if not touches:
        return None

    touch_ids = [t.id for t in touches]
    for idx, touch in enumerate(touches):
        touch.touch_order = idx + 1

    journey_status = _determine_journey_status(touches, lead_context_id, db)
    first_at = touches[0].touch_timestamp
    last_at = touches[-1].touch_timestamp

    conversion_id = next((t.conversion_event_id for t in reversed(touches) if t.conversion_event_id), None)

    existing = None
    if lead_context_id:
        existing = db.scalar(
            select(MarketingAttributionJourney).where(
                MarketingAttributionJourney.marketing_lead_context_id == lead_context_id
            )
        )
    elif contact_id:
        existing = db.scalar(
            select(MarketingAttributionJourney).where(
                MarketingAttributionJourney.contact_id == contact_id,
                MarketingAttributionJourney.marketing_lead_context_id.is_(None),
            )
        )

    now = datetime.now(UTC)
    if existing:
        existing.touchpoint_ids_json = [str(tid) for tid in touch_ids]
        existing.journey_status = journey_status
        existing.first_touch_at = first_at
        existing.last_touch_at = last_at
        existing.touch_count = len(touches)
        existing.conversion_event_id = conversion_id
        existing.computed_at = now
        journey = existing
    else:
        journey = MarketingAttributionJourney(
            contact_id=contact_id,
            marketing_lead_context_id=lead_context_id,
            touchpoint_ids_json=[str(tid) for tid in touch_ids],
            journey_status=journey_status,
            conversion_event_id=conversion_id,
            first_touch_at=first_at,
            last_touch_at=last_at,
            touch_count=len(touches),
            computed_at=now,
        )
        db.add(journey)

    db.flush()
    return journey


def _determine_journey_status(
    touches: list[MarketingTouchpoint],
    lead_context_id: UUID | None,
    db: Session,
) -> JourneyStatus:
    if not touches:
        return JourneyStatus.UNKNOWN

    has_unknown_source = any(
        t.verification_status in {TouchVerificationStatus.UNKNOWN, TouchVerificationStatus.UNVERIFIED}
        for t in touches
    )
    has_conversion = any(t.conversion_event_id or t.touch_type == TouchType.FORM_SUBMIT for t in touches)

    if lead_context_id:
        ctx = db.get(MarketingLeadContext, lead_context_id)
        if ctx and ctx.handoff_status == MarketingLeadHandoffStatus.HANDED_OFF and has_conversion:
            if has_unknown_source:
                return JourneyStatus.INCOMPLETE
            return JourneyStatus.COMPLETE
        if has_conversion:
            return JourneyStatus.INCOMPLETE if has_unknown_source else JourneyStatus.COMPLETE

    if has_unknown_source and len(touches) == 1:
        return JourneyStatus.UNKNOWN

    if has_unknown_source:
        return JourneyStatus.INCOMPLETE

    if len(touches) >= 1 and has_conversion:
        return JourneyStatus.COMPLETE

    return JourneyStatus.INCOMPLETE


def rebuild_all_journeys(db: Session) -> int:
    """Build journeys grouped by lead context or contact."""
    groups: set[tuple[UUID | None, UUID | None]] = set()
    for touch in db.scalars(select(MarketingTouchpoint)).all():
        if touch.lead_context_id:
            groups.add((touch.contact_id, touch.lead_context_id))
        elif touch.contact_id:
            groups.add((touch.contact_id, None))

    count = 0
    for contact_id, lead_context_id in groups:
        if build_journey_for_group(db, contact_id=contact_id, lead_context_id=lead_context_id):
            count += 1
    db.flush()
    return count


def detect_health_issues(db: Session, *, journey_id: UUID | None = None) -> list[MarketingAttributionHealth]:
    """Detect attribution health issues from real data."""
    db.query(MarketingAttributionHealth).filter(
        MarketingAttributionHealth.is_resolved.is_(False),
        MarketingAttributionHealth.journey_id == journey_id if journey_id else True,
    ).update({"is_resolved": True, "resolved_at": datetime.now(UTC)})

    issues: list[MarketingAttributionHealth] = []
    journey_query = select(MarketingAttributionJourney)
    if journey_id:
        journey_query = journey_query.where(MarketingAttributionJourney.id == journey_id)

    for journey in db.scalars(journey_query).all():
        if journey.journey_status == JourneyStatus.BROKEN:
            issues.append(
                MarketingAttributionHealth(
                    issue_type=AttributionHealthIssueType.BROKEN_JOURNEY,
                    severity=AttributionHealthSeverity.CRITICAL,
                    journey_id=journey.id,
                    message="Journey marked as broken",
                )
            )
        elif journey.journey_status == JourneyStatus.INCOMPLETE:
            issues.append(
                MarketingAttributionHealth(
                    issue_type=AttributionHealthIssueType.INCOMPLETE_JOURNEY,
                    severity=AttributionHealthSeverity.WARNING,
                    journey_id=journey.id,
                    message="Journey is incomplete — missing attribution data",
                )
            )
        elif journey.journey_status == JourneyStatus.UNKNOWN:
            issues.append(
                MarketingAttributionHealth(
                    issue_type=AttributionHealthIssueType.UNKNOWN_SOURCE,
                    severity=AttributionHealthSeverity.WARNING,
                    journey_id=journey.id,
                    message="Attribution unknown — insufficient touchpoint data",
                )
            )

        touch_ids = [UUID(tid) for tid in (journey.touchpoint_ids_json or [])]
        if touch_ids:
            touches = list(
                db.scalars(select(MarketingTouchpoint).where(MarketingTouchpoint.id.in_(touch_ids))).all()
            )
            seen_sources: dict[tuple[str, UUID], UUID] = {}
            for touch in touches:
                if not touch.source_id and not touch.campaign_id:
                    issues.append(
                        MarketingAttributionHealth(
                            issue_type=AttributionHealthIssueType.UNKNOWN_SOURCE,
                            severity=AttributionHealthSeverity.WARNING,
                            journey_id=journey.id,
                            touchpoint_id=touch.id,
                            message="Touchpoint has unknown source",
                        )
                    )
                key = (touch.source_entity_type or "", touch.source_entity_id or touch.id)
                if key in seen_sources:
                    issues.append(
                        MarketingAttributionHealth(
                            issue_type=AttributionHealthIssueType.DUPLICATE_TOUCH,
                            severity=AttributionHealthSeverity.WARNING,
                            journey_id=journey.id,
                            touchpoint_id=touch.id,
                            message="Duplicate touch detected",
                            details_json={"duplicate_of": str(seen_sources[key])},
                        )
                    )
                else:
                    seen_sources[key] = touch.id

    for issue in issues:
        db.add(issue)
    db.flush()
    return issues


def compute_allocation_weights(model_type: str, touch_count: int, *, config: dict | None = None) -> list[float]:
    """Return contribution percentages (sum=100) for touch positions."""
    if touch_count <= 0:
        return []
    if touch_count == 1:
        return [100.0]

    model = model_type.lower()
    if model == "first_touch":
        return [100.0] + [0.0] * (touch_count - 1)
    if model == "last_touch":
        return [0.0] * (touch_count - 1) + [100.0]
    if model == "linear":
        share = 100.0 / touch_count
        return [share] * touch_count
    if model == "position_based":
        cfg = config or {}
        first_pct = float(cfg.get("first_pct", 40))
        last_pct = float(cfg.get("last_pct", 40))
        middle_pct = 100.0 - first_pct - last_pct
        if touch_count == 2:
            return [first_pct, last_pct]
        middle_share = middle_pct / (touch_count - 2)
        return [first_pct] + [middle_share] * (touch_count - 2) + [last_pct]
    if model == "time_decay":
        cfg = config or {}
        half_life = float(cfg.get("half_life_days", 7))
        weights = [math.pow(0.5, (touch_count - 1 - i) / half_life) for i in range(touch_count)]
        total = sum(weights) or 1.0
        return [(w / total) * 100.0 for w in weights]
    if model in {"data_driven", "unknown"}:
        return []
    if model == "partial":
        share = 100.0 / touch_count
        return [share * 0.5] * touch_count
    return []
