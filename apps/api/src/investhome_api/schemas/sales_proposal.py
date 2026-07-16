"""Pydantic schemas for sales proposals."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.sales_proposal import (
    ProposalActivityType,
    ProposalApprovalDecision,
    ProposalRecipientType,
    ProposalStatus,
)


class SalesProposalCreate(BaseModel):
    opportunity_id: UUID
    title: str = Field(min_length=1, max_length=255)
    lead_id: UUID | None = None
    party_id: UUID | None = None
    currency: str = Field(default="USD", min_length=3, max_length=3)
    valid_until: date | None = None
    primary_project_id: UUID | None = None
    assigned_sales_user_id: UUID | None = None
    notes: str | None = None
    recipient_email: str | None = Field(default=None, max_length=255)
    language: str = Field(default="en", max_length=10)
    content_snapshot: dict | None = None
    terms_snapshot: dict | None = None
    branding_snapshot: dict | None = None


class SalesProposalUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    valid_until: date | None = None
    primary_project_id: UUID | None = None
    assigned_sales_user_id: UUID | None = None
    notes: str | None = None
    content_snapshot: dict | None = None
    terms_snapshot: dict | None = None
    branding_snapshot: dict | None = None


class SalesProposalItemCreate(BaseModel):
    inventory_asset_id: UUID
    approved_price_id: UUID | None = None
    item_title: str | None = Field(default=None, max_length=255)
    displayed_amount: Decimal | None = None
    promotional_terms: str | None = None
    payment_terms: str | None = None
    estimated_rent: Decimal | None = None
    selected_documents: list | None = None
    selected_media: list | None = None
    notes: str | None = None
    sort_order: int | None = None


class SalesProposalItemUpdate(BaseModel):
    approved_price_id: UUID | None = None
    item_title: str | None = Field(default=None, max_length=255)
    displayed_amount: Decimal | None = None
    promotional_terms: str | None = None
    payment_terms: str | None = None
    estimated_rent: Decimal | None = None
    selected_documents: list | None = None
    selected_media: list | None = None
    notes: str | None = None
    sort_order: int | None = None


class SalesProposalItemReorderEntry(BaseModel):
    item_id: UUID
    sort_order: int


class SalesProposalRecipientCreate(BaseModel):
    party_id: UUID | None = None
    recipient_type: ProposalRecipientType = ProposalRecipientType.CC
    email_snapshot: str | None = Field(default=None, max_length=255)
    language: str = Field(default="en", max_length=10)


class ProposalReviewRequest(BaseModel):
    decision: ProposalApprovalDecision
    comments: str | None = None


class ShortlistImportRequest(BaseModel):
    shortlist_id: UUID


class SalesProposalItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    proposal_version_id: UUID
    inventory_asset_id: UUID
    sort_order: int
    item_title: str | None
    approved_price_id: UUID
    displayed_amount: Decimal
    currency: str
    promotional_terms: str | None
    payment_terms: str | None
    estimated_rent: Decimal | None
    selected_documents: list | None
    selected_media: list | None
    notes: str | None


class SalesProposalVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    proposal_id: UUID
    version_number: int
    source_shortlist_id: UUID | None
    content_snapshot: dict | None
    pricing_snapshot: dict | None
    terms_snapshot: dict | None
    branding_snapshot: dict | None
    generated_document_id: UUID | None
    is_approved: bool
    approved_at: datetime | None
    created_by_user_id: UUID | None
    created_at: datetime


class SalesProposalRecipientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    proposal_id: UUID
    party_id: UUID | None
    recipient_type: ProposalRecipientType
    is_primary: bool
    email_snapshot: str | None
    language: str
    created_at: datetime


class SalesProposalApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    proposal_id: UUID
    proposal_version_id: UUID
    reviewer_user_id: UUID | None
    decision: ProposalApprovalDecision
    comments: str | None
    created_at: datetime


class SalesProposalActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    proposal_id: UUID
    activity_type: ProposalActivityType
    actor_user_id: UUID | None
    metadata_json: dict | None
    created_at: datetime


class SalesProposalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    opportunity_id: UUID
    lead_id: UUID | None
    party_id: UUID | None
    title: str
    proposal_number: str
    status: ProposalStatus
    currency: str
    valid_until: date | None
    primary_project_id: UUID | None
    current_version_id: UUID | None
    created_by_user_id: UUID | None
    assigned_sales_user_id: UUID | None
    approved_by_user_id: UUID | None
    approved_at: datetime | None
    sent_at: datetime | None
    viewed_at: datetime | None
    accepted_at: datetime | None
    rejected_at: datetime | None
    expired_at: datetime | None
    superseded_by_proposal_id: UUID | None
    notes: str | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SalesProposalDetailResponse(SalesProposalResponse):
    current_version: SalesProposalVersionResponse | None = None
    items: list[SalesProposalItemResponse] = Field(default_factory=list)
    recipients: list[SalesProposalRecipientResponse] = Field(default_factory=list)
    stale_check: dict | None = None


class SalesProposalListResponse(BaseModel):
    items: list[SalesProposalResponse]
    total: int
    offset: int
    limit: int


class StaleCheckResponse(BaseModel):
    has_stale: bool
    items: list[dict]


class ProposalExecutiveSummaryResponse(BaseModel):
    by_status: dict[str, int]
    value_by_currency: dict[str, str]
    expiring_soon: int
    pending_review: int


class ProposalHtmlResponse(BaseModel):
    html: str
    proposal_number: str
    version_number: int
