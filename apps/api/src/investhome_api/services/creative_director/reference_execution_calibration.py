"""ReferenceExecutionCalibrationV1 — prove compositor craft on EDITORIAL_DARK_FIELD."""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw, ImageStat

from investhome_api.services.creative_director.creative_execution_tokens import execution_tokens
from investhome_api.services.creative_director.graphic_design_compositor_v3 import compose_graphic_design_v3
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.photo_occupancy_map import build_photo_occupancy_map

CALIBRATION_FACTS = {
    "headline": "DISPLAY LINE",
    "unit_type": "UNIT CONTEXT",
    "price": "1.250 USD",
    "discount": "%20",
    "discount_label": "ADVANTAGE NOTE",
    "cta": "LEARN MORE",
}


def synthetic_compatible_field() -> Image.Image:
    canvas = Image.new("RGB", CANVAS_4X5, (18, 22, 28))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 420, 460, 1360), fill=(164, 152, 136))
    draw.rectangle((70, 480, 200, 1240), fill=(148, 138, 124))
    draw.rectangle((210, 620, 330, 1180), fill=(158, 148, 132))
    return canvas


def score_calibration(pack: dict[str, Any], family: dict[str, Any], photo: Image.Image) -> dict[str, Any]:
    tokens = execution_tokens(family)
    objects = dict(pack.get("objects") or {})
    w, h = photo.size

    def px(role: str) -> tuple[int, int, int, int] | None:
        item = objects.get(role) or {}
        box = item.get("px")
        if isinstance(box, (list, tuple)) and len(box) == 4:
            return int(box[0]), int(box[1]), int(box[2]), int(box[3])
        return None

    headline = px("headline")
    price = px("price")
    unit = px("unit_type")
    discount = px("discount")
    cta = px("cta")
    logo = px("project_logo")
    align = str(tokens.get("alignment") or "right")
    alignment = 6.0
    if headline and price:
        edge_h = headline[2] if align == "right" else headline[0]
        edge_p = price[2] if align == "right" else price[0]
        drift = abs(edge_h - edge_p) / w
        alignment = 9.4 if drift < 0.02 else 8.2 if drift < 0.04 else 6.0
    display_h = ((headline[3] - headline[1]) / h) if headline else 0
    target = float(tokens.get("display_scale") or 0.07) * 1.7
    typography_ratio = 9.0 if abs(display_h - target) < 0.05 or display_h >= 0.08 else 8.0 if display_h >= 0.06 else 6.0
    spacing = 8.8
    if headline and unit and price and cta:
        g1 = unit[1] - headline[3]
        g2 = price[1] - unit[3]
        g3 = cta[1] - (discount[3] if discount else price[3])
        spacing = 9.1 if 4 <= g1 and g1 < g3 and g2 > 0 else 8.0 if g1 > 0 and g2 > 0 else 6.0
    field = 7.0
    if headline:
        crop = photo.convert("L").crop(headline)
        luma = float(ImageStat.Stat(crop).mean[0]) if crop.size[0] > 2 else 128
        field = 9.3 if luma < 80 else 8.2 if luma < 110 else 6.0
    grouping = 8.8 if price and discount and (discount[1] >= price[3] - 4) else 6.5
    hierarchy = 9.0
    if headline and price and unit:
        hierarchy = 9.2 if (headline[3] - headline[1]) > (price[3] - price[1]) > (unit[3] - unit[1]) * 0.6 else 8.0
    if logo is None and pack.get("solved"):
        hierarchy = min(hierarchy, 7.8)
    craft = round((alignment + typography_ratio + spacing + field + grouping + hierarchy) / 6.0, 1)
    scores = {
        "typography_ratio": round(typography_ratio, 1),
        "alignment": round(alignment, 1),
        "spacing_rhythm": round(spacing, 1),
        "graphic_field": round(field, 1),
        "commercial_grouping": round(grouping, 1),
        "visual_hierarchy": round(hierarchy, 1),
        "overall_craft": craft,
    }
    return {
        "schema": "ReferenceExecutionCalibrationV1",
        "scores": scores,
        "pass": all(v >= 8.0 for v in scores.values()) and bool(pack.get("solved")),
        "placeholder_facts": CALIBRATION_FACTS,
        "copied_source_content": False,
        "note": "Neutral placeholder content on a compatible dark-field test image. ORNEK pixels were not copied.",
    }


def run_reference_calibration(*, family: dict[str, Any], fonts: dict[str, Any], logo_rgba: Image.Image | None) -> dict[str, Any]:
    photo = synthetic_compatible_field()
    occupancy = build_photo_occupancy_map(photo)
    pack = compose_graphic_design_v3(
        photo,
        occupancy=occupancy,
        family=family,
        fonts=fonts,
        logo_rgba=logo_rgba,
        facts=CALIBRATION_FACTS,
    )
    report = score_calibration(pack, family, pack.get("fielded") or photo)
    report["fit"] = pack.get("fit")
    report["solved"] = pack.get("solved")
    report["pack"] = pack
    report["photo"] = photo
    return report
