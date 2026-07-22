"""Marketing budget management Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BudgetFilters(BaseModel):
    year: int | None = None
    quarter: int | None = Field(default=None, ge=1, le=4)
    month: int | None = Field(default=None, ge=1, le=12)
    campaign_id: UUID | None = None
    channel_id: UUID | None = None
    country: str | None = None
    project_id: UUID | None = None
    owner_user_id: UUID | None = None
    team_id: UUID | None = None
    plan_id: UUID | None = None


class BudgetMetricValue(BaseModel):
    key: str
    label: str
    state: str
    value: Decimal | int | float | str | None = None
    unit: str | None = None
    currency: str | None = None
    evidence: dict | None = None


class BudgetHealthCategory(BaseModel):
    key: str
    label: str
    status: str
    summary: str | None = None
    evidence: dict | None = None


class BudgetDashboardResponse(BaseModel):
    kpis: list[BudgetMetricValue]
    health: list[BudgetHealthCategory]
    filters: BudgetFilters
    finance_connected: bool = False
    data_freshness_at: datetime | None = None


class BudgetPlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    plan_type: str = Field(pattern="^(annual|quarterly|monthly)$")
    fiscal_year: int | None = Field(default=None, ge=2000, le=2100)
    quarter: int | None = Field(default=None, ge=1, le=4)
    month: int | None = Field(default=None, ge=1, le=12)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    total_budget: Decimal | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    country: str | None = None
    region: str | None = None
    notes: str | None = None


class BudgetPlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    total_budget: Decimal | None = None
    status: str | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    notes: str | None = None


class BudgetPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    plan_type: str
    fiscal_year: int | None
    quarter: int | None
    month: int | None
    currency: str
    total_budget: Decimal | None
    status: str
    period_start: datetime | None
    period_end: datetime | None
    country: str | None
    region: str | None
    created_at: datetime
    updated_at: datetime


class BudgetAllocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plan_id: UUID
    hierarchy_level: str
    name: str
    campaign_id: UUID | None
    channel_id: UUID | None
    project_id: UUID | None
    country: str | None
    currency: str
    planned_amount: Decimal | None
    allocated_amount: Decimal | None
    committed_amount: Decimal | None
    spent_amount: Decimal | None
    status: str


class BudgetAllocationCreate(BaseModel):
    plan_id: UUID
    hierarchy_level: str
    name: str = Field(min_length=1, max_length=255)
    campaign_id: UUID | None = None
    channel_id: UUID | None = None
    project_id: UUID | None = None
    country: str | None = None
    planned_amount: Decimal | None = None
    allocated_amount: Decimal | None = None


class SpendMonitoringItem(BaseModel):
    allocation_id: UUID | None
    name: str
    hierarchy_level: str
    planned: Decimal | None
    committed: Decimal | None
    actual: Decimal | None
    remaining: Decimal | None
    variance: Decimal | None
    state: str


class SpendMonitoringResponse(BaseModel):
    items: list[SpendMonitoringItem]
    filters: BudgetFilters


class BurnRateResponse(BaseModel):
    monthly_burn: Decimal | None
    quarterly_burn: Decimal | None
    annual_burn: Decimal | None
    projected_exhaustion_date: datetime | None
    state: str
    evidence: dict | None = None


class VarianceItem(BaseModel):
    key: str
    label: str
    planned: Decimal | None
    actual: Decimal | None
    variance: Decimal | None
    variance_percent: float | None
    trend: str | None
    status: str
    state: str


class VarianceResponse(BaseModel):
    items: list[VarianceItem]
    filters: BudgetFilters


class ForecastSlot(BaseModel):
    metric_type: str
    label: str
    forecast_value: Decimal | None
    state: str
    pipeline_connected: bool = False
    evidence: dict | None = None


class ForecastResponse(BaseModel):
    slots: list[ForecastSlot]
    plan_id: UUID | None
    filters: BudgetFilters


class ForecastUpdate(BaseModel):
    metric_type: str
    forecast_value: Decimal | None = None
    notes: str | None = None


class ScenarioPlanCreate(BaseModel):
    plan_id: UUID
    name: str = Field(min_length=1, max_length=255)
    scenario_type: str = Field(pattern="^(base_case|optimistic|conservative|custom)$")
    budget_amount: Decimal | None = None
    spend_target: Decimal | None = None
    lead_target: int | None = None
    sales_target: int | None = None
    revenue_target: Decimal | None = None
    assumptions_json: dict | None = None


class ScenarioPlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    budget_amount: Decimal | None = None
    spend_target: Decimal | None = None
    lead_target: int | None = None
    sales_target: int | None = None
    revenue_target: Decimal | None = None
    assumptions_json: dict | None = None
    is_active: bool | None = None


class ScenarioPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plan_id: UUID
    name: str
    scenario_type: str
    budget_amount: Decimal | None
    spend_target: Decimal | None
    lead_target: int | None
    sales_target: int | None
    revenue_target: Decimal | None
    currency: str
    assumptions_json: dict | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BudgetApprovalCreate(BaseModel):
    entity_type: str = Field(min_length=1, max_length=40)
    entity_id: UUID
    approval_role: str
    sequence_order: int = 0


class BudgetApprovalDecision(BaseModel):
    status: str = Field(pattern="^(approved|rejected|returned)$")
    notes: str | None = None


class BudgetApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_type: str
    entity_id: UUID
    approval_role: str
    status: str
    sequence_order: int
    approver_user_id: UUID | None
    notes: str | None
    decided_at: datetime | None
    created_at: datetime


class BudgetRequestCreate(BaseModel):
    plan_id: UUID
    allocation_id: UUID | None = None
    request_type: str = Field(min_length=1, max_length=40)
    requested_amount: Decimal | None = None
    justification: str | None = None


class BudgetTransferCreate(BaseModel):
    plan_id: UUID
    from_allocation_id: UUID | None = None
    to_allocation_id: UUID | None = None
    amount: Decimal | None = None
    reason: str | None = None


class BudgetHealthResponse(BaseModel):
    overall_status: str
    categories: list[BudgetHealthCategory]


class PaginatedBudgetPlans(BaseModel):
    items: list[BudgetPlanResponse]
    total: int
    page: int
    page_size: int
