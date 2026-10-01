"""Phase 6.2 — Concept 3 design language recomposed around real Day_007.

Not a reconstruction of Concept 3. Not a V4 layout-mode template.
GPT Image is never called from this module.
"""

from __future__ import annotations

import math
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from investhome_api.services.creative_director.ai_visual_art_director import _img, _num, _text
from investhome_api.services.creative_director.brand_cta_engines import compose_editorial_cta, integrate_brand
from investhome_api.services.creative_director.commercial_number_renderer import render_percent, render_price
from investhome_api.services.creative_director.commercial_offer_composer import measure_tracked, offer_layout_v2
from investhome_api.services.creative_director.creative_font_registry import font_for_role
from investhome_api.services.creative_director.creative_relationship_system import (
    compositional_gravity,
    concept3_relationship_graph,
    groups_from_objects,
    reading_flow,
)
from investhome_api.services.creative_director.full_frame_architectural_family import _paste_fitted_logo
from investhome_api.services.creative_director.graphic_field_engine import (
    apply_structured_field_specs,
    field_spec,
    render_vector_fields,
)
from investhome_api.services.creative_director.phase5_design_scene import _vision
from investhome_api.services.creative_director.phase5_photo_foundation import apply_photographic_grade
from investhome_api.services.creative_director.phase5_premium_commercial_r1 import LOCKED_GRADE
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_concept3_compose import CANVAS_4X5, DAY007_ASSET_ID, DAY007_FILENAME
from investhome_api.services.creative_director.phase6_1_r1_compose import cover_zoom_crop
from investhome_api.services.creative_director.photo_occupancy_map import (
    LAYER_COLORS,
    build_photo_occupancy_map,
    occupancy_to_json,
)
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY, _draw_tracked, _norm_box, _objects
from investhome_api.services.creative_director.typographic_composition_engine import compose_campaign_type
from investhome_api.services.gpt_image_design.compose import _fit_logo
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

APPROVED_BOTTOM_COPY = "TARİHİN RUHU, GELECEĞİN DEĞERİ."
BRAND_CAPTION = "THE TEMPLE"
NATIVE_MODE = "DAY007_NATIVE_APERTURE"

SKETCH_KEYS = (
    "DESIGN_LANGUAGE_FIDELITY",
    "REAL_PHOTO_INTEGRATION",
    "ART_DIRECTION",
    "COMPOSITION",
    "TYPOGRAPHIC_AUTHORITY",
    "COMMERCIAL_STORYTELLING",
    "BRAND_RELATIONSHIP",
    "GRAPHIC_DEPTH",
    "NEGATIVE_SPACE",
    "WHOLE_CANVAS_CHARACTER",
    "PREMIUM_CHARACTER",
)

FINAL_KEYS = (
    "campaign_family_fidelity",
    "agency_campaign_feel",
    "art_direction",
    "composition",
    "real_photo_integration",
    "typographic_authority",
    "commercial_storytelling",
    "brand_integration",
    "graphic_depth",
    "negative_space",
    "whole_canvas_character",
    "premium_character",
    "readability",
    "architecture_fidelity",
    "publishability",
)

FINAL_FLOORS = {
    "campaign_family_fidelity": 9,
    "agency_campaign_feel": 8,
    "art_direction": 8,
    "composition": 8,
    "real_photo_integration": 9,
    "typographic_authority": 8,
    "commercial_storytelling": 8,
    "brand_integration": 8,
    "graphic_depth": 8,
    "negative_space": 8,
    "whole_canvas_character": 8,
    "premium_character": 8,
    "readability": 8,
    "architecture_fidelity": 9,
    "publishability": 8,
}

NATIVE_CROP_CANDIDATES = (
    ("N01", 1.00, 0.62, 0.22),
    ("N02", 1.06, 0.64, 0.16),
    ("N03", 1.08, 0.68, 0.18),
    ("N04", 1.10, 0.66, 0.14),
    ("N05", 1.12, 0.72, 0.20),
    ("N06", 1.04, 0.58, 0.24),
)


