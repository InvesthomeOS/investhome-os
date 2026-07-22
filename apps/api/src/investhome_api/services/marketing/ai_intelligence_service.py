"""Marketing AI intelligence — rule-based analytics, framework slots, no fabricated ML."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.marketing import MarketingCampaign, MarketingLeadContext
from investhome_api.models.marketing_ai import (
    AIConfidenceLevel,
    AIPredictionFramework,
    MarketingAIAnomaly,
    MarketingAIBriefing,
    MarketingAICopilotQuery,
    MarketingAIInsight,
    MarketingAIPrediction,
    MarketingAIRecommendation,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_ai import (
    AIAnomalyItem,
    AIAnomalyListResponse,
    AIBriefingItem,
    AIBriefingResponse,
    AIDashboardResponse,
    AIDashboardSection,
    AIInsightItem,
    AIInsightListResponse,
    AIMarketingHealthCategory,
    AIMarketingHealthResponse,
    AIPredictionFrameworkResponse,
    AIPredictionItem,
    AIPredictionsResponse,
    AIRecommendationItem,
    AIRecommendationListResponse,
    AISettingsResponse,
    AISettingsUpdate,
    CopilotAnswerSection,
    CopilotQueryResponse,
)
from investhome_api.schemas.marketing_analytics import MarketingDashboardFilters, MarketingTimeFilter
from investhome_api.services.marketing.analytics_service import (
    build_executive_dashboard,
    build_kpis,
    compute_health,
    fetch_executive_alerts,
    fetch_recommendations,
)

PREDICTION_FRAMEWORKS: list[dict] = [
    {
        "framework": "lead_scoring",
        "label": "Lead Scoring",
        "description": "Probability scores for Lead, Reservation, Sale, Investor, and Broker conversion.",
        "slots": [
            ("lead_probability", "Lead Conversion Probability"),
            ("reservation_probability", "Reservation Probability"),
            ("sale_probability", "Sale Probability"),
            ("investor_probability", "Investor Probability"),
            ("broker_probability", "Broker Probability"),
        ],
    },
    {
        "framework": "predictive_revenue",
        "label": "Predictive Revenue",
        "description": "Revenue, reservation, lead, pipeline, and conversion forecasts.",
        "slots": [
            ("revenue_forecast", "Revenue Forecast"),
            ("reservation_forecast", "Reservation Forecast"),
            ("lead_forecast", "Lead Forecast"),
            ("pipeline_forecast", "Pipeline Forecast"),
            ("conversion_forecast", "Conversion Forecast"),
        ],
    },
    {
        "framework": "campaign_optimization",
        "label": "Campaign Optimization",
        "description": "Increase, decrease, pause, scale, duplicate, and creative refresh recommendations.",
        "slots": [
            ("budget_adjustment", "Budget Adjustment Signal"),
            ("pause_signal", "Pause Signal"),
            ("scale_signal", "Scale Signal"),
            ("creative_refresh", "Creative Refresh Signal"),
        ],
    },
    {
        "framework": "creative_intelligence",
        "label": "Creative Intelligence",
        "description": "Fatigue, quality, CTR/conversion trends, and rotation recommendations.",
        "slots": [
            ("fatigue_score", "Creative Fatigue"),
            ("quality_score", "Creative Quality"),
            ("ctr_trend", "CTR Trend"),
            ("conversion_trend", "Conversion Trend"),
            ("rotation_recommendation", "Rotation Recommendation"),
        ],
    },
    {
        "framework": "audience_intelligence",
        "label": "Audience Intelligence",
        "description": "Growth, quality, saturation, expansion, and overlap analysis.",
        "slots": [
            ("growth_signal", "Audience Growth"),
            ("quality_signal", "Audience Quality"),
            ("saturation_signal", "Audience Saturation"),
            ("expansion_signal", "Expansion Opportunity"),
            ("overlap_signal", "Audience Overlap"),
        ],
    },
    {
        "framework": "budget_optimization",
        "label": "Budget Optimization",
        "description": "Reallocation recommendations — never auto-executed.",
        "slots": [
            ("reallocation_signal", "Reallocation Recommendation"),
            ("efficiency_score", "Spend Efficiency"),
        ],
    },
    {
        "framework": "next_best_action",
        "label": "Next Best Action",
        "description": "Suggested actions: call lead, assign sales, send email/WhatsApp, increase budget.",
        "slots": [
            ("primary_action", "Primary Action"),
            ("secondary_action", "Secondary Action"),
        ],
    },
]

COPILOT_INTENT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("best_campaign", re.compile(r"\b(best|top|highest)\b.*\bcampaign", re.I)),
    ("country_conversion", re.compile(r"\b(country|region|geo)\b.*\b(conversion|convert)", re.I)),
    ("projects_needing_marketing", re.compile(r"\bproject(s)?\b.*\b(need|marketing|promot)", re.I)),
    ("lead_decrease", re.compile(r"\b(lead|leads)\b.*\b(decrease|drop|declin|down|fall)", re.I)),
    ("comparison", re.compile(r"\b(compare|comparison|versus|vs\.?)\b", re.I)),
    ("broker_performance", re.compile(r"\bbroker\b.*\b(performance|convert|lead)", re.I)),
    ("landing_page_performance", re.compile(r"\b(landing\s*page|lp)\b.*\b(performance|convert|ctr)", re.I)),
    ("predict_leads", re.compile(r"\b(predict|forecast)\b.*\b(lead|qualified|reservation)", re.I)),
    ("budget_allocation", re.compile(r"\b(budget|spend|allocation)\b", re.I)),
    ("campaign_performance", re.compile(r"\bcampaign\b.*\b(performance|result|metric)", re.I)),
]


def _confidence_value(level: AIConfidenceLevel | str) -> str:
    return level.value if hasattr(level, "value") else str(level)


def _serialize_insight(row: MarketingAIInsight) -> AIInsightItem:
    return AIInsightItem(
        id=row.id,
        category=_confidence_value(row.category) if hasattr(row.category, "value") else str(row.category),
        severity=_confidence_value(row.severity) if hasattr(row.severity, "value") else str(row.severity),
        title=row.title,
        summary=row.summary,
        confidence=_confidence_value(row.confidence),
        evidence_refs=row.evidence_refs,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        created_at=row.created_at,
    )


def _serialize_recommendation(row: MarketingAIRecommendation) -> AIRecommendationItem:
    return AIRecommendationItem(
        id=row.id,
        recommendation_type=_confidence_value(row.recommendation_type)
        if hasattr(row.recommendation_type, "value")
        else str(row.recommendation_type),
        title=row.title,
        rationale=row.rationale,
        confidence=_confidence_value(row.confidence),
        evidence_refs=row.evidence_refs,
        requires_evidence=row.requires_evidence,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        status=row.status,
        created_at=row.created_at,
    )


def _serialize_anomaly(row: MarketingAIAnomaly) -> AIAnomalyItem:
    return AIAnomalyItem(
        id=row.id,
        anomaly_type=_confidence_value(row.anomaly_type) if hasattr(row.anomaly_type, "value") else str(row.anomaly_type),
        title=row.title,
        description=row.description,
        confidence=_confidence_value(row.confidence),
        severity=_confidence_value(row.severity) if hasattr(row.severity, "value") else str(row.severity),
        evidence_refs=row.evidence_refs,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        is_resolved=row.is_resolved,
        detected_at=row.detected_at,
    )


def _parse_intent(query: str) -> str | None:
    normalized = query.strip()
    for intent, pattern in COPILOT_INTENT_PATTERNS:
        if pattern.search(normalized):
            return intent
    return None


def _derive_insights_from_analytics(db: Session, user: User) -> list[AIInsightItem]:
    derived: list[AIInsightItem] = []
    time_filter = MarketingTimeFilter(preset="last_30_days")
    filters = MarketingDashboardFilters()
    kpis = {k.key: k for k in build_kpis(db, user, time_filter=time_filter, filters=filters)}

    lead_kpi = kpis.get("marketing_leads")
    if lead_kpi and lead_kpi.state == "ready" and (lead_kpi.value or 0) > 0:
        derived.append(
            AIInsightItem(
                id=UUID(int=0),
                category="campaign",
                severity="info",
                title="Marketing leads captured",
                summary=f"{lead_kpi.value} marketing lead(s) recorded in the selected period.",
                confidence="medium",
                evidence_refs=[{"source": "analytics.kpis", "metric_key": "marketing_leads", "value": str(lead_kpi.value)}],
            )
        )

    for alert in fetch_executive_alerts(db):
        derived.append(
            AIInsightItem(
                id=alert.id if hasattr(alert, "id") else UUID(int=0),
                category="general",
                severity=alert.severity if isinstance(alert.severity, str) else getattr(alert.severity, "value", "info"),
                title=alert.title,
                summary=alert.message,
                confidence="medium" if alert.message else "unknown",
                evidence_refs=[{"source": "analytics.alerts", "metric_key": alert.category}],
            )
        )

    return derived


def get_marketing_insights(
    db: Session,
    user: User,
    *,
    category: str | None = None,
    limit: int = 50,
) -> AIInsightListResponse:
    query = select(MarketingAIInsight).where(MarketingAIInsight.is_active.is_(True))
    if category:
        query = query.where(MarketingAIInsight.category == category)
    rows = db.scalars(query.order_by(MarketingAIInsight.created_at.desc()).limit(limit)).all()
    items = [_serialize_insight(row) for row in rows]
    if not items:
        items = _derive_insights_from_analytics(db, user)
    return AIInsightListResponse(items=items, total=len(items))


def _build_framework_recommendations(db: Session, user: User) -> list[AIRecommendationItem]:
    stored = db.scalars(
        select(MarketingAIRecommendation).order_by(MarketingAIRecommendation.created_at.desc()).limit(20)
    ).all()
    if stored:
        return [_serialize_recommendation(row) for row in stored]

    items: list[AIRecommendationItem] = []
    time_filter = MarketingTimeFilter(preset="last_30_days")
    filters = MarketingDashboardFilters()
    kpis = {k.key: k for k in build_kpis(db, user, time_filter=time_filter, filters=filters)}

    campaigns = db.scalars(select(MarketingCampaign).limit(5)).all()
    for campaign in campaigns:
        lead_count = db.scalar(
            select(func.count())
            .select_from(MarketingLeadContext)
            .where(MarketingLeadContext.campaign_id == campaign.id)
        ) or 0
        evidence = [
            {
                "source": "marketing_leads",
                "entity_type": "campaign",
                "entity_id": str(campaign.id),
                "metric_key": "lead_count",
                "value": str(lead_count),
            }
        ]
        if lead_count == 0:
            items.append(
                AIRecommendationItem(
                    id=UUID(int=0),
                    recommendation_type="improve_landing_page",
                    title=f"Review campaign: {campaign.name}",
                    rationale="Campaign has zero linked marketing leads — review landing page and tracking.",
                    confidence="medium",
                    evidence_refs=evidence,
                    requires_evidence=True,
                    entity_type="campaign",
                    entity_id=campaign.id,
                )
            )

    tracking_kpi = kpis.get("marketing_leads")
    if tracking_kpi and tracking_kpi.state == "unknown":
        items.append(
            AIRecommendationItem(
                id=UUID(int=0),
                recommendation_type="fix_tracking",
                title="Verify marketing tracking configuration",
                rationale="Lead metrics are unavailable — tracking or data source may not be connected.",
                confidence="unknown",
                evidence_refs=[{"source": "analytics.kpis", "metric_key": "marketing_leads", "value": "unknown"}],
                requires_evidence=True,
            )
        )

    for rec in fetch_recommendations(db):
        items.append(
            AIRecommendationItem(
                id=rec.id if hasattr(rec, "id") else UUID(int=0),
                recommendation_type="other",
                title=rec.title,
                rationale=rec.rationale or rec.description or "",
                confidence="medium" if (rec.rationale or rec.description) else "unknown",
                evidence_refs=[{"source": "analytics.recommendations", "metric_key": rec.recommendation_type}],
                requires_evidence=True,
            )
        )

    return items[:20]


def get_recommendations(
    db: Session,
    user: User,
    *,
    recommendation_type: str | None = None,
    limit: int = 50,
) -> AIRecommendationListResponse:
    query = select(MarketingAIRecommendation)
    if recommendation_type:
        query = query.where(MarketingAIRecommendation.recommendation_type == recommendation_type)
    rows = db.scalars(query.order_by(MarketingAIRecommendation.created_at.desc()).limit(limit)).all()
    if rows:
        items = [_serialize_recommendation(row) for row in rows]
    else:
        items = _build_framework_recommendations(db, user)
    return AIRecommendationListResponse(items=items, total=len(items))


def get_predictions(db: Session) -> AIPredictionsResponse:
    stored_by_framework: dict[str, list[MarketingAIPrediction]] = {}
    for row in db.scalars(select(MarketingAIPrediction)).all():
        fw = _confidence_value(row.framework)
        stored_by_framework.setdefault(fw, []).append(row)

    frameworks: list[AIPredictionFrameworkResponse] = []
    for spec in PREDICTION_FRAMEWORKS:
        fw_key = spec["framework"]
        stored = stored_by_framework.get(fw_key, [])
        stored_map = {row.prediction_key: row for row in stored}
        items: list[AIPredictionItem] = []
        for slot_key, slot_label in spec["slots"]:
            row = stored_map.get(slot_key)
            if row:
                items.append(
                    AIPredictionItem(
                        id=row.id,
                        framework=fw_key,
                        prediction_key=row.prediction_key,
                        label=row.label,
                        value=row.value,
                        confidence=_confidence_value(row.confidence),
                        confidence_pct=row.confidence_pct,
                        model_version=row.model_version,
                        metadata_json=row.metadata_json,
                        entity_type=row.entity_type,
                        entity_id=row.entity_id,
                    )
                )
            else:
                items.append(
                    AIPredictionItem(
                        framework=fw_key,
                        prediction_key=slot_key,
                        label=slot_label,
                        value=None,
                        confidence="unknown",
                        confidence_pct=None,
                        model_version=None,
                    )
                )
        frameworks.append(
            AIPredictionFrameworkResponse(
                framework=fw_key,
                label=spec["label"],
                description=spec["description"],
                model_connected=False,
                items=items,
            )
        )
    return AIPredictionsResponse(frameworks=frameworks)


def get_anomalies(db: Session, *, limit: int = 50) -> AIAnomalyListResponse:
    rows = db.scalars(
        select(MarketingAIAnomaly)
        .where(MarketingAIAnomaly.is_resolved.is_(False))
        .order_by(MarketingAIAnomaly.detected_at.desc())
        .limit(limit)
    ).all()
    return AIAnomalyListResponse(items=[_serialize_anomaly(row) for row in rows], total=len(rows))


def get_executive_briefing(db: Session, user: User, *, period: str = "weekly") -> AIBriefingResponse:
    row = db.scalar(
        select(MarketingAIBriefing)
        .where(MarketingAIBriefing.period == period)
        .order_by(MarketingAIBriefing.generated_at.desc())
        .limit(1)
    )
    if row:
        return AIBriefingResponse(
            briefing=AIBriefingItem(
                id=row.id,
                period=_confidence_value(row.period),
                title=row.title,
                summary=row.summary,
                confidence=_confidence_value(row.confidence),
                sections=row.sections_json,
                generated_at=row.generated_at,
            )
        )

    time_filter = MarketingTimeFilter(preset="last_7_days" if period == "weekly" else "last_30_days")
    filters = MarketingDashboardFilters()
    kpis = build_kpis(db, user, time_filter=time_filter, filters=filters)
    ready_kpis = [k for k in kpis if k.state == "ready"]
    if not ready_kpis:
        return AIBriefingResponse(
            briefing=AIBriefingItem(
                period=period,
                title=f"{period.title()} Marketing Briefing",
                summary="Insufficient data to generate an executive briefing. Connect analytics and campaign data sources.",
                confidence="unknown",
                sections=[
                    {"key": "status", "title": "Data Status", "content": "No connected metrics available for this period."}
                ],
            )
        )

    sections = [
        {
            "key": "highlights",
            "title": "Operational Highlights",
            "content": f"{len(ready_kpis)} KPI(s) reporting from connected data sources.",
            "data_points": [{"key": k.key, "label": k.label, "value": k.value, "state": k.state} for k in ready_kpis[:8]],
        }
    ]
    return AIBriefingResponse(
        briefing=AIBriefingItem(
            period=period,
            title=f"{period.title()} Marketing Briefing",
            summary="Briefing compiled from available operational data only — no ML model pipeline connected.",
            confidence="low",
            sections=sections,
            generated_at=datetime.now(UTC),
        )
    )


def get_marketing_health(db: Session, user: User) -> AIMarketingHealthResponse:
    base_health = compute_health(db, user)
    categories: list[AIMarketingHealthCategory] = []
    for cat in base_health.categories[:6]:
        categories.append(
            AIMarketingHealthCategory(
                key=cat.key,
                label=cat.label,
                status=cat.status if isinstance(cat.status, str) else getattr(cat.status, "value", "unknown"),
                score=None,
                message=cat.summary,
            )
        )
    categories.extend(
        [
            AIMarketingHealthCategory(
                key="prediction_pipeline",
                label="Prediction Pipeline",
                status="unknown",
                message="ML model pipeline not connected — predictions show Unknown.",
            ),
            AIMarketingHealthCategory(
                key="copilot_data",
                label="Copilot Data Coverage",
                status="warning" if base_health.overall_status == "unknown" else "healthy",
                message="Copilot answers from connected analytics data only.",
            ),
        ]
    )
    overall = base_health.overall_status
    if not isinstance(overall, str):
        overall = getattr(overall, "value", "unknown")
    return AIMarketingHealthResponse(
        overall_status=str(overall),
        overall_score=None,
        confidence="unknown",
        categories=categories,
        data_freshness_at=datetime.now(UTC),
    )


def build_ai_dashboard(db: Session, user: User) -> AIDashboardResponse:
    health = get_marketing_health(db, user)
    insights = get_marketing_insights(db, user, limit=5)
    recommendations = get_recommendations(db, user, limit=10)
    anomalies = get_anomalies(db, limit=5)
    briefing = get_executive_briefing(db, user).briefing
    predictions = get_predictions(db)

    campaign_recs = [r for r in recommendations.items if r.entity_type == "campaign" or r.recommendation_type in {
        "pause_campaign", "scale_campaign", "duplicate_campaign", "refresh_creative", "improve_landing_page"
    }]
    budget_recs = [r for r in recommendations.items if "budget" in r.recommendation_type]

    prediction_items = [item for fw in predictions.frameworks for item in fw.items]
    unknown_predictions = sum(1 for p in prediction_items if p.confidence == "unknown")

    return AIDashboardResponse(
        executive_summary=(
            "AI Marketing Intelligence layer active. Insights and recommendations derive from connected "
            "operational data — prediction models not connected."
        ),
        marketing_health=health,
        critical_insights=[i for i in insights.items if i.severity in ("critical", "warning")][:5],
        campaign_recommendations=campaign_recs[:5],
        budget_recommendations=budget_recs[:5],
        lead_quality=AIDashboardSection(
            key="lead_quality",
            title="Lead Quality",
            status="unknown",
            confidence="unknown",
            items=[{"message": "Lead scoring model not connected."}],
        ),
        prediction_confidence=AIDashboardSection(
            key="prediction_confidence",
            title="Prediction Confidence",
            status="unknown" if unknown_predictions == len(prediction_items) else "partial",
            confidence="unknown",
            items=[{"unknown_slots": unknown_predictions, "total_slots": len(prediction_items)}],
        ),
        anomaly_alerts=anomalies.items,
        next_best_actions=[r for r in recommendations.items if r.recommendation_type in {
            "call_lead", "assign_sales", "send_email", "send_whatsapp", "increase_budget"
        }][:5],
        executive_briefing=briefing,
        data_freshness_at=datetime.now(UTC),
    )


def query_copilot(
    db: Session,
    user: User,
    *,
    query_text: str,
    preset: str = "last_30_days",
    timezone: str = "UTC",
) -> CopilotQueryResponse:
    intent = _parse_intent(query_text)
    time_filter = MarketingTimeFilter(preset=preset, timezone=timezone)
    filters = MarketingDashboardFilters()
    evidence: list[dict] = []
    sections: list[CopilotAnswerSection] = []
    insufficient = False
    confidence = AIConfidenceLevel.UNKNOWN
    answer = "I can only answer from connected operational data. No matching intent or insufficient data."

    if intent == "best_campaign":
        campaigns = db.scalars(
            select(MarketingCampaign).order_by(MarketingCampaign.created_at.desc()).limit(10)
        ).all()
        if not campaigns:
            insufficient = True
            answer = "Insufficient data — no campaigns found."
        else:
            ranked = []
            for campaign in campaigns:
                lead_count = db.scalar(
                    select(func.count())
                    .select_from(MarketingLeadContext)
                    .where(MarketingLeadContext.campaign_id == campaign.id)
                ) or 0
                ranked.append((campaign, lead_count))
            ranked.sort(key=lambda x: x[1], reverse=True)
            best, count = ranked[0]
            confidence = AIConfidenceLevel.MEDIUM if count > 0 else AIConfidenceLevel.LOW
            answer = (
                f"Based on linked marketing leads, '{best.name}' has the highest count ({count}). "
                "This uses operational lead linkage only — not predictive ML."
            )
            evidence.append(
                {"source": "marketing_leads", "entity_type": "campaign", "entity_id": str(best.id), "value": str(count)}
            )
            sections.append(
                CopilotAnswerSection(
                    heading="Campaign ranking (by linked leads)",
                    content=answer,
                    data_points=[
                        {"campaign": c.name, "lead_count": lc} for c, lc in ranked[:5]
                    ],
                )
            )

    elif intent == "country_conversion":
        insufficient = True
        answer = "Insufficient data — country-level conversion metrics are not connected."

    elif intent == "projects_needing_marketing":
        insufficient = True
        answer = "Insufficient data — project-to-campaign coverage mapping is not fully connected."

    elif intent == "lead_decrease":
        kpis = build_kpis(db, user, time_filter=time_filter, filters=filters)
        lead_kpi = next((k for k in kpis if k.key == "marketing_leads"), None)
        if not lead_kpi or lead_kpi.state == "unknown":
            insufficient = True
            answer = "Insufficient data — historical lead trend data is not connected."
        else:
            confidence = AIConfidenceLevel.LOW
            answer = (
                f"Current period shows {lead_kpi.value or 0} marketing leads (state: {lead_kpi.state}). "
                "Period-over-period comparison requires trend data not yet connected."
            )
            evidence.append({"source": "analytics.kpis", "metric_key": "marketing_leads", "value": str(lead_kpi.value)})

    elif intent == "predict_leads":
        insufficient = True
        answer = (
            "Prediction framework slot available but ML model pipeline is not connected. "
            "Cannot forecast qualified leads or reservations."
        )

    elif intent == "budget_allocation":
        insufficient = True
        answer = "Insufficient data — budget optimization requires connected spend and performance data."

    elif intent in {"broker_performance", "landing_page_performance", "comparison", "campaign_performance"}:
        exec_dash = build_executive_dashboard(db, user, time_filter=time_filter, filters=filters)
        ready_kpis = [k for k in exec_dash.kpis if k.state == "ready"]
        if not ready_kpis:
            insufficient = True
            answer = "Insufficient data — requested performance metrics are not connected."
        else:
            confidence = AIConfidenceLevel.MEDIUM
            answer = f"Available operational metrics for '{intent.replace('_', ' ')}': {len(ready_kpis)} KPI(s) reporting."
            sections.append(
                CopilotAnswerSection(
                    heading="Connected KPIs",
                    content="Values from analytics executive dashboard.",
                    data_points=[{"key": k.key, "label": k.label, "value": k.value} for k in ready_kpis[:6]],
                )
            )
            for k in ready_kpis[:3]:
                evidence.append({"source": "analytics.kpis", "metric_key": k.key, "value": str(k.value)})

    elif intent is None:
        insufficient = True
        answer = (
            "Could not map query to a supported analytics intent. "
            "Try asking about best campaign, lead trends, or campaign performance."
        )

    response = CopilotQueryResponse(
        query=query_text,
        intent=intent,
        answer=answer,
        sections=sections,
        evidence_refs=evidence,
        confidence=_confidence_value(confidence),
        insufficient_data=insufficient,
        model_connected=False,
    )

    log_row = MarketingAICopilotQuery(
        user_id=user.id,
        query_text=query_text,
        intent=intent,
        response_json=response.model_dump(mode="json"),
        confidence=confidence,
    )
    db.add(log_row)
    return response


def accept_recommendation(db: Session, user: User, recommendation_id: UUID) -> AIRecommendationItem:
    row = db.get(MarketingAIRecommendation, recommendation_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
    if row.requires_evidence and not row.evidence_refs:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Recommendation requires evidence before acceptance",
        )
    row.status = "accepted"
    row.accepted_by_user_id = user.id
    row.accepted_at = datetime.now(UTC)
    db.flush()
    return _serialize_recommendation(row)


def get_ai_settings() -> AISettingsResponse:
    return AISettingsResponse()


def update_ai_settings(payload: AISettingsUpdate) -> AISettingsResponse:
    current = get_ai_settings()
    data = current.model_dump()
    for field, value in payload.model_dump(exclude_unset=True).items():
        data[field] = value
    return AISettingsResponse(**data)
