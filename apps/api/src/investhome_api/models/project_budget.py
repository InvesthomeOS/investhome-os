"""Normalized project budget foundation (Sprint 10A4A).

Legacy ``finance.ProjectBudget`` rows remain the finance-workspace line summary.
These models provide versioned budgets, categories, cost codes, and revisions.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


class BudgetCategoryType(str, enum.Enum):
    LAND = "land"
    ACQUISITION = "acquisition"
    HARD_COST = "hard_cost"
    SOFT_COST = "soft_cost"
    FINANCING = "financing"
    MARKETING = "marketing"
    SALES = "sales"
    LEASING = "leasing"
    OPERATING = "operating"
    CONTINGENCY = "contingency"
    TAX = "tax"
    INSURANCE = "insurance"
    PROFESSIONAL_FEES = "professional_fees"
    DEVELOPER_FEE = "developer_fee"
    OTHER = "other"


class BudgetVersionStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class BudgetRevisionStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ProjectBudgetCategory(Base):
    __tablename__ = "project_budget_categories"
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_project_budget_categories_company_code"),
        Index("ix_project_budget_categories_company_id", "company_id"),
        Index("ix_project_budget_categories_parent_id", "parent_id"),
        Index("ix_project_budget_categories_category_type", "category_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_type: Mapped[BudgetCategoryType] = mapped_column(
        Enum(BudgetCategoryType, native_enum=False, length=50),
        nullable=False,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("project_budget_categories.id", ondelete="SET NULL"), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ProjectCostCode(Base):
    __tablename__ = "project_cost_codes"
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_project_cost_codes_company_code"),
        Index("ix_project_cost_codes_company_id", "company_id"),
        Index("ix_project_cost_codes_category_id", "category_id"),
        Index("ix_project_cost_codes_parent_id", "parent_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project_budget_categories.id", ondelete="RESTRICT"), nullable=False
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("project_cost_codes.id", ondelete="SET NULL"), nullable=True
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ProjectBudgetVersion(Base):
    __tablename__ = "project_budget_versions"
    __table_args__ = (
        UniqueConstraint("project_id", "version_number", name="uq_project_budget_versions_project_version"),
        Index("ix_project_budget_versions_project_id", "project_id"),
        Index("ix_project_budget_versions_status", "status"),
        Index("ix_project_budget_versions_is_current", "is_current"),
        Index("ix_project_budget_versions_company_id", "company_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[BudgetVersionStatus] = mapped_column(
        Enum(BudgetVersionStatus, native_enum=False, length=30),
        nullable=False,
        default=BudgetVersionStatus.DRAFT,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class ProjectBudgetLine(Base):
    __tablename__ = "project_budget_lines"
    __table_args__ = (
        UniqueConstraint(
            "budget_version_id", "line_number", name="uq_project_budget_lines_version_line_number"
        ),
        Index("ix_project_budget_lines_project_id", "project_id"),
        Index("ix_project_budget_lines_budget_version_id", "budget_version_id"),
        Index("ix_project_budget_lines_category_id", "category_id"),
        Index("ix_project_budget_lines_cost_code_id", "cost_code_id"),
        Index("ix_project_budget_lines_parent_line_id", "parent_line_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    budget_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project_budget_versions.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project_budget_categories.id", ondelete="RESTRICT"), nullable=False
    )
    cost_code_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("project_cost_codes.id", ondelete="SET NULL"), nullable=True
    )
    parent_line_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("project_budget_lines.id", ondelete="SET NULL"), nullable=True
    )
    legacy_project_budget_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("project_budgets.id", ondelete="SET NULL"), nullable=True
    )
    line_number: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    original_budget: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    approved_revisions: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    current_budget: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    committed_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    actual_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    forecast_to_complete: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    forecast_at_completion: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    variance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_summary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class ProjectBudgetRevision(Base):
    __tablename__ = "project_budget_revisions"
    __table_args__ = (
        UniqueConstraint(
            "budget_version_id",
            "revision_number",
            name="uq_project_budget_revisions_version_number",
        ),
        Index("ix_project_budget_revisions_project_id", "project_id"),
        Index("ix_project_budget_revisions_budget_version_id", "budget_version_id"),
        Index("ix_project_budget_revisions_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    budget_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project_budget_versions.id", ondelete="CASCADE"), nullable=False
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[BudgetRevisionStatus] = mapped_column(
        Enum(BudgetRevisionStatus, native_enum=False, length=30),
        nullable=False,
        default=BudgetRevisionStatus.DRAFT,
    )
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ProjectBudgetRevisionLine(Base):
    __tablename__ = "project_budget_revision_lines"
    __table_args__ = (
        Index("ix_project_budget_revision_lines_revision_id", "revision_id"),
        Index("ix_project_budget_revision_lines_budget_line_id", "budget_line_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    revision_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project_budget_revisions.id", ondelete="CASCADE"), nullable=False
    )
    budget_line_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project_budget_lines.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