def _smooth(values: list[float], span: int = 9) -> list[float]:
    if not values:
        return values
    out = list(values)
    radius = max(1, span // 2)
    for _ in range(3):
        nxt = out[:]
        n = len(out)
        for i in range(n):
            sl = out[max(0, i - radius) : min(n, i + radius + 1)]
            nxt[i] = sum(sl) / len(sl)
        out = nxt
    return out


def detect_spire_geometry(hard: Image.Image) -> dict[str, float]:
    small = hard.convert("L").resize((40, 50), Image.Resampling.BOX)
    px = small.load()
    best_x, best = 0.62, -1.0
    for x in range(16, 38):
        energy = sum(1.0 for y in range(2, 34) if int(px[x, y]) > 72)
        if energy > best:
            best, best_x = energy, x / 39.0
    top = 0.18
    cx = min(39, max(0, int(round(best_x * 39))))
    for y in range(1, 28):
        if int(px[cx, y]) > 72:
            top = y / 49.0
            break
    return {"spire_axis": round(best_x, 4), "spire_top": round(top, 4)}


def _region(box: dict[str, Any] | None) -> dict[str, float] | None:
    if not isinstance(box, dict):
        return None
    return {k: round(float(box[k]), 4) for k in ("x", "y", "w", "h") if k in box}


def score_native_crop(occupancy: dict[str, Any], spire: dict[str, float]) -> float:
    cov = occupancy.get("coverage") or {}
    axis = float(spire.get("spire_axis") or occupancy.get("architecture_centroid_x") or 0.6)
    top = float(spire.get("spire_top") or 0.2)
    sky_left = float(cov.get("sky_left") or 0)
    hard = float(cov.get("hard_protected") or 0)
    text = float(cov.get("text_safe") or 0)
    axis_ok = 1.0 - min(1.0, abs(axis - 0.64) * 2.4)
    top_ok = 1.0 if 0.04 <= top <= 0.28 else 0.55
    left_room = min(1.0, sky_left * 6.0 + text * 3.0)
    building = min(1.0, hard * 3.2)
    return 0.32 * axis_ok + 0.18 * top_ok + 0.28 * left_room + 0.22 * building


def choose_native_day007_crop(source: Image.Image) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None
    for cid, zoom, cx, cy in NATIVE_CROP_CANDIDATES:
        crop, transform = cover_zoom_crop(source, zoom=zoom, cx=cx, cy=cy)
        graded = apply_photographic_grade(crop, dict(LOCKED_GRADE))
        occupancy = build_photo_occupancy_map(graded)
        hard = (occupancy.get("layers") or {}).get("hard_protected")
        spire = detect_spire_geometry(hard if isinstance(hard, Image.Image) else graded.convert("L"))
        score = score_native_crop(occupancy, spire)
        item = {
            "id": cid,
            "zoom": zoom,
            "centering": [cx, cy],
            "transform": transform,
            "score": round(score, 4),
            "spire": spire,
            "crop": graded,
            "occupancy": occupancy,
        }
        rows.append(item)
        if best is None or score > best["score"]:
            best = item
    assert best is not None
    return {
        "candidates": [{k: v for k, v in row.items() if k not in {"crop", "occupancy"}} for row in rows],
        "selected": {k: v for k, v in best.items() if k not in {"crop", "occupancy"}},
        "selected_image": best["crop"],
        "selected_occupancy": best["occupancy"],
        "selected_id": best["id"],
        "source_asset_id": DAY007_ASSET_ID,
        "filename": DAY007_FILENAME,
        "generated_architecture": False,
        "uniform_scale": True,
    }


def build_real_photo_composition_map(photo: Image.Image, occupancy: dict[str, Any] | None = None) -> dict[str, Any]:
    src = photo.convert("RGB").resize(CANVAS_4X5, Image.Resampling.LANCZOS)
    occ = occupancy or build_photo_occupancy_map(src)
    layers = occ.get("layers") or {}
    hard = layers.get("hard_protected")
    if not isinstance(hard, Image.Image):
        hard = Image.new("L", src.size, 0)
    spire = detect_spire_geometry(hard)
    regions = occ.get("regions") or {}
    pockets = occ.get("pockets") or {}
    axis = float(spire["spire_axis"])
    field_limit = max(0.26, min(0.46, axis - 0.16))
    map_v1 = {
        "schema": "RealPhotoCompositionMapV1",
        "source": {"filename": DAY007_FILENAME, "asset_id": DAY007_ASSET_ID, "canvas": list(CANVAS_4X5)},
        "spire_axis": spire["spire_axis"],
        "spire_top": spire["spire_top"],
        "building_silhouette": _region(regions.get("hard_protected")),
        "primary_architecture_mass": _region(regions.get("hard_protected")),
        "secondary_architecture_mass": _region(regions.get("soft_occupied")),
        "sky_pockets": {
            "left": _region(pockets.get("left") or regions.get("sky_left")),
            "right": _region(pockets.get("right") or regions.get("sky_right")),
        },
        "quiet_photographic_regions": _region(regions.get("preferred_negative_space")),
        "high_detail_regions": _region(regions.get("hard_protected")),
        "street_ground_region": _region(regions.get("soft_occupied")),
        "natural_visual_vectors": {
            "vertical_spire": {"x": axis, "y0": float(spire["spire_top"]), "y1": 0.82},
            "left_sky_ingress": {"x0": 0.0, "x1": field_limit, "y0": 0.0, "y1": 0.42},
            "ground_horizon": {"y": 0.78},
        },
        "safe_typography_regions": {
            "left_column": _region(regions.get("text_left") or regions.get("text_safe") or {"x": 0.04, "y": 0.08, "w": field_limit, "h": 0.62}),
            "commercial": _region(regions.get("commercial_safe")),
        },
        "dark_field_interaction_regions": {
            "left_of_spire": {"x0": 0.0, "x1": field_limit, "y0": 0.0, "y1": 1.0, "note": "must remain curved aperture, never rectangular sidebar"},
            "extendable": _region(regions.get("graphically_extendable")),
        },
        "possible_arc_trajectories": {
            "A_spire_edge": "along the left silhouette, from upper sky down the aperture edge",
            "B_sky_crown": "high left-sky sweep that answers the spire crown",
            "C_ground_rise": "low-left rise that climbs toward the spire",
        },
        "natural_reading_flow": ["left editorial column", "spire as visual axis", "bottom canvas closure"],
        "architecture_centroid_x": occ.get("architecture_centroid_x"),
        "coverage": occ.get("coverage"),
        "sky_area": occ.get("sky_area"),
        "invented_landmarks": False,
        "occupancy": occupancy_to_json(occ),
    }
    return map_v1


def render_composition_map(photo: Image.Image, mapped: dict[str, Any], occupancy: dict[str, Any]) -> Image.Image:
    src = photo.convert("RGB").resize((640, 800), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (1680, 980), (12, 14, 20))
    overlay = src.convert("RGBA")
    layers = occupancy.get("layers") or {}
    for name, alpha in (("soft_occupied", 56), ("preferred_negative_space", 64), ("text_safe", 72), ("hard_protected", 86)):
        mask = layers.get(name)
        if not isinstance(mask, Image.Image):
            continue
        tint = Image.new("RGBA", src.size, (*LAYER_COLORS.get(name, (180, 180, 180)), alpha))
        m = mask.convert("L").resize(src.size, Image.Resampling.BILINEAR)
        overlay = Image.composite(Image.alpha_composite(overlay, tint), overlay, m)
    canvas.paste(overlay.convert("RGB"), (36, 56))
    draw = ImageDraw.Draw(canvas)
    w, h = src.size
    axis = float(mapped.get("spire_axis") or 0.62)
    top = float(mapped.get("spire_top") or 0.16)
    x = 36 + int(w * axis)
    draw.line((x, 56 + int(h * top), x, 56 + int(h * 0.82)), fill=(201, 168, 92), width=3)
    draw.ellipse((x - 6, 56 + int(h * top) - 6, x + 6, 56 + int(h * top) + 6), outline=(244, 239, 228), width=2)
    draw.text((36, 16), "03  REAL PHOTO COMPOSITION MAP  —  Day_007 geometry is authoritative", fill=(201, 168, 92))
    y = 56
    notes = [
        f"spire axis {axis:.3f}",
        f"spire top {top:.3f}",
        f"centroid {mapped.get('architecture_centroid_x')}",
        f"sky area {mapped.get('sky_area')}",
        "HARD = real Temple silhouette",
        "NO Capitol / Monument / invented skyline",
        "left of spire = aperture candidate",
        "right of spire = photographic axis",
        "street / ground stays photographic",
        "type lives in left quiet / sky pocket",
    ]
    for line in notes:
        draw.text((720, y), line, fill=(226, 222, 214))
        y += 28
    y += 12
    for name, color in LAYER_COLORS.items():
        draw.rectangle((720, y, 748, y + 16), fill=color)
        draw.text((760, y), name.replace("_", " "), fill=(200, 196, 188))
        y += 24
    return canvas


def _polyline(kind: str, spire_x: float, n: int = 48) -> list[float]:
    cap = max(0.24, min(0.48, spire_x - 0.14))
    xs: list[float] = []
    for i in range(n):
        t = i / max(n - 1, 1)
        if kind == "A":
            pinch = math.sin(t * math.pi)
            x = 0.40 - 0.12 * pinch + 0.08 * (1.0 - t) ** 1.35
        elif kind == "B":
            x = 0.50 * (1.0 - t) ** 0.72 + 0.18 * t
        else:
            x = 0.18 + 0.30 * (t ** 0.82)
        xs.append(max(0.18, min(cap, x)))
    return _smooth(xs)


def _arc_polyline(kind: str, field: list[float], spire_x: float) -> list[float]:
    if kind == "B":
        xs = []
        n = len(field)
        for i, x in enumerate(field):
            t = i / max(n - 1, 1)
            lift = 0.10 * math.sin(t * math.pi * 0.85)
            xs.append(min(spire_x - 0.08, x * 0.92 + lift))
        return _smooth(xs)
    if kind == "C":
        return _smooth([min(spire_x - 0.10, x * 0.88 + 0.04) for x in field])
    return _smooth([min(spire_x - 0.12, x * 0.94) for x in field])


def native_field_specs(kind: str, mapped: dict[str, Any], *, production: bool) -> list[dict[str, Any]]:
    spire_x = float(mapped.get("spire_axis") or 0.62)
    field = _polyline(kind, spire_x)
    arc = _arc_polyline(kind, field, spire_x)
    core = [max(0.0, v * (0.58 if production else 0.52)) for v in field]
    marker_y = 0.34 if kind == "A" else (0.22 if kind == "B" else 0.58)
    marker_x = arc[int((len(arc) - 1) * marker_y)]
    strength = 0.94 if production else 0.86
    return [
        field_spec("curved_aperture", role="charcoal_editorial_aperture", polyline_x=field, strength=strength, feather=0.07, blur=10, bleed=0.06),
        field_spec("feathered_tonal_field", role="left_core_density", polyline_x=core, strength=0.24 if production else 0.16, feather=0.06, blur=16, bleed=0.0),
        field_spec("masked_photo_overlay", role="photographic_depth", polyline_x=field, strength=0.18, feather=0.10, blur=18, bleed=0.04),
        field_spec("tonal_transition", role="aperture_feather", polyline_x=[min(1.0, v + 0.06) for v in field], strength=0.10, feather=0.12, blur=22, bleed=0.08),
        field_spec("curved_rule", role="dominant_gold_gesture", polyline_x=arc, stroke=3 if production else 2),
        field_spec("radial_tick_sequence", role="measurement_ticks", polyline_x=arc, ticks=13 if production else 9, tick_length=0.016),
        field_spec("precision_marker", role="architecture_node", x=marker_x, y=marker_y, r=0.0055),
    ]


def sketch_layout(kind: str, mapped: dict[str, Any], *, production: bool) -> dict[str, Any]:
    spire_x = float(mapped.get("spire_axis") or 0.62)
    origins = {"A": (0.055, 0.125), "B": (0.058, 0.048), "C": (0.055, 0.275)}
    ox, oy = origins[kind]
    if production:
        oy = max(0.04, oy - 0.012)
    names = {
        "A": "SPIRE_EDGE_APERTURE",
        "B": "HIGH_SKY_APERTURE",
        "C": "GROUND_RISE_APERTURE",
    }
    gravities = {
        "A": "left editorial mass against the real spire as vertical axis",
        "B": "upper-left sky aperture answering the spire crown",
        "C": "lower-left rise climbing toward the architectural axis",
    }
    return {
        "schema": "CreativeDirectionTransferPlanV1",
        "sketch_id": kind,
        "composition_name": names[kind],
        "reconstruction_mode": NATIVE_MODE,
        "classified_as": None,
        "dark_field_shape": "curved charcoal aperture custom-fit to Day_007, not a rectangular sidebar",
        "dark_field_depth": "decisive left mass with photographic feather toward the real building",
        "arc_trajectory": mapped["possible_arc_trajectories"][{"A": "A_spire_edge", "B": "B_sky_crown", "C": "C_ground_rise"}[kind]],
        "brand_position": "opens the editorial column inside the aperture",
        "headline_position": "campaign-scale ALIRKEN / KAZAN stacked in the aperture",
        "offer_position": "vertical commercial story under the headline",
        "cta_position": "editorial close of the same column",
        "bottom_closure": APPROVED_BOTTOM_COPY,
        "negative_space_role": "real photograph and spire keep the right canvas; field must not swallow architecture",
        "reading_flow": ["brand", "headline", "advantage", "price", "unit", "cta", "architecture", "bottom editorial"],
        "visual_center_of_gravity": gravities[kind],
        "origin": {"x": ox, "y": oy},
        "spire_axis": spire_x,
        "type_scale": 1.08 if production else 0.90,
        "production": production,
        "template_mode": None,
    }


def build_transfer_plan(mapped: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "CreativeDirectionTransferPlanV1",
        "approved_direction": "Phase 6.0 Concept 3 design language",
        "reality_source": {"filename": DAY007_FILENAME, "asset_id": DAY007_ASSET_ID},
        "objective": "Preserve Concept 3 campaign family. Recompose natively around real Day_007 geometry.",
        "do_not": [
            "inherit Concept 3 x/y",
            "recreate invented skyline / Capitol / Monument",
            "pixel-match Concept 3",
            "use SKY_VEIL / GROUND_PLANE / CORNER_INGRESS / sidebar templates",
        ],
        "language_to_keep": [
            "charcoal editorial aperture",
            "one dominant curved gold gesture",
            "architecture as visual axis",
            "campaign-scale ALIRKEN KAZAN",
            "vertical commercial story",
            "ivory / gold / charcoal",
            "real Temple logo",
            "bottom editorial closure",
            "whole-canvas art direction",
        ],
        "geometry_from_photo": {
            "spire_axis": mapped.get("spire_axis"),
            "spire_top": mapped.get("spire_top"),
            "field_must_stop_before": round(float(mapped.get("spire_axis") or 0.62) - 0.12, 4),
        },
        "sketches": {k: sketch_layout(k, mapped, production=False) for k in ("A", "B", "C")},
    }


def render_transfer_plan(concept: Image.Image, photo: Image.Image, plan: dict[str, Any]) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1100), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 16), "04  CREATIVE DIRECTION TRANSFER PLAN  —  language stays, geometry is Day_007", fill=(201, 168, 92))
    for i, (image, cap) in enumerate(((concept, "CONCEPT 3 LANGUAGE"), (photo, "REAL DAY_007 GEOMETRY"))):
        tile = image.copy()
        tile.thumbnail((520, 650), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (36 + i * 560, 56))
        draw.text((36 + i * 560, 720), cap, fill=(226, 222, 214))
    y = 56
    lines = [
        "Charcoal aperture -> left of the REAL spire",
        "Gold gesture -> one curve answering Day_007",
        "Architecture axis -> Temple spire, not invented skyline",
        "Type column -> inside the aperture, campaign scale",
        "%35 and price remain major commercial masses",
        "Logo opens the column, not leftover space",
        "Bottom: TARIHIN RUHU, GELECEGIN DEGERI.",
        "No sidebar. No V4 template mode.",
        f"spire axis {plan.get('geometry_from_photo', {}).get('spire_axis')}",
    ]
    for line in lines:
        draw.text((1160, y), line, fill=(226, 222, 214))
        y += 36
    return canvas


