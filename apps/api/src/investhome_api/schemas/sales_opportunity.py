"""Pydantic schemas for sales opportunities."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.sales import (
    OpportunityLossReason,
    OpportunityNextAction,
    OpportunityPartyType,
    OpportunityPriority,
    OpportunityStage,
)


class SalesOpportunityCreate(BaseModel):
    party_id: UUID
    party_type: OpportunityPartyType
    lead_id: UUID | None = None
    crm_contact_id: UUID | None = None
    display_id: str | None = Field(default=None, max_length=50)
    assigned_sales_user_id: UUID | None = None
    stage: OpportunityStage = OpportunityStage.NEW
    probability: int = Field(default=0, ge=0, le=100)
    expected_close_date: date | None = None
    expected_revenue: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    priority: OpportunityPriority = OpportunityPriority.MEDIUM
    source: str | None = Field(default=None, max_length=100)
    current_risks: list | dict | None = None
    next_action: OpportunityNextAction | None = None
    next_action_date: date | None = None
    last_contact_at: datetime | None = None
    notes: str | None = None
    reservation_id: UUID | None = None
    is_demo: bool = False


class SalesOpportunityUpdate(BaseModel):
    display_id: str | None = Field(default=None, max_length=50)
    lead_id: UUID | None = None
    party_id: UUID | None = None
    party_type: OpportunityPartyType | None = None
    assigned_sales_user_id: UUID | None = None
    probability: int | None = Field(default=None, ge=0, le=100)
    expected_close_date: date | None = None
    expected_revenue: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    priority: OpportunityPriority | None = None
    source: str | None = Field(default=None, max_length=100)
    current_risks: list | dict | None = None
    next_action: OpportunityNextAction | None = None
    next_action_date: date | None = None
    last_contact_at: datetime | None = None
    notes: str | None = None
    loss_reason: OpportunityLossReason | None = None
    loss_notes: str | None = None
    dormant_review_date: date | None = None
    cancelled_reason: str | None = Field(default=None, max_length=255)
    reservation_id: UUID | None = None


class SalesOpportunityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    opportunity_code: str
    display_id: str | None
    lead_id: UUID | None
    crm_contact_id: UUID | None = None
    party_id: UUID
    party_type: OpportunityPartyType
    party_label: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    contact_owner_name: str | None = None
    contact_last_activity_at: datetime | None = None
    contact_next_follow_up_at: datetime | None = None
    assigned_sales_user_id: UUID | None
    stage: OpportunityStage
    probability: int
    expected_close_date: date | None
    expected_revenue: Decimal | None
    currency: str
    priority: OpportunityPriority
    source: str | None
    current_risks: list | dict | None
    next_action: OpportunityNextAction | None
    next_action_date: date | None
    last_contact_at: datetime | None
    notes: str | None
    loss_reason: OpportunityLossReason | None
    loss_notes: str | None
    dormant_review_date: date | None
    cancelled_reason: str | None
    reservation_id: UUID | None
    is_demo: bool
    archived_at: datetime | None
    created_by_id: UUID | None
    created_at: datetime
    updated_at: datetime


class SalesOpportunityListResponse(BaseModel):
    items: list[SalesOpportunityResponse]
    total: int
    offset: int
    limit: int


class StageChangeRequest(BaseModel):
    stage: OpportunityStage
    notes: str | None = None
    loss_reason: OpportunityLossReason | None = None
    loss_notes: str | None = None
    dormant_review_date: date | None = None
    cancelled_reason: str | None = Field(default=None, max_length=255)


class ProbabilityChangeRequest(BaseModel):
    probability: int = Field(ge=0, le=100)
    reason: str | None = None


class NextActionRequest(BaseModel):
    next_action: OpportunityNextAction
    next_action_date: date


class LinkInventoryRequest(BaseModel):
    inventory_asset_id: UUID
    match_reason: str | None = Field(default=None, max_length=255)
    is_favorite: bool = False
    notes: str | None = None


class LinkProjectRequest(BaseModel):
    project_id: UUID


class OpportunityInventoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    opportunity_id: UUID
    inventory_asset_id: UUID
    match_reason: str | None
    rejection_reason: str | None
    is_favorite: bool
    shortlisted_at: datetime | None
    notes: str | None
    created_at: datetime


class OpportunityProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    opportunity_id: UUID
    project_id: UUID
    created_at: datetime


class OpportunityTimelineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    opportunity_id: UUID
    event_type: str
    from_stage: str | None
    to_stage: str | None
    from_probability: int | None
    to_probability: int | None
    actor_user_id: UUID | None
    notes: str | None
    metadata_json: dict | None
    created_at: datetime


class PipelineStageGroup(BaseModel):
    stage: str
    count: int
    opportunities: list[SalesOpportunityResponse]


class PipelineSummaryResponse(BaseModel):
    stages: dict[str, int]
    total: int
    groups: list[PipelineStageGroup] | None = None


class DashboardMetricsResponse(BaseModel):
    open_opportunities: int
    pipeline_value: str
    won_count: int
    lost_count: int
    no_follow_up: int
    dormant_count: int
    expected_closings_30d: int


class ExecutiveSalesSummaryResponse(BaseModel):
    pipeline_value: str
    weighted_pipeline_value: str
    high_risk_count: int
    no_follow_up_count: int
    dormant_count: int
    expected_closings_30d: int
