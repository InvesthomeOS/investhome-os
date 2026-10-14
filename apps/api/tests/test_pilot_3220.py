"""3220 inventory pilot parser, dry-run, and idempotent apply tests."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook
from sqlalchemy import func, select

from investhome_api.models.inventory import InventoryAsset, InventoryAssetPrice, PriceType
from investhome_api.models.project import DevelopmentType, Project, ProjectStatus, ProjectType
from investhome_api.models.user_auth import User, UserStatus
from investhome_api.services.inventory.pilot_3220 import (
    EXPECTED_ASSET_COUNT,
    address_is_3220_16th,
    apply_pilot,
    build_plan,
    dry_run_report,
)
from investhome_api.services.project_detail_service import get_units


HEADERS = [
    "Unit Number",
    "Floor",
    "Bedroom Configuration",
    "Bathroom Configuration",
    "Square Feet",
    "View / Exposure",
    "Outdoor Space",
    "Monthly Rent",
    "Market Average",
    "Trent",
    "Urban Pace",
    "Turkey Price",
]


def _write_workbook(path: Path, rows: list[list[object]]) -> Path:
    book = Workbook()
    sheet = book.active
    sheet.title = "Inventory"
    sheet.append(["3220 16th St NW"])
    sheet.append(HEADERS)
    for row in rows:
        sheet.append(row)
    book.save(path)
    book.close()
    return path


def _clean_rows(count: int = EXPECTED_ASSET_COUNT) -> list[list[object]]:
    rows: list[list[object]] = []
    for index in range(count):
        floor = 2 + (index // 6)
        unit = f"{floor}{index % 6 + 1:02d}"
        rows.append(
            [
                unit,
                floor,
                1 + (index % 3),
                1 + (index % 2),
                700 + index,
                "City / NW",
                40 if index % 2 == 0 else "balcony",
                2500 + index,
                500000 + index * 1000,
                480000,
                510000,
                19000000,
            ]
        )
    return rows


def test_address_match_ignores_minnesota_campus():
    assert address_is_3220_16th("3220 16th St NW")
    assert address_is_3220_16th("3220 16th Street NW")
    assert not address_is_3220_16th("3220 & 3224 Minnesota Ave NE")
    assert not address_is_3220_16th("1627 16th St NW")


def test_clean_workbook_is_importable(tmp_path: Path):
    path = _write_workbook(tmp_path / "3220_Inventory_Pricing_Master_Pilot.xlsx", _clean_rows())
    plan = build_plan(path)
    report = dry_run_report(plan, None)

    assert plan.importable
    assert report["assets_to_create"] == 43
    assert len(report["unit_numbers"]) == 43
    assert len(set(report["unit_numbers"])) == 43
    assert report["total_square_feet"] == f"{sum(700 + index for index in range(43))}.00"
    assert report["total_initial_list_price"] == f"{sum(500000 + index * 1000 for index in range(43))}.00"
    assert any("Trent" in item for item in report["unsupported_fields"])
    assert any("Urban Pace" in item for item in report["unsupported_fields"])
    assert any("Turkey" in item for item in report["unsupported_fields"])
    assert any(item["unsupported_values"] for item in report["accepted_flags"])
    codes = [row.system_code for row in plan.accepted]
    assert len(codes) == len(set(codes))
    assert report["writes"] == 0


def test_real_3220_workbook_dry_run():
    workbook = (
        Path(__file__).resolve().parents[3]
        / "artifacts"
        / "3220"
        / "3220_Inventory_Pricing_Master_Pilot.xlsx"
    )
    assert workbook.is_file()
    report = dry_run_report(build_plan(workbook), None)
    assert report["writes"] == 0
    assert report["accepted_count"] == 43
    assert report["assets_to_create"] == 43
    assert report["rejected"] == []
    assert report["ambiguous"] == []
    assert report["unit_numbers"][0] == "001"
    assert report["unit_numbers"][-1] == "702"
    assert "003" in report["unit_numbers"]
    assert [floor["display_name"] for floor in report["floors"]] == [
        "Cellar",
        "1st",
        "2nd",
        "3rd",
        "4th",
        "5th",
        "6th",
        "7th",
    ]
    assert report["floors"][0]["floor_number"] == -1
    assert report["floors"][0]["level_code"] == "CL"
    assert report["total_square_feet"] == "35224.00"
    assert report["total_initial_list_price"] == "23765847.50"
    cellar = next(row for row in build_plan(workbook).accepted if row.display_id == "001")
    assert cellar.bedrooms == "2.0"
    assert cellar.bathrooms == "2.0"
    assert cellar.interior_sqft == "885.00"
    flagged = {item["unit"] for item in report["source_discrepancies"]}
    assert "003" in flagged
    assert "101" in flagged
    assert "506" in flagged


def test_duplicate_and_ambiguous_rows_are_flagged(tmp_path: Path):
    rows = _clean_rows()
    rows.append(rows[0])
    rows.append(["PH1", "PH", 2, 2, 900, "Park", 0, 3000, 800000, 1, 1, 1])
    rows.append(["Total", "", "", "", 100, "", "", "", 1, "", "", ""])
    path = _write_workbook(tmp_path / "3220.xlsx", rows)
    plan = build_plan(path)

    assert not plan.importable
    report = dry_run_report(plan, None)
    assert any(item["display_id"] == rows[0][0] for item in report["rejected"])
    assert any(item["display_id"] == "PH1" for item in report["ambiguous"])
    assert report["assets_to_create"] == 43


def test_apply_is_idempotent_and_uses_versioned_prices(tmp_path: Path, client, db):
    db.add(
        User(
            full_name="Pilot Actor",
            email="pilot-3220@example.com",
            hashed_password="not-a-real-secret",
            status=UserStatus.ACTIVE,
        )
    )
    db.add(
        Project(
            project_code="PRJ-CAMP-004",
            project_name="The Campus",
            address="3220 & 3224 Minnesota Ave NE",
            city="Washington",
            state="DC",
            project_type=ProjectType.MIXED_USE,
            development_type=DevelopmentType.GROUND_UP,
            project_status=ProjectStatus.PERMITTING,
        )
    )
    db.commit()

    path = _write_workbook(tmp_path / "3220_Inventory_Pricing_Master_Pilot.xlsx", _clean_rows())
    first = apply_pilot(path)
    second = apply_pilot(path)

    assert first["created_assets"] == 43
    assert first["active_assets"] == 43
    assert first["created_list_prices"] == 43
    assert second["created_assets"] == 0
    assert second["reused_assets"] == 43
    assert second["created_list_prices"] == 0
    assert second["reused_list_prices"] == 43
    assert second["active_assets"] == 43

    project = db.scalar(select(Project).where(Project.project_code == "3220-16TH-NW"))
    assert project is not None
    assert project.residential_units == 43
    assert project.total_units == 43
    assert project.address == "3220 16th St NW"

    asset_count = db.scalar(
        select(func.count()).select_from(InventoryAsset).where(InventoryAsset.project_id == project.id)
    )
    price_count = db.scalar(
        select(func.count())
        .select_from(InventoryAssetPrice)
        .where(InventoryAssetPrice.price_type == PriceType.LIST)
    )
    assert asset_count == 43
    assert price_count == 43

    sample = db.scalar(
        select(InventoryAsset).where(
            InventoryAsset.project_id == project.id,
            InventoryAsset.display_id == "201",
        )
    )
    assert sample is not None
    assert sample.availability_status.value == "available"
    assert sample.sales_status.value == "available_for_sale"
    assert sample.list_price == Decimal("500000.00")
    assert sample.asset_type.value == "residential_unit"

    actor = db.scalar(select(User).where(User.email == "pilot-3220@example.com"))
    assert actor is not None
    detail = get_units(db, actor, project.id, page_size=100)
    assert detail.total == 43
    match = next(item for item in detail.items if item["unit"] == "201")
    assert match["floor_number"] == 2
    assert match["floor_label"] == "2"
    assert match["sales_status"] == "available_for_sale"
