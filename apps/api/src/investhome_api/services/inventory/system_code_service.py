"""Centralized system code generation for inventory assets."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.inventory import Building, Floor, InventoryAsset
from investhome_api.models.project import Project


def _project_abbreviation(project_code: str) -> str:
    """Derive a short uppercase prefix from project code, e.g. PRJ-TEMP-001 -> TEM."""
    parts = [part for part in re.split(r"[-_\s]+", project_code.upper()) if part]
    if len(parts) >= 2:
        return parts[1][:3]
    if parts:
        return parts[0][:3]
    return "PRJ"


def _normalize_segment(value: str | None, *, fallback: str = "00") -> str:
    if not value:
        return fallback
    cleaned = re.sub(r"[^A-Z0-9]", "", value.upper())
    return cleaned or fallback


def build_system_code(
    *,
    project_code: str,
    building_code: str | None,
    floor_level_code: str | None,
    display_id: str,
) -> str:
    """Build uppercase system code: {PROJECT}-{BUILDING}-{FLOOR}-{DISPLAY_ID}."""
    segments = [
        _project_abbreviation(project_code),
        _normalize_segment(building_code, fallback="NA"),
        _normalize_segment(floor_level_code, fallback="00"),
        _normalize_segment(display_id, fallback="000"),
    ]
    return "-".join(segments)


def generate_system_code(
    db: Session,
    *,
    project_id,
    building_id,
    floor_id,
    display_id: str,
) -> str:
    """Generate a globally unique system code for a new inventory asset."""
    project = db.get(Project, project_id)
    if project is None:
        msg = "inventory.errors.project_not_found"
        raise ValueError(msg)

    building_code: str | None = None
    floor_level_code: str | None = None

    if building_id is not None:
        building = db.get(Building, building_id)
        if building is not None:
            building_code = building.code

    if floor_id is not None:
        floor = db.get(Floor, floor_id)
        if floor is not None:
            floor_level_code = floor.level_code or str(floor.floor_number)

    base_code = build_system_code(
        project_code=project.project_code,
        building_code=building_code,
        floor_level_code=floor_level_code,
        display_id=display_id,
    )

    candidate = base_code
    suffix = 1
    while db.scalar(select(InventoryAsset.id).where(InventoryAsset.system_code == candidate).limit(1)):
        candidate = f"{base_code}-{suffix}"
        suffix += 1

    return candidate
