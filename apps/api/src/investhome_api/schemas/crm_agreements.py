"""CRM Agreement Pydantic schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.crm_agreement import CrmAgreementStatus
from investhome_api.services.crm.bitrix_project_aliases import BITRIX_PROJECT_GROUP_LABELS


class CrmAgreementSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    contact_id: UUID
    contact_name: str | None = None
    project_id: UUID | None = None
    project_group: str
    project_group_label: str
    source: str
    source_external_id: str | None = None
    status: CrmAgreementStatus
    agreement_date: date | None = None
    unit_number: str | None = None
    investment_amount: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    review_required: bool = False
    created_at: datetime
    updated_at: datetime
    purchase_card_enabled: bool = True
    owners_label: str | None = None
    bitrix_deal_id: str | None = None
    amount_label: str | None = None
    stage_label: str | None = None
    participants: list["CrmAgreementParticipantSummary"] = Field(default_factory=list)


class CrmAgreementParticipantSummary(BaseModel):
    contact_id: UUID
    display_name: str
    role: str = "owner"
    ownership_pct: str | None = None
    is_primary: bool = False
    source: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    company: str | None = None
    position: str | None = None
    responsible: str | None = None


class CrmPurchaseDocument(BaseModel):
    id: UUID
    title: str
    original_file_name: str | None = None
    bitrix_file_id: str | None = None
    bitrix_entity_type: str | None = None
    bitrix_entity_id: str | None = None
    document_type: str | None = None
    mime_type: str | None = None
    source: str | None = None
    created_at: datetime | None = None


class CrmLabeledValue(BaseModel):
    label: str
    value: str


class CrmRelatedPurchase(BaseModel):
    agreement_id: UUID
    project_label: str
    unit_number: str | None = None
    amount_label: str | None = None
    owners_label: str | None = None
    is_current: bool = False


class CrmPurchaseCard(BaseModel):
    agreement_id: UUID
    bitrix_deal_id: str | None = None
    project_group: str
    project_label: str
    unit_number: str | None = None
    amount: str | None = None
    currency: str | None = None
    amount_label: str | None = None
    stage: str | None = None
    begin_date: str | None = None
    close_date: str | None = None
    status: CrmAgreementStatus
    primary_contact_id: UUID
    owners_label: str | None = None
    participants: list[CrmAgreementParticipantSummary] = Field(default_factory=list)
    payment: dict[str, Any] = Field(default_factory=dict)
    history: list[Any] = Field(default_factory=list)
    history_count: int = 0
    documents: list[CrmPurchaseDocument] = Field(default_factory=list)
    document_count: int = 0
    responsible_name: str | None = None
    comments: str | None = None
    agreement_date: date | None = None
    related_purchases: list[CrmRelatedPurchase] = Field(default_factory=list)
    primary_contact_name: str | None = None
    llc_name: str | None = None
    payment_fields: list[CrmLabeledValue] = Field(default_factory=list)
    llc_fields: list[CrmLabeledValue] = Field(default_factory=list)
    extra_fields: list[CrmLabeledValue] = Field(default_factory=list)


class CrmAgreementListResponse(BaseModel):
    items: list[CrmAgreementSummary]
    page: int
    page_size: int
    total: int
    pages: int
    request_id: str = ""
    project_groups: list[dict[str, str]] = Field(default_factory=list)


def agreement_project_group_options() -> list[dict[str, str]]:
    return [
        {"id": group.value, "label": label}
        for group, label in BITRIX_PROJECT_GROUP_LABELS.items()
    ]
