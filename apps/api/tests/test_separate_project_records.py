"""Independent Campus and Temple project rows keep unit and price identity."""

from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementStatus
from investhome_api.models.finance import FinanceTransaction, TransactionType
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
from investhome_api.models.user_auth import User, UserStatus
from investhome_api.services.inventory.separate_project_records import (
    ADDITION_BUILDING_ID,
    BUILDING_3220_ID,
    BUILDING_3224_ID,
    CAMPUS_3220_NAME,
    CAMPUS_3224_CODE,
    CAMPUS_3224_NAME,
    CAMPUS_PROJECT_CODE,
    CAMPUS_PROJECT_ID,
    DEMO_CAMPUS_ID,
    HISTORIC_BUILDING_ID,
    PHASE_3220_ID,
    PHASE_3224_ID,
    TEMPLE_PROJECT_ID,
    separate_campus_records,
    separate_temple_records,
)
from investhome_api.services.inventory.validation_service import (
    InventoryConflictError,
    assert_unique_display_identity,
)
from investhome_api.services.project_detail_service import get_units


def _project(db: Session, **values) -> Project:
    fields = {
        "project_type": ProjectType.RESIDENTIAL,
        "development_type": DevelopmentType.GROUND_UP,
        "project_status": ProjectStatus.SALES,
        "currency": "USD",
        "uses_phases": False,
        "is_demo": False,
    }
    fields.update(values)
    row = Project(**fields)
    db.add(row)
    db.flush()
    return row


def _units(db: Session, project_id: UUID, building_id: UUID, phase_id: UUID, count: int, prefix: str) -> None:
    for index in range(count):
        db.add(
            InventoryAsset(
                project_id=project_id,
                building_id=building_id,
                phase_id=phase_id,
                display_id=f"{index + 1:03d}",
                system_code=f"{prefix}-{index + 1:03d}",
                asset_type=InventoryAssetType.RESIDENTIAL_UNIT,
                usage_type=UsageType.RESIDENTIAL,
                sales_status=InventorySalesStatus.AVAILABLE_FOR_SALE,
                currency="USD",
                is_demo=False,
            )
        )
    db.flush()


