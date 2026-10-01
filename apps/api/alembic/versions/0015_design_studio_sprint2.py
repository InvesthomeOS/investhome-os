"""Design Studio Sprint 2 ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â style presets, materials, furniture, review fields.

Revision ID: 0015_design_studio_sprint2
Revises: 0014_visual_design_studio
Create Date: 2026-07-15

"""

from collections.abc import Sequence
import uuid

import sqlalchemy as sa
from alembic import op

revision: str = "0015_design_studio_sprint2"
down_revision: str | None = "0014_visual_design_studio"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SYSTEM_STYLE_PRESETS = [
    {
        "code": "modern",
        "name": "Modern",
        "description": "Clean lines, neutral palette, minimal ornamentation.",
        "color_palette": {"primary": "#2C3E50", "secondary": "#ECF0F1", "accent": "#3498DB"},
        "material_preferences": {"flooring": "polished_concrete", "walls": "smooth_paint"},
        "furniture_preferences": {"style": "contemporary", "density": "moderate"},
    },
    {
        "code": "contemporary",
        "name": "Contemporary",
        "description": "Current trends with balanced warmth and contrast.",
        "color_palette": {"primary": "#34495E", "secondary": "#F8F9FA", "accent": "#E74C3C"},
        "material_preferences": {"flooring": "engineered_wood", "walls": "accent_wall"},
        "furniture_preferences": {"style": "mixed", "density": "moderate"},
    },
    {
        "code": "minimalist",
        "name": "Minimalist",
        "description": "Sparse furnishings, monochromatic palette, open space.",
        "color_palette": {"primary": "#FFFFFF", "secondary": "#F5F5F5", "accent": "#BDC3C7"},
        "material_preferences": {"flooring": "light_oak", "walls": "white_matte"},
        "furniture_preferences": {"style": "minimal", "density": "low"},
    },
    {
        "code": "mid_century_modern",
        "name": "Mid-Century Modern",
        "description": "Organic curves, warm woods, retro accent colors.",
        "color_palette": {"primary": "#D4A574", "secondary": "#F5E6D3", "accent": "#E67E22"},
        "material_preferences": {"flooring": "teak", "walls": "warm_white"},
        "furniture_preferences": {"style": "mid_century", "density": "moderate"},
    },
    {
        "code": "luxury",
        "name": "Luxury",
        "description": "Rich materials, layered textures, statement pieces.",
        "color_palette": {"primary": "#1A1A2E", "secondary": "#C9A962", "accent": "#8B7355"},
        "material_preferences": {"flooring": "marble", "walls": "venetian_plaster"},
        "furniture_preferences": {"style": "luxury", "density": "high"},
    },
    {
        "code": "industrial",
        "name": "Industrial",
        "description": "Exposed materials, metal accents, urban loft aesthetic.",
        "color_palette": {"primary": "#2C2C2C", "secondary": "#7F8C8D", "accent": "#E67E22"},
        "material_preferences": {"flooring": "concrete", "walls": "exposed_brick"},
        "furniture_preferences": {"style": "industrial", "density": "moderate"},
    },
    {
        "code": "scandinavian",
        "name": "Scandinavian",
        "description": "Light woods, hygge warmth, functional simplicity.",
        "color_palette": {"primary": "#FFFFFF", "secondary": "#E8D5B7", "accent": "#5DADE2"},
        "material_preferences": {"flooring": "light_pine", "walls": "soft_white"},
        "furniture_preferences": {"style": "scandinavian", "density": "low"},
    },
    {
        "code": "transitional",
        "name": "Transitional",
        "description": "Blend of traditional and contemporary elements.",
        "color_palette": {"primary": "#5D6D7E", "secondary": "#FDFEFE", "accent": "#85929E"},
        "material_preferences": {"flooring": "hardwood", "walls": "neutral_paint"},
        "furniture_preferences": {"style": "transitional", "density": "moderate"},
    },
    {
        "code": "warm_modern",
        "name": "Warm Modern",
        "description": "Modern forms with warm tones and natural textures.",
        "color_palette": {"primary": "#8B7355", "secondary": "#F5F0E8", "accent": "#C4A882"},
        "material_preferences": {"flooring": "warm_oak", "walls": "greige"},
        "furniture_preferences": {"style": "warm_modern", "density": "moderate"},
    },
    {
        "code": "custom",
        "name": "Custom",
        "description": "User-defined style starting point.",
        "color_palette": {"primary": "#CCCCCC", "secondary": "#EEEEEE", "accent": "#999999"},
        "material_preferences": {},
        "furniture_preferences": {},
    },
]


def upgrade() -> None:
    style_presets = sa.table(
        "style_presets",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("code", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("color_palette", sa.JSON()),
        sa.column("material_preferences", sa.JSON()),
        sa.column("furniture_preferences", sa.JSON()),
        sa.column("is_system_preset", sa.Boolean()),
    )
    op.bulk_insert(
        style_presets,
        [
            {
                "id": uuid.uuid4(),
                "name": preset["name"],
                "code": preset["code"],
                "description": preset["description"],
                "color_palette": preset["color_palette"],
                "material_preferences": preset["material_preferences"],
                "furniture_preferences": preset["furniture_preferences"],
                "is_system_preset": True,
            }
            for preset in SYSTEM_STYLE_PRESETS
        ],
    )


def downgrade() -> None:
    style_presets = sa.table(
        "style_presets",
        sa.column("code", sa.String()),
    )
    op.execute(
        style_presets.delete().where(
            style_presets.c.code.in_([preset["code"] for preset in SYSTEM_STYLE_PRESETS])
        )
    )
