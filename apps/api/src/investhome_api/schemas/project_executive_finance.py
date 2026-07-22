"""Executive project finance schemas (Sprint 10A4C)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.schemas.project_dashboard import MetricValue


class FinancialHealthStatus(str, Enum):
    HEALTHY = "healthy"
    WATCH = "watch"
    AT_RISK = "at_risk"
    CRITICAL = "critical"
    UNAVAILABLE = "unavailable"


class ExecutiveAlertSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CashFlowHorizonBucket(BaseModel):
    days: int
    outflows: MetricValue
    inflows: MetricValue
    net_need: MetricValue
    item_count: int = 0


class CashFlowUpcomingItem(BaseModel):
    id: str
    kind: str
    direction: str
    label: str
    amount: Decimal
    currency: str = "USD"
    expected_date: date | None = None
    status: str | None = None
    source: str


class ProjectCashFlowSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: UUID
    currency: str = "USD"
    as_of: date
    horizon_30: CashFlowHorizonBucket
    horizon_60: CashFlowHorizonBucket
    horizon_90: CashFlowHorizonBucket
    large_upcoming_payments: list[CashFlowUpcomingItem] = Field(default_factory=list)
    large_upcoming_receipts: list[CashFlowUpcomingItem] = Field(default_factory=list)
    data_completeness: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class ExecutiveFinanceAlert(BaseModel):
    id: str
    code: str
    severity: ExecutiveAlertSeverity
    title: str
    message: str
    recommended_action: str | None = None
    related_metric: str | None = None
    due_date: date | None = None


class ProjectAiFinanceSummaryPayload(BaseModel):
    """AI-ready structure only — no model inference is performed."""

    project_id: UUID
    project_name: str
    health: FinancialHealthStatus
    needs_cash: bool
    is_profitable: bool | None
    is_risky: bool
    missing_info: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    metrics: dict[str, MetricValue] = Field(default_factory=dict)
    generated_at: datetime


class ProjectExecutiveFinanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: UUID
    project_name: str
    currency: str = "USD"
    as_of: date
    health: FinancialHealthStatus
    health_reasons: list[str] = Field(default_factory=list)

    expected_revenue: MetricValue
    received_revenue: MetricValue
    forecast_cost: MetricValue
    actual_cost: MetricValue
    expected_profit: MetricValue
    profit_margin: MetricValue
    current_cash: MetricValue
    funding_gap: MetricValue
    need_30_days: MetricValue
    need_60_days: MetricValue
    need_90_days: MetricValue

    equity_required: MetricValue
    equity_raised: MetricValue
    committed_funding: MetricValue
    funded_amount: MetricValue
    remaining_funding: MetricValue

    cash_flow: ProjectCashFlowSummaryResponse
    alerts: list[ExecutiveFinanceAlert] = Field(default_factory=list)
    ai_summary: ProjectAiFinanceSummaryPayload
    data_completeness: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    cost_source: str = "none"


class PortfolioExecutiveAttentionItem(BaseModel):
    project_id: UUID
    project_name: str
    health: FinancialHealthStatus
    funding_gap: MetricValue
    expected_profit: MetricValue
    need_30_days: MetricValue
    reason: str


class PortfolioUpcomingCashItem(BaseModel):
    project_id: UUID
    project_name: str
    kind: str
    direction: str
    label: str
    amount: Decimal
    currency: str = "USD"
    expected_date: date | None = None


class PortfolioAiFinanceSummaryPayload(BaseModel):
    """Portfolio-level AI-ready payload — computed fields only."""

    projects_needing_cash: list[UUID] = Field(default_factory=list)
    most_profitable_projects: list[UUID] = Field(default_factory=list)
    riskiest_projects: list[UUID] = Field(default_factory=list)
    projects_missing_info: list[UUID] = Field(default_factory=list)
    generated_at: datetime
