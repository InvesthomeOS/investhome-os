"""Pydantic schemas for inventory module."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.inventory import (
    AvailabilityStatus,
    BuildingType,
    ClosingStatus,
    ConstructionStatus,
    InventoryAssetType,
    InventorySalesStatus,
    LeasingStatus,
    ReservationStatus,
    StatusCategory,
    StructureStatus,
    UsageType,
)


class BuildingBase(BaseModel):
    project_id: UUID
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=50)
    building_type: BuildingType
    address: str | None = Field(default=None, max_length=500)
    total_floors: int | None = Field(default=None, ge=0)
    status: StructureStatus = StructureStatus.ACTIVE
    description: str | None = None


class BuildingCreate(BuildingBase):
    pass


class BuildingUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, min_length=1, max_length=50)
    building_type: BuildingType | None = None
    address: str | None = Field(default=None, max_length=500)
    total_floors: int | None = Field(default=None, ge=0)
    status: StructureStatus | None = None
    description: str | None = None


class BuildingResponse(BuildingBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_demo: bool
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class BuildingListResponse(BaseModel):
    items: list[BuildingResponse]
    total: int
    page: int
    page_size: int
    pages: int


class FloorBase(BaseModel):
    building_id: UUID
    floor_number: int
    display_name: str | None = Field(default=None, max_length=255)
    level_code: str | None = Field(default=None, max_length=50)
    sort_order: int = 0
    status: StructureStatus = StructureStatus.ACTIVE
    description: str | None = None


class FloorCreate(FloorBase):
    pass


class FloorUpdate(BaseModel):
    floor_number: int | None = None
    display_name: str | None = Field(default=None, max_length=255)
    level_code: str | None = Field(default=None, max_length=50)
    sort_order: int | None = None
    status: StructureStatus | None = None
    description: str | None = None


class FloorResponse(FloorBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_demo: bool
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class FloorListResponse(BaseModel):
    items: list[FloorResponse]
    total: int
    page: int
    page_size: int
    pages: int


class InventoryAssetBase(BaseModel):
    project_id: UUID
    building_id: UUID | None = None
    floor_id: UUID | None = None
    display_id: str = Field(min_length=1, max_length=50)
    legal_identifier: str | None = Field(default=None, max_length=100)
    asset_type: InventoryAssetType
    usage_type: UsageType
    unit_subtype: str | None = Field(default=None, max_length=80)
    bedrooms: Decimal | None = Field(default=None, ge=0)
    bathrooms: Decimal | None = Field(default=None, ge=0)
    interior_area_sqft: Decimal | None = Field(default=None, ge=0)
    exterior_area_sqft: Decimal | None = Field(default=None, ge=0)
    total_area_sqft: Decimal | None = Field(default=None, ge=0)
    orientation: str | None = Field(default=None, max_length=20)
    view_type: str | None = Field(default=None, max_length=80)
    availability_status: AvailabilityStatus = AvailabilityStatus.NOT_RELEASED
    reservation_status: ReservationStatus = ReservationStatus.NONE
    sales_status: InventorySalesStatus = InventorySalesStatus.NOT_FOR_SALE
    construction_status: ConstructionStatus = ConstructionStatus.PLANNED
    closing_status: ClosingStatus = ClosingStatus.NOT_STARTED
    leasing_status: LeasingStatus = LeasingStatus.NOT_APPLICABLE
    currency: str = Field(default="USD", min_length=3, max_length=3)
    release_date: date | None = None
    delivery_date: date | None = None
    description: str | None = None
    notes: str | None = None


class InventoryAssetCreate(InventoryAssetBase):
    pass


class InventoryAssetUpdate(BaseModel):
    building_id: UUID | None = None
    floor_id: UUID | None = None
    display_id: str | None = Field(default=None, min_length=1, max_length=50)
    legal_identifier: str | None = Field(default=None, max_length=100)
    asset_type: InventoryAssetType | None = None
    usage_type: UsageType | None = None
    unit_subtype: str | None = Field(default=None, max_length=80)
    bedrooms: Decimal | None = Field(default=None, ge=0)
    bathrooms: Decimal | None = Field(default=None, ge=0)
    interior_area_sqft: Decimal | None = Field(default=None, ge=0)
    exterior_area_sqft: Decimal | None = Field(default=None, ge=0)
    total_area_sqft: Decimal | None = Field(default=None, ge=0)
    orientation: str | None = Field(default=None, max_length=20)
    view_type: str | None = Field(default=None, max_length=80)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    release_date: date | None = None
    delivery_date: date | None = None
    description: str | None = None
    notes: str | None = None


class InventoryAssetResponse(InventoryAssetBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    system_code: str
    is_demo: bool
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class InventoryAssetListResponse(BaseModel):
    items: list[InventoryAssetResponse]
    total: int
    page: int
    page_size: int
    pages: int


class InventoryAssetStatusUpdate(BaseModel):
    status_category: StatusCategory
    new_status: str = Field(min_length=1, max_length=50)
    reason: str | None = None
    effective_at: datetime | None = None


class InventoryAssetStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    inventory_asset_id: UUID
    status_category: StatusCategory
    previous_status: str | None
    new_status: str
    reason: str | None
    changed_by_user_id: UUID | None
    effective_at: datetime
    created_at: datetime
