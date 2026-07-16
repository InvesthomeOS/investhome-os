"""Sales inventory matching API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.sales_inventory_matching import (
    MatchRelationshipType,
    MatchStatus,
    SalesInventoryMatch,
    SalesShortlist,
    SalesShortlistItem,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.sales_inventory_matching import (
    CompareRequest,
    CompareResponse,
    InventoryMatchingExecutiveSummary,
    InventorySearchRequest,
    InventorySearchResponse,
    MatchCreate,
    MatchListResponse,
    MatchReject,
    MatchResponse,
    MatchUpdate,
    PreferenceResponse,
    PreferenceSave,
    ReservationRequestPayload,
    ShortlistCreate,
    ShortlistItemCreate,
    ShortlistItemReorder,
    ShortlistItemResponse,
    ShortlistListResponse,
    ShortlistResponse,
    ShortlistUpdate,
    SoftHoldRequest,
    StaleCheckRequest,
    StaleCheckResponse,
)
from investhome_api.schemas.sales_opportunity import ExecutiveSalesSummaryResponse
from investhome_api.services.sales import inventory_matching_service as svc
from investhome_api.services.sales import opportunity_service as opp_svc

router = APIRouter(prefix="/sales", tags=["sales-inventory-matching"])


def _handle_error(exc: svc.InventoryMatchingError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.error_key)


@router.get("/inventory-preferences", response_model=PreferenceResponse)
def get_inventory_preferences(
    lead_id: UUID | None = Query(default=None),
    opportunity_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("sales", "view_inventory_matching")),
) -> PreferenceResponse:
    pref = svc.get_preference(db, lead_id=lead_id, opportunity_id=opportunity_id)
    if pref is None:
        raise HTTPException(status_code=404, detail="sales.errors.preference_not_found")
    return PreferenceResponse(**svc._preference_response(db, pref))


@router.put("/inventory-preferences", response_model=PreferenceResponse)
def save_inventory_preferences(
    body: PreferenceSave,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "save_inventory_preferences")),
) -> PreferenceResponse:
    try:
        pref = svc.save_preference(db, body.model_dump(), actor=user, request=request)
        db.commit()
        return PreferenceResponse(**svc._preference_response(db, pref))
    except svc.InventoryMatchingError as exc:
        db.rollback()
        raise _handle_error(exc) from exc


@router.post("/inventory-matching/search", response_model=InventorySearchResponse)
def search_inventory_for_matching(
    body: InventorySearchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "view_inventory_matching")),
) -> InventorySearchResponse:
    try:
        items, total = svc.search_inventory(db, body.model_dump(), user=user)
        return InventorySearchResponse(
            items=items,
            total=total,
            page=body.page,
            page_size=body.page_size,
        )
    except svc.InventoryMatchingError as exc:
        raise _handle_error(exc) from exc


@router.get("/inventory-matches", response_model=MatchListResponse)
def list_inventory_matches(
    lead_id: UUID | None = Query(default=None),
    opportunity_id: UUID | None = Query(default=None),
    relationship_type: MatchRelationshipType | None = Query(default=None),
    status: MatchStatus | None = Query(default=None),
    exclude_rejected: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "view_inventory_matching")),
) -> MatchListResponse:
    items = svc.list_matches(
        db,
        lead_id=lead_id,
        opportunity_id=opportunity_id,
        relationship_type=relationship_type,
        status=status,
        exclude_rejected=exclude_rejected,
        user=user,
    )
    return MatchListResponse(items=items, total=len(items))


@router.post("/inventory-matches", response_model=MatchResponse, status_code=status.HTTP_201_CREATED)
def create_inventory_match(
    body: MatchCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "add_inventory_match")),
) -> MatchResponse:
    try:
        match = svc.create_match(db, body.model_dump(), actor=user, request=request)
        db.commit()
        db.refresh(match)
        return MatchResponse(**svc._enrich_match(db, match, user=user))
    except svc.InventoryMatchingError as exc:
        db.rollback()
        raise _handle_error(exc) from exc


@router.patch("/inventory-matches/{match_id}", response_model=MatchResponse)
def update_inventory_match(
    match_id: UUID,
    body: MatchUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "add_inventory_match")),
) -> MatchResponse:
    match = db.get(SalesInventoryMatch, match_id)
    if match is None or match.archived_at is not None:
        raise HTTPException(status_code=404, detail="sales.errors.match_not_found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(match, field, value)
    db.commit()
    db.refresh(match)
    return MatchResponse(**svc._enrich_match(db, match, user=user))


@router.delete("/inventory-matches/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_inventory_match(
    match_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "add_inventory_match")),
) -> None:
    match = db.get(SalesInventoryMatch, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="sales.errors.match_not_found")
    svc.archive_match(db, match, actor=user)
    db.commit()


@router.post("/inventory-matches/{match_id}/reject", response_model=MatchResponse)
def reject_inventory_match(
    match_id: UUID,
    body: MatchReject,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "reject_inventory_match")),
) -> MatchResponse:
    match = db.get(SalesInventoryMatch, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="sales.errors.match_not_found")
    try:
        match = svc.reject_match(
            db,
            match,
            rejection_reason=body.rejection_reason,
            notes=body.notes,
            actor=user,
            request=request,
        )
        db.commit()
        db.refresh(match)
        return MatchResponse(**svc._enrich_match(db, match, user=user))
    except svc.InventoryMatchingError as exc:
        db.rollback()
        raise _handle_error(exc) from exc


@router.post("/inventory-matches/{match_id}/set-primary", response_model=MatchResponse)
def set_primary_inventory_match(
    match_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "set_primary_inventory")),
) -> MatchResponse:
    match = db.get(SalesInventoryMatch, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="sales.errors.match_not_found")
    try:
        match = svc.set_primary_match(db, match, actor=user, request=request)
        db.commit()
        db.refresh(match)
        return MatchResponse(**svc._enrich_match(db, match, user=user))
    except svc.InventoryMatchingError as exc:
        db.rollback()
        raise _handle_error(exc) from exc


@router.post("/inventory-matches/{match_id}/favorite", response_model=MatchResponse)
def favorite_inventory_match(
    match_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "add_inventory_match")),
) -> MatchResponse:
    match = db.get(SalesInventoryMatch, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="sales.errors.match_not_found")
    match = svc.favorite_match(db, match, actor=user, request=request)
    db.commit()
    db.refresh(match)
    return MatchResponse(**svc._enrich_match(db, match, user=user))


@router.get("/shortlists", response_model=ShortlistListResponse)
def list_shortlists(
    lead_id: UUID | None = Query(default=None),
    opportunity_id: UUID | None = Query(default=None),
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "view_inventory_matching")),
) -> ShortlistListResponse:
    items = svc.list_shortlists(
        db,
        lead_id=lead_id,
        opportunity_id=opportunity_id,
        include_archived=include_archived,
        user=user,
    )
    return ShortlistListResponse(items=items, total=len(items))


@router.post("/shortlists", response_model=ShortlistResponse, status_code=status.HTTP_201_CREATED)
def create_shortlist(
    body: ShortlistCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "create_shortlist")),
) -> ShortlistResponse:
    try:
        shortlist = svc.create_shortlist(db, body.model_dump(), actor=user, request=request)
        db.commit()
        return ShortlistResponse(**svc._enrich_shortlist(db, shortlist, user=user))
    except svc.InventoryMatchingError as exc:
        db.rollback()
        raise _handle_error(exc) from exc


@router.patch("/shortlists/{shortlist_id}", response_model=ShortlistResponse)
def update_shortlist(
    shortlist_id: UUID,
    body: ShortlistUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_shortlist")),
) -> ShortlistResponse:
    shortlist = db.get(SalesShortlist, shortlist_id)
    if shortlist is None or shortlist.archived_at is not None:
        raise HTTPException(status_code=404, detail="sales.errors.shortlist_not_found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(shortlist, field, value)
    db.commit()
    db.refresh(shortlist)
    return ShortlistResponse(**svc._enrich_shortlist(db, shortlist, user=user))


@router.delete("/shortlists/{shortlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_shortlist(
    shortlist_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "archive_shortlist")),
) -> None:
    shortlist = db.get(SalesShortlist, shortlist_id)
    if shortlist is None:
        raise HTTPException(status_code=404, detail="sales.errors.shortlist_not_found")
    svc.archive_shortlist(db, shortlist, actor=user)
    db.commit()


@router.post("/shortlists/{shortlist_id}/items", response_model=ShortlistItemResponse, status_code=status.HTTP_201_CREATED)
def add_shortlist_item(
    shortlist_id: UUID,
    body: ShortlistItemCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_shortlist")),
) -> ShortlistItemResponse:
    shortlist = db.get(SalesShortlist, shortlist_id)
    if shortlist is None:
        raise HTTPException(status_code=404, detail="sales.errors.shortlist_not_found")
    try:
        item = svc.add_shortlist_item(
            db,
            shortlist,
            inventory_asset_id=body.inventory_asset_id,
            notes=body.notes,
            is_favorite=body.is_favorite,
            actor=user,
            request=request,
        )
        db.commit()
        return ShortlistItemResponse(**svc._enrich_shortlist_item(db, item, user=user))
    except svc.InventoryMatchingError as exc:
        db.rollback()
        raise _handle_error(exc) from exc


@router.patch("/shortlists/{shortlist_id}/items/reorder", response_model=ShortlistResponse)
def reorder_shortlist_items(
    shortlist_id: UUID,
    body: ShortlistItemReorder,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_shortlist")),
) -> ShortlistResponse:
    shortlist = db.get(SalesShortlist, shortlist_id)
    if shortlist is None:
        raise HTTPException(status_code=404, detail="sales.errors.shortlist_not_found")
    svc.reorder_shortlist_items(db, shortlist, body.item_ids, actor=user)
    db.commit()
    return ShortlistResponse(**svc._enrich_shortlist(db, shortlist, user=user))


@router.delete("/shortlists/{shortlist_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_shortlist_item(
    shortlist_id: UUID,
    item_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_shortlist")),
) -> None:
    item = db.get(SalesShortlistItem, item_id)
    if item is None or item.shortlist_id != shortlist_id:
        raise HTTPException(status_code=404, detail="sales.errors.shortlist_item_not_found")
    db.delete(item)
    db.commit()


@router.post("/shortlists/{shortlist_id}/duplicate", response_model=ShortlistResponse, status_code=status.HTTP_201_CREATED)
def duplicate_shortlist(
    shortlist_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "create_shortlist")),
) -> ShortlistResponse:
    shortlist = db.get(SalesShortlist, shortlist_id)
    if shortlist is None:
        raise HTTPException(status_code=404, detail="sales.errors.shortlist_not_found")
    new_list = svc.duplicate_shortlist(db, shortlist, actor=user, request=request)
    db.commit()
    return ShortlistResponse(**svc._enrich_shortlist(db, new_list, user=user))


@router.post("/inventory-matching/compare", response_model=CompareResponse)
def compare_inventory_assets(
    body: CompareRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "compare_inventory")),
) -> CompareResponse:
    try:
        items = svc.compare_assets(db, body.asset_ids, user=user)
        return CompareResponse(items=items)
    except svc.InventoryMatchingError as exc:
        raise _handle_error(exc) from exc


@router.post("/inventory-matching/soft-hold")
def create_soft_hold(
    body: SoftHoldRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "create_soft_hold")),
):
    try:
        reservation = svc.create_soft_hold_from_sales(
            db,
            inventory_asset_id=body.inventory_asset_id,
            lead_id=body.lead_id,
            opportunity_id=body.opportunity_id,
            notes=body.notes,
            deposit_amount=body.deposit_amount,
            actor=user,
            request=request,
        )
        db.commit()
        from investhome_api.api.routes.inventory_reservations import _to_response

        return _to_response(db, reservation)
    except svc.InventoryMatchingError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    except Exception as exc:
        db.rollback()
        if hasattr(exc, "error_key"):
            raise HTTPException(status_code=getattr(exc, "status_code", 422), detail=exc.error_key) from exc
        raise


@router.post("/inventory-matching/reservation-request")
def request_reservation(
    body: ReservationRequestPayload,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "request_reservation")),
):
    try:
        reservation = svc.request_reservation_from_sales(
            db,
            body.reservation_id,
            notes=body.notes,
            deposit_amount=body.deposit_amount,
            actor=user,
            request=request,
        )
        db.commit()
        from investhome_api.api.routes.inventory_reservations import _to_response

        return _to_response(db, reservation)
    except svc.InventoryMatchingError as exc:
        db.rollback()
        raise _handle_error(exc) from exc


@router.get("/inventory-matching/stale-check", response_model=StaleCheckResponse)
def stale_check(
    asset_ids: list[UUID] = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "view_inventory_matching")),
) -> StaleCheckResponse:
    items = svc.stale_check(db, asset_ids, {}, user=user)
    return StaleCheckResponse(items=items)


@router.post("/inventory-matching/stale-check", response_model=StaleCheckResponse)
def stale_check_post(
    body: StaleCheckRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "view_inventory_matching")),
) -> StaleCheckResponse:
    items = svc.stale_check(db, body.asset_ids, body.snapshots, user=user)
    return StaleCheckResponse(items=items)


@router.get("/inventory-matching/executive-summary", response_model=InventoryMatchingExecutiveSummary)
def get_matching_executive_summary(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("sales", "view_pipeline")),
) -> InventoryMatchingExecutiveSummary:
    return InventoryMatchingExecutiveSummary(**svc.build_matching_executive_summary(db))


@router.get("/inventory-matching/executive-summary/combined")
def get_combined_executive_summary(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("sales", "view_pipeline")),
) -> dict:
    base = opp_svc.build_executive_summary(db)
    matching = svc.build_matching_executive_summary(db)
    return {**base, **matching}
