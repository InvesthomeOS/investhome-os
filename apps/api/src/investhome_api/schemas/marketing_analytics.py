"""Marketing analytics Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MarketingTimeFilter(BaseModel):
    preset: str = Field(default="last_30_days")
    timezone: str = Field(default="UTC", max_length=64)
    start_at: datetime | None = None
    end_at: datetime | None = None


class MarketingDashboardFilters(BaseModel):
    campaign_id: UUID | None = None
    project_id: UUID | None = None
    property_id: UUID | None = None
    country: str | None = None
    region: str | None = None
    language: str | None = None
    audience_id: UUID | None = None
    segment_id: UUID | None = None
    channel_id: UUID | None = None
    source_id: UUID | None = None
    owner_user_id: UUID | None = None
    team_id: UUID | None = None
    lead_type: str | None = None


class MetricValue(BaseModel):
    key: str
    label: str
    state: str  # ready, unknown, unavailable, not_connected, permission_restricted, empty
    value: int | float | str | None = None
    unit: str | None = None
    previous_value: int | float | None = None
    change_percent: float | None = None
    freshness_at: datetime | None = None
    evidence: dict | None = None


class WidgetConfig(BaseModel):
    key: str
    title: str
    subtitle: str | None = None
    widget_type: str
    state: str
    refresh_interval_seconds: int | None = None
    export_enabled: bool = False
    fullscreen_enabled: bool = True
    collapse_enabled: bool = True
    filters_enabled: bool = True
    data: dict | list | None = None


class FunnelStage(BaseModel):
    key: str
    label: str
    count: int | None = None
    state: str
    conversion_percent: float | None = None
    drop_off_percent: float | None = None


class MarketingFunnelResponse(BaseModel):
    stages: list[FunnelStage]
    time_filter: MarketingTimeFilter
    filters: MarketingDashboardFilters


class HealthCategory(BaseModel):
    key: str
    label: str
    status: str  # healthy, warning, critical, unknown
    summary: str | None = None
    evidence: dict | None = None


class MarketingHealthResponse(BaseModel):
    overall_status: str
    categories: list[HealthCategory]
    computed_at: datetime
    snapshot_id: UUID | None = None


class ExecutiveAlertItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    message: str | None
    category: str
    severity: str
    evidence_json: dict | None = None
    is_resolved: bool
    created_at: datetime


class RecommendationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    recommendation_type: str
    rationale: str | None
    confidence_level: str | None
    status: str
    created_at: datetime


class CampaignSummaryItem(BaseModel):
    id: UUID
    name: str
    status: str
    lead_count: int | None = None


class ChannelSummaryItem(BaseModel):
    id: UUID
    name: str
    category: str
    connection_status: str
    lead_count: int | None = None


class MarketingExecutiveDashboardResponse(BaseModel):
    kpis: list[MetricValue]
    funnel: MarketingFunnelResponse
    health: MarketingHealthResponse
    tracking_health: MarketingHealthResponse
    attribution_health: MarketingHealthResponse
    data_health: MarketingHealthResponse
    alerts: list[ExecutiveAlertItem]
    recommendations: list[RecommendationItem]
    active_campaigns: list[CampaignSummaryItem]
    channel_summaries: list[ChannelSummaryItem]
    widgets: list[WidgetConfig]
    time_filter: MarketingTimeFilter
    filters: MarketingDashboardFilters
    data_freshness_at: datetime | None = None


class MarketingKPIsResponse(BaseModel):
    kpis: list[MetricValue]
    time_filter: MarketingTimeFilter
    filters: MarketingDashboardFilters


class MarketingWidgetsResponse(BaseModel):
    widgets: list[WidgetConfig]
    dashboard_key: str = "executive"


class DashboardLayoutCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    dashboard_key: str = "executive"
    team_id: UUID | None = None
    visibility: str = "private"
    widgets_json: list | None = None
    filters_json: dict | None = None
    is_default: bool = False


class DashboardLayoutUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    visibility: str | None = None
    widgets_json: list | None = None
    filters_json: dict | None = None
    is_default: bool | None = None


class DashboardLayoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    owner_user_id: UUID
    team_id: UUID | None
    visibility: str
    widgets_json: list | None
    filters_json: dict | None
    is_default: bool
    dashboard_key: str
    created_at: datetime
    updated_at: datetime


class DashboardSavedViewCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    dashboard_key: str = "executive"
    filters_json: dict | None = None
    time_filter_json: dict | None = None
    is_default: bool = False
    is_shared: bool = False


class DashboardSavedViewUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    filters_json: dict | None = None
    time_filter_json: dict | None = None
    is_default: bool | None = None
    is_shared: bool | None = None


class DashboardSavedViewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    dashboard_key: str
    filters_json: dict | None
    time_filter_json: dict | None
    is_default: bool
    is_shared: bool
    created_at: datetime
    updated_at: datetime
