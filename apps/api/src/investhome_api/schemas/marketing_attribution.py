"""Pydantic schemas for multi-touch attribution."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TouchpointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    contact_id: UUID | None = None
    anonymous_visitor_id: str | None = None
    campaign_id: UUID | None = None
    channel_id: UUID | None = None
    source_id: UUID | None = None
    landing_page_id: UUID | None = None
    form_id: UUID | None = None
    conversion_event_id: UUID | None = None
    crm_timeline_event_id: UUID | None = None
    sales_lead_id: UUID | None = None
    opportunity_id: UUID | None = None
    reservation_id: UUID | None = None
    sale_id: UUID | None = None
    tracking_context_id: UUID | None = None
    submission_id: UUID | None = None
    lead_context_id: UUID | None = None
    touch_type: str
    touch_order: int | None = None
    touch_timestamp: datetime
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_term: str | None = None
    utm_content: str | None = None
    click_ids_json: dict | None = None
    device_json: dict | None = None
    country: str | None = None
    verification_status: str
    source_entity_type: str | None = None
    source_entity_id: UUID | None = None
    created_at: datetime


class TouchpointListResponse(BaseModel):
    items: list[TouchpointResponse]
    page: int
    page_size: int
    total: int
    pages: int


class AllocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    journey_id: UUID
    model_id: UUID
    touchpoint_id: UUID
    contribution_pct: float
    confidence: float | None = None
    computed_at: datetime


class JourneyTimelineStep(BaseModel):
    touchpoint_id: UUID
    touch_type: str
    touch_order: int
    touch_timestamp: datetime
    campaign_id: UUID | None = None
    channel_id: UUID | None = None
    source_id: UUID | None = None
    verification_status: str
    contribution_pct: float | None = None


class JourneyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    contact_id: UUID | None = None
    marketing_lead_context_id: UUID | None = None
    touchpoint_ids: list[UUID] = Field(default_factory=list)
    journey_status: str
    conversion_event_id: UUID | None = None
    first_touch_at: datetime | None = None
    last_touch_at: datetime | None = None
    touch_count: int
    computed_at: datetime | None = None
    timeline: list[JourneyTimelineStep] = Field(default_factory=list)
    allocations: list[AllocationResponse] = Field(default_factory=list)


class JourneyListResponse(BaseModel):
    items: list[JourneyResponse]
    page: int
    page_size: int
    total: int
    pages: int


class AttributionModelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    model_type: str
    config_json: dict | None = None
    is_default: bool = False
    description: str | None = None


class AttributionModelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    config_json: dict | None = None
    is_default: bool | None = None
    is_active: bool | None = None
    description: str | None = None


class AttributionModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    model_type: str
    config_json: dict | None = None
    is_default: bool
    is_active: bool
    description: str | None = None
    available: bool = True
    unavailable_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class AttributionRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    priority: int = 0
    is_active: bool = True
    conditions_json: dict | None = None
    allocation_json: dict | None = None
    model_id: UUID | None = None


class AttributionRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    priority: int | None = None
    is_active: bool | None = None
    conditions_json: dict | None = None
    allocation_json: dict | None = None
    model_id: UUID | None = None


class AttributionRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    priority: int
    is_active: bool
    conditions_json: dict | None = None
    allocation_json: dict | None = None
    model_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class AttributionHealthIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    issue_type: str
    severity: str
    journey_id: UUID | None = None
    touchpoint_id: UUID | None = None
    message: str | None = None
    details_json: dict | None = None
    is_resolved: bool
    detected_at: datetime


class AttributionHealthResponse(BaseModel):
    overall_status: str
    healthy_count: int
    warning_count: int
    critical_count: int
    issues: list[AttributionHealthIssueResponse]
    summary: dict[str, int]


class AttributionKPI(BaseModel):
    key: str
    label: str
    value: int | float | None
    state: str = "ready"
    message: str | None = None


class TopAttributionItem(BaseModel):
    id: UUID | None = None
    name: str | None = None
    count: int
    contribution_pct: float | None = None


class AttributionDashboardResponse(BaseModel):
    kpis: list[AttributionKPI]
    top_campaigns: list[TopAttributionItem]
    top_channels: list[TopAttributionItem]
    top_sources: list[TopAttributionItem]
    default_model_id: UUID | None = None
    journey_summary: dict[str, int]
    has_data: bool
    message: str | None = None


class ComputeAttributionRequest(BaseModel):
    model_id: UUID | None = None
    journey_ids: list[UUID] | None = None
    rebuild_journeys: bool = False
    rebuild_touchpoints: bool = False


class ComputeAttributionResponse(BaseModel):
    journeys_processed: int
    allocations_created: int
    health_issues_detected: int
    model_id: UUID | None = None
    model_type: str | None = None
    unavailable: bool = False
    message: str | None = None


class AttributionConversionResponse(BaseModel):
    conversion_event_id: UUID
    event_type: str
    lead_context_id: UUID | None = None
    journey_id: UUID | None = None
    journey_status: str | None = None
    attributed: bool
    attribution_state: str
    created_at: datetime


class AttributionConversionListResponse(BaseModel):
    items: list[AttributionConversionResponse]
    page: int
    page_size: int
    total: int
    pages: int
