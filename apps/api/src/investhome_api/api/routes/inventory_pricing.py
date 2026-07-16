"""Inventory pricing API routes."""

from datetime import date
from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.activity import ActivityAction, ActivityEntityType
from investhome_api.models.inventory import (
    PENDING_PRICE_REQUEST_STATUSES,
    InventoryAsset,
    InventoryAssetPrice,
    PriceChangeRequest,
    PriceRequestStatus,
    PriceType,
)
from investhome_api.models.project import Project
from investhome_api.models.user_auth import User
from investhome_api.schemas.inventory_pricing import (
    AssetPricingDetailResponse,
    AssetPricingSummary,
    InitialPriceCreate,
    InventoryAssetPriceResponse,
    PriceApprovalRecordResponse,
    PriceChangeRequestCreate,
    PriceChangeRequestListResponse,
    PriceChangeRequestResponse,
    PriceChangeRequestUpdate,
    PriceDecisionInput,
    PriceHistoryEntry,
)
from investhome_api.services.activity_recorder import activity_context_from_request
from investhome_api.services.activity_service import log_activity
from investhome_api.services.inventory.pricing_config import is_high_impact
from investhome_api.services.inventory.pricing_notifications import (
    collect_finance_reviewers,
    notify_price_activated,
    notify_price_approved,
    notify_price_draft_created,
    notify_price_rejected,
    notify_price_submitted,
    notify_revision_requested,
    notify_stale_conflict,
    notify_price_withdrawn,
)
from investhome_api.services.inventory.pricing_service import (
    PricingError,
    approve_price_request,
    archive_draft_price,
    create_initial_price,
    create_price_request,
    enrich_asset_pricing_summary,
    list_approval_records,
    list_current_prices,
    list_price_history,
    list_prices_for_asset,
    mask_amount_for_user,
    reject_price_request,
    request_price_revision,
    review_price_request,
    submit_price_request,
    update_draft_request,
    withdraw_price_request,
)
from investhome_api.services.permission_service import user_has_permission

prices_router = APIRouter(prefix="/inventory/prices", tags=["inventory-pricing"])
requests_router = APIRouter(prefix="/inventory/price-requests", tags=["inventory-pricing"])


def _pricing_error(exc: PricingError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.error_key)


def _get_asset_or_404(asset_id: UUID, db: Session) -> InventoryAsset:
    asset = db.get(InventoryAsset, asset_id)
    if asset is None or asset.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory asset not found")
    return asset


def _get_request_or_404(request_id: UUID, db: Session) -> PriceChangeRequest:
    request = db.get(PriceChangeRequest, request_id)
    if request is None or request.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Price change request not found")
    return request


def _get_price_or_404(price_id: UUID, db: Session) -> InventoryAssetPrice:
    price = db.get(InventoryAssetPrice, price_id)
    if price is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Price not found")
    return price


def _enrich_request(db: Session, request: PriceChangeRequest, user: User) -> PriceChangeRequestResponse:
    asset = db.get(InventoryAsset, request.inventory_asset_id)
    project = db.get(Project, asset.project_id) if asset else None
    actions: list[str] = []
    if request.status == PriceRequestStatus.DRAFT and (
        request.requested_by_user_id == user.id
        or user_has_permission(user, "inventory", "review_price_change")
    ):
        actions.extend(["update", "submit", "withdraw"])
    if request.status in PENDING_PRICE_REQUEST_STATUSES:
        if user_has_permission(user, "inventory", "review_price_change"):
            actions.append("review")
        if user_has_permission(user, "inventory", "approve_price"):
            if request.requested_by_user_id != user.id or user_has_permission(
                user, "inventory", "self_approve_price"
            ):
                actions.append("approve")
        if user_has_permission(user, "inventory", "reject_price"):
            actions.extend(["reject", "request_revision"])
        if request.requested_by_user_id == user.id:
            actions.append("withdraw")
    base = PriceChangeRequestResponse.model_validate(request)
    return base.model_copy(
        update={
            "asset_display_id": asset.display_id if asset else None,
            "asset_system_code": asset.system_code if asset else None,
            "project_id": asset.project_id if asset else None,
            "project_name": project.project_name if project else None,
            "is_high_impact": is_high_impact(request.change_percentage, request.change_amount),
            "valid_actions": actions,
        }
    )


