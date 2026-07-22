"""Marketing campaign management Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CampaignBriefBase(BaseModel):
    executive_summary: str | None = None
    objectives: str | None = None
    messaging: str | None = None
    strategies: str | None = None
    risks: str | None = None
    competitive_context: str | None = None
    success_criteria: str | None = None


class CampaignBriefUpdate(CampaignBriefBase):
    pass


class CampaignBriefResponse(CampaignBriefBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    created_at: datetime
    updated_at: datetime


class CampaignMilestoneCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    milestone_type: str = "other"
    status: str = "not_started"
    due_date: datetime | None = None
    depends_on_ids: list[str] | None = None
    notes: str | None = None
    sort_order: int = 0


class CampaignMilestoneUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    milestone_type: str | None = None
    status: str | None = None
    due_date: datetime | None = None
    depends_on_ids: list[str] | None = None
    notes: str | None = None
    sort_order: int | None = None


class CampaignMilestoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    name: str
    milestone_type: str
    status: str
    due_date: datetime | None
    completed_at: datetime | None
    depends_on_ids: list | None
    notes: str | None
    sort_order: int
    created_at: datetime
    updated_at: datetime


class CampaignChannelAssignmentCreate(BaseModel):
    channel_id: UUID
    provider: str | None = None
    budget_amount: Decimal | None = None
    budget_currency: str | None = Field(default=None, max_length=3)
    schedule_json: dict | None = None
    tracking_json: dict | None = None


class CampaignChannelAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    channel_id: UUID
    provider: str | None
    budget_amount: Decimal | None
    budget_currency: str | None
    schedule_json: dict | None
    tracking_json: dict | None
    status: str
    created_at: datetime
    updated_at: datetime


class CampaignBudgetAllocationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    channel_id: UUID | None = None
    budget_id: UUID | None = None
    currency: str = "USD"
    planned_amount: Decimal | None = None
    committed_amount: Decimal | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    notes: str | None = None


class CampaignBudgetAllocationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    planned_amount: Decimal | None = None
    committed_amount: Decimal | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    notes: str | None = None


class CampaignSpendAdjustment(BaseModel):
    amount: Decimal
    reason: str = Field(min_length=1, max_length=500)
    allocation_id: UUID | None = None


class CampaignBudgetAllocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    budget_id: UUID | None
    channel_id: UUID | None
    name: str
    currency: str
    planned_amount: Decimal | None
    committed_amount: Decimal | None
    spent_amount: Decimal | None
    period_start: datetime | None
    period_end: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class CampaignTrackingUpdate(BaseModel):
    utm_source: str | None = Field(default=None, max_length=120)
    utm_medium: str | None = Field(default=None, max_length=120)
    utm_campaign: str | None = Field(default=None, max_length=120)
    utm_term: str | None = Field(default=None, max_length=120)
    utm_content: str | None = Field(default=None, max_length=120)
    tracking_code: str | None = Field(default=None, max_length=120)
    landing_page_url: str | None = Field(default=None, max_length=512)

    @field_validator("utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", mode="before")
    @classmethod
    def normalize_utm(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip().lower().replace(" ", "_")
        return normalized or None


class CampaignTrackingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    utm_source: str | None
    utm_medium: str | None
    utm_campaign: str | None
    utm_term: str | None
    utm_content: str | None
    tracking_code: str | None
    landing_page_url: str | None
    readiness_status: str
    validation_errors: list | None
    created_at: datetime
    updated_at: datetime


class CampaignTargetCreate(BaseModel):
    metric_key: str = Field(min_length=1, max_length=80)
    metric_label: str | None = Field(default=None, max_length=255)
    target_value: Decimal | None = None
    unit: str | None = Field(default=None, max_length=40)
    period: str | None = Field(default=None, max_length=40)


class CampaignTargetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    metric_key: str
    metric_label: str | None
    target_value: Decimal | None
    unit: str | None
    period: str | None
    created_at: datetime
    updated_at: datetime


class CampaignTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    campaign_type: str | None = None
    objective: str | None = None
    template_json: dict | None = None


class CampaignTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    campaign_type: str | None
    objective: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CampaignSavedViewCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    filters_json: dict | None = None
    is_default: bool = False
    is_shared: bool = False


class CampaignSavedViewUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    filters_json: dict | None = None
    is_default: bool | None = None
    is_shared: bool | None = None


class CampaignSavedViewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    filters_json: dict | None
    is_default: bool
    is_shared: bool
    created_at: datetime
    updated_at: datetime


class CampaignSummaryStats(BaseModel):
    total: int
    draft: int
    planning: int
    pending_approval: int
    approved: int
    scheduled: int
    active: int
    paused: int
    completed: int
    cancelled: int
    archived: int


class CampaignListFilters(BaseModel):
    status: str | None = None
    campaign_type: str | None = None
    objective: str | None = None
    owner_user_id: UUID | None = None
    team_id: UUID | None = None
    search: str | None = None
    tags: list[str] | None = None
    include_archived: bool = False
    missing_owner: bool = False
    missing_budget: bool = False
    missing_tracking: bool = False
    page: int = 1
    page_size: int = 25
    sort_by: str = "updated_at"
    sort_dir: str = "desc"


class CampaignReadinessCheck(BaseModel):
    key: str
    label_key: str
    state: str  # ready, warning, blocked
    message: str | None = None


class CampaignReadinessResponse(BaseModel):
    overall_state: str  # ready, warning, blocked
    checks: list[CampaignReadinessCheck]
    can_activate: bool
    blockers: list[str]


class CampaignOverviewResponse(BaseModel):
    campaign_id: UUID
    readiness: CampaignReadinessResponse
    budget_summary: dict
    leads_summary: dict
    conversions_summary: dict
    spend_summary: dict
    approval_status: str | None
    notes: str | None = None
    target_project_id: UUID | None = None
    lead_source_id: UUID | None = None
    primary_channel: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    remaining_budget: Decimal | None = None


class CampaignApprovalAction(BaseModel):
    notes: str | None = None


class CampaignArchiveRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class CampaignDeleteRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class CampaignDuplicateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    include_budget: bool = False
    include_tracking: bool = True


class CampaignBulkActionRequest(BaseModel):
    campaign_ids: list[UUID] = Field(min_length=1)
    action: str  # archive, activate, pause, submit_approval


class CampaignBulkActionResult(BaseModel):
    eligible_count: int
    ineligible_count: int
    eligible_ids: list[UUID]
    ineligible: list[dict]
    results: list[dict] | None = None


class CampaignStatusTransitionRequest(BaseModel):
    target_status: str


class CampaignStatusTransitionResponse(BaseModel):
    valid: bool
    current_status: str
    target_status: str
    allowed_transitions: list[str]
    message: str | None = None


class CampaignLeadContextResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID | None
    contact_id: UUID | None
    company_id: UUID | None
    campaign_id: UUID | None
    source_id: UUID | None
    channel_id: UUID | None
    utm_data_json: dict | None
    attribution_json: dict | None
    created_at: datetime


class CampaignAnalyticsShell(BaseModel):
    state: str  # no_data, not_connected, permission_restricted, ready
    message_key: str
    metrics: dict | None = None


class CampaignAttributionShell(BaseModel):
    state: str
    message_key: str
    channels: list[dict] | None = None
