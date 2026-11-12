"""Campus phase migration stays on the 3220 project and leaves the demo record alone."""

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.finance import FinanceTransaction
from investhome_api.models.inventory import (
    Building,
    BuildingType,
    Floor,
    InventoryAsset,
    InventoryAssetPrice,
    InventoryAssetType,
    InventorySalesStatus,
    PriceSource,
    PriceStatus,
    PriceType,
    ProjectPhase,
    StructureStatus,
    UsageType,
)
from investhome_api.models.project import DevelopmentType, Project, ProjectStatus, ProjectType
from investhome_api.services.inventory.campus_phase_migration import (
    BUILDING_CODE,
    CAMPUS_PROJECT_CODE,
    CAMPUS_PROJECT_ID,
    DEMO_CAMPUS_CODE,
    EXPECTED_UNITS,
    PHASE_1_ADDRESS,
    PHASE_1_NAME,
    PHASE_2_ADDRESS,
    PHASE_2_NAME,
    CampusMigrationBlocked,
    migrate_campus_phases,
    revision_gaps,
)
from investhome_api.services.project_dashboard_service import _inventory_counts

DEMO_CAMPUS_ID = UUID("2240179f-24dc-46d9-bf8c-654944a34bb2")


def _project(db: Session, **overrides) -> Project:
    values = {
        "id": CAMPUS_PROJECT_ID,
        "project_code": CAMPUS_PROJECT_CODE,
        "project_name": "3220 16th St NW",
        "address": "3220 16th St NW",
        "city": "Washington",
        "state": "DC",
        "postal_code": "20010",
        "latitude": Decimal("38.9317000"),
        "longitude": Decimal("-77.0365000"),
        "project_type": ProjectType.RESIDENTIAL,
        "development_type": DevelopmentType.GROUND_UP,
        "project_status": ProjectStatus.PIPELINE,
        "currency": "USD",
        "total_units": EXPECTED_UNITS,
        "uses_phases": False,
        "is_demo": False,
    }
    values.update(overrides)
    row = Project(**values)
    db.add(row)
    db.flush()
    return row


def _demo(db: Session) -> Project:
    row = Project(
        id=DEMO_CAMPUS_ID,
        project_code=DEMO_CAMPUS_CODE,
        project_name="The Campus",
        address="3220 & 3224 Minnesota Ave NE",
        city="Washington",
        state="DC",
        project_type=ProjectType.RESIDENTIAL,
        development_type=DevelopmentType.GROUND_UP,
        project_status=ProjectStatus.PERMITTING,
        currency="USD",
        total_units=156,
        total_development_cost=Decimal("72000000.00"),
        projected_revenue=Decimal("89000000.00"),
        uses_phases=False,
        is_demo=True,
    )
    db.add(row)
    db.flush()
    return row


def _seed(db: Session, *, units: int = EXPECTED_UNITS, duplicate: str | None = None, stray_building: bool = False):
    project = _project(db)
    demo = _demo(db)
    building = Building(
        project_id=project.id,
        name="3220 16th St NW",
        code=BUILDING_CODE,
        building_type=BuildingType.CONDOMINIUM,
        address="3220 16th St NW",
        status=StructureStatus.ACTIVE,
        is_demo=False,
    )
    db.add(building)
    db.flush()
    floors = []
    for number, label in ((1, "1st"), (2, "2nd")):
        floor = Floor(
            building_id=building.id,
            floor_number=number,
            display_name=label,
            level_code=str(number),
            sort_order=number,
            status=StructureStatus.ACTIVE,
            is_demo=False,
        )
        db.add(floor)
        floors.append(floor)
    db.flush()
    other = None
    if stray_building:
        other = Building(
            project_id=project.id,
            name="Other",
            code="OTHER",
            building_type=BuildingType.CONDOMINIUM,
            status=StructureStatus.ACTIVE,
            is_demo=False,
        )
        db.add(other)
        db.flush()
    created = []
    for index in range(units):
        display_id = duplicate if duplicate and index == units - 1 else f"{index + 1:03d}"
        target = other if stray_building and index == 0 else building
        floor = floors[index % len(floors)]
        asset = InventoryAsset(
            project_id=project.id,
            building_id=target.id,
            floor_id=None if target is other else floor.id,
            display_id=display_id,
            system_code=f"3220-{index + 1:03d}",
            asset_type=InventoryAssetType.RESIDENTIAL_UNIT,
            usage_type=UsageType.RESIDENTIAL,
            sales_status=InventorySalesStatus.AVAILABLE_FOR_SALE,
            list_price=Decimal("500000.00"),
            currency="USD",
            is_demo=False,
        )
        db.add(asset)
        created.append(asset)
    db.flush()
    price = InventoryAssetPrice(
        inventory_asset_id=created[0].id,
        price_type=PriceType.LIST,
        amount=Decimal("539900.00"),
        currency="USD",
        effective_from=date(2026, 1, 1),
        status=PriceStatus.ACTIVE,
        source=PriceSource.IMPORT,
    )
    db.add(price)
    db.flush()
    return project, demo, building, floors, created, price


