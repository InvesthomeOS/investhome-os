from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from investhome_api.models.investor import (
    AccreditationStatus,
    InvestmentModel,
    InvestorStatus,
    InvestorType,
    RiskProfile,
)


class InvestorBase(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    country: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    investor_type: InvestorType = InvestorType.INDIVIDUAL
    accreditation_status: AccreditationStatus = AccreditationStatus.UNKNOWN
    preferred_investment_model: InvestmentModel | None = None
    investment_capacity: Decimal | None = Field(default=None, ge=0)
    minimum_ticket: Decimal | None = Field(default=None, ge=0)
    maximum_ticket: Decimal | None = Field(default=None, ge=0)
    preferred_markets: str | None = None
    preferred_projects: str | None = None
    risk_profile: RiskProfile | None = None
    status: InvestorStatus = InvestorStatus.PROSPECT
    assigned_to: str | None = Field(default=None, max_length=255)
    source: str | None = Field(default=None, max_length=100)
    notes: str | None = None
    last_contact_date: date | None = None
    next_follow_up_date: date | None = None

    @model_validator(mode="after")
    def validate_ticket_range(self) -> "InvestorBase":
        if (
            self.minimum_ticket is not None
            and self.maximum_ticket is not None
            and self.minimum_ticket > self.maximum_ticket
        ):
            msg = "minimum_ticket cannot exceed maximum_ticket"
            raise ValueError(msg)
        return self


class InvestorCreate(InvestorBase):
    pass


class InvestorUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    country: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    investor_type: InvestorType | None = None
    accreditation_status: AccreditationStatus | None = None
    preferred_investment_model: InvestmentModel | None = None
    investment_capacity: Decimal | None = Field(default=None, ge=0)
    minimum_ticket: Decimal | None = Field(default=None, ge=0)
    maximum_ticket: Decimal | None = Field(default=None, ge=0)
    preferred_markets: str | None = None
    preferred_projects: str | None = None
    risk_profile: RiskProfile | None = None
    status: InvestorStatus | None = None
    assigned_to: str | None = Field(default=None, max_length=255)
    source: str | None = Field(default=None, max_length=100)
    notes: str | None = None
    last_contact_date: date | None = None
    next_follow_up_date: date | None = None

    @model_validator(mode="after")
    def validate_ticket_range(self) -> "InvestorUpdate":
        if (
            self.minimum_ticket is not None
            and self.maximum_ticket is not None
            and self.minimum_ticket > self.maximum_ticket
        ):
            msg = "minimum_ticket cannot exceed maximum_ticket"
            raise ValueError(msg)
        return self


class InvestorResponse(InvestorBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_demo: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class InvestorListResponse(BaseModel):
    items: list[InvestorResponse]
    total: int
    page: int
    page_size: int
    pages: int


class InvestorStatsResponse(BaseModel):
    total: int
    active: int
    invested: int
    total_investment_capacity: Decimal