def test_splits_verified_rows_and_leaves_unscoped_temple_records(db: Session):
    campus = _project(
        db,
        id=CAMPUS_PROJECT_ID,
        project_code=CAMPUS_PROJECT_CODE,
        project_name="The Campus",
        address="3220 16th St NW",
        city="Washington",
        state="DC",
        total_units=64,
        uses_phases=True,
    )
    demo = _project(
        db,
        id=DEMO_CAMPUS_ID,
        project_code="PRJ-CAMP-004",
        project_name="The Campus",
        address="3220 & 3224 Minnesota Ave NE",
        total_units=156,
        is_demo=True,
    )
    temple = _project(
        db,
        id=TEMPLE_PROJECT_ID,
        project_code="PRJ-TEMP-001",
        project_name="The Temple",
        address="1610 Columbia Rd NW",
        city="Washington",
        state="DC",
    )
    phase_3224 = ProjectPhase(
        id=PHASE_3224_ID,
        project_id=campus.id,
        name="3224",
        display_order=2,
        active=True,
        address_line="3224 16th St NW",
    )
    phase_3220 = ProjectPhase(
        id=PHASE_3220_ID,
        project_id=campus.id,
        name="3220",
        display_order=1,
        active=True,
        address_line="3220 16th St NW",
    )
    building_3220 = Building(
        id=BUILDING_3220_ID,
        project_id=campus.id,
        name="3220 16th St NW",
        code="3220",
        building_type=BuildingType.CONDOMINIUM,
        status=StructureStatus.ACTIVE,
        is_demo=False,
    )
    building_3224 = Building(
        id=BUILDING_3224_ID,
        project_id=campus.id,
        name="3224 16th St NW",
        code="3224",
        building_type=BuildingType.CONDOMINIUM,
        address="3224 16th St NW",
        status=StructureStatus.PLANNED,
        is_demo=False,
    )
    historic = Building(
        id=HISTORIC_BUILDING_ID,
        project_id=temple.id,
        name="Historic",
        code="TEMPLE-HISTORIC",
        building_type=BuildingType.CONDOMINIUM,
        address="1610 Columbia Rd NW, Washington, DC 20009",
        status=StructureStatus.UNDER_CONSTRUCTION,
        is_demo=False,
    )
    addition = Building(
        id=ADDITION_BUILDING_ID,
        project_id=temple.id,
        name="Addition",
        code="TEMPLE-ADDITION",
        building_type=BuildingType.CONDOMINIUM,
        address="1610 Columbia Rd NW, Washington, DC 20009",
        status=StructureStatus.UNDER_CONSTRUCTION,
        is_demo=False,
    )
    tower = Building(
        project_id=temple.id,
        name="Temple Tower A",
        code="A",
        building_type=BuildingType.CONDOMINIUM,
        status=StructureStatus.UNDER_CONSTRUCTION,
        is_demo=False,
    )
    floor = Floor(
        building_id=building_3224.id,
        floor_number=1,
        display_name="1st",
        level_code="01",
        status=StructureStatus.ACTIVE,
        is_demo=False,
    )
    db.add_all([phase_3220, phase_3224, building_3220, building_3224, historic, addition, tower, floor])
    db.flush()
    _units(db, campus.id, building_3220.id, phase_3220.id, 43, "A")
    _units(db, campus.id, building_3224.id, phase_3224.id, 21, "B")
    linked = db.query(InventoryAsset).filter(InventoryAsset.phase_id == PHASE_3224_ID).first()
    assert linked is not None
    linked.floor_id = floor.id
    priced = db.query(InventoryAsset).filter(InventoryAsset.phase_id == PHASE_3224_ID).first()
    assert priced is not None
    price = InventoryAssetPrice(
        inventory_asset_id=priced.id,
        price_type=PriceType.LIST,
        amount=Decimal("530000.00"),
        currency="USD",
        effective_from=date(2026, 11, 11),
        status=PriceStatus.ACTIVE,
        source=PriceSource.IMPORT,
    )
    leftover = InventoryAsset(
        project_id=temple.id,
        building_id=tower.id,
        display_id="301",
        system_code="TEMPLE-301",
        asset_type=InventoryAssetType.RESIDENTIAL_UNIT,
        usage_type=UsageType.RESIDENTIAL,
        sales_status=InventorySalesStatus.AVAILABLE_FOR_SALE,
        currency="USD",
        is_demo=False,
    )
    agreement = CrmAgreement(
        contact_id=UUID("00000000-0000-0000-0000-000000000001"),
        project_id=temple.id,
        project_group="the_temple",
        source="bitrix",
        status=CrmAgreementStatus.ACTIVE,
        unit_number="103",
        metadata_json={"project_label": "The Temple Historic"},
    )
    finance = FinanceTransaction(
        transaction_date=date(2026, 1, 1),
        transaction_type=TransactionType.INCOME,
        amount=Decimal("100.00"),
        currency="USD",
        account_id=UUID("00000000-0000-0000-0000-000000000002"),
        project_id=temple.id,
        is_demo=False,
    )
    db.add_all([price, leftover, agreement, finance])
    db.add(
        User(
            full_name="Split Actor",
            email="split-projects@example.com",
            hashed_password="not-a-real-secret",
            status=UserStatus.ACTIVE,
        )
    )
    db.flush()
    price_id = price.id
    asset_id = priced.id

    report = separate_campus_records(db)

    assert report.campus_3220_id == CAMPUS_PROJECT_ID
    assert report.units_3220 == 43
    assert report.units_3224 == 21
    assert report.prices_3224 == 1
    assert report.uses_phases is False
    assert campus.project_code == CAMPUS_PROJECT_CODE
    assert campus.project_name == CAMPUS_3220_NAME
    assert campus.total_units == 43
    moved = db.get(Project, report.campus_3224_id)
    assert moved is not None
    assert moved.project_code == CAMPUS_3224_CODE
    assert moved.project_name == CAMPUS_3224_NAME
    assert moved.total_units == 21
    assert moved.uses_phases is False
    kept = db.get(InventoryAsset, asset_id)
    assert kept is not None
    assert kept.project_id == moved.id
    assert kept.phase_id is None
    assert kept.floor_id == floor.id
    assert db.get(Floor, floor.id).building_id == building_3224.id
    assert db.get(InventoryAssetPrice, price_id).inventory_asset_id == asset_id
    assert building_3224.project_id == moved.id
    assert building_3220.project_id == campus.id
    assert phase_3224.project_id == moved.id
    assert phase_3224.active is False
    assert phase_3220.project_id == campus.id
    assert phase_3220.active is False
    assert db.get(ProjectPhase, PHASE_3220_ID) is not None
    assert db.get(ProjectPhase, PHASE_3224_ID) is not None
    same_number = db.scalar(
        select(func.count())
        .select_from(InventoryAsset)
        .where(InventoryAsset.display_id == "001", InventoryAsset.project_id.in_([campus.id, moved.id]))
    )
    assert same_number == 2
    with pytest.raises(InventoryConflictError):
        assert_unique_display_identity(
            db,
            project_id=moved.id,
            building_id=building_3224.id,
            display_id="001",
            phase_id=None,
        )
    assert historic.project_id == temple.id
    assert addition.project_id == temple.id
    assert leftover.project_id == temple.id
    assert agreement.project_id == temple.id
    assert agreement.metadata_json["project_label"] == "The Temple Historic"
    assert finance.project_id == temple.id
    assert db.scalar(select(Project).where(Project.project_code == "TEMPLE-HISTORIC")) is None
    assert demo.project_code == "PRJ-CAMP-004"
    assert demo.total_units == 156
    assert demo.is_demo is True
    actor = db.scalar(select(User).where(User.email == "split-projects@example.com"))
    assert actor is not None
    stale = get_units(db, actor, moved.id, phase_id=PHASE_3224_ID, page_size=100)
    assert stale.total == 21
    original = get_units(db, actor, campus.id, phase_id=PHASE_3220_ID, page_size=100)
    assert original.total == 43


