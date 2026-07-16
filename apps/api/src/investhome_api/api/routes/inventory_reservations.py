"""Inventory reservation API routes."""

from datetime import UTC, datetime, timedelta
from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.activity import ActivityAction, ActivityEntityType
from investhome_api.models.inventory import (
    ACTIVE_RESERVATION_STATUSES,
    InventoryAsset,
    InventoryReservation,
    ReservationRecordStatus,
    ReservationType,
)
from investhome_api.models.investor import Investor
from investhome_api.models.lead import Lead
from investhome_api.models.user_auth import User
from investhome_api.schemas.inventory_reservations import (
    DepositPendingMark,
    DepositReceivedMark,
    ReservationApprove,
    ReservationCancel,
    ReservationConvert,
    ReservationEventResponse,
    ReservationHistoryResponse,
    ReservationListResponse,
    ReservationReject,
    ReservationRequestCreate,
    ReservationResponse,
    SoftHoldCreate,
)
from investhome_api.services.activity_recorder import activity_context_from_request
from investhome_api.services.activity_service import log_activity
from investhome_api.services.inventory.reservation_notifications import (
    notify_reservation_approved,
    notify_soft_hold_created,
)
from investhome_api.services.inventory.reservation_service import (
    ReservationError,
    approve_reservation,
    cancel_reservation,
    convert_reservation,
    create_soft_hold,
    enrich_reservation,
    expire_reservation,
    list_reservation_events,
    mark_deposit_pending,
    mark_deposit_received,
    reject_reservation,
    release_soft_hold,
    request_reservation,
)

router = APIRouter(prefix="/inventory/reservations", tags=["inventory-reservations"])


def _reservation_error(exc: ReservationError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.error_key)


def _get_reservation_or_404(reservation_id: UUID, db: Session) -> InventoryReservation:
    reservation = db.get(InventoryReservation, reservation_id)
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    return reservation


def _to_response(db: Session, reservation: InventoryReservation) -> ReservationResponse:
    extra = enrich_reservation(db, reservation)
    base = ReservationResponse.model_validate(reservation)
    return base.model_copy(update=extra)


def _log_reservation_activity(
    db: Session,
    *,
    reservation: InventoryReservation,
    description_key: str,
    actor: User,
    request: Request | None,
    metadata: dict | None = None,
) -> None:
    asset = db.get(InventoryAsset, reservation.inventory_asset_id)
    log_activity(
        db,
        action=ActivityAction.STATUS_CHANGED,
        entity_type=ActivityEntityType.INVENTORY_ASSET,
        entity_id=reservation.inventory_asset_id,
        description_key=description_key,
        actor_user=actor,
        metadata={
            "reservation_id": str(reservation.id),
            "display_id": asset.display_id if asset else None,
            "status": reservation.status.value,
            **(metadata or {}),
        },
        request_context=activity_context_from_request(request) if request else None,
        is_demo=reservation.is_demo,
    )


