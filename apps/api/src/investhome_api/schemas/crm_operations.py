"""Request and response models for shared CRM operational flows."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CrmPersonWrite(BaseModel):
    contact_id: UUID | None = None
    first_name: str | None = Field(default=None, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    source: str | None = Field(default=None, max_length=120)
    address_line1: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=120)
    state_province: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=100)
    language: str | None = Field(default=None, max_length=20)
    organization_name: str | None = Field(default=None, max_length=255)
    job_title: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=5000)
    owner_user_id: UUID | None = None
    next_follow_up_at: datetime | None = None


class CrmAgreementCreateRequest(CrmPersonWrite):
    project_group: str = Field(min_length=1, max_length=40)
    unit_number: str | None = Field(default=None, max_length=80)
    phase_id: UUID | None = None
    inventory_asset_id: UUID | None = None
    investment_amount: str | None = Field(default=None, max_length=80)
    agreement_date: date | None = None
    source_lead_id: UUID | None = None


class CrmLeadAgreementConvertRequest(BaseModel):
    project_group: str = Field(min_length=1, max_length=40)
    unit_number: str | None = Field(default=None, max_length=80)
    phase_id: UUID | None = None
    inventory_asset_id: UUID | None = None
    investment_amount: str | None = Field(default=None, max_length=80)
    agreement_date: date | None = None


class CrmAgreementCreateResult(BaseModel):
    agreement_id: UUID
    contact_id: UUID
    project_group: str
    unit_number: str | None = None
    stage_label: str
    reused_existing: bool
    lead_id: UUID | None = None
    lead_stage: str | None = None


class CrmAgreementStageUpdate(BaseModel):
    stage: str = Field(min_length=1, max_length=120)


class CrmAgencyCustomerCreate(CrmPersonWrite):
    agency_contact_id: UUID


class CrmContactProcessLead(BaseModel):
    id: UUID
    name: str
    stage: str
    active: bool
    focused: bool = False


class CrmContactProcessAgreement(BaseModel):
    id: UUID
    project_group: str
    project_label: str
    unit_number: str | None = None
    stage: str
    stage_label: str | None = None
    active: bool
    focused: bool = False


class CrmContactProcesses(BaseModel):
    contact_id: UUID
    leads: list[CrmContactProcessLead]
    agreements: list[CrmContactProcessAgreement]
