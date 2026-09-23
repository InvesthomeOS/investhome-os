"""CRM identity match review schemas — no fake scores, no merge side effects."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

CrmMatchKind = Literal["strong", "possible"]
CrmMatchStatus = Literal["pending", "in_review", "same_person", "different"]
CrmMatchAction = Literal["same_person", "different", "in_review"]
CrmMatchReason = Literal["phone", "email", "secondary_email", "bitrix", "name_review"]


class CrmMatchEvidence(BaseModel):
    reason: str
    value: str | None = None


class CrmMatchPurchase(BaseModel):
    id: UUID
    project: str | None = None
    unit: str | None = None
    source_id: str | None = None
    historical: bool = False


class CrmMatchPerson(BaseModel):
    id: UUID
    name: str
    phone: str | None = None
    email: str | None = None
    secondary_emails: list[str] = Field(default_factory=list)
    source: str | None = None
    source_ids: list[str] = Field(default_factory=list)
    notes: str | None = None
    review_required: bool = False
    href: str
    purchases: list[CrmMatchPurchase] = Field(default_factory=list)


class CrmMatchItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    person_a_id: UUID
    person_a_name: str
    person_b_id: UUID
    person_b_name: str
    reasons: list[str] = Field(default_factory=list)
    match_kind: CrmMatchKind
    shared_phone: str | None = None
    shared_email: str | None = None
    source: str | None = None
    status: CrmMatchStatus
    protected: bool = False
    protected_reason: str | None = None
    merge_queued: bool = False
    review_notes: str | None = None
    created_at: datetime | None = None


class CrmMatchDetail(CrmMatchItem):
    person_a: CrmMatchPerson
    person_b: CrmMatchPerson
    evidence: list[CrmMatchEvidence] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    linked_purchases: list[CrmMatchPurchase] = Field(default_factory=list)
    merge_blocked: bool = True
    merge_message: str


class CrmMatchKpis(BaseModel):
    pending: int = 0
    strong: int = 0
    possible: int = 0
    rejected: int = 0
    same_person: int = 0


class CrmMatchListResponse(BaseModel):
    items: list[CrmMatchItem]
    total: int
    kpis: CrmMatchKpis
    sources: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class CrmMatchDecisionRequest(BaseModel):
    action: CrmMatchAction
    notes: str | None = Field(default=None, max_length=4000)