@router.get("", response_model=ReservationListResponse)
def list_reservations(
    project_id: UUID | None = None,
    inventory_asset_id: UUID | None = None,
    investor_id: UUID | None = None,
    lead_id: UUID | None = None,
    reservation_type: ReservationType | None = None,
    status_filter: ReservationRecordStatus | None = Query(default=None, alias="status"),
    active_only: bool = Query(default=False),
    expiring_within_hours: int | None = Query(default=None, ge=1, le=168),
    search: str | None = Query(default=None, max_length=255),
    sort_by: str = Query(default="updated_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("inventory", "view")),
) -> ReservationListResponse:
    sort_columns = {
        "updated_at": InventoryReservation.updated_at,
        "created_at": InventoryReservation.created_at,
        "expires_at": InventoryReservation.expires_at,
        "status": InventoryReservation.status,
    }
    sort_column = sort_columns.get(sort_by, InventoryReservation.updated_at)
    order_fn = asc if sort_order == "asc" else desc

    query = select(InventoryReservation)
    if project_id is not None or search:
        query = query.join(InventoryAsset, InventoryAsset.id == InventoryReservation.inventory_asset_id)
    if project_id is not None:
        query = query.where(InventoryAsset.project_id == project_id)
    if inventory_asset_id is not None:
        query = query.where(InventoryReservation.inventory_asset_id == inventory_asset_id)
    if investor_id is not None:
        query = query.where(InventoryReservation.investor_id == investor_id)
    if lead_id is not None:
        query = query.where(InventoryReservation.lead_id == lead_id)
    if reservation_type is not None:
        query = query.where(InventoryReservation.reservation_type == reservation_type)
    if status_filter is not None:
        query = query.where(InventoryReservation.status == status_filter)
    if active_only:
        query = query.where(InventoryReservation.status.in_(ACTIVE_RESERVATION_STATUSES))
    if expiring_within_hours is not None:
        cutoff = datetime.now(UTC) + timedelta(hours=expiring_within_hours)
        query = query.where(
            InventoryReservation.status == ReservationRecordStatus.ACTIVE,
            InventoryReservation.expires_at.is_not(None),
            InventoryReservation.expires_at <= cutoff,
            InventoryReservation.expires_at > datetime.now(UTC),
        )
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                InventoryAsset.display_id.ilike(pattern),
                InventoryAsset.system_code.ilike(pattern),
            )
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(order_fn(sort_column)).offset((page - 1) * page_size).limit(page_size)
    ).all()
    pages = ceil(total / page_size) if total else 0
    return ReservationListResponse(
        items=[_to_response(db, row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/expiring", response_model=ReservationListResponse)
def list_expiring_reservations(
    within_hours: int = Query(default=48, ge=1, le=168),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("inventory", "view")),
) -> ReservationListResponse:
    return list_reservations(
        active_only=False,
        expiring_within_hours=within_hours,
        page=page,
        page_size=page_size,
        db=db,
        _user=_user,
    )


@router.get("/overdue-deposits", response_model=ReservationListResponse)
def list_overdue_deposits(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("inventory", "view")),
) -> ReservationListResponse:
    query = select(InventoryReservation).where(
        InventoryReservation.status == ReservationRecordStatus.DEPOSIT_PENDING,
        InventoryReservation.deposit_due_at.is_not(None),
        InventoryReservation.deposit_due_at < datetime.now(UTC),
    )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(InventoryReservation.deposit_due_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    pages = ceil(total / page_size) if total else 0
    return ReservationListResponse(
        items=[_to_response(db, row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/by-asset/{asset_id}/history", response_model=list[ReservationHistoryResponse])
def history_by_asset(
    asset_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("inventory", "view")),
) -> list[ReservationHistoryResponse]:
    reservations = db.scalars(
        select(InventoryReservation)
        .where(InventoryReservation.inventory_asset_id == asset_id)
        .order_by(InventoryReservation.created_at.desc())
    ).all()
    return [
        ReservationHistoryResponse(
            reservation=_to_response(db, r),
            events=[
                ReservationEventResponse.model_validate(e) for e in list_reservation_events(db, r.id)
            ],
        )
        for r in reservations
    ]


@router.get("/by-party/{party_id}", response_model=ReservationListResponse)
def list_by_party(
    party_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("inventory", "view")),
) -> ReservationListResponse:
    query = select(InventoryReservation).where(
        or_(
            InventoryReservation.investor_id == party_id,
            InventoryReservation.lead_id == party_id,
        )
    )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(InventoryReservation.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    pages = ceil(total / page_size) if total else 0
    return ReservationListResponse(
        items=[_to_response(db, row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{reservation_id}", response_model=ReservationResponse)
def get_reservation(
    reservation_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("inventory", "view")),
) -> ReservationResponse:
    return _to_response(db, _get_reservation_or_404(reservation_id, db))


@router.get("/{reservation_id}/events", response_model=list[ReservationEventResponse])
def get_reservation_events(
    reservation_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("inventory", "view")),
) -> list[ReservationEventResponse]:
    _get_reservation_or_404(reservation_id, db)
    events = list_reservation_events(db, reservation_id)
    return [ReservationEventResponse.model_validate(e) for e in events]


@router.post("/soft-hold", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
def create_soft_hold_endpoint(
    payload: SoftHoldCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "reserve")),
) -> ReservationResponse:
    try:
        reservation = create_soft_hold(
            db,
            asset_id=payload.inventory_asset_id,
            investor_id=payload.investor_id,
            lead_id=payload.lead_id,
            actor=actor,
            expires_at=payload.expires_at,
            deposit_amount=payload.deposit_amount,
            deposit_currency=payload.deposit_currency,
            notes=payload.notes,
            source=payload.source,
        )
        extra = enrich_reservation(db, reservation)
        _log_reservation_activity(
            db,
            reservation=reservation,
            description_key="activity.inventory.reservation.soft_hold_created",
            actor=actor,
            request=request,
            metadata={"party_name": extra.get("party_name")},
        )
        notify_soft_hold_created(
            db,
            reservation,
            display_id=extra.get("asset_display_id") or "",
            party_name=extra.get("party_name") or "",
        )
        db.commit()
    except ReservationError as exc:
        db.rollback()
        raise _reservation_error(exc) from exc
    db.refresh(reservation)
    return _to_response(db, reservation)


@router.post("/{reservation_id}/release", response_model=ReservationResponse)
def release_hold_endpoint(
    reservation_id: UUID,
    payload: ReservationCancel,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "release_hold")),
) -> ReservationResponse:
    reservation = _get_reservation_or_404(reservation_id, db)
    try:
        reservation = release_soft_hold(db, reservation, actor=actor, reason=payload.reason)
        _log_reservation_activity(
            db,
            reservation=reservation,
            description_key="activity.inventory.reservation.released",
            actor=actor,
            request=request,
        )
        db.commit()
    except ReservationError as exc:
        db.rollback()
        raise _reservation_error(exc) from exc
    db.refresh(reservation)
    return _to_response(db, reservation)


@router.post("/{reservation_id}/request", response_model=ReservationResponse)
def request_reservation_endpoint(
    reservation_id: UUID,
    payload: ReservationRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "request_reservation")),
) -> ReservationResponse:
    reservation = _get_reservation_or_404(reservation_id, db)
    try:
        reservation = request_reservation(
            db,
            reservation,
            actor=actor,
            notes=payload.notes,
            deposit_amount=payload.deposit_amount,
            deposit_due_at=payload.deposit_due_at,
        )
        _log_reservation_activity(
            db,
            reservation=reservation,
            description_key="activity.inventory.reservation.requested",
            actor=actor,
            request=request,
        )
        db.commit()
    except ReservationError as exc:
        db.rollback()
        raise _reservation_error(exc) from exc
    db.refresh(reservation)
    return _to_response(db, reservation)


