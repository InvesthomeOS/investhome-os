"""Phase 6.1 — reconstruct approved Concept 3 as a dedicated structured compositor."""

from __future__ import annotations

import io
import json
import math
from pathlib import Path
from typing import Any
from uuid import UUID

from PIL import Image, ImageChops, ImageDraw, ImageStat
from sqlalchemy.orm import Session

from investhome_api.services.creative_director.ai_visual_art_director import _img, _num, _text
from investhome_api.services.creative_director.commercial_number_renderer import render_percent, render_price
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
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, REQUIRED_FACTS, _read_bytes
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY, _draw_tracked, _norm_box, _objects
from investhome_api.services.gpt_image_design.compose import _fit_logo
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

CANVAS_4X5 = (1088, 1360)
CONCEPT3_ASSET_ID = "5c2b06d4-9f61-4358-a21b-7d5f9a098093"
DAY007_ASSET_ID = "c0afa1bf-b487-410c-be3d-91c31852550d"
DAY007_FILENAME = "IH_DC_TMP_001_Render_Exterior_Day_007.jpg"
DRAFT_BOTTOM_COPY = "TARİHİN RUHU, GELECEĞİN DEĞERİ."
BRAND_CAPTION = "THE TEMPLE"

FIDELITY_KEYS = (
    "overall_composition",
    "photo_graphic_relationship",
    "dark_field_geometry",
    "arc_system",
    "visual_mass",
    "brand_role",
    "campaign_group",
    "offer_group",
    "CTA_role",
    "typographic_mass",
    "reading_flow",
    "negative_space",
    "visual_depth",
    "whole_canvas_character",
)

FIDELITY_FLOORS = {
    "overall_composition": 9,
    "photo_graphic_relationship": 9,
    "dark_field_geometry": 9,
    "arc_system": 9,
    "visual_mass": 9,
    "brand_role": 8,
    "campaign_group": 9,
    "offer_group": 9,
    "CTA_role": 8,
    "typographic_mass": 8,
    "reading_flow": 9,
    "negative_space": 9,
    "visual_depth": 8,
    "whole_canvas_character": 9,
}

QUALITY_KEYS = (
    "agency_campaign_feel",
    "art_direction",
    "composition",
    "photo_graphic_integration",
    "typography",
    "commercial_storytelling",
    "brand_integration",
    "visual_depth",
    "premium_character",
    "readability",
    "architecture_fidelity",
    "publishability",
)

_DEFAULT_GROUPS = {
    "brand_group": {"x": 0.055, "y": 0.042, "w": 0.18, "h": 0.11},
    "campaign_group": {"x": 0.055, "y": 0.195, "w": 0.34, "h": 0.07},
    "offer_group": {"x": 0.055, "y": 0.30, "w": 0.30, "h": 0.34},
    "action_group": {"x": 0.055, "y": 0.70, "w": 0.24, "h": 0.055},
    "bottom_closure": {"x": 0.18, "y": 0.905, "w": 0.64, "h": 0.055},
}


def load_approved_concept3(db: Session) -> Image.Image:
    try:
        return Image.open(io.BytesIO(_read_bytes(db, UUID(CONCEPT3_ASSET_ID)))).convert("RGB")
    except Exception:
        for path in (
            Path("/tmp/05-concept-3.png"),
            Path("/tmp/phase6-0-pure-creative-director/05-concept-3.png"),
            Path("artifacts/phase6-0-pure-creative-director/05-concept-3.png"),
        ):
            if path.is_file():
                return Image.open(path).convert("RGB")
        raise RuntimeError("approved Concept 3 image is not available")


def load_day007(db: Session) -> Image.Image:
    return Image.open(io.BytesIO(_read_bytes(db, UUID(DAY007_ASSET_ID)))).convert("RGB")


def _box(raw: Any, fallback: dict[str, float]) -> dict[str, float]:
    if not isinstance(raw, dict):
        return dict(fallback)
    return {
        "x": max(0.0, min(0.9, _num(raw.get("x"), fallback["x"]))),
        "y": max(0.0, min(0.95, _num(raw.get("y"), fallback["y"]))),
        "w": max(0.04, min(0.9, _num(raw.get("w"), fallback["w"]))),
        "h": max(0.02, min(0.6, _num(raw.get("h"), fallback["h"]))),
    }


