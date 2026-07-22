"""Company workspace team management models."""

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
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from investhome_api.db.base import Base


class TeamType(str, enum.Enum):
    FUNCTIONAL = "functional"
    CROSS_FUNCTIONAL = "cross_functional"
    PROJECT = "project"
    TASK_FORCE = "task_force"
    SQUAD = "squad"
    COMMITTEE = "committee"
    WORKING_GROUP = "working_group"
    STEERING = "steering"
    VIRTUAL = "virtual"
    TEMPORARY = "temporary"
    OTHER = "other"


class TeamStatus(str, enum.Enum):
    DRAFT = "draft"
    FORMING = "forming"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    TEMPORARY = "temporary"
    COMPLETED = "completed"
    INACTIVE = "inactive"
    DISBANDED = "disbanded"
    ARCHIVED = "archived"
    MERGED = "merged"


class TeamLeadRole(str, enum.Enum):
    PRIMARY = "primary"
    DEPUTY = "deputy"


class TeamLeadStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ENDED = "ended"


class TeamMembershipType(str, enum.Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    TEMPORARY = "temporary"
    EXTERNAL_CONSULTANT = "external_consultant"
    CONTRACTOR = "contractor"
    OBSERVER = "observer"
    STAKEHOLDER = "stakeholder"


class TeamMemberStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ENDED = "ended"
    PENDING = "pending"


class TeamProjectLinkStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"


class TeamTaskStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TeamTaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TeamGoalStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ACHIEVED = "achieved"
    MISSED = "missed"
    CANCELLED = "cancelled"


class TeamKpiStatus(str, enum.Enum):
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    OFF_TRACK = "off_track"
    ACHIEVED = "achieved"


class TeamCapacityStatus(str, enum.Enum):
    UNDER_UTILIZED = "under_utilized"
    BALANCED = "balanced"
    NEAR_CAPACITY = "near_capacity"
    OVER_ALLOCATED = "over_allocated"


class CompanyTeam(Base):
    """Managed company team (distinct from foundation settings teams)."""

    __tablename__ = "company_teams"
    __table_args__ = (UniqueConstraint("company_id", "team_code", name="uq_company_teams_company_code"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    team_code: Mapped[str] = mapped_column(String(50), nullable=False)
    team_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("branches.id", ondelete="SET NULL"), nullable=True)
    department_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    team_type: Mapped[str] = mapped_column(String(40), nullable=False, default=TeamType.FUNCTIONAL.value)
    parent_team_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("company_teams.id", ondelete="SET NULL"), nullable=True
    )
    cost_center: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=TeamStatus.DRAFT.value)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_available_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    allocated_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    member_count: Mapped[int] = mapped_column(nullable=False, default=0)
    active_projects_count: Mapped[int] = mapped_column(nullable=False, default=0)
    open_tasks_count: Mapped[int] = mapped_column(nullable=False, default=0)
    merged_into_team_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("company_teams.id", ondelete="SET NULL"), nullable=True
    )
    disband_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    disband_effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    parent_team: Mapped[CompanyTeam | None] = relationship(
        remote_side="CompanyTeam.id",
        foreign_keys=[parent_team_id],
        back_populates="child_teams",
    )
    child_teams: Mapped[list[CompanyTeam]] = relationship(
        back_populates="parent_team",
        foreign_keys=[parent_team_id],
    )
    lead_assignments: Mapped[list[TeamLeadAssignment]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )
    members: Mapped[list[TeamMember]] = relationship(back_populates="team", cascade="all, delete-orphan")
    project_links: Mapped[list[TeamProjectLink]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )
    tasks: Mapped[list[TeamTask]] = relationship(back_populates="team", cascade="all, delete-orphan")
    goals: Mapped[list[TeamGoal]] = relationship(back_populates="team", cascade="all, delete-orphan")
    kpis: Mapped[list[TeamKPI]] = relationship(back_populates="team", cascade="all, delete-orphan")
    capacity_snapshots: Mapped[list[TeamCapacitySnapshot]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )


class TeamLeadAssignment(Base):
    __tablename__ = "team_lead_assignments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company_teams.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lead_role: Mapped[str] = mapped_column(String(20), nullable=False, default=TeamLeadRole.PRIMARY.value)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_temporary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=TeamLeadStatus.ACTIVE.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    team: Mapped[CompanyTeam] = relationship(back_populates="lead_assignments")


class TeamMember(Base):
    __tablename__ = "team_members"
    __table_args__ = (UniqueConstraint("team_id", "user_id", name="uq_team_members_team_user"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company_teams.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_in_team: Mapped[str | None] = mapped_column(String(120), nullable=True)
    membership_type: Mapped[str] = mapped_column(
        String(40), nullable=False, default=TeamMembershipType.PRIMARY.value
    )
    allocation_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    workload_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=TeamMemberStatus.ACTIVE.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    team: Mapped[CompanyTeam] = relationship(back_populates="members")


class TeamProjectLink(Base):
    __tablename__ = "team_project_links"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company_teams.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    project_stub_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str | None] = mapped_column(String(120), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    allocation_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    budget: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=TeamProjectLinkStatus.ACTIVE.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    team: Mapped[CompanyTeam] = relationship(back_populates="project_links")


class TeamTask(Base):
    __tablename__ = "team_tasks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company_teams.id", ondelete="CASCADE"), nullable=False)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    work_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("work_items.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default=TeamTaskPriority.MEDIUM.value)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=TeamTaskStatus.OPEN.value)
    estimated_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    actual_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    team: Mapped[CompanyTeam] = relationship(back_populates="tasks")


class TeamGoal(Base):
    __tablename__ = "team_goals"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company_teams.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_value: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    current_value: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=TeamGoalStatus.DRAFT.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    team: Mapped[CompanyTeam] = relationship(back_populates="goals")


class TeamKPI(Base):
    __tablename__ = "team_kpis"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company_teams.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_value: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    current_value: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    period: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=TeamKpiStatus.ON_TRACK.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    team: Mapped[CompanyTeam] = relationship(back_populates="kpis")


class TeamCapacitySnapshot(Base):
    __tablename__ = "team_capacity_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company_teams.id", ondelete="CASCADE"), nullable=False)
    period: Mapped[str] = mapped_column(String(30), nullable=False)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    available_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    allocated_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    remaining_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    utilization_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=TeamCapacityStatus.BALANCED.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    team: Mapped[CompanyTeam] = relationship(back_populates="capacity_snapshots")
