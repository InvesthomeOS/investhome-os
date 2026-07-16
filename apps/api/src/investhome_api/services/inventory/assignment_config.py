"""Assignment workflow configuration."""

from investhome_api.models.inventory import AssignmentType, InventoryAssetType

SELF_APPROVE_PERMISSION = "self_approve_assignment"


def assignment_type_for_child(asset_type: InventoryAssetType) -> AssignmentType:
    if asset_type == InventoryAssetType.PARKING_SPACE:
        return AssignmentType.PARKING_FOR
    if asset_type == InventoryAssetType.STORAGE_UNIT:
        return AssignmentType.STORAGE_FOR
    msg = f"Unsupported child asset type: {asset_type}"
    raise ValueError(msg)