def test_links_phase_one_and_keeps_identity(db: Session):
    project, demo, building, floors, assets, price = _seed(db)
    unit_ids = [asset.id for asset in assets]
    floor_ids = [floor.id for floor in floors]
    agreements = db.scalar(select(func.count()).select_from(CrmAgreement))
    finance = db.scalar(select(func.count()).select_from(FinanceTransaction))

    report = migrate_campus_phases(db)

    assert report.project_id == CAMPUS_PROJECT_ID
    assert report.project_code == CAMPUS_PROJECT_CODE
    assert report.project_name == "The Campus"
    assert report.uses_phases is True
    assert report.total_units == 43
    assert report.units_on_phase_1 == 43
    assert report.units_on_phase_2 == 0
    assert report.units_linked == 43
    assert list(report.unit_ids) == unit_ids
    assert project.address == "3220 16th St NW"
    assert project.latitude == Decimal("38.9317000")
    assert project.uses_phases is True
    phase_1 = db.get(ProjectPhase, report.phase_1_id)
    phase_2 = db.get(ProjectPhase, report.phase_2_id)
    assert phase_1.name == PHASE_1_NAME
    assert phase_1.address_line == PHASE_1_ADDRESS
    assert phase_1.city == "Washington"
    assert phase_1.region == "DC"
    assert phase_1.postal_code == "20010"
    assert phase_2.name == PHASE_2_NAME
    assert phase_2.address_line == PHASE_2_ADDRESS
    assert phase_2.postal_code is None
    assert all(asset.phase_id == phase_1.id for asset in assets)
    assert all(asset.project_id == project.id for asset in assets)
    assert all(asset.building_id == building.id for asset in assets)
    assert [asset.floor_id for asset in assets] == [floors[index % 2].id for index in range(43)]
    assert floor_ids == [floor.id for floor in floors]
    assert price.amount == Decimal("539900.00")
    assert price.inventory_asset_id == assets[0].id
    assert demo.project_code == DEMO_CAMPUS_CODE
    assert demo.is_demo is True
    assert demo.total_development_cost == Decimal("72000000.00")
    assert demo.projected_revenue == Decimal("89000000.00")
    assert demo.uses_phases is False
    assert db.scalar(select(func.count()).select_from(CrmAgreement)) == agreements
    assert db.scalar(select(func.count()).select_from(FinanceTransaction)) == finance


def test_rerun_creates_nothing_new(db: Session):
    _seed(db)
    first = migrate_campus_phases(db)
    second = migrate_campus_phases(db)

    assert second.phase_1_id == first.phase_1_id
    assert second.phase_2_id == first.phase_2_id
    assert second.building_3224_id == first.building_3224_id
    assert second.unit_ids == first.unit_ids
    assert second.phases_created == 0
    assert second.buildings_created == 0
    assert second.units_linked == 0
    assert second.units_on_phase_1 == 43
    assert db.scalar(select(func.count()).select_from(ProjectPhase)) == 2
    assert db.scalar(select(func.count()).select_from(Building)) == 2


def test_phase_filter_and_project_total(db: Session):
    project, demo, *_ = _seed(db)
    report = migrate_campus_phases(db)

    whole = _inventory_counts(db, [project.id])
    phase_1 = _inventory_counts(db, [project.id], report.phase_1_id)
    phase_2 = _inventory_counts(db, [project.id], report.phase_2_id)
    demo_units = _inventory_counts(db, [demo.id])

    assert whole["total_assets"] == 43
    assert phase_1["total_assets"] == 43
    assert phase_2["total_assets"] == 0
    assert phase_1["total_assets"] + phase_2["total_assets"] == project.total_units
    assert demo_units["total_assets"] == 0
    assert project.total_development_cost is None


