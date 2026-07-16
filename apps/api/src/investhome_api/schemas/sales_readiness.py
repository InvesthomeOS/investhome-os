"""Sales readiness API schemas."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.sales_readiness import (
    ReadinessCaseStatus,
    ReadinessRequirementStatus,
    ReadinessRequirementType,
    ReadinessSourceEntityType,
    ReadinessTemplateGroup,
)


class ReadinessRequirementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    readiness_case_id: UUID
    requirement_type: ReadinessRequirementType
    template_group: ReadinessTemplateGroup | None
    title: str
    description: str | None
    status: ReadinessRequirementStatus
    is_mandatory: bool
    source_entity_type: ReadinessSourceEntityType | None
    source_entity_id: UUID | None
    due_at: datetime | None
    verified_at: datetime | None
    verified_by_user_id: UUID | None
    waiver_reason: str | None
    blocked_reason: str | None
    notes: str | None
    last_sync_event: str | None
    created_at: datetime
    updated_at: datetime


class ReadinessStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    readiness_case_id: UUID
    previous_status: str | None
    new_status: str
    reason: str | None
    changed_by_user_id: UUID | None
    effective_at: datetime
    created_at: datetime


class DepositSummaryResponse(BaseModel):
    reservation_id: str | None
    deposit_amount: str | None
    received_amount: str | None
    remaining_amount: str | None
    currency: str | None
    due_at: str | None
    is_overdue: bool
    finance_transaction_id: str | None
    status: str


class ReadinessCaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    case_code: str
    opportunity_id: UUID
    lead_id: UUID | None
    party_id: UUID | None
    inventory_asset_id: UUID | None
    reservation_id: UUID | None
    proposal_id: UUID | None
    status: ReadinessCaseStatus
    readiness_percentage: int
    target_contract_date: date | None
    target_closing_handoff_date: date | None
    assigned_sales_user_id: UUID | None
    assigned_manager_user_id: UUID | None
    assigned_legal_user_id: UUID | None
    assigned_finance_user_id: UUID | None
    blocker_summary: str | None
    notes: str | None
    handoff_requested_at: datetime | None
    handoff_approved_at: datetime | None
    handoff_return_reason: str | None
    signature_status: str | None
    signed_document_id: UUID | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    requirements: list[ReadinessRequirementResponse] = Field(default_factory=list)
    deposit_summary: DepositSummaryResponse | None = None
    opportunity_code: str | None = None
    party_name: str | None = None
    inventory_display_id: str | None = None
    missing_mandatory_count: int = 0


class ReadinessCaseListResponse(BaseModel):
    items: list[ReadinessCaseResponse]
    total: int
    offset: int
    limit: int


class ReadinessDashboardKpisResponse(BaseModel):
    active_cases: int
    blocked: int
    reservation_approved: int
    deposit_pending: int
    deposit_received: int
    documents_missing: int
    contract_preparation: int
    signature_pending: int
    ready_for_handoff: int
    handed_off_this_month: int


class CreateReadinessCaseRequest(BaseModel):
    inventory_asset_id: UUID | None = None
    reservation_id: UUID | None = None
    proposal_id: UUID | None = None
    project_id: UUID | None = None
    target_contract_date: date | None = None
    target_closing_handoff_date: date | None = None
    assigned_sales_user_id: UUID | None = None
    assigned_manager_user_id: UUID | None = None
    assigned_legal_user_id: UUID | None = None
    assigned_finance_user_id: UUID | None = None
    notes: str | None = None


class UpdateReadinessCaseRequest(BaseModel):
    assigned_sales_user_id: UUID | None = None
    assigned_manager_user_id: UUID | None = None
    assigned_legal_user_id: UUID | None = None
    assigned_finance_user_id: UUID | None = None
    target_contract_date: date | None = None
    target_closing_handoff_date: date | None = None
    notes: str | None = None
    signature_status: str | None = None
    signed_document_id: UUID | None = None


class VerifyRequirementRequest(BaseModel):
    notes: str | None = None


class RejectRequirementRequest(BaseModel):
    reason: str


class WaiveRequirementRequest(BaseModel):
    reason: str


class ReopenRequirementRequest(BaseModel):
    reason: str | None = None


class LinkSourceRequest(BaseModel):
    source_entity_type: ReadinessSourceEntityType
    source_entity_id: UUID


class AddRequirementRequest(BaseModel):
    requirement_type: ReadinessRequirementType
    template_group: ReadinessTemplateGroup | None = None
    title: str
    description: str | None = None
    is_mandatory: bool = False
    due_at: datetime | None = None


class HandoffRequestPayload(BaseModel):
    notes: str | None = None


class HandoffApprovePayload(BaseModel):
    notes: str | None = None


class HandoffReturnPayload(BaseModel):
    reason: str


class ContractSignedPayload(BaseModel):
    signed_document_id: UUID | None = None


class CancelCasePayload(BaseModel):
    reason: str | None = None


class CreateFollowUpFromReadinessRequest(BaseModel):
    follow_up_type: str = "deposit_follow_up"
    title: str | None = None
    due_at: datetime | None = None
    notes: str | None = None
