"""Inventory domain models — buildings, floors, inventory assets."""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


class BuildingType(str, enum.Enum):
    APARTMENT = "apartment"
    CONDOMINIUM = "condominium"
    MIXED_USE = "mixed_use"
    OFFICE = "office"
    RETAIL = "retail"
    TOWNHOUSE = "townhouse"
    SINGLE_FAMILY = "single_family"
    PARKING_STRUCTURE = "parking_structure"
    STORAGE = "storage"
    OTHER = "other"


class StructureStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PLANNED = "planned"
    UNDER_CONSTRUCTION = "under_construction"


class InventoryAssetType(str, enum.Enum):
    RESIDENTIAL_UNIT = "residential_unit"
    COMMERCIAL_UNIT = "commercial_unit"
    PARKING_SPACE = "parking_space"
    STORAGE_UNIT = "storage_unit"
    LAND_PARCEL = "land_parcel"
    OFFICE_UNIT = "office_unit"
    RETAIL_UNIT = "retail_unit"


class UsageType(str, enum.Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    RETAIL = "retail"
    OFFICE = "office"
    PARKING = "parking"
    STORAGE = "storage"
    INDUSTRIAL = "industrial"
    MIXED = "mixed"


class AvailabilityStatus(str, enum.Enum):
    NOT_RELEASED = "not_released"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    HOLD = "hold"


class ReservationStatus(str, enum.Enum):
    NONE = "none"
    SOFT_HOLD = "soft_hold"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ReservationType(str, enum.Enum):
    SOFT_HOLD = "soft_hold"
    RESERVATION = "reservation"


class ReservationRecordStatus(str, enum.Enum):
    ACTIVE = "active"
    REQUESTED = "requested"
    APPROVED = "approved"
    DEPOSIT_PENDING = "deposit_pending"
    DEPOSIT_RECEIVED = "deposit_received"
    CONVERTED = "converted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    RELEASED = "released"


class ReservationSource(str, enum.Enum):
    MANUAL = "manual"
    SALES = "sales"
    LEAD = "lead"
    INVESTOR = "investor"
    IMPORT = "import"


ACTIVE_RESERVATION_STATUSES = frozenset(
    {
        ReservationRecordStatus.ACTIVE,
        ReservationRecordStatus.REQUESTED,
        ReservationRecordStatus.APPROVED,
        ReservationRecordStatus.DEPOSIT_PENDING,
        ReservationRecordStatus.DEPOSIT_RECEIVED,
    }
)

TERMINAL_RESERVATION_STATUSES = frozenset(
    {
        ReservationRecordStatus.CONVERTED,
        ReservationRecordStatus.EXPIRED,
        ReservationRecordStatus.CANCELLED,
        ReservationRecordStatus.REJECTED,
        ReservationRecordStatus.RELEASED,
    }
)


class InventorySalesStatus(str, enum.Enum):
    NOT_FOR_SALE = "not_for_sale"
    AVAILABLE_FOR_SALE = "available_for_sale"
    UNDER_CONTRACT = "under_contract"
    SOLD = "sold"


class ConstructionStatus(str, enum.Enum):
    PLANNED = "planned"
    FOUNDATION = "foundation"
    STRUCTURE = "structure"
    ENVELOPE = "envelope"
    INTERIOR = "interior"
    FINISHING = "finishing"
    INSPECTION = "inspection"
    READY = "ready"
    DELIVERED = "delivered"
    ON_HOLD = "on_hold"


class ClosingStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    TITLE_CLEAR = "title_clear"
    FUNDING_PENDING = "funding_pending"
    SCHEDULED = "scheduled"
    CLOSED = "closed"
    FALLEN_THROUGH = "fallen_through"


class LeasingStatus(str, enum.Enum):
    NOT_APPLICABLE = "not_applicable"
    VACANT = "vacant"
    LISTED = "listed"
    APPLICATION = "application"
    LEASED = "leased"
    NOTICE_GIVEN = "notice_given"
    OFF_MARKET = "off_market"


class StatusCategory(str, enum.Enum):
    AVAILABILITY = "availability"
    RESERVATION = "reservation"
    SALES = "sales"
    CONSTRUCTION = "construction"
    CLOSING = "closing"
    LEASING = "leasing"


class Building(Base):
    __tablename__ = "buildings"
    __table_args__ = (
        UniqueConstraint("project_id", "code", name="uq_buildings_project_code"),
        Index("ix_buildings_project_id", "project_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    building_type: Mapped[BuildingType] = mapped_column(
        Enum(BuildingType, native_enum=False, length=50),
        nullable=False,
    )
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    total_floors: Mapped[int | None] = mapped_column(nullable=True)
    status: Mapped[StructureStatus] = mapped_column(
        Enum(StructureStatus, native_enum=False, length=50),
        nullable=False,
        default=StructureStatus.ACTIVE,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Floor(Base):
    __tablename__ = "floors"
    __table_args__ = (
        UniqueConstraint("building_id", "floor_number", name="uq_floors_building_floor_number"),
        UniqueConstraint("building_id", "level_code", name="uq_floors_building_level_code"),
        Index("ix_floors_building_id", "building_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    building_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("buildings.id", ondelete="CASCADE"),
        nullable=False,
    )
    floor_number: Mapped[int] = mapped_column(nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    level_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)
    status: Mapped[StructureStatus] = mapped_column(
        Enum(StructureStatus, native_enum=False, length=50),
        nullable=False,
        default=StructureStatus.ACTIVE,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InventoryAsset(Base):
    __tablename__ = "inventory_assets"
    __table_args__ = (
        UniqueConstraint("project_id", "display_id", name="uq_inventory_assets_project_display_id"),
        Index("ix_inventory_assets_project_id", "project_id"),
        Index("ix_inventory_assets_building_id", "building_id"),
        Index("ix_inventory_assets_floor_id", "floor_id"),
        Index("ix_inventory_assets_system_code", "system_code", unique=True),
        Index("ix_inventory_assets_availability_status", "availability_status"),
        Index("ix_inventory_assets_sales_status", "sales_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    building_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("buildings.id", ondelete="SET NULL"),
        nullable=True,
    )
    floor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("floors.id", ondelete="SET NULL"),
        nullable=True,
    )
    display_id: Mapped[str] = mapped_column(String(50), nullable=False)
    system_code: Mapped[str] = mapped_column(String(100), nullable=False)
    legal_identifier: Mapped[str | None] = mapped_column(String(100), nullable=True)
    asset_type: Mapped[InventoryAssetType] = mapped_column(
        Enum(InventoryAssetType, native_enum=False, length=50),
        nullable=False,
    )
    usage_type: Mapped[UsageType] = mapped_column(
        Enum(UsageType, native_enum=False, length=50),
        nullable=False,
    )
    unit_subtype: Mapped[str | None] = mapped_column(String(80), nullable=True)
    bedrooms: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)
    bathrooms: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)
    interior_area_sqft: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    exterior_area_sqft: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    total_area_sqft: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    orientation: Mapped[str | None] = mapped_column(String(20), nullable=True)
    view_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    availability_status: Mapped[AvailabilityStatus] = mapped_column(
        Enum(AvailabilityStatus, native_enum=False, length=50),
        nullable=False,
        default=AvailabilityStatus.NOT_RELEASED,
    )
    reservation_status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus, native_enum=False, length=50),
        nullable=False,
        default=ReservationStatus.NONE,
    )
    sales_status: Mapped[InventorySalesStatus] = mapped_column(
        Enum(InventorySalesStatus, native_enum=False, length=50),
        nullable=False,
        default=InventorySalesStatus.NOT_FOR_SALE,
    )
    construction_status: Mapped[ConstructionStatus] = mapped_column(
        Enum(ConstructionStatus, native_enum=False, length=50),
        nullable=False,
        default=ConstructionStatus.PLANNED,
    )
    closing_status: Mapped[ClosingStatus] = mapped_column(
        Enum(ClosingStatus, native_enum=False, length=50),
        nullable=False,
        default=ClosingStatus.NOT_STARTED,
    )
    leasing_status: Mapped[LeasingStatus] = mapped_column(
        Enum(LeasingStatus, native_enum=False, length=50),
        nullable=False,
        default=LeasingStatus.NOT_APPLICABLE,
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    list_price: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    promotional_price: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    active_reservation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("inventory_reservations.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InventoryReservation(Base):
    __tablename__ = "inventory_reservations"
    __table_args__ = (
        Index("ix_inventory_reservations_asset_id", "inventory_asset_id"),
        Index("ix_inventory_reservations_investor_id", "investor_id"),
        Index("ix_inventory_reservations_lead_id", "lead_id"),
        Index("ix_inventory_reservations_status", "status"),
        Index("ix_inventory_reservations_expires_at", "expires_at"),
        Index(
            "uq_inventory_reservations_active_asset",
            "inventory_asset_id",
            unique=True,
            sqlite_where=text(
                "status IN ('active', 'requested', 'approved', 'deposit_pending', 'deposit_received')"
            ),
            postgresql_where=text(
                "status IN ('active', 'requested', 'approved', 'deposit_pending', 'deposit_received')"
            ),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    inventory_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("inventory_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    reservation_type: Mapped[ReservationType] = mapped_column(
        Enum(ReservationType, native_enum=False, length=50),
        nullable=False,
    )
    status: Mapped[ReservationRecordStatus] = mapped_column(
        Enum(ReservationRecordStatus, native_enum=False, length=50),
        nullable=False,
    )
    source: Mapped[ReservationSource] = mapped_column(
        Enum(ReservationSource, native_enum=False, length=50),
        nullable=False,
        default=ReservationSource.MANUAL,
    )
    investor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("investors.id", ondelete="SET NULL"),
        nullable=True,
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
    )
    reserved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deposit_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deposit_amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    deposit_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    finance_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("finance_transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    extension_count: Mapped[int] = mapped_column(default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deposit_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    converted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class InventoryReservationEvent(Base):
    __tablename__ = "inventory_reservation_events"
    __table_args__ = (Index("ix_inventory_reservation_events_reservation_id", "reservation_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reservation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("inventory_reservations.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class PriceType(str, enum.Enum):
    ORIGINAL = "original"
    LAUNCH = "launch"
    LIST = "list"
    PROMOTIONAL = "promotional"
    RESERVATION = "reservation"
    CONTRACTED = "contracted"
    CLOSING = "closing"
    APPRAISED = "appraised"
    ESTIMATED_RENT = "estimated_rent"


SENSITIVE_PRICE_TYPES = frozenset({PriceType.CONTRACTED, PriceType.CLOSING})


class PriceStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    ACTIVE = "active"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class PriceSource(str, enum.Enum):
    INITIAL = "initial"
    MANUAL_REQUEST = "manual_request"
    PROMOTION = "promotion"
    CONTRACT = "contract"
    CLOSING = "closing"
    APPRAISAL = "appraisal"
    RENT_ESTIMATE = "rent_estimate"
    IMPORT = "import"
    OTHER = "other"


class PriceRequestStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
    APPLIED = "applied"


PENDING_PRICE_REQUEST_STATUSES = frozenset(
    {
        PriceRequestStatus.SUBMITTED,
        PriceRequestStatus.UNDER_REVIEW,
    }
)


class PriceApprovalDecision(str, enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


class InventoryAssetPrice(Base):
    __tablename__ = "inventory_asset_prices"
    __table_args__ = (
        Index("ix_inventory_asset_prices_asset_id", "inventory_asset_id"),
        Index("ix_inventory_asset_prices_type_status", "price_type", "status"),
        Index(
            "uq_inventory_asset_prices_active",
            "inventory_asset_id",
            "price_type",
            "currency",
            unique=True,
            postgresql_where="status = 'active'",
            sqlite_where="status = 'active'",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    inventory_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("inventory_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    price_type: Mapped[PriceType] = mapped_column(
        Enum(PriceType, native_enum=False, length=50),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[PriceStatus] = mapped_column(
        Enum(PriceStatus, native_enum=False, length=50),
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[PriceSource] = mapped_column(
        Enum(PriceSource, native_enum=False, length=50),
        nullable=False,
    )
    approved_request_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("price_change_requests.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PriceChangeRequest(Base):
    __tablename__ = "price_change_requests"
    __table_args__ = (
        Index("ix_price_change_requests_asset_id", "inventory_asset_id"),
        Index("ix_price_change_requests_status", "status"),
        Index("ix_price_change_requests_requester", "requested_by_user_id"),
        Index("ix_price_change_requests_approver", "assigned_approver_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    inventory_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("inventory_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    price_type: Mapped[PriceType] = mapped_column(
        Enum(PriceType, native_enum=False, length=50),
        nullable=False,
    )
    current_price_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("inventory_asset_prices.id", ondelete="SET NULL"),
        nullable=True,
    )
    current_amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    proposed_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    change_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    change_percentage: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    assigned_approver_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    status: Mapped[PriceRequestStatus] = mapped_column(
        Enum(PriceRequestStatus, native_enum=False, length=50),
        nullable=False,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PriceApprovalRecord(Base):
    __tablename__ = "price_approval_records"
    __table_args__ = (Index("ix_price_approval_records_request_id", "price_change_request_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    price_change_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("price_change_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    decision: Mapped[PriceApprovalDecision] = mapped_column(
        Enum(PriceApprovalDecision, native_enum=False, length=50),
        nullable=False,
    )
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class InventoryPriceEvent(Base):
    __tablename__ = "inventory_price_events"
    __table_args__ = (
        Index("ix_inventory_price_events_asset_id", "inventory_asset_id"),
        Index("ix_inventory_price_events_request_id", "price_change_request_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    inventory_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("inventory_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    price_change_request_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("price_change_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    inventory_asset_price_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("inventory_asset_prices.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class InventoryAssetStatusHistory(Base):
    __tablename__ = "inventory_asset_status_history"
    __table_args__ = (Index("ix_inventory_status_history_asset_id", "inventory_asset_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    inventory_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("inventory_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    status_category: Mapped[StatusCategory] = mapped_column(
        Enum(StatusCategory, native_enum=False, length=50),
        nullable=False,
    )
    previous_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    effective_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