def compose_day007_native(
    photo: Image.Image,
    *,
    mapped: dict[str, Any],
    sketch_id: str,
    fonts: dict[str, Any],
    logo_rgba: Image.Image,
    occupancy: dict[str, Any] | None = None,
    production: bool = False,
) -> dict[str, Any]:
    w, h = CANVAS_4X5
    photo = photo.convert("RGB").resize((w, h), Image.Resampling.LANCZOS)
    layout = sketch_layout(sketch_id, mapped, production=production)
    fields = native_field_specs(sketch_id, mapped, production=production)
    applied = apply_structured_field_specs(
        photo,
        occupancy,
        fields,
        charcoal=(16, 18, 22),
        darken=0.22 if production else 0.30,
        charcoal_mix=0.70 if production else 0.58,
        protect_architecture=True,
    )
    fielded = applied["image"]
    vectors = render_vector_fields((w, h), fields)
    clip = applied["mask"].convert("L").filter(ImageFilter.MaxFilter(17))
    r_ch, g_ch, b_ch, a_ch = vectors.split()
    vectors.putalpha(ImageChops.multiply(a_ch, clip))
    canvas = fielded.convert("RGBA")
    canvas.alpha_composite(vectors)
    draw = ImageDraw.Draw(canvas)

    scale = float(layout["type_scale"])
    ox = int(w * float(layout["origin"]["x"]))
    oy = int(h * float(layout["origin"]["y"]))
    display = font_for_role(fonts, "DISPLAY_SERIF", max(46, int(h * 0.056 * scale)))
    display_sm = font_for_role(fonts, "DISPLAY_SERIF", max(42, int(h * 0.052 * scale)))
    discount_font = font_for_role(fonts, "DISPLAY_SERIF", max(52, int(h * 0.074 * scale)))
    label_font = font_for_role(fonts, "EDITORIAL_SANS", max(14, int(h * 0.017 * scale)))
    price_font = font_for_role(fonts, "DISPLAY_SERIF", max(30, int(h * 0.040 * scale)))
    currency_font = font_for_role(fonts, "EDITORIAL_SANS", max(13, int(h * 0.017 * scale)))
    unit_font = font_for_role(fonts, "EDITORIAL_SANS", max(15, int(h * 0.018 * scale)))
    cta_font = font_for_role(fonts, "CTA", max(13, int(h * 0.016 * scale)))
    brand_font = font_for_role(fonts, "DISPLAY_SERIF", max(12, int(h * 0.016 * scale)))
    closure_font = font_for_role(fonts, "EDITORIAL_SANS", max(11, int(h * 0.013)))

    facts = {
        "headline": REQUIRED_FACTS["headline"],
        "unit_type": f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}",
        "price": REQUIRED_FACTS["list_price"],
        "discount": REQUIRED_FACTS["discount"],
        "discount_label": REQUIRED_FACTS["discount_label"],
        "cta": REQUIRED_FACTS["cta"],
    }
    first, last = (facts["headline"].split(" ", 1) + [""])[:2]
    campaign = compose_campaign_type(
        draw,
        origin=(ox, oy + int(h * 0.110)),
        first=first,
        last=last or first,
        display=display,
        display_sm=display_sm,
        fill=IVORY,
        accent=IVORY,
        tracking=22.0,
    )
    headline = campaign["headline"]
    if (headline[3] - headline[1]) / h < 0.03:
        raise RuntimeError("native headline height must be >= 0.03 for COPY_EDIT_ONLY")

    metrics = {
        "discount": dict(zip(("width", "height"), measure_tracked(facts["discount"], discount_font, 8))),
        "discount_label": dict(zip(("width", "height"), measure_tracked(facts["discount_label"], label_font, 180))),
        "price": dict(zip(("width", "height"), measure_tracked(facts["price"], price_font, 8))),
    }
    offer_origin = (headline[0], headline[3] + int(h * 0.022))
    offer = offer_layout_v2(origin=offer_origin, metrics=metrics, canvas=(w, h), geometry="stacked_statement")
    rx0, ry0, rx1, ry1 = offer["rule_px"]
    draw.line((rx0, ry0, rx1, ry1), fill=GOLD, width=2)
    disc = render_percent(draw, origin=(offer["boxes"]["discount"][0], offer["boxes"]["discount"][1]), text=facts["discount"], font=discount_font, fill=GOLD, alignment="left")
    label = _draw_tracked(draw, (offer["boxes"]["discount_label"][0], offer["boxes"]["discount_label"][1]), facts["discount_label"], label_font, IVORY, tracking=180, anchor="lt")
    price = render_price(
        draw,
        origin=(offer["boxes"]["price"][0], offer["boxes"]["price"][1]),
        text=facts["price"],
        number_font=price_font,
        currency_font=currency_font,
        fill=GOLD,
        alignment="left",
        tracking=8.0,
    )
    offer_bbox = (
        min(disc[0], label[0], price[0], headline[0]),
        min(disc[1], label[1], price[1]),
        max(disc[2], label[2], price[2]),
        max(disc[3], label[3], price[3]),
    )
    unit_w, unit_h = measure_tracked(facts["unit_type"], unit_font, 180)
    cta_w, cta_h = measure_tracked(facts["cta"], cta_font, 240)
    action = compose_editorial_cta(
        offer_bbox=offer_bbox,
        unit_size=(unit_w, unit_h),
        cta_size=(cta_w, cta_h),
        canvas=(w, h),
        mode="COLUMN_OPEN",
        alignment="left",
    )
    unit = _draw_tracked(draw, (action["unit_px"][0], action["unit_px"][1]), facts["unit_type"], unit_font, IVORY, tracking=180, anchor="lt")
    cta = _draw_tracked(draw, (action["cta_px"][0], action["cta_px"][1]), facts["cta"], cta_font, IVORY, tracking=240, anchor="lt")
    draw.line(action["rule_px"][:2] + action["rule_px"][2:], fill=GOLD, width=1)

    lw, lh = int(w * 0.11), int(h * 0.072)
    brand = integrate_brand(
        campaign_bbox=headline,
        offer_bbox=offer_bbox,
        architecture_x=float(mapped.get("spire_axis") or 0.62),
        canvas=(w, h),
        logo_size=(lw, lh),
        mode="COLUMN_OPEN",
    )
    lx, ly, _lx1, _ly1 = brand["px"]
    fitted = _fit_logo(logo_rgba, lw, lh).convert("RGBA")
    gold_logo = Image.new("RGBA", fitted.size, (*GOLD, 0))
    gold_logo.putalpha(fitted.getchannel("A"))
    logo_px = _paste_fitted_logo(canvas, gold_logo, lx, ly)
    caption = _draw_tracked(draw, (logo_px[0], logo_px[3] + 6), BRAND_CAPTION, brand_font, GOLD, tracking=280, anchor="lt")

    closure = _draw_tracked(draw, (w // 2, int(h * 0.915)), APPROVED_BOTTOM_COPY, closure_font, IVORY, tracking=320, anchor="mt")
    rule_y = closure[3] + 8
    half = int(w * 0.07)
    draw.line((w // 2 - half, rule_y, w // 2 + half, rule_y), fill=GOLD, width=1)
    closure_px = (closure[0], closure[1], closure[2], rule_y + 2)

    objects = _objects((w, h), headline=headline, unit=unit, price=price, discount=disc, label=label, cta=cta, logo=logo_px)
    objects["brand_caption"] = {"role": "brand_caption", "bounds": _norm_box(*caption, (w, h)), "px": list(caption)}
    objects["editorial_closure"] = {
        "role": "editorial_closure",
        "bounds": _norm_box(*closure_px, (w, h)),
        "px": list(closure_px),
        "copy_status": "APPROVED",
        "text": APPROVED_BOTTOM_COPY,
        "rendered_copy": APPROVED_BOTTOM_COPY,
    }
    graph = concept3_relationship_graph()
    graph = {**graph, "mode": NATIVE_MODE}
    occ = occupancy or {}
    return {
        "schema": "GraphicDesignCompositorV4",
        "compositor": "GraphicDesignCompositorV4",
        "engines": [
            "GraphicDesignCompositorV4",
            "CreativeRelationshipGraphV1",
            "CreativeGroupV2",
            "GraphicFieldEngineV1",
            "TypographicCompositionEngineV1",
            "CommercialOfferComposerV2",
            "BrandIntegrationEngineV1",
            "EditorialCTAComposerV1",
        ],
        "reconstruction_mode": NATIVE_MODE,
        "composition_name": layout["composition_name"],
        "sketch_id": sketch_id,
        "classified_as": None,
        "template_mode": None,
        "image": canvas.convert("RGB"),
        "fielded": fielded,
        "field_mask": applied["mask"],
        "graphic_fields": fields,
        "foundation": photo,
        "objects": objects,
        "groups_v2": groups_from_objects(objects, mode=NATIVE_MODE),
        "relationship_graph": graph,
        "gravity": compositional_gravity(occ, objects),
        "reading_flow": reading_flow(objects),
        "typography": campaign,
        "offer": offer,
        "brand_engine": brand,
        "cta_engine": action,
        "art_plan": layout,
        "pill": False,
        "button_rectangle": False,
        "split_panel": False,
        "real_logo": True,
        "bottom_copy_status": "APPROVED",
        "bottom_copy": APPROVED_BOTTOM_COPY,
        "canvas": [w, h],
        "production": production,
    }


def render_sketch_comparison(concept: Image.Image, photo: Image.Image, sketches: dict[str, Image.Image]) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1280), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 16), "08  SKETCH COMPARISON  —  same campaign language, three native geometries", fill=(201, 168, 92))
    tiles = [("CONCEPT 3", concept), ("DAY_007", photo), ("SKETCH A", sketches["A"]), ("SKETCH B", sketches["B"]), ("SKETCH C", sketches["C"])]
    for i, (cap, image) in enumerate(tiles):
        tile = image.copy()
        tile.thumbnail((340, 430), Image.Resampling.LANCZOS)
        x = 36 + (i % 5) * 372
        y = 56 + (0 if i < 5 else 520)
        canvas.paste(tile.convert("RGB"), (x, y))
        draw.text((x, y + 440), cap, fill=(226, 222, 214))
    return canvas


def _parse_sketch_scores(raw: dict[str, Any]) -> dict[str, float]:
    return {k: round(_num(raw.get(k), 0), 2) for k in SKETCH_KEYS}


def request_sketch_critic(
    concept: Image.Image,
    photo: Image.Image,
    sketches: dict[str, Image.Image],
) -> tuple[dict[str, Any], int]:
    content = [
        _text(
            "You are a fresh visual art director. Image 1 is APPROVED Concept 3 DESIGN LANGUAGE "
            "(not a pixel layout to copy). Image 2 is the REAL Day_007 photograph — its geometry "
            "is authoritative. Images 3-5 are structured sketches A, B, C that transfer Concept 3 "
            "language onto the real photo. Do NOT select a template. Do NOT average sketches. "
            "Select ONE sketch that most successfully transfers the approved art direction to the "
            "REAL photograph without becoming a rectangular sidebar or a Concept 3 copy. "
            "Score 0-10 each sketch for: " + ", ".join(SKETCH_KEYS) + ". "
            "JSON: {selected: 'A'|'B'|'C', sketches: {A:{scores:{...}, notes}, B:{...}, C:{...}}, reason}."
        ),
        _text("IMAGE 1 — APPROVED CONCEPT 3 (design language)"),
        _img(concept, quality=80),
        _text("IMAGE 2 — REAL DAY_007"),
        _img(photo, quality=80),
        _text("IMAGE 3 — SKETCH A"),
        _img(sketches["A"], quality=80),
        _text("IMAGE 4 — SKETCH B"),
        _img(sketches["B"], quality=80),
        _text("IMAGE 5 — SKETCH C"),
        _img(sketches["C"], quality=80),
    ]
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 2200,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Visual art director. Select one sketch. JSON only. Do not inflate. Do not average."},
                {"role": "user", "content": content},
            ],
        }
    )
    block = parsed.get("sketches") if isinstance(parsed.get("sketches"), dict) else parsed
    out = {}
    for key in ("A", "B", "C"):
        item = block.get(key) if isinstance(block, dict) else {}
        scores_raw = item.get("scores") if isinstance(item, dict) and isinstance(item.get("scores"), dict) else (item if isinstance(item, dict) else {})
        scores = _parse_sketch_scores(scores_raw if isinstance(scores_raw, dict) else {})
        out[key] = {
            "scores": scores,
            "mean": round(sum(scores.values()) / max(1, len(scores)), 2),
            "notes": str((item or {}).get("notes") or parsed.get("reason") or ""),
        }
    selected = str(parsed.get("selected") or "").strip().upper()
    if selected not in {"A", "B", "C"}:
        selected = max(out, key=lambda k: out[k]["mean"])
    return {
        "schema": "SketchCriticV1",
        "selected": selected,
        "reason": str(parsed.get("reason") or out[selected]["notes"]),
        "sketches": out,
        "averaged": False,
        "vision_returned": bool(parsed),
    }, calls


