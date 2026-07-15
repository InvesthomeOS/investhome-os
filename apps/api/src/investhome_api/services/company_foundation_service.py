"""Company foundation business logic."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.company_foundation import (
    BrandAsset,
    BrandProfile,
    CompanyProfile,
    Department,
    Office,
    SystemPreference,
    Team,
    UserDepartment,
    UserTeam,
)
from investhome_api.schemas.company_foundation import (
    SUPPORTED_AREA_UNITS,
    SUPPORTED_CURRENCIES,
    SUPPORTED_LANGUAGES,
    SUPPORTED_LENGTH_UNITS,
    SUPPORTED_MEASUREMENT_SYSTEMS,
)

DEFAULT_PREFERENCES: dict[str, dict] = {
    "general.default_language": {"category": "general", "value": "tr"},
    "general.default_timezone": {"category": "general", "value": "Europe/Istanbul"},
    "general.default_date_format": {"category": "general", "value": "DD/MM/YYYY"},
    "general.default_number_format": {"category": "general", "value": "1.234,56"},
    "general.default_currency": {"category": "general", "value": "USD"},
    "general.default_measurement_system": {"category": "general", "value": "imperial"},
    "general.default_area_unit": {"category": "general", "value": "square_feet"},
    "general.supported_languages": {"category": "general", "value": ["tr", "en"]},
    "finance.primary_reporting_currency": {"category": "finance", "value": "USD"},
    "finance.supported_currencies": {"category": "finance", "value": ["USD", "TRY", "EUR", "GBP", "AED"]},
    "finance.fiscal_year_start_month": {"category": "finance", "value": 1},
    "finance.decimal_precision": {"category": "finance", "value": 2},
    "projects.default_area_unit": {"category": "projects", "value": "square_feet"},
    "projects.default_project_currency": {"category": "projects", "value": "USD"},
    "documents.default_confidentiality": {"category": "documents", "value": "internal"},
    "documents.upload_size_limit_bytes": {"category": "documents", "value": 52_428_800},
    "documents.expiration_reminder_days": {"category": "documents", "value": [30, 7, 1]},
    "notifications.default_reminder_days": {"category": "notifications", "value": [7, 3, 1]},
    "notifications.critical_threshold_hours": {"category": "notifications", "value": 24},
    "ai.default_provider": {"category": "ai", "value": "local"},
    "ai.default_model": {"category": "ai", "value": "local-heuristic-v1"},
    "ai.allow_external_confidential": {"category": "ai", "value": False},
    "ai.allow_external_highly_confidential": {"category": "ai", "value": False},
    "storage.active_provider": {"category": "storage", "value": "local"},
    "integrations.enabled_providers": {"category": "integrations", "value": []},
}


def get_company_profile(db: Session) -> CompanyProfile | None:
    return db.scalar(select(CompanyProfile).where(CompanyProfile.status == "active").limit(1))


def get_or_create_company_profile(db: Session) -> CompanyProfile:
    company = get_company_profile(db)
    if company is not None:
        return company
    company = CompanyProfile(
        company_name="Investhome",
        legal_name="Investhome Development",
        short_name="Investhome",
        company_code="investhome",
        slogan="Building tomorrow's communities",
        default_language="tr",
        default_timezone="Europe/Istanbul",
        default_currency="USD",
        default_measurement_system="imperial",
        default_area_unit="square_feet",
    )
    db.add(company)
    db.flush()
    return company


def get_default_brand(db: Session, company_id: UUID) -> BrandProfile | None:
    return db.scalar(
        select(BrandProfile)
        .where(
            BrandProfile.company_id == company_id,
            BrandProfile.is_default.is_(True),
            BrandProfile.archived_at.is_(None),
            BrandProfile.status == "active",
        )
        .limit(1)
    )


def set_default_brand(db: Session, brand_id: UUID, company_id: UUID) -> BrandProfile:
    for brand in db.scalars(select(BrandProfile).where(BrandProfile.company_id == company_id)).all():
        brand.is_default = brand.id == brand_id
    brand = db.get(BrandProfile, brand_id)
    if brand is None or brand.company_id != company_id:
        raise ValueError("brand_not_found")
    brand.is_default = True
    db.flush()
    return brand


def mask_secret_value(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, str) and value:
        return "••••••••"
    return "••••"


def get_preference(db: Session, key: str) -> SystemPreference | None:
    return db.scalar(select(SystemPreference).where(SystemPreference.preference_key == key))


def ensure_default_preferences(db: Session) -> None:
    for key, meta in DEFAULT_PREFERENCES.items():
        existing = get_preference(db, key)
        if existing is None:
            db.add(
                SystemPreference(
                    category=meta["category"],
                    preference_key=key,
                    value_json={"value": meta["value"]},
                    is_secret=key.endswith("_secret") or key.endswith("_api_key"),
                )
            )
    db.flush()


def get_all_preferences(db: Session, *, include_secrets: bool = False) -> list[SystemPreference]:
    ensure_default_preferences(db)
    prefs = db.scalars(select(SystemPreference).order_by(SystemPreference.category, SystemPreference.preference_key)).all()
    if include_secrets:
        return list(prefs)
    return list(prefs)


def update_preferences(db: Session, updates: dict[str, object]) -> list[SystemPreference]:
    ensure_default_preferences(db)
    secret_keys = {"ai.openai_api_key", "integrations.mail_api_key", "storage.s3_secret_key"}
    for key, value in updates.items():
        if key in secret_keys:
            continue
        pref = get_preference(db, key)
        if pref is None:
            category = key.split(".", 1)[0]
            pref = SystemPreference(category=category, preference_key=key, value_json={"value": value})
            db.add(pref)
        else:
            if pref.is_secret and not include_secrets_allowed(value):
                continue
            pref.value_json = {"value": value}
    db.flush()
    return get_all_preferences(db)


def include_secrets_allowed(value: object) -> bool:
    return False


def build_company_context(db: Session) -> dict:
    company = get_or_create_company_profile(db)
    brand = get_default_brand(db, company.id)
    return {
        "company_name": company.company_name,
        "short_name": company.short_name,
        "slogan": company.slogan or (brand.slogan if brand else None),
        "default_language": company.default_language,
        "default_timezone": company.default_timezone,
        "default_currency": company.default_currency,
        "default_measurement_system": company.default_measurement_system,
        "default_area_unit": company.default_area_unit,
        "brand": brand,
    }


def get_provider_statuses() -> list[dict]:
    settings = get_settings()
    return [
        {
            "provider_id": "local_ai",
            "category": "ai",
            "status": "ready" if settings.ai_provider == "local" else "available",
            "configured": True,
            "message_key": "settings.providers.ai.local",
            "requires_secret": False,
        },
        {
            "provider_id": "openai",
            "category": "ai",
            "status": "configured" if settings.ai_api_key else "not_configured",
            "configured": bool(settings.ai_api_key),
            "message_key": "settings.providers.ai.openai",
            "requires_secret": True,
        },
        {
            "provider_id": "local_ocr",
            "category": "ai",
            "status": "ready",
            "configured": True,
            "message_key": "settings.providers.ocr.local",
            "requires_secret": False,
        },
        {
            "provider_id": "local_storage",
            "category": "storage",
            "status": "ready",
            "configured": True,
            "message_key": "settings.providers.storage.local",
            "requires_secret": False,
        },
        {
            "provider_id": "s3",
            "category": "storage",
            "status": "not_configured",
            "configured": False,
            "message_key": "settings.providers.storage.s3",
            "requires_secret": True,
        },
    ]


def supported_options() -> dict:
    return {
        "currencies": sorted(SUPPORTED_CURRENCIES),
        "languages": sorted(SUPPORTED_LANGUAGES),
        "measurement_systems": sorted(SUPPORTED_MEASUREMENT_SYSTEMS),
        "area_units": sorted(SUPPORTED_AREA_UNITS),
        "length_units": sorted(SUPPORTED_LENGTH_UNITS),
        "office_types": [
            "headquarters", "regional", "sales", "operations",
            "development", "representative", "virtual", "other",
        ],
        "brand_asset_types": [
            "logo", "icon", "favicon", "presentation_template", "proposal_template",
            "email_template", "letterhead", "business_card", "social_template",
            "brochure_template", "disclaimer", "font_reference", "brand_guide",
            "photo", "video", "other",
        ],
    }


def archive_office(db: Session, office: Office) -> Office:
    office.archived_at = datetime.now(UTC)
    office.status = "inactive"
    db.flush()
    return office


def archive_brand(db: Session, brand: BrandProfile) -> BrandProfile:
    brand.archived_at = datetime.now(UTC)
    brand.status = "inactive"
    if brand.is_default:
        brand.is_default = False
    db.flush()
    return brand


def archive_brand_asset(db: Session, asset: BrandAsset) -> BrandAsset:
    asset.archived_at = datetime.now(UTC)
    asset.status = "inactive"
    db.flush()
    return asset


def assign_user_organization(
    db: Session,
    user_id: UUID,
    *,
    department_id: UUID | None,
    team_id: UUID | None,
    is_primary_department: bool,
) -> None:
    if department_id:
        existing = db.scalar(
            select(UserDepartment).where(
                UserDepartment.user_id == user_id,
                UserDepartment.department_id == department_id,
            )
        )
        if existing is None:
            if is_primary_department:
                for row in db.scalars(select(UserDepartment).where(UserDepartment.user_id == user_id)).all():
                    row.is_primary = False
            db.add(UserDepartment(user_id=user_id, department_id=department_id, is_primary=is_primary_department))
    if team_id:
        existing = db.scalar(
            select(UserTeam).where(UserTeam.user_id == user_id, UserTeam.team_id == team_id)
        )
        if existing is None:
            db.add(UserTeam(user_id=user_id, team_id=team_id))
    db.flush()