@router.post("/{reservation_id}/approve", response_model=ReservationResponse)
def approve_reservation_endpoint(
    reservation_id: UUID,
    payload: ReservationApprove,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "approve_reservation")),
) -> ReservationResponse:
    reservation = _get_reservation_or_404(reservation_id, db)
    try:
        reservation = approve_reservation(db, reservation, actor=actor, notes=payload.notes)
        extra = enrich_reservation(db, reservation)
        _log_reservation_activity(
            db,
            reservation=reservation,
            description_key="activity.inventory.reservation.approved",
            actor=actor,
            request=request,
        )
        notify_reservation_approved(
            db,
            reservation,
            display_id=extra.get("asset_display_id") or "",
        )
        db.commit()
    except ReservationError as exc:
        db.rollback()
        raise _reservation_error(exc) from exc
    db.refresh(reservation)
    return _to_response(db, reservation)


@router.post("/{reservation_id}/reject", response_model=ReservationResponse)
def reject_reservation_endpoint(
    reservation_id: UUID,
    payload: ReservationReject,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "approve_reservation")),
) -> ReservationResponse:
    reservation = _get_reservation_or_404(reservation_id, db)
    try:
        reservation = reject_reservation(db, reservation, actor=actor, reason=payload.reason)
        _log_reservation_activity(
            db,
            reservation=reservation,
            description_key="activity.inventory.reservation.rejected",
            actor=actor,
            request=request,
        )
        db.commit()
    except ReservationError as exc:
        db.rollback()
        raise _reservation_error(exc) from exc
    db.refresh(reservation)
    return _to_response(db, reservation)


