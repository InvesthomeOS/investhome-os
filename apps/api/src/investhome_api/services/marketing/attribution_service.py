"""Attribution service — dashboard, CRUD, compute orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.marketing import MarketingCampaign, MarketingChannel, MarketingLeadContext, MarketingLeadSource
from investhome_api.models.marketing_attribution import (
    AttributionHealthSeverity,
    AttributionModelType,
    JourneyStatus,
    MarketingAttributionAllocation,
    MarketingAttributionHealth,
    MarketingAttributionJourney,
    MarketingAttributionModel,
    MarketingAttributionRule,
    MarketingTouchpoint,
)
from investhome_api.models.marketing_landing_conversion import MarketingConversionEvent
from investhome_api.services.marketing.attribution_engine import (
    build_journey_for_group,
    compute_allocation_weights,
    detect_health_issues,
    rebuild_all_journeys,
    rebuild_all_touchpoints,
)
from investhome_api.services.marketing.submission_service import compute_pages


def list_touchpoints(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    contact_id: UUID | None = None,
    lead_context_id: UUID | None = None,
    campaign_id: UUID | None = None,
    channel_id: UUID | None = None,
    source_id: UUID | None = None,
    touch_type: str | None = None,
) -> tuple[list[MarketingTouchpoint], int]:
    query = select(MarketingTouchpoint)
    if contact_id:
        query = query.where(MarketingTouchpoint.contact_id == contact_id)
    if lead_context_id:
        query = query.where(MarketingTouchpoint.lead_context_id == lead_context_id)
    if campaign_id:
        query = query.where(MarketingTouchpoint.campaign_id == campaign_id)
    if channel_id:
        query = query.where(MarketingTouchpoint.channel_id == channel_id)
    if source_id:
        query = query.where(MarketingTouchpoint.source_id == source_id)
    if touch_type:
        query = query.where(MarketingTouchpoint.touch_type == touch_type)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = list(
        db.scalars(
            query.order_by(MarketingTouchpoint.touch_timestamp.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return items, total


def list_journeys(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    contact_id: UUID | None = None,
    lead_context_id: UUID | None = None,
    journey_status: str | None = None,
) -> tuple[list[MarketingAttributionJourney], int]:
    query = select(MarketingAttributionJourney)
    if contact_id:
        query = query.where(MarketingAttributionJourney.contact_id == contact_id)
    if lead_context_id:
        query = query.where(MarketingAttributionJourney.marketing_lead_context_id == lead_context_id)
    if journey_status:
        query = query.where(MarketingAttributionJourney.journey_status == journey_status)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = list(
        db.scalars(
            query.order_by(MarketingAttributionJourney.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return items, total


def get_journey(db: Session, journey_id: UUID) -> MarketingAttributionJourney | None:
    return db.get(MarketingAttributionJourney, journey_id)


def get_customer_journey(
    db: Session,
    *,
    contact_id: UUID | None = None,
    lead_context_id: UUID | None = None,
    model_id: UUID | None = None,
) -> MarketingAttributionJourney | None:
    query = select(MarketingAttributionJourney)
    if lead_context_id:
        query = query.where(MarketingAttributionJourney.marketing_lead_context_id == lead_context_id)
    elif contact_id:
        query = query.where(MarketingAttributionJourney.contact_id == contact_id)
    else:
        return None
    return db.scalar(query.order_by(MarketingAttributionJourney.updated_at.desc()).limit(1))


def get_journey_touchpoints(db: Session, journey: MarketingAttributionJourney) -> list[MarketingTouchpoint]:
    touch_ids = [UUID(tid) for tid in (journey.touchpoint_ids_json or [])]
    if not touch_ids:
        return []
    touches = list(db.scalars(select(MarketingTouchpoint).where(MarketingTouchpoint.id.in_(touch_ids))).all())
    order_map = {tid: idx for idx, tid in enumerate(touch_ids)}
    return sorted(touches, key=lambda t: order_map.get(t.id, 999))


def get_journey_allocations(
    db: Session,
    journey_id: UUID,
    model_id: UUID | None = None,
) -> list[MarketingAttributionAllocation]:
    query = select(MarketingAttributionAllocation).where(MarketingAttributionAllocation.journey_id == journey_id)
    if model_id:
        query = query.where(MarketingAttributionAllocation.model_id == model_id)
    return list(db.scalars(query.order_by(MarketingAttributionAllocation.contribution_pct.desc())).all())


def list_models(db: Session, *, active_only: bool = True) -> list[MarketingAttributionModel]:
    query = select(MarketingAttributionModel)
    if active_only:
        query = query.where(MarketingAttributionModel.is_active.is_(True))
    return list(db.scalars(query.order_by(MarketingAttributionModel.is_default.desc(), MarketingAttributionModel.name)).all())


def get_default_model(db: Session) -> MarketingAttributionModel | None:
    return db.scalar(
        select(MarketingAttributionModel).where(
            MarketingAttributionModel.is_default.is_(True),
            MarketingAttributionModel.is_active.is_(True),
        )
    )


def create_model(db: Session, *, payload: dict, user_id: UUID | None) -> MarketingAttributionModel:
    if payload.get("is_default"):
        for m in db.scalars(select(MarketingAttributionModel).where(MarketingAttributionModel.is_default.is_(True))).all():
            m.is_default = False
    model = MarketingAttributionModel(
        name=payload["name"],
        model_type=AttributionModelType(payload["model_type"]),
        config_json=payload.get("config_json"),
        is_default=payload.get("is_default", False),
        description=payload.get("description"),
        created_by_user_id=user_id,
        updated_by_user_id=user_id,
    )
    db.add(model)
    db.flush()
    return model


def update_model(db: Session, model_id: UUID, *, payload: dict, user_id: UUID | None) -> MarketingAttributionModel | None:
    model = db.get(MarketingAttributionModel, model_id)
    if not model:
        return None
    if payload.get("is_default"):
        for m in db.scalars(select(MarketingAttributionModel).where(MarketingAttributionModel.is_default.is_(True))).all():
            m.is_default = False
    for field in ("name", "config_json", "is_default", "is_active", "description"):
        if field in payload and payload[field] is not None:
            setattr(model, field, payload[field])
    model.updated_by_user_id = user_id
    db.flush()
    return model


def list_rules(db: Session) -> list[MarketingAttributionRule]:
    return list(
        db.scalars(
            select(MarketingAttributionRule)
            .order_by(MarketingAttributionRule.priority.desc(), MarketingAttributionRule.name)
        ).all()
    )


def create_rule(db: Session, *, payload: dict, user_id: UUID | None) -> MarketingAttributionRule:
    rule = MarketingAttributionRule(
        name=payload["name"],
        priority=payload.get("priority", 0),
        is_active=payload.get("is_active", True),
        conditions_json=payload.get("conditions_json"),
        allocation_json=payload.get("allocation_json"),
        model_id=payload.get("model_id"),
        created_by_user_id=user_id,
        updated_by_user_id=user_id,
    )
    db.add(rule)
    db.flush()
    return rule


def update_rule(db: Session, rule_id: UUID, *, payload: dict, user_id: UUID | None) -> MarketingAttributionRule | None:
    rule = db.get(MarketingAttributionRule, rule_id)
    if not rule:
        return None
    for field in ("name", "priority", "is_active", "conditions_json", "allocation_json", "model_id"):
        if field in payload and payload[field] is not None:
            setattr(rule, field, payload[field])
    rule.updated_by_user_id = user_id
    db.flush()
    return rule


def _model_availability(model: MarketingAttributionModel) -> tuple[bool, str | None]:
    if model.model_type == AttributionModelType.DATA_DRIVEN:
        return False, "Data-driven attribution requires ML pipeline — framework only"
    return True, None


def _kpi_state(value: int | None) -> str:
    if value is None:
        return "unknown"
    return "ready" if value > 0 else "no_data"


def build_attribution_dashboard(db: Session) -> dict:
    journey_counts = dict(
        db.execute(
            select(MarketingAttributionJourney.journey_status, func.count())
            .group_by(MarketingAttributionJourney.journey_status)
        ).all()
    )

    attributed_leads = db.scalar(
        select(func.count())
        .select_from(MarketingAttributionJourney)
        .where(MarketingAttributionJourney.journey_status == JourneyStatus.COMPLETE)
    ) or 0

    unknown_count = journey_counts.get(JourneyStatus.UNKNOWN, 0) + journey_counts.get(JourneyStatus.INCOMPLETE, 0)
    broken_count = journey_counts.get(JourneyStatus.BROKEN, 0)
    incomplete_count = journey_counts.get(JourneyStatus.INCOMPLETE, 0)

    handoff_journeys = db.scalar(
        select(func.count())
        .select_from(MarketingLeadContext)
        .where(MarketingLeadContext.handoff_status == "handed_off")
    ) or 0

    touch_count = db.scalar(select(func.count()).select_from(MarketingTouchpoint)) or 0
    has_data = touch_count > 0 or attributed_leads > 0

    default_model = get_default_model(db)

    top_campaigns = _top_entities(db, "campaign_id", MarketingCampaign, MarketingTouchpoint.campaign_id)
    top_channels = _top_entities(db, "channel_id", MarketingChannel, MarketingTouchpoint.channel_id)
    top_sources = _top_entities(db, "source_id", MarketingLeadSource, MarketingTouchpoint.source_id)

    return {
        "kpis": [
            {"key": "attributed_leads", "label": "Attributed Leads", "value": attributed_leads, "state": _kpi_state(attributed_leads)},
            {"key": "attributed_opportunities", "label": "Attributed Opportunities", "value": None, "state": "not_connected", "message": "Requires sales opportunity linkage"},
            {"key": "attributed_reservations", "label": "Attributed Reservations", "value": None, "state": "not_connected", "message": "Requires reservation linkage"},
            {"key": "attributed_sales", "label": "Attributed Sales", "value": None, "state": "not_connected", "message": "Requires sale linkage"},
            {"key": "unknown_attribution", "label": "Unknown Attribution", "value": unknown_count, "state": _kpi_state(unknown_count)},
            {"key": "broken_journeys", "label": "Broken Journeys", "value": broken_count, "state": _kpi_state(broken_count)},
            {"key": "incomplete_journeys", "label": "Incomplete Journeys", "value": incomplete_count, "state": _kpi_state(incomplete_count)},
            {"key": "sales_handoffs", "label": "Sales Handoffs", "value": handoff_journeys, "state": _kpi_state(handoff_journeys)},
        ],
        "top_campaigns": top_campaigns,
        "top_channels": top_channels,
        "top_sources": top_sources,
        "default_model_id": default_model.id if default_model else None,
        "journey_summary": {k.value if hasattr(k, "value") else str(k): v for k, v in journey_counts.items()},
        "has_data": has_data,
        "message": None if has_data else "No touchpoint data — run compute attribution after capturing conversions",
    }


def _top_entities(db: Session, field: str, name_model: type, column) -> list[dict]:
    rows = db.execute(
        select(column, func.count())
        .where(column.isnot(None))
        .group_by(column)
        .order_by(func.count().desc())
        .limit(5)
    ).all()
    if not rows:
        return []
    result = []
    for entity_id, count in rows:
        entity = db.get(name_model, entity_id)
        result.append({"id": entity_id, "name": getattr(entity, "name", None) if entity else None, "count": count})
    return result


def build_health_summary(db: Session) -> dict:
    issues = list(
        db.scalars(
            select(MarketingAttributionHealth)
            .where(MarketingAttributionHealth.is_resolved.is_(False))
            .order_by(MarketingAttributionHealth.detected_at.desc())
        ).all()
    )
    healthy = 0
    warning = sum(1 for i in issues if i.severity == AttributionHealthSeverity.WARNING)
    critical = sum(1 for i in issues if i.severity == AttributionHealthSeverity.CRITICAL)

    journey_total = db.scalar(select(func.count()).select_from(MarketingAttributionJourney)) or 0
    if journey_total > 0 and not issues:
        healthy = journey_total

    if critical > 0:
        overall = "critical"
    elif warning > 0:
        overall = "warning"
    elif healthy > 0 or journey_total > 0:
        overall = "healthy"
    else:
        overall = "unknown"

    summary: dict[str, int] = {}
    for issue in issues:
        key = issue.issue_type.value if hasattr(issue.issue_type, "value") else str(issue.issue_type)
        summary[key] = summary.get(key, 0) + 1

    return {
        "overall_status": overall,
        "healthy_count": healthy,
        "warning_count": warning,
        "critical_count": critical,
        "issues": issues,
        "summary": summary,
    }


def list_attribution_conversions(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[dict], int]:
    query = select(MarketingConversionEvent)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    events = list(
        db.scalars(
            query.order_by(MarketingConversionEvent.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )

    items = []
    for event in events:
        journey = None
        if event.lead_context_id:
            journey = db.scalar(
                select(MarketingAttributionJourney).where(
                    MarketingAttributionJourney.marketing_lead_context_id == event.lead_context_id
                )
            )
        attributed = journey is not None and journey.journey_status == JourneyStatus.COMPLETE
        if journey and journey.journey_status == JourneyStatus.UNKNOWN:
            state = "unknown"
        elif journey and journey.journey_status == JourneyStatus.INCOMPLETE:
            state = "partial"
        elif attributed:
            state = "attributed"
        else:
            state = "unknown"

        items.append(
            {
                "conversion_event_id": event.id,
                "event_type": event.event_type,
                "lead_context_id": event.lead_context_id,
                "journey_id": journey.id if journey else None,
                "journey_status": journey.journey_status.value if journey else None,
                "attributed": attributed,
                "attribution_state": state,
                "created_at": event.created_at,
            }
        )
    return items, total


def _rule_matches(touch: MarketingTouchpoint, conditions: dict | None) -> bool:
    if not conditions:
        return False
    for key, value in conditions.items():
        touch_val = getattr(touch, key, None)
        if touch_val is None and key in touch.__dict__:
            touch_val = touch.__dict__.get(key)
        if str(touch_val) != str(value):
            return False
    return True


def compute_attribution(
    db: Session,
    *,
    model_id: UUID | None = None,
    journey_ids: list[UUID] | None = None,
    rebuild_journeys: bool = False,
    rebuild_touchpoints: bool = False,
) -> dict:
    if rebuild_touchpoints:
        rebuild_all_touchpoints(db)
    if rebuild_journeys or rebuild_touchpoints:
        rebuild_all_journeys(db)

    model = db.get(MarketingAttributionModel, model_id) if model_id else get_default_model(db)
    if not model:
        return {
            "journeys_processed": 0,
            "allocations_created": 0,
            "health_issues_detected": 0,
            "model_id": None,
            "model_type": None,
            "unavailable": True,
            "message": "No attribution model configured",
        }

    available, reason = _model_availability(model)
    if not available:
        return {
            "journeys_processed": 0,
            "allocations_created": 0,
            "health_issues_detected": 0,
            "model_id": model.id,
            "model_type": model.model_type.value,
            "unavailable": True,
            "message": reason,
        }

    journey_query = select(MarketingAttributionJourney)
    if journey_ids:
        journey_query = journey_query.where(MarketingAttributionJourney.id.in_(journey_ids))
    journeys = list(db.scalars(journey_query).all())

    rules = [r for r in list_rules(db) if r.is_active]
    allocations_created = 0
    now = datetime.now(UTC)

    for journey in journeys:
        db.query(MarketingAttributionAllocation).filter(
            MarketingAttributionAllocation.journey_id == journey.id,
            MarketingAttributionAllocation.model_id == model.id,
        ).delete()

        touches = get_journey_touchpoints(db, journey)
        if not touches:
            continue

        weights: list[float] = []
        if model.model_type == AttributionModelType.CUSTOM:
            for rule in sorted(rules, key=lambda r: r.priority, reverse=True):
                if any(_rule_matches(t, rule.conditions_json) for t in touches):
                    custom_weights = (rule.allocation_json or {}).get("weights")
                    if custom_weights and len(custom_weights) == len(touches):
                        weights = [float(w) for w in custom_weights]
                        break
            if not weights:
                weights = compute_allocation_weights("linear", len(touches))
        else:
            weights = compute_allocation_weights(
                model.model_type.value,
                len(touches),
                config=model.config_json,
            )

        if not weights:
            continue

        confidence = 1.0 if journey.journey_status == JourneyStatus.COMPLETE else 0.5
        for touch, weight in zip(touches, weights, strict=False):
            if weight <= 0:
                continue
            db.add(
                MarketingAttributionAllocation(
                    journey_id=journey.id,
                    model_id=model.id,
                    touchpoint_id=touch.id,
                    contribution_pct=round(weight, 4),
                    confidence=confidence,
                    computed_at=now,
                )
            )
            allocations_created += 1

        journey.computed_at = now

    health_issues = detect_health_issues(db)
    db.commit()

    return {
        "journeys_processed": len(journeys),
        "allocations_created": allocations_created,
        "health_issues_detected": len(health_issues),
        "model_id": model.id,
        "model_type": model.model_type.value,
        "unavailable": False,
        "message": None,
    }


def paginate(items: list, page: int, page_size: int, total: int) -> dict:
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": compute_pages(total, page_size),
    }