def request_final_critic(concept: Image.Image, photo: Image.Image, final: Image.Image) -> tuple[dict[str, Any], int]:
    content = [
        _text(
            "Evaluate the FINAL candidate as a NEW execution of the approved campaign family. "
            "Image 1 = approved Concept 3. Image 2 = real Day_007. Image 3 = structured candidate. "
            "Do NOT ask if it is pixel-identical to Concept 3. Ask: if Concept 3 and this candidate "
            "appeared in the same premium campaign, would they clearly feel art-directed by the same "
            "creative team? Do not penalize refusal of invented Capitol/Monument/skyline. "
            "architecture_fidelity means the REAL Temple photograph is intact. Score 0-10 for: "
            + ", ".join(FINAL_KEYS)
            + ". JSON {scores:{...}, same_campaign_family: bool, notes}."
        ),
        _text("IMAGE 1 — APPROVED CONCEPT 3"),
        _img(concept, quality=82),
        _text("IMAGE 2 — REAL DAY_007"),
        _img(photo, quality=82),
        _text("IMAGE 3 — PHASE 6.2 NATIVE CANDIDATE"),
        _img(final, quality=82),
    ]
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 1800,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Campaign-family critic. JSON only. Do not inflate. Do not redesign."},
                {"role": "user", "content": content},
            ],
        }
    )
    raw = parsed.get("scores") if isinstance(parsed.get("scores"), dict) else parsed
    scores = {k: round(_num(raw.get(k), 0), 2) for k in FINAL_KEYS}
    failed = [k for k, floor in FINAL_FLOORS.items() if scores.get(k, 0) < floor]
    return {
        "schema": "FinalVisualCriticV1",
        "question": "Would Concept 3 and this candidate feel art-directed by the same creative team?",
        "scores": scores,
        "floors": FINAL_FLOORS,
        "failed": failed,
        "pass": not failed,
        "same_campaign_family": bool(parsed.get("same_campaign_family") if "same_campaign_family" in parsed else not failed),
        "notes": str(parsed.get("notes") or ""),
    }, calls
