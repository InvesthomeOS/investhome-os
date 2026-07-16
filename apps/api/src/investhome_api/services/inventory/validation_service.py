"""Centralized conditional validation for inventory assets."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from investhome_api.models.inventory import (
    Building,
    Floor,
    InventoryAsset,
    InventoryAssetType,
    UsageType,
)


class InventoryValidationError(ValueError):
    """Validation failure with i18n error key."""

    def __init__(self, error_key: str, *, detail: str | None = None) -> None:
        self.error_key = error_key
        super().__init__(detail or error_key)


BUILDING_FLOOR_REQUIRED_TYPES = frozenset(
    {
        InventoryAssetType.RESIDENTIAL_UNIT,
        InventoryAssetType.OFFICE_UNIT,
    }
)

BUILDING_REQUIRED_TYPES = frozenset(
    {
        InventoryAssetType.COMMERCIAL_UNIT,
        InventoryAssetType.RETAIL_UNIT,
    }
)

OPTIONAL_STRUCTURE_TYPES = frozenset(
    {
        InventoryAssetType.PARKING_SPACE,
        InventoryAssetType.STORAGE_UNIT,
    }
)

NO_STRUCTURE_TYPES = frozenset({InventoryAssetType.LAND_PARCEL})


def validate_building_floor_assignment(
    *,
    asset_type: InventoryAssetType,
    usage_type: UsageType | None,
    building_id: UUID | None,
    floor_id: UUID | None,
) -> None:
    """Validate building/floor requirements based on asset type and usage."""
    if asset_type in NO_STRUCTURE_TYPES:
        if building_id is not None or floor_id is not None:
            raise InventoryValidationError("inventory.errors.land_parcel_no_structure")
        return

    if asset_type in BUILDING_FLOOR_REQUIRED_TYPES or (
        usage_type in {UsageType.RESIDENTIAL, UsageType.OFFICE}
        and asset_type not in OPTIONAL_STRUCTURE_TYPES
    ):
        if building_id is None:
            raise InventoryValidationError("inventory.errors.building_required")
        if floor_id is None:
            raise InventoryValidationError("inventory.errors.floor_required")
        return

    if asset_type in BUILDING_REQUIRED_TYPES or usage_type in {UsageType.RETAIL, UsageType.COMMERCIAL}:
        if building_id is None:
            raise InventoryValidationError("inventory.errors.building_required")
        return

    if usage_type == UsageType.RESIDENTIAL and asset_type == InventoryAssetType.RESIDENTIAL_UNIT:
        if building_id is None:
            raise InventoryValidationError("inventory.errors.building_required")
        if floor_id is None:
            raise InventoryValidationError("inventory.errors.floor_required")


def validate_structure_references(
    db: Session,
    *,
    project_id: UUID,
    building_id: UUID | None,
    floor_id: UUID | None,
) -> None:
    """Ensure building/floor exist, belong to project, and are not archived."""
    if building_id is not None:
        building = db.get(Building, building_id)
        if building is None or building.archived_at is not None:
            raise InventoryValidationError("inventory.errors.building_not_found")
        if building.project_id != project_id:
            raise InventoryValidationError("inventory.errors.building_project_mismatch")

    if floor_id is not None:
        floor = db.get(Floor, floor_id)
        if floor is None or floor.archived_at is not None:
            raise InventoryValidationError("inventory.errors.floor_not_found")
        building = db.get(Building, floor.building_id)
        if building is None or building.project_id != project_id:
            raise InventoryValidationError("inventory.errors.floor_project_mismatch")
        if building_id is not None and floor.building_id != building_id:
            raise InventoryValidationError("inventory.errors.floor_building_mismatch")


def validate_asset_create(
    db: Session,
    *,
    project_id: UUID,
    asset_type: InventoryAssetType,
    usage_type: UsageType,
    building_id: UUID | None,
    floor_id: UUID | None,
) -> None:
    validate_building_floor_assignment(
        asset_type=asset_type,
        usage_type=usage_type,
        building_id=building_id,
        floor_id=floor_id,
    )
    validate_structure_references(
        db,
        project_id=project_id,
        building_id=building_id,
        floor_id=floor_id,
    )


def validate_asset_update(
    db: Session,
    asset: InventoryAsset,
    *,
    building_id: UUID | None,
    floor_id: UUID | None,
    asset_type: InventoryAssetType | None = None,
    usage_type: UsageType | None = None,
) -> None:
    effective_type = asset_type or asset.asset_type
    effective_usage = usage_type or asset.usage_type
    effective_building = building_id if building_id is not None else asset.building_id
    effective_floor = floor_id if floor_id is not None else asset.floor_id

    validate_building_floor_assignment(
        asset_type=effective_type,
        usage_type=effective_usage,
        building_id=effective_building,
        floor_id=effective_floor,
    )
    validate_structure_references(
        db,
        project_id=asset.project_id,
        building_id=effective_building,
        floor_id=effective_floor,
    )
