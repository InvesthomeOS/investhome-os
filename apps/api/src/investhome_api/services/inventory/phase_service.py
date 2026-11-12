"""One phase API for Project → optional Phase → Unit.

Phases are project master data. Other modules store the phase id, not a second name.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.inventory import InventoryAsset, ProjectPhase
from investhome_api.models.project import Project


class PhaseError(Exception):
    def __init__(self, key: str) -> None:
        super().__init__(key)
        self.key = key


def _clean_name(name: str) -> str:
    return " ".join(name.split())


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _require_project(db: Session, project_id: UUID) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise PhaseError("inventory.errors.project_not_found")
    return project


def list_phases(db: Session, project_id: UUID, *, include_inactive: bool = False) -> list[dict]:
    _require_project(db, project_id)
    query = select(ProjectPhase).where(ProjectPhase.project_id == project_id)
    if not include_inactive:
        query = query.where(ProjectPhase.active.is_(True))
    phases = list(db.scalars(query.order_by(ProjectPhase.display_order.asc(), ProjectPhase.name.asc())).all())
    counts: dict[UUID, int] = {}
    if phases:
        rows = db.execute(
            select(InventoryAsset.phase_id, func.count())
            .where(
                InventoryAsset.phase_id.in_([phase.id for phase in phases]),
                InventoryAsset.archived_at.is_(None),
            )
            .group_by(InventoryAsset.phase_id)
        ).all()
        counts = {phase_id: int(total) for phase_id, total in rows if phase_id is not None}
    return [
        {
            "id": phase.id,
            "project_id": phase.project_id,
            "name": phase.name,
            "display_order": phase.display_order,
            "active": phase.active,
            "address_line": phase.address_line,
            "city": phase.city,
            "region": phase.region,
            "postal_code": phase.postal_code,
            "unit_count": counts.get(phase.id, 0),
        }
        for phase in phases
    ]


def create_phase(
    db: Session,
    project_id: UUID,
    *,
    name: str,
    display_order: int,
    active: bool,
    address_line: str | None = None,
    city: str | None = None,
    region: str | None = None,
    postal_code: str | None = None,
) -> ProjectPhase:
    _require_project(db, project_id)
    cleaned = _clean_name(name)
    if not cleaned:
        raise PhaseError("inventory.errors.phase_name_required")
    existing = db.scalar(
        select(ProjectPhase.id).where(ProjectPhase.project_id == project_id, ProjectPhase.name == cleaned)
    )
    if existing is not None:
        raise PhaseError("inventory.errors.phase_duplicate")
    phase = ProjectPhase(
        project_id=project_id,
        name=cleaned,
        display_order=display_order,
        active=active,
        address_line=_clean_optional(address_line),
        city=_clean_optional(city),
        region=_clean_optional(region),
        postal_code=_clean_optional(postal_code),
    )
    db.add(phase)
    db.flush()
    return phase


def update_phase(
    db: Session,
    project_id: UUID,
    phase_id: UUID,
    *,
    name: str | None = None,
    display_order: int | None = None,
    active: bool | None = None,
    address_line: str | None = None,
    city: str | None = None,
    region: str | None = None,
    postal_code: str | None = None,
) -> ProjectPhase:
    _require_project(db, project_id)
    phase = db.get(ProjectPhase, phase_id)
    if phase is None or phase.project_id != project_id:
        raise PhaseError("inventory.errors.phase_not_found")
    if name is not None:
        cleaned = _clean_name(name)
        if not cleaned:
            raise PhaseError("inventory.errors.phase_name_required")
        duplicate = db.scalar(
            select(ProjectPhase.id).where(
                ProjectPhase.project_id == project_id,
                ProjectPhase.name == cleaned,
                ProjectPhase.id != phase.id,
            )
        )
        if duplicate is not None:
            raise PhaseError("inventory.errors.phase_duplicate")
        phase.name = cleaned
    if display_order is not None:
        phase.display_order = display_order
    if active is not None:
        phase.active = active
    if address_line is not None:
        phase.address_line = _clean_optional(address_line)
    if city is not None:
        phase.city = _clean_optional(city)
    if region is not None:
        phase.region = _clean_optional(region)
    if postal_code is not None:
        phase.postal_code = _clean_optional(postal_code)
    db.flush()
    return phase


def reorder_phases(db: Session, project_id: UUID, ordered_ids: list[UUID]) -> list[dict]:
    _require_project(db, project_id)
    phases = {
        phase.id: phase
        for phase in db.scalars(select(ProjectPhase).where(ProjectPhase.project_id == project_id)).all()
    }
    seen: set[UUID] = set()
    for index, phase_id in enumerate(ordered_ids):
        phase = phases.get(phase_id)
        if phase is None:
            raise PhaseError("inventory.errors.phase_not_found")
        if phase_id in seen:
            raise PhaseError("inventory.errors.phase_not_found")
        seen.add(phase_id)
        phase.display_order = index
    db.flush()
    return list_phases(db, project_id, include_inactive=True)


def assign_interest(
    db: Session,
    *,
    project_id: UUID | None,
    phase_id: UUID | None,
    inventory_asset_id: UUID | None,
) -> tuple[UUID | None, UUID | None, UUID | None, str | None]:
    """Validate a project / phase / unit triple. Raises PhaseError for unknown or mismatched ids."""
    if project_id is None and (phase_id is not None or inventory_asset_id is not None):
        raise PhaseError("inventory.errors.project_not_found")
    project_name = None
    if project_id is not None:
        project = db.get(Project, project_id)
        if project is None:
            raise PhaseError("inventory.errors.project_not_found")
        project_name = project.project_name
    if phase_id is not None:
        phase = db.get(ProjectPhase, phase_id)
        if phase is None:
            raise PhaseError("inventory.errors.phase_not_found")
        if project_id is None or phase.project_id != project_id:
            raise PhaseError("inventory.errors.phase_project_mismatch")
    if inventory_asset_id is not None:
        asset = db.get(InventoryAsset, inventory_asset_id)
        if asset is None:
            raise PhaseError("crm.agreements.errors.unit_not_found")
        if project_id is None or asset.project_id != project_id:
            raise PhaseError("crm.agreements.errors.unit_project_mismatch")
        if phase_id is not None and asset.phase_id != phase_id:
            raise PhaseError("crm.agreements.errors.unit_phase_mismatch")
        if phase_id is None and asset.phase_id is not None:
            phase_id = asset.phase_id
    return project_id, phase_id, inventory_asset_id, project_name
