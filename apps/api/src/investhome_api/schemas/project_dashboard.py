"""Projects portfolio dashboard response schemas (Sprint 10A2)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MetricValue(BaseModel):
    """Typed metric that distinguishes zero from unavailable."""

    value: Decimal | int | float | None = None
    available: bool = True
    reason: str | None = None


def metric(value: Decimal | int | float | None) -> MetricValue:
    return MetricValue(value=value, available=True)


def unavailable(reason: str) -> MetricValue:
    return MetricValue(value=None, available=False, reason=reason)


class ProjectRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertCategory(str, Enum):
    BUDGET = "budget"
    SCHEDULE = "schedule"
    DOCUMENT = "document"
    CONSTRUCTION = "construction"
    DATA_QUALITY = "data_quality"
    SALES = "sales"
    LEASING = "leasing"
    TEAM = "team"


class MilestoneType(str, Enum):
    CLOSING = "closing"
    DELIVERY = "delivery"
    START = "start"
    COMPLETION = "completion"
    ACQUISITION = "acquisition"


class DashboardFiltersApplied(BaseModel):
    status: str | None = None
    project_type: str | None = None
    priority: str | None = None
    development_stage: str | None = None
    project_manager_user_id: UUID | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    completion_year: int | None = None
    include_archived: bool = False
    search: str | None = None


class DashboardMeta(BaseModel):
    generated_at: datetime
    currency_mode: str = "project_native"
    financial_access: bool
    applied_filters: DashboardFiltersApplied
    data_completeness: dict[str, str] = Field(default_factory=dict)
    partial_data_warnings: list[str] = Field(default_factory=list)


class PortfolioSummary(BaseModel):
    total_projects: int
    active_projects: int
    planning_projects: int
    under_construction_projects: int
    completed_projects: int
    on_hold_projects: int
    cancelled_projects: int
    archived_projects: int
    total_units: int
    residential_units: int
    commercial_units: int
    available_units: MetricValue
    reserved_units: MetricValue
    under_contract_units: MetricValue
    sold_units: MetricValue
    occupied_units: MetricValue
    vacant_units: MetricValue
    portfolio_value: MetricValue
    total_development_budget: MetricValue
    construction_budget: MetricValue
    budget_spent: MetricValue
    budget_remaining: MetricValue
    budget_utilization_percentage: MetricValue
    average_project_completion: MetricValue
    projects_delayed: int
    projects_at_risk: int
    status_distribution: dict[str, int] = Field(default_factory=dict)
    stage_distribution: dict[str, int] = Field(default_factory=dict)
    priority_distribution: dict[str, int] = Field(default_factory=dict)


class FinancialSummary(BaseModel):
    expected_revenue: MetricValue
    expected_profit: MetricValue
    current_portfolio_value: MetricValue
    total_development_cost: MetricValue
    construction_budget: MetricValue
    soft_cost_budget: MetricValue
    land_cost: MetricValue
    equity_raised: MetricValue
    equity_required: MetricValue
    debt_outstanding: MetricValue
    budget_spent: MetricValue
    budget_remaining: MetricValue
    budget_utilization_percentage: MetricValue
    realized_revenue: MetricValue
    remaining_revenue: MetricValue
    realized_profit: MetricValue
    roi: MetricValue
    irr: MetricValue
    equity_multiple: MetricValue
    average_profit_margin: MetricValue
    # Executive finance rollups (Sprint 10A4C) — additive, never fabricate zeros
    funding_gap: MetricValue = Field(
        default_factory=lambda: MetricValue(value=None, available=False, reason="Not computed")
    )
    cash_position: MetricValue = Field(
        default_factory=lambda: MetricValue(value=None, available=False, reason="Not computed")
    )
    forecast_cost: MetricValue = Field(
        default_factory=lambda: MetricValue(value=None, available=False, reason="Not computed")
    )
    need_30_days: MetricValue = Field(
        default_factory=lambda: MetricValue(value=None, available=False, reason="Not computed")
    )
    need_60_days: MetricValue = Field(
        default_factory=lambda: MetricValue(value=None, available=False, reason="Not computed")
    )
    need_90_days: MetricValue = Field(
        default_factory=lambda: MetricValue(value=None, available=False, reason="Not computed")
    )
    projects_requiring_attention: list[dict[str, Any]] = Field(default_factory=list)
    upcoming_large_cash_events: list[dict[str, Any]] = Field(default_factory=list)
    ai_finance_summary: dict[str, Any] | None = None


class ConstructionProjectRow(BaseModel):
    project_id: UUID
    project_name: str
    status: str
    development_stage: str | None
    completion_percentage: Decimal | None
    estimated_start_date: date | None
    actual_start_date: date | None
    estimated_completion_date: date | None
    actual_completion_date: date | None
    days_remaining: int | None
    days_delayed: int | None
    is_delayed: bool
    risk: ProjectRiskLevel
    next_milestone: str | None = None


class ConstructionSummary(BaseModel):
    average_completion_percentage: MetricValue
    projects_on_schedule: int
    projects_delayed: int
    projects_without_schedule: int
    projects_without_progress: int
    average_days_remaining: MetricValue
    completion_distribution: dict[str, int] = Field(default_factory=dict)
    stage_distribution: dict[str, int] = Field(default_factory=dict)
    projects: list[ConstructionProjectRow] = Field(default_factory=list)


class SalesSummary(BaseModel):
    available_units: MetricValue
    reserved_units: MetricValue
    under_contract_units: MetricValue
    sold_units: MetricValue
    cancelled_units: MetricValue
    sales_rate: MetricValue
    gross_sales_volume: MetricValue
    by_status: dict[str, int] = Field(default_factory=dict)


class LeasingSummary(BaseModel):
    occupied_units: MetricValue
    vacant_units: MetricValue
    occupancy_rate: MetricValue
    leases_expiring_30_days: MetricValue
    leases_expiring_60_days: MetricValue
    leases_expiring_90_days: MetricValue
    monthly_rental_income: MetricValue
    by_status: dict[str, int] = Field(default_factory=dict)


class ProjectMilestoneItem(BaseModel):
    id: str
    project_id: UUID
    project_name: str
    title: str
    type: MilestoneType
    description: str | None = None
    date: date
    status: str
    priority: str
    days_remaining: int
    is_overdue: bool
    owner: str | None = None
    source: str = "derived_schedule"
    action_url: str


class ProjectAlertItem(BaseModel):
    id: str
    project_id: UUID
    project_name: str
    severity: AlertSeverity
    category: AlertCategory
    title: str
    message: str
    action_required: bool = True
    recommended_action: str | None = None
    created_at: datetime
    due_date: date | None = None
    days_remaining: int | None = None
    source: str
    action_url: str


class ProjectActivityItem(BaseModel):
    id: UUID
    project_id: UUID | None
    project_name: str | None
    type: str
    title: str
    description: str | None = None
    actor: str | None = None
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    action_url: str | None = None


class ProjectDashboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    portfolio: PortfolioSummary
    financials: FinancialSummary | None
    construction: ConstructionSummary
    sales: SalesSummary
    leasing: LeasingSummary
    milestones: list[ProjectMilestoneItem]
    alerts: list[ProjectAlertItem]
    activity: list[ProjectActivityItem]
    meta: DashboardMeta


class ProjectMilestoneListResponse(BaseModel):
    items: list[ProjectMilestoneItem]
    total: int


class ProjectAlertListResponse(BaseModel):
    items: list[ProjectAlertItem]
    total: int


class ProjectActivityListResponse(BaseModel):
    items: list[ProjectActivityItem]
    total: int
