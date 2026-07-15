"""Company, brand, office, organization, and system preference models."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from investhome_api.db.base import Base


class RecordStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class OfficeType(str, enum.Enum):
    HEADQUARTERS = "headquarters"
    REGIONAL = "regional"
    SALES = "sales"
    OPERATIONS = "operations"
    DEVELOPMENT = "development"
    REPRESENTATIVE = "representative"
    VIRTUAL = "virtual"
    OTHER = "other"


class MeasurementSystem(str, enum.Enum):
    IMPERIAL = "imperial"
    METRIC = "metric"


class AreaUnit(str, enum.Enum):
    SQUARE_FEET = "square_feet"
    SQUARE_METERS = "square_meters"


class BrandAssetType(str, enum.Enum):
    LOGO = "logo"
    ICON = "icon"
    FAVICON = "favicon"
    PRESENTATION_TEMPLATE = "presentation_template"
    PROPOSAL_TEMPLATE = "proposal_template"
    EMAIL_TEMPLATE = "email_template"
    LETTERHEAD = "letterhead"
    BUSINESS_CARD = "business_card"
    SOCIAL_TEMPLATE = "social_template"
    BROCHURE_TEMPLATE = "brochure_template"
    DISCLAIMER = "disclaimer"
    FONT_REFERENCE = "font_reference"
    BRAND_GUIDE = "brand_guide"
    PHOTO = "photo"
    VIDEO = "video"
    OTHER = "other"


class PreferenceCategory(str, enum.Enum):
    GENERAL = "general"
    FINANCE = "finance"
    PROJECTS = "projects"
    DOCUMENTS = "documents"
    NOTIFICATIONS = "notifications"
    AI = "ai"
    STORAGE = "storage"
    INTEGRATIONS = "integrations"


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    short_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    company_code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    slogan: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    primary_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    primary_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    registration_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state_or_region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address_line_1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line_2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(30), nullable=True)
    default_language: Mapped[str] = mapped_column(String(5), nullable=False, default="tr")
    default_timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/Istanbul")
    default_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    default_measurement_system: Mapped[str] = mapped_column(String(20), nullable=False, default="imperial")
    default_area_unit: Mapped[str] = mapped_column(String(20), nullable=False, default="square_feet")
    default_date_format: Mapped[str] = mapped_column(String(30), nullable=False, default="DD/MM/YYYY")
    default_number_format: Mapped[str] = mapped_column(String(30), nullable=False, default="1.234,56")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=RecordStatus.ACTIVE.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    offices: Mapped[list[Office]] = relationship(back_populates="company", cascade="all, delete-orphan")
    brands: Mapped[list[BrandProfile]] = relationship(back_populates="company", cascade="all, delete-orphan")
    departments: Mapped[list[Department]] = relationship(back_populates="company", cascade="all, delete-orphan")


class Office(Base):
    __tablename__ = "offices"
    __table_args__ = (UniqueConstraint("company_id", "office_code", name="uq_offices_company_code"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company_profiles.id", ondelete="CASCADE"), nullable=False)
    office_name: Mapped[str] = mapped_column(String(255), nullable=False)
    office_code: Mapped[str] = mapped_column(String(50), nullable=False)
    office_type: Mapped[str] = mapped_column(String(30), nullable=False, default=OfficeType.OTHER.value)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state_or_region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address_line_1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line_2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(30), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    default_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=RecordStatus.ACTIVE.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    company: Mapped[CompanyProfile] = relationship(back_populates="offices")


class BrandProfile(Base):
    __tablename__ = "brand_profiles"
    __table_args__ = (UniqueConstraint("company_id", "brand_code", name="uq_brands_company_code"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company_profiles.id", ondelete="CASCADE"), nullable=False)
    brand_name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand_code: Mapped[str] = mapped_column(String(50), nullable=False)
    legal_display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    slogan: Mapped[str | None] = mapped_column(String(500), nullable=True)
    brand_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_primary_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    logo_secondary_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    logo_monochrome_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    favicon_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    primary_color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    secondary_color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    accent_color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    background_color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    surface_color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    text_primary_color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    text_secondary_color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    success_color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    warning_color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    error_color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    font_heading: Mapped[str | None] = mapped_column(String(120), nullable=True)
    font_body: Mapped[str | None] = mapped_column(String(120), nullable=True)
    font_monospace: Mapped[str | None] = mapped_column(String(120), nullable=True)
    border_radius_style: Mapped[str | None] = mapped_column(String(30), nullable=True)
    standard_disclaimer_tr: Mapped[str | None] = mapped_column(Text, nullable=True)
    standard_disclaimer_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_footer_tr: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_footer_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    social_links: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    contact_information: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=RecordStatus.ACTIVE.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    company: Mapped[CompanyProfile] = relationship(back_populates="brands")
    assets: Mapped[list[BrandAsset]] = relationship(back_populates="brand_profile", cascade="all, delete-orphan")


class BrandAsset(Base):
    __tablename__ = "brand_assets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    brand_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("brand_profiles.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str | None] = mapped_column(String(5), nullable=True)
    usage_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=RecordStatus.ACTIVE.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    brand_profile: Mapped[BrandProfile] = relationship(back_populates="assets")


class SystemPreference(Base):
    __tablename__ = "system_preferences"
    __table_args__ = (UniqueConstraint("preference_key", name="uq_system_preferences_key"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    preference_key: Mapped[str] = mapped_column(String(120), nullable=False)
    value_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_secret: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Department(Base):
    __tablename__ = "departments"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_departments_company_code"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company_profiles.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    manager_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=RecordStatus.ACTIVE.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    company: Mapped[CompanyProfile] = relationship(back_populates="departments")
    teams: Mapped[list[Team]] = relationship(back_populates="department", cascade="all, delete-orphan")


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint("department_id", "code", name="uq_teams_department_code"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    department_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    manager_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=RecordStatus.ACTIVE.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    department: Mapped[Department] = relationship(back_populates="teams")


class UserDepartment(Base):
    __tablename__ = "user_departments"
    __table_args__ = (UniqueConstraint("user_id", "department_id", name="uq_user_departments"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    department_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserTeam(Base):
    __tablename__ = "user_teams"
    __table_args__ = (UniqueConstraint("user_id", "team_id", name="uq_user_teams"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
