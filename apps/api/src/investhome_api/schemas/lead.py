from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from investhome_api.models.lead import LeadStatus


class LeadBase(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    country: str | None = Field(default=None, max_length=100)
    source: str | None = Field(default=None, max_length=100)
    status: LeadStatus = LeadStatus.NEW
    assigned_to: str | None = Field(default=None, max_length=255)
    estimated_budget: Decimal | None = Field(default=None, ge=0)
    interested_project: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    country: str | None = Field(default=None, max_length=100)
    source: str | None = Field(default=None, max_length=100)
    status: LeadStatus | None = None
    assigned_to: str | None = Field(default=None, max_length=255)
    estimated_budget: Decimal | None = Field(default=None, ge=0)
    interested_project: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class LeadResponse(LeadBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_demo: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class LeadListResponse(BaseModel):
    items: list[LeadResponse]
    total: int
