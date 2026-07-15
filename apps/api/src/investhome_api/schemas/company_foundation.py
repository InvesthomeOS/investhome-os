"""Company foundation API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator


SUPPORTED_CURRENCIES = frozenset({"USD", "TRY", "EUR", "GBP", "AED"})
SUPPORTED_LANGUAGES = frozenset({"tr", "en"})
SUPPORTED_MEASUREMENT_SYSTEMS = frozenset({"imperial", "metric"})
SUPPORTED_AREA_UNITS = frozenset({"square_feet", "square_meters"})
SUPPORTED_LENGTH_UNITS = frozenset({"feet", "inches", "meters", "centimeters", "millimeters"})


class CompanyProfileResponse(BaseModel):
    id: UUID
    company_name: str
    legal_name: str | None = None
    short_name: str | None = None
    company_code: str
    slogan: str | None = None
    description: str | None = None
    website: str | None = None
    primary_email: str | None = None
    primary_phone: str | None = None
    tax_id: str | None = None
    registration_number: str | None = None
    country: str | None = None
    state_or_region: str | None = None
    city: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    postal_code: str | None = None
    default_language: str
    default_timezone: str
    default_currency: str
    default_measurement_system: str
    default_area_unit: str
    default_date_format: str
    default_number_format: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CompanyProfileUpdate(BaseModel):
    company_name: str | None = Field(default=None, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    short_name: str | None = Field(default=None, max_length=80)
    slogan: str | None = Field(default=None, max_length=500)
    description: str | None = None
    website: str | None = Field(default=None, max_length=500)
    primary_email: str | None = Field(default=None, max_length=255)
    primary_phone: str | None = Field(default=None, max_length=50)
    tax_id: str | None = Field(default=None, max_length=100)
    registration_number: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    state_or_region: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    address_line_1: str | None = Field(default=None, max_length=255)
    address_line_2: str | None = Field(default=None, max_length=255)
    postal_code: str | None = Field(default=None, max_length=30)
    default_language: str | None = Field(default=None, pattern="^(tr|en)$")
    default_timezone: str | None = Field(default=None, max_length=64)
    default_currency: str | None = Field(default=None, min_length=3, max_length=3)
    default_measurement_system: str | None = Field(default=None, pattern="^(imperial|metric)$")
    default_area_unit: str | None = Field(default=None, pattern="^(square_feet|square_meters)$")
    default_date_format: str | None = Field(default=None, max_length=30)
    default_number_format: str | None = Field(default=None, max_length=30)
    status: str | None = Field(default=None, pattern="^(active|inactive)$")

    @field_validator("default_currency")
    @classmethod
    def validate_currency(cls, value: str | None) -> str | None:
        if value is not None and value.upper() not in SUPPORTED_CURRENCIES:
            raise ValueError("unsupported_currency")
        return value.upper() if value else None


class OfficeResponse(BaseModel):
    id: UUID
    company_id: UUID
    office_name: str
    office_code: str
    office_type: str
    country: str | None = None
    state_or_region: str | None = None
    city: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    postal_code: str | None = None
    phone: str | None = None
    email: str | None = None
    timezone: str | None = None
    default_currency: str | None = None
    is_primary: bool
    status: str
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None

    model_config = {"from_attributes": True}


class OfficeCreate(BaseModel):
    office_name: str = Field(min_length=1, max_length=255)
    office_code: str = Field(min_length=1, max_length=50)
    office_type: str = Field(default="other", max_length=30)
    country: str | None = Field(default=None, max_length=100)
    state_or_region: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    address_line_1: str | None = Field(default=None, max_length=255)
    address_line_2: str | None = Field(default=None, max_length=255)
    postal_code: str | None = Field(default=None, max_length=30)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    timezone: str | None = Field(default=None, max_length=64)
    default_currency: str | None = Field(default=None, min_length=3, max_length=3)
    is_primary: bool = False


class OfficeUpdate(BaseModel):
    office_name: str | None = Field(default=None, max_length=255)
    office_type: str | None = Field(default=None, max_length=30)
    country: str | None = None
    state_or_region: str | None = None
    city: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    postal_code: str | None = None
    phone: str | None = None
    email: str | None = None
    timezone: str | None = None
    default_currency: str | None = None
    is_primary: bool | None = None
    status: str | None = Field(default=None, pattern="^(active|inactive)$")


class BrandProfileResponse(BaseModel):
    id: UUID
    company_id: UUID
    brand_name: str
    brand_code: str
    legal_display_name: str | None = None
    slogan: str | None = None
    brand_description: str | None = None
    logo_primary_document_id: UUID | None = None
    logo_secondary_document_id: UUID | None = None
    logo_monochrome_document_id: UUID | None = None
    favicon_document_id: UUID | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None
    background_color: str | None = None
    surface_color: str | None = None
    text_primary_color: str | None = None
    text_secondary_color: str | None = None
    success_color: str | None = None
    warning_color: str | None = None
    error_color: str | None = None
    font_heading: str | None = None
    font_body: str | None = None
    font_monospace: str | None = None
    border_radius_style: str | None = None
    standard_disclaimer_tr: str | None = None
    standard_disclaimer_en: str | None = None
    email_footer_tr: str | None = None
    email_footer_en: str | None = None
    social_links: dict | None = None
    contact_information: dict | None = None
    is_default: bool
    status: str
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None

    model_config = {"from_attributes": True}


class BrandProfileCreate(BaseModel):
    brand_name: str = Field(min_length=1, max_length=255)
    brand_code: str = Field(min_length=1, max_length=50)
    legal_display_name: str | None = None
    slogan: str | None = None
    brand_description: str | None = None
    primary_color: str | None = Field(default="#1e3a5f", max_length=20)
    secondary_color: str | None = Field(default="#64748b", max_length=20)
    accent_color: str | None = Field(default="#0ea5e9", max_length=20)
    is_default: bool = False


class BrandProfileUpdate(BaseModel):
    brand_name: str | None = Field(default=None, max_length=255)
    legal_display_name: str | None = None
    slogan: str | None = None
    brand_description: str | None = None
    logo_primary_document_id: UUID | None = None
    logo_secondary_document_id: UUID | None = None
    logo_monochrome_document_id: UUID | None = None
    favicon_document_id: UUID | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None
    background_color: str | None = None
    surface_color: str | None = None
    text_primary_color: str | None = None
    text_secondary_color: str | None = None
    success_color: str | None = None
    warning_color: str | None = None
    error_color: str | None = None
    font_heading: str | None = None
    font_body: str | None = None
    font_monospace: str | None = None
    border_radius_style: str | None = None
    standard_disclaimer_tr: str | None = None
    standard_disclaimer_en: str | None = None
    email_footer_tr: str | None = None
    email_footer_en: str | None = None
    social_links: dict | None = None
    contact_information: dict | None = None
    status: str | None = Field(default=None, pattern="^(active|inactive)$")


class BrandAssetResponse(BaseModel):
    id: UUID
    brand_profile_id: UUID
    document_id: UUID
    asset_type: str
    title: str | None = None
    language: str | None = None
    usage_notes: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None

    model_config = {"from_attributes": True}


class BrandAssetCreate(BaseModel):
    document_id: UUID
    asset_type: str = Field(max_length=40)
    title: str | None = Field(default=None, max_length=255)
    language: str | None = Field(default=None, pattern="^(tr|en)$")
    usage_notes: str | None = None


class BrandAssetUpdate(BaseModel):
    asset_type: str | None = Field(default=None, max_length=40)
    title: str | None = None
    language: str | None = None
    usage_notes: str | None = None
    status: str | None = Field(default=None, pattern="^(active|inactive)$")


class PreferenceItemResponse(BaseModel):
    preference_key: str
    category: str
    value: dict | list | str | int | float | bool | None
    is_secret: bool
    is_configured: bool = True


class SystemPreferencesResponse(BaseModel):
    items: list[PreferenceItemResponse]
    categories: dict[str, list[PreferenceItemResponse]]


class SystemPreferencesUpdate(BaseModel):
    preferences: dict[str, dict | list | str | int | float | bool | None]


class DepartmentResponse(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    code: str
    description: str | None = None
    manager_user_id: UUID | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=50)
    description: str | None = None
    manager_user_id: UUID | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    description: str | None = None
    manager_user_id: UUID | None = None
    status: str | None = Field(default=None, pattern="^(active|inactive)$")


class TeamResponse(BaseModel):
    id: UUID
    department_id: UUID
    name: str
    code: str
    description: str | None = None
    manager_user_id: UUID | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=50)
    description: str | None = None
    manager_user_id: UUID | None = None


class TeamUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    description: str | None = None
    manager_user_id: UUID | None = None
    status: str | None = Field(default=None, pattern="^(active|inactive)$")


class UserOrganizationAssignment(BaseModel):
    department_id: UUID | None = None
    team_id: UUID | None = None
    is_primary_department: bool = False


class PublicBrandResponse(BaseModel):
    """Non-sensitive branding for login and public surfaces."""
    company_name: str
    short_name: str | None = None
    slogan: str | None = None
    primary_color: str | None = None
    accent_color: str | None = None
    logo_primary_document_id: UUID | None = None


class CompanyContextResponse(BaseModel):
    """Public branding context for authenticated users."""
    company_name: str
    short_name: str | None = None
    slogan: str | None = None
    default_language: str
    default_timezone: str
    default_currency: str
    default_measurement_system: str
    default_area_unit: str
    brand: BrandProfileResponse | None = None


class SupportedOptionsResponse(BaseModel):
    currencies: list[str]
    languages: list[str]
    measurement_systems: list[str]
    area_units: list[str]
    length_units: list[str]
    office_types: list[str]
    brand_asset_types: list[str]


class ProviderStatusResponse(BaseModel):
    provider_id: str
    category: str
    status: str
    configured: bool
    message_key: str
    requires_secret: bool = False


class ProviderStatusListResponse(BaseModel):
    items: list[ProviderStatusResponse]
