"""Inventory reservation workflow — centralized status sync and conflict protection."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from investhome_api.models.finance import FinanceTransaction, TransactionStatus, TransactionType
from investhome_api.models.investor import Investor
from investhome_api.models.inventory import (
    ACTIVE_RESERVATION_STATUSES,
    AvailabilityStatus,
    InventoryAsset,
    InventoryAssetStatusHistory,
    InventoryReservation,
    InventoryReservationEvent,
    InventorySalesStatus,
    ReservationRecordStatus,
    ReservationSource,
    ReservationStatus,
    ReservationType,
    StatusCategory,
    TERMINAL_RESERVATION_STATUSES,
)
from investhome_api.models.lead import Lead
from investhome_api.models.user_auth import User
from investhome_api.services.inventory.status_service import update_asset_status

SOFT_HOLD_DEFAULT_HOURS = 48
SOFT_HOLD_REMINDER_HOURS = (24, 4)
DEPOSIT_REMINDER_DAYS = (3, 1)


class ReservationError(ValueError):
    def __init__(self, error_key: str, *, status_code: int = 422) -> None:
        self.error_key = error_key
        self.status_code = status_code
        super().__init__(error_key)


def _now(clock: datetime | None = None) -> datetime:
    return clock or datetime.now(UTC)


def _append_event(
    db: Session,
    reservation: InventoryReservation,
    *,
    event_type: str,
    from_status: str | None,
    to_status: str,
    actor: User | None,
    notes: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> InventoryReservationEvent:
    event = InventoryReservationEvent(
        reservation_id=reservation.id,
        event_type=event_type,
        from_status=from_status,
        to_status=to_status,
        actor_user_id=actor.id if actor else None,
        notes=notes,
        metadata_json=json.dumps(metadata) if metadata else None,
    )
    db.add(event)
    db.flush()
    return event


def _transition(
    db: Session,
    reservation: InventoryReservation,
    *,
    new_status: ReservationRecordStatus,
    event_type: str,
    actor: User | None,
    notes: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> InventoryReservationEvent:
    previous = reservation.status.value
    reservation.status = new_status
    reservation.updated_at = _now()
    return _append_event(
        db,
        reservation,
        event_type=event_type,
        from_status=previous,
        to_status=new_status.value,
        actor=actor,
        notes=notes,
        metadata=metadata,
    )


def _get_active_reservation(db: Session, asset_id: UUID) -> InventoryReservation | None:
    return db.scalar(
        select(InventoryReservation).where(
            InventoryReservation.inventory_asset_id == asset_id,
            InventoryReservation.status.in_(ACTIVE_RESERVATION_STATUSES),
        )
    )


def _lock_asset(db: Session, asset_id: UUID) -> InventoryAsset:
    asset = db.scalar(
        select(InventoryAsset).where(InventoryAsset.id == asset_id).with_for_update()
    )
    if asset is None or asset.archived_at is not None:
        raise ReservationError("inventory.errors.asset_not_found", status_code=404)
    return asset


def _validate_party(db: Session, *, investor_id: UUID | None, lead_id: UUID | None) -> str:
    if investor_id is None and lead_id is None:
        raise ReservationError("inventory.errors.party_required")
    if investor_id is not None:
        investor = db.get(Investor, investor_id)
        if investor is None or investor.archived_at is not None:
            raise ReservationError("inventory.errors.investor_not_found", status_code=404)
        return investor.full_name
    assert lead_id is not None
    lead = db.get(Lead, lead_id)
    if lead is None or lead.archived_at is not None:
        raise ReservationError("inventory.errors.lead_not_found", status_code=404)
    return lead.full_name


def _sync_asset_for_reservation(
    db: Session,
    asset: InventoryAsset,
    reservation: InventoryReservation,
    *,
    actor: User | None,
) -> None:
    """Map reservation workflow to asset status dimensions."""
    if reservation.status in TERMINAL_RESERVATION_STATUSES:
        if reservation.status == ReservationRecordStatus.EXPIRED:
            _set_asset_dimension(
                db, asset, StatusCategory.RESERVATION, ReservationStatus.EXPIRED.value, actor
            )
            if asset.sales_status != InventorySalesStatus.UNDER_CONTRACT:
                _set_asset_dimension(
                    db, asset, StatusCategory.AVAILABILITY, AvailabilityStatus.AVAILABLE.value, actor
                )
                _set_asset_dimension(
                    db, asset, StatusCategory.RESERVATION, ReservationStatus.NONE.value, actor
                )
        elif reservation.status in {
            ReservationRecordStatus.CANCELLED,
            ReservationRecordStatus.REJECTED,
            ReservationRecordStatus.RELEASED,
        }:
            _set_asset_dimension(
                db, asset, StatusCategory.RESERVATION, ReservationStatus.CANCELLED.value, actor
            )
            if asset.sales_status != InventorySalesStatus.UNDER_CONTRACT:
                _set_asset_dimension(
                    db, asset, StatusCategory.AVAILABILITY, AvailabilityStatus.AVAILABLE.value, actor
                )
                _set_asset_dimension(
                    db, asset, StatusCategory.RESERVATION, ReservationStatus.NONE.value, actor
                )
        elif reservation.status == ReservationRecordStatus.CONVERTED:
            _set_asset_dimension(
                db, asset, StatusCategory.RESERVATION, ReservationStatus.CONFIRMED.value, actor
            )
        asset.active_reservation_id = None
        return

    asset.active_reservation_id = reservation.id

    if reservation.status == ReservationRecordStatus.ACTIVE:
        _set_asset_dimension(
            db, asset, StatusCategory.AVAILABILITY, AvailabilityStatus.HOLD.value, actor
        )
        _set_asset_dimension(
            db, asset, StatusCategory.RESERVATION, ReservationStatus.SOFT_HOLD.value, actor
        )
    elif reservation.status in {
        ReservationRecordStatus.REQUESTED,
        ReservationRecordStatus.APPROVED,
        ReservationRecordStatus.DEPOSIT_PENDING,
        ReservationRecordStatus.DEPOSIT_RECEIVED,
    }:
        _set_asset_dimension(
            db, asset, StatusCategory.AVAILABILITY, AvailabilityStatus.HOLD.value, actor
        )
        _set_asset_dimension(
            db, asset, StatusCategory.RESERVATION, ReservationStatus.CONFIRMED.value, actor
        )


def _set_asset_dimension(
    db: Session,
    asset: InventoryAsset,
    category: StatusCategory,
    new_status: str,
    actor: User | None,
) -> None:
    from investhome_api.services.inventory.status_service import _get_current_status

    current = _get_current_status(asset, category)
    if current == new_status:
        return
    try:
        update_asset_status(
            db,
            asset,
            category=category,
            new_status=new_status,
            reason="reservation_sync",
            actor=actor,
        )
    except Exception:
        field_map = {
            StatusCategory.AVAILABILITY: "availability_status",
            StatusCategory.RESERVATION: "reservation_status",
            StatusCategory.SALES: "sales_status",
            StatusCategory.CONSTRUCTION: "construction_status",
            StatusCategory.CLOSING: "closing_status",
            StatusCategory.LEASING: "leasing_status",
        }
        setattr(asset, field_map[category], new_status)
        asset.updated_at = _now()


def _ensure_not_expired(reservation: InventoryReservation, *, clock: datetime | None = None) -> None:
    now = _now(clock)
    if (
        reservation.status == ReservationRecordStatus.ACTIVE
        and reservation.expires_at is not None
        and reservation.expires_at <= now
    ):
        raise ReservationError("inventory.errors.reservation_expired")


def _ensure_active_status(reservation: InventoryReservation, *allowed: ReservationRecordStatus) -> None:
    if reservation.status not in allowed:
        raise ReservationError("inventory.errors.invalid_reservation_state")


def _ensure_no_self_approval(reservation: InventoryReservation, actor: User) -> None:
    if reservation.reserved_by_user_id == actor.id:
        raise ReservationError("inventory.errors.self_approval_blocked")


def create_soft_hold(
    db: Session,
    *,
    asset_id: UUID,
    investor_id: UUID | None,
    lead_id: UUID | None,
    actor: User,
    expires_at: datetime | None = None,
    deposit_amount: Decimal | None = None,
    deposit_currency: str | None = None,
    notes: str | None = None,
    source: ReservationSource = ReservationSource.MANUAL,
    clock: datetime | None = None,
) -> InventoryReservation:
    now = _now(clock)
    _validate_party(db, investor_id=investor_id, lead_id=lead_id)
    asset = _lock_asset(db, asset_id)

    if asset.availability_status != AvailabilityStatus.AVAILABLE:
        raise ReservationError("inventory.errors.asset_not_available")
    if asset.sales_status == InventorySalesStatus.UNDER_CONTRACT:
        raise ReservationError("inventory.errors.asset_under_contract")
    if _get_active_reservation(db, asset.id) is not None:
        raise ReservationError("inventory.errors.active_reservation_exists")

    expiry = expires_at or (now + timedelta(hours=SOFT_HOLD_DEFAULT_HOURS))

    reservation = InventoryReservation(
        inventory_asset_id=asset.id,
        reservation_type=ReservationType.SOFT_HOLD,
        status=ReservationRecordStatus.ACTIVE,
        source=source,
        investor_id=investor_id,
        lead_id=lead_id,
        reserved_by_user_id=actor.id,
        expires_at=expiry,
        deposit_amount=deposit_amount,
        deposit_currency=deposit_currency or asset.currency,
        notes=notes,
        is_demo=asset.is_demo,
    )
    db.add(reservation)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ReservationError("inventory.errors.active_reservation_exists", status_code=409) from exc

    _append_event(
        db,
        reservation,
        event_type="inventory.soft_hold.created",
        from_status=None,
        to_status=ReservationRecordStatus.ACTIVE.value,
        actor=actor,
        notes=notes,
    )
    _sync_asset_for_reservation(db, asset, reservation, actor=actor)
    return reservation


def release_soft_hold(
    db: Session,
    reservation: InventoryReservation,
    *,
    actor: User,
    reason: str | None = None,
) -> InventoryReservation:
    _ensure_active_status(reservation, ReservationRecordStatus.ACTIVE)
    asset = _lock_asset(db, reservation.inventory_asset_id)
    now = _now()
    reservation.released_at = now
    _transition(
        db,
        reservation,
        new_status=ReservationRecordStatus.RELEASED,
        event_type="inventory.soft_hold.released",
        actor=actor,
        notes=reason,
    )
    _sync_asset_for_reservation(db, asset, reservation, actor=actor)
    return reservation


def request_reservation(
    db: Session,
    reservation: InventoryReservation,
    *,
    actor: User,
    notes: str | None = None,
    deposit_amount: Decimal | None = None,
    deposit_due_at: datetime | None = None,
    clock: datetime | None = None,
) -> InventoryReservation:
    _ensure_not_expired(reservation, clock=clock)
    _ensure_active_status(
        reservation,
        ReservationRecordStatus.ACTIVE,
        ReservationRecordStatus.REQUESTED,
    )
    if reservation.status == ReservationRecordStatus.REQUESTED:
        raise ReservationError("inventory.errors.already_requested")

    asset = _lock_asset(db, reservation.inventory_asset_id)
    reservation.reservation_type = ReservationType.RESERVATION
    reservation.requested_at = _now(clock)
    if deposit_amount is not None:
        reservation.deposit_amount = deposit_amount
    if deposit_due_at is not None:
        reservation.deposit_due_at = deposit_due_at

    _transition(
        db,
        reservation,
        new_status=ReservationRecordStatus.REQUESTED,
        event_type="inventory.reservation.requested",
        actor=actor,
        notes=notes,
    )
    _sync_asset_for_reservation(db, asset, reservation, actor=actor)
    return reservation


def approve_reservation(
    db: Session,
    reservation: InventoryReservation,
    *,
    actor: User,
    notes: str | None = None,
    clock: datetime | None = None,
) -> InventoryReservation:
    _ensure_not_expired(reservation, clock=clock)
    _ensure_active_status(reservation, ReservationRecordStatus.REQUESTED)
    _ensure_no_self_approval(reservation, actor)

    asset = _lock_asset(db, reservation.inventory_asset_id)
    reservation.approved_by_user_id = actor.id
    reservation.approved_at = _now(clock)
    _transition(
        db,
        reservation,
        new_status=ReservationRecordStatus.APPROVED,
        event_type="inventory.reservation.approved",
        actor=actor,
        notes=notes,
    )
    _sync_asset_for_reservation(db, asset, reservation, actor=actor)
    return reservation


def reject_reservation(
    db: Session,
    reservation: InventoryReservation,
    *,
    actor: User,
    reason: str,
) -> InventoryReservation:
    _ensure_active_status(
        reservation,
        ReservationRecordStatus.REQUESTED,
        ReservationRecordStatus.APPROVED,
        ReservationRecordStatus.DEPOSIT_PENDING,
    )
    asset = _lock_asset(db, reservation.inventory_asset_id)
    reservation.cancellation_reason = reason
    reservation.cancelled_at = _now()
    _transition(
        db,
        reservation,
        new_status=ReservationRecordStatus.REJECTED,
        event_type="inventory.reservation.rejected",
        actor=actor,
        notes=reason,
    )
    _sync_asset_for_reservation(db, asset, reservation, actor=actor)
    return reservation


def cancel_reservation(
    db: Session,
    reservation: InventoryReservation,
    *,
    actor: User,
    reason: str | None = None,
) -> InventoryReservation:
    if reservation.status in TERMINAL_RESERVATION_STATUSES:
        raise ReservationError("inventory.errors.invalid_reservation_state")

    asset = _lock_asset(db, reservation.inventory_asset_id)
    reservation.cancellation_reason = reason
    reservation.cancelled_at = _now()
    _transition(
        db,
        reservation,
        new_status=ReservationRecordStatus.CANCELLED,
        event_type="inventory.reservation.cancelled",
        actor=actor,
        notes=reason,
    )
    _sync_asset_for_reservation(db, asset, reservation, actor=actor)
    return reservation


def mark_deposit_pending(
    db: Session,
    reservation: InventoryReservation,
    *,
    actor: User,
    deposit_due_at: datetime,
    deposit_amount: Decimal | None = None,
) -> InventoryReservation:
    _ensure_active_status(reservation, ReservationRecordStatus.APPROVED)
    asset = _lock_asset(db, reservation.inventory_asset_id)
    reservation.deposit_due_at = deposit_due_at
    if deposit_amount is not None:
        reservation.deposit_amount = deposit_amount
    _transition(
        db,
        reservation,
        new_status=ReservationRecordStatus.DEPOSIT_PENDING,
        event_type="inventory.reservation.deposit_pending",
        actor=actor,
    )
    _sync_asset_for_reservation(db, asset, reservation, actor=actor)
    return reservation


def mark_deposit_received(
    db: Session,
    reservation: InventoryReservation,
    *,
    actor: User,
    finance_transaction_id: UUID | None = None,
    reference_number: str | None = None,
    received_at: datetime | None = None,
    clock: datetime | None = None,
) -> InventoryReservation:
    _ensure_active_status(
        reservation,
        ReservationRecordStatus.APPROVED,
        ReservationRecordStatus.DEPOSIT_PENDING,
    )
    asset = _lock_asset(db, reservation.inventory_asset_id)
    now = received_at or _now(clock)

    if finance_transaction_id is not None:
        txn = db.get(FinanceTransaction, finance_transaction_id)
        if txn is None or txn.archived_at is not None:
            raise ReservationError("inventory.errors.finance_transaction_not_found", status_code=404)
        reservation.finance_transaction_id = finance_transaction_id
    elif reservation.deposit_amount and reservation.deposit_amount > 0:
        txn = _create_deposit_draft(db, reservation, asset, reference_number=reference_number)
        reservation.finance_transaction_id = txn.id

    reservation.deposit_received_at = now
    _transition(
        db,
        reservation,
        new_status=ReservationRecordStatus.DEPOSIT_RECEIVED,
        event_type="inventory.reservation.deposit_received",
        actor=actor,
        metadata={"finance_transaction_id": str(reservation.finance_transaction_id) if reservation.finance_transaction_id else None},
    )
    _sync_asset_for_reservation(db, asset, reservation, actor=actor)
    return reservation


def _create_deposit_draft(
    db: Session,
    reservation: InventoryReservation,
    asset: InventoryAsset,
    *,
    reference_number: str | None,
) -> FinanceTransaction:
    """Create draft finance transaction for reservation deposit (manual linkage OK)."""
    from investhome_api.models.finance import FinancialAccount

    account = db.scalar(select(FinancialAccount).where(FinancialAccount.archived_at.is_(None)).limit(1))
    if account is None:
        raise ReservationError("inventory.errors.no_financial_account", status_code=422)

    party_name = ""
    if reservation.investor_id:
        inv = db.get(Investor, reservation.investor_id)
        party_name = inv.full_name if inv else ""
    elif reservation.lead_id:
        lead = db.get(Lead, reservation.lead_id)
        party_name = lead.full_name if lead else ""

    txn = FinanceTransaction(
        transaction_date=_now().date(),
        transaction_type=TransactionType.INCOME,
        category="unit_deposit",
        amount=reservation.deposit_amount or Decimal("0"),
        currency=reservation.deposit_currency or asset.currency,
        description=f"Reservation deposit — {asset.display_id} ({party_name})".strip(),
        account_id=account.id,
        project_id=asset.project_id,
        investor_id=reservation.investor_id,
        counterparty=party_name or None,
        reference_number=reference_number,
        status=TransactionStatus.DRAFT,
        is_demo=asset.is_demo,
    )
    db.add(txn)
    db.flush()
    return txn


def convert_reservation(
    db: Session,
    reservation: InventoryReservation,
    *,
    actor: User,
    notes: str | None = None,
    clock: datetime | None = None,
) -> InventoryReservation:
    _ensure_not_expired(reservation, clock=clock)
    _ensure_active_status(
        reservation,
        ReservationRecordStatus.APPROVED,
        ReservationRecordStatus.DEPOSIT_RECEIVED,
    )
    asset = _lock_asset(db, reservation.inventory_asset_id)
    reservation.converted_at = _now(clock)
    _transition(
        db,
        reservation,
        new_status=ReservationRecordStatus.CONVERTED,
        event_type="inventory.reservation.converted",
        actor=actor,
        notes=notes,
    )
    _sync_asset_for_reservation(db, asset, reservation, actor=actor)
    return reservation


def expire_reservation(
    db: Session,
    reservation: InventoryReservation,
    *,
    actor: User | None = None,
    clock: datetime | None = None,
) -> InventoryReservation | None:
    if reservation.status not in ACTIVE_RESERVATION_STATUSES:
        return None
    if reservation.status == ReservationRecordStatus.ACTIVE and reservation.expires_at:
        if reservation.expires_at > _now(clock):
            return None

    asset = _lock_asset(db, reservation.inventory_asset_id)
    reservation.expired_at = _now(clock)
    _transition(
        db,
        reservation,
        new_status=ReservationRecordStatus.EXPIRED,
        event_type="inventory.reservation.expired",
        actor=actor,
    )
    _sync_asset_for_reservation(db, asset, reservation, actor=actor)
    return reservation


def get_valid_actions(reservation: InventoryReservation, *, clock: datetime | None = None) -> list[str]:
    now = _now(clock)
    if reservation.status in TERMINAL_RESERVATION_STATUSES:
        return []

    actions: list[str] = []
    if reservation.status == ReservationRecordStatus.ACTIVE:
        if reservation.expires_at is None or reservation.expires_at > now:
            actions.extend(["release", "request"])
    if reservation.status == ReservationRecordStatus.REQUESTED:
        actions.extend(["approve", "reject", "cancel"])
    if reservation.status == ReservationRecordStatus.APPROVED:
        actions.extend(["deposit_pending", "deposit_received", "convert", "cancel", "reject"])
    if reservation.status == ReservationRecordStatus.DEPOSIT_PENDING:
        actions.extend(["deposit_received", "cancel", "reject"])
    if reservation.status == ReservationRecordStatus.DEPOSIT_RECEIVED:
        actions.append("convert")
    return actions


def enrich_reservation(
    db: Session,
    reservation: InventoryReservation,
    *,
    clock: datetime | None = None,
) -> dict[str, Any]:
    asset = db.get(InventoryAsset, reservation.inventory_asset_id)
    party_name = None
    if reservation.investor_id:
        inv = db.get(Investor, reservation.investor_id)
        party_name = inv.full_name if inv else None
    elif reservation.lead_id:
        lead = db.get(Lead, reservation.lead_id)
        party_name = lead.full_name if lead else None

    seconds_until_expiry = None
    if reservation.expires_at and reservation.status == ReservationRecordStatus.ACTIVE:
        delta = reservation.expires_at - _now(clock)
        seconds_until_expiry = max(int(delta.total_seconds()), 0)

    return {
        "asset_display_id": asset.display_id if asset else None,
        "asset_system_code": asset.system_code if asset else None,
        "party_name": party_name,
        "seconds_until_expiry": seconds_until_expiry,
        "valid_actions": get_valid_actions(reservation, clock=clock),
    }


def list_reservation_events(db: Session, reservation_id: UUID) -> list[InventoryReservationEvent]:
    return list(
        db.scalars(
            select(InventoryReservationEvent)
            .where(InventoryReservationEvent.reservation_id == reservation_id)
            .order_by(InventoryReservationEvent.created_at.desc())
        ).all()
    )


def expire_due_soft_holds(db: Session, *, clock: datetime | None = None) -> list[InventoryReservation]:
    now = _now(clock)
    due = db.scalars(
        select(InventoryReservation).where(
            InventoryReservation.status == ReservationRecordStatus.ACTIVE,
            InventoryReservation.expires_at.is_not(None),
            InventoryReservation.expires_at <= now,
        )
    ).all()
    expired: list[InventoryReservation] = []
    for reservation in due:
        result = expire_reservation(db, reservation, clock=clock)
        if result is not None:
            expired.append(result)
    return expired
