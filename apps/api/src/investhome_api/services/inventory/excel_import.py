"""Project-independent inventory workbook import.

Business identity is project + optional phase + display id. Building is physical
and is never used to merge two units. Dry-run is the default. Apply writes only
inventory assets and list-price history. Agreements, ownership, and budgets stay
untouched.

Project identity is an id, an exact code, or an exact name. Addresses are not
matched, so 3224 16th St NW is never inferred from 3224 Minnesota Ave NE.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.inventory import (
    AvailabilityStatus,
    Building,
    Floor,
    InventoryAsset,
    InventoryAssetType,
    InventorySalesStatus,
    PriceType,
    ProjectPhase,
    UsageType,
)
from investhome_api.models.project import Project
from investhome_api.models.user_auth import User
from investhome_api.schemas.inventory import _unit_identifier
from investhome_api.services.inventory.phase_identity import find_duplicate_phase_units
from investhome_api.services.inventory.pricing_service import PricingError, get_active_price, import_list_price
from investhome_api.services.inventory.system_code_service import generate_system_code
from investhome_api.services.inventory.validation_service import (
    InventoryValidationError,
    validate_asset_create,
)
HEADER_FIELDS = {
    "project id": "project",
    "project": "project",
    "project code": "project",
    "building": "building",
    "bina": "building",
    "phase": "phase",
    "faz": "phase",
    "unit number": "unit",
    "unit": "unit",
    "display id": "unit",
    "floor": "floor",
    "kat": "floor",
    "unit type": "unit_type",
    "type": "unit_type",
    "bedrooms": "bedrooms",
    "bedroom": "bedrooms",
    "bathrooms": "bathrooms",
    "bathroom": "bathrooms",
    "interior sf": "interior_sf",
    "interior sqft": "interior_sf",
    "exterior sf": "exterior_sf",
    "exterior sqft": "exterior_sf",
    "list price": "list_price",
    "sales status": "sales_status",
    "availability status": "availability_status",
}

UNIT_TYPES: dict[str, tuple[InventoryAssetType, UsageType]] = {
    "residential": (InventoryAssetType.RESIDENTIAL_UNIT, UsageType.RESIDENTIAL),
    "residential unit": (InventoryAssetType.RESIDENTIAL_UNIT, UsageType.RESIDENTIAL),
    "residential_unit": (InventoryAssetType.RESIDENTIAL_UNIT, UsageType.RESIDENTIAL),
    "commercial": (InventoryAssetType.COMMERCIAL_UNIT, UsageType.COMMERCIAL),
    "commercial unit": (InventoryAssetType.COMMERCIAL_UNIT, UsageType.COMMERCIAL),
    "commercial_unit": (InventoryAssetType.COMMERCIAL_UNIT, UsageType.COMMERCIAL),
    "parking": (InventoryAssetType.PARKING_SPACE, UsageType.PARKING),
    "parking space": (InventoryAssetType.PARKING_SPACE, UsageType.PARKING),
    "parking_space": (InventoryAssetType.PARKING_SPACE, UsageType.PARKING),
    "storage": (InventoryAssetType.STORAGE_UNIT, UsageType.STORAGE),
    "storage unit": (InventoryAssetType.STORAGE_UNIT, UsageType.STORAGE),
    "storage_unit": (InventoryAssetType.STORAGE_UNIT, UsageType.STORAGE),
    "office": (InventoryAssetType.OFFICE_UNIT, UsageType.OFFICE),
    "office unit": (InventoryAssetType.OFFICE_UNIT, UsageType.OFFICE),
    "office_unit": (InventoryAssetType.OFFICE_UNIT, UsageType.OFFICE),
    "retail": (InventoryAssetType.RETAIL_UNIT, UsageType.RETAIL),
    "retail unit": (InventoryAssetType.RETAIL_UNIT, UsageType.RETAIL),
    "retail_unit": (InventoryAssetType.RETAIL_UNIT, UsageType.RETAIL),
    "land": (InventoryAssetType.LAND_PARCEL, UsageType.MIXED),
    "land parcel": (InventoryAssetType.LAND_PARCEL, UsageType.MIXED),
    "land_parcel": (InventoryAssetType.LAND_PARCEL, UsageType.MIXED),
}


@dataclass
class ImportIssue:
    row_number: int
    code: str
    message: str


@dataclass
class RowPlan:
    row_number: int
    action: str
    project_id: str | None = None
    display_id: str | None = None
    asset_id: str | None = None
    system_code: str | None = None
    price_action: str = "none"
    messages: list[str] = field(default_factory=list)


@dataclass
class ImportReport:
    dry_run: bool
    blocked: bool
    issues: list[ImportIssue]
    rows: list[RowPlan]
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    price_writes: int = 0

    def as_dict(self) -> dict[str, object]:
        return {
            "dry_run": self.dry_run,
            "blocked": self.blocked,
            "created": self.created,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "price_writes": self.price_writes,
            "issues": [issue.__dict__ for issue in self.issues],
            "rows": [
                {
                    "row_number": row.row_number,
                    "action": row.action,
                    "project_id": row.project_id,
                    "display_id": row.display_id,
                    "asset_id": row.asset_id,
                    "system_code": row.system_code,
                    "price_action": row.price_action,
                    "messages": row.messages,
                }
                for row in self.rows
            ],
        }


@dataclass
class _ParsedRow:
    row_number: int
    values: dict[str, object]
    errors: list[str]


def _clean(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _header_key(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _decimal(value: object) -> Decimal:
    text = str(value).strip().replace(",", "").replace("$", "")
    return Decimal(text)


def _enum_value(enum_cls: type, raw: str):
    token = raw.strip().casefold().replace(" ", "_").replace("-", "_")
    for item in enum_cls:
        if item.value.casefold() == token or item.name.casefold() == token:
            return item
    return None


def load_workbook_rows(path: str) -> list[_ParsedRow]:
    from openpyxl import load_workbook

    workbook = load_workbook(path, data_only=True, read_only=True)
    try:
        sheet = workbook.worksheets[0]
        grid = list(sheet.iter_rows(values_only=True))
    finally:
        workbook.close()
    if not grid:
        return []
    fields = [HEADER_FIELDS.get(_header_key(cell)) for cell in grid[0]]
    parsed: list[_ParsedRow] = []
    for offset, values in enumerate(grid[1:], start=2):
        if values is None or all(_clean(cell) is None for cell in values):
            continue
        raw: dict[str, object] = {}
        errors: list[str] = []
        for index, field_name in enumerate(fields):
            if field_name is None or index >= len(values) or _clean(values[index]) is None:
                continue
            cell = values[index]
            if field_name == "unit":
                try:
                    raw[field_name] = str(_unit_identifier(cell))
                except ValueError as exc:
                    errors.append(str(exc))
                continue
            if field_name in {"bedrooms", "bathrooms", "interior_sf", "exterior_sf", "list_price"}:
                try:
                    raw[field_name] = _decimal(cell)
                except InvalidOperation:
                    errors.append(f"{field_name} is not a number")
                continue
            if field_name == "sales_status":
                status = _enum_value(InventorySalesStatus, str(cell))
                if status is None:
                    errors.append("sales status is not a known value")
                else:
                    raw[field_name] = status
                continue
            if field_name == "availability_status":
                status = _enum_value(AvailabilityStatus, str(cell))
                if status is None:
                    errors.append("availability status is not a known value")
                else:
                    raw[field_name] = status
                continue
            raw[field_name] = _clean(cell)
        if "unit_type" in raw and str(raw["unit_type"]).casefold() not in UNIT_TYPES:
            errors.append("unit type is not a known value")
        parsed.append(_ParsedRow(offset, raw, errors))
    return parsed


def _parse_uuid(value: str) -> UUID | None:
    try:
        return UUID(value)
    except ValueError:
        return None


def _resolve_project(projects: list[Project], token: str) -> tuple[Project | None, str | None]:
    """Match an id, exact code, or exact name. Addresses are ignored."""
    identifier = _parse_uuid(token)
    if identifier is not None:
        matches = [row for row in projects if row.id == identifier]
        if len(matches) == 1:
            return matches[0], None
        return None, "project id does not exist"
    codes = [row for row in projects if row.project_code.casefold() == token.casefold()]
    if len(codes) == 1:
        return codes[0], None
    if len(codes) > 1:
        return None, "project code matches more than one project"
    names = [row for row in projects if row.project_name.casefold() == token.casefold()]
    if len(names) == 1:
        return names[0], None
    if len(names) > 1:
        return None, "project name matches more than one project"
    return None, "project identity is not an existing id, code, or exact name"


def _resolve_building(rows: list[Building], token: str) -> tuple[Building | None, str | None]:
    matches = [
        row
        for row in rows
        if row.archived_at is None
        and (row.code.casefold() == token.casefold() or row.name.casefold() == token.casefold())
    ]
    if len(matches) == 1:
        return matches[0], None
    if len(matches) > 1:
        return None, f"building {token} matches more than one building"
    return None, f"building {token} was not found in the project"


def _resolve_phase(rows: list[ProjectPhase], token: str) -> tuple[ProjectPhase | None, str | None]:
    matches = [row for row in rows if row.name.casefold() == token.casefold()]
    if len(matches) == 1:
        return matches[0], None
    if len(matches) > 1:
        return None, f"phase {token} matches more than one phase"
    return None, f"phase {token} was not found in the project"


def _resolve_floor(rows: list[Floor], token: str) -> tuple[Floor | None, str | None]:
    number = int(token) if token.lstrip("-").isdigit() else None
    matches: list[Floor] = []
    for row in rows:
        if row.archived_at is not None:
            continue
        if number is not None and row.floor_number == number:
            matches.append(row)
        elif (row.display_name or "").casefold() == token.casefold():
            matches.append(row)
        elif (row.level_code or "").casefold() == token.casefold():
            matches.append(row)
    unique = {row.id: row for row in matches}
    if len(unique) == 1:
        return next(iter(unique.values())), None
    if len(unique) > 1:
        return None, f"floor {token} matches more than one floor"
    return None, f"floor {token} was not found in the building"


def _matching_assets(
    assets: list[InventoryAsset],
    *,
    phase: ProjectPhase | None,
    phase_specified: bool,
    display_id: str,
) -> list[InventoryAsset]:
    rows = [row for row in assets if row.display_id == display_id]
    if phase_specified:
        phase_id = phase.id if phase is not None else None
        return [row for row in rows if row.phase_id == phase_id]
    return rows


def _changed_fields(
    asset: InventoryAsset,
    parsed: _ParsedRow,
    *,
    building: Building | None,
    floor: Floor | None,
    phase: ProjectPhase | None,
) -> dict[str, object]:
    changes: dict[str, object] = {}
    if building is not None and asset.building_id is None:
        changes["building_id"] = building.id
    if floor is not None and asset.floor_id != floor.id:
        changes["floor_id"] = floor.id
    if phase is not None and asset.phase_id is None:
        changes["phase_id"] = phase.id
    unit_type = parsed.values.get("unit_type")
    if isinstance(unit_type, str):
        asset_type, usage_type = UNIT_TYPES[unit_type.casefold()]
        if asset.asset_type != asset_type:
            changes["asset_type"] = asset_type
        if asset.usage_type != usage_type:
            changes["usage_type"] = usage_type
    mapping = (
        ("bedrooms", "bedrooms"),
        ("bathrooms", "bathrooms"),
        ("interior_sf", "interior_area_sqft"),
        ("exterior_sf", "exterior_area_sqft"),
    )
    for source, target in mapping:
        if source in parsed.values and getattr(asset, target) != parsed.values[source]:
            changes[target] = parsed.values[source]
    if "sales_status" in parsed.values and asset.sales_status != parsed.values["sales_status"]:
        changes["sales_status"] = parsed.values["sales_status"]
    if (
        "availability_status" in parsed.values
        and asset.availability_status != parsed.values["availability_status"]
    ):
        changes["availability_status"] = parsed.values["availability_status"]
    return changes


def run_inventory_import(
    db: Session,
    path: str,
    *,
    apply: bool = False,
    actor: User | None = None,
) -> ImportReport:
    """Plan a workbook. Writes only when apply is true and every row is clean."""
    issues: list[ImportIssue] = []
    plans: list[RowPlan] = []
    parsed_rows = load_workbook_rows(path)
    if not parsed_rows:
        return ImportReport(
            dry_run=not apply,
            blocked=True,
            issues=[ImportIssue(0, "workbook", "workbook has no data rows")],
            rows=[],
        )

    projects = list(db.scalars(select(Project)))
    workbook_project_ids: set[UUID] = set()
    prepared: list[dict[str, object]] = []
    seen_keys: dict[tuple[str, str, str], int] = {}

    for parsed in parsed_rows:
        plan = RowPlan(row_number=parsed.row_number, action="blocked")
        messages = list(parsed.errors)
        display_id = parsed.values.get("unit")
        project_token = parsed.values.get("project")
        plan.display_id = str(display_id) if display_id else None
        if not display_id:
            messages.append("unit number is required")
        if not isinstance(project_token, str):
            messages.append("project identity is required")
            project = None
        else:
            project, project_error = _resolve_project(projects, project_token)
            if project_error or project is None:
                messages.append(project_error or "project identity is required")
                project = None
            else:
                plan.project_id = str(project.id)
                workbook_project_ids.add(project.id)

        building = None
        phase = None
        floor = None
        phase_specified = "phase" in parsed.values
        if project is not None and isinstance(parsed.values.get("building"), str):
            buildings = list(
                db.scalars(select(Building).where(Building.project_id == project.id))
            )
            building, building_error = _resolve_building(buildings, str(parsed.values["building"]))
            if building_error:
                messages.append(building_error)
        if project is not None and isinstance(parsed.values.get("phase"), str):
            phases = list(
                db.scalars(select(ProjectPhase).where(ProjectPhase.project_id == project.id))
            )
            phase, phase_error = _resolve_phase(phases, str(parsed.values["phase"]))
            if phase_error:
                messages.append(phase_error)
            if not project.uses_phases:
                phase = None
                phase_specified = False
        if "floor" in parsed.values and building is None:
            messages.append("floor requires a matched building")
        elif building is not None and isinstance(parsed.values.get("floor"), str):
            floors = list(db.scalars(select(Floor).where(Floor.building_id == building.id)))
            floor, floor_error = _resolve_floor(floors, str(parsed.values["floor"]))
            if floor_error:
                messages.append(floor_error)

        existing: list[InventoryAsset] = []
        structural_error = any(
            message.startswith(("building ", "phase ", "floor ")) for message in messages
        )
        if project is not None and display_id and not structural_error:
            project_assets = list(
                db.scalars(select(InventoryAsset).where(InventoryAsset.project_id == project.id))
            )
            existing = _matching_assets(
                project_assets,
                phase=phase,
                phase_specified=phase_specified,
                display_id=str(display_id),
            )
            phase_key = str(phase.id) if phase is not None else ""
            if not phase_specified and len(existing) > 1:
                messages.append("phase is blank and more than one unit uses this number")
            elif len(existing) > 1:
                messages.append(
                    "existing units already share project + phase + unit across buildings; not merged"
                )
            key = (str(project.id), phase_key if phase_specified else "*", str(display_id))
            if key in seen_keys:
                messages.append(
                    f"workbook repeats project + phase + unit; first row is {seen_keys[key]}"
                )
            else:
                seen_keys[key] = parsed.row_number
            if len(existing) == 1:
                asset = existing[0]
                plan.asset_id = str(asset.id)
                plan.system_code = asset.system_code
                if asset.archived_at is not None:
                    messages.append("matching unit is archived and was not restored")
                if (
                    building is not None
                    and asset.building_id is not None
                    and asset.building_id != building.id
                ):
                    messages.append("workbook building differs from the existing unit building")
                if phase is not None and asset.phase_id is not None and asset.phase_id != phase.id:
                    messages.append("workbook phase differs from the existing unit phase")

        if not existing and "unit_type" not in parsed.values and not messages:
            messages.append("unit type is required for a new unit")

        for message in messages:
            issues.append(ImportIssue(parsed.row_number, "row", message))
        plan.messages = messages
        if messages:
            plan.action = "blocked"
        elif existing:
            asset = existing[0]
            changes = _changed_fields(
                asset,
                parsed,
                building=building,
                floor=floor,
                phase=phase,
            )
            price_action = "none"
            if "list_price" in parsed.values:
                active = get_active_price(db, asset.id, PriceType.LIST, asset.currency)
                amount = parsed.values["list_price"]
                assert isinstance(amount, Decimal)
                if active is not None and active.amount == amount.quantize(Decimal("0.01")):
                    price_action = "unchanged"
                elif active is None:
                    price_action = "created"
                else:
                    price_action = "changed"
            plan.price_action = price_action
            plan.action = "update" if changes or price_action in {"created", "changed"} else "unchanged"
        else:
            plan.action = "create"
            if "list_price" in parsed.values:
                plan.price_action = "created"
        plans.append(plan)
        prepared.append(
            {
                "parsed": parsed,
                "plan": plan,
                "project": project,
                "building": building,
                "phase": phase,
                "floor": floor,
                "existing": existing,
            }
        )

    if workbook_project_ids:
        for conflict in find_duplicate_phase_units(db.connection()):
            if conflict["project_id"] not in workbook_project_ids:
                continue
            issues.append(
                ImportIssue(
                    0,
                    "identity_conflict",
                    "database already has project + phase + unit count "
                    f"{conflict['duplicate_count']} for display_id {conflict['display_id']}",
                )
            )

    blocked = bool(issues)
    report = ImportReport(
        dry_run=not apply,
        blocked=blocked,
        issues=issues,
        rows=plans,
        created=sum(1 for row in plans if row.action == "create" and not blocked),
        updated=sum(1 for row in plans if row.action == "update" and not blocked),
        unchanged=sum(1 for row in plans if row.action == "unchanged" and not blocked),
        price_writes=sum(
            1
            for row in plans
            if row.price_action in {"created", "changed"} and not blocked
        ),
    )
    if blocked or not apply:
        if blocked:
            report.created = 0
            report.updated = 0
            report.unchanged = 0
            report.price_writes = 0
        return report

    for item in prepared:
        plan = item["plan"]
        parsed = item["parsed"]
        project = item["project"]
        building = item["building"]
        floor = item["floor"]
        phase = item["phase"]
        existing = item["existing"]
        assert isinstance(plan, RowPlan)
        assert isinstance(parsed, _ParsedRow)
        assert isinstance(project, Project)
        assert isinstance(existing, list)
        if plan.action == "create":
            unit_type = str(parsed.values["unit_type"])
            asset_type, usage_type = UNIT_TYPES[unit_type.casefold()]
            building_id = building.id if isinstance(building, Building) else None
            floor_id = floor.id if isinstance(floor, Floor) else None
            try:
                validate_asset_create(
                    db,
                    project_id=project.id,
                    asset_type=asset_type,
                    usage_type=usage_type,
                    building_id=building_id,
                    floor_id=floor_id,
                )
            except InventoryValidationError as exc:
                raise RuntimeError(exc.error_key) from exc
            display_id = str(parsed.values["unit"])
            system_code = generate_system_code(
                db,
                project_id=project.id,
                building_id=building_id,
                floor_id=floor_id,
                display_id=display_id,
            )
            asset = InventoryAsset(
                project_id=project.id,
                building_id=building_id,
                floor_id=floor_id,
                phase_id=phase.id if isinstance(phase, ProjectPhase) else None,
                display_id=display_id,
                system_code=system_code,
                asset_type=asset_type,
                usage_type=usage_type,
                bedrooms=parsed.values.get("bedrooms") if isinstance(parsed.values.get("bedrooms"), Decimal) else None,
                bathrooms=parsed.values.get("bathrooms") if isinstance(parsed.values.get("bathrooms"), Decimal) else None,
                interior_area_sqft=parsed.values.get("interior_sf") if isinstance(parsed.values.get("interior_sf"), Decimal) else None,
                exterior_area_sqft=parsed.values.get("exterior_sf") if isinstance(parsed.values.get("exterior_sf"), Decimal) else None,
                sales_status=parsed.values.get("sales_status", InventorySalesStatus.NOT_FOR_SALE),
                availability_status=parsed.values.get("availability_status", AvailabilityStatus.NOT_RELEASED),
                currency="USD",
            )
            db.add(asset)
            db.flush()
            plan.asset_id = str(asset.id)
            plan.system_code = asset.system_code
        else:
            asset = existing[0]
            original_id = asset.id
            original_code = asset.system_code
            for name, value in _changed_fields(
                asset,
                parsed,
                building=building if isinstance(building, Building) else None,
                floor=floor if isinstance(floor, Floor) else None,
                phase=phase if isinstance(phase, ProjectPhase) else None,
            ).items():
                setattr(asset, name, value)
            if asset.id != original_id or asset.system_code != original_code:
                raise RuntimeError("import attempted to change unit identity")
            plan.asset_id = str(original_id)
            plan.system_code = original_code
        if "list_price" in parsed.values:
            amount = parsed.values["list_price"]
            assert isinstance(amount, Decimal)
            try:
                plan.price_action = import_list_price(
                    db,
                    asset=asset,
                    amount=amount,
                    actor=actor,
                    reason="inventory excel import",
                )
            except PricingError as exc:
                raise RuntimeError(exc.error_key) from exc
        db.flush()
    return report
