"""Marketing budget management — plans, allocations, forecasts, scenarios."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


class BudgetPlanType(str, enum.Enum):
    ANNUAL = "annual"
    QUARTERLY = "quarterly"
    MONTHLY = "monthly"


class BudgetPlanStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    LOCKED = "locked"
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"
    ARCHIVED = "archived"


class BudgetHierarchyLevel(str, enum.Enum):
    ORGANIZATION = "organization"
    BUSINESS_UNIT = "business_unit"
    COUNTRY = "country"
    REGION = "region"
    PROJECT = "project"
    CAMPAIGN = "campaign"
    CHANNEL = "channel"
    CREATIVE = "creative"


class BudgetSpendRecordType(str, enum.Enum):
    ACTUAL = "actual"
    COMMITTED = "committed"


class BudgetRequestStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class BudgetTransferStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class BudgetApprovalRole(str, enum.Enum):
    MARKETING_MANAGER = "marketing_manager"
    MARKETING_DIRECTOR = "marketing_director"
    CMO = "cmo"
    CEO = "ceo"
    FINANCE = "finance"


class BudgetApprovalStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    RETURNED = "returned"
    CANCELLED = "cancelled"


class ForecastMetricType(str, enum.Enum):
    LEAD = "lead"
    QUALIFIED_LEAD = "qualified_lead"
    MEETING = "meeting"
    RESERVATION = "reservation"
    SALES = "sales"
    REVENUE = "revenue"
    SPEND = "spend"


class ScenarioType(str, enum.Enum):
    BASE_CASE = "base_case"
    OPTIMISTIC = "optimistic"
    CONSERVATIVE = "conservative"
    CUSTOM = "custom"


class VarianceStatus(str, enum.Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


class MarketingBudgetPlan(Base):
    __tablename__ = "marketing_budget_plans"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan_type: Mapped[BudgetPlanType] = mapped_column(
        Enum(BudgetPlanType, native_enum=False, length=20),
        nullable=False,
    )
    fiscal_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quarter: Mapped[int | None] = mapped_column(Integer, nullable=True)
    month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), server_default="USD", nullable=False)
    total_budget: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    status: Mapped[BudgetPlanStatus] = mapped_column(
        Enum(BudgetPlanStatus, native_enum=False, length=30),
        server_default=BudgetPlanStatus.DRAFT.value,
        nullable=False,
    )
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    business_unit_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    country: Mapped[str | None] = mapped_column(String(80), nullable=True)
    region: Mapped[str | None] = mapped_column(String(80), nullable=True)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_marketing_budget_plans_status", "status"),
        Index("ix_marketing_budget_plans_fiscal_year", "fiscal_year"),
        Index("ix_marketing_budget_plans_plan_type", "plan_type"),
    )


class MarketingBudgetAllocation(Base):
    __tablename__ = "marketing_budget_allocations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_budget_plans.id", ondelete="CASCADE"), nullable=False
    )
    parent_allocation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_budget_allocations.id", ondelete="SET NULL"), nullable=True
    )
    hierarchy_level: Mapped[BudgetHierarchyLevel] = mapped_column(
        Enum(BudgetHierarchyLevel, native_enum=False, length=30),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    business_unit_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    country: Mapped[str | None] = mapped_column(String(80), nullable=True)
    region: Mapped[str | None] = mapped_column(String(80), nullable=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_campaigns.id", ondelete="SET NULL"), nullable=True
    )
    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_channels.id", ondelete="SET NULL"), nullable=True
    )
    creative_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    legacy_budget_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_budgets.id", ondelete="SET NULL"), nullable=True
    )
    currency: Mapped[str] = mapped_column(String(3), server_default="USD", nullable=False)
    planned_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    allocated_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    committed_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    spent_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(30), server_default="draft", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_marketing_budget_allocations_plan_id", "plan_id"),
        Index("ix_marketing_budget_allocations_campaign_id", "campaign_id"),
        Index("ix_marketing_budget_allocations_channel_id", "channel_id"),
        Index("ix_marketing_budget_allocations_hierarchy", "hierarchy_level"),
    )


class MarketingBudgetSpendRecord(Base):
    __tablename__ = "marketing_budget_spend_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_budget_plans.id", ondelete="SET NULL"), nullable=True
    )
    allocation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_budget_allocations.id", ondelete="SET NULL"), nullable=True
    )
    record_type: Mapped[BudgetSpendRecordType] = mapped_column(
        Enum(BudgetSpendRecordType, native_enum=False, length=20),
        nullable=False,
    )
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), server_default="USD", nullable=False)
    source_ref_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source_ref_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_marketing_budget_spend_records_plan_id", "plan_id"),
        Index("ix_marketing_budget_spend_records_allocation_id", "allocation_id"),
        Index("ix_marketing_budget_spend_records_record_type", "record_type"),
    )


class MarketingBudgetRequest(Base):
    __tablename__ = "marketing_budget_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_budget_plans.id", ondelete="CASCADE"), nullable=False
    )
    allocation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_budget_allocations.id", ondelete="SET NULL"), nullable=True
    )
    request_type: Mapped[str] = mapped_column(String(40), nullable=False)
    requested_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), server_default="USD", nullable=False)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[BudgetRequestStatus] = mapped_column(
        Enum(BudgetRequestStatus, native_enum=False, length=20),
        server_default=BudgetRequestStatus.DRAFT.value,
        nullable=False,
    )
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_marketing_budget_requests_plan_id", "plan_id"),
        Index("ix_marketing_budget_requests_status", "status"),
    )


class MarketingBudgetTransfer(Base):
    __tablename__ = "marketing_budget_transfers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_budget_plans.id", ondelete="CASCADE"), nullable=False
    )
    from_allocation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_budget_allocations.id", ondelete="SET NULL"), nullable=True
    )
    to_allocation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_budget_allocations.id", ondelete="SET NULL"), nullable=True
    )
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), server_default="USD", nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[BudgetTransferStatus] = mapped_column(
        Enum(BudgetTransferStatus, native_enum=False, length=20),
        server_default=BudgetTransferStatus.DRAFT.value,
        nullable=False,
    )
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_marketing_budget_transfers_plan_id", "plan_id"),
        Index("ix_marketing_budget_transfers_status", "status"),
    )


class MarketingBudgetApproval(Base):
    __tablename__ = "marketing_budget_approvals"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    approval_role: Mapped[BudgetApprovalRole] = mapped_column(
        Enum(BudgetApprovalRole, native_enum=False, length=30),
        nullable=False,
    )
    status: Mapped[BudgetApprovalStatus] = mapped_column(
        Enum(BudgetApprovalStatus, native_enum=False, length=20),
        server_default=BudgetApprovalStatus.DRAFT.value,
        nullable=False,
    )
    sequence_order: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    approver_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_marketing_budget_approvals_entity", "entity_type", "entity_id"),
        Index("ix_marketing_budget_approvals_status", "status"),
    )


class MarketingForecast(Base):
    __tablename__ = "marketing_forecasts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_budget_plans.id", ondelete="CASCADE"), nullable=True
    )
    metric_type: Mapped[ForecastMetricType] = mapped_column(
        Enum(ForecastMetricType, native_enum=False, length=30),
        nullable=False,
    )
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    forecast_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    state: Mapped[str] = mapped_column(String(30), server_default="unknown", nullable=False)
    pipeline_connected: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_marketing_forecasts_plan_id", "plan_id"),
        Index("ix_marketing_forecasts_metric_type", "metric_type"),
    )


class MarketingScenarioPlan(Base):
    __tablename__ = "marketing_scenario_plans"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_budget_plans.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scenario_type: Mapped[ScenarioType] = mapped_column(
        Enum(ScenarioType, native_enum=False, length=20),
        nullable=False,
    )
    budget_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    spend_target: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    lead_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sales_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    revenue_target: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), server_default="USD", nullable=False)
    assumptions_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_marketing_scenario_plans_plan_id", "plan_id"),
        Index("ix_marketing_scenario_plans_scenario_type", "scenario_type"),
    )
