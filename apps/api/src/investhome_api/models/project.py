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
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


class ProjectType(str, enum.Enum):
    RESIDENTIAL = "residential"
    MIXED_USE = "mixed_use"
    COMMERCIAL = "commercial"
    LAND = "land"
    MULTIFAMILY = "multifamily"
    CONDOMINIUM = "condominium"
    SINGLE_FAMILY = "single_family"
    TOWNHOME = "townhome"


class DevelopmentType(str, enum.Enum):
    GROUND_UP = "ground_up"
    RENOVATION = "renovation"
    CONVERSION = "conversion"
    VALUE_ADD = "value_add"
    FIX_AND_FLIP = "fix_and_flip"
    RENTAL = "rental"
    LAND_DEVELOPMENT = "land_development"


class ProjectStatus(str, enum.Enum):
    PIPELINE = "pipeline"
    DUE_DILIGENCE = "due_diligence"
    ACQUISITION = "acquisition"
    PRE_DEVELOPMENT = "pre_development"
    PERMITTING = "permitting"
    CONSTRUCTION = "construction"
    LEASING = "leasing"
    SALES = "sales"
    STABILIZATION = "stabilization"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"


class ProjectPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DevelopmentStage(str, enum.Enum):
    DEAL_SCREENING = "deal_screening"
    DUE_DILIGENCE = "due_diligence"
    ACQUISITION = "acquisition"
    DESIGN = "design"
    ENTITLEMENT = "entitlement"
    PERMITTING = "permitting"
    PROCUREMENT = "procurement"
    CONSTRUCTION = "construction"
    SALES = "sales"
    LEASE_UP = "lease_up"
    STABILIZATION = "stabilization"
    EXIT = "exit"
    CLOSED = "closed"


# Statuses considered actively in development for portfolio metrics.
ACTIVE_PROJECT_STATUSES: frozenset[ProjectStatus] = frozenset(
    {
        ProjectStatus.DUE_DILIGENCE,
        ProjectStatus.ACQUISITION,
        ProjectStatus.PRE_DEVELOPMENT,
        ProjectStatus.PERMITTING,
        ProjectStatus.CONSTRUCTION,
        ProjectStatus.LEASING,
        ProjectStatus.SALES,
        ProjectStatus.STABILIZATION,
    }
)


class Project(Base):
    """Real estate development project.

    Future relationships (investors, investments, transactions, units, documents,
    milestones) can attach via foreign keys to ``projects.id`` without schema changes
    to this core table.
    """

    __tablename__ = "projects"
    __table_args__ = (
        # project_status / project_type / city indexes already exist from 0004
        Index("ix_projects_priority", "priority"),
        Index("ix_projects_development_stage", "development_stage"),
        Index("ix_projects_state", "state"),
        Index("ix_projects_company_id", "company_id"),
        Index("ix_projects_project_manager_user_id", "project_manager_user_id"),
        Index("ix_projects_target_completion_date", "target_completion_date"),
        Index("ix_projects_created_at", "created_at"),
        Index("ix_projects_slug", "slug", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str | None] = mapped_column(String(280), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    project_type: Mapped[ProjectType] = mapped_column(
        Enum(ProjectType, native_enum=False, length=50),
        nullable=False,
        default=ProjectType.RESIDENTIAL,
    )
    development_type: Mapped[DevelopmentType] = mapped_column(
        Enum(DevelopmentType, native_enum=False, length=50),
        nullable=False,
        default=DevelopmentType.GROUND_UP,
    )
    project_status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, native_enum=False, length=50),
        nullable=False,
        default=ProjectStatus.PIPELINE,
    )
    priority: Mapped[ProjectPriority] = mapped_column(
        Enum(
            ProjectPriority,
            native_enum=False,
            length=20,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=ProjectPriority.MEDIUM,
    )
    development_stage: Mapped[DevelopmentStage | None] = mapped_column(
        Enum(
            DevelopmentStage,
            native_enum=False,
            length=40,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=True,
    )
    ownership_entity: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    total_units: Mapped[int | None] = mapped_column(nullable=True)
    residential_units: Mapped[int | None] = mapped_column(nullable=True)
    commercial_units: Mapped[int | None] = mapped_column(nullable=True)
    gross_square_feet: Mapped[int | None] = mapped_column(nullable=True)
    net_sellable_square_feet: Mapped[int | None] = mapped_column(nullable=True)
    lot_size: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    acquisition_price: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    land_cost: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    construction_budget: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    soft_cost_budget: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    total_development_cost: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    current_project_value: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    projected_sale_value: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    equity_required: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    equity_raised: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    debt_amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    loan_to_cost: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    projected_revenue: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    projected_profit: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    projected_roi: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    projected_irr: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    completion_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    acquisition_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    estimated_closing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    assigned_project_manager: Mapped[str | None] = mapped_column(String(255), nullable=True)
    project_manager_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
