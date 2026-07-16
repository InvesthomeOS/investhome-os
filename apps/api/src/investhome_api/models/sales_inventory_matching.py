"""Sales inventory matching, preferences, and shortlist models."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


class MatchRelationshipType(str, enum.Enum):
    MATCHED = "matched"
    SHORTLISTED = "shortlisted"
    FAVORITE = "favorite"
    PROPOSED = "proposed"
    SELECTED = "selected"
    REJECTED = "rejected"
    SOFT_HOLD = "soft_hold"
    RESERVED = "reserved"


class MatchStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    REJECTED = "rejected"
    CONVERTED = "converted"
    ARCHIVED = "archived"


class MatchSource(str, enum.Enum):
    MANUAL = "manual"
    SAVED_FILTER = "saved_filter"
    RULE_BASED = "rule_based"
    IMPORTED = "imported"


class MatchRejectionReason(str, enum.Enum):
    BUDGET = "budget"
    SIZE = "size"
    LAYOUT = "layout"
    LOCATION = "location"
    FLOOR = "floor"
    EXPOSURE = "exposure"
    DELIVERY_TIMING = "delivery_timing"
    AVAILABILITY = "availability"
    FINANCING = "financing"
    CLIENT_PREFERENCE = "client_preference"
    OTHER = "other"


class ShortlistStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    SHARED = "shared"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class SalesInventoryPreference(Base):
    """Search criteria for inventory matching — one per lead OR opportunity."""

    __tablename__ = "sales_inventory_preferences"
    __table_args__ = (
        CheckConstraint(
            "(lead_id IS NOT NULL AND opportunity_id IS NULL) OR "
            "(lead_id IS NULL AND opportunity_id IS NOT NULL)",
            name="ck_sales_inventory_preferences_lead_xor_opportunity",
        ),
        Index("ix_sales_inventory_preferences_lead_id", "lead_id", unique=True),
        Index("ix_sales_inventory_preferences_opportunity_id", "opportunity_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=True,
    )
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("sales_opportunities.id", ondelete="CASCADE"),
        nullable=True,
    )
    budget_min: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    budget_max: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    bedrooms_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bedrooms_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bathrooms_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bathrooms_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    area_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    area_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    floor_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    floor_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivery_date_before: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SalesInventoryPreferenceProject(Base):
    __tablename__ = "sales_inventory_preference_projects"
    __table_args__ = (
        UniqueConstraint("preference_id", "project_id", name="uq_pref_project"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    preference_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sales_inventory_preferences.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )


class SalesInventoryPreferenceAssetType(Base):
    __tablename__ = "sales_inventory_preference_asset_types"
    __table_args__ = (
        UniqueConstraint("preference_id", "asset_type", name="uq_pref_asset_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    preference_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sales_inventory_preferences.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False)


class SalesInventoryPreferenceUsageType(Base):
    __tablename__ = "sales_inventory_preference_usage_types"
    __table_args__ = (
        UniqueConstraint("preference_id", "usage_type", name="uq_pref_usage_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    preference_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sales_inventory_preferences.id", ondelete="CASCADE"),
        nullable=False,
    )
    usage_type: Mapped[str] = mapped_column(String(50), nullable=False)


class SalesInventoryPreferenceBuilding(Base):
    __tablename__ = "sales_inventory_preference_buildings"
    __table_args__ = (
        UniqueConstraint("preference_id", "building_id", name="uq_pref_building"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    preference_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sales_inventory_preferences.id", ondelete="CASCADE"),
        nullable=False,
    )
    building_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("buildings.id", ondelete="CASCADE"),
        nullable=False,
    )


class SalesInventoryMatch(Base):
    __tablename__ = "sales_inventory_matches"
    __table_args__ = (
        CheckConstraint(
            "(lead_id IS NOT NULL AND opportunity_id IS NULL) OR "
            "(lead_id IS NULL AND opportunity_id IS NOT NULL)",
            name="ck_sales_inventory_matches_lead_xor_opportunity",
        ),
        Index("ix_sales_inventory_matches_lead_id", "lead_id"),
        Index("ix_sales_inventory_matches_opportunity_id", "opportunity_id"),
        Index("ix_sales_inventory_matches_asset_id", "inventory_asset_id"),
        Index("ix_sales_inventory_matches_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=True,
    )
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("sales_opportunities.id", ondelete="CASCADE"),
        nullable=True,
    )
    inventory_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("inventory_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    relationship_type: Mapped[MatchRelationshipType] = mapped_column(
        Enum(MatchRelationshipType, native_enum=False, length=30),
        nullable=False,
        default=MatchRelationshipType.MATCHED,
    )
    status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus, native_enum=False, length=20),
        nullable=False,
        default=MatchStatus.ACTIVE,
    )
    match_source: Mapped[MatchSource] = mapped_column(
        Enum(MatchSource, native_enum=False, length=20),
        nullable=False,
        default=MatchSource.MANUAL,
    )
    match_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    match_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rejection_reason: Mapped[MatchRejectionReason | None] = mapped_column(
        Enum(MatchRejectionReason, native_enum=False, length=30),
        nullable=True,
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    inventory_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SalesShortlist(Base):
    __tablename__ = "sales_shortlists"
    __table_args__ = (
        CheckConstraint(
            "(lead_id IS NOT NULL AND opportunity_id IS NULL) OR "
            "(lead_id IS NULL AND opportunity_id IS NOT NULL)",
            name="ck_sales_shortlists_lead_xor_opportunity",
        ),
        Index("ix_sales_shortlists_lead_id", "lead_id"),
        Index("ix_sales_shortlists_opportunity_id", "opportunity_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=True,
    )
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("sales_opportunities.id", ondelete="CASCADE"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ShortlistStatus] = mapped_column(
        Enum(ShortlistStatus, native_enum=False, length=20),
        nullable=False,
        default=ShortlistStatus.DRAFT,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SalesShortlistItem(Base):
    __tablename__ = "sales_shortlist_items"
    __table_args__ = (
        UniqueConstraint("shortlist_id", "inventory_asset_id", name="uq_shortlist_asset"),
        Index("ix_sales_shortlist_items_shortlist_id", "shortlist_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    shortlist_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sales_shortlists.id", ondelete="CASCADE"),
        nullable=False,
    )
    inventory_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("inventory_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    inventory_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
