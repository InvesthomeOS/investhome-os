"""Marketing lead source API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_audience_segment import (
    LeadSourceCreate,
    LeadSourceDetail,
    LeadSourceMappingCreate,
    LeadSourceMappingResponse,
    LeadSourceSummary,
    LeadSourceUpdate,
    NormalizationRequest,
    NormalizationResponse,
)
from investhome_api.services.activity_recorder import log_entity_created, log_entity_updated
from investhome_api.services.marketing.campaign_service import compute_pages
from investhome_api.services.marketing.lead_source_service import (
    archive_lead_source,
    create_lead_source,
    create_source_mapping,
    get_lead_source_summary,
    get_source_hierarchy,
    get_source_leads,
    get_source_mappings,
    list_lead_sources,
    normalize_source_value,
    update_lead_source,
)

router = APIRouter(prefix="/marketing/sources", tags=["marketing-sources"])


def _summary(s) -> LeadSourceSummary:
    return LeadSourceSummary(
        id=s.id,
        name=s.name,
        normalized_name=s.normalized_name,
        parent_id=s.parent_id,
        source_type=s.source_type.value,
        channel_id=s.channel_id,
        tracking_code=s.tracking_code,
        tracking_readiness=s.tracking_readiness,
        is_active=s.is_active,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


def _detail(s) -> LeadSourceDetail:
    return LeadSourceDetail(
        **_summary(s).model_dump(),
        description=s.description,
        utm_defaults_json=s.utm_defaults_json,
    )


@router.get("/summary")
def sources_summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view")),
) -> dict:
    return get_lead_source_summary(db)


@router.get("/hierarchy")
def sources_hierarchy(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view")),
) -> dict:
    return {"items": get_source_hierarchy(db)}


@router.get("")
def list_sources(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = None,
    source_type: str | None = None,
) -> dict:
    rows, total = list_lead_sources(db, page=page, page_size=page_size, search=search, source_type=source_type)
    return {
        "items": [_summary(r) for r in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": compute_pages(total, page_size),
    }


@router.post("", status_code=status.HTTP_201_CREATED, response_model=LeadSourceDetail)
def create_source(
    payload: LeadSourceCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "create")),
) -> LeadSourceDetail:
    source = create_lead_source(db, user, payload.model_dump())
    log_entity_created(
        db,
        entity_type=ActivityEntityType.MARKETING_LEAD_SOURCE,
        entity_id=source.id,
        description_key="marketing.lead_source.created",
        actor=user,
        request=request,
    )
    db.commit()
    db.refresh(source)
    return _detail(source)


@router.get("/{source_id}", response_model=LeadSourceDetail)
def get_source(
    source_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view")),
) -> LeadSourceDetail:
    from investhome_api.services.marketing.lead_source_service import _get_source_or_404

    return _detail(_get_source_or_404(db, source_id))


@router.put("/{source_id}", response_model=LeadSourceDetail)
def update_source(
    source_id: UUID,
    payload: LeadSourceUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "update")),
) -> LeadSourceDetail:
    source = update_lead_source(db, source_id, user, payload.model_dump(exclude_unset=True))
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.MARKETING_LEAD_SOURCE,
        entity_id=source.id,
        description_key="marketing.lead_source.updated",
        actor=user,
        before={},
        after={"name": source.name},
        request=request,
    )
    db.commit()
    db.refresh(source)
    return _detail(source)


@router.get("/{source_id}/mappings")
def source_mappings(
    source_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_source_mapping")),
) -> dict:
    mappings = get_source_mappings(db, source_id)
    return {"items": [LeadSourceMappingResponse.model_validate(m) for m in mappings]}


@router.post("/{source_id}/mappings", status_code=status.HTTP_201_CREATED, response_model=LeadSourceMappingResponse)
def add_mapping(
    source_id: UUID,
    payload: LeadSourceMappingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_source_mapping")),
) -> LeadSourceMappingResponse:
    mapping = create_source_mapping(db, source_id, payload.model_dump())
    db.commit()
    db.refresh(mapping)
    return LeadSourceMappingResponse.model_validate(mapping)


@router.post("/{source_id}/normalize", response_model=NormalizationResponse)
def normalize_value(
    source_id: UUID,
    payload: NormalizationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_source_normalization")),
) -> NormalizationResponse:
    result = normalize_source_value(db, source_id, payload.raw_value)
    db.commit()
    return NormalizationResponse(**result)


@router.get("/{source_id}/leads")
def source_leads(
    source_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_leads")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> dict:
    rows, total = get_source_leads(db, source_id, page=page, page_size=page_size)
    return {
        "items": [{"id": str(r.id), "contact_id": str(r.contact_id) if r.contact_id else None} for r in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": compute_pages(total, page_size),
    }


@router.post("/{source_id}/archive", response_model=LeadSourceDetail)
def archive_source(
    source_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "archive")),
) -> LeadSourceDetail:
    source = archive_lead_source(db, source_id)
    db.commit()
    db.refresh(source)
    return _detail(source)
