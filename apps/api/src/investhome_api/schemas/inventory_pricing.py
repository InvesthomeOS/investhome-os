"""Pydantic schemas for inventory pricing."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.inventory import (
    PriceApprovalDecision,
    PriceRequestStatus,
    PriceSource,
    PriceStatus,
    PriceType,
)


class InventoryAssetPriceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    inventory_asset_id: UUID
    price_type: PriceType
    amount: Decimal
    currency: str
    effective_from: date
    effective_to: date | None = None
    status: PriceStatus
    reason: str | None = None
    source: PriceSource
    approved_request_id: UUID | None = None
    created_by_user_id: UUID | None = None
    is_demo: bool
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class InitialPriceCreate(BaseModel):
    inventory_asset_id: UUID
    price_type: PriceType
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    effective_from: date
    effective_to: date | None = None
    reason: str | None = None


class PriceChangeRequestCreate(BaseModel):
    inventory_asset_id: UUID
    price_type: PriceType
    proposed_amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    effective_from: date
    effective_to: date | None = None
    reason: str = Field(min_length=1)
    supporting_document_id: UUID | None = None
    assigned_approver_user_id: UUID | None = None
    submit: bool = False


class PriceChangeRequestUpdate(BaseModel):
    proposed_amount: Decimal | None = Field(default=None, gt=0)
    effective_from: date | None = None
    effective_to: date | None = None
    reason: str | None = Field(default=None, min_length=1)
    supporting_document_id: UUID | None = None
    assigned_approver_user_id: UUID | None = None
    clear_assigned_approver: bool = False


class PriceDecisionInput(BaseModel):
    comments: str | None = None
    decision_notes: str | None = None


class PriceApprovalRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    price_change_request_id: UUID
    reviewer_user_id: UUID
    decision: PriceApprovalDecision
    comments: str | None = None
    created_at: datetime


class PriceChangeRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    inventory_asset_id: UUID
    price_type: PriceType
    current_price_id: UUID | None = None
    current_amount: Decimal | None = None
    proposed_amount: Decimal
    currency: str
    change_amount: Decimal
    change_percentage: Decimal | None = None
    effective_from: date
    effective_to: date | None = None
    reason: str
    supporting_document_id: UUID | None = None
    requested_by_user_id: UUID
    assigned_approver_user_id: UUID | None = None
    status: PriceRequestStatus
    reviewed_at: datetime | None = None
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    decision_notes: str | None = None
    is_demo: bool
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None
    asset_display_id: str | None = None
    asset_system_code: str | None = None
    project_id: UUID | None = None
    project_name: str | None = None
    is_high_impact: bool | None = None
    valid_actions: list[str] = Field(default_factory=list)


class PriceChangeRequestListResponse(BaseModel):
    items: list[PriceChangeRequestResponse]
    total: int
    page: int
    page_size: int
    pages: int


class AssetPricingSummary(BaseModel):
    list_price: str | None = None
    promotional_price: str | None = None
    contracted_price: str | None = None
    currency: str
    pending_price_requests: int = 0


class PriceHistoryEntry(BaseModel):
    price: InventoryAssetPriceResponse
    previous_amount: Decimal | None = None
    change_amount: Decimal | None = None
    change_percentage: Decimal | None = None
    approved_request_id: UUID | None = None


class AssetPricingDetailResponse(BaseModel):
    current_prices: list[InventoryAssetPriceResponse]
    pending_requests: list[PriceChangeRequestResponse]
    history: list[PriceHistoryEntry]
    approval_history: list[PriceApprovalRecordResponse]
