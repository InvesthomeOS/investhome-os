"""Landing page service — CRUD, sections, publishing readiness, status transitions."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.marketing_landing_conversion import (
    LandingPageDomain,
    LandingPageSection,
    LandingPageSectionRegistry,
    LandingPageStatus,
    LandingPageVersion,
    MarketingForm,
    MarketingLandingPage,
    PublicDataFieldRegistry,
)
from investhome_api.models.user_auth import User

LANDING_PAGE_TRANSITIONS: dict[LandingPageStatus, set[LandingPageStatus]] = {
    LandingPageStatus.DRAFT: {LandingPageStatus.IN_REVIEW, LandingPageStatus.ARCHIVED},
    LandingPageStatus.IN_REVIEW: {LandingPageStatus.DRAFT, LandingPageStatus.PENDING_APPROVAL},
    LandingPageStatus.PENDING_APPROVAL: {LandingPageStatus.APPROVED, LandingPageStatus.DRAFT},
    LandingPageStatus.APPROVED: {LandingPageStatus.SCHEDULED, LandingPageStatus.PUBLISHED, LandingPageStatus.DRAFT},
    LandingPageStatus.SCHEDULED: {LandingPageStatus.PUBLISHED, LandingPageStatus.PAUSED, LandingPageStatus.DRAFT},
    LandingPageStatus.PUBLISHED: {LandingPageStatus.PAUSED, LandingPageStatus.ARCHIVED},
    LandingPageStatus.PAUSED: {LandingPageStatus.PUBLISHED, LandingPageStatus.ARCHIVED},
    LandingPageStatus.ARCHIVED: {LandingPageStatus.DRAFT},
}

DEFAULT_SECTION_REGISTRY = [
    ("hero", "Hero", ["project.name", "project.tagline"]),
    ("lead_form", "Lead Form", []),
    ("project_summary", "Project Summary", ["project.name", "project.location", "project.description"]),
    ("property_summary", "Property Summary", ["property.name", "property.price_display", "property.bedrooms"]),
    ("features", "Features", ["project.features"]),
    ("testimonials", "Testimonials", []),
    ("cta", "Call to Action", []),
    ("gallery", "Gallery", ["project.gallery_urls"]),
    ("video", "Video", []),
    ("faq", "FAQ", []),
    ("footer", "Footer", []),
]

DEFAULT_PUBLIC_FIELDS = [
    ("project", "name", "Project Name"),
    ("project", "location", "Location"),
    ("project", "description", "Description"),
    ("project", "tagline", "Tagline"),
    ("project", "features", "Features"),
    ("project", "gallery_urls", "Gallery URLs"),
    ("property", "name", "Property Name"),
    ("property", "price_display", "Price Display"),
    ("property", "bedrooms", "Bedrooms"),
]


def compute_pages(total: int, page_size: int) -> int:
    return max(1, math.ceil(total / page_size)) if total else 1


def ensure_registries(db: Session) -> None:
    for section_type, label, fields in DEFAULT_SECTION_REGISTRY:
        existing = db.scalar(select(LandingPageSectionRegistry).where(LandingPageSectionRegistry.section_type == section_type))
        if not existing:
            db.add(
                LandingPageSectionRegistry(
                    section_type=section_type,
                    label=label,
                    allowed_public_fields_json=fields,
                    config_schema_json={"type": "object"},
                )
            )
    for entity_type, field_key, label in DEFAULT_PUBLIC_FIELDS:
        existing = db.scalar(
            select(PublicDataFieldRegistry).where(
                PublicDataFieldRegistry.entity_type == entity_type,
                PublicDataFieldRegistry.field_key == field_key,
            )
        )
        if not existing:
            db.add(PublicDataFieldRegistry(entity_type=entity_type, field_key=field_key, label=label))
    db.flush()


def _get_page_or_404(db: Session, page_id: UUID) -> MarketingLandingPage:
    page = db.get(MarketingLandingPage, page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Landing page not found")
    return page


def list_landing_pages(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    status_filter: str | None = None,
    search: str | None = None,
) -> tuple[list[MarketingLandingPage], int]:
    query = select(MarketingLandingPage)
    if status_filter:
        query = query.where(MarketingLandingPage.status == LandingPageStatus(status_filter))
    if search:
        query = query.where(MarketingLandingPage.name.ilike(f"%{search}%"))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(MarketingLandingPage.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(rows), total


def create_landing_page(db: Session, payload: dict, user: User) -> MarketingLandingPage:
    ensure_registries(db)
    existing = db.scalar(select(MarketingLandingPage).where(MarketingLandingPage.slug == payload["slug"]))
    if existing:
        raise HTTPException(status_code=409, detail="Slug already exists")
    page = MarketingLandingPage(
        name=payload["name"],
        slug=payload["slug"],
        campaign_id=payload.get("campaign_id"),
        form_id=payload.get("form_id"),
        project_id=payload.get("project_id"),
        property_id=payload.get("property_id"),
        meta_title=payload.get("meta_title"),
        meta_description=payload.get("meta_description"),
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    db.add(page)
    db.flush()
    return page


def update_landing_page(db: Session, page_id: UUID, payload: dict, user: User) -> MarketingLandingPage:
    page = _get_page_or_404(db, page_id)
    if "slug" in payload and payload["slug"] != page.slug:
        existing = db.scalar(select(MarketingLandingPage).where(MarketingLandingPage.slug == payload["slug"]))
        if existing:
            raise HTTPException(status_code=409, detail="Slug already exists")
    for key, value in payload.items():
        if value is not None or key in payload:
            setattr(page, key, value)
    page.updated_by_user_id = user.id
    db.flush()
    return page


def get_landing_page_detail(db: Session, page_id: UUID) -> MarketingLandingPage:
    return _get_page_or_404(db, page_id)


def list_sections(db: Session, page_id: UUID) -> list[LandingPageSection]:
    _get_page_or_404(db, page_id)
    return list(
        db.scalars(
            select(LandingPageSection)
            .where(LandingPageSection.landing_page_id == page_id)
            .order_by(LandingPageSection.sort_order)
        ).all()
    )


def add_section(db: Session, page_id: UUID, payload: dict) -> LandingPageSection:
    _get_page_or_404(db, page_id)
    ensure_registries(db)
    registry = db.scalar(
        select(LandingPageSectionRegistry).where(LandingPageSectionRegistry.section_type == payload["section_type"])
    )
    if not registry:
        raise HTTPException(status_code=400, detail="Invalid section type")
    config = payload.get("config_json") or {}
    if "public_fields" in config:
        allowed = set(registry.allowed_public_fields_json or [])
        for field in config["public_fields"]:
            if field not in allowed and allowed:
                raise HTTPException(status_code=400, detail=f"Public field not allowlisted: {field}")
    section = LandingPageSection(
        landing_page_id=page_id,
        section_type=payload["section_type"],
        sort_order=payload.get("sort_order", 0),
        config_json=config,
        is_visible=payload.get("is_visible", True),
    )
    db.add(section)
    db.flush()
    return section


def update_section(db: Session, section_id: UUID, payload: dict) -> LandingPageSection:
    section = db.get(LandingPageSection, section_id)
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")
    if "config_json" in payload and payload["config_json"]:
        registry = db.scalar(
            select(LandingPageSectionRegistry).where(
                LandingPageSectionRegistry.section_type == section.section_type.value
                if hasattr(section.section_type, "value")
                else section.section_type
            )
        )
        config = payload["config_json"]
        if registry and "public_fields" in config:
            allowed = set(registry.allowed_public_fields_json or [])
            for field in config["public_fields"]:
                if field not in allowed and allowed:
                    raise HTTPException(status_code=400, detail=f"Public field not allowlisted: {field}")
    for key, value in payload.items():
        if value is not None:
            setattr(section, key, value)
    db.flush()
    return section


def compute_publish_readiness(db: Session, page_id: UUID) -> dict:
    page = _get_page_or_404(db, page_id)
    blockers: list[str] = []
    warnings: list[str] = []

    sections = list_sections(db, page_id)
    if not sections:
        blockers.append("no_sections")

    if page.form_id:
        form = db.get(MarketingForm, page.form_id)
        form_status = form.status.value if form and hasattr(form.status, "value") else (form.status if form else None)
        if not form or form_status != "published":
            blockers.append("form_not_published")
    else:
        has_form_section = any(
            (s.section_type.value if hasattr(s.section_type, "value") else s.section_type) == "lead_form"
            for s in sections
        )
        if has_form_section:
            blockers.append("form_not_linked")

    domains = db.scalars(select(LandingPageDomain).where(LandingPageDomain.landing_page_id == page_id)).all()
    if not domains:
        warnings.append("no_domain_configured")
    elif not any(
        (d.verification_status.value if hasattr(d.verification_status, "value") else d.verification_status) == "verified"
        for d in domains
    ):
        blockers.append("domain_not_verified")

    if not page.consent_config_json:
        blockers.append("consent_not_configured")

    if page.approval_status != "approved":
        blockers.append("approval_incomplete")

    if page.status not in (LandingPageStatus.APPROVED, LandingPageStatus.SCHEDULED):
        blockers.append("status_not_publishable")

    return {
        "landing_page_id": str(page_id),
        "ready": len(blockers) == 0,
        "blockers": blockers,
        "warnings": warnings,
    }


def transition_landing_page_status(db: Session, page_id: UUID, target_status: str, user: User) -> MarketingLandingPage:
    page = _get_page_or_404(db, page_id)
    target = LandingPageStatus(target_status)
    current = page.status
    allowed = LANDING_PAGE_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Invalid status transition", "from": current.value, "to": target.value},
        )
    if target == LandingPageStatus.PUBLISHED:
        readiness = compute_publish_readiness(db, page_id)
        if not readiness["ready"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"message": "Publishing blocked", "blockers": readiness["blockers"]},
            )
        version = _create_version_snapshot(db, page, user)
        page.published_version_id = version.id
        page.published_at = datetime.now(tz=UTC)
    page.status = target
    page.updated_by_user_id = user.id
    db.flush()
    return page


def _create_version_snapshot(db: Session, page: MarketingLandingPage, user: User) -> LandingPageVersion:
    sections = list_sections(db, page.id)
    last_version = db.scalar(
        select(func.max(LandingPageVersion.version_number)).where(LandingPageVersion.landing_page_id == page.id)
    )
    version_number = (last_version or 0) + 1
    snapshot = {
        "page": {"name": page.name, "slug": page.slug, "meta_title": page.meta_title},
        "sections": [
            {
                "section_type": s.section_type.value if hasattr(s.section_type, "value") else s.section_type,
                "config_json": s.config_json,
                "sort_order": s.sort_order,
            }
            for s in sections
        ],
    }
    version = LandingPageVersion(
        landing_page_id=page.id,
        version_number=version_number,
        snapshot_json=snapshot,
        created_by_user_id=user.id,
    )
    db.add(version)
    db.flush()
    return version


def list_versions(db: Session, page_id: UUID) -> list[LandingPageVersion]:
    _get_page_or_404(db, page_id)
    return list(
        db.scalars(
            select(LandingPageVersion)
            .where(LandingPageVersion.landing_page_id == page_id)
            .order_by(LandingPageVersion.version_number.desc())
        ).all()
    )


def add_domain(db: Session, page_id: UUID, payload: dict) -> LandingPageDomain:
    _get_page_or_404(db, page_id)
    domain = LandingPageDomain(
        landing_page_id=page_id,
        domain=payload["domain"],
        path_prefix=payload.get("path_prefix"),
        is_primary=payload.get("is_primary", False),
    )
    db.add(domain)
    db.flush()
    return domain


def list_domains(db: Session, page_id: UUID) -> list[LandingPageDomain]:
    _get_page_or_404(db, page_id)
    return list(db.scalars(select(LandingPageDomain).where(LandingPageDomain.landing_page_id == page_id)).all())


def list_section_registry(db: Session) -> list[LandingPageSectionRegistry]:
    ensure_registries(db)
    return list(db.scalars(select(LandingPageSectionRegistry).where(LandingPageSectionRegistry.is_active.is_(True))).all())


def list_public_data_fields(db: Session, entity_type: str | None = None) -> list[PublicDataFieldRegistry]:
    ensure_registries(db)
    query = select(PublicDataFieldRegistry).where(PublicDataFieldRegistry.is_active.is_(True))
    if entity_type:
        query = query.where(PublicDataFieldRegistry.entity_type == entity_type)
    return list(db.scalars(query).all())
