"""Branch management models — locations, working hours, assets, documents."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from investhome_api.db.base import Base


class BranchType(str, enum.Enum):
    HEAD_OFFICE = "head_office"
    REGIONAL_OFFICE = "regional_office"
    CORPORATE_OFFICE = "corporate_office"
    SALES_OFFICE = "sales_office"
    CONSTRUCTION_OFFICE = "construction_office"
    PROJECT_OFFICE = "project_office"
    WAREHOUSE = "warehouse"
    SERVICE_CENTER = "service_center"
    TEMPORARY_OFFICE = "temporary_office"
    REMOTE_OFFICE = "remote_office"
    OTHER = "other"


class BranchStatus(str, enum.Enum):
    PLANNING = "planning"
    OPENING_SOON = "opening_soon"
    ACTIVE = "active"
    INACTIVE = "inactive"
    TEMPORARILY_CLOSED = "temporarily_closed"
    CLOSED = "closed"
    ARCHIVED = "archived"


class BranchAssetType(str, enum.Enum):
    VEHICLE = "vehicle"
    EQUIPMENT = "equipment"
    FURNITURE = "furniture"
    IT_DEVICE = "it_device"
    KEYS = "keys"
    ACCESS_CARD = "access_card"


class BranchAssetStatus(str, enum.Enum):
    ACTIVE = "active"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"
    LOST = "lost"


class BranchDocumentType(str, enum.Enum):
    LEASE = "lease"
    INSURANCE = "insurance"
    LICENSE = "license"
    PERMIT = "permit"
    CONTRACT = "contract"
    OTHER = "other"


class Branch(Base):
    __tablename__ = "branches"
    __table_args__ = (UniqueConstraint("branch_code", name="uq_branches_branch_code"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    branch_code: Mapped[str] = mapped_column(String(50), nullable=False)
    branch_name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    branch_type: Mapped[str] = mapped_column(String(40), nullable=False, default=BranchType.OTHER.value)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(30), nullable=True)
    full_address: Mapped[str] = mapped_column(String(500), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    google_maps_link: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    main_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mobile_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    emergency_contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manager_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=BranchStatus.PLANNING.value)
    opening_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    department_count: Mapped[int] = mapped_column(nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    company: Mapped["Company"] = relationship("Company", back_populates="branches")
    working_hours: Mapped[BranchWorkingHours | None] = relationship(
        back_populates="branch", cascade="all, delete-orphan", uselist=False
    )
    assets: Mapped[list[BranchAsset]] = relationship(back_populates="branch", cascade="all, delete-orphan")
    documents: Mapped[list[BranchDocument]] = relationship(back_populates="branch", cascade="all, delete-orphan")


class BranchWorkingHours(Base):
    __tablename__ = "branch_working_hours"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    branch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    business_days: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    open_time: Mapped[str | None] = mapped_column(String(10), nullable=True)
    close_time: Mapped[str | None] = mapped_column(String(10), nullable=True)
    holidays: Mapped[list | None] = mapped_column(JSON, nullable=True)
    special_hours: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    branch: Mapped[Branch] = relationship(back_populates="working_hours")


class BranchAsset(Base):
    __tablename__ = "branch_assets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=BranchAssetStatus.ACTIVE.value)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    branch: Mapped[Branch] = relationship(back_populates="assets")


class BranchDocument(Base):
    __tablename__ = "branch_documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    document_type: Mapped[str] = mapped_column(String(30), nullable=False, default=BranchDocumentType.OTHER.value)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    branch: Mapped[Branch] = relationship(back_populates="documents")
