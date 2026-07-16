"""Pydantic schemas for inventory reservations."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from investhome_api.models.inventory import (
    ReservationRecordStatus,
    ReservationSource,
    ReservationType,
)


class SoftHoldCreate(BaseModel):
    inventory_asset_id: UUID
    investor_id: UUID | None = None
    lead_id: UUID | None = None
    expires_at: datetime | None = None
    deposit_amount: Decimal | None = Field(default=None, ge=0)
    deposit_currency: str | None = Field(default=None, min_length=3, max_length=3)
    notes: str | None = None
    source: ReservationSource = ReservationSource.MANUAL

    @model_validator(mode="after")
    def require_party(self) -> "SoftHoldCreate":
        if self.investor_id is None and self.lead_id is None:
            raise ValueError("inventory.errors.party_required")
        return self


class ReservationRequestCreate(BaseModel):
    notes: str | None = None
    deposit_amount: Decimal | None = Field(default=None, ge=0)
    deposit_due_at: datetime | None = None


class ReservationApprove(BaseModel):
    notes: str | None = None


class ReservationReject(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class ReservationCancel(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


class DepositPendingMark(BaseModel):
    deposit_due_at: datetime
    deposit_amount: Decimal | None = Field(default=None, ge=0)


class DepositReceivedMark(BaseModel):
    finance_transaction_id: UUID | None = None
    reference_number: str | None = Field(default=None, max_length=100)
    received_at: datetime | None = None


class ReservationConvert(BaseModel):
    notes: str | None = None


class ReservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    inventory_asset_id: UUID
    reservation_type: ReservationType
    status: ReservationRecordStatus
    source: ReservationSource
    investor_id: UUID | None
    lead_id: UUID | None
    reserved_by_user_id: UUID | None
    approved_by_user_id: UUID | None
    expires_at: datetime | None
    deposit_due_at: datetime | None
    deposit_amount: Decimal | None
    deposit_currency: str | None
    finance_transaction_id: UUID | None
    extension_count: int
    notes: str | None
    cancellation_reason: str | None
    requested_at: datetime | None
    approved_at: datetime | None
    deposit_received_at: datetime | None
    converted_at: datetime | None
    expired_at: datetime | None
    cancelled_at: datetime | None
    released_at: datetime | None
    is_demo: bool
    created_at: datetime
    updated_at: datetime
    # Enriched fields (optional)
    asset_display_id: str | None = None
    asset_system_code: str | None = None
    party_name: str | None = None
    seconds_until_expiry: int | None = None
    valid_actions: list[str] = Field(default_factory=list)


class ReservationEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reservation_id: UUID
    event_type: str
    from_status: str | None
    to_status: str
    actor_user_id: UUID | None
    notes: str | None
    created_at: datetime


class ReservationListResponse(BaseModel):
    items: list[ReservationResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ReservationHistoryResponse(BaseModel):
    reservation: ReservationResponse
    events: list[ReservationEventResponse]
