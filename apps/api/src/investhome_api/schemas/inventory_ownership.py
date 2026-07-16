"""Inventory ownership API schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.inventory import (
    AcquisitionMethod,
    OwnershipApprovalDecision,
    OwnershipRecordStatus,
    OwnershipSource,
    OwnershipType,
    TransferPartyRole,
    TransferRequestStatus,
    TransferType,
)


class TransferPartyInput(BaseModel):
    party_id: UUID
    ownership_type: OwnershipType
    previous_percentage: Decimal | None = None
    proposed_percentage: Decimal = Field(..., ge=Decimal("0.0001"), le=Decimal("100"))
    role: TransferPartyRole
    notes: str | None = None


class OwnershipTransferRequestCreate(BaseModel):
    inventory_asset_id: UUID
    transfer_type: TransferType
    effective_date: date
    reason: str = Field(min_length=1)
    parties: list[TransferPartyInput] = Field(min_length=1)
    supporting_document_id: UUID | None = None
    related_transaction_id: UUID | None = None
    assigned_approver_user_id: UUID | None = None
    submit: bool = False


class OwnershipTransferRequestUpdate(BaseModel):
    effective_date: date | None = None
    reason: str | None = Field(default=None, min_length=1)
    parties: list[TransferPartyInput] | None = None
    supporting_document_id: UUID | None = None
    related_transaction_id: UUID | None = None
    assigned_approver_user_id: UUID | None = None


class TransferPartyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    party_id: UUID
    party_name: str | None = None
    party_type: str | None = None
    ownership_type: OwnershipType
    previous_percentage: Decimal | None
    proposed_percentage: Decimal
    role: TransferPartyRole
    notes: str | None
    created_at: datetime


class OwnershipApprovalRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reviewer_user_id: UUID
    decision: OwnershipApprovalDecision
    comments: str | None
    created_at: datetime


class OwnershipTransferRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    inventory_asset_id: UUID
    asset_display_id: str | None = None
    project_name: str | None = None
    transfer_type: TransferType
    effective_date: date
    reason: str
    supporting_document_id: UUID | None
    related_transaction_id: UUID | None
    requested_by_user_id: UUID
    assigned_approver_user_id: UUID | None
    status: TransferRequestStatus
    reviewed_at: datetime | None
    approved_at: datetime | None
    rejected_at: datetime | None
    decision_notes: str | None
    parties: list[TransferPartyResponse] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    proposed_legal_total: Decimal | None = None
    current_legal_total: Decimal | None = None
    created_at: datetime
    updated_at: datetime


class OwnershipTransferRequestListResponse(BaseModel):
    items: list[OwnershipTransferRequestResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class OwnershipRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    inventory_asset_id: UUID
    party_id: UUID
    party_name: str | None = None
    party_type: str | None = None
    ownership_type: OwnershipType
    ownership_percentage: Decimal
    effective_from: date
    effective_to: date | None
    status: OwnershipRecordStatus
    acquisition_method: AcquisitionMethod
    transfer_reason: str | None
    related_document_id: UUID | None
    related_transaction_id: UUID | None
    source: OwnershipSource
    notes: str | None
    created_by_user_id: UUID | None
    approved_by_user_id: UUID | None
    ownership_transfer_request_id: UUID | None
    created_at: datetime
    updated_at: datetime


class AssetOwnershipDetailResponse(BaseModel):
    asset_id: UUID
    current_legal: list[OwnershipRecordResponse]
    current_beneficial: list[OwnershipRecordResponse]
    current_economic: list[OwnershipRecordResponse]
    current_other: list[OwnershipRecordResponse]
    pending_requests: list[OwnershipTransferRequestResponse]
    scheduled_transfers: list[OwnershipTransferRequestResponse]
    history: list[OwnershipRecordResponse]
    legal_total: Decimal
    proposed_legal_total: Decimal | None = None


class OwnershipSummaryResponse(BaseModel):
    primary_legal_owner: str | None
    owner_count: int
    ownership_status: str


class OwnershipDecisionInput(BaseModel):
    comments: str | None = None
    decision_notes: str | None = None


class OwnershipPreviewResponse(BaseModel):
    current_legal_total: Decimal
    proposed_legal_total: Decimal
    valid: bool
    errors: list[str] = Field(default_factory=list)
    outgoing: list[TransferPartyResponse] = Field(default_factory=list)
    incoming: list[TransferPartyResponse] = Field(default_factory=list)
    continuing: list[TransferPartyResponse] = Field(default_factory=list)
