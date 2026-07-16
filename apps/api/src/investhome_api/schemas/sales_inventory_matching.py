"""Pydantic schemas for sales inventory matching."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.sales_inventory_matching import (
    MatchRejectionReason,
    MatchRelationshipType,
    MatchSource,
    MatchStatus,
    ShortlistStatus,
)


class PreferenceSave(BaseModel):
    lead_id: UUID | None = None
    opportunity_id: UUID | None = None
    budget_min: Decimal | None = Field(default=None, ge=0)
    budget_max: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    bedrooms_min: int | None = Field(default=None, ge=0)
    bedrooms_max: int | None = Field(default=None, ge=0)
    bathrooms_min: int | None = Field(default=None, ge=0)
    bathrooms_max: int | None = Field(default=None, ge=0)
    area_min: Decimal | None = Field(default=None, ge=0)
    area_max: Decimal | None = Field(default=None, ge=0)
    floor_min: int | None = None
    floor_max: int | None = None
    delivery_date_before: date | None = None
    notes: str | None = None
    preferred_project_ids: list[UUID] = Field(default_factory=list)
    preferred_asset_types: list[str] = Field(default_factory=list)
    preferred_usage_types: list[str] = Field(default_factory=list)
    preferred_building_ids: list[UUID] = Field(default_factory=list)


class PreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID | None
    opportunity_id: UUID | None
    budget_min: Decimal | None
    budget_max: Decimal | None
    currency: str
    bedrooms_min: int | None
    bedrooms_max: int | None
    bathrooms_min: int | None
    bathrooms_max: int | None
    area_min: Decimal | None
    area_max: Decimal | None
    floor_min: int | None
    floor_max: int | None
    delivery_date_before: date | None
    notes: str | None
    preferred_project_ids: list[UUID] = Field(default_factory=list)
    preferred_asset_types: list[str] = Field(default_factory=list)
    preferred_usage_types: list[str] = Field(default_factory=list)
    preferred_building_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class InventorySearchRequest(BaseModel):
    lead_id: UUID | None = None
    opportunity_id: UUID | None = None
    project_id: UUID | None = None
    building_id: UUID | None = None
    asset_type: str | None = None
    usage_type: str | None = None
    availability_status: str | None = "available"
    bedrooms_min: int | None = None
    bedrooms_max: int | None = None
    area_min: Decimal | None = None
    area_max: Decimal | None = None
    budget_min: Decimal | None = None
    budget_max: Decimal | None = None
    search: str | None = Field(default=None, max_length=255)
    exclude_rejected: bool = True
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class InventorySearchResultItem(BaseModel):
    asset_id: UUID
    display_id: str | None
    system_code: str | None
    project_id: UUID
    asset_type: str
    usage_type: str
    availability_status: str
    reservation_status: str
    sales_status: str
    bedrooms: int | None
    bathrooms: int | None
    interior_area_sqft: Decimal | None
    list_price: str | None
    currency: str
    is_stale: bool = False
    existing_match_id: UUID | None = None
    relationship_type: MatchRelationshipType | None = None


class InventorySearchResponse(BaseModel):
    items: list[InventorySearchResultItem]
    total: int
    page: int
    page_size: int


class MatchCreate(BaseModel):
    lead_id: UUID | None = None
    opportunity_id: UUID | None = None
    inventory_asset_id: UUID
    relationship_type: MatchRelationshipType = MatchRelationshipType.MATCHED
    match_source: MatchSource = MatchSource.MANUAL
    match_score: int | None = Field(default=None, ge=0, le=100)
    match_reason: str | None = Field(default=None, max_length=255)


class MatchUpdate(BaseModel):
    relationship_type: MatchRelationshipType | None = None
    match_reason: str | None = Field(default=None, max_length=255)
    status: MatchStatus | None = None


class MatchReject(BaseModel):
    rejection_reason: MatchRejectionReason
    notes: str | None = Field(default=None, max_length=500)


class MatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID | None
    opportunity_id: UUID | None
    inventory_asset_id: UUID
    relationship_type: MatchRelationshipType
    status: MatchStatus
    match_source: MatchSource
    match_score: int | None
    match_reason: str | None
    rejection_reason: MatchRejectionReason | None
    is_primary: bool
    inventory_snapshot: dict | None
    is_stale: bool = False
    stale_fields: list[str] = Field(default_factory=list)
    created_by_user_id: UUID | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    asset_display_id: str | None = None
    list_price: str | None = None


class MatchListResponse(BaseModel):
    items: list[MatchResponse]
    total: int


class ShortlistCreate(BaseModel):
    lead_id: UUID | None = None
    opportunity_id: UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: ShortlistStatus = ShortlistStatus.DRAFT


class ShortlistUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: ShortlistStatus | None = None


class ShortlistItemCreate(BaseModel):
    inventory_asset_id: UUID
    notes: str | None = None
    is_favorite: bool = False


class ShortlistItemUpdate(BaseModel):
    notes: str | None = None
    is_favorite: bool | None = None
    sort_order: int | None = None


class ShortlistItemReorder(BaseModel):
    item_ids: list[UUID] = Field(min_length=1)


class ShortlistItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shortlist_id: UUID
    inventory_asset_id: UUID
    sort_order: int
    notes: str | None
    is_favorite: bool
    inventory_snapshot: dict | None
    is_stale: bool = False
    stale_fields: list[str] = Field(default_factory=list)
    asset_display_id: str | None = None
    list_price: str | None = None
    availability_status: str | None = None


class ShortlistResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID | None
    opportunity_id: UUID | None
    title: str
    description: str | None
    status: ShortlistStatus
    created_by_user_id: UUID | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    items: list[ShortlistItemResponse] = Field(default_factory=list)


class ShortlistListResponse(BaseModel):
    items: list[ShortlistResponse]
    total: int


class CompareRequest(BaseModel):
    asset_ids: list[UUID] = Field(min_length=2, max_length=5)


class CompareAssetItem(BaseModel):
    asset_id: UUID
    display_id: str | None
    system_code: str | None
    asset_type: str
    usage_type: str
    bedrooms: int | None
    bathrooms: int | None
    interior_area_sqft: Decimal | None
    availability_status: str
    reservation_status: str
    sales_status: str
    list_price: str | None
    currency: str
    project_name: str | None = None
    building_code: str | None = None
    floor_label: str | None = None


class CompareResponse(BaseModel):
    items: list[CompareAssetItem]


class SoftHoldRequest(BaseModel):
    inventory_asset_id: UUID
    lead_id: UUID | None = None
    opportunity_id: UUID | None = None
    notes: str | None = None
    deposit_amount: Decimal | None = None


class ReservationRequestPayload(BaseModel):
    reservation_id: UUID
    notes: str | None = None
    deposit_amount: Decimal | None = None


class StaleCheckRequest(BaseModel):
    asset_ids: list[UUID] = Field(min_length=1, max_length=50)
    snapshots: dict[str, dict] = Field(default_factory=dict)


class StaleCheckItem(BaseModel):
    asset_id: UUID
    is_stale: bool
    stale_fields: list[str] = Field(default_factory=list)
    current: dict


class StaleCheckResponse(BaseModel):
    items: list[StaleCheckItem]


class InventoryMatchingExecutiveSummary(BaseModel):
    opportunities_without_match: int
    opportunities_with_shortlist: int
    opportunities_primary_selected: int
    shortlisted_unavailable: int
    match_to_reservation_count: int
