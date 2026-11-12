"""Workbook import keeps unit identity and refuses an unverified project."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook
from sqlalchemy import func, select

from investhome_api.models.inventory import (
    AvailabilityStatus,
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
from investhome_api.services.inventory.excel_import import run_inventory_import
from investhome_api.services.inventory.phase_identity import find_duplicate_phase_units
from investhome_api.services.inventory.sales_price_rollup import project_sales_price_totals


def _project(db, *, code: str, name: str, address: str) -> Project:
    project = Project(
        project_code=code,
        project_name=name,
        address=address,
        city="Washington",
        state="DC",
        project_type=ProjectType.RESIDENTIAL,
        development_type=DevelopmentType.GROUND_UP,
        project_status=ProjectStatus.CONSTRUCTION,
    )
    db.add(project)
    db.flush()
    return project


def _building(db, project: Project, *, code: str, name: str) -> Building:
    building = Building(
        project_id=project.id,
        name=name,
        code=code,
        building_type=BuildingType.CONDOMINIUM,
        status=StructureStatus.ACTIVE,
    )
    db.add(building)
    db.flush()
    return building


def _floor(db, building: Building, number: int) -> Floor:
    floor = Floor(
        building_id=building.id,
        floor_number=number,
        display_name=str(number),
        level_code=str(number),
        status=StructureStatus.ACTIVE,
    )
    db.add(floor)
    db.flush()
    return floor


def _workbook(path: Path, rows: list[list[object]]) -> Path:
    book = Workbook()
    sheet = book.active
    sheet.append(
        [
            "Project ID",
            "Building",
            "Phase",
            "Unit Number",
            "Floor",
            "Unit Type",
            "Bedrooms",
            "Bathrooms",
            "Interior SF",
            "Exterior SF",
            "List Price",
            "Sales Status",
            "Availability Status",
        ]
    )
    for row in rows:
        sheet.append(row)
    book.save(path)
    return path


def _row(code: str, **overrides: object) -> list[object]:
    values = {
        "building": "A",
        "phase": None,
        "unit": "201",
        "floor": 2,
        "unit_type": "residential",
        "beds": 2,
        "baths": 2,
        "interior": 900,
        "exterior": 40,
        "price": 500000,
        "sales": "available_for_sale",
        "availability": "available",
    }
    values.update(overrides)
    return [
        code,
        values["building"],
        values["phase"],
        values["unit"],
        values["floor"],
        values["unit_type"],
        values["beds"],
        values["baths"],
        values["interior"],
        values["exterior"],
        values["price"],
        values["sales"],
        values["availability"],
    ]


def test_dry_run_plans_a_create_and_writes_nothing(tmp_path: Path, db):
    project = _project(db, code="PRJ-IMPORT-0", name="Import Zero", address="0 Test St")
    building = _building(db, project, code="A", name="Tower A")
    _floor(db, building, 2)
    db.commit()
    report = run_inventory_import(
        db,
        str(_workbook(tmp_path / "dry.xlsx", [_row(project.project_code)])),
        apply=False,
    )
    db.commit()
    assert report.dry_run is True
    assert report.blocked is False
    assert report.created == 1
    assert db.scalar(select(func.count()).select_from(InventoryAsset)) == 0
    assert db.scalar(select(func.count()).select_from(InventoryAssetPrice)) == 0


def test_second_run_reuses_uuid_and_skips_same_price(tmp_path: Path, db):
    project = _project(db, code="PRJ-IMPORT-1", name="Import One", address="1 Test St")
    building = _building(db, project, code="A", name="Tower A")
    _floor(db, building, 2)
    db.commit()
    path = _workbook(tmp_path / "units.xlsx", [_row(project.project_code)])

    first = run_inventory_import(db, str(path), apply=True)
    db.commit()
    second = run_inventory_import(db, str(path), apply=True)
    db.commit()

    assets = list(db.scalars(select(InventoryAsset).where(InventoryAsset.project_id == project.id)))
    prices = list(db.scalars(select(InventoryAssetPrice)))
    assert first.created == 1
    assert first.price_writes == 1
    assert second.created == 0
    assert second.unchanged == 1
    assert second.price_writes == 0
    assert len(assets) == 1
    assert assets[0].id.hex == first.rows[0].asset_id.replace("-", "")
    assert assets[0].system_code == first.rows[0].system_code == second.rows[0].system_code
    assert len(prices) == 1
    assert prices[0].status == PriceStatus.ACTIVE
    assert assets[0].list_price == Decimal("500000.00")


def test_blank_cells_do_not_clear_existing_values(tmp_path: Path, db):
    project = _project(db, code="PRJ-IMPORT-2", name="Import Two", address="2 Test St")
    building = _building(db, project, code="A", name="Tower A")
    _floor(db, building, 2)
    db.commit()
    path = _workbook(tmp_path / "full.xlsx", [_row(project.project_code)])
    run_inventory_import(db, str(path), apply=True)
    db.commit()
    blank = _workbook(
        tmp_path / "blank.xlsx",
        [_row(project.project_code, beds=None, baths=None, interior=None, exterior=None, price=500000)],
    )
    report = run_inventory_import(db, str(blank), apply=True)
    db.commit()
    asset = db.scalar(select(InventoryAsset).where(InventoryAsset.project_id == project.id))
    assert report.price_writes == 0
    assert asset is not None
    assert asset.bedrooms == Decimal("2")
    assert asset.bathrooms == Decimal("2")
    assert asset.interior_area_sqft == Decimal("900")
    assert asset.exterior_area_sqft == Decimal("40")


def test_price_change_uses_history_and_keeps_identity(tmp_path: Path, db):
    project = _project(db, code="PRJ-IMPORT-3", name="Import Three", address="3 Test St")
    building = _building(db, project, code="A", name="Tower A")
    _floor(db, building, 2)
    db.commit()
    original = _workbook(tmp_path / "price.xlsx", [_row(project.project_code)])
    run_inventory_import(db, str(original), apply=True)
    db.commit()
    before = db.scalar(select(InventoryAsset).where(InventoryAsset.display_id == "201"))
    assert before is not None
    original_id = before.id
    original_code = before.system_code
    changed = _workbook(tmp_path / "price-2.xlsx", [_row(project.project_code, price=525000)])
    report = run_inventory_import(db, str(changed), apply=True)
    db.commit()
    asset = db.scalar(select(InventoryAsset).where(InventoryAsset.id == original_id))
    prices = list(
        db.scalars(
            select(InventoryAssetPrice)
            .where(InventoryAssetPrice.inventory_asset_id == original_id)
            .order_by(InventoryAssetPrice.created_at)
        )
    )
    assert report.price_writes == 1
    assert asset is not None
    assert asset.id == original_id
    assert asset.system_code == original_code
    assert asset.list_price == Decimal("525000.00")
    assert [row.status for row in prices] == [PriceStatus.SUPERSEDED, PriceStatus.ACTIVE]
    assert prices[1].amount == Decimal("525000.00")


def test_unknown_project_and_unmatched_structure_write_nothing(tmp_path: Path, db):
    campus = _project(
        db,
        code="PRJ-CAMP-004",
        name="The Campus",
        address="3220 & 3224 Minnesota Ave NE",
    )
    target = _project(db, code="PRJ-IMPORT-4", name="Import Four", address="4 Test St")
    building = _building(db, target, code="A", name="Tower A")
    _floor(db, building, 2)
    keeper = InventoryAsset(
        project_id=target.id,
        building_id=building.id,
        display_id="101",
        system_code="KEEP-101",
        asset_type=InventoryAssetType.RESIDENTIAL_UNIT,
        usage_type=UsageType.RESIDENTIAL,
        bedrooms=Decimal("1"),
        currency="USD",
    )
    db.add(keeper)
    db.commit()

    refused = run_inventory_import(
        db,
        str(_workbook(tmp_path / "missing-project.xlsx", [_row("3224 16th St NW")])),
        apply=True,
    )
    missing_building = run_inventory_import(
        db,
        str(_workbook(tmp_path / "missing-building.xlsx", [_row(target.project_code, building="Missing")])),
        apply=True,
    )
    missing_floor = run_inventory_import(
        db,
        str(_workbook(tmp_path / "missing-floor.xlsx", [_row(target.project_code, floor=9)])),
        apply=True,
    )
    missing_phase = run_inventory_import(
        db,
        str(_workbook(tmp_path / "missing-phase.xlsx", [_row(target.project_code, phase="Historic")])),
        apply=True,
    )
    db.commit()

    assert refused.blocked
    assert any("project identity" in issue.message for issue in refused.issues)
    assert missing_building.blocked
    assert missing_floor.blocked
    assert missing_phase.blocked
    assert db.scalar(select(func.count()).select_from(InventoryAsset).where(InventoryAsset.project_id == campus.id)) == 0
    assert db.scalar(select(func.count()).select_from(InventoryAsset).where(InventoryAsset.project_id == target.id)) == 1
    kept = db.scalar(select(InventoryAsset).where(InventoryAsset.display_id == "101"))
    assert kept is not None
    assert kept.system_code == "KEEP-101"
    assert kept.bedrooms == Decimal("1")


def test_cross_building_duplicate_stops_without_merge(db, tmp_path: Path):
    project = _project(db, code="PRJ-IMPORT-5", name="Import Five", address="5 Test St")
    first = _building(db, project, code="H", name="Historic")
    second = _building(db, project, code="N", name="Addition")
    for building in (first, second):
        db.add(
            InventoryAsset(
                project_id=project.id,
                building_id=building.id,
                display_id="301",
                system_code=f"{building.code}-301",
                asset_type=InventoryAssetType.RESIDENTIAL_UNIT,
                usage_type=UsageType.RESIDENTIAL,
                currency="USD",
                sales_status=InventorySalesStatus.AVAILABLE_FOR_SALE,
                availability_status=AvailabilityStatus.AVAILABLE,
            )
        )
    db.commit()
    conflicts = find_duplicate_phase_units(db.connection())
    report = run_inventory_import(
        db,
        str(_workbook(tmp_path / "dup.xlsx", [_row(project.project_code, unit="301", building="H", floor=None)])),
        apply=True,
    )
    db.commit()
    rows = list(
        db.scalars(
            select(InventoryAsset)
            .where(InventoryAsset.project_id == project.id)
            .order_by(InventoryAsset.system_code)
        )
    )
    assert len(conflicts) == 1
    assert conflicts[0]["duplicate_count"] == 2
    assert report.blocked
    assert report.created == 0
    assert [row.system_code for row in rows] == ["H-301", "N-301"]
    assert [row.sales_status for row in rows] == [
        InventorySalesStatus.AVAILABLE_FOR_SALE,
        InventorySalesStatus.AVAILABLE_FOR_SALE,
    ]


def test_sales_price_rollup_does_not_write_budget(tmp_path: Path, db):
    project = _project(db, code="PRJ-IMPORT-6", name="Import Six", address="6 Test St")
    building = _building(db, project, code="A", name="Tower A")
    _floor(db, building, 2)
    db.commit()
    run_inventory_import(
        db,
        str(_workbook(tmp_path / "roll.xlsx", [_row(project.project_code, price=100), _row(project.project_code, unit="202", price=50)])),
        apply=True,
    )
    db.commit()
    asset = db.scalar(select(InventoryAsset).where(InventoryAsset.display_id == "201"))
    assert asset is not None
    db.add(
        InventoryAssetPrice(
            inventory_asset_id=asset.id,
            price_type=PriceType.CONTRACTED,
            amount=Decimal("90.00"),
            currency="USD",
            effective_from=date.today(),
            status=PriceStatus.ACTIVE,
            source=PriceSource.CONTRACT,
            is_demo=False,
        )
    )
    db.commit()
    before_prices = db.scalar(select(func.count()).select_from(InventoryAssetPrice))
    totals = project_sales_price_totals(db, project.id)
    after_prices = db.scalar(select(func.count()).select_from(InventoryAssetPrice))
    assert totals["budget_written"] is False
    assert totals["scenario_estimate"] is None
    assert totals["currencies"]["USD"]["list"] == "150.00"
    assert totals["currencies"]["USD"]["contracted"] == "90.00"
    assert totals["currencies"]["USD"]["estimated_rent"] == "0.00"
    assert before_prices == after_prices
