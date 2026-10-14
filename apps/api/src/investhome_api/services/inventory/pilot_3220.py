"""Idempotent 3220 16th St NW inventory pilot.

Reads 3220_Inventory_Pricing_Master_Pilot.xlsx and creates Project, Building,
Floor, and residential InventoryAsset rows through the existing inventory
services. Dry-run is the default. Apply never writes unless the workbook
yields exactly 43 unambiguous residential units.

No new tables or columns. Market Average becomes the versioned list price.
Trent, Urban Pace, and Turkey prices are reported and not stored.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.inventory import (
    AvailabilityStatus,
    Building,
    BuildingType,
    Floor,
    InventoryAsset,
    InventoryAssetType,
    InventorySalesStatus,
    PriceSource,
    PriceType,
    StructureStatus,
    UsageType,
)
from investhome_api.models.project import DevelopmentType, Project, ProjectStatus, ProjectType
from investhome_api.models.user_auth import Role, User, UserRole, UserStatus
from investhome_api.schemas.inventory import BuildingCreate, FloorCreate, InventoryAssetCreate
from investhome_api.schemas.project import ProjectCreate, ProjectUpdate
from investhome_api.services.activity_recorder import log_entity_created
from investhome_api.services.inventory.pricing_service import PricingError, create_initial_price, get_active_price
from investhome_api.services.inventory.system_code_service import build_system_code, generate_system_code
from investhome_api.services.inventory.validation_service import InventoryValidationError, validate_asset_create
from investhome_api.services.project_service import create_project, update_project

EXPECTED_ASSET_COUNT = 43
PROJECT_CODE = "3220-16TH-NW"
PROJECT_NAME = "3220 16th St NW"
PROJECT_ADDRESS = "3220 16th St NW"
PROJECT_CITY = "Washington"
PROJECT_STATE = "DC"
PROJECT_COUNTRY = "United States"
BUILDING_CODE = "3220"
BUILDING_NAME = "3220 16th St NW"
WORKBOOK_NAME = "3220_Inventory_Pricing_Master_Pilot.xlsx"
TWOPLACES = Decimal("0.01")

FIELD_ALIASES: dict[str, set[str]] = {
    "unit_number": {
        "unit",
        "unit number",
        "unit no",
        "unit #",
        "unit id",
        "apt",
        "apartment",
        "residence",
    },
    "floor": {"floor", "level", "story", "storey", "floor number"},
    "bedrooms": {
        "trent br",
        "bedrooms",
        "bedroom",
        "beds",
        "bed",
        "br",
        "bedroom configuration",
        "bed config",
    },
    "bathrooms": {
        "trent ba",
        "bathrooms",
        "bathroom",
        "baths",
        "bath",
        "ba",
        "bathroom configuration",
        "bath config",
    },
    "canonical_sf": {
        "canonical sf",
        "square feet",
        "sqft",
        "sq ft",
        "sf",
        "area",
        "interior sf",
        "interior sqft",
        "interior area",
        "interior square feet",
        "nrsf",
    },
    "rent_sf": {"rent sf"},
    "trent_sf": {"trent sf"},
    "urban_sf": {"urban pace sf"},
    "view": {
        "views",
        "view",
        "view type",
        "exposure",
        "view exposure",
    },
    "orientation": {"orientation", "facing"},
    "outdoor": {
        "outdoor",
        "outdoor space",
        "balcony",
        "terrace",
        "exterior",
        "exterior sf",
        "exterior sqft",
        "exterior area",
        "outdoor sf",
    },
    "monthly_rent": {"monthly rent", "rent", "est rent", "estimated rent", "rent monthly"},
    "usa_reference_price": {"usa reference price"},
    "market_average": {
        "market average",
        "market avg",
        "market average usa",
        "usa market average",
        "usa list",
        "list price",
        "market price",
    },
    "trent_mid": {"trent mid"},
    "trent_high": {"trent high"},
    "trent_avg": {"trent avg"},
    "urban_mid": {"urban pace mid"},
    "urban_high": {"urban pace high"},
    "urban_avg": {"urban pace avg"},
    "urban_floorplan": {"urban floorplan"},
}

# Exact headers only. "Trent BR" / "Trent SF" must stay available as source fields.
UNSUPPORTED_EXACT: dict[str, str] = {
    "trent": "Bare Trent price column is not stored.",
    "urban pace": "Bare Urban Pace price column is not stored.",
    "urbanpace": "Bare Urban Pace price column is not stored.",
    "turkey": "Turkey price is not stored in this phase.",
    "turkey price": "Turkey price is not stored in this phase.",
}

# No basement convention exists on Floor. Cellar is below the 1st floor.
CELLAR_FLOOR = (-1, "Cellar", "CL")
NAMED_FLOORS: dict[str, tuple[int, str, str]] = {
    "cellar": CELLAR_FLOOR,
    "basement": CELLAR_FLOOR,
    "below grade": CELLAR_FLOOR,
}
PRICE_SOURCE_FIELDS = (
    "usa_reference_price",
    "market_average",
    "canonical_sf",
    "rent_sf",
    "trent_sf",
)

ORIENTATIONS = {
    "N": "N",
    "S": "S",
    "E": "E",
    "W": "W",
    "NE": "NE",
    "NW": "NW",
    "SE": "SE",
    "SW": "SW",
    "NORTH": "N",
    "SOUTH": "S",
    "EAST": "E",
    "WEST": "W",
    "NORTHEAST": "NE",
    "NORTHWEST": "NW",
    "SOUTHEAST": "SE",
    "SOUTHWEST": "SW",
}

SKIP_UNIT_LABELS = {"total", "totals", "subtotal", "average", "avg", "sum", "notes", "note"}


class PilotRefused(RuntimeError):
    """Apply was refused. Nothing was written by this call."""


@dataclass
class PilotRow:
    sheet: str
    row_number: int
    display_id: str
    floor_number: int | None
    floor_label: str | None
    bedrooms: str | None
    bathrooms: str | None
    interior_sqft: str | None
    exterior_sqft: str | None
    total_sqft: str | None
    view_type: str | None
    orientation: str | None
    list_price: str | None
    monthly_rent: str | None
    status: str
    reasons: list[str] = field(default_factory=list)
    unsupported_values: list[str] = field(default_factory=list)
    discrepancies: list[str] = field(default_factory=list)
    floor_level_code: str | None = None
    system_code: str | None = None


@dataclass
class PilotPlan:
    workbook_path: str | None
    workbook_found: bool
    project_code: str = PROJECT_CODE
    project_name: str = PROJECT_NAME
    address: str = PROJECT_ADDRESS
    city: str = PROJECT_CITY
    state: str = PROJECT_STATE
    building_code: str = BUILDING_CODE
    building_name: str = BUILDING_NAME
    sheets_used: list[str] = field(default_factory=list)
    sheets_ignored: list[str] = field(default_factory=list)
    unsupported_fields: list[str] = field(default_factory=list)
    unmapped_headers: list[str] = field(default_factory=list)
    rows: list[PilotRow] = field(default_factory=list)
    structure_errors: list[str] = field(default_factory=list)
    importable: bool = False

    @property
    def accepted(self) -> list[PilotRow]:
        return [row for row in self.rows if row.status == "accepted"]

    def summary(self) -> dict[str, Any]:
        accepted = self.accepted
        floors_by_number: dict[int, dict[str, Any]] = {}
        for row in accepted:
            if row.floor_number is None or row.floor_number in floors_by_number:
                continue
            floors_by_number[row.floor_number] = {
                "floor_number": row.floor_number,
                "level_code": row.floor_level_code,
                "display_name": row.floor_label,
            }
        sqft = _sum_decimal(row.interior_sqft or row.total_sqft for row in accepted)
        list_price = _sum_decimal(row.list_price for row in accepted)
        discrepancies = [
            {"unit": row.display_id, "row_number": row.row_number, "items": row.discrepancies}
            for row in accepted
            if row.discrepancies
        ]
        return {
            "workbook_path": self.workbook_path,
            "workbook_found": self.workbook_found,
            "importable": self.importable,
            "project": {
                "action": "create_or_reuse",
                "project_code": self.project_code,
                "project_name": self.project_name,
                "address": self.address,
                "city": self.city,
                "state": self.state,
                "residential_units": EXPECTED_ASSET_COUNT,
                "total_units": EXPECTED_ASSET_COUNT,
                "match_rule": (
                    "Reuse a non-archived project with code 3220-16TH-NW or address "
                    "3220 16th St NW. 3220 Minnesota Ave NE is not a match."
                ),
            },
            "building": {
                "action": "create_or_reuse",
                "code": self.building_code,
                "name": self.building_name,
                "building_type": BuildingType.CONDOMINIUM.value,
            },
            "floors": [floors_by_number[number] for number in sorted(floors_by_number)],
            "assets_to_create": len(accepted),
            "expected_assets": EXPECTED_ASSET_COUNT,
            "unit_numbers": [row.display_id for row in accepted],
            "total_square_feet": str(sqft),
            "total_initial_list_price": str(list_price),
            "currency": "USD",
            "price_type": PriceType.LIST.value,
            "rent_price_type": PriceType.ESTIMATED_RENT.value,
            "asset_type": InventoryAssetType.RESIDENTIAL_UNIT.value,
            "availability_status": AvailabilityStatus.AVAILABLE.value,
            "sales_status": InventorySalesStatus.AVAILABLE_FOR_SALE.value,
            "unsupported_fields": self.unsupported_fields,
            "unmapped_headers": self.unmapped_headers,
            "sheets_used": self.sheets_used,
            "sheets_ignored": self.sheets_ignored,
            "structure_errors": self.structure_errors,
            "accepted_count": len(accepted),
            "rejected": [_row_dict(row) for row in self.rows if row.status == "rejected"],
            "ambiguous": [_row_dict(row) for row in self.rows if row.status == "ambiguous"],
            "accepted_flags": [
                _row_dict(row) for row in accepted if row.reasons or row.unsupported_values
            ],
            "source_discrepancies": discrepancies,
        }


def default_workbook_candidates() -> list[Path]:
    downloads = Path.home() / "Downloads" / WORKBOOK_NAME
    return [
        Path("artifacts/3220") / WORKBOOK_NAME,
        Path(WORKBOOK_NAME),
        downloads,
    ]


def resolve_workbook(explicit: str | None) -> Path | None:
    if explicit:
        path = Path(explicit)
        return path if path.is_file() else None
    for candidate in default_workbook_candidates():
        if candidate.is_file():
            return candidate
    return None


def address_is_3220_16th(address: str | None) -> bool:
    if not address:
        return False
    tokens = re.sub(r"[^a-z0-9]+", " ", address.lower()).split()
    if "minnesota" in tokens:
        return False
    return "3220" in tokens and "16th" in tokens and "nw" in tokens


def build_plan(workbook: Path | None) -> PilotPlan:
    plan = PilotPlan(workbook_path=str(workbook) if workbook else None, workbook_found=workbook is not None)
    if workbook is None:
        plan.structure_errors.append(
            f"{WORKBOOK_NAME} was not found. Dry-run cannot list the 43 units until the workbook is supplied."
        )
        return plan
    from openpyxl import load_workbook

    book = load_workbook(workbook, data_only=True, read_only=True)
    try:
        parsed_sheets: list[tuple[str, list[PilotRow], list[str], list[str]]] = []
        for sheet in book.worksheets:
            rows, unsupported, unmapped, header_found = _parse_sheet(sheet.title, sheet.iter_rows(values_only=True))
            if header_found:
                parsed_sheets.append((sheet.title, rows, unsupported, unmapped))
            else:
                plan.sheets_ignored.append(sheet.title)
        if not parsed_sheets:
            plan.structure_errors.append("No worksheet with a unit-number header was found.")
            return plan
        named = [item for item in parsed_sheets if item[0].strip().lower() == "unit inventory"]
        if named:
            chosen_name, chosen_rows, unsupported, unmapped = named[0]
            parsed_sheets = [item for item in parsed_sheets if item is not named[0]]
        else:
            parsed_sheets.sort(key=lambda item: sum(1 for row in item[1] if row.status == "accepted"), reverse=True)
            chosen_name, chosen_rows, unsupported, unmapped = parsed_sheets.pop(0)
            parsed_sheets = parsed_sheets
        plan.sheets_used.append(chosen_name)
        for name, _rows, _unsupported, _unmapped in parsed_sheets:
            plan.sheets_ignored.append(name)
            if not named:
                plan.structure_errors.append(
                    f"Additional inventory sheet '{name}' was ignored. Only '{chosen_name}' is used."
                )
        plan.unsupported_fields = unsupported
        plan.unmapped_headers = unmapped
        plan.rows = _mark_duplicate_units(chosen_rows)
        _assign_preview_codes(plan)
        accepted = len(plan.accepted)
        rejected = sum(1 for row in plan.rows if row.status == "rejected")
        ambiguous = sum(1 for row in plan.rows if row.status == "ambiguous")
        if accepted != EXPECTED_ASSET_COUNT:
            plan.structure_errors.append(
                f"Accepted residential rows are {accepted}; the pilot requires exactly {EXPECTED_ASSET_COUNT}."
            )
        if rejected or ambiguous:
            plan.structure_errors.append(
                "Rejected or ambiguous source rows are present. They are flagged and will not be rewritten."
            )
        plan.importable = accepted == EXPECTED_ASSET_COUNT and rejected == 0 and ambiguous == 0 and not any(
            error.startswith("Additional inventory sheet") for error in plan.structure_errors
        )
        if any(error.startswith("Additional inventory sheet") for error in plan.structure_errors):
            plan.importable = False
    finally:
        book.close()
    return plan


def dry_run_report(plan: PilotPlan, db: Session | None = None) -> dict[str, Any]:
    report = plan.summary()
    report["mode"] = "dry_run"
    report["writes"] = 0
    if db is None:
        report["duplicate_collision_checks"] = {
            "database_checked": False,
            "detail": "Database was not opened. Workbook-only duplicate checks are included.",
        }
        return report
    report["duplicate_collision_checks"] = _collision_check(db, plan)
    project = report["duplicate_collision_checks"].get("project")
    if isinstance(project, dict) and project.get("action"):
        report["project"]["action"] = project["action"]
        if project.get("id"):
            report["project"]["existing_id"] = project["id"]
    return report


def apply_pilot(workbook: Path, *, session: Session | None = None) -> dict[str, Any]:
    """Write the pilot. Caller must already have confirmed this is not a dry-run."""
    plan = build_plan(workbook)
    if not plan.importable:
        raise PilotRefused("Workbook is not importable. Run a dry-run and resolve flagged rows first.")

    owns_session = session is None
    db = session or _session()
    try:
        collisions = _collision_check(db, plan)
        blockers = collisions.get("blockers") or []
        if blockers:
            raise PilotRefused("; ".join(blockers))
        actor = _resolve_actor(db)
        project, project_action = _ensure_project(db, actor)
        building, building_action = _ensure_building(db, project)
        floors = _ensure_floors(db, building, plan.accepted)
        created_assets = 0
        reused_assets = 0
        created_list_prices = 0
        reused_list_prices = 0
        created_rent_prices = 0
        price_flags: list[str] = []
        for row in plan.accepted:
            floor = floors[row.floor_number]
            asset, created = _ensure_asset(db, project, building, floor, row)
            db.commit()
            if created:
                created_assets += 1
            else:
                reused_assets += 1
            list_result = _ensure_price(
                db,
                asset,
                actor,
                price_type=PriceType.LIST,
                amount=Decimal(row.list_price or "0"),
                reason="3220 pilot market average",
            )
            if list_result == "created":
                created_list_prices += 1
            elif list_result == "reused":
                reused_list_prices += 1
            elif list_result.startswith("differs:"):
                price_flags.append(f"{row.display_id} list price {list_result}")
            if row.monthly_rent:
                rent_result = _ensure_price(
                    db,
                    asset,
                    actor,
                    price_type=PriceType.ESTIMATED_RENT,
                    amount=Decimal(row.monthly_rent),
                    reason="3220 pilot monthly rent",
                )
                if rent_result == "created":
                    created_rent_prices += 1
                elif rent_result.startswith("differs:"):
                    price_flags.append(f"{row.display_id} monthly rent {rent_result}")
        _set_project_counts(db, project, actor)
        active_count = int(
            db.scalar(
                select(func.count())
                .select_from(InventoryAsset)
                .where(
                    InventoryAsset.project_id == project.id,
                    InventoryAsset.archived_at.is_(None),
                )
            )
            or 0
        )
        if active_count != EXPECTED_ASSET_COUNT:
            raise PilotRefused(
                f"Active inventory assets for {PROJECT_CODE} are {active_count}, not {EXPECTED_ASSET_COUNT}."
            )
        return {
            "mode": "apply",
            "project_id": str(project.id),
            "project_action": project_action,
            "building_action": building_action,
            "floors": len(floors),
            "created_assets": created_assets,
            "reused_assets": reused_assets,
            "created_list_prices": created_list_prices,
            "reused_list_prices": reused_list_prices,
            "created_rent_prices": created_rent_prices,
            "active_assets": active_count,
            "price_flags": price_flags,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        if owns_session:
            db.close()


def _parse_sheet(
    sheet_name: str,
    rows: Any,
) -> tuple[list[PilotRow], list[str], list[str], bool]:
    materialized = list(rows)
    header_index = _header_index(materialized)
    if header_index is None:
        return [], [], [], False
    header = [_normalize_header(cell) for cell in materialized[header_index]]
    mapping, unsupported, unmapped = _map_headers(header)
    if "unit_number" not in mapping or not any(name in mapping for name in PRICE_SOURCE_FIELDS):
        return [], unsupported, unmapped, False
    parsed: list[PilotRow] = []
    for offset, raw in enumerate(materialized[header_index + 1 :], start=header_index + 2):
        if _row_empty(raw):
            continue
        parsed.append(_parse_row(sheet_name, offset, raw, mapping))
    return parsed, unsupported, unmapped, True


def _header_index(rows: list[tuple[Any, ...]]) -> int | None:
    best_index = None
    best_score = 0
    for index, raw in enumerate(rows[:25]):
        headers = [_normalize_header(cell) for cell in raw]
        mapping, _unsupported, _unmapped = _map_headers(headers)
        score = len(mapping)
        if "unit_number" in mapping and score > best_score:
            best_index = index
            best_score = score
    return best_index


def _map_headers(headers: list[str]) -> tuple[dict[str, int], list[str], list[str]]:
    mapping: dict[str, int] = {}
    unsupported: list[str] = []
    unmapped: list[str] = []
    for index, header in enumerate(headers):
        if not header:
            continue
        unsupported_note = _unsupported_header(header)
        if unsupported_note:
            unsupported.append(f"{header}: {unsupported_note}")
            continue
        field_name = _field_for_header(header)
        if field_name is None:
            unmapped.append(header)
            continue
        if field_name in mapping:
            unmapped.append(f"{header} (duplicate of {field_name})")
            continue
        mapping[field_name] = index
    return mapping, unsupported, unmapped


def _parse_row(sheet: str, row_number: int, raw: tuple[Any, ...], mapping: dict[str, int]) -> PilotRow:
    discrepancies: list[str] = []
    unsupported_values: list[str] = []
    unit_raw = _cell(raw, mapping.get("unit_number"))
    display_id = _display_id(unit_raw)
    if display_id is None or display_id.lower() in SKIP_UNIT_LABELS:
        return PilotRow(
            sheet=sheet,
            row_number=row_number,
            display_id=display_id or "",
            floor_number=None,
            floor_label=None,
            bedrooms=None,
            bathrooms=None,
            interior_sqft=None,
            exterior_sqft=None,
            total_sqft=None,
            view_type=None,
            orientation=None,
            list_price=None,
            monthly_rent=None,
            status="rejected",
            reasons=["Blank, total, or unreadable unit number."],
        )

    floor_number, floor_label, floor_level_code, floor_reason = _parse_floor(_cell(raw, mapping.get("floor")))
    reasons: list[str] = []
    if floor_reason:
        reasons.append(floor_reason)

    bedrooms, bed_notes = _parse_bedrooms(_cell(raw, mapping.get("bedrooms")))
    bathrooms, bath_notes = _parse_count(_cell(raw, mapping.get("bathrooms")), "bathroom configuration")
    discrepancies.extend(bed_notes)
    if bath_notes:
        discrepancies.append(bath_notes)

    interior, _sf_source, sf_notes = _choose_square_feet(raw, mapping)
    discrepancies.extend(sf_notes)
    config_note = _configuration_discrepancy(
        _cell(raw, mapping.get("bedrooms")),
        _cell(raw, mapping.get("urban_floorplan")),
    )
    if config_note:
        discrepancies.append(config_note)

    _exterior, _exterior_reason, exterior_text = _parse_outdoor(_cell(raw, mapping.get("outdoor")))
    if exterior_text:
        note = f"Outdoor '{exterior_text}' has no dedicated field and was not stored."
        discrepancies.append(note)
        unsupported_values.append(note)

    view_type, orientation, view_notes = _parse_view(
        _cell(raw, mapping.get("view")),
        _cell(raw, mapping.get("orientation")),
    )
    discrepancies.extend(view_notes)

    list_price, price_notes = _choose_list_price(raw, mapping)
    discrepancies.extend(price_note for price_note in price_notes if not price_note.startswith("Missing"))
    rent, rent_reason = _parse_money(_cell(raw, mapping.get("monthly_rent")), "monthly rent")
    if rent_reason and _cell(raw, mapping.get("monthly_rent")) not in (None, ""):
        discrepancies.append(rent_reason)
        rent = None

    status = "accepted"
    if floor_number is None:
        status = "ambiguous"
        if not floor_reason:
            reasons.append("Missing floor.")
    if list_price is None:
        status = "rejected"
        reasons.append("Missing USA Reference Price. It could not be read or derived.")

    return PilotRow(
        sheet=sheet,
        row_number=row_number,
        display_id=display_id,
        floor_number=floor_number,
        floor_label=floor_label,
        floor_level_code=floor_level_code,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        interior_sqft=interior,
        exterior_sqft=None,
        total_sqft=interior,
        view_type=view_type,
        orientation=orientation,
        list_price=list_price,
        monthly_rent=rent,
        status=status,
        reasons=reasons,
        unsupported_values=unsupported_values,
        discrepancies=discrepancies,
    )


def _mark_duplicate_units(rows: list[PilotRow]) -> list[PilotRow]:
    seen: dict[str, int] = {}
    for row in rows:
        if not row.display_id or row.status == "rejected" and "unit number" in " ".join(row.reasons).lower():
            continue
        key = row.display_id.casefold()
        if key in seen:
            row.status = "rejected"
            row.reasons.append(f"Duplicate unit number {row.display_id} (also on row {seen[key]}).")
        else:
            seen[key] = row.row_number
    return rows


def _assign_preview_codes(plan: PilotPlan) -> None:
    seen: set[str] = set()
    for row in plan.accepted:
        level = row.floor_level_code or (f"{row.floor_number:02d}" if row.floor_number is not None else "00")
        code = build_system_code(
            project_code=PROJECT_CODE,
            building_code=BUILDING_CODE,
            floor_level_code=level,
            display_id=row.display_id,
        )
        candidate = code
        suffix = 1
        while candidate in seen:
            candidate = f"{code}-{suffix}"
            suffix += 1
        seen.add(candidate)
        row.system_code = candidate


def _collision_check(db: Session, plan: PilotPlan) -> dict[str, Any]:
    project, project_note = _find_project(db)
    blockers: list[str] = []
    if project_note == "ambiguous":
        blockers.append("More than one existing project matches 3220 16th St NW.")
    planned_ids = [row.display_id for row in plan.accepted]
    planned_codes = [row.system_code for row in plan.accepted if row.system_code]
    existing_assets: list[InventoryAsset] = []
    if project is not None and project_note != "ambiguous":
        existing_assets = list(
            db.scalars(
                select(InventoryAsset).where(
                    InventoryAsset.project_id == project.id,
                    InventoryAsset.archived_at.is_(None),
                )
            ).all()
        )
    existing_ids = {asset.display_id for asset in existing_assets}
    extras = sorted(existing_ids - set(planned_ids))
    if extras:
        blockers.append(
            "Existing active assets are not in the workbook and would make the project count differ from 43: "
            + ", ".join(extras)
        )
    code_hits: list[str] = []
    if planned_codes:
        code_hits = list(
            db.scalars(select(InventoryAsset.system_code).where(InventoryAsset.system_code.in_(planned_codes))).all()
        )
    owned_codes = {asset.system_code for asset in existing_assets}
    foreign_codes = sorted(set(code_hits) - owned_codes)
    return {
        "database_checked": True,
        "workbook_duplicate_unit_numbers": [
            row.display_id for row in plan.rows if any(reason.startswith("Duplicate unit") for reason in row.reasons)
        ],
        "project": {
            "action": "reuse" if project is not None and project_note != "ambiguous" else "create" if project_note != "ambiguous" else "blocked",
            "id": str(project.id) if project is not None and project_note != "ambiguous" else None,
            "project_code": project.project_code if project is not None and project_note != "ambiguous" else PROJECT_CODE,
            "address": project.address if project is not None and project_note != "ambiguous" else PROJECT_ADDRESS,
            "note": project_note,
        },
        "existing_active_assets": len(existing_assets),
        "existing_display_ids_reused": sorted(existing_ids.intersection(planned_ids)),
        "system_code_collisions_resolved_by_suffix": foreign_codes,
        "blockers": blockers,
    }


def _find_project(db: Session) -> tuple[Project | None, str]:
    by_code = db.scalar(
        select(Project).where(Project.project_code == PROJECT_CODE, Project.archived_at.is_(None))
    )
    candidates = list(
        db.scalars(
            select(Project).where(
                Project.archived_at.is_(None),
                Project.address.is_not(None),
                Project.address.ilike("%3220%"),
            )
        ).all()
    )
    by_address = [project for project in candidates if address_is_3220_16th(project.address)]
    ids = {project.id for project in by_address}
    if by_code is not None:
        ids.add(by_code.id)
    if len(ids) > 1:
        return None, "ambiguous"
    if by_code is not None:
        return by_code, "matched_code"
    if by_address:
        return by_address[0], "matched_address"
    return None, "not_found"


def _ensure_project(db: Session, actor: User) -> tuple[Project, str]:
    project, note = _find_project(db)
    if note == "ambiguous":
        raise PilotRefused("Project match is ambiguous.")
    if project is None:
        created = create_project(
            db,
            ProjectCreate(
                project_code=PROJECT_CODE,
                project_name=PROJECT_NAME,
                address=PROJECT_ADDRESS,
                city=PROJECT_CITY,
                state=PROJECT_STATE,
                country=PROJECT_COUNTRY,
                project_type=ProjectType.RESIDENTIAL,
                development_type=DevelopmentType.GROUND_UP,
                project_status=ProjectStatus.PIPELINE,
                residential_units=EXPECTED_ASSET_COUNT,
                commercial_units=0,
                total_units=EXPECTED_ASSET_COUNT,
                currency="USD",
                description="3220 16th St NW residential inventory pilot.",
            ),
            actor=actor,
        )
        return created, "created"
    return project, "reused"


def _set_project_counts(db: Session, project: Project, actor: User) -> None:
    commercial = project.commercial_units or 0
    if commercial > 0:
        raise PilotRefused(
            f"Project commercial_units is {commercial}. Refusing to overwrite the unit counts."
        )
    if project.residential_units == EXPECTED_ASSET_COUNT and project.total_units == EXPECTED_ASSET_COUNT:
        return
    update_project(
        db,
        project.id,
        ProjectUpdate(
            residential_units=EXPECTED_ASSET_COUNT,
            commercial_units=0,
            total_units=EXPECTED_ASSET_COUNT,
        ),
        actor=actor,
    )


def _ensure_building(db: Session, project: Project) -> tuple[Building, str]:
    existing = db.scalar(
        select(Building).where(
            Building.project_id == project.id,
            Building.code == BUILDING_CODE,
            Building.archived_at.is_(None),
        )
    )
    if existing is not None:
        return existing, "reused"
    payload = BuildingCreate(
        project_id=project.id,
        name=BUILDING_NAME,
        code=BUILDING_CODE,
        building_type=BuildingType.CONDOMINIUM,
        address=PROJECT_ADDRESS,
        status=StructureStatus.ACTIVE,
    )
    building = Building(**payload.model_dump())
    db.add(building)
    db.flush()
    from investhome_api.models.activity import ActivityEntityType

    log_entity_created(
        db,
        entity_type=ActivityEntityType.BUILDING,
        entity_id=building.id,
        description_key="activity.inventory.building.created",
        actor=None,
        metadata={"name": building.name, "code": building.code, "pilot": PROJECT_CODE},
        is_demo=False,
    )
    return building, "created"


def _ensure_floors(db: Session, building: Building, rows: list[PilotRow]) -> dict[int, Floor]:
    labels: dict[int, str] = {}
    codes: dict[int, str] = {}
    for row in rows:
        if row.floor_number is None:
            continue
        labels.setdefault(row.floor_number, row.floor_label or f"Floor {row.floor_number}")
        codes.setdefault(row.floor_number, row.floor_level_code or f"{row.floor_number:02d}")
    floors: dict[int, Floor] = {}
    for number in sorted(labels):
        existing = db.scalar(
            select(Floor).where(
                Floor.building_id == building.id,
                Floor.floor_number == number,
                Floor.archived_at.is_(None),
            )
        )
        if existing is not None:
            floors[number] = existing
            continue
        payload = FloorCreate(
            building_id=building.id,
            floor_number=number,
            display_name=labels[number],
            level_code=codes[number],
            sort_order=number,
            status=StructureStatus.ACTIVE,
        )
        floor = Floor(**payload.model_dump())
        db.add(floor)
        db.flush()
        floors[number] = floor
    building.total_floors = len(floors)
    return floors


def _ensure_asset(
    db: Session,
    project: Project,
    building: Building,
    floor: Floor,
    row: PilotRow,
) -> tuple[InventoryAsset, bool]:
    existing = db.scalar(
        select(InventoryAsset).where(
            InventoryAsset.project_id == project.id,
            InventoryAsset.display_id == row.display_id,
            InventoryAsset.archived_at.is_(None),
        )
    )
    if existing is not None:
        return existing, False
    payload = InventoryAssetCreate(
        project_id=project.id,
        building_id=building.id,
        floor_id=floor.id,
        display_id=row.display_id,
        asset_type=InventoryAssetType.RESIDENTIAL_UNIT,
        usage_type=UsageType.RESIDENTIAL,
        bedrooms=_decimal_or_none(row.bedrooms),
        bathrooms=_decimal_or_none(row.bathrooms),
        interior_area_sqft=_decimal_or_none(row.interior_sqft),
        exterior_area_sqft=_decimal_or_none(row.exterior_sqft),
        total_area_sqft=_decimal_or_none(row.total_sqft),
        orientation=row.orientation,
        view_type=row.view_type,
        availability_status=AvailabilityStatus.AVAILABLE,
        sales_status=InventorySalesStatus.AVAILABLE_FOR_SALE,
        currency="USD",
    )
    validate_asset_create(
        db,
        project_id=payload.project_id,
        asset_type=payload.asset_type,
        usage_type=payload.usage_type,
        building_id=payload.building_id,
        floor_id=payload.floor_id,
    )
    system_code = generate_system_code(
        db,
        project_id=project.id,
        building_id=building.id,
        floor_id=floor.id,
        display_id=row.display_id,
    )
    asset = InventoryAsset(**payload.model_dump(), system_code=system_code, is_demo=False)
    db.add(asset)
    db.flush()
    from investhome_api.models.activity import ActivityEntityType

    log_entity_created(
        db,
        entity_type=ActivityEntityType.INVENTORY_ASSET,
        entity_id=asset.id,
        description_key="activity.inventory.asset.created",
        actor=None,
        metadata={"display_id": asset.display_id, "system_code": asset.system_code, "pilot": PROJECT_CODE},
        is_demo=False,
    )
    return asset, True


def _ensure_price(
    db: Session,
    asset: InventoryAsset,
    actor: User,
    *,
    price_type: PriceType,
    amount: Decimal,
    reason: str,
) -> str:
    existing = get_active_price(db, asset.id, price_type, "USD")
    quantized = amount.quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    if existing is not None:
        if existing.amount != quantized:
            return f"differs:{existing.amount}"
        return "reused"
    create_initial_price(
        db,
        asset_id=asset.id,
        price_type=price_type,
        amount=quantized,
        currency="USD",
        effective_from=datetime.now(UTC).date(),
        effective_to=None,
        reason=reason,
        actor=actor,
        source=PriceSource.INITIAL,
    )
    db.commit()
    return "created"


def _resolve_actor(db: Session) -> User:
    admin_id = db.scalar(
        select(UserRole.user_id)
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.code == "super_admin")
        .limit(1)
    )
    if admin_id is not None:
        admin = db.get(User, admin_id)
        if admin is not None and admin.archived_at is None:
            return admin
    user = db.scalar(
        select(User).where(User.archived_at.is_(None), User.status == UserStatus.ACTIVE).limit(1)
    )
    if user is None:
        raise PilotRefused("No active user is available to attribute pricing records.")
    return user


def _session() -> Session:
    from investhome_api.db.session import SessionLocal

    return SessionLocal()


def _normalize_header(value: Any) -> str:
    text = str(value or "").replace("\n", " ").replace("_", " ").replace("/", " ")
    text = re.sub(r"[^a-z0-9\s#]", "", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def _unsupported_header(header: str) -> str | None:
    if header in UNSUPPORTED_EXACT:
        return UNSUPPORTED_EXACT[header]
    if "turk" in header or "trkiye" in header:
        return "Turkey pricing is not stored in this phase."
    return None


def _field_for_header(header: str) -> str | None:
    for field_name, aliases in FIELD_ALIASES.items():
        if header in aliases:
            return field_name
    return None


def _cell(raw: tuple[Any, ...], index: int | None) -> Any:
    if index is None or index >= len(raw):
        return None
    return raw[index]


def _row_empty(raw: tuple[Any, ...]) -> bool:
    return all(cell is None or str(cell).strip() == "" for cell in raw)


def _display_id(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        text = str(int(value))
    elif isinstance(value, int):
        text = str(value)
    elif isinstance(value, Decimal):
        text = str(int(value)) if value == value.to_integral() else format(value, "f")
    else:
        text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    if not text or len(text) > 50:
        return None
    return text


def _parse_floor(value: Any) -> tuple[int | None, str | None, str | None, str | None]:
    """Return floor_number, display label, level_code, and an error.

    Floor.floor_number is an integer and the seed data only uses positive levels.
    Cellar is stored as -1 with level code CL so it stays distinct and below 1st.
    """
    if value is None or str(value).strip() == "":
        return None, None, None, "Missing floor. Residential units require a floor."
    if isinstance(value, float) and value.is_integer():
        number = int(value)
        return number, str(number), f"{number:02d}", None
    if isinstance(value, int) and not isinstance(value, bool):
        return value, str(value), f"{value:02d}", None
    text = str(value).strip()
    named = NAMED_FLOORS.get(text.lower())
    if named is not None:
        number, label, code = named
        return number, label, code, None
    if re.fullmatch(r"\d+", text):
        number = int(text)
        return number, text, f"{number:02d}", None
    ordinal = re.fullmatch(r"(\d+)(st|nd|rd|th)", text, flags=re.IGNORECASE)
    if ordinal is not None:
        number = int(ordinal.group(1))
        return number, text, f"{number:02d}", None
    return None, text, None, f"Ambiguous floor '{text}'."


def _parse_bedrooms(value: Any) -> tuple[str | None, list[str]]:
    if value is None or str(value).strip() == "":
        return None, []
    number = _plain_decimal(value)
    if number is not None:
        return _format_count(number), []
    text = str(value).strip()
    den = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(?:/|\+)\s*den", text, flags=re.IGNORECASE)
    if den is not None:
        stored = _format_count(Decimal(den.group(1)))
        return stored, [
            f"Trent BR '{text}' stored as {stored} bedrooms. Den is not a separate field."
        ]
    return None, [f"Bedroom configuration '{text}' was not stored."]


def _choose_square_feet(raw: tuple[Any, ...], mapping: dict[str, int]) -> tuple[str | None, str | None, list[str]]:
    labeled = (
        ("Canonical SF", _optional_area(_cell(raw, mapping.get("canonical_sf")))),
        ("Rent SF", _optional_area(_cell(raw, mapping.get("rent_sf")))),
        ("Trent SF", _optional_area(_cell(raw, mapping.get("trent_sf")))),
        ("Urban Pace SF", _optional_area(_cell(raw, mapping.get("urban_sf")))),
    )
    present = [(label, amount) for label, amount in labeled if amount is not None]
    notes: list[str] = []
    if len({amount for _label, amount in present}) > 1:
        detail = ", ".join(f"{label} {amount}" for label, amount in present)
        chosen_label = next(label for label, amount in labeled if amount is not None)
        notes.append(f"Square footage discrepancy: {detail}. Using {chosen_label}.")
    for label, amount in labeled:
        if amount is not None:
            return str(amount), label, notes
    return None, None, notes


def _choose_list_price(raw: tuple[Any, ...], mapping: dict[str, int]) -> tuple[str | None, list[str]]:
    notes: list[str] = []
    usa = _optional_money(_cell(raw, mapping.get("usa_reference_price")))
    market = _optional_money(_cell(raw, mapping.get("market_average")))
    trent_avg = _optional_money(_cell(raw, mapping.get("trent_avg")))
    if trent_avg is None:
        trent_avg = _average_money(
            _optional_money(_cell(raw, mapping.get("trent_mid"))),
            _optional_money(_cell(raw, mapping.get("trent_high"))),
        )
    urban_avg = _optional_money(_cell(raw, mapping.get("urban_avg")))
    if urban_avg is None:
        urban_avg = _average_money(
            _optional_money(_cell(raw, mapping.get("urban_mid"))),
            _optional_money(_cell(raw, mapping.get("urban_high"))),
        )
    if trent_avg is not None and urban_avg is not None and trent_avg != urban_avg:
        notes.append(
            f"Broker price discrepancy: Trent Avg {trent_avg} vs Urban Pace Avg {urban_avg}. "
            "USA Reference Price was not changed."
        )
    derived = market if market is not None else _average_money(trent_avg, urban_avg)
    chosen = usa if usa is not None else derived
    if chosen is None:
        return None, notes
    return str(chosen), notes


def _configuration_discrepancy(trent_br: Any, urban_floorplan: Any) -> str | None:
    if trent_br in (None, "") or urban_floorplan in (None, ""):
        return None
    trent_text = str(trent_br).strip()
    urban_text = str(urban_floorplan).strip()
    trent_count = _leading_count(trent_text)
    urban_count = _leading_count(urban_text)
    if trent_count is None or urban_count is None:
        return None
    trent_den = "den" in trent_text.lower()
    urban_den = "den" in urban_text.lower()
    if trent_count != urban_count or trent_den != urban_den:
        return (
            f"Bedroom configuration discrepancy: Trent BR '{trent_text}' vs "
            f"Urban Floorplan '{urban_text}'. Stored Trent BR."
        )
    return None


def _leading_count(value: str) -> Decimal | None:
    match = re.search(r"\d+(?:\.\d+)?", value)
    if match is None:
        return None
    return Decimal(match.group())


def _optional_area(value: Any) -> Decimal | None:
    number = _plain_decimal(value)
    if number is None or number < 0:
        return None
    return number.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _optional_money(value: Any) -> Decimal | None:
    number = _plain_decimal(value)
    if number is None or number < 0:
        return None
    return number.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _average_money(left: Decimal | None, right: Decimal | None) -> Decimal | None:
    if left is None or right is None:
        return None
    return ((left + right) / 2).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _format_count(number: Decimal) -> str:
    return format(number.quantize(Decimal("0.1")), "f")


def _parse_count(value: Any, label: str) -> tuple[str | None, str | None]:
    if value is None or str(value).strip() == "":
        return None, None
    number = _plain_decimal(value)
    if number is None:
        return None, f"Ambiguous {label} '{value}'."
    if number < 0 or number > Decimal("99"):
        return None, f"Unreadable {label} '{value}'."
    return format(number.quantize(Decimal("0.1")), "f"), None


def _parse_area(value: Any, label: str) -> tuple[str | None, str | None]:
    if value is None or str(value).strip() == "":
        return None, None
    number = _plain_decimal(value)
    if number is None:
        return None, f"Ambiguous {label} '{value}'."
    if number < 0:
        return None, f"Unreadable {label} '{value}'."
    return str(number.quantize(TWOPLACES, rounding=ROUND_HALF_UP)), None


def _parse_outdoor(value: Any) -> tuple[str | None, str | None, str | None]:
    if value is None or str(value).strip() == "":
        return None, None, None
    number = _plain_decimal(value)
    if number is None:
        return None, None, str(value).strip()
    if number < 0:
        return None, f"Unreadable outdoor space '{value}'.", None
    return str(number.quantize(TWOPLACES, rounding=ROUND_HALF_UP)), None, None


def _parse_view(view_raw: Any, orientation_raw: Any) -> tuple[str | None, str | None, list[str]]:
    reasons: list[str] = []
    orientation = _orientation_token(orientation_raw) if orientation_raw not in (None, "") else None
    view_text = None if view_raw in (None, "") else str(view_raw).strip()
    if view_text and orientation is None:
        extracted = _orientation_token(view_text)
        if extracted and _normalize_header(view_text).upper() in ORIENTATIONS:
            orientation = extracted
            view_text = None
        elif extracted:
            orientation = extracted
    if view_text and len(view_text) > 80:
        reasons.append(f"Ambiguous view '{view_text[:40]}…' exceeds 80 characters.")
        view_text = None
    if orientation_raw not in (None, "") and orientation is None:
        reasons.append(f"Ambiguous orientation '{orientation_raw}'.")
    return view_text, orientation, reasons


def _orientation_token(value: Any) -> str | None:
    text = re.sub(r"[^A-Za-z]", "", str(value)).upper()
    if text in ORIENTATIONS:
        return ORIENTATIONS[text]
    for token in ("NORTHWEST", "NORTHEAST", "SOUTHWEST", "SOUTHEAST", "NORTH", "SOUTH", "EAST", "WEST", "NW", "NE", "SW", "SE"):
        if token in text:
            return ORIENTATIONS[token]
    return None


def _parse_money(value: Any, label: str) -> tuple[str | None, str | None]:
    if value is None or str(value).strip() == "":
        return None, f"Missing {label}."
    number = _plain_decimal(value)
    if number is None or number < 0:
        return None, f"Ambiguous {label} '{value}'."
    return str(number.quantize(TWOPLACES, rounding=ROUND_HALF_UP)), None


def _plain_decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    text = str(value).strip().replace(",", "").replace("$", "").replace(" ", "")
    text = text.replace("sqft", "").replace("sf", "")
    if not re.fullmatch(r"\d+(\.\d+)?", text):
        return None
    return Decimal(text)


def _decimal_or_none(value: str | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value)


def _sum_decimal(values: Any) -> Decimal:
    total = Decimal("0.00")
    for value in values:
        if value:
            total += Decimal(value)
    return total.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _row_dict(row: PilotRow) -> dict[str, Any]:
    payload = asdict(row)
    return payload


def _json_ready(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


def run_command(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="investhome-3220-pilot",
        description="Dry-run or apply the 3220 16th St NW inventory pilot. Dry-run is the default.",
    )
    parser.add_argument("--workbook", default=None, help=f"Path to {WORKBOOK_NAME}")
    parser.add_argument("--apply", action="store_true", help="Write inventory. Refused without --confirm-3220-pilot.")
    parser.add_argument(
        "--confirm-3220-pilot",
        action="store_true",
        help="Required with --apply. Dry-run never writes.",
    )
    args = parser.parse_args(argv)
    workbook = resolve_workbook(args.workbook)
    plan = build_plan(workbook)
    if not args.apply:
        db = None
        try:
            db = _session()
            report = dry_run_report(plan, db)
        except Exception as exc:  # noqa: BLE001 — dry-run must still return the workbook report
            report = dry_run_report(plan, None)
            report["duplicate_collision_checks"] = {
                "database_checked": False,
                "detail": f"Database collision check failed: {exc.__class__.__name__}",
            }
        finally:
            if db is not None:
                db.rollback()
                db.close()
        print(json.dumps(_json_ready(report), indent=2))
        return 0
    if not args.confirm_3220_pilot:
        print("Refused. --apply requires --confirm-3220-pilot. No rows were written.", file=sys.stderr)
        return 2
    if workbook is None:
        print(f"Refused. {WORKBOOK_NAME} was not found. No rows were written.", file=sys.stderr)
        return 2
    try:
        result = apply_pilot(workbook)
    except (PilotRefused, PricingError, InventoryValidationError) as exc:
        print(f"Refused. {exc}", file=sys.stderr)
        return 2
    print(json.dumps(_json_ready(result), indent=2))
    return 0


def console_main() -> None:
    raise SystemExit(run_command())


if __name__ == "__main__":
    console_main()
