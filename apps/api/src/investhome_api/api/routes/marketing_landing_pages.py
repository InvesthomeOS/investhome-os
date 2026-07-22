"""Marketing landing pages API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_landing_conversion import (
    LandingPageCreate,
    LandingPageDetail,
    LandingPageDomainCreate,
    LandingPageDomainResponse,
    LandingPageListResponse,
    LandingPageReadinessResponse,
    LandingPageSectionCreate,
    LandingPageSectionResponse,
    LandingPageSectionUpdate,
    LandingPageStatusTransition,
    LandingPageSummary,
    LandingPageUpdate,
    LandingPageVersionResponse,
    PublicDataFieldItem,
    SectionRegistryItem,
)
from investhome_api.services.activity_recorder import activity_context_from_request, log_entity_created, log_entity_updated
from investhome_api.services.marketing.landing_page_service import (
    add_domain,
    add_section,
    compute_pages,
    compute_publish_readiness,
    create_landing_page,
    get_landing_page_detail,
    list_domains,
    list_landing_pages,
    list_public_data_fields,
    list_section_registry,
    list_sections,
    list_versions,
    transition_landing_page_status,
    update_landing_page,
    update_section,
)

router = APIRouter(prefix="/marketing/landing-pages", tags=["marketing-landing-pages"])


def _to_summary(page) -> LandingPageSummary:
    return LandingPageSummary(
        id=page.id,
        name=page.name,
        slug=page.slug,
        status=page.status.value if hasattr(page.status, "value") else page.status,
        campaign_id=page.campaign_id,
        form_id=page.form_id,
        published_at=page.published_at,
        created_at=page.created_at,
        updated_at=page.updated_at,
    )


@router.get("", response_model=LandingPageListResponse)
def list_landing_pages_route(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_landing_pages")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    status: str | None = None,
    search: str | None = None,
):
    items, total = list_landing_pages(db, page=page, page_size=page_size, status_filter=status, search=search)
    return LandingPageListResponse(
        items=[_to_summary(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=compute_pages(total, page_size),
    )


@router.post("", response_model=LandingPageSummary, status_code=201)
def create_landing_page_route(
    payload: LandingPageCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_landing_pages")),
):
    page = create_landing_page(db, payload.model_dump(), user)
    db.commit()
    log_entity_created(
        db,
        entity_type=ActivityEntityType.MARKETING_LANDING_PAGE,
        entity_id=page.id,
        description_key="marketing.landing_page.created",
        actor=user,
        request=request,
    )
    db.commit()
    return _to_summary(page)


@router.get("/section-registry", response_model=list[SectionRegistryItem])
def section_registry_route(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_landing_pages")),
):
    return list_section_registry(db)


@router.get("/public-data-fields", response_model=list[PublicDataFieldItem])
def public_data_fields_route(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_landing_pages")),
    entity_type: str | None = None,
):
    return list_public_data_fields(db, entity_type)


@router.get("/{page_id}", response_model=LandingPageDetail)
def get_landing_page_route(
    page_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_landing_pages")),
):
    page = get_landing_page_detail(db, page_id)
    sections = list_sections(db, page_id)
    return LandingPageDetail(
        **_to_summary(page).model_dump(),
        project_id=page.project_id,
        property_id=page.property_id,
        meta_title=page.meta_title,
        meta_description=page.meta_description,
        tracking_config_json=page.tracking_config_json,
        consent_config_json=page.consent_config_json,
        approval_status=page.approval_status,
        published_version_id=page.published_version_id,
        sections=[
            LandingPageSectionResponse(
                id=s.id,
                landing_page_id=s.landing_page_id,
                section_type=s.section_type.value if hasattr(s.section_type, "value") else s.section_type,
                sort_order=s.sort_order,
                config_json=s.config_json,
                is_visible=s.is_visible,
            )
            for s in sections
        ],
    )


@router.patch("/{page_id}", response_model=LandingPageSummary)
def update_landing_page_route(
    page_id: UUID,
    payload: LandingPageUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_landing_pages")),
):
    page = update_landing_page(db, page_id, payload.model_dump(exclude_unset=True), user)
    db.commit()
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.MARKETING_LANDING_PAGE,
        entity_id=page.id,
        description_key="marketing.landing_page.updated",
        actor=user,
        request=request,
    )
    db.commit()
    return _to_summary(page)


@router.get("/{page_id}/readiness", response_model=LandingPageReadinessResponse)
def landing_page_readiness_route(
    page_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_landing_pages")),
):
    return compute_publish_readiness(db, page_id)


@router.post("/{page_id}/transition", response_model=LandingPageSummary)
def transition_landing_page_route(
    page_id: UUID,
    payload: LandingPageStatusTransition,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_landing_pages")),
):
    page = transition_landing_page_status(db, page_id, payload.target_status, user)
    db.commit()
    return _to_summary(page)


@router.get("/{page_id}/sections", response_model=list[LandingPageSectionResponse])
def list_sections_route(
    page_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_landing_pages")),
):
    sections = list_sections(db, page_id)
    return [
        LandingPageSectionResponse(
            id=s.id,
            landing_page_id=s.landing_page_id,
            section_type=s.section_type.value if hasattr(s.section_type, "value") else s.section_type,
            sort_order=s.sort_order,
            config_json=s.config_json,
            is_visible=s.is_visible,
        )
        for s in sections
    ]


@router.post("/{page_id}/sections", response_model=LandingPageSectionResponse, status_code=201)
def add_section_route(
    page_id: UUID,
    payload: LandingPageSectionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_landing_pages")),
):
    section = add_section(db, page_id, payload.model_dump())
    db.commit()
    return LandingPageSectionResponse(
        id=section.id,
        landing_page_id=section.landing_page_id,
        section_type=section.section_type.value if hasattr(section.section_type, "value") else section.section_type,
        sort_order=section.sort_order,
        config_json=section.config_json,
        is_visible=section.is_visible,
    )


@router.patch("/sections/{section_id}", response_model=LandingPageSectionResponse)
def update_section_route(
    section_id: UUID,
    payload: LandingPageSectionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_landing_pages")),
):
    section = update_section(db, section_id, payload.model_dump(exclude_unset=True))
    db.commit()
    return LandingPageSectionResponse(
        id=section.id,
        landing_page_id=section.landing_page_id,
        section_type=section.section_type.value if hasattr(section.section_type, "value") else section.section_type,
        sort_order=section.sort_order,
        config_json=section.config_json,
        is_visible=section.is_visible,
    )


@router.get("/{page_id}/versions", response_model=list[LandingPageVersionResponse])
def list_versions_route(
    page_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_landing_pages")),
):
    return list_versions(db, page_id)


@router.get("/{page_id}/domains", response_model=list[LandingPageDomainResponse])
def list_domains_route(
    page_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_domains")),
):
    domains = list_domains(db, page_id)
    return [
        LandingPageDomainResponse(
            id=d.id,
            landing_page_id=d.landing_page_id,
            domain=d.domain,
            path_prefix=d.path_prefix,
            is_primary=d.is_primary,
            verification_status=d.verification_status.value if hasattr(d.verification_status, "value") else d.verification_status,
        )
        for d in domains
    ]


@router.post("/{page_id}/domains", response_model=LandingPageDomainResponse, status_code=201)
def add_domain_route(
    page_id: UUID,
    payload: LandingPageDomainCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_domains")),
):
    domain = add_domain(db, page_id, payload.model_dump())
    db.commit()
    return LandingPageDomainResponse(
        id=domain.id,
        landing_page_id=domain.landing_page_id,
        domain=domain.domain,
        path_prefix=domain.path_prefix,
        is_primary=domain.is_primary,
        verification_status=domain.verification_status.value if hasattr(domain.verification_status, "value") else domain.verification_status,
    )
