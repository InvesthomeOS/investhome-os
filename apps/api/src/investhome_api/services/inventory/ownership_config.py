"""Ownership workflow configuration."""

from investhome_api.models.inventory import OwnershipType, TransferType

# Legal-owner changes require supporting document unless this is disabled.
REQUIRE_DOCUMENT_FOR_LEGAL_CHANGES = True

# Allow self-approval when actor has this permission.
SELF_APPROVE_PERMISSION = "self_approve_ownership_change"

LEGAL_CHANGE_TRANSFER_TYPES = frozenset(
    {
        TransferType.INITIAL_OWNERSHIP,
        TransferType.FULL_TRANSFER,
        TransferType.PARTIAL_TRANSFER,
        TransferType.PERCENTAGE_CHANGE,
        TransferType.OWNER_ADDITION,
        TransferType.OWNER_REMOVAL,
        TransferType.OWNERSHIP_TYPE_CHANGE,
        TransferType.CORRECTION,
    }
)


def transfer_affects_legal(transfer_type: TransferType) -> bool:
    return transfer_type in LEGAL_CHANGE_TRANSFER_TYPES


def is_legal_ownership_type(ownership_type: OwnershipType) -> bool:
    from investhome_api.models.inventory import LEGAL_OWNERSHIP_TYPES

    return ownership_type in LEGAL_OWNERSHIP_TYPES
