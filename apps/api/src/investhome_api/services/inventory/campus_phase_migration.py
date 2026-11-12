"""Turn the real 3220 project into The Campus without moving unit UUIDs.

The demo project PRJ-CAMP-004 is never loaded for update. Phase names are the
short labels the project filter already renders. Street addresses go in the
0096 phase address columns. The command does not commit; the caller commits
or rolls the whole transaction back.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from investhome_api.models.inventory import (
    Building,
    BuildingType,
    Floor,
    InventoryAsset,
    InventoryAssetPrice,
    ProjectPhase,
    StructureStatus,
)
from investhome_api.models.project import Project

CAMPUS_PROJECT_ID = UUID("d08ffa5a-bb69-4eaf-976c-b8ceae218e41")
CAMPUS_PROJECT_CODE = "3220-16TH-NW"
CAMPUS_PROJECT_NAME = "The Campus"
DEMO_CAMPUS_CODE = "PRJ-CAMP-004"
PHASE_1_NAME = "3220"
PHASE_1_ADDRESS = "3220 16th St NW"
PHASE_2_NAME = "3224"
PHASE_2_ADDRESS = "3224 16th St NW"
BUILDING_CODE = "3220"
PHASE_2_BUILDING_CODE = "3224"
PHASE_2_BUILDING_NAME = "3224 16th St NW"
EXPECTED_UNITS = 43

_SCHEMA = (
    ("0096", "project_phases", ("address_line", "city", "region", "postal_code")),
    ("0096", "project_budget_versions", ("phase_id",)),
    ("0096", "funding_commitments", ("phase_id",)),
    ("0097", "finance_transactions", ("agreement_id",)),
    (
        "0097",
        "crm_agreement_participants",
        ("commission_rate", "commission_amount", "commission_paid", "commission_condition"),
    ),
)

_DEMO_FIELDS = (
    "id",
    "project_code",
    "project_name",
    "address",
    "city",
    "state",
    "postal_code",
    "latitude",
    "longitude",
    "is_demo",
    "uses_phases",
    "total_units",
    "total_development_cost",
    "projected_revenue",
    "archived_at",
)

_PROJECT_LOCKED_FIELDS = (
    "address",
    "address_line2",
    "city",
    "state",
    "postal_code",
    "country",
    "latitude",
    "longitude",
)


class CampusMigrationBlocked(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class CampusMigrationReport:
    project_id: UUID
    project_code: str
    project_name: str
    uses_phases: bool
    total_units: int
    phase_1_id: UUID
    phase_2_id: UUID
    building_3220_id: UUID
    building_3224_id: UUID
    unit_ids: tuple[UUID, ...]
    units_on_phase_1: int
    units_on_phase_2: int
    phases_created: int
    buildings_created: int
    units_linked: int


def revision_gaps(present: dict[str, set[str]]) -> list[str]:
    gaps: list[str] = []
    for revision, table, columns in _SCHEMA:
        found = present.get(table)
        if found is None:
            gaps.append(f"{revision}:{table}")
            continue
        gaps.extend(f"{revision}:{table}.{column}" for column in columns if column not in found)
    return gaps


def schema_gaps(bind) -> list[str]:
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    present = {
        table: {column["name"] for column in inspector.get_columns(table)}
        for table in tables
    }
    return revision_gaps(present)


def _snapshot(row: Project, fields: tuple[str, ...]) -> tuple:
    return tuple(getattr(row, field) for field in fields)


def _phase(
    db: Session,
    project_id: UUID,
    *,
    name: str,
    display_order: int,
    address_line: str,
    city: str | None,
    region: str | None,
    postal_code: str | None,
) -> tuple[ProjectPhase, bool]:
    row = db.scalar(
        select(ProjectPhase).where(ProjectPhase.project_id == project_id, ProjectPhase.name == name)
    )
    created = row is None
    if row is None:
        row = ProjectPhase(
            project_id=project_id,
            name=name,
            display_order=display_order,
            active=True,
            address_line=address_line,
            city=city,
            region=region,
            postal_code=postal_code,
        )
        db.add(row)
        db.flush()
        return row, created
    if row.address_line not in (None, address_line):
        raise CampusMigrationBlocked("phase_address_conflict")
    if row.city not in (None, city):
        raise CampusMigrationBlocked("phase_address_conflict")
    if row.region not in (None, region):
        raise CampusMigrationBlocked("phase_address_conflict")
    if postal_code is not None and row.postal_code not in (None, postal_code):
        raise CampusMigrationBlocked("phase_address_conflict")
    row.address_line = address_line
    row.city = city
    row.region = region
    if postal_code is not None:
        row.postal_code = postal_code
    row.display_order = display_order
    row.active = True
    return row, created


def _phase_two_building(db: Session, project_id: UUID) -> tuple[Building, bool]:
    row = db.scalar(
        select(Building).where(
            Building.project_id == project_id,
            Building.code == PHASE_2_BUILDING_CODE,
        )
    )
    created = row is None
    if row is None:
        row = Building(
            project_id=project_id,
            name=PHASE_2_BUILDING_NAME,
            code=PHASE_2_BUILDING_CODE,
            building_type=BuildingType.CONDOMINIUM,
            address=PHASE_2_ADDRESS,
            status=StructureStatus.PLANNED,
            is_demo=False,
        )
        db.add(row)
        db.flush()
        return row, created
    if row.name not in (PHASE_2_BUILDING_CODE, PHASE_2_BUILDING_NAME):
        raise CampusMigrationBlocked("building_identity_conflict")
    if row.address not in (None, PHASE_2_ADDRESS):
        raise CampusMigrationBlocked("building_identity_conflict")
    if row.is_demo:
        raise CampusMigrationBlocked("building_identity_conflict")
    row.name = PHASE_2_BUILDING_NAME
    row.address = PHASE_2_ADDRESS
    return row, created


def migrate_campus_phases(db: Session) -> CampusMigrationReport:
    gaps = schema_gaps(db.connection())
    if gaps:
        raise CampusMigrationBlocked("schema_not_ready:" + ",".join(gaps))

    project = db.get(Project, CAMPUS_PROJECT_ID)
    if project is None:
        raise CampusMigrationBlocked("project_not_found")
    if project.project_code != CAMPUS_PROJECT_CODE:
        raise CampusMigrationBlocked("project_code_mismatch")
    if project.is_demo:
        raise CampusMigrationBlocked("project_is_demo")
    if project.archived_at is not None:
        raise CampusMigrationBlocked("project_archived")
    if project.total_units != EXPECTED_UNITS:
        raise CampusMigrationBlocked("unit_count")

    demo = db.scalar(select(Project).where(Project.project_code == DEMO_CAMPUS_CODE))
    if demo is None:
        raise CampusMigrationBlocked("demo_campus_missing")
    if demo.id == project.id or not demo.is_demo:
        raise CampusMigrationBlocked("demo_campus_not_isolated")
    demo_before = _snapshot(demo, _DEMO_FIELDS)
    location_before = _snapshot(project, _PROJECT_LOCKED_FIELDS)

    assets = list(
        db.scalars(
            select(InventoryAsset)
            .where(InventoryAsset.project_id == project.id)
            .order_by(InventoryAsset.display_id, InventoryAsset.id)
        ).all()
    )
    active = [asset for asset in assets if asset.archived_at is None]
    if len(assets) != EXPECTED_UNITS or len(active) != EXPECTED_UNITS:
        raise CampusMigrationBlocked("unit_count")
    if len({asset.display_id for asset in active}) != EXPECTED_UNITS:
        raise CampusMigrationBlocked("duplicate_display_id")

    building = db.scalar(
        select(Building).where(Building.project_id == project.id, Building.code == BUILDING_CODE)
    )
    if building is None or building.archived_at is not None:
        raise CampusMigrationBlocked("building_link")
    extra_codes = {
        row.code
        for row in db.scalars(select(Building).where(Building.project_id == project.id)).all()
        if row.code not in {BUILDING_CODE, PHASE_2_BUILDING_CODE}
    }
    if extra_codes:
        raise CampusMigrationBlocked("unexpected_building")

    floors = {
        floor.id: floor
        for floor in db.scalars(select(Floor).where(Floor.building_id == building.id)).all()
    }
    if not floors:
        raise CampusMigrationBlocked("floor_link")
    for asset in active:
        floor = floors.get(asset.floor_id)
        if asset.building_id != building.id or floor is None or floor.building_id != building.id:
            raise CampusMigrationBlocked("floor_link")

    phases_created = 0
    phase_1, created = _phase(
        db,
        project.id,
        name=PHASE_1_NAME,
        display_order=1,
        address_line=PHASE_1_ADDRESS,
        city=project.city,
        region=project.state,
        postal_code=project.postal_code,
    )
    phases_created += int(created)
    phase_2, created = _phase(
        db,
        project.id,
        name=PHASE_2_NAME,
        display_order=2,
        address_line=PHASE_2_ADDRESS,
        city=project.city,
        region=project.state,
        postal_code=None,
    )
    phases_created += int(created)
    phase_2_building, building_created = _phase_two_building(db, project.id)

    asset_before = [
        (asset.id, asset.project_id, asset.building_id, asset.floor_id, asset.display_id, asset.list_price)
        for asset in active
    ]
    price_before = list(
        db.scalars(
            select(InventoryAssetPrice.id)
            .join(InventoryAsset, InventoryAsset.id == InventoryAssetPrice.inventory_asset_id)
            .where(InventoryAsset.project_id == project.id)
            .order_by(InventoryAssetPrice.id)
        ).all()
    )
    linked = 0
    for asset in active:
        if asset.phase_id is None:
            asset.phase_id = phase_1.id
            linked += 1
        elif asset.phase_id != phase_1.id:
            raise CampusMigrationBlocked("phase_conflict")

    project.project_name = CAMPUS_PROJECT_NAME
    project.uses_phases = True
    db.flush()

    phase_1_units = [
        asset for asset in active if asset.phase_id == phase_1.id and asset.building_id == building.id
    ]
    phase_2_units = [asset for asset in active if asset.phase_id == phase_2.id]
    if len(phase_1_units) != EXPECTED_UNITS or phase_2_units:
        raise CampusMigrationBlocked("postcheck_failed")
    if _snapshot(project, _PROJECT_LOCKED_FIELDS) != location_before:
        raise CampusMigrationBlocked("postcheck_failed")
    if project.project_code != CAMPUS_PROJECT_CODE or project.total_units != EXPECTED_UNITS:
        raise CampusMigrationBlocked("postcheck_failed")
    if project.is_demo or project.id != CAMPUS_PROJECT_ID:
        raise CampusMigrationBlocked("postcheck_failed")
    asset_after = [
        (asset.id, asset.project_id, asset.building_id, asset.floor_id, asset.display_id, asset.list_price)
        for asset in active
    ]
    if asset_after != asset_before:
        raise CampusMigrationBlocked("postcheck_failed")
    price_after = list(
        db.scalars(
            select(InventoryAssetPrice.id)
            .join(InventoryAsset, InventoryAsset.id == InventoryAssetPrice.inventory_asset_id)
            .where(InventoryAsset.project_id == project.id)
            .order_by(InventoryAssetPrice.id)
        ).all()
    )
    if price_after != price_before:
        raise CampusMigrationBlocked("postcheck_failed")
    db.refresh(demo)
    if _snapshot(demo, _DEMO_FIELDS) != demo_before:
        raise CampusMigrationBlocked("postcheck_failed")
    phase_2_floors = db.scalars(select(Floor).where(Floor.building_id == phase_2_building.id)).all()
    if phase_2_floors:
        raise CampusMigrationBlocked("postcheck_failed")

    return CampusMigrationReport(
        project_id=project.id,
        project_code=project.project_code,
        project_name=project.project_name,
        uses_phases=project.uses_phases,
        total_units=project.total_units or 0,
        phase_1_id=phase_1.id,
        phase_2_id=phase_2.id,
        building_3220_id=building.id,
        building_3224_id=phase_2_building.id,
        unit_ids=tuple(asset.id for asset in active),
        units_on_phase_1=len(phase_1_units),
        units_on_phase_2=0,
        phases_created=phases_created,
        buildings_created=int(building_created),
        units_linked=linked,
    )