def _log_pricing_activity(
    request: Request,
    db: Session,
    *,
    user: User,
    entity_type: ActivityEntityType,
    entity_id: UUID,
    action: ActivityAction,
    description_key: str,
    metadata: dict | None = None,
    changed_fields: list[str] | None = None,
    previous_values: dict | None = None,
    new_values: dict | None = None,
) -> None:
    log_activity(
        db,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description_key=description_key,
        actor_user=user,
        metadata=metadata,
        changed_fields=changed_fields,
        previous_values=previous_values,
        new_values=new_values,
        request_context=activity_context_from_request(request),
    )


@prices_router.get("/by-asset/{asset_id}", response_model=list[InventoryAssetPriceResponse])
def list_prices_by_asset(
    asset_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view_price")),
) -> list[InventoryAssetPriceResponse]:
    _get_asset_or_404(asset_id, db)
    if not user_has_permission(user, "inventory", "view_price_history"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return [InventoryAssetPriceResponse.model_validate(p) for p in list_prices_for_asset(db, asset_id)]


@prices_router.get("/by-asset/{asset_id}/current", response_model=list[InventoryAssetPriceResponse])
def get_current_prices(
    asset_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view_price")),
) -> list[InventoryAssetPriceResponse]:
    _get_asset_or_404(asset_id, db)
    prices = list_current_prices(db, asset_id)
    from investhome_api.models.inventory import SENSITIVE_PRICE_TYPES

    filtered = [
        p
        for p in prices
        if p.price_type not in SENSITIVE_PRICE_TYPES
        or user_has_permission(user, "inventory", "view_sensitive_price")
    ]
    return [InventoryAssetPriceResponse.model_validate(p) for p in filtered]


@prices_router.get("/by-asset/{asset_id}/history", response_model=list[PriceHistoryEntry])
def get_price_history(
    asset_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view_price_history")),
) -> list[PriceHistoryEntry]:
    _get_asset_or_404(asset_id, db)
    history = list_price_history(db, asset_id)
    entries: list[PriceHistoryEntry] = []
    from investhome_api.models.inventory import SENSITIVE_PRICE_TYPES

    for price in history:
        if price.price_type in SENSITIVE_PRICE_TYPES and not user_has_permission(
            user, "inventory", "view_sensitive_price"
        ):
            continue
        entries.append(
            PriceHistoryEntry(
                price=InventoryAssetPriceResponse.model_validate(price),
                approved_request_id=price.approved_request_id,
            )
        )
    return entries


@prices_router.get("/by-asset/{asset_id}/detail", response_model=AssetPricingDetailResponse)
def get_asset_pricing_detail(
    asset_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view_price")),
) -> AssetPricingDetailResponse:
    asset = _get_asset_or_404(asset_id, db)
    current = get_current_prices(asset_id, db, user)
    pending_query = select(PriceChangeRequest).where(
        PriceChangeRequest.inventory_asset_id == asset_id,
        PriceChangeRequest.status.in_(PENDING_PRICE_REQUEST_STATUSES),
        PriceChangeRequest.archived_at.is_(None),
    )
    pending = [_enrich_request(db, r, user) for r in db.scalars(pending_query).all()]
    history = get_price_history(asset_id, db, user) if user_has_permission(user, "inventory", "view_price_history") else []
    approval_rows = []
    for req in db.scalars(
        select(PriceChangeRequest).where(PriceChangeRequest.inventory_asset_id == asset_id)
    ).all():
        approval_rows.extend(
            PriceApprovalRecordResponse.model_validate(r) for r in list_approval_records(db, req.id)
        )
    _ = asset
    return AssetPricingDetailResponse(
        current_prices=current,
        pending_requests=pending,
        history=history,
        approval_history=sorted(approval_rows, key=lambda r: r.created_at, reverse=True),
    )


@prices_router.get("/by-asset/{asset_id}/summary", response_model=AssetPricingSummary)
def get_asset_pricing_summary(
    asset_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view")),
) -> AssetPricingSummary:
    asset = _get_asset_or_404(asset_id, db)
    summary = enrich_asset_pricing_summary(db, asset, user=user)
    return AssetPricingSummary.model_validate(summary)


@prices_router.post("/initial", response_model=InventoryAssetPriceResponse, status_code=status.HTTP_201_CREATED)
def create_initial(
    payload: InitialPriceCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "create_initial_price")),
) -> InventoryAssetPriceResponse:
    try:
        price = create_initial_price(
            db,
            asset_id=payload.inventory_asset_id,
            price_type=payload.price_type,
            amount=payload.amount,
            currency=payload.currency,
            effective_from=payload.effective_from,
            effective_to=payload.effective_to,
            reason=payload.reason,
            actor=user,
        )
        _log_pricing_activity(
            request,
            db,
            user=user,
            entity_type=ActivityEntityType.INVENTORY_PRICE,
            entity_id=price.id,
            action=ActivityAction.CREATED,
            description_key="activity.inventory.price.initialized",
            new_values={"amount": str(price.amount), "price_type": price.price_type.value},
        )
        db.commit()
        db.refresh(price)
        return InventoryAssetPriceResponse.model_validate(price)
    except PricingError as exc:
        db.rollback()
        raise _pricing_error(exc) from exc


