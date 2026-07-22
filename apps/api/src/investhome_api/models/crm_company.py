"""CRM Company — first-class CRM entity distinct from org workspace Company.

Architecture Decision (ADR):
- CrmCompany is the CRM workspace source of truth for external organizations
  (investment companies, brokerages, lenders, vendors, etc.).
- Org workspace `companies` table (Company model) remains for internal entity management.
- Profile sections are 1:1 related tables for field-level permission stripping.
- Company types support multi-select via `crm_company_type_assignments` junction.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
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


class CrmCompanyType(str, enum.Enum):
    INVESTMENT_COMPANY = "investment_company"
    BUYER_ENTITY = "buyer_entity"
    BROKERAGE = "brokerage"
    LAW_FIRM = "law_firm"
    BANK = "bank"
    LENDER = "lender"
    PROPERTY_MANAGEMENT = "property_management"
    CONSTRUCTION = "construction"
    CONTRACTOR = "contractor"
    ARCHITECTURE = "architecture"
    ACCOUNTING = "accounting"
    CONSULTING = "consulting"
    INSURANCE = "insurance"
    MEDIA = "media"
    GOVERNMENT = "government"
    VENDOR = "vendor"
    PARTNER = "partner"
    INTERNAL_ENTITY = "internal_entity"
    OTHER = "other"


class CrmCompanyStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PROSPECT = "prospect"
    ARCHIVED = "archived"


class CrmEntityType(str, enum.Enum):
    CORPORATION = "corporation"
    LLC = "llc"
    PARTNERSHIP = "partnership"
    TRUST = "trust"
    SOLE_PROPRIETORSHIP = "sole_proprietorship"
    NON_PROFIT = "non_profit"
    GOVERNMENT = "government"
    OTHER = "other"


class CrmCompanyLifecycleStage(str, enum.Enum):
    NEW = "new"
    ENGAGED = "engaged"
    QUALIFIED = "qualified"
    ACTIVE_RELATIONSHIP = "active_relationship"
    DORMANT = "dormant"
    CHURNED = "churned"


class CrmCompanyRelationshipStatus(str, enum.Enum):
    UNKNOWN = "unknown"
    COLD = "cold"
    WARM = "warm"
    HOT = "hot"
    ACTIVE = "active"
    AT_RISK = "at_risk"
    LOST = "lost"


class CrmCompanyRelationshipStrength(str, enum.Enum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    STRATEGIC = "strategic"


class CrmCompanyAddressType(str, enum.Enum):
    HEADQUARTERS = "headquarters"
    BILLING = "billing"
    SHIPPING = "shipping"
    MAILING = "mailing"
    BRANCH = "branch"
    OTHER = "other"


class CrmCompanyContactRole(str, enum.Enum):
    PRIMARY = "primary"
    BILLING = "billing"
    LEGAL = "legal"
    TECHNICAL = "technical"
    EXECUTIVE = "executive"
    OTHER = "other"


class CrmCompanyContactStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    FORMER = "former"


class CrmCompanyRelationshipType(str, enum.Enum):
    PARENT = "parent"
    SUBSIDIARY = "subsidiary"
    AFFILIATE = "affiliate"
    PARTNER = "partner"
    COMPETITOR = "competitor"
    VENDOR = "vendor"
    CLIENT = "client"
    INVESTOR = "investor"
    OTHER = "other"


class CrmCompanyRelationshipLinkStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class CrmCompany(Base):
    __tablename__ = "crm_companies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trade_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_type: Mapped[CrmCompanyType] = mapped_column(
        Enum(CrmCompanyType, native_enum=False, length=40),
        nullable=False,
    )
    entity_type: Mapped[CrmEntityType | None] = mapped_column(
        Enum(CrmEntityType, native_enum=False, length=30),
        nullable=True,
    )
    status: Mapped[CrmCompanyStatus] = mapped_column(
        Enum(CrmCompanyStatus, native_enum=False, length=20),
        nullable=False,
        default=CrmCompanyStatus.ACTIVE,
    )
    lifecycle_stage: Mapped[CrmCompanyLifecycleStage] = mapped_column(
        Enum(CrmCompanyLifecycleStage, native_enum=False, length=30),
        nullable=False,
        default=CrmCompanyLifecycleStage.NEW,
    )
    registration_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ein: Mapped[str | None] = mapped_column(String(80), nullable=True)
    duns_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    incorporation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    incorporation_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    incorporation_state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    primary_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    secondary_emails: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    primary_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    secondary_phones: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(120), nullable=True)
    employee_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    annual_revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    relationship_status: Mapped[CrmCompanyRelationshipStatus] = mapped_column(
        Enum(CrmCompanyRelationshipStatus, native_enum=False, length=20),
        nullable=False,
        default=CrmCompanyRelationshipStatus.UNKNOWN,
    )
    relationship_strength: Mapped[CrmCompanyRelationshipStrength] = mapped_column(
        Enum(CrmCompanyRelationshipStrength, native_enum=False, length=20),
        nullable=False,
        default=CrmCompanyRelationshipStrength.MODERATE,
    )
    relationship_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    parent_company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("crm_companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    legal_data: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    compliance_data: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

    type_assignments: Mapped[list[CrmCompanyTypeAssignment]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )
    addresses: Mapped[list[CrmCompanyAddress]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )
    contact_links: Mapped[list[CrmCompanyContact]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )
    relationships_from: Mapped[list[CrmCompanyRelationship]] = relationship(
        back_populates="source_company",
        foreign_keys="CrmCompanyRelationship.source_company_id",
        cascade="all, delete-orphan",
    )
    tag_links: Mapped[list[CrmCompanyTag]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )
    financial_profile: Mapped[CrmCompanyFinancialProfile | None] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
        uselist=False,
    )
    investment_profile: Mapped[CrmCompanyInvestmentProfile | None] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
        uselist=False,
    )
    brokerage_profile: Mapped[CrmCompanyBrokerageProfile | None] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
        uselist=False,
    )
    lender_profile: Mapped[CrmCompanyLenderProfile | None] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
        uselist=False,
    )
    vendor_profile: Mapped[CrmCompanyVendorProfile | None] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
        uselist=False,
    )
    law_firm_profile: Mapped[CrmCompanyLawFirmProfile | None] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
        uselist=False,
    )
    property_management_profile: Mapped[CrmCompanyPropertyManagementProfile | None] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
        uselist=False,
    )
    parent_company: Mapped[CrmCompany | None] = relationship(
        remote_side="CrmCompany.id",
        foreign_keys=[parent_company_id],
    )


class CrmCompanyTypeAssignment(Base):
    __tablename__ = "crm_company_type_assignments"
    __table_args__ = (UniqueConstraint("company_id", "company_type", name="uq_crm_company_type"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    company_type: Mapped[CrmCompanyType] = mapped_column(
        Enum(CrmCompanyType, native_enum=False, length=40),
        nullable=False,
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    company: Mapped[CrmCompany] = relationship(back_populates="type_assignments")


class CrmCompanyAddress(Base):
    __tablename__ = "crm_company_addresses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    address_type: Mapped[CrmCompanyAddressType] = mapped_column(
        Enum(CrmCompanyAddressType, native_enum=False, length=20),
        nullable=False,
        default=CrmCompanyAddressType.HEADQUARTERS,
    )
    address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state_province: Mapped[str | None] = mapped_column(String(120), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(30), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    company: Mapped[CrmCompany] = relationship(back_populates="addresses")


class CrmCompanyContact(Base):
    __tablename__ = "crm_company_contacts"
    __table_args__ = (UniqueConstraint("company_id", "contact_id", name="uq_crm_company_contact"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_contacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[CrmCompanyContactRole] = mapped_column(
        Enum(CrmCompanyContactRole, native_enum=False, length=20),
        nullable=False,
        default=CrmCompanyContactRole.OTHER,
    )
    job_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    department: Mapped[str | None] = mapped_column(String(120), nullable=True)
    relationship_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    ownership_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    signing_authority: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[CrmCompanyContactStatus] = mapped_column(
        Enum(CrmCompanyContactStatus, native_enum=False, length=20),
        nullable=False,
        default=CrmCompanyContactStatus.ACTIVE,
    )
    company: Mapped[CrmCompany] = relationship(back_populates="contact_links")


class CrmCompanyRelationship(Base):
    __tablename__ = "crm_company_relationships"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    relationship_type: Mapped[CrmCompanyRelationshipType] = mapped_column(
        Enum(CrmCompanyRelationshipType, native_enum=False, length=20),
        nullable=False,
    )
    is_reciprocal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[CrmCompanyRelationshipLinkStatus] = mapped_column(
        Enum(CrmCompanyRelationshipLinkStatus, native_enum=False, length=20),
        nullable=False,
        default=CrmCompanyRelationshipLinkStatus.ACTIVE,
    )
    strength: Mapped[CrmCompanyRelationshipStrength] = mapped_column(
        Enum(CrmCompanyRelationshipStrength, native_enum=False, length=20),
        nullable=False,
        default=CrmCompanyRelationshipStrength.MODERATE,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_company: Mapped[CrmCompany] = relationship(
        back_populates="relationships_from",
        foreign_keys=[source_company_id],
    )


class CrmCompanyTag(Base):
    __tablename__ = "crm_company_tags"
    __table_args__ = (UniqueConstraint("company_id", "tag_id", name="uq_crm_company_tag"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_tags.id", ondelete="CASCADE"),
        nullable=False,
    )
    company: Mapped[CrmCompany] = relationship(back_populates="tag_links")


class CrmCompanySavedView(Base):
    __tablename__ = "crm_company_saved_views"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    filters: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    columns: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    sort_by: Mapped[str | None] = mapped_column(String(60), nullable=True)
    sort_order: Mapped[str | None] = mapped_column(String(4), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class CrmCompanyFinancialProfile(Base):
    __tablename__ = "crm_company_financial_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_companies.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    credit_rating: Mapped[str | None] = mapped_column(String(20), nullable=True)
    annual_revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_worth: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_assets: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_liabilities: Mapped[float | None] = mapped_column(Float, nullable=True)
    fiscal_year_end: Mapped[str | None] = mapped_column(String(20), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    company: Mapped[CrmCompany] = relationship(back_populates="financial_profile")


class CrmCompanyInvestmentProfile(Base):
    __tablename__ = "crm_company_investment_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_companies.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    aum: Mapped[float | None] = mapped_column(Float, nullable=True)
    investment_focus: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    preferred_asset_classes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    preferred_regions: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    ticket_size_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    ticket_size_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    fund_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    company: Mapped[CrmCompany] = relationship(back_populates="investment_profile")


class CrmCompanyBrokerageProfile(Base):
    __tablename__ = "crm_company_brokerage_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_companies.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    license_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    license_state: Mapped[str | None] = mapped_column(String(60), nullable=True)
    specialization: Mapped[str | None] = mapped_column(String(120), nullable=True)
    market_coverage: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    agent_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    company: Mapped[CrmCompany] = relationship(back_populates="brokerage_profile")


class CrmCompanyLenderProfile(Base):
    __tablename__ = "crm_company_lender_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_companies.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    lender_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    nmls_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    loan_types: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    max_loan_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_credit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    company: Mapped[CrmCompany] = relationship(back_populates="lender_profile")


class CrmCompanyVendorProfile(Base):
    __tablename__ = "crm_company_vendor_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_companies.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    vendor_category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(String(60), nullable=True)
    contract_status: Mapped[str | None] = mapped_column(String(60), nullable=True)
    insurance_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    company: Mapped[CrmCompany] = relationship(back_populates="vendor_profile")


class CrmCompanyLawFirmProfile(Base):
    __tablename__ = "crm_company_law_firm_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_companies.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    bar_number: Mapped[str | None] = mapped_column(String(60), nullable=True)
    practice_areas: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    attorney_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    company: Mapped[CrmCompany] = relationship(back_populates="law_firm_profile")


class CrmCompanyPropertyManagementProfile(Base):
    __tablename__ = "crm_company_property_management_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_companies.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    units_managed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    property_types: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    service_areas: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    license_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    company: Mapped[CrmCompany] = relationship(back_populates="property_management_profile")
