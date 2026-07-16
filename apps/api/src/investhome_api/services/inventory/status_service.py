"""Inventory asset status update with append-only history."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from investhome_api.models.inventory import (
    AvailabilityStatus,
    ClosingStatus,
    ConstructionStatus,
    InventoryAsset,
    InventoryAssetStatusHistory,
    InventorySalesStatus,
    LeasingStatus,
    ReservationStatus,
    StatusCategory,
)
from investhome_api.models.user_auth import User

STATUS_FIELD_BY_CATEGORY: dict[StatusCategory, str] = {
    StatusCategory.AVAILABILITY: "availability_status",
    StatusCategory.RESERVATION: "reservation_status",
    StatusCategory.SALES: "sales_status",
    StatusCategory.CONSTRUCTION: "construction_status",
    StatusCategory.CLOSING: "closing_status",
    StatusCategory.LEASING: "leasing_status",
}

STATUS_ENUM_BY_CATEGORY = {
    StatusCategory.AVAILABILITY: AvailabilityStatus,
    StatusCategory.RESERVATION: ReservationStatus,
    StatusCategory.SALES: InventorySalesStatus,
    StatusCategory.CONSTRUCTION: ConstructionStatus,
    StatusCategory.CLOSING: ClosingStatus,
    StatusCategory.LEASING: LeasingStatus,
}


class StatusTransitionError(ValueError):
    def __init__(self, error_key: str) -> None:
        self.error_key = error_key
        super().__init__(error_key)


def _get_current_status(asset: InventoryAsset, category: StatusCategory) -> str:
    field = STATUS_FIELD_BY_CATEGORY[category]
    value = getattr(asset, field)
    return value.value if hasattr(value, "value") else str(value)


def update_asset_status(
    db: Session,
    asset: InventoryAsset,
    *,
    category: StatusCategory,
    new_status: str,
    reason: str | None,
    actor: User | None,
    effective_at: datetime | None = None,
) -> InventoryAssetStatusHistory:
    """Update one status dimension and append history row."""
    enum_cls = STATUS_ENUM_BY_CATEGORY[category]
    try:
        parsed_status = enum_cls(new_status)
    except ValueError as exc:
        raise StatusTransitionError("inventory.errors.invalid_status_value") from exc

    previous = _get_current_status(asset, category)
    if previous == parsed_status.value:
        raise StatusTransitionError("inventory.errors.status_unchanged")

    field = STATUS_FIELD_BY_CATEGORY[category]
    setattr(asset, field, parsed_status)
    asset.updated_at = datetime.now(UTC)

    history = InventoryAssetStatusHistory(
        inventory_asset_id=asset.id,
        status_category=category,
        previous_status=previous,
        new_status=parsed_status.value,
        reason=reason,
        changed_by_user_id=actor.id if actor else None,
        effective_at=effective_at or datetime.now(UTC),
    )
    db.add(history)
    db.flush()
    return history


def list_status_history(
    db: Session,
    asset_id: UUID,
    *,
    category: StatusCategory | None = None,
) -> list[InventoryAssetStatusHistory]:
    from sqlalchemy import select

    query = select(InventoryAssetStatusHistory).where(
        InventoryAssetStatusHistory.inventory_asset_id == asset_id
    )
    if category is not None:
        query = query.where(InventoryAssetStatusHistory.status_category == category)
    query = query.order_by(InventoryAssetStatusHistory.effective_at.desc())
    return list(db.scalars(query).all())
