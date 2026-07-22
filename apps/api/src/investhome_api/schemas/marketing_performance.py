"""Schemas for campaign performance and lead attribution — Sprint 8A3."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PerformanceMetricValue(BaseModel):
    value: str | int | float | None = None
    state: str = "ready"
    reason: str | None = None


class PerformanceFilters(BaseModel):
    date_from: datetime | None = None
    date_to: datetime | None = None
    campaign_id: UUID | None = None
    project_id: UUID | None = None
    campaign_type: str | None = None
    owner_user_id: UUID | None = None
    status: str | None = None
    company_id: UUID | None = None


class CampaignPerformanceMetrics(BaseModel):
    campaign_id: UUID
    campaign_name: str
    campaign_type: str | None = None
    primary_channel: str | None = None
    status: str
    target_project_id: UUID | None = None
    owner_user_id: UUID | None = None
    planned_budget: PerformanceMetricValue
    actual_spend: PerformanceMetricValue
    total_leads: PerformanceMetricValue
    new_leads: PerformanceMetricValue
    qualified_leads: PerformanceMetricValue
    converted_leads: PerformanceMetricValue
    open_opportunities: PerformanceMetricValue
    won_opportunities: PerformanceMetricValue
    lost_opportunities: PerformanceMetricValue
    conversion_rate: PerformanceMetricValue
    cpl: PerformanceMetricValue
    cpql: PerformanceMetricValue
    cpc: PerformanceMetricValue
    estimated_revenue: PerformanceMetricValue
    confirmed_revenue: PerformanceMetricValue
    estimated_roi: PerformanceMetricValue
    confirmed_roi: PerformanceMetricValue


class CampaignPerformanceListResponse(BaseModel):
    items: list[CampaignPerformanceMetrics]
    page: int
    page_size: int
    total: int


class CampaignLeadBreakdownItem(BaseModel):
    lead_id: UUID
    full_name: str
    email: str | None = None
    status: str
    attribution_status: str
    attribution_source: str | None = None
    utm_source: str | None = None
    first_touch_at: datetime | None = None
    converted_at: datetime | None = None
    created_at: datetime


class CampaignLeadBreakdownResponse(BaseModel):
    items: list[CampaignLeadBreakdownItem]
    page: int
    page_size: int
    total: int
    status_breakdown: dict[str, int] = Field(default_factory=dict)


class ChannelPerformanceItem(BaseModel):
    channel: str
    campaign_count: int
    spend: PerformanceMetricValue
    leads: PerformanceMetricValue
    qualified_leads: PerformanceMetricValue
    conversions: PerformanceMetricValue
    cpl: PerformanceMetricValue
    conversion_rate: PerformanceMetricValue


class ChannelPerformanceResponse(BaseModel):
    items: list[ChannelPerformanceItem]


class ProjectPerformanceItem(BaseModel):
    project_id: UUID | None = None
    project_name: str
    campaign_count: int
    spend: PerformanceMetricValue
    leads: PerformanceMetricValue
    qualified_leads: PerformanceMetricValue
    conversions: PerformanceMetricValue
    cpl: PerformanceMetricValue
    conversion_rate: PerformanceMetricValue


class ProjectPerformanceResponse(BaseModel):
    items: list[ProjectPerformanceItem]


class MarketingPerformanceOverview(BaseModel):
    total_campaigns: PerformanceMetricValue
    active_campaigns: PerformanceMetricValue
    total_budget: PerformanceMetricValue
    total_spend: PerformanceMetricValue
    total_leads: PerformanceMetricValue
    qualified_leads: PerformanceMetricValue
    converted_leads: PerformanceMetricValue
    avg_cpl: PerformanceMetricValue
    avg_conversion_rate: PerformanceMetricValue
    campaigns_requiring_attention: PerformanceMetricValue
    currency: str | None = None


class LeadAttributionCreate(BaseModel):
    lead_id: UUID
    campaign_id: UUID | None = None
    company_id: UUID | None = None
    attribution_source: str = "manual"
    utm_source: str | None = Field(default=None, max_length=255)
    utm_medium: str | None = Field(default=None, max_length=255)
    utm_campaign: str | None = Field(default=None, max_length=255)
    utm_term: str | None = Field(default=None, max_length=255)
    utm_content: str | None = Field(default=None, max_length=255)
    first_touch_at: datetime | None = None
    converted_at: datetime | None = None
    attribution_reason: str | None = None


class LeadAttributionUpdate(BaseModel):
    campaign_id: UUID | None = None
    company_id: UUID | None = None
    attribution_source: str | None = None
    utm_source: str | None = Field(default=None, max_length=255)
    utm_medium: str | None = Field(default=None, max_length=255)
    utm_campaign: str | None = Field(default=None, max_length=255)
    utm_term: str | None = Field(default=None, max_length=255)
    utm_content: str | None = Field(default=None, max_length=255)
    first_touch_at: datetime | None = None
    converted_at: datetime | None = None
    attribution_reason: str | None = None


class LeadAttributionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID
    campaign_id: UUID | None = None
    company_id: UUID | None = None
    attribution_source: str
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_term: str | None = None
    utm_content: str | None = None
    first_touch_at: datetime | None = None
    converted_at: datetime | None = None
    attribution_reason: str | None = None
    campaign_name: str | None = None
    campaign_type: str | None = None
    project_id: UUID | None = None
    lead_full_name: str | None = None
    lead_status: str | None = None
    attribution_status: str | None = None
    created_at: datetime
    updated_at: datetime


class LeadAttributionListResponse(BaseModel):
    items: list[LeadAttributionResponse]
    page: int
    page_size: int
    total: int


class LeadAttributionFields(BaseModel):
    """Optional attribution fields on lead create/update."""

    campaign_id: UUID | None = None
    company_id: UUID | None = None
    attribution_source: str | None = None
    utm_source: str | None = Field(default=None, max_length=255)
    utm_medium: str | None = Field(default=None, max_length=255)
    utm_campaign: str | None = Field(default=None, max_length=255)
    utm_term: str | None = Field(default=None, max_length=255)
    utm_content: str | None = Field(default=None, max_length=255)


class CampaignPerformanceDetail(BaseModel):
    metrics: CampaignPerformanceMetrics
    lead_trend: list[dict[str, int | str]]
    status_breakdown: dict[str, int]
    spend_vs_budget: dict[str, str | None]
    top_sources: list[dict[str, str | int]]
    utm_breakdown: list[dict[str, str | int]]
    recent_leads: list[CampaignLeadBreakdownItem]
