"""Branch management API schemas."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.branch import (
    BranchAssetStatus,
    BranchAssetType,
    BranchDocumentType,
    BranchStatus,
    BranchType,
)


class BranchWorkingHoursBase(BaseModel):
    business_days: dict | None = None
    open_time: str | None = Field(default=None, max_length=10)
    close_time: str | None = Field(default=None, max_length=10)
    holidays: list | None = None
    special_hours: list | None = None


class BranchWorkingHoursResponse(BranchWorkingHoursBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    branch_id: UUID
    created_at: datetime
    updated_at: datetime


class BranchAssetBase(BaseModel):
    asset_type: BranchAssetType
    name: str = Field(min_length=1, max_length=255)
    status: BranchAssetStatus = BranchAssetStatus.ACTIVE
    notes: str | None = None


class BranchAssetCreate(BranchAssetBase):
    pass


class BranchAssetUpdate(BaseModel):
    asset_type: BranchAssetType | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    status: BranchAssetStatus | None = None
    notes: str | None = None


class BranchAssetResponse(BranchAssetBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    branch_id: UUID
    created_at: datetime
    updated_at: datetime


class BranchDocumentBase(BaseModel):
    document_type: BranchDocumentType = BranchDocumentType.OTHER
    title: str = Field(min_length=1, max_length=255)
    document_id: UUID | None = None
    reference_number: str | None = Field(default=None, max_length=100)
    expiry_date: date | None = None
    notes: str | None = None


class BranchDocumentCreate(BranchDocumentBase):
    pass


class BranchDocumentResponse(BranchDocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    branch_id: UUID
    created_at: datetime
    updated_at: datetime


class BranchBase(BaseModel):
    branch_code: str = Field(min_length=1, max_length=50)
    branch_name: str = Field(min_length=1, max_length=255)
    company_id: UUID
    branch_type: BranchType = BranchType.OTHER
    country: str = Field(min_length=1, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    city: str = Field(min_length=1, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=30)
    full_address: str = Field(min_length=1, max_length=500)
    latitude: float | None = None
    longitude: float | None = None
    google_maps_link: str | None = Field(default=None, max_length=1000)
    timezone: str | None = Field(default=None, max_length=64)
    main_phone: str | None = Field(default=None, max_length=50)
    mobile_phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    website: str | None = Field(default=None, max_length=500)
    emergency_contact: str | None = Field(default=None, max_length=255)
    manager_user_id: UUID | None = None
    status: BranchStatus = BranchStatus.PLANNING
    opening_date: date | None = None
    department_count: int = Field(default=0, ge=0)
    notes: str | None = None
    working_hours: BranchWorkingHoursBase | None = None


class BranchCreate(BranchBase):
    pass


class BranchUpdate(BaseModel):
    branch_code: str | None = Field(default=None, min_length=1, max_length=50)
    branch_name: str | None = Field(default=None, min_length=1, max_length=255)
    company_id: UUID | None = None
    branch_type: BranchType | None = None
    country: str | None = Field(default=None, min_length=1, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=30)
    full_address: str | None = Field(default=None, min_length=1, max_length=500)
    latitude: float | None = None
    longitude: float | None = None
    google_maps_link: str | None = Field(default=None, max_length=1000)
    timezone: str | None = Field(default=None, max_length=64)
    main_phone: str | None = Field(default=None, max_length=50)
    mobile_phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    website: str | None = Field(default=None, max_length=500)
    emergency_contact: str | None = Field(default=None, max_length=255)
    manager_user_id: UUID | None = None
    status: BranchStatus | None = None
    opening_date: date | None = None
    department_count: int | None = Field(default=None, ge=0)
    notes: str | None = None
    working_hours: BranchWorkingHoursBase | None = None


class BranchSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    branch_code: str
    branch_name: str
    company_id: UUID
    company_name: str | None = None
    branch_type: str
    country: str
    state: str | None
    city: str
    status: str
    manager_user_id: UUID | None
    manager_name: str | None = None
    employee_count: int = 0
    department_count: int
    opening_date: date | None
    created_at: datetime
    updated_at: datetime


class BranchDetailResponse(BranchSummaryResponse):
    district: str | None
    postal_code: str | None
    full_address: str
    latitude: float | None
    longitude: float | None
    google_maps_link: str | None
    timezone: str | None
    main_phone: str | None
    mobile_phone: str | None
    email: str | None
    website: str | None
    emergency_contact: str | None
    notes: str | None
    archived_at: datetime | None
    working_hours: BranchWorkingHoursResponse | None = None
    assets: list[BranchAssetResponse] = Field(default_factory=list)
    documents: list[BranchDocumentResponse] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class BranchListResponse(BaseModel):
    items: list[BranchSummaryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class BranchMutationResponse(BaseModel):
    branch: BranchDetailResponse
    warnings: list[str] = Field(default_factory=list)


class AssignManagerRequest(BaseModel):
    manager_user_id: UUID | None = None


class TransferEmployeesRequest(BaseModel):
    target_branch_id: UUID
    employee_user_ids: list[UUID] = Field(default_factory=list)
    notes: str | None = None


class BranchEmployeeSummary(BaseModel):
    user_id: UUID
    full_name: str
    email: str
    status: str


class BranchEmployeesResponse(BaseModel):
    items: list[BranchEmployeeSummary]
    total: int
    stub: bool = True


class BranchImportRow(BaseModel):
    branch_code: str
    branch_name: str
    company_id: UUID
    branch_type: BranchType = BranchType.OTHER
    country: str
    city: str
    full_address: str
    status: BranchStatus = BranchStatus.PLANNING


class BranchImportRequest(BaseModel):
    rows: list[BranchImportRow]


class BranchImportResponse(BaseModel):
    created: int
    skipped: int
    errors: list[str] = Field(default_factory=list)