def _smooth(values: list[float], span: int = 11) -> list[float]:
    if not values:
        return values
    out = list(values)
    n = len(out)
    radius = max(1, span // 2)
    for _ in range(3):
        nxt = out[:]
        for i in range(n):
            sl = out[max(0, i - radius) : min(n, i + radius + 1)]
            nxt[i] = sum(sl) / len(sl)
        out = nxt
    return out


def extract_dark_field_polyline(concept: Image.Image, samples: int = 48) -> dict[str, Any]:
    luma = concept.convert("L")
    w, h = luma.size
    px = luma.load()
    rgb = concept.load()
    xs: list[float] = []
    gold_xs: list[float] = []
    for i in range(samples):
        y = int((i / max(samples - 1, 1)) * (h - 1))
        dark_end = int(w * 0.12)
        for x in range(int(w * 0.08), int(w * 0.72)):
            if px[x, y] < 82:
                dark_end = x
            elif px[x, y] > 118 and x > int(w * 0.16):
                break
        gold_x = None
        for x in range(max(8, dark_end - 40), min(w - 1, dark_end + 90)):
            r, g, b = rgb[x, y]
            if r > 150 and g > 110 and r - b > 40 and g - b > 18 and b < 170:
                gold_x = x
                break
        xs.append(dark_end / w)
        gold_xs.append((gold_x / w) if gold_x is not None else xs[-1])
    field_x = _smooth(xs, 7)
    arc_x = _smooth([(g if abs(g - f) < 0.12 else f) for g, f in zip(gold_xs, field_x)], 5)
    mean_top = sum(field_x[:8]) / 8
    mean_mid = sum(field_x[20:28]) / 8
    mean_bot = sum(field_x[-8:]) / 8
    return {
        "samples": samples,
        "field_polyline_x": [round(v, 4) for v in field_x],
        "arc_polyline_x": [round(v, 4) for v in arc_x],
        "width_top": round(mean_top, 4),
        "width_mid": round(mean_mid, 4),
        "width_bot": round(mean_bot, 4),
        "asymmetric": mean_mid + 0.02 < min(mean_top, mean_bot),
        "sidebar": abs(mean_top - mean_mid) < 0.02 and abs(mean_bot - mean_mid) < 0.02,
    }


def fit_ellipse_to_polyline(polyline_x: list[float]) -> dict[str, float]:
    n = len(polyline_x)
    pts = [(polyline_x[i], i / max(n - 1, 1)) for i in range(n)]
    best = {"cx": 0.98, "cy": 0.50, "rx": 0.68, "ry": 0.90, "error": 9.0}
    for cx in (0.82, 0.90, 0.98, 1.06, 1.14, 1.22):
        for cy in (0.44, 0.50, 0.56):
            for rx in (0.52, 0.60, 0.68, 0.76, 0.84):
                for ry in (0.72, 0.84, 0.96, 1.08):
                    err = 0.0
                    count = 0
                    for x, y in pts[2:-2]:
                        ny = (y - cy) / ry
                        if abs(ny) >= 0.98:
                            continue
                        pred = cx - rx * math.sqrt(max(0.0, 1.0 - ny * ny))
                        err += abs(pred - x)
                        count += 1
                    if count < 8:
                        continue
                    err /= count
                    if err < best["error"]:
                        best = {"cx": cx, "cy": cy, "rx": rx, "ry": ry, "error": round(err, 4)}
    return best


def analyze_concept3_pixels(concept: Image.Image) -> dict[str, Any]:
    w, h = concept.size
    edge = extract_dark_field_polyline(concept)
    ellipse = fit_ellipse_to_polyline(edge["arc_polyline_x"])
    luma = concept.convert("L")
    left = ImageStat.Stat(luma.crop((0, 0, int(w * 0.38), h))).mean[0]
    right = ImageStat.Stat(luma.crop((int(w * 0.55), 0, w, h))).mean[0]
    node_x = edge["arc_polyline_x"][int(len(edge["arc_polyline_x"]) * 0.42)]
    return {
        "schema": "ApprovedCreativeStructureMapV1",
        "canvas": [w, h],
        "photo_boundary_behavior": "photograph occupies the right aperture; left edge is a curved feathered overlay, not a vertical crop",
        "dark_field_geometry": {
            "shape": "curved_left_editorial_field",
            "not_sidebar": not edge["sidebar"],
            "width_top": edge["width_top"],
            "width_mid": edge["width_mid"],
            "width_bot": edge["width_bot"],
            "polyline_x": edge["field_polyline_x"],
            "transparency": "charcoal overlay with photographic depth still perceptible",
            "edge_behavior": "feathered along the gold arc",
        },
        "main_gold_arc": {
            "kind": "elliptical_arc",
            **ellipse,
            "polyline_x": edge["arc_polyline_x"],
            "arc_start": 100.0,
            "arc_end": 258.0,
        },
        "secondary_arc_ticks": {"kind": "radial_tick_sequence", "ticks": 16, **{k: ellipse[k] for k in ("cx", "cy", "rx", "ry")}},
        "spire_relationship": "primary vertical axis on the right photographic aperture",
        "visual_center_of_gravity": {"x": 0.58, "y": 0.46},
        "reading_flow": [
            "BRAND_GROUP",
            "CAMPAIGN_GROUP",
            "OFFER_GROUP",
            "ACTION_GROUP",
            "EDITORIAL_CLOSURE_GROUP",
        ],
        "left_luma": round(left, 2),
        "right_luma": round(right, 2),
        "precision_marker": {"x": round(node_x, 4), "y": 0.42, "r": 0.0065},
        "negative_space": "deliberate left breathing margin inside the dark field; right photograph remains open around the spire",
        "logo_scale_and_role": "small gold mark in the upper brand zone; identity, not a hero illustration",
        "groups": dict(_DEFAULT_GROUPS),
        "type_scale_ratios": {
            "headline_to_canvas": 0.032,
            "discount_to_headline": 1.55,
            "price_to_discount": 0.62,
            "cta_to_headline": 0.42,
        },
        "draft_generated_copy": DRAFT_BOTTOM_COPY,
        "pixel_edge": edge,
    }


def request_structure_vision(concept: Image.Image, pixel_map: dict[str, Any]) -> tuple[dict[str, Any], int]:
    content = [
        _text(
            "Extract ApprovedCreativeStructureMapV1 from this approved Concept 3. "
            "Return JSON with normalized 0-1 boxes: brand_group, campaign_group, offer_group, "
            "action_group, bottom_closure. Also: logo_box, headline_box, discount_box, price_box, "
            "unit_box, cta_box, bottom_text if readable, type_scale notes, gold_arc description, "
            "dark_field description. Do not classify SKY_VEIL, GROUND_PLANE, CORNER_INGRESS, "
            "SPLIT_PANEL, or SIDEBAR. The composition is Concept 3 itself."
        ),
        _img(concept, quality=86),
        _text("Pixel-measured field widths: " + json.dumps({k: pixel_map["dark_field_geometry"][k] for k in ("width_top", "width_mid", "width_bot")})),
    ]
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 1800,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Measurement analyst. JSON only. Do not redesign."},
                {"role": "user", "content": content},
            ],
        }
    )
    groups = dict(_DEFAULT_GROUPS)
    src = parsed.get("groups") if isinstance(parsed.get("groups"), dict) else parsed
    for key in groups:
        groups[key] = _box(src.get(key) or parsed.get(key), groups[key])
    draft = str(parsed.get("bottom_text") or parsed.get("draft_generated_copy") or pixel_map.get("draft_generated_copy") or DRAFT_BOTTOM_COPY)
    pixel_map["groups"] = groups
    pixel_map["vision"] = {k: parsed.get(k) for k in ("gold_arc", "dark_field", "logo_box", "reading_flow", "notes") if k in parsed}
    pixel_map["draft_generated_copy"] = draft.strip() or DRAFT_BOTTOM_COPY
    pixel_map["vision_calls"] = calls
    return pixel_map, calls


