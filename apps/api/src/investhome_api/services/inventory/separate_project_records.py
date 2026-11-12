"""Split The Campus and The Temple into independent project rows.

No new tables. Asset, floor, price, and price-history UUIDs stay. A row moves
only when its building or phase already identifies the destination. Finance,
documents, and agreements that are not tied to those rows stay where they are.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.document import Document
from investhome_api.models.finance import FinanceTransaction, FundingCommitment
from investhome_api.models.inventory import Building, Floor, InventoryAsset, InventoryAssetPrice, ProjectPhase
from investhome_api.models.lead import Lead
from investhome_api.models.project import Project

CAMPUS_PROJECT_ID = UUID("d08ffa5a-bb69-4eaf-976c-b8ceae218e41")
CAMPUS_PROJECT_CODE = "3220-16TH-NW"
CAMPUS_3220_NAME = "The Campus / 3220"
PHASE_3220_ID = UUID("408637b5-b4c9-4b1b-8228-5d2e6e0ee33b")
PHASE_3224_ID = UUID("be98feb3-4a27-4636-81a7-acf3c65b5ac7")
BUILDING_3220_ID = UUID("89b05e1f-c786-4cea-8ae2-afaf21b76d95")
BUILDING_3224_ID = UUID("2e6ddcb9-fb26-4e8c-93ae-5638f94cc346")
CAMPUS_3224_CODE = "3224-16TH-NW"
CAMPUS_3224_NAME = "The Campus / 3224"
DEMO_CAMPUS_ID = UUID("2240179f-24dc-46d9-bf8c-654944a34bb2")
TEMPLE_PROJECT_ID = UUID("e163a03b-6864-4215-b2b4-6386f0254044")
HISTORIC_BUILDING_ID = UUID("6db2fb04-c18e-4769-912b-4f1b69ef6aa8")
ADDITION_BUILDING_ID = UUID("ea7058ec-0776-4deb-80d0-cf153bb4d079")
TEMPLE_HISTORIC_CODE = "TEMPLE-HISTORIC"
TEMPLE_ADDITION_CODE = "TEMPLE-ADDITION"
TEMPLE_HISTORIC_NAME = "The Temple / Historic"
TEMPLE_ADDITION_NAME = "The Temple / Addition"
EXPECTED_3220 = 43
EXPECTED_3224 = 21


class ProjectSplitBlocked(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class CampusSplitReport:
    campus_3220_id: UUID
    campus_3224_id: UUID
    units_3220: int
    units_3224: int
    prices_3224: int
    uses_phases: bool


@dataclass(frozen=True)
class TempleSplitReport:
    temple_id: UUID
    temple_historic_id: UUID
    temple_addition_id: UUID
    units_left: int
    agreements_left: int
    finance_left: int
    funding_left: int
    documents_left: int


def _require(row: Project | Building | ProjectPhase | None, code: str):
    if row is None:
        raise ProjectSplitBlocked(code)
    return row


def _child_project(db: Session, source: Project, *, code: str, name: str, address: str | None) -> Project:
    existing = db.scalar(select(Project).where(Project.project_code == code))
    if existing is not None:
        if existing.id in {source.id, DEMO_CAMPUS_ID} or existing.is_demo:
            raise ProjectSplitBlocked("project_code_conflict")
        return existing
    created = Project(
        id=uuid4(),
        project_code=code,
        project_name=name,
        address=address,
        city=source.city,
        state=source.state,
        postal_code=source.postal_code,
        country=source.country,
        latitude=source.latitude,
        longitude=source.longitude,
        timezone=source.timezone,
        project_type=source.project_type,
        development_type=source.development_type,
        project_status=source.project_status,
        priority=source.priority,
        currency=source.currency,
        uses_phases=False,
        is_demo=False,
        total_units=0,
    )
    db.add(created)
    db.flush()
    return created


def _assets_for_phase(db: Session, phase_id: UUID) -> list[InventoryAsset]:
    return list(
        db.scalars(
            select(InventoryAsset).where(InventoryAsset.phase_id == phase_id).order_by(InventoryAsset.id)
        ).all()
    )


def _count_linked(db: Session, model, column, asset_ids: list[UUID]) -> int:
    if not asset_ids:
        return 0
    return int(db.scalar(select(func.count()).select_from(model).where(column.in_(asset_ids))) or 0)


def _unique_display_ids(assets: list[InventoryAsset]) -> None:
    seen: set[str] = set()
    for asset in assets:
        if asset.display_id in seen:
            raise ProjectSplitBlocked("display_id_conflict")
        seen.add(asset.display_id)


def _assert_project_links(db: Session, assets: list[InventoryAsset], project_id: UUID) -> None:
    for asset in assets:
        if asset.project_id != project_id or asset.building_id is None:
            raise ProjectSplitBlocked("project_link")
        building = db.get(Building, asset.building_id)
        if building is None or building.project_id != project_id:
            raise ProjectSplitBlocked("project_link")
        if asset.floor_id is None:
            continue
        floor = db.get(Floor, asset.floor_id)
        if floor is None or floor.building_id != building.id:
            raise ProjectSplitBlocked("project_link")


def _count_project(db: Session, model, project_id: UUID) -> int:
    column = model.project_id
    return int(db.scalar(select(func.count()).select_from(model).where(column == project_id)) or 0)


def separate_campus_records(db: Session) -> CampusSplitReport:
    campus = _require(db.get(Project, CAMPUS_PROJECT_ID), "campus_missing")
    if campus.project_code != CAMPUS_PROJECT_CODE or campus.is_demo:
        raise ProjectSplitBlocked("campus_identity")
    demo = _require(db.get(Project, DEMO_CAMPUS_ID), "demo_missing")
    demo_before = (
        demo.project_code,
        demo.project_name,
        demo.is_demo,
        demo.total_units,
        demo.uses_phases,
        demo.address,
    )
    phase_3220 = _require(db.get(ProjectPhase, PHASE_3220_ID), "phase_3220_missing")
    phase_3224 = _require(db.get(ProjectPhase, PHASE_3224_ID), "phase_3224_missing")
    building_3224 = _require(db.get(Building, BUILDING_3224_ID), "building_3224_missing")
    building_3220 = _require(db.get(Building, BUILDING_3220_ID), "building_3220_missing")
    units_3224 = _assets_for_phase(db, PHASE_3224_ID)
    units_3220 = _assets_for_phase(db, PHASE_3220_ID)
    if len(units_3224) != EXPECTED_3224 or len(units_3220) != EXPECTED_3220:
        raise ProjectSplitBlocked("unit_count")
    asset_ids = [row.id for row in units_3224]
    price_ids = list(
        db.scalars(
            select(InventoryAssetPrice.id)
            .where(InventoryAssetPrice.inventory_asset_id.in_(asset_ids))
            .order_by(InventoryAssetPrice.id)
        ).all()
    )
    if any(row.project_id != campus.id or row.building_id != building_3224.id for row in units_3224):
        raise ProjectSplitBlocked("unit_link")
    if any(row.project_id != campus.id or row.building_id != building_3220.id for row in units_3220):
        raise ProjectSplitBlocked("unit_link")
    if building_3224.project_id not in {campus.id} and building_3224.project_id is not None:
        existing_target = db.get(Project, building_3224.project_id)
        if existing_target is None or existing_target.project_code != CAMPUS_3224_CODE:
            raise ProjectSplitBlocked("building_link")
    loose_finance = int(
        db.scalar(
            select(func.count()).select_from(FinanceTransaction).where(
                FinanceTransaction.project_id == campus.id
            )
        )
        or 0
    )
    loose_funding = int(
        db.scalar(
            select(func.count()).select_from(FundingCommitment).where(FundingCommitment.project_id == campus.id)
        )
        or 0
    )
    loose_docs = int(
        db.scalar(select(func.count()).select_from(Document).where(Document.project_id == campus.id)) or 0
    )
    if loose_finance or loose_funding or loose_docs:
        raise ProjectSplitBlocked("unscoped_campus_record")
    if _count_linked(db, CrmAgreement, CrmAgreement.inventory_asset_id, asset_ids):
        raise ProjectSplitBlocked("agreement_link_unexpected")
    if _count_linked(db, Lead, Lead.inventory_asset_id, asset_ids):
        raise ProjectSplitBlocked("lead_link_unexpected")

    campus_3224 = _child_project(
        db,
        campus,
        code=CAMPUS_3224_CODE,
        name=CAMPUS_3224_NAME,
        address=phase_3224.address_line or building_3224.address,
    )
    for asset in units_3224:
        asset.project_id = campus_3224.id
    building_3224.project_id = campus_3224.id
    phase_3224.project_id = campus_3224.id
    _unique_display_ids(units_3220)
    _unique_display_ids(units_3224)
    for asset in [*units_3220, *units_3224]:
        asset.phase_id = None
    phase_3220.active = False
    phase_3224.active = False
    phase_3220.project_id = campus.id
    campus.project_name = CAMPUS_3220_NAME
    campus.uses_phases = False
    campus.total_units = EXPECTED_3220
    campus_3224.uses_phases = False
    campus_3224.total_units = EXPECTED_3224
    campus_3224.is_demo = False

    db.flush()
    _assert_project_links(db, units_3220, campus.id)
    _assert_project_links(db, units_3224, campus_3224.id)
    price_after = list(
        db.scalars(
            select(InventoryAssetPrice.id)
            .where(InventoryAssetPrice.inventory_asset_id.in_(asset_ids))
            .order_by(InventoryAssetPrice.id)
        ).all()
    )
    if price_after != price_ids:
        raise ProjectSplitBlocked("price_history_changed")
    if any(row.phase_id is not None for row in [*units_3220, *units_3224]):
        raise ProjectSplitBlocked("phase_link_active")
    if phase_3220.active or phase_3224.active:
        raise ProjectSplitBlocked("phase_link_active")
    db.refresh(demo)
    demo_after = (
        demo.project_code,
        demo.project_name,
        demo.is_demo,
        demo.total_units,
        demo.uses_phases,
        demo.address,
    )
    if demo_after != demo_before:
        raise ProjectSplitBlocked("demo_changed")
    return CampusSplitReport(
        campus_3220_id=campus.id,
        campus_3224_id=campus_3224.id,
        units_3220=EXPECTED_3220,
        units_3224=EXPECTED_3224,
        prices_3224=len(price_ids),
        uses_phases=False,
    )


def separate_temple_records(db: Session) -> TempleSplitReport:
    """Move only the verified Historic and Addition buildings.

    Units, agreements, finance, funding, and documents stay on the original
    Temple project unless a row's building is one of those two buildings.
    """
    temple = _require(db.get(Project, TEMPLE_PROJECT_ID), "temple_missing")
    historic_building = _require(db.get(Building, HISTORIC_BUILDING_ID), "historic_building_missing")
    addition_building = _require(db.get(Building, ADDITION_BUILDING_ID), "addition_building_missing")
    if historic_building.project_id != temple.id or addition_building.project_id != temple.id:
        existing = {historic_building.project_id, addition_building.project_id}
        if existing != {temple.id} and None not in existing:
            owned = db.scalars(select(Project).where(Project.id.in_(existing))).all()
            codes = {row.project_code for row in owned}
            if codes != {TEMPLE_HISTORIC_CODE, TEMPLE_ADDITION_CODE}:
                raise ProjectSplitBlocked("temple_building_identity")
    if historic_building.code != "TEMPLE-HISTORIC" or addition_building.code != "TEMPLE-ADDITION":
        raise ProjectSplitBlocked("temple_building_identity")
    agreements_before = _count_project(db, CrmAgreement, temple.id)
    finance_before = _count_project(db, FinanceTransaction, temple.id)
    funding_before = _count_project(db, FundingCommitment, temple.id)
    documents_before = _count_project(db, Document, temple.id)
    historic_units = list(
        db.scalars(select(InventoryAsset).where(InventoryAsset.building_id == historic_building.id)).all()
    )
    addition_units = list(
        db.scalars(select(InventoryAsset).where(InventoryAsset.building_id == addition_building.id)).all()
    )
    historic = _child_project(
        db,
        temple,
        code=TEMPLE_HISTORIC_CODE,
        name=TEMPLE_HISTORIC_NAME,
        address=historic_building.address,
    )
    addition = _child_project(
        db,
        temple,
        code=TEMPLE_ADDITION_CODE,
        name=TEMPLE_ADDITION_NAME,
        address=addition_building.address,
    )
    historic_building.project_id = historic.id
    addition_building.project_id = addition.id
    for asset in historic_units:
        asset.project_id = historic.id
        asset.phase_id = None
    for asset in addition_units:
        asset.project_id = addition.id
        asset.phase_id = None
    historic.total_units = len(historic_units)
    addition.total_units = len(addition_units)
    historic.uses_phases = False
    addition.uses_phases = False
    db.flush()
    _assert_project_links(db, historic_units, historic.id)
    _assert_project_links(db, addition_units, addition.id)
    if _count_project(db, CrmAgreement, temple.id) != agreements_before:
        raise ProjectSplitBlocked("temple_agreement_moved")
    if _count_project(db, FinanceTransaction, temple.id) != finance_before:
        raise ProjectSplitBlocked("temple_finance_moved")
    if _count_project(db, FundingCommitment, temple.id) != funding_before:
        raise ProjectSplitBlocked("temple_funding_moved")
    if _count_project(db, Document, temple.id) != documents_before:
        raise ProjectSplitBlocked("temple_document_moved")
    units_left = _count_project(db, InventoryAsset, temple.id)
    return TempleSplitReport(
        temple_id=temple.id,
        temple_historic_id=historic.id,
        temple_addition_id=addition.id,
        units_left=units_left,
        agreements_left=agreements_before,
        finance_left=finance_before,
        funding_left=funding_before,
        documents_left=documents_before,
    )
