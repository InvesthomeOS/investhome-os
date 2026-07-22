"""Multi-touch attribution API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.activity import ActivityAction, ActivityEntityType, ActivitySource
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_attribution import (
    AllocationResponse,
    AttributionConversionListResponse,
    AttributionConversionResponse,
    AttributionDashboardResponse,
    AttributionHealthIssueResponse,
    AttributionHealthResponse,
    AttributionModelCreate,
    AttributionModelResponse,
    AttributionModelUpdate,
    AttributionRuleCreate,
    AttributionRuleResponse,
    AttributionRuleUpdate,
    ComputeAttributionRequest,
    ComputeAttributionResponse,
    JourneyListResponse,
    JourneyResponse,
    JourneyTimelineStep,
    TouchpointListResponse,
    TouchpointResponse,
)
from investhome_api.services.activity_service import ActivityRequestContext, log_activity
from investhome_api.services.marketing.attribution_service import (
    build_attribution_dashboard,
    build_health_summary,
    compute_attribution,
    create_model,
    create_rule,
    get_customer_journey,
    get_default_model,
    get_journey,
    get_journey_allocations,
    get_journey_touchpoints,
    list_attribution_conversions,
    list_journeys,
    list_models,
    list_rules,
    list_touchpoints,
    paginate,
    update_model,
    update_rule,
)
from investhome_api.services.marketing.attribution_service import _model_availability

router = APIRouter(prefix="/marketing/attribution", tags=["marketing-attribution"])


def _serialize_touchpoint(t) -> TouchpointResponse:
    return TouchpointResponse(
        id=t.id,
        contact_id=t.contact_id,
        anonymous_visitor_id=t.anonymous_visitor_id,
        campaign_id=t.campaign_id,
        channel_id=t.channel_id,
        source_id=t.source_id,
        landing_page_id=t.landing_page_id,
        form_id=t.form_id,
        conversion_event_id=t.conversion_event_id,
        crm_timeline_event_id=t.crm_timeline_event_id,
        sales_lead_id=t.sales_lead_id,
        opportunity_id=t.opportunity_id,
        reservation_id=t.reservation_id,
        sale_id=t.sale_id,
        tracking_context_id=t.tracking_context_id,
        submission_id=t.submission_id,
        lead_context_id=t.lead_context_id,
        touch_type=t.touch_type.value if hasattr(t.touch_type, "value") else str(t.touch_type),
        touch_order=t.touch_order,
        touch_timestamp=t.touch_timestamp,
        utm_source=t.utm_source,
        utm_medium=t.utm_medium,
        utm_campaign=t.utm_campaign,
        utm_term=t.utm_term,
        utm_content=t.utm_content,
        click_ids_json=t.click_ids_json,
        device_json=t.device_json,
        country=t.country,
        verification_status=t.verification_status.value if hasattr(t.verification_status, "value") else str(t.verification_status),
        source_entity_type=t.source_entity_type,
        source_entity_id=t.source_entity_id,
        created_at=t.created_at,
    )


def _serialize_journey(db: Session, journey, *, model_id: UUID | None = None) -> JourneyResponse:
    touches = get_journey_touchpoints(db, journey)
    allocations = get_journey_allocations(db, journey.id, model_id=model_id)
    alloc_map = {a.touchpoint_id: a.contribution_pct for a in allocations}
    timeline = [
        JourneyTimelineStep(
            touchpoint_id=t.id,
            touch_type=t.touch_type.value if hasattr(t.touch_type, "value") else str(t.touch_type),
            touch_order=t.touch_order or idx + 1,
            touch_timestamp=t.touch_timestamp,
            campaign_id=t.campaign_id,
            channel_id=t.channel_id,
            source_id=t.source_id,
            verification_status=t.verification_status.value if hasattr(t.verification_status, "value") else str(t.verification_status),
            contribution_pct=alloc_map.get(t.id),
        )
        for idx, t in enumerate(touches)
    ]
    return JourneyResponse(
        id=journey.id,
        contact_id=journey.contact_id,
        marketing_lead_context_id=journey.marketing_lead_context_id,
        touchpoint_ids=[UUID(tid) for tid in (journey.touchpoint_ids_json or [])],
        journey_status=journey.journey_status.value if hasattr(journey.journey_status, "value") else str(journey.journey_status),
        conversion_event_id=journey.conversion_event_id,
        first_touch_at=journey.first_touch_at,
        last_touch_at=journey.last_touch_at,
        touch_count=journey.touch_count,
        computed_at=journey.computed_at,
        timeline=timeline,
        allocations=[AllocationResponse.model_validate(a) for a in allocations],
    )


def _audit(db: Session, user: User, event_suffix: str, entity_id: UUID) -> None:
    log_activity(
        db,
        event_type=f"marketing.attribution.{event_suffix}",
        action=ActivityAction.CREATED if "created" in event_suffix else ActivityAction.UPDATED,
        entity_type=ActivityEntityType.MARKETING_ATTRIBUTION,
        entity_id=entity_id,
        actor_user_id=user.id,
        context=ActivityRequestContext(source=ActivitySource.WEB),
    )


@router.get("/dashboard", response_model=AttributionDashboardResponse)
def get_attribution_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_attribution")),
):
    return build_attribution_dashboard(db)


@router.get("/touchpoints", response_model=TouchpointListResponse)
def get_touchpoints(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_attribution")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    contact_id: UUID | None = None,
    lead_context_id: UUID | None = None,
    campaign_id: UUID | None = None,
    channel_id: UUID | None = None,
    source_id: UUID | None = None,
    touch_type: str | None = None,
):
    items, total = list_touchpoints(
        db,
        page=page,
        page_size=page_size,
        contact_id=contact_id,
        lead_context_id=lead_context_id,
        campaign_id=campaign_id,
        channel_id=channel_id,
        source_id=source_id,
        touch_type=touch_type,
    )
    return TouchpointListResponse(
        items=[_serialize_touchpoint(t) for t in items],
        **{k: v for k, v in paginate([], page, page_size, total).items() if k != "items"},
    )


@router.get("/journeys", response_model=JourneyListResponse)
def list_journeys_route(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_attribution")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    contact_id: UUID | None = None,
    lead_context_id: UUID | None = None,
    journey_status: str | None = None,
    model_id: UUID | None = None,
):
    items, total = list_journeys(
        db,
        page=page,
        page_size=page_size,
        contact_id=contact_id,
        lead_context_id=lead_context_id,
        journey_status=journey_status,
    )
    return JourneyListResponse(
        items=[_serialize_journey(db, j, model_id=model_id) for j in items],
        **{k: v for k, v in paginate([], page, page_size, total).items() if k != "items"},
    )


@router.get("/journeys/{journey_id}", response_model=JourneyResponse)
def get_journey_route(
    journey_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_attribution")),
    model_id: UUID | None = None,
):
    journey = get_journey(db, journey_id)
    if not journey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journey not found")
    return _serialize_journey(db, journey, model_id=model_id)


@router.get("/customer-journey", response_model=JourneyResponse | None)
def get_customer_journey_route(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_attribution")),
    contact_id: UUID | None = None,
    lead_context_id: UUID | None = None,
    model_id: UUID | None = None,
):
    journey = get_customer_journey(db, contact_id=contact_id, lead_context_id=lead_context_id, model_id=model_id)
    if not journey:
        return None
    return _serialize_journey(db, journey, model_id=model_id)


@router.get("/models", response_model=list[AttributionModelResponse])
def get_attribution_models(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_attribution")),
):
    models = list_models(db)
    result = []
    for m in models:
        available, reason = _model_availability(m)
        result.append(
            AttributionModelResponse(
                id=m.id,
                name=m.name,
                model_type=m.model_type.value,
                config_json=m.config_json,
                is_default=m.is_default,
                is_active=m.is_active,
                description=m.description,
                available=available,
                unavailable_reason=reason,
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
        )
    return result


@router.post("/models", response_model=AttributionModelResponse, status_code=status.HTTP_201_CREATED)
def create_attribution_model(
    payload: AttributionModelCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_attribution_models")),
):
    model = create_model(db, payload=payload.model_dump(), user_id=user.id)
    db.commit()
    _audit(db, user, "model.changed", model.id)
    db.commit()
    available, reason = _model_availability(model)
    return AttributionModelResponse(
        id=model.id,
        name=model.name,
        model_type=model.model_type.value,
        config_json=model.config_json,
        is_default=model.is_default,
        is_active=model.is_active,
        description=model.description,
        available=available,
        unavailable_reason=reason,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.put("/models/{model_id}", response_model=AttributionModelResponse)
def update_attribution_model(
    model_id: UUID,
    payload: AttributionModelUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_attribution_models")),
):
    model = update_model(db, model_id, payload=payload.model_dump(exclude_unset=True), user_id=user.id)
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    db.commit()
    _audit(db, user, "model.changed", model.id)
    db.commit()
    available, reason = _model_availability(model)
    return AttributionModelResponse(
        id=model.id,
        name=model.name,
        model_type=model.model_type.value,
        config_json=model.config_json,
        is_default=model.is_default,
        is_active=model.is_active,
        description=model.description,
        available=available,
        unavailable_reason=reason,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.get("/rules", response_model=list[AttributionRuleResponse])
def get_attribution_rules(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_attribution")),
):
    return [AttributionRuleResponse.model_validate(r) for r in list_rules(db)]


@router.post("/rules", response_model=AttributionRuleResponse, status_code=status.HTTP_201_CREATED)
def create_attribution_rule(
    payload: AttributionRuleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_attribution_rules")),
):
    rule = create_rule(db, payload=payload.model_dump(), user_id=user.id)
    db.commit()
    _audit(db, user, "rule.changed", rule.id)
    db.commit()
    return AttributionRuleResponse.model_validate(rule)


@router.put("/rules/{rule_id}", response_model=AttributionRuleResponse)
def update_attribution_rule(
    rule_id: UUID,
    payload: AttributionRuleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_attribution_rules")),
):
    rule = update_rule(db, rule_id, payload=payload.model_dump(exclude_unset=True), user_id=user.id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    db.commit()
    _audit(db, user, "rule.changed", rule.id)
    db.commit()
    return AttributionRuleResponse.model_validate(rule)


@router.get("/health", response_model=AttributionHealthResponse)
def get_attribution_health(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_attribution")),
):
    data = build_health_summary(db)
    return AttributionHealthResponse(
        overall_status=data["overall_status"],
        healthy_count=data["healthy_count"],
        warning_count=data["warning_count"],
        critical_count=data["critical_count"],
        issues=[AttributionHealthIssueResponse.model_validate(i) for i in data["issues"]],
        summary=data["summary"],
    )


@router.get("/conversions", response_model=AttributionConversionListResponse)
def get_attribution_conversions(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_attribution")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    items, total = list_attribution_conversions(db, page=page, page_size=page_size)
    return AttributionConversionListResponse(
        items=[AttributionConversionResponse(**i) for i in items],
        **{k: v for k, v in paginate([], page, page_size, total).items() if k != "items"},
    )


@router.post("/compute", response_model=ComputeAttributionResponse)
def compute_attribution_route(
    payload: ComputeAttributionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "compute_attribution")),
):
    result = compute_attribution(
        db,
        model_id=payload.model_id,
        journey_ids=payload.journey_ids,
        rebuild_journeys=payload.rebuild_journeys,
        rebuild_touchpoints=payload.rebuild_touchpoints,
    )
    _audit(db, user, "updated", result.get("model_id") or get_default_model(db).id if get_default_model(db) else user.id)
    db.commit()
    return ComputeAttributionResponse(**result)
