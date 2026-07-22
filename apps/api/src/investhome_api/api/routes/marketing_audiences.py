"""Marketing audience API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_audience_segment import (
    AudienceCreate,
    AudienceDetail,
    AudienceMemberAdd,
    AudienceMembershipResponse,
    AudienceReadinessResponse,
    AudienceSummary,
    AudienceSummaryStats,
    AudienceUpdate,
    SavedViewCreate,
)
from investhome_api.services.activity_recorder import log_entity_created, log_entity_updated
from investhome_api.services.marketing.audience_service import (
    add_audience_member,
    archive_audience,
    create_audience,
    create_saved_view,
    duplicate_audience,
    exclude_audience_member,
    get_audience_members,
    get_audience_readiness,
    get_audience_summary,
    list_audiences,
    list_saved_views,
    refresh_audience,
    restore_audience,
    update_audience,
)
from investhome_api.services.marketing.campaign_service import compute_pages

router = APIRouter(prefix="/marketing/audiences", tags=["marketing-audiences"])


def _summary(a) -> AudienceSummary:
    return AudienceSummary(
        id=a.id,
        name=a.name,
        audience_type=a.audience_type.value,
        mode=a.mode.value,
        status=a.status.value,
        source=a.source,
        estimated_size=a.estimated_size,
        calculated_size=a.calculated_size,
        language=a.language,
        last_refreshed_at=a.last_refreshed_at,
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


def _detail(a) -> AudienceDetail:
    return AudienceDetail(
        **_summary(a).model_dump(),
        description=a.description,
        contact_ids=a.contact_ids,
        company_ids=a.company_ids,
        segment_ids=a.segment_ids,
        consent_requirements_json=a.consent_requirements_json,
        channel_eligibility_json=a.channel_eligibility_json,
        geo_json=a.geo_json,
        refresh_policy_json=a.refresh_policy_json,
        version=a.version,
    )


@router.get("/summary", response_model=AudienceSummaryStats)
def audience_summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view")),
) -> AudienceSummaryStats:
    stats = get_audience_summary(db)
    return AudienceSummaryStats(**stats)


@router.get("")
def list_audiences_route(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = None,
    mode: str | None = None,
    status: str | None = None,
) -> dict:
    rows, total = list_audiences(db, page=page, page_size=page_size, search=search, mode=mode, status_filter=status)
    return {
        "items": [_summary(r) for r in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": compute_pages(total, page_size),
    }


@router.post("", status_code=status.HTTP_201_CREATED, response_model=AudienceDetail)
def create_audience_route(
    payload: AudienceCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "create")),
) -> AudienceDetail:
    audience = create_audience(db, user, payload.model_dump())
    log_entity_created(
        db,
        entity_type=ActivityEntityType.MARKETING_AUDIENCE,
        entity_id=audience.id,
        description_key="marketing.audience.created",
        actor=user,
        request=request,
    )
    db.commit()
    db.refresh(audience)
    return _detail(audience)


@router.get("/saved-views")
def audience_saved_views(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view")),
) -> dict:
    views = list_saved_views(db, user.id)
    return {"items": [{"id": str(v.id), "name": v.name, "filters_json": v.filters_json} for v in views]}


@router.post("/saved-views", status_code=status.HTTP_201_CREATED)
def create_audience_saved_view(
    payload: SavedViewCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view")),
) -> dict:
    view = create_saved_view(db, user, payload.name, payload.filters_json)
    db.commit()
    return {"id": str(view.id), "name": view.name}


@router.get("/{audience_id}", response_model=AudienceDetail)
def get_audience(
    audience_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view")),
) -> AudienceDetail:
    from investhome_api.services.marketing.audience_service import _get_audience_or_404

    return _detail(_get_audience_or_404(db, audience_id))


@router.put("/{audience_id}", response_model=AudienceDetail)
def update_audience_route(
    audience_id: UUID,
    payload: AudienceUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "update")),
) -> AudienceDetail:
    audience = update_audience(db, audience_id, user, payload.model_dump(exclude_unset=True))
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.MARKETING_AUDIENCE,
        entity_id=audience.id,
        description_key="marketing.audience.updated",
        actor=user,
        before={},
        after={"name": audience.name},
        request=request,
    )
    db.commit()
    db.refresh(audience)
    return _detail(audience)


@router.post("/{audience_id}/duplicate", response_model=AudienceDetail)
def duplicate_audience_route(
    audience_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "create")),
) -> AudienceDetail:
    audience = duplicate_audience(db, audience_id, user)
    db.commit()
    db.refresh(audience)
    return _detail(audience)


@router.post("/{audience_id}/refresh", response_model=AudienceDetail)
def refresh_audience_route(
    audience_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "refresh_segments")),
) -> AudienceDetail:
    audience = refresh_audience(db, audience_id)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.MARKETING_AUDIENCE,
        entity_id=audience.id,
        description_key="marketing.audience.refreshed",
        actor=user,
        before={},
        after={"calculated_size": audience.calculated_size},
        request=request,
    )
    db.commit()
    db.refresh(audience)
    return _detail(audience)


@router.get("/{audience_id}/readiness", response_model=AudienceReadinessResponse)
def audience_readiness(
    audience_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view")),
) -> AudienceReadinessResponse:
    return AudienceReadinessResponse(**get_audience_readiness(db, audience_id))


@router.get("/{audience_id}/members")
def audience_members(
    audience_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_audience_members")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    included_only: bool | None = None,
) -> dict:
    rows, total = get_audience_members(db, audience_id, page=page, page_size=page_size, included_only=included_only)
    return {
        "items": [AudienceMembershipResponse.model_validate(r) for r in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": compute_pages(total, page_size),
    }


@router.post("/{audience_id}/members", status_code=status.HTTP_201_CREATED, response_model=AudienceMembershipResponse)
def add_member(
    audience_id: UUID,
    payload: AudienceMemberAdd,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_audience_members")),
) -> AudienceMembershipResponse:
    membership = add_audience_member(
        db, audience_id, contact_id=payload.contact_id, company_id=payload.company_id
    )
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.MARKETING_AUDIENCE,
        entity_id=audience_id,
        description_key="marketing.audience.member_added",
        actor=user,
        before={},
        after={"membership_id": str(membership.id)},
        request=request,
    )
    db.commit()
    db.refresh(membership)
    return AudienceMembershipResponse.model_validate(membership)


@router.post("/{audience_id}/members/{membership_id}/exclude", response_model=AudienceMembershipResponse)
def exclude_member(
    audience_id: UUID,
    membership_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_audience_members")),
) -> AudienceMembershipResponse:
    membership = exclude_audience_member(db, audience_id, membership_id)
    db.commit()
    db.refresh(membership)
    return AudienceMembershipResponse.model_validate(membership)


@router.post("/{audience_id}/archive", response_model=AudienceDetail)
def archive_audience_route(
    audience_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "archive")),
) -> AudienceDetail:
    audience = archive_audience(db, audience_id)
    db.commit()
    db.refresh(audience)
    return _detail(audience)


@router.post("/{audience_id}/restore", response_model=AudienceDetail)
def restore_audience_route(
    audience_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "restore")),
) -> AudienceDetail:
    audience = restore_audience(db, audience_id)
    db.commit()
    db.refresh(audience)
    return _detail(audience)