def match_day007_crop(concept: Image.Image, source: Image.Image) -> dict[str, Any]:
    tw, th = CANVAS_4X5
    ref = concept.convert("RGB").resize((tw, th), Image.Resampling.LANCZOS)
    x0 = int(tw * 0.46)
    target = ref.crop((x0, 0, tw, th)).convert("L").resize((48, 72), Image.Resampling.BOX)
    t_bytes = list(target.getdata())
    t_mean = sum(t_bytes) / len(t_bytes)
    src = source.convert("RGB")
    sw, sh = src.size
    scale = max(tw / max(sw, 1), th / max(sh, 1))
    nw = max(tw, int(round(sw * scale)))
    nh = max(th, int(round(sh * scale)))
    scaled = src.resize((nw, nh), Image.Resampling.LANCZOS)
    best: dict[str, Any] | None = None
    for cx in [i / 20 for i in range(6, 17)]:
        for cy in [i / 20 for i in range(4, 14)]:
            left = int(round((nw - tw) * max(0.0, min(1.0, cx))))
            top = int(round((nh - th) * max(0.0, min(1.0, cy))))
            left = max(0, min(left, nw - tw))
            top = max(0, min(top, nh - th))
            crop = scaled.crop((left, top, left + tw, top + th))
            probe = crop.crop((x0, 0, tw, th)).convert("L").resize((48, 72), Image.Resampling.BOX)
            p_bytes = list(probe.getdata())
            p_mean = sum(p_bytes) / len(p_bytes)
            num = den_a = den_b = 0.0
            for a, b in zip(t_bytes, p_bytes):
                da, db = a - t_mean, b - p_mean
                num += da * db
                den_a += da * da
                den_b += db * db
            ncc = num / max(1e-6, math.sqrt(den_a * den_b))
            if best is None or ncc > best["ncc"]:
                transform = {
                    "source_crop": [
                        round(left / scale, 2),
                        round(top / scale, 2),
                        round((left + tw) / scale, 2),
                        round((top + th) / scale, 2),
                    ],
                    "source_scale": round(scale, 6),
                    "scale_x": round(scale, 6),
                    "scale_y": round(scale, 6),
                    "non_uniform_scale": False,
                    "source_position": [0, 0],
                    "centering": [round(cx, 3), round(cy, 3)],
                    "canvas_size": [tw, th],
                    "source_size": [sw, sh],
                }
                best = {"centering": [round(cx, 3), round(cy, 3)], "ncc": round(ncc, 4), "transform": transform, "crop": crop}
    assert best is not None
    graded = apply_photographic_grade(best["crop"], dict(LOCKED_GRADE))
    best["graded"] = graded
    best["source_asset_id"] = DAY007_ASSET_ID
    best["filename"] = DAY007_FILENAME
    best["uniform_scale"] = True
    best["non_uniform_scale"] = False
    best["generated_architecture"] = False
    return best


