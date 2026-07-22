"""Marketing segment API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status, HTTPException
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_audience_segment import (
    SegmentCreate,
    SegmentDetail,
    SegmentFieldRegistryResponse,
    SegmentPreviewResponse,
    SegmentSummary,
    SegmentSummaryStats,
    SegmentUpdate,
)
from investhome_api.services.activity_recorder import log_entity_created, log_entity_updated
from investhome_api.services.marketing.campaign_service import compute_pages
from investhome_api.services.marketing.segment_field_registry import get_field_registry
from investhome_api.services.marketing.segment_service import (
    calculate_segment,
    create_segment,
    get_segment_rules,
    get_segment_summary,
    list_segment_versions,
    list_segments,
    preview_segment,
    refresh_segment,
    update_segment,
    validate_segment_dependencies,
)

router = APIRouter(prefix="/marketing/segments", tags=["marketing-segments"])


def _summary(s) -> SegmentSummary:
    return SegmentSummary(
        id=s.id,
        name=s.name,
        segment_type=s.segment_type.value,
        visibility=s.visibility,
        estimated_size=s.estimated_size,
        calculated_size=s.calculated_size,
        calculation_status=s.calculation_status.value,
        current_version=s.current_version,
        last_refreshed_at=s.last_refreshed_at,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


def _detail(s) -> SegmentDetail:
    return SegmentDetail(
        **_summary(s).model_dump(),
        description=s.description,
        rules_json=s.rules_json,
        depends_on_segment_ids=s.depends_on_segment_ids,
        refresh_frequency=s.refresh_frequency,
    )


@router.get("/field-registry", response_model=SegmentFieldRegistryResponse)
def segment_field_registry(
    user: User = Depends(require_permission("marketing", "view")),
) -> SegmentFieldRegistryResponse:
    perms = {p for _, p in [(None, "view")]}  # simplified; full RBAC via require_permission above
    return SegmentFieldRegistryResponse(fields=get_field_registry(include_restricted=False, user_permissions=perms))


@router.get("/summary", response_model=SegmentSummaryStats)
def segment_summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view")),
) -> SegmentSummaryStats:
    return SegmentSummaryStats(**get_segment_summary(db))


@router.get("")
def list_segments_route(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = None,
    segment_type: str | None = None,
    calculation_status: str | None = None,
) -> dict:
    rows, total = list_segments(
        db, page=page, page_size=page_size, search=search,
        segment_type=segment_type, calculation_status=calculation_status,
    )
    return {
        "items": [_summary(r) for r in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": compute_pages(total, page_size),
    }


@router.post("", status_code=status.HTTP_201_CREATED, response_model=SegmentDetail)
def create_segment_route(
    payload: SegmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "create")),
) -> SegmentDetail:
    data = payload.model_dump()
    if payload.rule_groups:
        data["rule_groups"] = [g.model_dump() for g in payload.rule_groups]
    segment = create_segment(db, user, data)
    log_entity_created(
        db,
        entity_type=ActivityEntityType.MARKETING_SEGMENT,
        entity_id=segment.id,
        description_key="marketing.segment.created",
        actor=user,
        request=request,
    )
    db.commit()
    db.refresh(segment)
    return _detail(segment)


@router.get("/{segment_id}", response_model=SegmentDetail)
def get_segment(
    segment_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view")),
) -> SegmentDetail:
    from investhome_api.services.marketing.segment_service import _get_segment_or_404

    return _detail(_get_segment_or_404(db, segment_id))


@router.put("/{segment_id}", response_model=SegmentDetail)
def update_segment_route(
    segment_id: UUID,
    payload: SegmentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_segment_rules")),
) -> SegmentDetail:
    data = payload.model_dump(exclude_unset=True)
    if payload.rule_groups is not None:
        data["rule_groups"] = [g.model_dump() if hasattr(g, "model_dump") else g for g in payload.rule_groups]
    segment = update_segment(db, segment_id, user, data)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.MARKETING_SEGMENT,
        entity_id=segment.id,
        description_key="marketing.segment.rules_changed",
        actor=user,
        before={},
        after={"version": segment.current_version},
        request=request,
    )
    db.commit()
    db.refresh(segment)
    return _detail(segment)


@router.get("/{segment_id}/rules")
def get_rules(
    segment_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view")),
) -> dict:
    return {"rule_groups": get_segment_rules(db, segment_id)}


@router.post("/{segment_id}/preview", response_model=SegmentPreviewResponse)
def preview_segment_route(
    segment_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view")),
) -> SegmentPreviewResponse:
    return SegmentPreviewResponse(**preview_segment(db, segment_id))


@router.post("/{segment_id}/calculate")
def calculate_segment_route(
    segment_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "refresh_segments")),
) -> dict:
    run = calculate_segment(db, segment_id, user)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.MARKETING_SEGMENT,
        entity_id=segment_id,
        description_key="marketing.segment.calculation_completed",
        actor=user,
        before={},
        after={"status": run.status.value, "member_count": run.member_count},
        request=request,
    )
    db.commit()
    return {
        "run_id": str(run.id),
        "status": run.status.value,
        "member_count": run.member_count,
        "warnings": run.warnings_json,
    }


@router.post("/{segment_id}/refresh", response_model=SegmentDetail)
def refresh_segment_route(
    segment_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "refresh_segments")),
) -> SegmentDetail:
    segment = refresh_segment(db, segment_id, user)
    db.commit()
    db.refresh(segment)
    return _detail(segment)


@router.get("/{segment_id}/dependencies/validate")
def validate_dependencies(
    segment_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view")),
) -> dict:
    from investhome_api.services.marketing.segment_service import _get_segment_or_404

    segment = _get_segment_or_404(db, segment_id)
    try:
        validate_segment_dependencies(db, segment_id, segment.depends_on_segment_ids or [])
        return {"valid": True, "segment_id": str(segment_id)}
    except HTTPException as exc:
        return {"valid": False, "segment_id": str(segment_id), "error": exc.detail}


@router.get("/{segment_id}/versions")
def segment_versions(
    segment_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view")),
) -> dict:
    versions = list_segment_versions(db, segment_id)
    return {
        "items": [
            {
                "id": str(v.id),
                "version": v.version,
                "rules_snapshot_json": v.rules_snapshot_json,
                "created_at": v.created_at.isoformat(),
            }
            for v in versions
        ]
    }
