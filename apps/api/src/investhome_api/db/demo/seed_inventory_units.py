"""Idempotent inventory units — ensure ≥30 assets across demo projects."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.db.session import SessionLocal
from investhome_api.models.inventory import (
    AvailabilityStatus,
    Building,
    BuildingType,
    ConstructionStatus,
    Floor,
    InventoryAsset,
    InventoryAssetType,
    InventorySalesStatus,
    StructureStatus,
    UsageType,
)
from investhome_api.models.project import Project
from investhome_api.services.inventory.system_code_service import generate_system_code

# (project_code, building_code, building_name, floors, unit_specs)
# unit_specs: list of (display_id, floor_number|None, bedrooms, baths, sqft, subtype)
PROJECT_UNIT_PLANS: list[tuple[str, str, str, list[int], list[tuple]]] = [
    (
        "PRJ-TEMP-001",
        "A",
        "Temple Tower A",
        [3, 4, 5, 12],
        [
            ("301", 3, "2", "2", "980", "2br_corner"),
            ("302", 3, "1", "1", "720", "1br"),
            ("303", 3, "2", "2", "910", "2br"),
            ("401", 4, "2", "2", "990", "2br"),
            ("402", 4, "1", "1", "680", "1br"),
            ("403", 4, "3", "2", "1200", "3br"),
            ("501", 5, "2", "2", "1000", "2br"),
            ("502", 5, "2", "2.5", "1100", "2br_den"),
            ("12A", 12, "3", "2.5", "1450", "3br_penthouse"),
            ("12B", 12, "2", "2", "1180", "2br_ph"),
        ],
    ),
    (
        "PRJ-UNIL-002",
        "M",
        "UniLoft Main",
        [2, 3, 4],
        [
            ("2A", 2, "1", "1", "680", "loft_studio"),
            ("2B", 2, "1", "1", "720", "loft_studio"),
            ("2C", 2, "2", "1", "880", "loft_1br"),
            ("3A", 3, "1", "1", "700", "loft_studio"),
            ("3B", 3, "2", "2", "950", "loft_2br"),
            ("4A", 4, "2", "2", "1020", "loft_2br"),
            ("4B", 4, "1", "1", "740", "loft_studio"),
        ],
    ),
    (
        "PRJ-309H-003",
        "H",
        "309 H Building",
        [1, 2],
        [
            ("101", 1, "1", "1", "620", "1br"),
            ("102", 1, "2", "1", "820", "2br"),
            ("201", 2, "2", "2", "900", "2br"),
            ("202", 2, "1", "1", "640", "1br"),
        ],
    ),
    (
        "PRJ-1812H-005",
        "T",
        "1812 Townhomes",
        [1],
        [
            ("TH-1", 1, "3", "2.5", "1800", "townhome"),
            ("TH-2", 1, "3", "2.5", "1850", "townhome"),
            ("TH-3", 1, "4", "3", "2100", "townhome"),
        ],
    ),
    (
        "PRJ-NOMA-006",
        "N",
        "NoMa Tower",
        [5, 6],
        [
            ("501", 5, "1", "1", "650", "1br"),
            ("502", 5, "2", "2", "920", "2br"),
            ("601", 6, "2", "2", "980", "2br"),
            ("602", 6, "3", "2", "1250", "3br"),
        ],
    ),
    (
        "PRJ-1627-011",
        "S",
        "1627 Sixteenth",
        [2, 3],
        [
            ("201", 2, "1", "1", "700", "1br"),
            ("202", 2, "2", "2", "950", "2br"),
            ("301", 3, "2", "2", "1000", "2br"),
        ],
    ),
]


def _get_or_create_building(
    session: Session, project_id, code: str, name: str, floors: int
) -> Building:
    existing = session.scalar(
        select(Building).where(Building.project_id == project_id, Building.code == code)
    )
    if existing is not None:
        if not existing.is_demo:
            existing.is_demo = True
        return existing
    building = Building(
        project_id=project_id,
        name=name,
        code=code,
        building_type=BuildingType.APARTMENT,
        total_floors=floors,
        status=StructureStatus.ACTIVE,
        description=f"Demo building {name}",
        is_demo=True,
    )
    session.add(building)
    session.flush()
    return building


def _get_or_create_floor(session: Session, building_id, floor_number: int) -> Floor:
    existing = session.scalar(
        select(Floor).where(Floor.building_id == building_id, Floor.floor_number == floor_number)
    )
    if existing is not None:
        if not existing.is_demo:
            existing.is_demo = True
        return existing
    floor = Floor(
        building_id=building_id,
        floor_number=floor_number,
        display_name=f"Level {floor_number}",
        level_code=f"{floor_number:02d}",
        sort_order=floor_number,
        status=StructureStatus.ACTIVE,
        is_demo=True,
    )
    session.add(floor)
    session.flush()
    return floor


def seed_inventory_units(session: Session | None = None) -> dict[str, int]:
    """Ensure ≥30 inventory assets across projects. Idempotent by project+display_id."""
    own_session = session is None
    session = session or SessionLocal()
    inserted = {"buildings": 0, "floors": 0, "assets": 0}
    try:
        projects = {
            p.project_code: p
            for p in session.scalars(select(Project).where(Project.is_demo.is_(True))).all()
        }
        # Also include any project matching our codes even if not flagged yet
        for code, *_rest in PROJECT_UNIT_PLANS:
            if code not in projects:
                proj = session.scalar(select(Project).where(Project.project_code == code))
                if proj is not None:
                    projects[code] = proj

        for project_code, b_code, b_name, floor_nums, units in PROJECT_UNIT_PLANS:
            project = projects.get(project_code)
            if project is None:
                continue

            before_b = session.scalar(
                select(Building.id).where(
                    Building.project_id == project.id, Building.code == b_code
                )
            )
            building = _get_or_create_building(
                session, project.id, b_code, b_name, max(floor_nums) if floor_nums else 1
            )
            if before_b is None:
                inserted["buildings"] += 1

            floor_map: dict[int, Floor] = {}
            for fn in floor_nums:
                before_f = session.scalar(
                    select(Floor.id).where(
                        Floor.building_id == building.id, Floor.floor_number == fn
                    )
                )
                floor_map[fn] = _get_or_create_floor(session, building.id, fn)
                if before_f is None:
                    inserted["floors"] += 1

            for display_id, floor_num, beds, baths, sqft, subtype in units:
                existing = session.scalar(
                    select(InventoryAsset).where(
                        InventoryAsset.project_id == project.id,
                        InventoryAsset.display_id == display_id,
                    )
                )
                if existing is not None:
                    if not existing.is_demo:
                        existing.is_demo = True
                    continue

                floor = floor_map.get(floor_num)
                system_code = generate_system_code(
                    session,
                    project_id=project.id,
                    building_id=building.id,
                    floor_id=floor.id if floor else None,
                    display_id=display_id,
                )
                session.add(
                    InventoryAsset(
                        project_id=project.id,
                        building_id=building.id,
                        floor_id=floor.id if floor else None,
                        display_id=display_id,
                        system_code=system_code,
                        asset_type=InventoryAssetType.RESIDENTIAL_UNIT,
                        usage_type=UsageType.RESIDENTIAL,
                        unit_subtype=subtype,
                        bedrooms=Decimal(beds),
                        bathrooms=Decimal(baths),
                        interior_area_sqft=Decimal(sqft),
                        availability_status=AvailabilityStatus.AVAILABLE,
                        sales_status=InventorySalesStatus.AVAILABLE_FOR_SALE,
                        construction_status=ConstructionStatus.READY,
                        list_price=Decimal(sqft) * Decimal("650"),
                        is_demo=True,
                    )
                )
                inserted["assets"] += 1

        if own_session:
            session.commit()
        else:
            session.flush()
        return inserted
    finally:
        if own_session:
            session.close()
