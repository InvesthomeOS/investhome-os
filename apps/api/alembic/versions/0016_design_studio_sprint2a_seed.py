"""Design Studio Sprint 2A — seed furniture catalog and material packages.

Revision ID: 0016_design_studio_sprint2a_seed
Revises: 0015_design_studio_sprint2
Create Date: 2026-07-15

"""

from collections.abc import Sequence
import uuid

import sqlalchemy as sa
from alembic import op

revision: str = "0016_design_studio_sprint2a_seed"
down_revision: str | None = "0015_design_studio_sprint2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SYSTEM_FURNITURE_ITEMS = [
    ("Sofa", "sofa", "living_room", "sofa", 220, 95, 85),
    ("Bed", "bed", "bedroom", "bed", 160, 210, 110),
    ("Dining Table", "dining_table", "dining_room", "dining_table", 180, 90, 75),
    ("Chair", "chair", "dining_room", "dining_chair", 45, 50, 85),
    ("Coffee Table", "coffee_table", "living_room", "coffee_table", 120, 60, 45),
    ("Toilet", "toilet", "bathroom", "toilet", 40, 65, 80),
    ("Shower", "shower", "bathroom", "shower", 90, 90, 200),
    ("Kitchen Island", "kitchen_island", "kitchen", "kitchen_island", 180, 90, 90),
]

SYSTEM_MATERIAL_PACKAGES = [
    {
        "name": "Urban Loft Package",
        "description": "Concrete floors, matte walls, brushed metal accents.",
        "flooring": "Polished Concrete",
        "wall_finish": "Matte White Paint",
        "cabinetry": "Dark Walnut Veneer",
        "countertop": "Quartz — Cloud White",
        "metal_finish": "Brushed Nickel",
        "color_palette": {"primary": "#2C2C2C", "secondary": "#F5F5F5", "accent": "#8B7355"},
    },
    {
        "name": "Coastal Calm Package",
        "description": "Light woods, soft blues, natural stone.",
        "flooring": "Light Oak Engineered",
        "wall_finish": "Soft Blue-Gray",
        "cabinetry": "White Shaker",
        "countertop": "Carrara Marble Look",
        "metal_finish": "Polished Chrome",
        "color_palette": {"primary": "#A8C5DA", "secondary": "#FFFFFF", "accent": "#5DADE2"},
    },
    {
        "name": "Warm Modern Package",
        "description": "Greige palette with warm wood and brass accents.",
        "flooring": "Wide Plank Oak",
        "wall_finish": "Greige Paint",
        "cabinetry": "Natural Oak",
        "countertop": "Butcher Block + Quartz",
        "metal_finish": "Brushed Brass",
        "color_palette": {"primary": "#8B7355", "secondary": "#F5F0E8", "accent": "#C4A882"},
    },
]


def upgrade() -> None:
    conn = op.get_bind()
    furniture_count = conn.execute(sa.text("SELECT COUNT(*) FROM furniture_items")).scalar()
    if furniture_count == 0:
        furniture_items = sa.table(
            "furniture_items",
            sa.column("id", sa.Uuid()),
            sa.column("name", sa.String()),
            sa.column("code", sa.String()),
            sa.column("room_type", sa.String()),
            sa.column("furniture_type", sa.String()),
            sa.column("width", sa.Float()),
            sa.column("depth", sa.Float()),
            sa.column("height", sa.Float()),
            sa.column("measurement_unit", sa.String()),
            sa.column("default_rotation", sa.Float()),
            sa.column("icon_or_preview", sa.String()),
            sa.column("is_system_item", sa.Boolean()),
        )
        op.bulk_insert(
            furniture_items,
            [
                {
                    "id": uuid.uuid4(),
                    "name": name,
                    "code": code,
                    "room_type": room,
                    "furniture_type": ftype,
                    "width": width,
                    "depth": depth,
                    "height": height,
                    "measurement_unit": "cm",
                    "default_rotation": 0,
                    "icon_or_preview": ftype,
                    "is_system_item": True,
                }
                for name, code, room, ftype, width, depth, height in SYSTEM_FURNITURE_ITEMS
            ],
        )

    package_count = conn.execute(sa.text("SELECT COUNT(*) FROM material_packages")).scalar()
    if package_count == 0:
        material_packages = sa.table(
            "material_packages",
            sa.column("id", sa.Uuid()),
            sa.column("name", sa.String()),
            sa.column("description", sa.Text()),
            sa.column("flooring", sa.String()),
            sa.column("wall_finish", sa.String()),
            sa.column("cabinetry", sa.String()),
            sa.column("countertop", sa.String()),
            sa.column("metal_finish", sa.String()),
            sa.column("color_palette", sa.JSON()),
        )
        op.bulk_insert(
            material_packages,
            [{"id": uuid.uuid4(), **pkg} for pkg in SYSTEM_MATERIAL_PACKAGES],
        )


def downgrade() -> None:
    conn = op.get_bind()
    codes = [code for _, code, _, _, _, _, _ in SYSTEM_FURNITURE_ITEMS]
    conn.execute(
        sa.text("DELETE FROM furniture_items WHERE code IN :codes").bindparams(
            sa.bindparam("codes", expanding=True)
        ),
        {"codes": codes},
    )
    names = [pkg["name"] for pkg in SYSTEM_MATERIAL_PACKAGES]
    conn.execute(
        sa.text("DELETE FROM material_packages WHERE name IN :names").bindparams(
            sa.bindparam("names", expanding=True)
        ),
        {"names": names},
    )
