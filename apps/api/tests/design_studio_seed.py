"""Seed design studio catalog data for in-memory tests."""

from __future__ import annotations

from sqlalchemy.orm import Session

from investhome_api.models.design_studio import FurnitureItem, MaterialPackage, StylePreset

SYSTEM_STYLE_PRESETS = [
    ("modern", "Modern"),
    ("luxury", "Luxury"),
    ("scandinavian", "Scandinavian"),
    ("industrial", "Industrial"),
    ("minimalist", "Minimalist"),
]

SYSTEM_FURNITURE = [
    ("Sofa", "sofa", "sofa", 220, 95, 85),
    ("Bed", "bed", "bed", 160, 210, 110),
    ("Dining Table", "dining_table", "dining_table", 180, 90, 75),
    ("Chair", "chair", "dining_chair", 45, 50, 85),
    ("Coffee Table", "coffee_table", "coffee_table", 120, 60, 45),
    ("Toilet", "toilet", "toilet", 40, 65, 80),
    ("Shower", "shower", "shower", 90, 90, 200),
    ("Kitchen Island", "kitchen_island", "kitchen_island", 180, 90, 90),
]

SYSTEM_PACKAGES = [
    ("Urban Loft Package", "Polished Concrete"),
    ("Coastal Calm Package", "Light Oak"),
    ("Warm Modern Package", "Wide Plank Oak"),
]


def seed_design_studio_catalog(db: Session) -> None:
    if db.query(StylePreset).first() is None:
        for code, name in SYSTEM_STYLE_PRESETS:
            db.add(
                StylePreset(
                    name=name,
                    code=code,
                    description=f"{name} system preset",
                    color_palette={"primary": "#333333", "secondary": "#EEEEEE", "accent": "#999999"},
                    is_system_preset=True,
                )
            )

    if db.query(FurnitureItem).first() is None:
        for name, code, ftype, w, d, h in SYSTEM_FURNITURE:
            db.add(
                FurnitureItem(
                    name=name,
                    code=code,
                    furniture_type=ftype,
                    width=w,
                    depth=d,
                    height=h,
                    is_system_item=True,
                )
            )

    if db.query(MaterialPackage).first() is None:
        for name, flooring in SYSTEM_PACKAGES:
            db.add(MaterialPackage(name=name, flooring=flooring, wall_finish="Paint"))

    db.commit()
