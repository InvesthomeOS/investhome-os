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
            brand = session.scalar(
                select(BrandProfile).where(BrandProfile.is_default.is_(True)).limit(1)
            )
            if brand is not None and (
                brand.primary_color in {None, "", "#1e3a5f", "#1E3A5F"}
                or brand.font_body in {None, "", "Plus Jakarta Sans"}
                or brand.font_heading in {None, "", "Fraunces"}
            ):
                brand.primary_color = "#9D7B55"
                brand.secondary_color = "#C3A47F"
                brand.accent_color = "#77BFBB"
                brand.background_color = "#F7F4EF"
                brand.surface_color = "#FFFFFF"
                brand.text_primary_color = "#000000"
                brand.text_secondary_color = "#7C7B7A"
                brand.font_heading = "Helvetica Neue"
                brand.font_body = "Helvetica Neue"
                brand.font_monospace = "Helvetica Neue"
                counts["brand"] = 1
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
            primary_color="#9D7B55",
            secondary_color="#C3A47F",
            accent_color="#77BFBB",
            background_color="#F7F4EF",
            surface_color="#FFFFFF",
            text_primary_color="#000000",
            text_secondary_color="#7C7B7A",
            success_color="#16a34a",
            warning_color="#d97706",
            error_color="#dc2626",
            font_heading="Helvetica Neue",
            font_body="Helvetica Neue",
            font_monospace="Helvetica Neue",
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
