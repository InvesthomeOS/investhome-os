"""Demo inventory seed data — Temple and UniLoft buildings, floors, assets."""

from decimal import Decimal

from sqlalchemy import select

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


def _get_project_id(session, project_code: str):
    return session.scalar(select(Project.id).where(Project.project_code == project_code))


def seed_demo_inventory() -> dict[str, int]:
    """Insert demo inventory when buildings table is empty. Returns counts."""
    with SessionLocal() as session:
        existing = session.scalar(select(Building.id).limit(1))
        if existing is not None:
            return {"buildings": 0, "floors": 0, "assets": 0}

        temple_id = _get_project_id(session, "PRJ-TEMP-001")
        uniloft_id = _get_project_id(session, "PRJ-UNIL-002")
        if temple_id is None or uniloft_id is None:
            return {"buildings": 0, "floors": 0, "assets": 0}

        temple_tower = Building(
            project_id=temple_id,
            name="Temple Tower A",
            code="A",
            building_type=BuildingType.MIXED_USE,
            address="1610 Columbia Rd NW",
            total_floors=12,
            status=StructureStatus.UNDER_CONSTRUCTION,
            description="Demo — primary residential tower at The Temple.",
            is_demo=True,
        )
        temple_retail = Building(
            project_id=temple_id,
            name="Temple Retail Podium",
            code="R",
            building_type=BuildingType.RETAIL,
            total_floors=2,
            status=StructureStatus.ACTIVE,
            description="Demo — ground-floor retail at The Temple.",
            is_demo=True,
        )
        uniloft_main = Building(
            project_id=uniloft_id,
            name="UniLoft Main",
            code="M",
            building_type=BuildingType.APARTMENT,
            address="300 I St NE",
            total_floors=6,
            status=StructureStatus.ACTIVE,
            description="Demo — renovated loft building at UniLoft.",
            is_demo=True,
        )
        session.add_all([temple_tower, temple_retail, uniloft_main])
        session.flush()

        temple_floor_3 = Floor(
            building_id=temple_tower.id,
            floor_number=3,
            display_name="Level 3",
            level_code="03",
            sort_order=3,
            status=StructureStatus.ACTIVE,
            is_demo=True,
        )
        temple_floor_12 = Floor(
            building_id=temple_tower.id,
            floor_number=12,
            display_name="Level 12",
            level_code="12",
            sort_order=12,
            status=StructureStatus.ACTIVE,
            is_demo=True,
        )
        uniloft_floor_2 = Floor(
            building_id=uniloft_main.id,
            floor_number=2,
            display_name="Loft Level 2",
            level_code="02",
            sort_order=2,
            status=StructureStatus.ACTIVE,
            is_demo=True,
        )
        session.add_all([temple_floor_3, temple_floor_12, uniloft_floor_2])
        session.flush()

        asset_specs = [
            {
                "project_id": temple_id,
                "building_id": temple_tower.id,
                "floor_id": temple_floor_3.id,
                "display_id": "301",
                "asset_type": InventoryAssetType.RESIDENTIAL_UNIT,
                "usage_type": UsageType.RESIDENTIAL,
                "unit_subtype": "2br_corner",
                "bedrooms": Decimal("2"),
                "bathrooms": Decimal("2"),
                "interior_area_sqft": Decimal("980.00"),
                "availability_status": AvailabilityStatus.AVAILABLE,
                "sales_status": InventorySalesStatus.AVAILABLE_FOR_SALE,
                "construction_status": ConstructionStatus.INTERIOR,
            },
            {
                "project_id": temple_id,
                "building_id": temple_tower.id,
                "floor_id": temple_floor_12.id,
                "display_id": "12A",
                "asset_type": InventoryAssetType.RESIDENTIAL_UNIT,
                "usage_type": UsageType.RESIDENTIAL,
                "unit_subtype": "3br_penthouse",
                "bedrooms": Decimal("3"),
                "bathrooms": Decimal("2.5"),
                "interior_area_sqft": Decimal("1450.00"),
                "availability_status": AvailabilityStatus.NOT_RELEASED,
                "construction_status": ConstructionStatus.FINISHING,
            },
            {
                "project_id": temple_id,
                "building_id": temple_retail.id,
                "floor_id": None,
                "display_id": "R-04",
                "asset_type": InventoryAssetType.RETAIL_UNIT,
                "usage_type": UsageType.RETAIL,
                "interior_area_sqft": Decimal("2200.00"),
                "availability_status": AvailabilityStatus.AVAILABLE,
                "sales_status": InventorySalesStatus.AVAILABLE_FOR_SALE,
                "construction_status": ConstructionStatus.READY,
            },
            {
                "project_id": temple_id,
                "building_id": None,
                "floor_id": None,
                "display_id": "P-142",
                "asset_type": InventoryAssetType.PARKING_SPACE,
                "usage_type": UsageType.PARKING,
                "interior_area_sqft": Decimal("180.00"),
                "availability_status": AvailabilityStatus.AVAILABLE,
                "sales_status": InventorySalesStatus.AVAILABLE_FOR_SALE,
            },
            {
                "project_id": temple_id,
                "building_id": None,
                "floor_id": None,
                "display_id": "S-22",
                "asset_type": InventoryAssetType.STORAGE_UNIT,
                "usage_type": UsageType.STORAGE,
                "interior_area_sqft": Decimal("45.00"),
                "availability_status": AvailabilityStatus.AVAILABLE,
            },
            {
                "project_id": uniloft_id,
                "building_id": uniloft_main.id,
                "floor_id": uniloft_floor_2.id,
                "display_id": "2B",
                "asset_type": InventoryAssetType.RESIDENTIAL_UNIT,
                "usage_type": UsageType.RESIDENTIAL,
                "unit_subtype": "loft_studio",
                "bedrooms": Decimal("1"),
                "bathrooms": Decimal("1"),
                "interior_area_sqft": Decimal("720.00"),
                "availability_status": AvailabilityStatus.AVAILABLE,
                "construction_status": ConstructionStatus.DELIVERED,
            },
        ]

        assets: list[InventoryAsset] = []
        for spec in asset_specs:
            system_code = generate_system_code(
                session,
                project_id=spec["project_id"],
                building_id=spec.get("building_id"),
                floor_id=spec.get("floor_id"),
                display_id=spec["display_id"],
            )
            assets.append(InventoryAsset(**spec, system_code=system_code, is_demo=True))

        session.add_all(assets)
        session.commit()

        return {"buildings": 3, "floors": 3, "assets": len(assets)}