@prices_router.post("/{price_id}/archive", response_model=InventoryAssetPriceResponse)
def archive_price(
    price_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "review_price_change")),
) -> InventoryAssetPriceResponse:
    price = _get_price_or_404(price_id, db)
    try:
        archived = archive_draft_price(db, price, actor=user)
        _log_pricing_activity(
            request,
            db,
            user=user,
            entity_type=ActivityEntityType.INVENTORY_PRICE,
            entity_id=price.id,
            action=ActivityAction.ARCHIVED,
            description_key="activity.inventory.price.archived",
        )
        db.commit()
        db.refresh(archived)
        return InventoryAssetPriceResponse.model_validate(archived)
    except PricingError as exc:
        db.rollback()
        raise _pricing_error(exc) from exc


@requests_router.get("", response_model=PriceChangeRequestListResponse)
def list_price_requests(
    project_id: UUID | None = None,
    inventory_asset_id: UUID | None = None,
    price_type: PriceType | None = None,
    currency: str | None = None,
    status_filter: PriceRequestStatus | None = Query(default=None, alias="status"),
    requester_id: UUID | None = None,
    approver_id: UUID | None = None,
    effective_from: date | None = None,
    include_archived: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view_price")),
) -> PriceChangeRequestListResponse:
    query = select(PriceChangeRequest).join(
        InventoryAsset, InventoryAsset.id == PriceChangeRequest.inventory_asset_id
    )
    if not include_archived:
        query = query.where(PriceChangeRequest.archived_at.is_(None))
    if project_id is not None:
        query = query.where(InventoryAsset.project_id == project_id)
    if inventory_asset_id is not None:
        query = query.where(PriceChangeRequest.inventory_asset_id == inventory_asset_id)
    if price_type is not None:
        query = query.where(PriceChangeRequest.price_type == price_type)
    if currency is not None:
        query = query.where(PriceChangeRequest.currency == currency)
    if status_filter is not None:
        query = query.where(PriceChangeRequest.status == status_filter)
    if requester_id is not None:
        query = query.where(PriceChangeRequest.requested_by_user_id == requester_id)
    if approver_id is not None:
        query = query.where(PriceChangeRequest.assigned_approver_user_id == approver_id)
    if effective_from is not None:
        query = query.where(PriceChangeRequest.effective_from >= effective_from)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    pages = ceil(total / page_size) if total else 0
    rows = db.scalars(
        query.order_by(desc(PriceChangeRequest.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return PriceChangeRequestListResponse(
        items=[_enrich_request(db, row, user) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@requests_router.get("/pending", response_model=PriceChangeRequestListResponse)
def list_pending_approvals(
    project_id: UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "review_price_change")),
) -> PriceChangeRequestListResponse:
    query = (
        select(PriceChangeRequest)
        .join(InventoryAsset, InventoryAsset.id == PriceChangeRequest.inventory_asset_id)
        .where(
            PriceChangeRequest.status.in_(PENDING_PRICE_REQUEST_STATUSES),
            PriceChangeRequest.archived_at.is_(None),
        )
    )
    if project_id is not None:
        query = query.where(InventoryAsset.project_id == project_id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    pages = ceil(total / page_size) if total else 0
    rows = db.scalars(
        query.order_by(desc(PriceChangeRequest.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return PriceChangeRequestListResponse(
        items=[_enrich_request(db, row, user) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@requests_router.get("/by-asset/{asset_id}", response_model=list[PriceChangeRequestResponse])
def list_requests_by_asset(
    asset_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view_price")),
) -> list[PriceChangeRequestResponse]:
    _get_asset_or_404(asset_id, db)
    rows = db.scalars(
        select(PriceChangeRequest)
        .where(
            PriceChangeRequest.inventory_asset_id == asset_id,
            PriceChangeRequest.archived_at.is_(None),
        )
        .order_by(desc(PriceChangeRequest.created_at))
    ).all()
    return [_enrich_request(db, row, user) for row in rows]


@requests_router.get("/by-requester/{user_id}", response_model=list[PriceChangeRequestResponse])
def list_requests_by_requester(
    user_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view_price")),
) -> list[PriceChangeRequestResponse]:
    rows = db.scalars(
        select(PriceChangeRequest)
        .where(
            PriceChangeRequest.requested_by_user_id == user_id,
            PriceChangeRequest.archived_at.is_(None),
        )
        .order_by(desc(PriceChangeRequest.created_at))
    ).all()
    return [_enrich_request(db, row, user) for row in rows]


@requests_router.get("/by-approver/{user_id}", response_model=list[PriceChangeRequestResponse])
def list_requests_by_approver(
    user_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "review_price_change")),
) -> list[PriceChangeRequestResponse]:
    rows = db.scalars(
        select(PriceChangeRequest)
        .where(
            PriceChangeRequest.assigned_approver_user_id == user_id,
            PriceChangeRequest.archived_at.is_(None),
        )
        .order_by(desc(PriceChangeRequest.created_at))
    ).all()
    return [_enrich_request(db, row, user) for row in rows]


@requests_router.get("/{request_id}", response_model=PriceChangeRequestResponse)
def get_price_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view_price")),
) -> PriceChangeRequestResponse:
    return _enrich_request(db, _get_request_or_404(request_id, db), user)


@requests_router.post("", response_model=PriceChangeRequestResponse, status_code=status.HTTP_201_CREATED)
def create_request(
    payload: PriceChangeRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "request_price_change")),
) -> PriceChangeRequestResponse:
    asset = _get_asset_or_404(payload.inventory_asset_id, db)
    try:
        price_request = create_price_request(
            db,
            asset_id=payload.inventory_asset_id,
            price_type=payload.price_type,
            proposed_amount=payload.proposed_amount,
            currency=payload.currency,
            effective_from=payload.effective_from,
            effective_to=payload.effective_to,
            reason=payload.reason,
            supporting_document_id=payload.supporting_document_id,
            assigned_approver_user_id=payload.assigned_approver_user_id,
            actor=user,
            submit=payload.submit,
        )
        _log_pricing_activity(
            request,
            db,
            user=user,
            entity_type=ActivityEntityType.PRICE_CHANGE_REQUEST,
            entity_id=price_request.id,
            action=ActivityAction.UPDATED,
            description_key="activity.inventory.price.submitted",
            new_values={"proposed_amount": str(payload.proposed_amount), "price_type": payload.price_type.value},
        )
        if price_request.status == PriceRequestStatus.DRAFT:
            notify_price_draft_created(db, price_request, display_id=asset.display_id)
        else:
            notify_price_submitted(db, price_request, collect_finance_reviewers(db), display_id=asset.display_id)
        db.commit()
        db.refresh(price_request)
        return _enrich_request(db, price_request, user)
    except PricingError as exc:
        db.rollback()
        raise _pricing_error(exc) from exc


@requests_router.patch("/{request_id}", response_model=PriceChangeRequestResponse)
def update_request(
    request_id: UUID,
    payload: PriceChangeRequestUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "request_price_change")),
) -> PriceChangeRequestResponse:
    price_request = _get_request_or_404(request_id, db)
    try:
        updated = update_draft_request(
            db,
            price_request,
            actor=user,
            proposed_amount=payload.proposed_amount,
            effective_from=payload.effective_from,
            effective_to=payload.effective_to,
            reason=payload.reason,
            supporting_document_id=payload.supporting_document_id,
            assigned_approver_user_id=payload.assigned_approver_user_id,
            clear_assigned_approver=payload.clear_assigned_approver,
        )
        db.commit()
        db.refresh(updated)
        return _enrich_request(db, updated, user)
    except PricingError as exc:
        db.rollback()
        raise _pricing_error(exc) from exc


@requests_router.post("/{request_id}/submit", response_model=PriceChangeRequestResponse)
def submit_request(
    request_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "request_price_change")),
) -> PriceChangeRequestResponse:
    price_request = _get_request_or_404(request_id, db)
    asset = _get_asset_or_404(price_request.inventory_asset_id, db)
    try:
        submitted = submit_price_request(db, price_request, actor=user)
        _log_pricing_activity(
            request,
            db,
            user=user,
            entity_type=ActivityEntityType.PRICE_CHANGE_REQUEST,
            entity_id=price_request.id,
            action=ActivityAction.UPDATED,
            description_key="activity.inventory.price.submitted",
        )
        notify_price_submitted(db, submitted, collect_finance_reviewers(db), display_id=asset.display_id)
        db.commit()
        db.refresh(submitted)
        return _enrich_request(db, submitted, user)
    except PricingError as exc:
        db.rollback()
        if exc.error_key == "inventory.pricing.errors.stale_request":
            notify_stale_conflict(db, price_request, display_id=asset.display_id)
            db.commit()
        raise _pricing_error(exc) from exc


