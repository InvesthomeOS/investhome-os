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
