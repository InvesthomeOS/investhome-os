"""Demo seed data for Visual Design Studio Sprint 2."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select

from investhome_api.db.session import SessionLocal
from investhome_api.models.design_studio import (
    DesignProject,
    DesignStatus,
    DesignType,
    DesignVersion,
    FurnitureItem,
    FurnitureType,
    MaterialPackage,
    StylePreset,
)
from investhome_api.models.document import Document, DocumentStatus, DocumentType, StorageProvider
from investhome_api.models.drawing_intelligence import DrawingAnalysis, DrawingElement
from investhome_api.models.project import Project

DEMO_MATERIAL_PACKAGES = [
    {
        "name": "Urban Loft Package",
        "description": "Concrete floors, matte walls, brushed metal accents.",
        "flooring": "Polished Concrete",
        "wall_finish": "Matte White Paint",
        "ceiling_finish": "Flat White",
        "cabinetry": "Dark Walnut Veneer",
        "countertop": "Quartz — Cloud White",
        "backsplash": "Subway Tile — Gray",
        "bathroom_finish": "Large Format Porcelain",
        "metal_finish": "Brushed Nickel",
        "door_finish": "Matte Black",
        "color_palette": {"primary": "#2C2C2C", "secondary": "#F5F5F5", "accent": "#8B7355"},
    },
    {
        "name": "Coastal Calm Package",
        "description": "Light woods, soft blues, natural stone.",
        "flooring": "Light Oak Engineered",
        "wall_finish": "Soft Blue-Gray",
        "ceiling_finish": "Warm White",
        "cabinetry": "White Shaker",
        "countertop": "Carrara Marble Look",
        "backsplash": "Glass Mosaic — Seafoam",
        "bathroom_finish": "Matte Ceramic Tile",
        "metal_finish": "Polished Chrome",
        "door_finish": "White Painted",
        "color_palette": {"primary": "#A8C5DA", "secondary": "#FFFFFF", "accent": "#5DADE2"},
    },
    {
        "name": "Warm Modern Package",
        "description": "Greige palette with warm wood and brass accents.",
        "flooring": "Wide Plank Oak",
        "wall_finish": "Greige Paint",
        "ceiling_finish": "Off-White",
        "cabinetry": "Natural Oak",
        "countertop": "Butcher Block + Quartz",
        "backsplash": "Terracotta Zellige",
        "bathroom_finish": "Warm Travertine Look",
        "metal_finish": "Brushed Brass",
        "door_finish": "Natural Wood",
        "color_palette": {"primary": "#8B7355", "secondary": "#F5F0E8", "accent": "#C4A882"},
    },
]

DEMO_FURNITURE_ITEMS = [
    ("Modern Sofa", "sofa_lr_01", "living_room", FurnitureType.SOFA, 220, 95, 85),
    ("Accent Armchair", "armchair_lr_01", "living_room", FurnitureType.ARMCHAIR, 80, 85, 90),
    ("Coffee Table", "coffee_table_lr_01", "living_room", FurnitureType.COFFEE_TABLE, 120, 60, 45),
    ("Media Unit", "media_unit_lr_01", "living_room", FurnitureType.MEDIA_UNIT, 180, 45, 55),
    ("Area Rug", "rug_lr_01", "living_room", FurnitureType.RUG, 240, 160, 2),
    ("Dining Table", "dining_table_01", "dining_room", FurnitureType.DINING_TABLE, 180, 90, 75),
    ("Dining Chair", "dining_chair_01", "dining_room", FurnitureType.DINING_CHAIR, 45, 50, 85),
    ("Queen Bed", "bed_br_01", "bedroom", FurnitureType.BED, 160, 210, 110),
    ("Bedside Table", "bedside_br_01", "bedroom", FurnitureType.BEDSIDE_TABLE, 50, 40, 55),
    ("Wardrobe", "wardrobe_br_01", "bedroom", FurnitureType.WARDROBE, 200, 60, 220),
    ("Desk", "desk_office_01", "office", FurnitureType.DESK, 140, 70, 75),
    ("Kitchen Island", "island_kitchen_01", "kitchen", FurnitureType.KITCHEN_ISLAND, 180, 90, 90),
    ("Bar Stool", "stool_kitchen_01", "kitchen", FurnitureType.STOOL, 40, 40, 75),
    ("Vanity", "vanity_bath_01", "bathroom", FurnitureType.VANITY, 100, 50, 85),
    ("Bathtub", "bathtub_bath_01", "bathroom", FurnitureType.BATHTUB, 170, 80, 60),
    ("Shower", "shower_bath_01", "bathroom", FurnitureType.SHOWER, 90, 90, 200),
    ("Toilet", "toilet_bath_01", "bathroom", FurnitureType.TOILET, 40, 65, 80),
]


def seed_demo_design_studio_sprint2() -> dict[str, int]:
    """Seed material packages, furniture, and a furnished design project example."""
    counts = {"material_packages": 0, "furniture_items": 0, "design_projects": 0, "design_versions": 0}

    with SessionLocal() as session:
        existing_furniture = session.scalar(select(FurnitureItem.id).limit(1))
        if existing_furniture is not None:
            return counts

        for pkg_data in DEMO_MATERIAL_PACKAGES:
            session.add(MaterialPackage(**pkg_data))
            counts["material_packages"] += 1

        for name, code, room, ftype, w, d, h in DEMO_FURNITURE_ITEMS:
            session.add(
                FurnitureItem(
                    name=name,
                    code=code,
                    room_type=room,
                    furniture_type=ftype,
                    width=w,
                    depth=d,
                    height=h,
                    measurement_unit="cm",
                    is_system_item=True,
                    icon_or_preview=ftype.value,
                )
            )
            counts["furniture_items"] += 1

        session.flush()

        project = session.scalar(select(Project).where(Project.is_demo.is_(True)).limit(1))
        if project is None:
            session.commit()
            return counts

        document = session.scalar(
            select(Document).where(
                Document.project_id == project.id,
                Document.document_type == DocumentType.ARCHITECTURAL_DRAWING,
            ).limit(1)
        )
        if document is None:
            document = Document(
                title="Demo Floor Plan — Furnished Layout",
                original_file_name="demo-floor-plan.svg",
                stored_file_name="demo-floor-plan.svg",
                file_extension="svg",
                mime_type="image/svg+xml",
                file_size=2048,
                storage_provider=StorageProvider.LOCAL,
                storage_key=f"documents/{uuid4()}/demo-floor-plan.svg",
                checksum=uuid4().hex,
                document_type=DocumentType.ARCHITECTURAL_DRAWING,
                status=DocumentStatus.ACTIVE,
                project_id=project.id,
                is_demo=True,
            )
            session.add(document)
            session.flush()

        analysis = session.scalar(select(DrawingAnalysis).where(DrawingAnalysis.document_id == document.id))
        if analysis is None:
            analysis = DrawingAnalysis(
                document_id=document.id,
                document_version_id=document.id,
                processing_status="completed",
                preview_status="ready",
            )
            session.add(analysis)
            session.flush()
            for label in ("Living Room", "Kitchen", "Bedroom"):
                session.add(
                    DrawingElement(
                        analysis_id=analysis.id,
                        element_type="room",
                        label=label,
                        confidence="high",
                        geometry_json='{"type":"polygon"}',
                    )
                )

        modern_preset = session.scalar(select(StylePreset).where(StylePreset.code == "modern"))
        warm_package = session.scalar(
            select(MaterialPackage).where(MaterialPackage.name == "Warm Modern Package")
        )
        sofa = session.scalar(select(FurnitureItem).where(FurnitureItem.code == "sofa_lr_01"))
        coffee_table = session.scalar(select(FurnitureItem).where(FurnitureItem.code == "coffee_table_lr_01"))
        dining_table = session.scalar(select(FurnitureItem).where(FurnitureItem.code == "dining_table_01"))

        design_project = DesignProject(
            project_id=project.id,
            document_id=document.id,
            document_version_id=document.id,
            drawing_analysis_id=analysis.id if analysis else None,
            title="Furnished Floor Plan — Demo",
            description="Sprint 2 demo design with style, materials, and furniture layout.",
            design_type=DesignType.FURNITURE_LAYOUT,
            status=DesignStatus.DRAFT,
            source_geometry_version=str(document.id),
        )
        session.add(design_project)
        session.flush()
        counts["design_projects"] += 1

        base_params_v1 = {
            "mode": "room_regions",
            "palette": "default",
            "regions": [
                {"id": "living", "label": "Living Room", "color": "#E8D5B7"},
                {"id": "kitchen", "label": "Kitchen", "color": "#A8C5DA"},
            ],
            "backgroundColor": "#FFFFFF",
            "selected_style_preset_id": str(modern_preset.id) if modern_preset else None,
            "selected_material_package_id": str(warm_package.id) if warm_package else None,
            "color_overlays": [],
            "furniture_items": [str(sofa.id), str(coffee_table.id)] if sofa and coffee_table else [],
            "furniture_positions": {
                str(sofa.id): {"x": 120, "y": 180} if sofa else {},
                str(coffee_table.id): {"x": 200, "y": 220} if coffee_table else {},
            },
            "furniture_rotations": {
                str(sofa.id): 0 if sofa else 0,
                str(coffee_table.id): 0 if coffee_table else 0,
            },
            "furniture_dimensions": {},
            "editor_metadata": {"layout_mode": "free_layout"},
        }

        session.add(
            DesignVersion(
                design_project_id=design_project.id,
                version_number=1,
                design_parameters=base_params_v1,
            )
        )
        counts["design_versions"] += 1

        base_params_v2 = dict(base_params_v1)
        if dining_table:
            base_params_v2["furniture_items"] = list(base_params_v1["furniture_items"]) + [str(dining_table.id)]
            base_params_v2["furniture_positions"] = {
                **base_params_v1["furniture_positions"],
                str(dining_table.id): {"x": 350, "y": 150},
            }
            base_params_v2["furniture_rotations"] = {
                **base_params_v1["furniture_rotations"],
                str(dining_table.id): 90,
            }

        session.add(
            DesignVersion(
                design_project_id=design_project.id,
                version_number=2,
                design_parameters=base_params_v2,
            )
        )
        counts["design_versions"] += 1

        session.commit()

    return counts
