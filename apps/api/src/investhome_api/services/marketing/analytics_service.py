"""Marketing analytics aggregation — honest operational data only."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.marketing import (
    MarketingCampaign,
    MarketingChannel,
    MarketingLeadContext,
    MarketingLeadHandoffStatus,
    MarketingRecommendation,
)
from investhome_api.models.marketing_analytics import (
    DashboardVisibility,
    HealthCategoryStatus,
    MarketingDashboardLayout,
    MarketingDashboardSavedView,
    MarketingExecutiveAlert,
    MarketingHealthSnapshot,
)
from investhome_api.models.marketing_landing_conversion import (
    MarketingFormSubmission,
    MarketingLandingPage,
    MarketingSalesHandoff,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_analytics import (
    CampaignSummaryItem,
    ChannelSummaryItem,
    DashboardLayoutCreate,
    DashboardLayoutResponse,
    DashboardLayoutUpdate,
    DashboardSavedViewCreate,
    DashboardSavedViewResponse,
    DashboardSavedViewUpdate,
    ExecutiveAlertItem,
    FunnelStage,
    HealthCategory,
    MarketingDashboardFilters,
    MarketingExecutiveDashboardResponse,
    MarketingFunnelResponse,
    MarketingHealthResponse,
    MarketingKPIsResponse,
    MarketingTimeFilter,
    MarketingWidgetsResponse,
    MetricValue,
    RecommendationItem,
    WidgetConfig,
)
from investhome_api.services.permission_service import user_has_permission

HEALTH_CATEGORIES = [
    ("tracking", "Tracking"),
    ("data_quality", "Data Quality"),
    ("campaign_readiness", "Campaign Readiness"),
    ("content_readiness", "Content Readiness"),
    ("lead_quality", "Lead Quality"),
    ("conversion_configuration", "Conversion Configuration"),
    ("integrations", "Integrations"),
    ("permissions", "Permissions"),
    ("publishing_status", "Publishing Status"),
    ("consent", "Consent"),
]

FUNNEL_STAGES = [
    ("visitors", "Visitors"),
    ("landing_page_views", "Landing Page Views"),
    ("cta_clicks", "CTA Clicks"),
    ("form_starts", "Form Starts"),
    ("form_submissions", "Form Submissions"),
    ("verified_leads", "Verified Leads"),
    ("qualified_leads", "Qualified Leads"),
    ("sales_handoff", "Sales Handoff"),
    ("opportunity", "Opportunity"),
    ("reservation", "Reservation"),
    ("sale", "Sale"),
]

DEFAULT_EXECUTIVE_WIDGETS = [
    {"key": "kpi_bar", "widget_type": "metric_row", "title": "KPI Bar"},
    {"key": "funnel", "widget_type": "funnel", "title": "Conversion Funnel"},
    {"key": "campaign_summary", "widget_type": "table", "title": "Campaign Summary"},
    {"key": "channel_summary", "widget_type": "table", "title": "Channel Summary"},
    {"key": "lead_quality", "widget_type": "status_grid", "title": "Lead Quality"},
    {"key": "sales_handoff", "widget_type": "metric", "title": "Sales Handoff"},
    {"key": "health_grid", "widget_type": "status_grid", "title": "Health Overview"},
    {"key": "alerts", "widget_type": "alert_panel", "title": "Executive Alerts"},
    {"key": "recommendations", "widget_type": "recommendation_panel", "title": "Recommendations"},
    {"key": "recent_campaigns", "widget_type": "timeline", "title": "Recent Campaigns"},
    {"key": "quick_actions", "widget_type": "card", "title": "Quick Actions"},
]


def _resolve_time_range(time_filter: MarketingTimeFilter) -> tuple[datetime | None, datetime | None]:
    tz = ZoneInfo(time_filter.timezone or "UTC")
    now = datetime.now(tz)
    preset = time_filter.preset

    if preset == "custom" and time_filter.start_at and time_filter.end_at:
        return time_filter.start_at, time_filter.end_at

    start: datetime | None
    end = now.astimezone(UTC)

    if preset == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
    elif preset == "yesterday":
        yesterday = now - timedelta(days=1)
        start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
        end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999).astimezone(UTC)
    elif preset == "last_7_days":
        start = (now - timedelta(days=7)).astimezone(UTC)
    elif preset == "last_90_days":
        start = (now - timedelta(days=90)).astimezone(UTC)
    elif preset == "this_month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
    elif preset == "previous_month":
        first_this = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_prev = first_this - timedelta(days=1)
        start = last_prev.replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
        end = last_prev.replace(hour=23, minute=59, second=59, microsecond=999999).astimezone(UTC)
    elif preset == "quarter":
        quarter_start_month = ((now.month - 1) // 3) * 3 + 1
        start = now.replace(month=quarter_start_month, day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
    elif preset == "year":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
    else:
        start = (now - timedelta(days=30)).astimezone(UTC)

    return start, end


def _apply_lead_filters(query, filters: MarketingDashboardFilters, *, model=MarketingLeadContext):
    if filters.campaign_id is not None:
        query = query.where(model.campaign_id == filters.campaign_id)
    if filters.source_id is not None:
        query = query.where(model.source_id == filters.source_id)
    if filters.channel_id is not None:
        query = query.where(model.channel_id == filters.channel_id)
    return query


def _count_leads(
    db: Session,
    filters: MarketingDashboardFilters,
    time_filter: MarketingTimeFilter,
    *,
    extra_where=None,
) -> int:
    start, end = _resolve_time_range(time_filter)
    query = select(func.count()).select_from(MarketingLeadContext)
    query = _apply_lead_filters(query, filters)
    if start is not None:
        query = query.where(MarketingLeadContext.created_at >= start)
    if end is not None:
        query = query.where(MarketingLeadContext.created_at <= end)
    if extra_where is not None:
        query = query.where(extra_where)
    return db.scalar(query) or 0


def _has_permission(user: User, action: str) -> bool:
    return user_has_permission(user, "marketing", action) or user_has_permission(user, "marketing", "view")


def _metric_unknown(key: str, label: str, *, reason: str = "unavailable") -> MetricValue:
    return MetricValue(key=key, label=label, state=reason, value=None)


def build_kpis(
    db: Session,
    user: User,
    *,
    time_filter: MarketingTimeFilter,
    filters: MarketingDashboardFilters,
) -> list[MetricValue]:
    now = datetime.now(UTC)
    kpis: list[MetricValue] = []

    if not _has_permission(user, "view_leads"):
        for key, label in [
            ("marketing_leads", "Marketing Leads"),
            ("qualified_leads", "Qualified Leads"),
            ("sales_handoffs", "Sales Handoffs"),
        ]:
            kpis.append(_metric_unknown(key, label, reason="permission_restricted"))
    else:
        lead_count = _count_leads(db, filters, time_filter)
        kpis.append(
            MetricValue(
                key="marketing_leads",
                label="Marketing Leads",
                state="ready" if lead_count > 0 else "empty",
                value=lead_count,
                freshness_at=now,
                evidence={"source": "marketing_lead_contexts", "count": lead_count},
            )
        )

        qualified_count = _count_leads(
            db,
            filters,
            time_filter,
            extra_where=MarketingLeadContext.marketing_status == "qualified",
        )
        kpis.append(
            MetricValue(
                key="qualified_leads",
                label="Qualified Leads",
                state="ready" if qualified_count > 0 else "empty",
                value=qualified_count,
                freshness_at=now,
                evidence={"source": "marketing_lead_contexts", "filter": "marketing_status=qualified"},
            )
        )

        handoff_query = select(func.count()).select_from(MarketingSalesHandoff)
        start, end = _resolve_time_range(time_filter)
        if start is not None:
            handoff_query = handoff_query.where(MarketingSalesHandoff.created_at >= start)
        if end is not None:
            handoff_query = handoff_query.where(MarketingSalesHandoff.created_at <= end)
        handoff_count = db.scalar(handoff_query) or 0
        if handoff_count == 0:
            handed_off_count = _count_leads(
                db,
                filters,
                time_filter,
                extra_where=MarketingLeadContext.handoff_status == MarketingLeadHandoffStatus.HANDED_OFF,
            )
            handoff_count = handed_off_count

        kpis.append(
            MetricValue(
                key="sales_handoffs",
                label="Sales Handoffs",
                state="ready" if handoff_count > 0 else "empty",
                value=handoff_count,
                freshness_at=now,
                evidence={"source": "marketing_sales_handoffs"},
            )
        )

    for key, label in [
        ("meetings", "Meetings"),
        ("reservations", "Reservations"),
        ("sales", "Sales"),
    ]:
        kpis.append(
            MetricValue(
                key=key,
                label=label,
                state="unknown",
                value=None,
                evidence={"reason": "Sales CRM integration not connected for this metric"},
            )
        )

    if _has_permission(user, "view_spend"):
        kpis.append(
            MetricValue(
                key="revenue",
                label="Revenue",
                state="unknown",
                value=None,
                evidence={"reason": "Finance revenue source not connected"},
            )
        )
    else:
        kpis.append(_metric_unknown("revenue", "Revenue", reason="permission_restricted"))

    submission_count = 0
    if _has_permission(user, "view_leads"):
        sub_query = select(func.count()).select_from(MarketingFormSubmission)
        start, end = _resolve_time_range(time_filter)
        if start is not None:
            sub_query = sub_query.where(MarketingFormSubmission.created_at >= start)
        if end is not None:
            sub_query = sub_query.where(MarketingFormSubmission.created_at <= end)
        submission_count = db.scalar(sub_query) or 0

    lead_count_for_rate = _count_leads(db, filters, time_filter) if _has_permission(user, "view_leads") else 0
    if submission_count > 0 and lead_count_for_rate > 0:
        rate = round((lead_count_for_rate / submission_count) * 100, 2)
        kpis.append(
            MetricValue(
                key="conversion_rate",
                label="Conversion Rate",
                state="ready",
                value=rate,
                unit="%",
                freshness_at=now,
                evidence={"numerator": lead_count_for_rate, "denominator": submission_count},
            )
        )
    else:
        kpis.append(
            MetricValue(
                key="conversion_rate",
                label="Conversion Rate",
                state="unknown",
                value=None,
                evidence={"reason": "Insufficient denominator data for conversion rate"},
            )
        )

    health = compute_health(db, user)
    kpis.extend(
        [
            MetricValue(
                key="marketing_health",
                label="Marketing Health",
                state="ready",
                value=health.overall_status,
                freshness_at=health.computed_at,
            ),
            MetricValue(
                key="tracking_health",
                label="Tracking Health",
                state="ready",
                value=next((c.status for c in health.categories if c.key == "tracking"), "unknown"),
                freshness_at=health.computed_at,
            ),
            MetricValue(
                key="attribution_health",
                label="Attribution Health",
                state="ready",
                value=next((c.status for c in health.categories if c.key == "data_quality"), "unknown"),
                freshness_at=health.computed_at,
            ),
            MetricValue(
                key="data_freshness",
                label="Data Freshness",
                state="ready",
                value=now.isoformat(),
                freshness_at=now,
            ),
        ]
    )

    return kpis


def _stage_unknown(key: str, label: str) -> FunnelStage:
    return FunnelStage(key=key, label=label, count=None, state="unknown")


def build_funnel(
    db: Session,
    user: User,
    *,
    time_filter: MarketingTimeFilter,
    filters: MarketingDashboardFilters,
) -> MarketingFunnelResponse:
    stages: list[FunnelStage] = []
    counts: dict[str, int | None] = {}

    if not _has_permission(user, "view_leads"):
        for key, label in FUNNEL_STAGES:
            stages.append(FunnelStage(key=key, label=label, count=None, state="permission_restricted"))
        return MarketingFunnelResponse(stages=stages, time_filter=time_filter, filters=filters)

    start, end = _resolve_time_range(time_filter)
    counts: dict[str, int | None] = {k: None for k, _ in FUNNEL_STAGES}

    sub_query = select(func.count()).select_from(MarketingFormSubmission)
    if start is not None:
        sub_query = sub_query.where(MarketingFormSubmission.created_at >= start)
    if end is not None:
        sub_query = sub_query.where(MarketingFormSubmission.created_at <= end)
    submission_count = db.scalar(sub_query) or 0
    counts["form_submissions"] = submission_count

    verified_count = _count_leads(
        db,
        filters,
        time_filter,
        extra_where=MarketingLeadContext.verification_status == "verified",
    )
    counts["verified_leads"] = verified_count

    qualified_count = _count_leads(
        db,
        filters,
        time_filter,
        extra_where=MarketingLeadContext.marketing_status == "qualified",
    )
    counts["qualified_leads"] = qualified_count

    handoff_count = _count_leads(
        db,
        filters,
        time_filter,
        extra_where=MarketingLeadContext.handoff_status == MarketingLeadHandoffStatus.HANDED_OFF,
    )
    counts["sales_handoff"] = handoff_count

    prev_count: int | None = None
    for key, label in FUNNEL_STAGES:
        count = counts.get(key)
        if count is None:
            stages.append(_stage_unknown(key, label))
            continue

        state = "ready" if count > 0 else "empty"
        conversion_percent: float | None = None
        drop_off_percent: float | None = None

        if prev_count is not None and prev_count > 0:
            conversion_percent = round((count / prev_count) * 100, 2)
            drop_off_percent = round(100 - conversion_percent, 2)

        stages.append(
            FunnelStage(
                key=key,
                label=label,
                count=count,
                state=state,
                conversion_percent=conversion_percent,
                drop_off_percent=drop_off_percent,
            )
        )
        if count is not None:
            prev_count = count

    return MarketingFunnelResponse(stages=stages, time_filter=time_filter, filters=filters)


def _derive_category_status(db: Session, key: str, user: User) -> HealthCategory:
    label = dict(HEALTH_CATEGORIES)[key]
    evidence: dict = {}

    if key == "tracking":
        source_count = db.scalar(select(func.count()).select_from(MarketingLeadContext).where(MarketingLeadContext.utm_data_json.isnot(None))) or 0
        if source_count == 0:
            return HealthCategory(key=key, label=label, status="unknown", summary="No UTM tracking data recorded", evidence={"utm_records": 0})
        return HealthCategory(key=key, label=label, status="healthy", summary=f"{source_count} leads with UTM data", evidence={"utm_records": source_count})

    if key == "data_quality":
        total = db.scalar(select(func.count()).select_from(MarketingLeadContext)) or 0
        with_contact = db.scalar(
            select(func.count()).select_from(MarketingLeadContext).where(MarketingLeadContext.contact_id.isnot(None))
        ) or 0
        if total == 0:
            return HealthCategory(key=key, label=label, status="unknown", summary="No lead data", evidence={"total": 0})
        ratio = with_contact / total
        status_val = "healthy" if ratio >= 0.8 else "warning" if ratio >= 0.5 else "critical"
        return HealthCategory(key=key, label=label, status=status_val, summary=f"{with_contact}/{total} leads linked to contacts", evidence={"linked": with_contact, "total": total})

    if key == "campaign_readiness":
        active = db.scalar(
            select(func.count()).select_from(MarketingCampaign).where(
                MarketingCampaign.archived_at.is_(None),
                MarketingCampaign.status.in_(["active", "scheduled", "approved"]),
            )
        ) or 0
        total = db.scalar(select(func.count()).select_from(MarketingCampaign).where(MarketingCampaign.archived_at.is_(None))) or 0
        if total == 0:
            return HealthCategory(key=key, label=label, status="unknown", summary="No campaigns configured")
        status_val = "healthy" if active > 0 else "warning"
        return HealthCategory(key=key, label=label, status=status_val, summary=f"{active} active of {total} campaigns", evidence={"active": active, "total": total})

    if key == "content_readiness":
        from investhome_api.models.marketing_content_studio import MarketingContent

        published = db.scalar(
            select(func.count()).select_from(MarketingContent).where(MarketingContent.status == "published")
        ) or 0
        total = db.scalar(select(func.count()).select_from(MarketingContent)) or 0
        if total == 0:
            return HealthCategory(key=key, label=label, status="unknown", summary="No content assets")
        status_val = "healthy" if published > 0 else "warning"
        return HealthCategory(key=key, label=label, status=status_val, summary=f"{published} published of {total} content items", evidence={"published": published, "total": total})

    if key == "lead_quality":
        verified = db.scalar(
            select(func.count()).select_from(MarketingLeadContext).where(MarketingLeadContext.verification_status == "verified")
        ) or 0
        total = db.scalar(select(func.count()).select_from(MarketingLeadContext)) or 0
        if total == 0:
            return HealthCategory(key=key, label=label, status="unknown", summary="No leads to assess")
        ratio = verified / total
        status_val = "healthy" if ratio >= 0.5 else "warning" if ratio > 0 else "critical"
        return HealthCategory(key=key, label=label, status=status_val, summary=f"{verified} verified of {total} leads", evidence={"verified": verified, "total": total})

    if key == "conversion_configuration":
        pages = db.scalar(select(func.count()).select_from(MarketingLandingPage)) or 0
        forms = db.scalar(select(func.count()).select_from(MarketingFormSubmission)) or 0
        if pages == 0:
            return HealthCategory(key=key, label=label, status="warning", summary="No landing pages configured", evidence={"landing_pages": 0})
        status_val = "healthy" if forms > 0 else "warning"
        return HealthCategory(key=key, label=label, status=status_val, summary=f"{pages} landing pages, {forms} submissions", evidence={"landing_pages": pages, "submissions": forms})

    if key == "integrations":
        channels = db.scalars(select(MarketingChannel)).all()
        if not channels:
            return HealthCategory(key=key, label=label, status="unknown", summary="No channels configured")
        connected = sum(1 for c in channels if c.connection_status.value == "connected")
        status_val = "healthy" if connected == len(channels) else "warning" if connected > 0 else "critical"
        return HealthCategory(key=key, label=label, status=status_val, summary=f"{connected}/{len(channels)} channels connected", evidence={"connected": connected, "total": len(channels)})

    if key == "permissions":
        has_dashboard = _has_permission(user, "view_dashboard")
        status_val = "healthy" if has_dashboard else "critical"
        return HealthCategory(key=key, label=label, status=status_val, summary="Dashboard access verified" if has_dashboard else "Missing dashboard permission")

    if key == "publishing_status":
        published_pages = db.scalar(
            select(func.count()).select_from(MarketingLandingPage).where(MarketingLandingPage.status == "published")
        ) or 0
        total_pages = db.scalar(select(func.count()).select_from(MarketingLandingPage)) or 0
        if total_pages == 0:
            return HealthCategory(key=key, label=label, status="unknown", summary="No landing pages")
        status_val = "healthy" if published_pages > 0 else "warning"
        return HealthCategory(key=key, label=label, status=status_val, summary=f"{published_pages} published pages", evidence={"published": published_pages, "total": total_pages})

    if key == "consent":
        from investhome_api.models.marketing_landing_conversion import ConsentEvidence

        consent_count = db.scalar(select(func.count()).select_from(ConsentEvidence)) or 0
        if consent_count == 0:
            return HealthCategory(key=key, label=label, status="unknown", summary="No consent evidence recorded")
        return HealthCategory(key=key, label=label, status="healthy", summary=f"{consent_count} consent records", evidence={"records": consent_count})

    return HealthCategory(key=key, label=label, status="unknown", summary="Not evaluated", evidence=evidence)


def _overall_from_categories(categories: list[HealthCategory]) -> str:
    statuses = [c.status for c in categories]
    if "critical" in statuses:
        return "critical"
    if "warning" in statuses:
        return "warning"
    if all(s == "healthy" for s in statuses):
        return "healthy"
    if all(s == "unknown" for s in statuses):
        return "unknown"
    return "warning"


def compute_health(db: Session, user: User) -> MarketingHealthResponse:
    categories = [_derive_category_status(db, key, user) for key, _ in HEALTH_CATEGORIES]
    overall = _overall_from_categories(categories)
    computed_at = datetime.now(UTC)

    snapshot = MarketingHealthSnapshot(
        overall_status=HealthCategoryStatus(overall),
        categories_json={c.key: {"status": c.status, "summary": c.summary} for c in categories},
        computed_by="system",
    )
    db.add(snapshot)
    db.flush()

    return MarketingHealthResponse(
        overall_status=overall,
        categories=categories,
        computed_at=computed_at,
        snapshot_id=snapshot.id,
    )


def compute_tracking_health(db: Session, user: User) -> MarketingHealthResponse:
    cat = _derive_category_status(db, "tracking", user)
    return MarketingHealthResponse(
        overall_status=cat.status,
        categories=[cat],
        computed_at=datetime.now(UTC),
    )


def compute_attribution_health(db: Session, user: User) -> MarketingHealthResponse:
    cat = _derive_category_status(db, "data_quality", user)
    return MarketingHealthResponse(
        overall_status=cat.status,
        categories=[cat],
        computed_at=datetime.now(UTC),
    )


def compute_data_health(db: Session, user: User) -> MarketingHealthResponse:
    cats = [_derive_category_status(db, "data_quality", user), _derive_category_status(db, "integrations", user)]
    return MarketingHealthResponse(
        overall_status=_overall_from_categories(cats),
        categories=cats,
        computed_at=datetime.now(UTC),
    )


def fetch_executive_alerts(db: Session, *, limit: int = 20) -> list[ExecutiveAlertItem]:
    rows = db.scalars(
        select(MarketingExecutiveAlert)
        .where(MarketingExecutiveAlert.is_resolved.is_(False))
        .order_by(MarketingExecutiveAlert.created_at.desc())
        .limit(limit)
    ).all()
    return [
        ExecutiveAlertItem(
            id=row.id,
            title=row.title,
            message=row.message,
            category=row.category,
            severity=row.severity.value if hasattr(row.severity, "value") else str(row.severity),
            evidence_json=row.evidence_json,
            is_resolved=row.is_resolved,
            created_at=row.created_at,
        )
        for row in rows
    ]


def fetch_recommendations(db: Session, *, limit: int = 20) -> list[RecommendationItem]:
    rows = db.scalars(
        select(MarketingRecommendation)
        .where(MarketingRecommendation.status == "active")
        .order_by(MarketingRecommendation.created_at.desc())
        .limit(limit)
    ).all()
    return [RecommendationItem.model_validate(row) for row in rows]


def _build_widgets(
    db: Session,
    user: User,
    *,
    kpis: list[MetricValue],
    funnel: MarketingFunnelResponse,
    health: MarketingHealthResponse,
    alerts: list[ExecutiveAlertItem],
    recommendations: list[RecommendationItem],
) -> list[WidgetConfig]:
    widgets: list[WidgetConfig] = []
    for spec in DEFAULT_EXECUTIVE_WIDGETS:
        key = spec["key"]
        data: dict | list | None = None
        state = "ready"

        if key == "kpi_bar":
            data = [k.model_dump() for k in kpis]
        elif key == "funnel":
            data = [s.model_dump() for s in funnel.stages]
        elif key == "health_grid":
            data = [c.model_dump() for c in health.categories]
        elif key == "alerts":
            data = [a.model_dump() for a in alerts]
            state = "empty" if not alerts else "ready"
        elif key == "recommendations":
            data = [r.model_dump() for r in recommendations]
            state = "empty" if not recommendations else "ready"
        elif key == "campaign_summary":
            campaigns = db.scalars(
                select(MarketingCampaign)
                .where(MarketingCampaign.archived_at.is_(None))
                .order_by(MarketingCampaign.updated_at.desc())
                .limit(10)
            ).all()
            data = [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "status": c.status.value if hasattr(c.status, "value") else str(c.status),
                }
                for c in campaigns
            ]
            state = "empty" if not campaigns else "ready"
        elif key == "channel_summary":
            channels = db.scalars(select(MarketingChannel).order_by(MarketingChannel.name).limit(10)).all()
            data = [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "connection_status": c.connection_status.value if hasattr(c.connection_status, "value") else str(c.connection_status),
                }
                for c in channels
            ]
            state = "empty" if not channels else "ready"

        widgets.append(
            WidgetConfig(
                key=key,
                title=spec["title"],
                widget_type=spec["widget_type"],
                state=state,
                export_enabled=_has_permission(user, "export_analytics"),
                data=data,
            )
        )
    return widgets


def build_executive_dashboard(
    db: Session,
    user: User,
    *,
    time_filter: MarketingTimeFilter,
    filters: MarketingDashboardFilters,
) -> MarketingExecutiveDashboardResponse:
    kpis = build_kpis(db, user, time_filter=time_filter, filters=filters)
    funnel = build_funnel(db, user, time_filter=time_filter, filters=filters)
    health = compute_health(db, user)
    tracking = compute_tracking_health(db, user)
    attribution = compute_attribution_health(db, user)
    data_health = compute_data_health(db, user)
    alerts = fetch_executive_alerts(db)
    recommendations = fetch_recommendations(db)

    campaigns = db.scalars(
        select(MarketingCampaign)
        .where(MarketingCampaign.archived_at.is_(None))
        .order_by(MarketingCampaign.updated_at.desc())
        .limit(10)
    ).all()
    active_campaigns = [
        CampaignSummaryItem(
            id=c.id,
            name=c.name,
            status=c.status.value if hasattr(c.status, "value") else str(c.status),
        )
        for c in campaigns
    ]

    channels = db.scalars(select(MarketingChannel).order_by(MarketingChannel.name).limit(10)).all()
    channel_summaries = [
        ChannelSummaryItem(
            id=c.id,
            name=c.name,
            category=c.category.value if hasattr(c.category, "value") else str(c.category),
            connection_status=c.connection_status.value if hasattr(c.connection_status, "value") else str(c.connection_status),
        )
        for c in channels
    ]

    widgets = _build_widgets(
        db,
        user,
        kpis=kpis,
        funnel=funnel,
        health=health,
        alerts=alerts,
        recommendations=recommendations,
    )

    return MarketingExecutiveDashboardResponse(
        kpis=kpis,
        funnel=funnel,
        health=health,
        tracking_health=tracking,
        attribution_health=attribution,
        data_health=data_health,
        alerts=alerts,
        recommendations=recommendations,
        active_campaigns=active_campaigns,
        channel_summaries=channel_summaries,
        widgets=widgets,
        time_filter=time_filter,
        filters=filters,
        data_freshness_at=datetime.now(UTC),
    )


def get_dashboard_widgets(
    db: Session,
    user: User,
    *,
    dashboard_key: str,
    time_filter: MarketingTimeFilter,
    filters: MarketingDashboardFilters,
) -> MarketingWidgetsResponse:
    exec_data = build_executive_dashboard(db, user, time_filter=time_filter, filters=filters)
    return MarketingWidgetsResponse(widgets=exec_data.widgets, dashboard_key=dashboard_key)


def list_layouts(db: Session, user_id: UUID, *, dashboard_key: str | None = None) -> list[DashboardLayoutResponse]:
    query = select(MarketingDashboardLayout).where(MarketingDashboardLayout.owner_user_id == user_id)
    if dashboard_key:
        query = query.where(MarketingDashboardLayout.dashboard_key == dashboard_key)
    rows = db.scalars(query.order_by(MarketingDashboardLayout.name)).all()
    return [DashboardLayoutResponse.model_validate(r) for r in rows]


def create_layout(db: Session, user: User, payload: DashboardLayoutCreate) -> DashboardLayoutResponse:
    layout = MarketingDashboardLayout(
        name=payload.name,
        owner_user_id=user.id,
        team_id=payload.team_id,
        visibility=DashboardVisibility(payload.visibility),
        widgets_json=payload.widgets_json,
        filters_json=payload.filters_json,
        is_default=payload.is_default,
        dashboard_key=payload.dashboard_key,
    )
    db.add(layout)
    db.flush()
    return DashboardLayoutResponse.model_validate(layout)


def get_layout(db: Session, layout_id: UUID) -> MarketingDashboardLayout:
    layout = db.get(MarketingDashboardLayout, layout_id)
    if layout is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Layout not found")
    return layout


def update_layout(db: Session, layout: MarketingDashboardLayout, payload: DashboardLayoutUpdate) -> DashboardLayoutResponse:
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "visibility" and value is not None:
            setattr(layout, field, DashboardVisibility(value))
        else:
            setattr(layout, field, value)
    db.flush()
    return DashboardLayoutResponse.model_validate(layout)


def delete_layout(db: Session, layout: MarketingDashboardLayout) -> None:
    db.delete(layout)


def list_saved_views(db: Session, user_id: UUID, *, dashboard_key: str | None = None) -> list[DashboardSavedViewResponse]:
    query = select(MarketingDashboardSavedView).where(MarketingDashboardSavedView.user_id == user_id)
    if dashboard_key:
        query = query.where(MarketingDashboardSavedView.dashboard_key == dashboard_key)
    rows = db.scalars(query.order_by(MarketingDashboardSavedView.name)).all()
    return [DashboardSavedViewResponse.model_validate(r) for r in rows]


def create_saved_view(db: Session, user: User, payload: DashboardSavedViewCreate) -> DashboardSavedViewResponse:
    view = MarketingDashboardSavedView(
        user_id=user.id,
        name=payload.name,
        dashboard_key=payload.dashboard_key,
        filters_json=payload.filters_json,
        time_filter_json=payload.time_filter_json,
        is_default=payload.is_default,
        is_shared=payload.is_shared,
    )
    db.add(view)
    db.flush()
    return DashboardSavedViewResponse.model_validate(view)


def get_saved_view(db: Session, view_id: UUID) -> MarketingDashboardSavedView:
    view = db.get(MarketingDashboardSavedView, view_id)
    if view is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved view not found")
    return view


def update_saved_view(
    db: Session, view: MarketingDashboardSavedView, payload: DashboardSavedViewUpdate
) -> DashboardSavedViewResponse:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(view, field, value)
    db.flush()
    return DashboardSavedViewResponse.model_validate(view)


def delete_saved_view(db: Session, view: MarketingDashboardSavedView) -> None:
    db.delete(view)
