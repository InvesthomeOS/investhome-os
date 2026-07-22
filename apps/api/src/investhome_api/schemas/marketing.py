"""Marketing workspace Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UtmParams(BaseModel):
    """Reusable UTM parameters with validation and normalization."""

    utm_source: str | None = Field(default=None, max_length=120)
    utm_medium: str | None = Field(default=None, max_length=120)
    utm_campaign: str | None = Field(default=None, max_length=120)
    utm_term: str | None = Field(default=None, max_length=120)
    utm_content: str | None = Field(default=None, max_length=120)

    @field_validator("utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", mode="before")
    @classmethod
    def normalize_utm(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip().lower().replace(" ", "_")
        return normalized or None


class MarketingCampaignBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=80)
    description: str | None = None
    objective: str = "awareness"
    campaign_type: str = "other"
    status: str = "draft"
    priority: str = "normal"
    owner_user_id: UUID | None = None
    team_id: UUID | None = None
    company_id: UUID | None = None
    target_project_id: UUID | None = None
    lead_source_id: UUID | None = None
    primary_channel: str | None = None
    project_ids: list[str] | None = None
    property_ids: list[str] | None = None
    audience_ids: list[str] | None = None
    segment_ids: list[str] | None = None
    channel_ids: list[str] | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    timezone: str | None = Field(default=None, max_length=64)
    budget_amount: Decimal | None = None
    budget_currency: str | None = Field(default=None, max_length=3)
    targets_json: dict | None = None
    tags: list[str] | None = None
    notes: str | None = None
    metadata_json: dict | None = None


class MarketingCampaignCreate(MarketingCampaignBase):
    pass


class MarketingCampaignUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=80)
    description: str | None = None
    objective: str | None = None
    campaign_type: str | None = None
    status: str | None = None
    priority: str | None = None
    owner_user_id: UUID | None = None
    team_id: UUID | None = None
    company_id: UUID | None = None
    target_project_id: UUID | None = None
    lead_source_id: UUID | None = None
    primary_channel: str | None = None
    project_ids: list[str] | None = None
    property_ids: list[str] | None = None
    audience_ids: list[str] | None = None
    segment_ids: list[str] | None = None
    channel_ids: list[str] | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    timezone: str | None = None
    budget_amount: Decimal | None = None
    budget_currency: str | None = None
    targets_json: dict | None = None
    tags: list[str] | None = None
    notes: str | None = None
    metadata_json: dict | None = None


class MarketingCampaignSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str | None
    objective: str
    campaign_type: str
    status: str
    priority: str
    owner_user_id: UUID | None
    company_id: UUID | None = None
    target_project_id: UUID | None = None
    lead_source_id: UUID | None = None
    primary_channel: str | None = None
    start_date: datetime | None
    end_date: datetime | None
    budget_amount: Decimal | None
    budget_currency: str | None
    spent_amount: Decimal | None = None
    actual_leads: int | None = None
    tags: list | None
    created_at: datetime
    updated_at: datetime


class MarketingCampaignDetail(MarketingCampaignSummary):
    description: str | None
    team_id: UUID | None
    project_ids: list | None
    property_ids: list | None
    audience_ids: list | None
    segment_ids: list | None
    channel_ids: list | None
    timezone: str | None
    targets_json: dict | None
    notes: str | None = None
    metadata_json: dict | None = None
    archived_at: datetime | None
    remaining_budget: Decimal | None = None


class MarketingCampaignListResponse(BaseModel):
    items: list[MarketingCampaignSummary]
    page: int
    page_size: int
    total: int
    pages: int


class MarketingCampaignCreateResponse(BaseModel):
    campaign: MarketingCampaignDetail


class MarketingAudienceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    audience_type: str
    source: str | None = None
    estimated_size: int | None = None
    contact_ids: list[str] | None = None
    company_ids: list[str] | None = None
    segment_rules_json: dict | None = None
    consent_json: dict | None = None
    geo_json: dict | None = None
    channel_ids: list[str] | None = None
    language: str | None = None


class MarketingAudienceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    audience_type: str
    source: str | None
    estimated_size: int | None
    language: str | None
    created_at: datetime
    updated_at: datetime


class MarketingSegmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    segment_type: str
    rules_json: dict | None = None
    refresh_frequency: str | None = None
    visibility: str = "team"


class MarketingSegmentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    segment_type: str
    visibility: str
    estimated_size: int | None
    last_refreshed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MarketingLeadSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    source_type: str
    channel_id: UUID | None = None
    utm_defaults_json: dict | None = None
    tracking_code: str | None = None
    description: str | None = None


class MarketingLeadSourceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    source_type: str
    channel_id: UUID | None
    tracking_code: str | None
    created_at: datetime
    updated_at: datetime


class MarketingLeadContextSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID | None
    contact_id: UUID | None
    company_id: UUID | None
    campaign_id: UUID | None
    source_id: UUID | None
    channel_id: UUID | None
    utm_data_json: dict | None
    created_at: datetime


class MarketingContentAssetSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    content_type: str
    format: str | None
    status: str
    campaign_id: UUID | None
    created_at: datetime


class MarketingEventSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    event_type: str
    campaign_id: UUID | None
    start_at: datetime | None
    end_at: datetime | None
    status: str


class MarketingBudgetSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    campaign_id: UUID | None
    channel_id: UUID | None
    currency: str
    planned_amount: Decimal | None
    committed_amount: Decimal | None
    spent_amount: Decimal | None
    status: str


class MarketingApprovalSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_type: str
    entity_id: UUID
    approval_type: str
    status: str
    created_at: datetime


class MarketingAlertSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    message: str | None
    category: str
    severity: str
    is_resolved: bool
    created_at: datetime


class MarketingRecommendationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    recommendation_type: str
    rationale: str | None
    confidence_level: str | None
    status: str
    created_at: datetime


class MarketingProviderStatus(BaseModel):
    channel_id: UUID
    channel_name: str
    category: str
    provider: str | None
    connection_status: str
    last_sync_at: datetime | None


class MarketingNavItem(BaseModel):
    href: str
    label_key: str
    permission: str | None = None


class MarketingNavGroup(BaseModel):
    key: str
    label_key: str
    items: list[MarketingNavItem]


class MarketingQuickAction(BaseModel):
    key: str
    label_key: str
    href: str
    permission: str


class MarketingDashboardWidget(BaseModel):
    key: str
    state: str  # loading, empty, error, not_connected, permission_restricted, no_data, ready
    title_key: str
    data: dict | list | None = None


class MarketingMetricValue(BaseModel):
    """Honest metric — distinguishes zero from unavailable (Sprint 8A1)."""

    value: Decimal | int | float | None = None
    available: bool = True
    reason: str | None = None


class MarketingWorkspaceOverviewResponse(BaseModel):
    """Lightweight marketing workspace KPIs for Overview / Dashboard."""

    total_campaigns: MarketingMetricValue
    active_campaigns: MarketingMetricValue
    budget: MarketingMetricValue
    spend: MarketingMetricValue
    estimated_leads: MarketingMetricValue
    actual_leads: MarketingMetricValue
    estimated_roi: MarketingMetricValue
    top_performing: MarketingMetricValue
    upcoming: MarketingMetricValue
    currency: str | None = None
    upcoming_campaigns: list[MarketingCampaignSummary] = Field(default_factory=list)
    qualified_leads: MarketingMetricValue | None = None
    converted_leads: MarketingMetricValue | None = None
    avg_cpl: MarketingMetricValue | None = None
    avg_conversion_rate: MarketingMetricValue | None = None
    campaigns_requiring_attention: MarketingMetricValue | None = None


class MarketingDashboardResponse(BaseModel):
    widgets: list[MarketingDashboardWidget]
    active_campaigns: list[MarketingCampaignSummary]
    alerts: list[MarketingAlertSummary]
    recommendations: list[MarketingRecommendationSummary]
    provider_statuses: list[MarketingProviderStatus]
    campaign_count: int
    audience_count: int
    lead_context_count: int
    workspace_overview: MarketingWorkspaceOverviewResponse | None = None


class MarketingNavigationResponse(BaseModel):
    groups: list[MarketingNavGroup]


class MarketingQuickActionsResponse(BaseModel):
    actions: list[MarketingQuickAction]


class MarketingProviderStatusesResponse(BaseModel):
    providers: list[MarketingProviderStatus]