def concept3_field_specs(structure: dict[str, Any]) -> list[dict[str, Any]]:
    field = structure["dark_field_geometry"]
    arc = structure["main_gold_arc"]
    ticks = structure["secondary_arc_ticks"]
    marker = structure["precision_marker"]
    poly = field["polyline_x"]
    return [
        field_spec(
            "photo_overlay_field",
            axis="horizontal",
            start=0.0,
            end=float(field["width_mid"]),
            strength=0.78,
            role="dark_editorial_field",
            polyline_x=poly,
            feather=0.11,
            blur=24,
        ),
        field_spec(
            "feathered_tonal_field",
            start=0.0,
            end=0.22,
            strength=0.18,
            role="left_breathing_weight",
            polyline_x=[max(0.0, v * 0.55) for v in poly],
            feather=0.08,
            blur=18,
        ),
        field_spec(
            "elliptical_arc",
            role="main_gold_arc",
            cx=arc["cx"],
            cy=arc["cy"],
            rx=arc["rx"],
            ry=arc["ry"],
            arc_start=arc["arc_start"],
            arc_end=arc["arc_end"],
            stroke=2,
            polyline_x=structure["pixel_edge"]["arc_polyline_x"],
        ),
        field_spec(
            "curved_rule",
            role="arc_stroke_from_pixels",
            polyline_x=structure["pixel_edge"]["arc_polyline_x"],
            stroke=2,
        ),
        field_spec(
            "radial_tick_sequence",
            role="measurement_ticks",
            cx=ticks["cx"],
            cy=ticks["cy"],
            rx=ticks["rx"],
            ry=ticks["ry"],
            arc_start=108,
            arc_end=248,
            ticks=16,
            tick_length=0.016,
        ),
        field_spec(
            "editorial_measurement_marks",
            role="concentric_blueprint",
            cx=arc["cx"],
            cy=arc["cy"],
            rx=arc["rx"],
            ry=arc["ry"],
            arc_start=112,
            arc_end=240,
        ),
        field_spec("precision_marker", role="arc_node", x=marker["x"], y=marker["y"], r=marker["r"]),
    ]


