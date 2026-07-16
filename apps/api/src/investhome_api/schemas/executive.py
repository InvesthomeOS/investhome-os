"""Executive dashboard API schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ExecutiveFilters(BaseModel):
    date_from: date
    date_to: date
    project_id: UUID | None = None
    assigned_to: str | None = None
    currency: str | None = None


class MetricComparison(BaseModel):
    current: Decimal | int | None
    previous: Decimal | int | None = None
    change: Decimal | int | None = None
    change_available: bool = False


class CurrencyMetricComparison(BaseModel):
    totals: dict[str, Decimal]
    previous_totals: dict[str, Decimal] | None = None
    change_available: bool = False


class SummaryCard(BaseModel):
    key: str
    value: Decimal | int | str | None
    currency_totals: dict[str, Decimal] | None = None
    comparison: MetricComparison | None = None
    currency_comparison: CurrencyMetricComparison | None = None
    link_module: str
    link_query: dict[str, str] | None = None


class ExecutiveSummaryResponse(BaseModel):
    cards: list[SummaryCard]
    period_label_key: str = "executive.filters.last30Days"


class AttentionItem(BaseModel):
    severity: Literal["information", "warning", "critical"]
    title_key: str
    description_key: str
    metadata: dict[str, str | int | float | None] = Field(default_factory=dict)
    entity_type: str
    entity_id: UUID
    related_label: str | None = None
    due_date: date | None = None
    age_days: int | None = None
    link_module: str
    link_query: dict[str, str] | None = None


class ExecutiveAttentionResponse(BaseModel):
    items: list[AttentionItem]


class PipelineStage(BaseModel):
    status: str
    count: int
    estimated_budget_total: Decimal


class LeadsPipelineSummary(BaseModel):
    total: int
    qualified: int
    meetings: int
    proposals: int
    won: int
    lost: int


class ExecutiveLeadsPipelineResponse(BaseModel):
    stages: list[PipelineStage]
    summary: LeadsPipelineSummary
    conversion_rate: Decimal | None
    won_in_period: int
    lost_in_period: int
    total_estimated_budget: Decimal


class InvestorStatusCount(BaseModel):
    status: str
    count: int


class InvestorModelCount(BaseModel):
    model: str
    count: int


class InvestorCountryCount(BaseModel):
    country: str
    count: int


class ExecutiveInvestorOverviewResponse(BaseModel):
    by_status: list[InvestorStatusCount]
    total_investment_capacity: dict[str, Decimal]
    total_committed: dict[str, Decimal]
    total_funded: dict[str, Decimal]
    remaining_committed: dict[str, Decimal]
    upcoming_follow_ups: list[AttentionItem]
    by_investment_model: list[InvestorModelCount]
    by_country: list[InvestorCountryCount]


class ProjectStatusCount(BaseModel):
    status: str
    count: int


class ProjectHealthRow(BaseModel):
    project_id: UUID
    project_name: str
    status: str
    units: int | None
    completion_target: date | None
    development_cost: Decimal | None
    current_value: Decimal | None
    equity_required: Decimal | None
    equity_raised: Decimal | None
    funding_gap: Decimal | None
    budget_variance: Decimal | None
    health_status: Literal["on_track", "attention", "at_risk"]


class ExecutiveProjectPortfolioResponse(BaseModel):
    by_status: list[ProjectStatusCount]
    total_units: int
    units_under_development: int
    total_development_cost: Decimal
    current_portfolio_value: Decimal
    projected_sale_value: Decimal
    total_equity_required: Decimal
    total_equity_raised: Decimal
    total_projected_profit: Decimal
    projects: list[ProjectHealthRow]


class AccountCashRow(BaseModel):
    account_id: UUID
    account_name: str
    currency: str
    current_balance: Decimal | None
    available_balance: Decimal | None


class CashFlowPoint(BaseModel):
    period_start: date
    period_end: date
    inflows: dict[str, Decimal]
    outflows: dict[str, Decimal]
    net: dict[str, Decimal]


class ProjectFundingGap(BaseModel):
    project_id: UUID
    project_name: str
    currency: str
    funding_gap: Decimal


class RecentTransactionRow(BaseModel):
    transaction_id: UUID
    transaction_date: date
    description: str | None
    amount: Decimal
    currency: str
    transaction_type: str
    status: str
    link_module: str = "finance"
    link_query: dict[str, str] | None = None


class ExecutiveFinancialOverviewResponse(BaseModel):
    cash_by_account: list[AccountCashRow]
    available_cash: dict[str, Decimal]
    income_in_period: dict[str, Decimal]
    expenses_in_period: dict[str, Decimal]
    investor_inflows: dict[str, Decimal]
    loan_draws: dict[str, Decimal]
    loan_payments: dict[str, Decimal]
    upcoming_payments: dict[str, Decimal]
    overdue_payments: dict[str, Decimal]
    total_project_budget: dict[str, Decimal]
    total_paid: dict[str, Decimal]
    funding_gap_by_project: list[ProjectFundingGap]
    cash_flow_trend: list[CashFlowPoint]
    recent_transactions: list[RecentTransactionRow] = Field(default_factory=list)


class DeadlineItem(BaseModel):
    deadline_type: str
    title: str
    related_label: str | None
    due_date: date
    window: Literal["overdue", "next_7_days", "next_30_days", "later"]
    entity_type: str
    entity_id: UUID
    link_module: str
    link_query: dict[str, str] | None = None
    metadata: dict[str, str | int | float | None] = Field(default_factory=dict)


class ExecutiveDeadlinesResponse(BaseModel):
    items: list[DeadlineItem]


class ActivityItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    action: str
    entity_type: str
    entity_id: UUID
    description_key: str
    metadata: dict[str, object] | None = None
    actor: str | None
    actor_user_id: UUID | None = None
    source: str | None = None
    entity_label: str | None = None
    link_module: str | None = None
    is_demo: bool
    created_at: datetime


class ExecutiveActivityResponse(BaseModel):
    items: list[ActivityItem]


class ApprovalItem(BaseModel):
    approval_type: str
    title_key: str
    entity_type: str
    entity_id: UUID
    related_label: str | None = None
    submitted_at: datetime | None = None
    age_days: int | None = None
    link_module: str
    link_query: dict[str, str] | None = None
    metadata: dict[str, str | int | float | None] = Field(default_factory=dict)


class ExecutiveApprovalsResponse(BaseModel):
    items: list[ApprovalItem]
    total_pending: int


class DelayedProjectRow(BaseModel):
    project_id: UUID
    project_name: str
    completion_target: date | None
    health_status: Literal["on_track", "attention", "at_risk"]
    days_overdue: int | None = None
    link_module: str = "projects"
    link_query: dict[str, str] | None = None


class ExecutiveConstructionSnapshotResponse(BaseModel):
    limited_data: bool = True
    delayed_projects: list[DelayedProjectRow]
    upcoming_inspections_available: bool = False
    open_rfis_available: bool = False
    open_punch_items_available: bool = False
    drawing_proposals_pending: int = 0


class AiInsightItem(BaseModel):
    kind: Literal["priority", "risk", "opportunity"]
    title_key: str
    description_key: str
    metadata: dict[str, str | int | float | None] = Field(default_factory=dict)
    link_module: str
    link_query: dict[str, str] | None = None
    severity: Literal["information", "warning", "critical"] | None = None


class ExecutiveAiInsightsResponse(BaseModel):
    priorities: list[AiInsightItem]
    risks: list[AiInsightItem]
    opportunities: list[AiInsightItem]
    generated_at: datetime
    ai_level: str = "L2"