def test_temple_split_keeps_unscoped_records(db: Session):
    temple = _project(
        db,
        id=TEMPLE_PROJECT_ID,
        project_code="PRJ-TEMP-001",
        project_name="The Temple",
        address="1610 Columbia Rd NW",
    )
    historic = Building(
        id=HISTORIC_BUILDING_ID,
        project_id=temple.id,
        name="Historic",
        code="TEMPLE-HISTORIC",
        building_type=BuildingType.CONDOMINIUM,
        status=StructureStatus.UNDER_CONSTRUCTION,
        is_demo=False,
    )
    addition = Building(
        id=ADDITION_BUILDING_ID,
        project_id=temple.id,
        name="Addition",
        code="TEMPLE-ADDITION",
        building_type=BuildingType.CONDOMINIUM,
        status=StructureStatus.UNDER_CONSTRUCTION,
        is_demo=False,
    )
    tower = Building(
        project_id=temple.id,
        name="Temple Tower A",
        code="A",
        building_type=BuildingType.CONDOMINIUM,
        status=StructureStatus.UNDER_CONSTRUCTION,
        is_demo=False,
    )
    db.add_all([historic, addition, tower])
    db.flush()
    leftover = InventoryAsset(
        project_id=temple.id,
        building_id=tower.id,
        display_id="301",
        system_code="TEMPLE-301",
        asset_type=InventoryAssetType.RESIDENTIAL_UNIT,
        usage_type=UsageType.RESIDENTIAL,
        sales_status=InventorySalesStatus.AVAILABLE_FOR_SALE,
        currency="USD",
        is_demo=False,
    )
    agreement = CrmAgreement(
        contact_id=UUID("00000000-0000-0000-0000-000000000001"),
        project_id=temple.id,
        project_group="the_temple",
        source="bitrix",
        status=CrmAgreementStatus.ACTIVE,
        unit_number="103",
        metadata_json={"project_label": "The Temple Historic"},
    )
    db.add_all([leftover, agreement])
    db.flush()

    report = separate_temple_records(db)

    assert historic.project_id == report.temple_historic_id
    assert addition.project_id == report.temple_addition_id
    assert leftover.project_id == temple.id
    assert agreement.project_id == temple.id
    assert report.units_left == 1
    assert report.agreements_left == 1
    assert report.finance_left == 0
    assert report.documents_left == 0
    historic_project = db.get(Project, report.temple_historic_id)
    addition_project = db.get(Project, report.temple_addition_id)
    assert historic_project is not None and historic_project.total_units == 0
    assert addition_project is not None and addition_project.total_units == 0
    assert db.scalar(select(func.count()).select_from(InventoryAsset).where(InventoryAsset.project_id == historic_project.id)) == 0
    assert db.scalar(select(func.count()).select_from(CrmAgreement).where(CrmAgreement.project_id == historic_project.id)) == 0