def test_rejects_wrong_project_code(db: Session):
    _project(db, project_code="OTHER-CODE")
    _demo(db)
    with pytest.raises(CampusMigrationBlocked, match="project_code_mismatch"):
        migrate_campus_phases(db)


def test_rejects_missing_project(db: Session):
    with pytest.raises(CampusMigrationBlocked, match="project_not_found"):
        migrate_campus_phases(db)


def test_rejects_duplicate_unit_numbers(db: Session):
    _seed(db, duplicate="001")
    with pytest.raises(CampusMigrationBlocked, match="duplicate_display_id"):
        migrate_campus_phases(db)
    assert db.get(Project, CAMPUS_PROJECT_ID).project_name == "3220 16th St NW"
    assert db.get(Project, CAMPUS_PROJECT_ID).uses_phases is False


def test_rejects_unexpected_building_and_missing_floor(db: Session):
    _seed(db, stray_building=True)
    with pytest.raises(CampusMigrationBlocked, match="unexpected_building"):
        migrate_campus_phases(db)

    db.rollback()
    _, _, _, _, assets, _ = _seed(db)
    assets[0].floor_id = None
    db.flush()
    with pytest.raises(CampusMigrationBlocked, match="floor_link"):
        migrate_campus_phases(db)
    assert db.get(Project, CAMPUS_PROJECT_ID).uses_phases is False


def test_rollback_removes_phases_name_and_links(db: Session):
    project, _, _, _, assets, _ = _seed(db)
    original_ids = [asset.id for asset in assets]
    db.commit()
    try:
        try:
            migrate_campus_phases(db)
            raise RuntimeError("stop before commit")
        except RuntimeError:
            db.rollback()
        db.expire_all()
        restored = db.get(Project, CAMPUS_PROJECT_ID)
        assert restored.project_name == "3220 16th St NW"
        assert restored.project_code == CAMPUS_PROJECT_CODE
        assert restored.uses_phases is False
        assert restored.address == "3220 16th St NW"
        assert db.scalars(select(ProjectPhase).where(ProjectPhase.project_id == project.id)).all() == []
        restored_assets = db.scalars(
            select(InventoryAsset).where(InventoryAsset.project_id == project.id)
        ).all()
        assert sorted(asset.id for asset in restored_assets) == sorted(original_ids)
        assert all(asset.phase_id is None for asset in restored_assets)
        codes = db.scalars(select(Building.code).where(Building.project_id == project.id)).all()
        assert list(codes) == [BUILDING_CODE]
        demo = db.get(Project, DEMO_CAMPUS_ID)
        assert demo.project_name == "The Campus"
        assert demo.total_units == 156
    finally:
        _cleanup(db)


def _cleanup(db: Session):
    db.rollback()
    ids = [CAMPUS_PROJECT_ID, DEMO_CAMPUS_ID]
    asset_ids = list(
        db.scalars(select(InventoryAsset.id).where(InventoryAsset.project_id.in_(ids))).all()
    )
    if asset_ids:
        db.execute(delete(InventoryAssetPrice).where(InventoryAssetPrice.inventory_asset_id.in_(asset_ids)))
        db.execute(delete(InventoryAsset).where(InventoryAsset.id.in_(asset_ids)))
    building_ids = list(db.scalars(select(Building.id).where(Building.project_id.in_(ids))).all())
    if building_ids:
        db.execute(delete(Floor).where(Floor.building_id.in_(building_ids)))
        db.execute(delete(Building).where(Building.id.in_(building_ids)))
    db.execute(delete(ProjectPhase).where(ProjectPhase.project_id.in_(ids)))
    db.execute(delete(Project).where(Project.id.in_(ids)))
    db.commit()


def test_schema_gap_names_the_revision():
    gaps = revision_gaps({"project_phases": {"id", "name"}, "finance_transactions": set()})
    assert "0096:project_phases.address_line" in gaps
    assert "0097:finance_transactions.agreement_id" in gaps
    assert "0096:project_budget_versions" in gaps
