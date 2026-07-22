"""Marketing workspace dashboard aggregation."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.marketing import (
    MarketingAlert,
    MarketingAudience,
    MarketingCampaign,
    MarketingChannel,
    MarketingLeadContext,
    MarketingRecommendation,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing import (
    MarketingAlertSummary,
    MarketingCampaignSummary,
    MarketingDashboardResponse,
    MarketingDashboardWidget,
    MarketingProviderStatus,
    MarketingRecommendationSummary,
)
from investhome_api.services.marketing.campaign_service import _to_summary, get_workspace_overview


DASHBOARD_WIDGET_KEYS = [
    "executive_summary",
    "active_campaigns",
    "lead_generation",
    "conversion_funnel",
    "channel_performance",
    "campaign_budget",
    "content_pipeline",
    "upcoming_events",
    "marketing_calendar",
    "lead_source_performance",
    "attribution_summary",
    "alerts",
    "recommended_actions",
    "quick_actions",
]


def _widget_state(*, has_permission: bool, count: int | None = None, connected: bool = True) -> str:
    if not has_permission:
        return "permission_restricted"
    if not connected:
        return "not_connected"
    if count is not None and count == 0:
        return "empty"
    return "no_data"


def _count(db: Session, model, *, exclude_archived: bool = True) -> int:
    query = select(func.count()).select_from(model)
    if exclude_archived and hasattr(model, "archived_at"):
        query = query.where(model.archived_at.is_(None))
    return db.scalar(query) or 0


def _fetch_active_campaigns(db: Session, *, limit: int = 10) -> list[MarketingCampaignSummary]:
    rows = db.scalars(
        select(MarketingCampaign)
        .where(
            MarketingCampaign.archived_at.is_(None),
            MarketingCampaign.status.in_(["active", "scheduled", "approved"]),
        )
        .order_by(MarketingCampaign.updated_at.desc())
        .limit(limit)
    ).all()
    return [_to_summary(row) for row in rows]


def _fetch_alerts(db: Session, *, limit: int = 10) -> list[MarketingAlertSummary]:
    rows = db.scalars(
        select(MarketingAlert)
        .where(MarketingAlert.is_resolved.is_(False))
        .order_by(MarketingAlert.created_at.desc())
        .limit(limit)
    ).all()
    return [
        MarketingAlertSummary(
            id=row.id,
            title=row.title,
            message=row.message,
            category=row.category.value,
            severity=row.severity.value,
            is_resolved=row.is_resolved,
            created_at=row.created_at,
        )
        for row in rows
    ]


def _fetch_recommendations(db: Session, *, limit: int = 10) -> list[MarketingRecommendationSummary]:
    rows = db.scalars(
        select(MarketingRecommendation)
        .where(MarketingRecommendation.status == "active")
        .order_by(MarketingRecommendation.created_at.desc())
        .limit(limit)
    ).all()
    return [
        MarketingRecommendationSummary(
            id=row.id,
            title=row.title,
            description=row.description,
            recommendation_type=row.recommendation_type,
            rationale=row.rationale,
            confidence_level=row.confidence_level,
            status=row.status,
            created_at=row.created_at,
        )
        for row in rows
    ]


def _fetch_provider_statuses(db: Session) -> list[MarketingProviderStatus]:
    rows = db.scalars(select(MarketingChannel).order_by(MarketingChannel.name)).all()
    return [
        MarketingProviderStatus(
            channel_id=row.id,
            channel_name=row.name,
            category=row.category.value,
            provider=row.provider,
            connection_status=row.connection_status.value,
            last_sync_at=row.last_sync_at,
        )
        for row in rows
    ]


def build_marketing_dashboard(db: Session, user: User) -> MarketingDashboardResponse:
    campaign_count = _count(db, MarketingCampaign)
    audience_count = _count(db, MarketingAudience)
    lead_context_count = db.scalar(select(func.count()).select_from(MarketingLeadContext)) or 0

    widgets = [
        MarketingDashboardWidget(
            key=key,
            state=_widget_state(has_permission=True, count=campaign_count if key == "active_campaigns" else None),
            title_key=f"marketing.dashboard.widgets.{key}",
            data=None,
        )
        for key in DASHBOARD_WIDGET_KEYS
    ]

    return MarketingDashboardResponse(
        widgets=widgets,
        active_campaigns=_fetch_active_campaigns(db),
        alerts=_fetch_alerts(db),
        recommendations=_fetch_recommendations(db),
        provider_statuses=_fetch_provider_statuses(db),
        campaign_count=campaign_count,
        audience_count=audience_count,
        lead_context_count=lead_context_count,
        workspace_overview=get_workspace_overview(db),
    )