@router.post("/{reservation_id}/cancel", response_model=ReservationResponse)
def cancel_reservation_endpoint(
    reservation_id: UUID,
    payload: ReservationCancel,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "cancel_reservation")),
) -> ReservationResponse:
    reservation = _get_reservation_or_404(reservation_id, db)
    try:
        reservation = cancel_reservation(db, reservation, actor=actor, reason=payload.reason)
        _log_reservation_activity(
            db,
            reservation=reservation,
            description_key="activity.inventory.reservation.cancelled",
            actor=actor,
            request=request,
        )
        db.commit()
    except ReservationError as exc:
        db.rollback()
        raise _reservation_error(exc) from exc
    db.refresh(reservation)
    return _to_response(db, reservation)


@router.post("/{reservation_id}/deposit-pending", response_model=ReservationResponse)
def deposit_pending_endpoint(
    reservation_id: UUID,
    payload: DepositPendingMark,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "mark_deposit_received")),
) -> ReservationResponse:
    reservation = _get_reservation_or_404(reservation_id, db)
    try:
        reservation = mark_deposit_pending(
            db,
            reservation,
            actor=actor,
            deposit_due_at=payload.deposit_due_at,
            deposit_amount=payload.deposit_amount,
        )
        _log_reservation_activity(
            db,
            reservation=reservation,
            description_key="activity.inventory.reservation.deposit_pending",
            actor=actor,
            request=request,
        )
        db.commit()
    except ReservationError as exc:
        db.rollback()
        raise _reservation_error(exc) from exc
    db.refresh(reservation)
    return _to_response(db, reservation)


@router.post("/{reservation_id}/deposit-received", response_model=ReservationResponse)
def deposit_received_endpoint(
    reservation_id: UUID,
    payload: DepositReceivedMark,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "mark_deposit_received")),
) -> ReservationResponse:
    reservation = _get_reservation_or_404(reservation_id, db)
    try:
        reservation = mark_deposit_received(
            db,
            reservation,
            actor=actor,
            finance_transaction_id=payload.finance_transaction_id,
            reference_number=payload.reference_number,
            received_at=payload.received_at,
        )
        _log_reservation_activity(
            db,
            reservation=reservation,
            description_key="activity.inventory.reservation.deposit_received",
            actor=actor,
            request=request,
        )
        db.commit()
    except ReservationError as exc:
        db.rollback()
        raise _reservation_error(exc) from exc
    db.refresh(reservation)
    return _to_response(db, reservation)


@router.post("/{reservation_id}/convert", response_model=ReservationResponse)
def convert_reservation_endpoint(
    reservation_id: UUID,
    payload: ReservationConvert,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "convert_reservation")),
) -> ReservationResponse:
    reservation = _get_reservation_or_404(reservation_id, db)
    try:
        reservation = convert_reservation(db, reservation, actor=actor, notes=payload.notes)
        _log_reservation_activity(
            db,
            reservation=reservation,
            description_key="activity.inventory.reservation.converted",
            actor=actor,
            request=request,
        )
        db.commit()
    except ReservationError as exc:
        db.rollback()
        raise _reservation_error(exc) from exc
    db.refresh(reservation)
    return _to_response(db, reservation)


@router.post("/{reservation_id}/expire", response_model=ReservationResponse)
def expire_reservation_endpoint(
    reservation_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "manage_status")),
) -> ReservationResponse:
    reservation = _get_reservation_or_404(reservation_id, db)
    try:
        result = expire_reservation(db, reservation, actor=actor)
        if result is None:
            raise ReservationError("inventory.errors.invalid_reservation_state")
        _log_reservation_activity(
            db,
            reservation=result,
            description_key="activity.inventory.reservation.expired",
            actor=actor,
            request=request,
        )
        db.commit()
        reservation = result
    except ReservationError as exc:
        db.rollback()
        raise _reservation_error(exc) from exc
    db.refresh(reservation)
    return _to_response(db, reservation)