@requests_router.post("/{request_id}/review", response_model=PriceChangeRequestResponse)
def review_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "review_price_change")),
) -> PriceChangeRequestResponse:
    price_request = _get_request_or_404(request_id, db)
    asset = _get_asset_or_404(price_request.inventory_asset_id, db)
    try:
        reviewed = review_price_request(db, price_request, actor=user)
        db.commit()
        db.refresh(reviewed)
        return _enrich_request(db, reviewed, user)
    except PricingError as exc:
        db.rollback()
        if exc.error_key == "inventory.pricing.errors.stale_request":
            notify_stale_conflict(db, price_request, display_id=asset.display_id)
            db.commit()
        raise _pricing_error(exc) from exc


@requests_router.post("/{request_id}/approve", response_model=PriceChangeRequestResponse)
def approve_request(
    request_id: UUID,
    payload: PriceDecisionInput,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "approve_price")),
) -> PriceChangeRequestResponse:
    price_request = _get_request_or_404(request_id, db)
    asset = _get_asset_or_404(price_request.inventory_asset_id, db)
    try:
        approved, new_price = approve_price_request(
            db, price_request, actor=user, comments=payload.comments
        )
        _log_pricing_activity(
            request,
            db,
            user=user,
            entity_type=ActivityEntityType.PRICE_CHANGE_REQUEST,
            entity_id=price_request.id,
            action=ActivityAction.APPROVED,
            description_key="activity.inventory.price.approved",
            new_values={"amount": str(new_price.amount), "price_type": new_price.price_type.value},
        )
        notify_price_approved(db, approved, display_id=asset.display_id)
        notify_price_activated(db, approved, collect_finance_reviewers(db), display_id=asset.display_id, asset=asset)
        db.commit()
        db.refresh(approved)
        return _enrich_request(db, approved, user)
    except PricingError as exc:
        db.rollback()
        if exc.error_key == "inventory.pricing.errors.stale_request":
            notify_stale_conflict(db, price_request, display_id=asset.display_id)
            db.commit()
        raise _pricing_error(exc) from exc


