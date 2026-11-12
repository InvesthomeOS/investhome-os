"""Link an agreement to a unit without folding the phase into the unit identifier."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.inventory import InventoryAsset, ProjectPhase


def clean_unit_identifier(value: str | None) -> str | None:
    text = " ".join(str(value or "").split())
    return text or None


def resolve_agreement_unit(
    db: Session,
    *,
    project_id: UUID | None,
    unit_number: str | None,
    phase_id: UUID | None = None,
    inventory_asset_id: UUID | None = None,
) -> tuple[str | None, UUID | None, UUID | None]:
    """Return (unit identifier, phase id, asset id).

    The identifier is always the business unit string, never a phase label.
    """
    identifier = clean_unit_identifier(unit_number)
    if phase_id is not None:
        phase = db.get(ProjectPhase, phase_id)
        if phase is None:
            raise ValueError("inventory.errors.phase_not_found")
        if project_id is not None and phase.project_id != project_id:
            raise ValueError("inventory.errors.phase_project_mismatch")
    if inventory_asset_id is not None:
        asset = db.get(InventoryAsset, inventory_asset_id)
        if asset is None:
            raise ValueError("crm.agreements.errors.unit_not_found")
        if project_id is not None and asset.project_id != project_id:
            raise ValueError("crm.agreements.errors.unit_project_mismatch")
        if phase_id is not None and asset.phase_id != phase_id:
            raise ValueError("crm.agreements.errors.unit_phase_mismatch")
        return asset.display_id, asset.phase_id, asset.id
    if identifier and project_id is not None:
        rows = list(
            db.scalars(
                select(InventoryAsset).where(
                    InventoryAsset.project_id == project_id,
                    func.lower(InventoryAsset.display_id) == identifier.casefold(),
                )
            ).all()
        )
        project_has_phases = (
            db.scalar(
                select(ProjectPhase.id)
                .where(ProjectPhase.project_id == project_id, ProjectPhase.active.is_(True))
                .limit(1)
            )
            is not None
        )
        if phase_id is not None:
            matched = [row for row in rows if row.phase_id == phase_id]
            if len(matched) > 1:
                raise ValueError("inventory.errors.display_id_duplicate")
            if len(matched) == 1:
                asset = matched[0]
                return asset.display_id, asset.phase_id, asset.id
            if rows:
                raise ValueError("crm.agreements.errors.unit_phase_mismatch")
            return identifier, phase_id, None
        if len(rows) > 1 or (project_has_phases and any(row.phase_id is not None for row in rows)):
            raise ValueError("crm.agreements.errors.phase_required")
        if len(rows) == 1:
            asset = rows[0]
            return asset.display_id, asset.phase_id, asset.id
    return identifier, phase_id, None


def assert_unit_open_for_sale(
    db: Session,
    asset_id: UUID | None,
    *,
    ignore_agreement_id: UUID | None = None,
) -> None:
    """Reject a second active sale and mark a free unit under contract."""
    if asset_id is None:
        return
    from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementStatus
    from investhome_api.models.inventory import InventorySalesStatus
    from investhome_api.services.crm.unit_change import (
        is_historical_unit_change,
        is_relationship_detached,
    )

    holders = list(
        db.scalars(
            select(CrmAgreement).where(
                CrmAgreement.inventory_asset_id == asset_id,
                CrmAgreement.status != CrmAgreementStatus.CANCELLED,
            )
        ).all()
    )
    for row in holders:
        if ignore_agreement_id is not None and row.id == ignore_agreement_id:
            continue
        if is_historical_unit_change(row) or is_relationship_detached(row):
            continue
        raise ValueError("crm.agreements.errors.unit_already_committed")
    asset = db.get(InventoryAsset, asset_id)
    if asset is not None and asset.sales_status == InventorySalesStatus.AVAILABLE_FOR_SALE:
        asset.sales_status = InventorySalesStatus.UNDER_CONTRACT
