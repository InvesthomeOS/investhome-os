"""CRM operational lead workspace schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

CrmLeadStage = Literal["yeni", "contacted", "following", "qualified", "converted", "unqualified"]
CrmLeadIngestStatus = Literal["ok", "unmatched", "failed"]


class CrmLeadMatch(BaseModel):
    kind: Literal["lead", "person"]
    id: UUID
    name: str
    phone: str | None = None
    email: str | None = None
    reason: str
    href: str | None = None


class CrmLeadOwnerOption(BaseModel):
    id: UUID
    name: str


class CrmLeadActivityItem(BaseModel):
    id: UUID
    action: str
    description: str
    actor_name: str | None = None
    created_at: datetime
    metadata: dict[str, Any] | None = None


class CrmLeadItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    phone: str | None = None
    email: str | None = None
    source: str | None = None
    campaign: str | None = None
    ad_id: str | None = None
    form_id: str | None = None
    project: str | None = None
    owner_user_id: UUID | None = None
    owner_name: str | None = None
    stage: CrmLeadStage
    notes: str | None = None
    provider: str | None = None
    ingest_status: str
    converted_contact_id: UUID | None = None
    converted_contact_name: str | None = None
    created_at: datetime
    updated_at: datetime


class CrmLeadDetail(CrmLeadItem):
    existing_person_id: UUID | None = None
    existing_person_name: str | None = None
    metadata: dict[str, Any] | None = None
    activity: list[CrmLeadActivityItem] = Field(default_factory=list)


class CrmLeadKpis(BaseModel):
    total: int = 0
    active: int = 0
    yeni: int = 0
    following: int = 0
    qualified: int = 0
    converted: int = 0
    unqualified: int = 0
    unmatched: int = 0
    failed: int = 0


class CrmLeadListResponse(BaseModel):
    items: list[CrmLeadItem]
    total: int
    kpis: CrmLeadKpis
    sources: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    owners: list[CrmLeadOwnerOption] = Field(default_factory=list)
    stages: list[str] = Field(
        default_factory=lambda: ["yeni", "contacted", "following", "qualified", "converted", "unqualified"]
    )


class CrmLeadWrite(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    source: str | None = Field(default=None, max_length=100)
    campaign: str | None = Field(default=None, max_length=255)
    ad_id: str | None = Field(default=None, max_length=120)
    form_id: str | None = Field(default=None, max_length=120)
    project: str | None = Field(default=None, max_length=255)
    owner_user_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=5000)
    stage: CrmLeadStage | None = None


class CrmLeadCreate(CrmLeadWrite):
    provider: str | None = Field(default="manual", max_length=40)


class CrmLeadUpdate(CrmLeadWrite):
    pass


class CrmLeadStageUpdate(BaseModel):
    stage: CrmLeadStage


class CrmLeadConvertRequest(BaseModel):
    confirm_existing_person_id: UUID | None = None


class CrmLeadConvertResponse(BaseModel):
    lead: CrmLeadDetail
    contact_id: UUID
    contact_name: str
    reused_existing: bool
    href: str


class CrmLeadIngestRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=40)
    source: str | None = Field(default=None, max_length=100)
    campaign: str | None = Field(default=None, max_length=255)
    ad_id: str | None = Field(default=None, max_length=120)
    form_id: str | None = Field(default=None, max_length=120)
    full_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    project: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=5000)
    payload: dict[str, Any] | None = None


class CrmLeadConflictBody(BaseModel):
    code: Literal["existing_lead", "existing_person", "ambiguous_person"]
    message: str
    matches: list[CrmLeadMatch] = Field(default_factory=list)
