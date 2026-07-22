from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from investhome_api.models.project import (
    DevelopmentStage,
    DevelopmentType,
    ProjectPriority,
    ProjectStatus,
    ProjectType,
)
from investhome_api.models.project_team import ProjectTeamMemberStatus, ProjectTeamRole

FINANCIAL_FIELDS: frozenset[str] = frozenset(
    {
        "acquisition_price",
        "land_cost",
        "construction_budget",
        "soft_cost_budget",
        "total_development_cost",
        "current_project_value",
        "projected_sale_value",
        "equity_required",
        "equity_raised",
        "debt_amount",
        "loan_to_cost",
        "projected_revenue",
        "projected_profit",
        "projected_roi",
        "projected_irr",
    }
)


class ProjectUserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str | None = None


class ProjectTeamMemberBase(BaseModel):
    user_id: UUID
    role: ProjectTeamRole
    is_primary: bool = False
    start_date: date | None = None
    end_date: date | None = None
    status: ProjectTeamMemberStatus = ProjectTeamMemberStatus.ACTIVE
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_dates(self) -> "ProjectTeamMemberBase":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class ProjectTeamMemberCreate(ProjectTeamMemberBase):
    pass


class ProjectTeamMemberUpdate(BaseModel):
    role: ProjectTeamRole | None = None
    is_primary: bool | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: ProjectTeamMemberStatus | None = None
    notes: str | None = Field(default=None, max_length=500)