def _px(box: dict[str, float], size: tuple[int, int]) -> tuple[int, int, int, int]:
    w, h = size
    x0 = int(box["x"] * w)
    y0 = int(box["y"] * h)
    return x0, y0, x0 + int(box["w"] * w), y0 + int(box["h"] * h)


def compose_approved_concept3(
    photo: Image.Image,
    *,
    structure: dict[str, Any],
    fonts: dict[str, Any],
    logo_rgba: Image.Image,
    occupancy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    w, h = CANVAS_4X5
    photo = photo.convert("RGB").resize((w, h), Image.Resampling.LANCZOS)
    fields = concept3_field_specs(structure)
    applied = apply_structured_field_specs(photo, occupancy, fields, darken=0.44, protect_architecture=False)
    fielded = applied["image"]
    vectors = render_vector_fields((w, h), fields)
    canvas = fielded.convert("RGBA")
    canvas.alpha_composite(vectors)
    draw = ImageDraw.Draw(canvas)
    groups = structure["groups"]
    brand_box = _px(groups["brand_group"], (w, h))
    campaign_box = _px(groups["campaign_group"], (w, h))
    offer_box = _px(groups["offer_group"], (w, h))
    action_box = _px(groups["action_group"], (w, h))
    closure_box = _px(groups["bottom_closure"], (w, h))

    ox = brand_box[0]
    headline_font = font_for_role(fonts, "EDITORIAL_SANS", max(28, int(h * 0.034)))
    discount_font = font_for_role(fonts, "DISPLAY_SERIF", max(42, int(h * 0.058)))
    label_font = font_for_role(fonts, "EDITORIAL_SANS", max(12, int(h * 0.015)))
    price_font = font_for_role(fonts, "DISPLAY_SERIF", max(26, int(h * 0.032)))
    currency_font = font_for_role(fonts, "EDITORIAL_SANS", max(12, int(h * 0.016)))
    unit_num = font_for_role(fonts, "DISPLAY_SERIF", max(18, int(h * 0.022)))
    unit_word = font_for_role(fonts, "EDITORIAL_SANS", max(14, int(h * 0.016)))
    cta_font = font_for_role(fonts, "CTA", max(12, int(h * 0.014)))
    brand_font = font_for_role(fonts, "DISPLAY_SERIF", max(12, int(h * 0.016)))

    lw, lh = int(w * 0.09), int(h * 0.07)
    fitted = _fit_logo(logo_rgba, lw, lh).convert("RGBA")
    gold_logo = Image.new("RGBA", fitted.size, (*GOLD, 0))
    gold_logo.putalpha(fitted.getchannel("A"))
    lx, ly = ox, brand_box[1]
    logo_px = _paste_fitted_logo(canvas, gold_logo, lx, ly)
    caption = _draw_tracked(
        draw,
        (ox, logo_px[3] + 6),
        BRAND_CAPTION,
        brand_font,
        GOLD,
        tracking=280,
        anchor="lt",
    )

    hy = campaign_box[1]
    headline = _draw_tracked(draw, (ox, hy), REQUIRED_FACTS["headline"], headline_font, IVORY, tracking=80, anchor="lt")
    rule_y = headline[3] + 10
    draw.line((ox, rule_y, headline[2], rule_y), fill=GOLD, width=1)

    oy = max(offer_box[1], rule_y + int(h * 0.028))
    disc = render_percent(draw, origin=(ox, oy), text=REQUIRED_FACTS["discount"], font=discount_font, fill=GOLD, alignment="left")
    label = _draw_tracked(draw, (ox, disc[3] + 4), REQUIRED_FACTS["discount_label"], label_font, IVORY, tracking=220, anchor="lt")
    r2 = label[3] + 12
    draw.line((ox, r2, max(disc[2], label[2]), r2), fill=GOLD, width=1)
    price = render_price(
        draw,
        origin=(ox, r2 + int(h * 0.018)),
        text=REQUIRED_FACTS["list_price"],
        number_font=price_font,
        currency_font=currency_font,
        fill=GOLD,
        alignment="left",
        tracking=10.0,
    )
    r3 = price[3] + 12
    draw.line((ox, r3, price[2], r3), fill=GOLD, width=1)
    unit_a = _draw_tracked(draw, (ox, r3 + int(h * 0.016)), REQUIRED_FACTS["unit"], unit_num, GOLD, tracking=8, anchor="lt")
    unit_b = _draw_tracked(draw, (unit_a[2] + 10, r3 + int(h * 0.020)), REQUIRED_FACTS["unit_label"], unit_word, IVORY, tracking=180, anchor="lt")
    unit = (min(unit_a[0], unit_b[0]), min(unit_a[1], unit_b[1]), max(unit_a[2], unit_b[2]), max(unit_a[3], unit_b[3]))

    cy = max(action_box[1], unit[3] + int(h * 0.045))
    cta_text = _draw_tracked(draw, (ox + 16, cy), REQUIRED_FACTS["cta"], cta_font, IVORY, tracking=240, anchor="lt")
    cta = (cta_text[0] - 16, cta_text[1] - 10, cta_text[2] + 16, cta_text[3] + 10)
    draw.rectangle(cta, outline=GOLD, width=1)

    rule_cx = (closure_box[0] + closure_box[2]) // 2
    rule_y2 = closure_box[3] - 8
    half = int(w * 0.08)
    draw.line((rule_cx - half, rule_y2, rule_cx + half, rule_y2), fill=GOLD, width=1)
    closure_px = (closure_box[0], closure_box[1], closure_box[2], closure_box[3])

    objects = _objects(
        (w, h),
        headline=headline,
        unit=unit,
        price=price,
        discount=disc,
        label=label,
        cta=cta,
        logo=logo_px,
    )
    objects["brand_caption"] = {"role": "brand_caption", "bounds": _norm_box(*caption, (w, h)), "px": list(caption)}
    objects["editorial_closure"] = {
        "role": "editorial_closure",
        "bounds": _norm_box(*closure_px, (w, h)),
        "px": list(closure_px),
        "copy_status": "PENDING_HUMAN_COPY_APPROVAL",
        "draft_generated_copy": structure.get("draft_generated_copy") or DRAFT_BOTTOM_COPY,
        "rendered_copy": None,
    }
    group_list = groups_from_objects(objects, mode="APPROVED_CONCEPT_3")
    graph = concept3_relationship_graph()
    gravity = compositional_gravity(occupancy or {}, objects)
    flow = reading_flow(objects)
    final = canvas.convert("RGB")
    return {
        "schema": "ApprovedConcept3ReconstructionV1",
        "compositor": "ApprovedConcept3ReconstructionV1",
        "reconstruction_mode": "APPROVED_CONCEPT_3",
        "classified_as": None,
        "image": final,
        "fielded": fielded,
        "field_mask": applied["mask"],
        "graphic_fields": fields,
        "foundation": photo,
        "objects": objects,
        "groups_v2": group_list,
        "relationship_graph": graph,
        "gravity": gravity,
        "reading_flow": flow,
        "cta_treatment": "restrained_outlined_editorial",
        "pill": False,
        "button_rectangle": False,
        "split_panel": False,
        "sidebar": False,
        "real_logo": True,
        "bottom_copy_status": "PENDING_HUMAN_COPY_APPROVAL",
        "draft_generated_copy": structure.get("draft_generated_copy") or DRAFT_BOTTOM_COPY,
        "canvas": [w, h],
    }


def dark_field_mask_from_concept(concept: Image.Image) -> Image.Image:
    edge = extract_dark_field_polyline(concept, samples=concept.height)
    spec = field_spec("photo_overlay_field", polyline_x=edge["field_polyline_x"], strength=1.0, feather=0.04, blur=2)
    applied = apply_structured_field_specs(concept, None, [spec], darken=0.5)
    return applied["mask"].point(lambda v: 255 if v > 40 else 0)


def geometric_fidelity(concept: Image.Image, production: Image.Image, prod_mask: Image.Image) -> dict[str, Any]:
    ref_mask = dark_field_mask_from_concept(concept)
    a = ref_mask.resize((108, 136), Image.Resampling.BOX)
    b = prod_mask.convert("L").resize((108, 136), Image.Resampling.BOX)
    inter = ImageChops.multiply(a, b)
    union = ImageChops.lighter(a, b)
    ia = sum(1 for v in inter.getdata() if v > 40)
    ua = sum(1 for v in union.getdata() if v > 40)
    iou = ia / max(1, ua)
    small_a = concept.convert("L").resize((54, 68), Image.Resampling.BOX)
    small_b = production.convert("L").resize((54, 68), Image.Resampling.BOX)
    ncc_num = ncc_da = ncc_db = 0.0
    ma = sum(small_a.getdata()) / (54 * 68)
    mb = sum(small_b.getdata()) / (54 * 68)
    for pa, pb in zip(small_a.getdata(), small_b.getdata()):
        da, db = pa - ma, pb - mb
        ncc_num += da * db
        ncc_da += da * da
        ncc_db += db * db
    ncc = ncc_num / max(1e-6, math.sqrt(ncc_da * ncc_db))
    return {
        "dark_field_iou": round(iou, 4),
        "luma_ncc": round(ncc, 4),
        "dark_field_score_hint": round(min(10.0, iou * 10), 2),
        "composition_score_hint": round(min(10.0, max(0.0, (ncc + 1) * 5)), 2),
    }


def request_fidelity_and_quality(concept: Image.Image, production: Image.Image) -> tuple[dict[str, Any], int]:
    keys = list(FIDELITY_KEYS) + list(QUALITY_KEYS)
    content = [
        _text(
            "Compare APPROVED CONCEPT 3 (image 1) with the STRUCTURED PRODUCTION RECONSTRUCTION (image 2). "
            "Do not compare against any older 5.x design. Score 0-10 for: "
            + ", ".join(keys)
            + ". architecture_fidelity means the real Temple photograph is used — do not penalize "
            "the reconstruction for refusing the draft's invented landmarks. "
            "If a relationship was lost, name it in failed_relationships. JSON only."
        ),
        _text("IMAGE 1 — APPROVED CONCEPT 3"),
        _img(concept, quality=82),
        _text("IMAGE 2 — STRUCTURED PRODUCTION MASTER"),
        _img(production, quality=82),
    ]
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 1800,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Art director comparing reconstruction fidelity. JSON only. Do not redesign."},
                {"role": "user", "content": content},
            ],
        }
    )
    scores = parsed.get("scores") if isinstance(parsed.get("scores"), dict) else parsed
    fidelity = {k: round(_num(scores.get(k), 0), 2) for k in FIDELITY_KEYS}
    quality = {k: round(_num(scores.get(k), 0), 2) for k in QUALITY_KEYS}
    failed = [k for k, floor in FIDELITY_FLOORS.items() if fidelity.get(k, 0) < floor]
    return {
        "schema": "ApprovedConceptReconstructionFidelityV1",
        "scores": fidelity,
        "quality": quality,
        "floors": FIDELITY_FLOORS,
        "failed": failed,
        "pass": not failed,
        "failed_relationships": parsed.get("failed_relationships") or parsed.get("what_failed") or failed,
        "notes": str(parsed.get("notes") or ""),
    }, calls
