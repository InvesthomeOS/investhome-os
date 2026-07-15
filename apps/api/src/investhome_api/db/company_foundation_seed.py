"""Company foundation development seed data."""

from sqlalchemy import select

from investhome_api.db.session import SessionLocal
from investhome_api.models.company_foundation import BrandProfile, CompanyProfile, Department, Office
from investhome_api.services.company_foundation_service import ensure_default_preferences, get_or_create_company_profile

INITIAL_DEPARTMENTS = [
    ("Executive", "executive"),
    ("Development", "development"),
    ("Construction", "construction"),
    ("Finance", "finance"),
    ("Sales", "sales"),
    ("Investor Relations", "investor_relations"),
    ("Marketing", "marketing"),
    ("Operations", "operations"),
    ("Administration", "administration"),
]

DEVELOPMENT_OFFICES = [
    {
        "office_name": "Türkiye Office (Development)",
        "office_code": "tr-dev",
        "office_type": "regional",
        "country": "Türkiye",
        "city": "[Development placeholder]",
        "timezone": "Europe/Istanbul",
        "default_currency": "TRY",
        "is_primary": True,
    },
    {
        "office_name": "Washington, DC Office (Development)",
        "office_code": "dc-dev",
        "office_type": "representative",
        "country": "United States",
        "state_or_region": "District of Columbia",
        "city": "Washington, DC",
        "timezone": "America/New_York",
        "default_currency": "USD",
    },
    {
        "office_name": "Dubai Office (Development)",
        "office_code": "dubai-dev",
        "office_type": "sales",
        "country": "United Arab Emirates",
        "city": "Dubai",
        "timezone": "Asia/Dubai",
        "default_currency": "AED",
    },
    {
        "office_name": "London Office (Development)",
        "office_code": "london-dev",
        "office_type": "sales",
        "country": "United Kingdom",
        "city": "London",
        "timezone": "Europe/London",
        "default_currency": "GBP",
    },
]


def seed_company_foundation() -> dict[str, int]:
    """Seed company profile, brand, offices, departments, and preferences when missing."""
    counts = {
        "company": 0,
        "brand": 0,
        "offices": 0,
        "departments": 0,
        "preferences": 0,
    }
    with SessionLocal() as session:
        existing = session.scalar(select(CompanyProfile.id).limit(1))
        if existing is not None:
            ensure_default_preferences(session)
            session.commit()
            return counts

        company = get_or_create_company_profile(session)
        counts["company"] = 1

        brand = BrandProfile(
            company_id=company.id,
            brand_name="Investhome",
            brand_code="investhome",
            legal_display_name="Investhome",
            slogan="Building tomorrow's communities",
            brand_description="Default Investhome brand profile (development seed).",
            primary_color="#1e3a5f",
            secondary_color="#64748b",
            accent_color="#0ea5e9",
            background_color="#f8fafc",
            surface_color="#ffffff",
            text_primary_color="#0f172a",
            text_secondary_color="#64748b",
            success_color="#16a34a",
            warning_color="#d97706",
            error_color="#dc2626",
            font_heading="Inter",
            font_body="Inter",
            font_monospace="JetBrains Mono",
            border_radius_style="medium",
            is_default=True,
        )
        session.add(brand)
        counts["brand"] = 1

        for payload in DEVELOPMENT_OFFICES:
            session.add(Office(company_id=company.id, **payload))
            counts["offices"] += 1

        for name, code in INITIAL_DEPARTMENTS:
            session.add(Department(company_id=company.id, name=name, code=code))
            counts["departments"] += 1

        ensure_default_preferences(session)
        counts["preferences"] = 1

        session.commit()
    return counts
