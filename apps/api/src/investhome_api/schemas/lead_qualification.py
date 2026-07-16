"""Lead qualification API schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.lead_qualification import (
    CashOrFinancing,
    FollowUpStatus,
    FollowUpType,
    InvestmentObjective,
    LeadInterestType,
    PurchaseTimeline,
    QualificationStatus,
    RiskTolerance,
)


class LeadQualificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID
    investment_objective: InvestmentObjective | None
    investment_capacity: str | None
    budget_min: Decimal | None
    budget_max: Decimal | None
    preferred_currency: str
    cash_or_financing: CashOrFinancing | None
    expected_purchase_timeline: PurchaseTimeline | None
    preferred_markets: list | None
    preferred_projects: list | None
    preferred_property_types: list | None
    bedrooms_min: int | None
    bedrooms_max: int | None
    bathrooms_min: int | None
    bathrooms_max: int | None
    area_min: Decimal | None
    area_max: Decimal | None
    target_rental_yield: Decimal | None
    expected_roi: Decimal | None
    risk_tolerance: RiskTolerance | None
    decision_makers: str | None
    accredited_investor: bool | None
    required_documents: list | None
    current_concerns: str | None
    sales_notes: str | None
    qualification_status: QualificationStatus
    qualified_at: datetime | None
    qualified_by_id: UUID | None
    created_at: datetime
    updated_at: datetime


class LeadQualificationUpdate(BaseModel):
    investment_objective: InvestmentObjective | None = None
    investment_capacity: str | None = Field(default=None, max_length=100)
    budget_min: Decimal | None = Field(default=None, ge=0)
    budget_max: Decimal | None = Field(default=None, ge=0)
    preferred_currency: str | None = Field(default=None, max_length=3)
    cash_or_financing: CashOrFinancing | None = None
    expected_purchase_timeline: PurchaseTimeline | None = None
    preferred_markets: list | None = None
    preferred_projects: list | None = None
    preferred_property_types: list | None = None
    bedrooms_min: int | None = Field(default=None, ge=0)
    bedrooms_max: int | None = Field(default=None, ge=0)
    bathrooms_min: int | None = Field(default=None, ge=0)
    bathrooms_max: int | None = Field(default=None, ge=0)
    area_min: Decimal | None = Field(default=None, ge=0)
    area_max: Decimal | None = Field(default=None, ge=0)
    target_rental_yield: Decimal | None = None
    expected_roi: Decimal | None = None
    risk_tolerance: RiskTolerance | None = None
    decision_makers: str | None = None
    accredited_investor: bool | None = None
    required_documents: list | None = None
    current_concerns: str | None = None
    sales_notes: str | None = None


class QualificationStatusChange(BaseModel):
    status: QualificationStatus
    notes: str | None = None


class LeadScoreComponentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    component_key: str
    score: int
    weight: Decimal


class LeadScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID
    total_score: int
    computed_at: datetime
    computed_by_id: UUID | None
    is_manual_override: bool
    components: list[LeadScoreComponentResponse] = []


class LeadScoreRecalculate(BaseModel):
    manual_override: int | None = Field(default=None, ge=0, le=100)


class LeadInventoryInterestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID
    inventory_asset_id: UUID
    interest_type: LeadInterestType
    match_reason: str | None
    rejection_reason: str | None
    opportunity_id: UUID | None
    created_at: datetime
    updated_at: datetime


class LeadInventoryInterestCreate(BaseModel):
    inventory_asset_id: UUID
    interest_type: LeadInterestType
    match_reason: str | None = Field(default=None, max_length=255)
    rejection_reason: str | None = Field(default=None, max_length=255)
    opportunity_id: UUID | None = None


class LeadFollowUpResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID
    follow_up_type: FollowUpType
    due_at: datetime
    completed_at: datetime | None
    assigned_user_id: UUID | None
    notes: str | None
    status: FollowUpStatus
    created_at: datetime
    updated_at: datetime


class LeadFollowUpCreate(BaseModel):
    follow_up_type: FollowUpType
    due_at: datetime
    assigned_user_id: UUID | None = None
    notes: str | None = None


class LeadTimelineEntry(BaseModel):
    source: str
    event_type: str
    actor_user_id: str | None
    notes: str | None
    metadata: dict | None
    created_at: str


class LeadTimelineResponse(BaseModel):
    items: list[LeadTimelineEntry]


class LeadDetailSummaryResponse(BaseModel):
    lead_id: UUID
    opportunity_count: int
    reservation_count: int
    inventory_interest_count: int
    follow_up_count: int
    pending_follow_up_count: int
    lead_score: int | None
    qualification_status: QualificationStatus | None


class LeadQualificationExecutiveSummary(BaseModel):
    qualified_count: int
    unqualified_count: int
    awaiting_review_count: int
    avg_lead_score: float
    without_follow_up_count: int
    ready_for_opportunity_count: int
