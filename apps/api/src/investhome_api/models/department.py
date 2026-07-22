"""Department management models — hierarchy, assignments, KPIs, budgets."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from investhome_api.db.base import Base


class DepartmentType(str, enum.Enum):
    EXECUTIVE_MANAGEMENT = "executive_management"
    FINANCE = "finance"
    HUMAN_RESOURCES = "human_resources"
    SALES = "sales"
    MARKETING = "marketing"
    OPERATIONS = "operations"
    IT = "it"
    LEGAL = "legal"
    RESEARCH_DEVELOPMENT = "research_development"
    CUSTOMER_SERVICE = "customer_service"
    PROCUREMENT = "procurement"
    QUALITY_ASSURANCE = "quality_assurance"
    PROJECT_MANAGEMENT = "project_management"
    CONSTRUCTION = "construction"
    DESIGN = "design"
    INVESTOR_RELATIONS = "investor_relations"
    ADMINISTRATION = "administration"
    OTHER = "other"


class DepartmentStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    RESTRUCTURING = "restructuring"
    MERGED = "merged"
    CLOSED = "closed"
    ARCHIVED = "archived"


class AssignmentStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    ENDED = "ended"


class KPIStatus(str, enum.Enum):
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    BEHIND = "behind"
    ACHIEVED = "achieved"
    CANCELLED = "cancelled"


class ResponsibilityStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    COMPLETED = "completed"
    OVERDUE = "overdue"


class BudgetApprovalStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISED = "revised"


class CompanyDepartment(Base):
    __tablename__ = "company_departments"
    __table_args__ = (UniqueConstraint("company_id", "department_code", name="uq_company_departments_code"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    department_code: Mapped[str] = mapped_column(String(50), nullable=False)
    department_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("branches.id", ondelete="SET NULL"), nullable=True)
    department_type: Mapped[str] = mapped_column(String(40), nullable=False, default=DepartmentType.OTHER.value)
    parent_department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("company_departments.id", ondelete="SET NULL"), nullable=True
    )
    department_head_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    cost_center: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=DepartmentStatus.DRAFT.value)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    annual_budget: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    fiscal_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    employee_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    team_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    open_positions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    merged_into_department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("company_departments.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    parent: Mapped[CompanyDepartment | None] = relationship(
        "CompanyDepartment", remote_side=[id], foreign_keys=[parent_department_id], back_populates="children"
    )
    children: Mapped[list[CompanyDepartment]] = relationship(
        "CompanyDepartment", foreign_keys=[parent_department_id], back_populates="parent"
    )
    employee_assignments: Mapped[list[DepartmentEmployeeAssignment]] = relationship(
        back_populates="department", cascade="all, delete-orphan"
    )
    kpis: Mapped[list[DepartmentKPI]] = relationship(back_populates="department", cascade="all, delete-orphan")
    responsibilities: Mapped[list[DepartmentResponsibility]] = relationship(
        back_populates="department", cascade="all, delete-orphan"
    )
    budgets: Mapped[list[DepartmentBudget]] = relationship(back_populates="department", cascade="all, delete-orphan")
    project_links: Mapped[list[DepartmentProjectLink]] = relationship(
        back_populates="department", cascade="all, delete-orphan"
    )


class DepartmentEmployeeAssignment(Base):
    __tablename__ = "department_employee_assignments"
    __table_args__ = (UniqueConstraint("department_id", "user_id", name="uq_dept_employee_assignments"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    department_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("company_departments.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    allocation_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=AssignmentStatus.ACTIVE.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    department: Mapped[CompanyDepartment] = relationship(back_populates="employee_assignments")


class DepartmentKPI(Base):
    __tablename__ = "department_kpis"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    department_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("company_departments.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    current_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    period: Mapped[str | None] = mapped_column(String(50), nullable=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    progress: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=KPIStatus.ON_TRACK.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    department: Mapped[CompanyDepartment] = relationship(back_populates="kpis")


class DepartmentResponsibility(Base):
    __tablename__ = "department_responsibilities"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    department_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("company_departments.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=ResponsibilityStatus.ACTIVE.value)
    review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    department: Mapped[CompanyDepartment] = relationship(back_populates="responsibilities")


class DepartmentBudget(Base):
    __tablename__ = "department_budgets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    department_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("company_departments.id", ondelete="CASCADE"), nullable=False
    )
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    approved_budget: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    used_budget: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True, default=0)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    cost_center: Mapped[str | None] = mapped_column(String(50), nullable=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approval_status: Mapped[str] = mapped_column(String(20), nullable=False, default=BudgetApprovalStatus.DRAFT.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    department: Mapped[CompanyDepartment] = relationship(back_populates="budgets")


class DepartmentProjectLink(Base):
    __tablename__ = "department_project_links"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    department_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("company_departments.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    link_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    department: Mapped[CompanyDepartment] = relationship(back_populates="project_links")
