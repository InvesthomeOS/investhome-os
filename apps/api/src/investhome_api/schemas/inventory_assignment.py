"""Inventory assignment API schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.inventory import (
    AssignmentApprovalDecision,
    AssignmentRecordStatus,
    AssignmentRequestStatus,
    AssignmentRequestType,
    AssignmentType,
)


class AssignmentRequestCreate(BaseModel):
    child_asset_id: UUID
    parent_asset_id: UUID | None = None
    request_type: AssignmentRequestType | None = None
    effective_date: date
    reason: str = Field(min_length=1)
    assignment_price: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    supporting_document_id: UUID | None = None
    related_transaction_id: UUID | None = None
    assigned_approver_user_id: UUID | None = None
    submit: bool = False


class AssignmentRequestUpdate(BaseModel):
    parent_asset_id: UUID | None = None
    effective_date: date | None = None
    reason: str | None = Field(default=None, min_length=1)
    assignment_price: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    supporting_document_id: UUID | None = None
    related_transaction_id: UUID | None = None
    assigned_approver_user_id: UUID | None = None


class AssignmentDecisionInput(BaseModel):
    comments: str | None = None
    decision_notes: str | None = None


class AssignmentRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    child_asset_id: UUID
    child_display_id: str | None = None
    parent_asset_id: UUID
    parent_display_id: str | None = None
    assignment_type: AssignmentType
    status: AssignmentRecordStatus
    effective_from: date
    effective_to: date | None
    assignment_price: Decimal | None
    currency: str
    supporting_document_id: UUID | None
    related_transaction_id: UUID | None
    notes: str | None
    created_by_user_id: UUID | None
    approved_by_user_id: UUID | None
    assignment_request_id: UUID | None
    created_at: datetime
    updated_at: datetime


class AssignmentApprovalRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reviewer_user_id: UUID
    decision: AssignmentApprovalDecision
    comments: str | None
    created_at: datetime


class AssignmentRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    child_asset_id: UUID
    child_display_id: str | None = None
    parent_asset_id: UUID | None
    parent_display_id: str | None = None
    project_name: str | None = None
    request_type: AssignmentRequestType
    assignment_type: AssignmentType
    effective_date: date
    reason: str
    assignment_price: Decimal | None
    currency: str
    supporting_document_id: UUID | None
    related_transaction_id: UUID | None
    requested_by_user_id: UUID
    assigned_approver_user_id: UUID | None
    status: AssignmentRequestStatus
    reviewed_at: datetime | None
    approved_at: datetime | None
    rejected_at: datetime | None
    decision_notes: str | None
    actions: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class AssignmentRequestListResponse(BaseModel):
    items: list[AssignmentRequestResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AssignmentSummaryResponse(BaseModel):
    assigned_to_display_id: str | None
    assigned_to_asset_id: str | None
    assignment_status: str
    assignment_type: str | None
    parking_count: int
    storage_count: int
    has_scheduled: bool
    has_pending: bool


class AssetAssignmentDetailResponse(BaseModel):
    child_asset_id: UUID
    current: AssignmentRecordResponse | None
    history: list[AssignmentRecordResponse]
    pending_requests: list[AssignmentRequestResponse]
    scheduled_requests: list[AssignmentRequestResponse]
    parent_accessories: list[AssignmentRecordResponse] = Field(default_factory=list)