class ProjectTeamMemberResponse(ProjectTeamMemberBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    user: ProjectUserSummary | None = None
    created_at: datetime
    updated_at: datetime


class ProjectTeamListResponse(BaseModel):
    items: list[ProjectTeamMemberResponse]
    total: int


class ProjectStatusChangeRequest(BaseModel):
    status: ProjectStatus
    note: str | None = Field(default=None, max_length=500)


class ProjectStatusTransitionResponse(BaseModel):
    current_status: ProjectStatus
    allowed: list[ProjectStatus]


class ProjectBase(BaseModel):
    project_code: str = Field(min_length=1, max_length=50)
    project_name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=280)
    address: str | None = Field(default=None, max_length=500)
    address_line2: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, max_length=100)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    timezone: str | None = Field(default=None, max_length=64)
    project_type: ProjectType = ProjectType.RESIDENTIAL
    development_type: DevelopmentType = DevelopmentType.GROUND_UP
    project_status: ProjectStatus = ProjectStatus.PIPELINE
    priority: ProjectPriority = ProjectPriority.MEDIUM
    development_stage: DevelopmentStage | None = None
    ownership_entity: str | None = Field(default=None, max_length=255)
    company_id: UUID | None = None
    total_units: int | None = Field(default=None, ge=0)
    residential_units: int | None = Field(default=None, ge=0)
    commercial_units: int | None = Field(default=None, ge=0)
    gross_square_feet: int | None = Field(default=None, ge=0)
    net_sellable_square_feet: int | None = Field(default=None, ge=0)
    lot_size: Decimal | None = Field(default=None, ge=0)
    acquisition_price: Decimal | None = Field(default=None, ge=0)
    land_cost: Decimal | None = Field(default=None, ge=0)
    construction_budget: Decimal | None = Field(default=None, ge=0)
    soft_cost_budget: Decimal | None = Field(default=None, ge=0)
    total_development_cost: Decimal | None = Field(default=None, ge=0)
    current_project_value: Decimal | None = Field(default=None, ge=0)
    projected_sale_value: Decimal | None = Field(default=None, ge=0)
    equity_required: Decimal | None = Field(default=None, ge=0)
    equity_raised: Decimal | None = Field(default=None, ge=0)
    debt_amount: Decimal | None = Field(default=None, ge=0)
    loan_to_cost: Decimal | None = Field(default=None, ge=0, le=100)
    projected_revenue: Decimal | None = Field(default=None, ge=0)
    projected_profit: Decimal | None = Field(default=None)
    projected_roi: Decimal | None = None
    projected_irr: Decimal | None = None
    currency: str = Field(default="USD", min_length=3, max_length=3)
    completion_percentage: Decimal | None = Field(default=None, ge=0, le=100)
    acquisition_date: date | None = None
    start_date: date | None = None
    actual_start_date: date | None = None
    target_completion_date: date | None = None
    actual_completion_date: date | None = None
    estimated_closing_date: date | None = None
    assigned_project_manager: str | None = Field(default=None, max_length=255)
    project_manager_user_id: UUID | None = None
    description: str | None = None
    notes: str | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("project_code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("project_code cannot be empty")
        return cleaned

    @model_validator(mode="after")
    def validate_project_rules(self) -> "ProjectBase":
        if (
            self.total_units is not None
            and self.residential_units is not None
            and self.commercial_units is not None
            and self.residential_units + self.commercial_units > self.total_units
        ):
            raise ValueError("residential_units plus commercial_units cannot exceed total_units")

        if self.start_date and self.target_completion_date and self.target_completion_date < self.start_date:
            raise ValueError("target_completion_date cannot be before start_date")

        if (
            self.actual_start_date
            and self.actual_completion_date
            and self.actual_completion_date < self.actual_start_date
        ):
            raise ValueError("actual_completion_date cannot be before actual_start_date")

        has_identity = bool(
            (self.address and self.address.strip())
            or (self.description and self.description.strip())
            or (self.project_code and self.project_code.strip())
        )
        if not has_identity:
            raise ValueError("Provide at least one of address, description, or project_code")

        return self


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    project_code: str | None = Field(default=None, min_length=1, max_length=50)
    project_name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=280)
    address: str | None = Field(default=None, max_length=500)
    address_line2: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, max_length=100)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    timezone: str | None = Field(default=None, max_length=64)
    project_type: ProjectType | None = None
    development_type: DevelopmentType | None = None
    project_status: ProjectStatus | None = None
    priority: ProjectPriority | None = None
    development_stage: DevelopmentStage | None = None
    ownership_entity: str | None = Field(default=None, max_length=255)
    company_id: UUID | None = None
    total_units: int | None = Field(default=None, ge=0)
    residential_units: int | None = Field(default=None, ge=0)
    commercial_units: int | None = Field(default=None, ge=0)
    gross_square_feet: int | None = Field(default=None, ge=0)
    net_sellable_square_feet: int | None = Field(default=None, ge=0)
    lot_size: Decimal | None = Field(default=None, ge=0)
    acquisition_price: Decimal | None = Field(default=None, ge=0)
    land_cost: Decimal | None = Field(default=None, ge=0)
    construction_budget: Decimal | None = Field(default=None, ge=0)
    soft_cost_budget: Decimal | None = Field(default=None, ge=0)
    total_development_cost: Decimal | None = Field(default=None, ge=0)
    current_project_value: Decimal | None = Field(default=None, ge=0)
    projected_sale_value: Decimal | None = Field(default=None, ge=0)
    equity_required: Decimal | None = Field(default=None, ge=0)
    equity_raised: Decimal | None = Field(default=None, ge=0)
    debt_amount: Decimal | None = Field(default=None, ge=0)
    loan_to_cost: Decimal | None = Field(default=None, ge=0, le=100)
    projected_revenue: Decimal | None = Field(default=None, ge=0)
    projected_profit: Decimal | None = None
    projected_roi: Decimal | None = None
    projected_irr: Decimal | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    completion_percentage: Decimal | None = Field(default=None, ge=0, le=100)
    acquisition_date: date | None = None
    start_date: date | None = None
    actual_start_date: date | None = None
    target_completion_date: date | None = None
    actual_completion_date: date | None = None
    estimated_closing_date: date | None = None
    assigned_project_manager: str | None = Field(default=None, max_length=255)
    project_manager_user_id: UUID | None = None
    description: str | None = None
    notes: str | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_unit_counts(self) -> "ProjectUpdate":
        if (
            self.total_units is not None
            and self.residential_units is not None
            and self.commercial_units is not None
            and self.residential_units + self.commercial_units > self.total_units
        ):
            raise ValueError("residential_units plus commercial_units cannot exceed total_units")
        if self.start_date and self.target_completion_date and self.target_completion_date < self.start_date:
            raise ValueError("target_completion_date cannot be before start_date")
        if (
            self.actual_start_date
            and self.actual_completion_date
            and self.actual_completion_date < self.actual_start_date
        ):
            raise ValueError("actual_completion_date cannot be before actual_start_date")
        return self


class ProjectResponse(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_demo: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    created_by_user_id: UUID | None = None
    updated_by_user_id: UUID | None = None
    project_manager: ProjectUserSummary | None = None
    team_summary: list[ProjectTeamMemberResponse] = Field(default_factory=list)


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ProjectStatsResponse(BaseModel):
    total: int
    active: int
    under_construction: int
    completed: int
    units_under_development: int
    total_units: int
    total_development_cost: Decimal
    current_portfolio_value: Decimal
    equity_raised: Decimal
