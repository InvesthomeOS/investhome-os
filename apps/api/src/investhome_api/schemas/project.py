from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from investhome_api.models.project import DevelopmentType, ProjectStatus, ProjectType


class ProjectBase(BaseModel):
    project_code: str = Field(min_length=1, max_length=50)
    project_name: str = Field(min_length=1, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, max_length=100)
    project_type: ProjectType = ProjectType.RESIDENTIAL
    development_type: DevelopmentType = DevelopmentType.GROUND_UP
    project_status: ProjectStatus = ProjectStatus.PIPELINE
    ownership_entity: str | None = Field(default=None, max_length=255)
    total_units: int | None = Field(default=None, ge=0)
    residential_units: int | None = Field(default=None, ge=0)
    commercial_units: int | None = Field(default=None, ge=0)
    gross_square_feet: int | None = Field(default=None, ge=0)
    acquisition_price: Decimal | None = Field(default=None, ge=0)
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
    start_date: date | None = None
    target_completion_date: date | None = None
    actual_completion_date: date | None = None
    assigned_project_manager: str | None = Field(default=None, max_length=255)
    description: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_unit_counts(self) -> "ProjectBase":
        if (
            self.total_units is not None
            and self.residential_units is not None
            and self.commercial_units is not None
            and self.residential_units + self.commercial_units > self.total_units
        ):
            msg = "residential_units plus commercial_units cannot exceed total_units"
            raise ValueError(msg)
        return self


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    project_code: str | None = Field(default=None, min_length=1, max_length=50)
    project_name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, max_length=100)
    project_type: ProjectType | None = None
    development_type: DevelopmentType | None = None
    project_status: ProjectStatus | None = None
    ownership_entity: str | None = Field(default=None, max_length=255)
    total_units: int | None = Field(default=None, ge=0)
    residential_units: int | None = Field(default=None, ge=0)
    commercial_units: int | None = Field(default=None, ge=0)
    gross_square_feet: int | None = Field(default=None, ge=0)
    acquisition_price: Decimal | None = Field(default=None, ge=0)
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
    start_date: date | None = None
    target_completion_date: date | None = None
    actual_completion_date: date | None = None
    assigned_project_manager: str | None = Field(default=None, max_length=255)
    description: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_unit_counts(self) -> "ProjectUpdate":
        if (
            self.total_units is not None
            and self.residential_units is not None
            and self.commercial_units is not None
            and self.residential_units + self.commercial_units > self.total_units
        ):
            msg = "residential_units plus commercial_units cannot exceed total_units"
            raise ValueError(msg)
        return self


class ProjectResponse(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_demo: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ProjectStatsResponse(BaseModel):
    total: int
    active: int
    units_under_development: int
    total_development_cost: Decimal
    current_portfolio_value: Decimal
    equity_raised: Decimal
