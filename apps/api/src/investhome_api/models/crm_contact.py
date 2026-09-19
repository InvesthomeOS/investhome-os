"""CRM Contact — unified relationship management record.

Architecture Decision (ADR):
- CrmContact is the CRM workspace source of truth for people and organizations
  connected to Investhome across all relationship types.
- Lead and Investor remain owned by their respective modules (Sales / Investors).
  Optional `lead_id` and `investor_id` foreign keys link CRM records without
  duplicating pipeline or investment data.
- Sales `Party` (party_id + party_type on opportunities) continues to reference
  Lead/Investor directly for the commercial pipeline — CRM does NOT own opportunities.
- Profile sections (investment, buyer, broker, vendor) are 1:1 related tables so
  field-level permission stripping can omit entire sections from API responses.
- Contact types support multi-select via `crm_contact_type_assignments` junction;
  `contact_type` column remains the primary type for list sorting and backward compat.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from investhome_api.db.base import Base


class CrmContactType(str, enum.Enum):
    INVESTOR = "investor"
    PROSPECT = "prospect"
    BUYER = "buyer"
    BROKER = "broker"
    REALTOR = "realtor"
    PARTNER = "partner"
    VENDOR = "vendor"
    CONTRACTOR = "contractor"
    ATTORNEY = "attorney"
    LENDER = "lender"
    PROPERTY_MANAGER = "property_manager"
    ARCHITECT = "architect"
    CONSULTANT = "consultant"
    MEDIA_CONTACT = "media_contact"
    GOVERNMENT_CONTACT = "government_contact"
    INTERNAL_TEAM = "internal_team"


class CrmRecordKind(str, enum.Enum):
    PERSON = "person"
    ORGANIZATION = "organization"


class CrmContactStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PROSPECT = "prospect"
    ARCHIVED = "archived"


class CrmLifecycleStage(str, enum.Enum):
    NEW = "new"
    ENGAGED = "engaged"
    QUALIFIED = "qualified"
    ACTIVE_RELATIONSHIP = "active_relationship"
    DORMANT = "dormant"
    CHURNED = "churned"


class CrmRelationshipStatus(str, enum.Enum):
    UNKNOWN = "unknown"
    COLD = "cold"
    WARM = "warm"
    HOT = "hot"
    ACTIVE = "active"
    AT_RISK = "at_risk"
    LOST = "lost"


class CrmRelationshipStrength(str, enum.Enum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    STRATEGIC = "strategic"


class CrmContactPriority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class CrmContact(Base):
    __tablename__ = "crm_contacts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    contact_type: Mapped[CrmContactType] = mapped_column(
        Enum(CrmContactType, native_enum=False, length=40),
        nullable=False,
    )
    record_kind: Mapped[CrmRecordKind] = mapped_column(
        Enum(CrmRecordKind, native_enum=False, length=20),
        nullable=False,
        default=CrmRecordKind.PERSON,
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    organization_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    department: Mapped[str | None] = mapped_column(String(120), nullable=True)
    primary_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    secondary_emails: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    primary_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    secondary_phones: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    whatsapp: Mapped[str | None] = mapped_column(String(50), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state_province: Mapped[str | None] = mapped_column(String(120), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(30), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lifecycle_stage: Mapped[CrmLifecycleStage] = mapped_column(
        Enum(CrmLifecycleStage, native_enum=False, length=30),
        nullable=False,
        default=CrmLifecycleStage.NEW,
    )
    relationship_status: Mapped[CrmRelationshipStatus] = mapped_column(
        Enum(CrmRelationshipStatus, native_enum=False, length=20),
        nullable=False,
        default=CrmRelationshipStatus.UNKNOWN,
    )
    relationship_strength: Mapped[CrmRelationshipStrength] = mapped_column(
        Enum(CrmRelationshipStrength, native_enum=False, length=20),
        nullable=False,
        default=CrmRelationshipStrength.MODERATE,
    )
    priority: Mapped[CrmContactPriority] = mapped_column(
        Enum(CrmContactPriority, native_enum=False, length=20),
        nullable=False,
        default=CrmContactPriority.NORMAL,
    )
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    referred_by_contact_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("crm_contacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    relationship_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    engagement_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[CrmContactStatus] = mapped_column(
        Enum(CrmContactStatus, native_enum=False, length=20),
        nullable=False,
        default=CrmContactStatus.ACTIVE,
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        nullable=True,
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
    )
    investor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("investors.id", ondelete="SET NULL"),
        nullable=True,
    )
    compliance_data: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    communication_prefs: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    junk_reason: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    junked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
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

    type_assignments: Mapped[list[CrmContactTypeAssignment]] = relationship(
        back_populates="contact",
        cascade="all, delete-orphan",
    )
    investment_profile: Mapped[CrmContactInvestmentProfile | None] = relationship(
        back_populates="contact",
        cascade="all, delete-orphan",
        uselist=False,
    )
    buyer_profile: Mapped[CrmContactBuyerProfile | None] = relationship(
        back_populates="contact",
        cascade="all, delete-orphan",
        uselist=False,
    )
    broker_profile: Mapped[CrmContactBrokerProfile | None] = relationship(
        back_populates="contact",
        cascade="all, delete-orphan",
        uselist=False,
    )
    vendor_profile: Mapped[CrmContactVendorProfile | None] = relationship(
        back_populates="contact",
        cascade="all, delete-orphan",
        uselist=False,
    )
    tag_links: Mapped[list[CrmContactTag]] = relationship(
        back_populates="contact",
        cascade="all, delete-orphan",
    )


class CrmContactTypeAssignment(Base):
    __tablename__ = "crm_contact_type_assignments"
    __table_args__ = (UniqueConstraint("contact_id", "contact_type", name="uq_crm_contact_type"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    contact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_contacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    contact_type: Mapped[CrmContactType] = mapped_column(
        Enum(CrmContactType, native_enum=False, length=40),
        nullable=False,
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contact: Mapped[CrmContact] = relationship(back_populates="type_assignments")


class CrmTag(Base):
    __tablename__ = "crm_tags"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class CrmContactTag(Base):
    __tablename__ = "crm_contact_tags"
    __table_args__ = (UniqueConstraint("contact_id", "tag_id", name="uq_crm_contact_tag"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    contact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_contacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_tags.id", ondelete="CASCADE"),
        nullable=False,
    )
    contact: Mapped[CrmContact] = relationship(back_populates="tag_links")
    tag: Mapped[CrmTag] = relationship()


class CrmContactInvestmentProfile(Base):
    __tablename__ = "crm_contact_investment_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    contact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_contacts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    investor_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    accreditation_status: Mapped[str | None] = mapped_column(String(60), nullable=True)
    risk_profile: Mapped[str | None] = mapped_column(String(60), nullable=True)
    investment_capacity_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    investment_capacity_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    preferred_asset_classes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    preferred_regions: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    investment_timeline: Mapped[str | None] = mapped_column(String(60), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact: Mapped[CrmContact] = relationship(back_populates="investment_profile")


class CrmContactBuyerProfile(Base):
    __tablename__ = "crm_contact_buyer_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    contact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_contacts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    budget_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    preferred_locations: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    property_types: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    bedroom_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    financing_status: Mapped[str | None] = mapped_column(String(60), nullable=True)
    purchase_timeline: Mapped[str | None] = mapped_column(String(60), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact: Mapped[CrmContact] = relationship(back_populates="buyer_profile")


class CrmContactBrokerProfile(Base):
    __tablename__ = "crm_contact_broker_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    contact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_contacts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    license_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    brokerage_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    specialization: Mapped[str | None] = mapped_column(String(120), nullable=True)
    service_areas: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    commission_structure: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact: Mapped[CrmContact] = relationship(back_populates="broker_profile")


class CrmContactVendorProfile(Base):
    __tablename__ = "crm_contact_vendor_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    contact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_contacts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    vendor_category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    service_scope: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contract_status: Mapped[str | None] = mapped_column(String(60), nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(String(120), nullable=True)
    insurance_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact: Mapped[CrmContact] = relationship(back_populates="vendor_profile")


class CrmContactSavedView(Base):
    __tablename__ = "crm_contact_saved_views"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_shared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    filters_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    sort_by: Mapped[str | None] = mapped_column(String(40), nullable=True)
    sort_dir: Mapped[str | None] = mapped_column(String(4), nullable=True)
    columns_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    density: Mapped[str | None] = mapped_column(String(20), nullable=True)
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


class CrmContactMergeHistory(Base):
    __tablename__ = "crm_contact_merge_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    survivor_contact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_contacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    merged_contact_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    merged_snapshot: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    merged_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class CrmContactDuplicateCandidate(Base):
    __tablename__ = "crm_contact_duplicate_candidates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    contact_id_a: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_contacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    contact_id_b: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_contacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    match_reason: Mapped[str] = mapped_column(String(60), nullable=False)
    match_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