@requests_router.post("/{request_id}/reject", response_model=PriceChangeRequestResponse)
def reject_request(
    request_id: UUID,
    payload: PriceDecisionInput,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "reject_price")),
) -> PriceChangeRequestResponse:
    if not payload.decision_notes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Decision notes required")
    price_request = _get_request_or_404(request_id, db)
    asset = _get_asset_or_404(price_request.inventory_asset_id, db)
    try:
        rejected = reject_price_request(
            db, price_request, actor=user, decision_notes=payload.decision_notes
        )
        _log_pricing_activity(
            request,
            db,
            user=user,
            entity_type=ActivityEntityType.PRICE_CHANGE_REQUEST,
            entity_id=price_request.id,
            action=ActivityAction.REJECTED,
            description_key="activity.inventory.price.rejected",
        )
        notify_price_rejected(db, rejected, display_id=asset.display_id)
        db.commit()
        db.refresh(rejected)
        return _enrich_request(db, rejected, user)
    except PricingError as exc:
        db.rollback()
        raise _pricing_error(exc) from exc


@requests_router.post("/{request_id}/request-revision", response_model=PriceChangeRequestResponse)
def request_revision(
    request_id: UUID,
    payload: PriceDecisionInput,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "review_price_change")),
) -> PriceChangeRequestResponse:
    if not payload.decision_notes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Decision notes required")
    price_request = _get_request_or_404(request_id, db)
    asset = _get_asset_or_404(price_request.inventory_asset_id, db)
    try:
        revised = request_price_revision(
            db, price_request, actor=user, decision_notes=payload.decision_notes
        )
        _log_pricing_activity(
            request,
            db,
            user=user,
            entity_type=ActivityEntityType.PRICE_CHANGE_REQUEST,
            entity_id=price_request.id,
            action=ActivityAction.UPDATED,
            description_key="activity.inventory.price.revision_requested",
        )
        notify_revision_requested(db, revised, display_id=asset.display_id)
        db.commit()
        db.refresh(revised)
        return _enrich_request(db, revised, user)
    except PricingError as exc:
        db.rollback()
        raise _pricing_error(exc) from exc


@requests_router.post("/{request_id}/withdraw", response_model=PriceChangeRequestResponse)
def withdraw_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "request_price_change")),
) -> PriceChangeRequestResponse:
    price_request = _get_request_or_404(request_id, db)
    asset = _get_asset_or_404(price_request.inventory_asset_id, db)
    try:
        withdrawn = withdraw_price_request(db, price_request, actor=user)
        notify_price_withdrawn(
            db,
            withdrawn,
            display_id=asset.display_id,
            reviewer_id=withdrawn.assigned_approver_user_id,
        )
        db.commit()
        db.refresh(withdrawn)
        return _enrich_request(db, withdrawn, user)
    except PricingError as exc:
        db.rollback()
        raise _pricing_error(exc) from exc
