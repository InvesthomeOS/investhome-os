"""Background jobs for scheduled ownership transfers."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.db import session as db_session
from investhome_api.models.inventory import InventoryAsset, OwnershipTransferRequest
from investhome_api.models.user_auth import User
from investhome_api.services.inventory.ownership_notifications import (
    notify_scheduled_applied,
    notify_scheduled_failed,
)
from investhome_api.services.inventory.ownership_service import (
    OwnershipError,
    apply_scheduled_transfer,
    list_due_scheduled_transfers,
)

JOB_APPLY_SCHEDULED_TRANSFERS = "inventory_apply_scheduled_transfers"


def _requester(db: Session, request: OwnershipTransferRequest) -> User | None:
    return db.get(User, request.requested_by_user_id)


def run_apply_scheduled_transfers(*, clock: datetime | None = None) -> dict[str, int]:
    """Apply approved future-dated ownership transfers. Idempotent."""
    now = clock or datetime.now(UTC)
    applied = 0
    failed = 0
    with db_session.SessionLocal() as db:
        due = list_due_scheduled_transfers(db, clock=now)
        for request in due:
            asset = db.get(InventoryAsset, request.inventory_asset_id)
            display_id = asset.display_id if asset else str(request.inventory_asset_id)
            requester = _requester(db, request)
            users = [requester] if requester else []
            try:
                apply_scheduled_transfer(db, request, clock=now)
                if users:
                    notify_scheduled_applied(db, request, users, display_id=display_id)
                applied += 1
            except OwnershipError:
                if users:
                    notify_scheduled_failed(db, request, users, display_id=display_id)
                failed += 1
        db.commit()
    return {"applied_count": applied, "failed_count": failed}


async def apply_scheduled_transfers_job(ctx: dict) -> dict[str, int]:
    return run_apply_scheduled_transfers()
