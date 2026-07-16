"""Background jobs for scheduled parking/storage assignments."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from investhome_api.db import session as db_session
from investhome_api.models.inventory import InventoryAsset, InventoryAssetAssignmentRequest
from investhome_api.models.user_auth import User
from investhome_api.services.inventory.assignment_notifications import (
    notify_scheduled_applied,
    notify_scheduled_failed,
)
from investhome_api.services.inventory.assignment_service import (
    AssignmentError,
    apply_scheduled_assignment,
    list_due_scheduled_assignments,
)

JOB_APPLY_SCHEDULED_ASSIGNMENTS = "inventory_apply_scheduled_assignments"


def _requester(db: Session, request: InventoryAssetAssignmentRequest) -> User | None:
    return db.get(User, request.requested_by_user_id)


def run_apply_scheduled_assignments(*, clock: datetime | None = None) -> dict[str, int]:
    """Apply approved future-dated assignments. Idempotent."""
    now = clock or datetime.now(UTC)
    applied = 0
    failed = 0
    with db_session.SessionLocal() as db:
        due = list_due_scheduled_assignments(db, clock=now)
        for request in due:
            asset = db.get(InventoryAsset, request.child_asset_id)
            display_id = asset.display_id if asset else str(request.child_asset_id)
            requester = _requester(db, request)
            users = [requester] if requester else []
            try:
                apply_scheduled_assignment(db, request, clock=now)
                if users:
                    notify_scheduled_applied(db, request, users, display_id=display_id)
                applied += 1
            except AssignmentError:
                if users:
                    notify_scheduled_failed(db, request, users, display_id=display_id)
                failed += 1
        db.commit()
    return {"applied_count": applied, "failed_count": failed}


async def apply_scheduled_assignments_job(ctx: dict) -> dict[str, int]:
    return run_apply_scheduled_assignments()
