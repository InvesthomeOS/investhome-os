"""Background jobs for inventory reservation lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.db.session import SessionLocal
from investhome_api.models.inventory import (
    InventoryAsset,
    InventoryReservation,
    ReservationRecordStatus,
)
from investhome_api.models.user_auth import Role, User, UserRole
from investhome_api.services.inventory.reservation_notifications import (
    notify_deposit_overdue,
    notify_reservation_expired,
    notify_reservation_expiring,
)
from investhome_api.services.inventory.reservation_service import (
    DEPOSIT_REMINDER_DAYS,
    SOFT_HOLD_REMINDER_HOURS,
    expire_due_soft_holds,
)

JOB_EXPIRE_SOFT_HOLDS = "inventory_expire_soft_holds"
JOB_RESERVATION_REMINDERS = "inventory_reservation_reminders"
JOB_OVERDUE_DEPOSITS = "inventory_overdue_deposits"


def _sales_users(db: Session) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(Role.code == "sales", User.archived_at.is_(None))
        ).all()
    )


def _reservation_users(db: Session, reservation: InventoryReservation) -> list[User]:
    users: list[User] = []
    if reservation.reserved_by_user_id:
        user = db.get(User, reservation.reserved_by_user_id)
        if user:
            users.append(user)
    for sales_user in _sales_users(db):
        if sales_user.id not in {u.id for u in users}:
            users.append(sales_user)
    return users


def run_expire_soft_holds(*, clock: datetime | None = None) -> dict[str, int]:
    """Expire active soft holds past expires_at. Idempotent."""
    now = clock or datetime.now(UTC)
    with SessionLocal() as db:
        expired = expire_due_soft_holds(db, clock=now)
        for reservation in expired:
            asset = db.get(InventoryAsset, reservation.inventory_asset_id)
            display_id = asset.display_id if asset else str(reservation.inventory_asset_id)
            notify_reservation_expired(
                db,
                reservation,
                _reservation_users(db, reservation),
                display_id=display_id,
            )
        db.commit()
        return {"expired_count": len(expired)}


def run_reservation_reminders(*, clock: datetime | None = None) -> dict[str, int]:
    """Send 24h and 4h expiry reminders for active soft holds."""
    now = clock or datetime.now(UTC)
    sent = 0
    with SessionLocal() as db:
        active = db.scalars(
            select(InventoryReservation).where(
                InventoryReservation.status == ReservationRecordStatus.ACTIVE,
                InventoryReservation.expires_at.is_not(None),
                InventoryReservation.expires_at > now,
            )
        ).all()
        for reservation in active:
            if reservation.expires_at is None:
                continue
            hours_left = (reservation.expires_at - now).total_seconds() / 3600
            for threshold in SOFT_HOLD_REMINDER_HOURS:
                if threshold - 0.5 <= hours_left <= threshold + 0.5:
                    asset = db.get(InventoryAsset, reservation.inventory_asset_id)
                    display_id = asset.display_id if asset else ""
                    notify_reservation_expiring(
                        db,
                        reservation,
                        _reservation_users(db, reservation),
                        display_id=display_id,
                        hours_remaining=int(threshold),
                    )
                    sent += 1
        db.commit()
    return {"reminders_sent": sent}


def run_overdue_deposit_reminders(*, clock: datetime | None = None) -> dict[str, int]:
    """Notify on overdue deposit due dates and upcoming 3-day/1-day reminders."""
    now = clock or datetime.now(UTC)
    sent = 0
    with SessionLocal() as db:
        pending = db.scalars(
            select(InventoryReservation).where(
                InventoryReservation.status == ReservationRecordStatus.DEPOSIT_PENDING,
                InventoryReservation.deposit_due_at.is_not(None),
            )
        ).all()
        for reservation in pending:
            if reservation.deposit_due_at is None:
                continue
            asset = db.get(InventoryAsset, reservation.inventory_asset_id)
            display_id = asset.display_id if asset else ""
            if reservation.deposit_due_at <= now:
                days_overdue = max((now - reservation.deposit_due_at).days, 1)
                notify_deposit_overdue(
                    db,
                    reservation,
                    _sales_users(db),
                    display_id=display_id,
                    days_overdue=days_overdue,
                )
                sent += 1
                continue
            days_left = (reservation.deposit_due_at - now).days
            for threshold in DEPOSIT_REMINDER_DAYS:
                if days_left == threshold:
                    notify_reservation_expiring(
                        db,
                        reservation,
                        _sales_users(db),
                        display_id=display_id,
                        hours_remaining=threshold * 24,
                    )
                    sent += 1
        db.commit()
    return {"deposit_notifications_sent": sent}


async def expire_soft_holds_job(ctx: dict) -> dict[str, int]:
    return run_expire_soft_holds()


async def reservation_reminders_job(ctx: dict) -> dict[str, int]:
    return run_reservation_reminders()


async def overdue_deposits_job(ctx: dict) -> dict[str, int]:
    return run_overdue_deposit_reminders()
