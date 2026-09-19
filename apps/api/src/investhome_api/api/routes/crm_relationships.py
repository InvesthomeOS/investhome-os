"""CRM Relationship API routes — prefix /crm/relationships."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import get_current_user, require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_relationships import (
    CrmDecisionMapRoleCreate,
    CrmDecisionMapResponse,
    CrmDecisionMapRoleResponse,
    CrmGraphExpandRequest,
    CrmIntroductionPathsResponse,
    CrmReferralCreate,
    CrmReferralResponse,
    CrmRelationshipAlertResponse,
    CrmRelationshipAlertStatusUpdate,
    CrmRelationshipBulkActionRequest,
    CrmRelationshipBulkActionResponse,
    CrmRelationshipCreate,
    CrmRelationshipDetail,
    CrmRelationshipDuplicateCandidate,
    CrmRelationshipGraphResponse,
    CrmRelationshipIntelligenceDashboard,
    CrmRelationshipListResponse,
    CrmRelationshipRecommendation,
    CrmRelationshipReviewCreate,
    CrmRelationshipReviewResponse,
    CrmRelationshipSavedViewCreate,
    CrmRelationshipSavedViewResponse,
    CrmRelationshipScoreBreakdown,
    CrmRelationshipScoreCalculateRequest,
    CrmRelationshipScoreCalculateResponse,
    CrmRelationshipUpdate,
)
from investhome_api.services.activity_service import snapshot_entity
from investhome_api.services.crm.introduction_path_service import find_introduction_paths
from investhome_api.services.crm.relationship_graph_service import expand_node, get_relationship_graph
from investhome_api.services.crm.relationship_score_service import (
    calculate_relationship_scores,
    recalculate_scores,
)
from investhome_api.services.crm.relationship_service import (
    CRM_RELATIONSHIP_ACTIVITY_FIELDS,
    archive_relationship,
    bulk_action,
    build_intelligence_dashboard,
    can_view_confidential,
    can_view_referral_compensation,
    create_referral,
    create_relationship,
    create_review,
    create_saved_view,
    delete_relationship,
    export_relationships_csv,
    find_duplicate_candidates,
    get_decision_map,
    get_recommendations,
    get_relationship_or_404,
    list_alerts,
    list_referrals,
    list_relationships,
    list_reviews,
    list_saved_views,
    restore_relationship,
    serialize_referral,
    serialize_relationship_detail,
    strip_confidential_fields,
    strip_referral_compensation,
    update_alert_status,
    update_relationship,
    upsert_decision_map_role,
)
from investhome_api.services.crm_relationship_activity import (
    record_relationship_archived,
    record_relationship_created,
    record_relationship_deleted,
    record_relationship_restored,
    record_relationship_updated,
)
from investhome_api.services.permission_service import user_has_permission

router = APIRouter(prefix="/crm/relationships", tags=["crm-relationships"])


def _require_relationships_read():
    async def _dependency(user: User = Depends(get_current_user)) -> User:
        if not user_has_permission(user, "crm", "read"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return _dependency


@router.get("", response_model=CrmRelationshipListResponse)
def list_crm_relationships(
    search: str | None = Query(default=None, max_length=255),
    status_filter: str | None = Query(default=None, alias="status"),
    category: str | None = Query(default=None),
    relationship_type: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    entity_id: UUID | None = Query(default=None),
    include_archived: bool = Query(default=False),
    sort_by: str = Query(default="updated_at"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(_require_relationships_read()),
) -> CrmRelationshipListResponse:
    return list_relationships(
        db,
        search=search,
        status_filter=status_filter,
        category=category,
        relationship_type=relationship_type,
        entity_type=entity_type,
        entity_id=entity_id,
        include_archived=include_archived,
        include_confidential=can_view_confidential(user),
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=CrmRelationshipDetail, status_code=status.HTTP_201_CREATED)
def create_crm_relationship(
    payload: CrmRelationshipCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "create")),
) -> CrmRelationshipDetail:
    rel = create_relationship(db, payload, user)
    record_relationship_created(db, rel, user, request)
    db.commit()
    db.refresh(rel)
    detail = serialize_relationship_detail(db, rel)
    return strip_confidential_fields(detail, can_view_confidential(user))


@router.post("/check-duplicates", response_model=list[CrmRelationshipDuplicateCandidate])
def check_duplicates(
    payload: CrmRelationshipCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_require_relationships_read()),
) -> list[CrmRelationshipDuplicateCandidate]:
    del user
    return find_duplicate_candidates(db, payload)


@router.get("/graph", response_model=CrmRelationshipGraphResponse)
def get_graph(
    center_entity_type: str | None = Query(default=None),
    center_entity_id: UUID | None = Query(default=None),
    depth: int = Query(default=2, ge=1, le=5),
    limit: int = Query(default=50, ge=1, le=200),
    category: str | None = Query(default=None),
    relationship_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(_require_relationships_read()),
) -> CrmRelationshipGraphResponse:
    return get_relationship_graph(
        db,
        center_entity_type=center_entity_type,
        center_entity_id=center_entity_id,
        depth=depth,
        limit=limit,
        include_confidential=can_view_confidential(user),
        category=category,
        relationship_type=relationship_type,
    )


@router.post("/expand-node", response_model=CrmRelationshipGraphResponse)
def expand_graph_node(
    payload: CrmGraphExpandRequest,
    db: Session = Depends(get_db),
    user: User = Depends(_require_relationships_read()),
) -> CrmRelationshipGraphResponse:
    return expand_node(
        db,
        node_id=payload.node_id,
        depth=payload.depth,
        include_confidential=can_view_confidential(user),
    )


@router.get("/scores/calculate", response_model=CrmRelationshipScoreCalculateResponse)
def calculate_scores_get(
    relationship_id: UUID = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "update")),
) -> CrmRelationshipScoreCalculateResponse:
    del user
    rel = get_relationship_or_404(db, relationship_id)
    breakdown = calculate_relationship_scores(db, rel)
    from investhome_api.services.crm.relationship_score_service import apply_scores_to_relationship
    apply_scores_to_relationship(db, rel, breakdown)
    db.commit()
    return CrmRelationshipScoreCalculateResponse(calculated=1, results=[breakdown])


@router.post("/scores/calculate", response_model=CrmRelationshipScoreCalculateResponse)
def calculate_scores_post(
    payload: CrmRelationshipScoreCalculateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "update")),
) -> CrmRelationshipScoreCalculateResponse:
    del user
    count, results = recalculate_scores(
        db,
        relationship_ids=payload.relationship_ids,
        recalculate_all=payload.recalculate_all,
    )
    db.commit()
    return CrmRelationshipScoreCalculateResponse(calculated=count, results=results)


@router.get("/{relationship_id}/score-breakdown", response_model=CrmRelationshipScoreBreakdown)
def get_score_breakdown(
    relationship_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(_require_relationships_read()),
) -> CrmRelationshipScoreBreakdown:
    del user
    rel = get_relationship_or_404(db, relationship_id)
    return calculate_relationship_scores(db, rel)


@router.get("/alerts", response_model=list[CrmRelationshipAlertResponse])
def get_alerts(
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    user: User = Depends(_require_relationships_read()),
) -> list[CrmRelationshipAlertResponse]:
    del user
    return list_alerts(db, status_filter=status_filter)


@router.patch("/alerts/{alert_id}", response_model=CrmRelationshipAlertResponse)
def patch_alert_status(
    alert_id: UUID,
    payload: CrmRelationshipAlertStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "update")),
) -> CrmRelationshipAlertResponse:
    del user
    result = update_alert_status(db, alert_id, payload.status.value)
    db.commit()
    return result


@router.get("/recommendations", response_model=list[CrmRelationshipRecommendation])
def get_relationship_recommendations(
    db: Session = Depends(get_db),
    user: User = Depends(_require_relationships_read()),
) -> list[CrmRelationshipRecommendation]:
    del user
    return get_recommendations(db)


@router.get("/intelligence", response_model=CrmRelationshipIntelligenceDashboard)
def get_intelligence_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(_require_relationships_read()),
) -> CrmRelationshipIntelligenceDashboard:
    del user
    return build_intelligence_dashboard(db)


@router.get("/introduction-paths", response_model=CrmIntroductionPathsResponse)
def get_introduction_paths(
    source_entity_type: str = Query(...),
    source_entity_id: UUID = Query(...),
    target_entity_type: str = Query(...),
    target_entity_id: UUID = Query(...),
    strategy: str = Query(default="shortest"),
    db: Session = Depends(get_db),
    user: User = Depends(_require_relationships_read()),
) -> CrmIntroductionPathsResponse:
    return find_introduction_paths(
        db,
        source_entity_type=source_entity_type,
        source_entity_id=source_entity_id,
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id,
        strategy=strategy,
        include_confidential=can_view_confidential(user),
    )


@router.get("/export", response_class=PlainTextResponse)
def export_relationships(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "export_relationship_graph")),
) -> PlainTextResponse:
    csv_data = export_relationships_csv(db, include_confidential=can_view_confidential(user))
    return PlainTextResponse(csv_data, media_type="text/csv")


@router.post("/bulk-update", response_model=CrmRelationshipBulkActionResponse)
def bulk_update_relationships(
    payload: CrmRelationshipBulkActionRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "bulk_actions")),
) -> CrmRelationshipBulkActionResponse:
    del request
    result = bulk_action(db, payload)
    db.commit()
    return result


@router.get("/saved-views", response_model=list[CrmRelationshipSavedViewResponse])
def get_saved_views(
    db: Session = Depends(get_db),
    user: User = Depends(_require_relationships_read()),
) -> list[CrmRelationshipSavedViewResponse]:
    return list_saved_views(db, user.id)


@router.post("/saved-views", response_model=CrmRelationshipSavedViewResponse, status_code=status.HTTP_201_CREATED)
def post_saved_view(
    payload: CrmRelationshipSavedViewCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "create")),
) -> CrmRelationshipSavedViewResponse:
    result = create_saved_view(db, user.id, payload)
    db.commit()
    return result


@router.get("/referrals", response_model=list[CrmReferralResponse])
def get_referrals(
    db: Session = Depends(get_db),
    user: User = Depends(_require_relationships_read()),
) -> list[CrmReferralResponse]:
    can_comp = can_view_referral_compensation(user)
    return [strip_referral_compensation(r, can_comp) for r in list_referrals(db)]


@router.post("/referrals", response_model=CrmReferralResponse, status_code=status.HTTP_201_CREATED)
def post_referral(
    payload: CrmReferralCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "create")),
) -> CrmReferralResponse:
    referral = create_referral(db, payload)
    db.commit()
    db.refresh(referral)
    result = serialize_referral(db, referral)
    return strip_referral_compensation(result, can_view_referral_compensation(user))


@router.get("/reviews", response_model=list[CrmRelationshipReviewResponse])
def get_reviews(
    relationship_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(_require_relationships_read()),
) -> list[CrmRelationshipReviewResponse]:
    del user
    return list_reviews(db, relationship_id)


@router.post("/reviews", response_model=CrmRelationshipReviewResponse, status_code=status.HTTP_201_CREATED)
def post_review(
    payload: CrmRelationshipReviewCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "create")),
) -> CrmRelationshipReviewResponse:
    review = create_review(db, payload)
    db.commit()
    db.refresh(review)
    return CrmRelationshipReviewResponse(
        id=review.id,
        relationship_id=review.relationship_id,
        reviewer_user_id=review.reviewer_user_id,
        review_date=review.review_date,
        status=review.status.value,
        notes=review.notes,
        scores_snapshot=review.scores_snapshot,
        created_at=review.created_at,
    )


@router.get("/company/{company_id}/decision-map", response_model=CrmDecisionMapResponse)
def get_company_decision_map(
    company_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(_require_relationships_read()),
) -> CrmDecisionMapResponse:
    del user
    return get_decision_map(db, company_id)


@router.put("/company/{company_id}/decision-map", response_model=CrmDecisionMapRoleResponse)
def put_company_decision_map_role(
    company_id: UUID,
    payload: CrmDecisionMapRoleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "update")),
) -> CrmDecisionMapRoleResponse:
    del user
    result = upsert_decision_map_role(db, company_id, payload)
    db.commit()
    return result


@router.get("/{relationship_id}", response_model=CrmRelationshipDetail)
def get_crm_relationship(
    relationship_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(_require_relationships_read()),
) -> CrmRelationshipDetail:
    rel = get_relationship_or_404(db, relationship_id)
    if rel.is_confidential and not can_view_confidential(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Confidential relationship")
    detail = serialize_relationship_detail(db, rel)
    return strip_confidential_fields(detail, can_view_confidential(user))


@router.put("/{relationship_id}", response_model=CrmRelationshipDetail)
def update_crm_relationship(
    relationship_id: UUID,
    payload: CrmRelationshipUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "update")),
) -> CrmRelationshipDetail:
    rel = get_relationship_or_404(db, relationship_id)
    before = snapshot_entity(rel, CRM_RELATIONSHIP_ACTIVITY_FIELDS)
    update_relationship(db, rel, payload)
    record_relationship_updated(db, rel, user, before, request)
    db.commit()
    db.refresh(rel)
    detail = serialize_relationship_detail(db, rel)
    return strip_confidential_fields(detail, can_view_confidential(user))


@router.post("/{relationship_id}/archive", response_model=CrmRelationshipDetail)
def archive_crm_relationship(
    relationship_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "archive")),
) -> CrmRelationshipDetail:
    rel = get_relationship_or_404(db, relationship_id)
    archive_relationship(db, rel)
    record_relationship_archived(db, rel, user, request)
    db.commit()
    db.refresh(rel)
    return serialize_relationship_detail(db, rel)


@router.post("/{relationship_id}/restore", response_model=CrmRelationshipDetail)
def restore_crm_relationship(
    relationship_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "restore")),
) -> CrmRelationshipDetail:
    rel = get_relationship_or_404(db, relationship_id)
    restore_relationship(db, rel)
    record_relationship_restored(db, rel, user, request)
    db.commit()
    db.refresh(rel)
    return serialize_relationship_detail(db, rel)


@router.delete("/{relationship_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_crm_relationship(
    relationship_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "delete")),
) -> None:
    rel = get_relationship_or_404(db, relationship_id)
    record_relationship_deleted(db, rel.id, user, request)
    delete_relationship(db, rel)
    db.commit()
