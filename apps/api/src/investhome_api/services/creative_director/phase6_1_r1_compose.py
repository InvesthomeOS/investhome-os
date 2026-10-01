"""Phase 6.1-R1 compositor — fidelity correction only. Does not overwrite 6.1."""

from __future__ import annotations

import math
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat

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
from investhome_api.services.creative_director.graphic_field_engine import apply_structured_field_specs, field_spec
from investhome_api.services.creative_director.phase5_design_scene import _vision
from investhome_api.services.creative_director.phase5_photo_foundation import apply_photographic_grade
from investhome_api.services.creative_director.phase5_premium_commercial_r1 import LOCKED_GRADE
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_concept3_compose import (
    CANVAS_4X5,
    DAY007_ASSET_ID,
    DAY007_FILENAME,
    FIDELITY_FLOORS,
    FIDELITY_KEYS,
    analyze_concept3_pixels,
    dark_field_mask_from_concept,
    geometric_fidelity,
)
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY, _draw_tracked, _norm_box, _objects
from investhome_api.services.gpt_image_design.compose import _fit_logo
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

PARENT_61_ASSET_ID = "1173f9ef-1066-4388-8d1d-6893fed8a8b2"
PARENT_61_SPEC_ID = "2c1f6b36-f0eb-490d-b312-8e70545ec85f"
APPROVED_BOTTOM_COPY = "TARİHİN RUHU, GELECEĞİN DEĞERİ."
BRAND_CAPTION = "THE TEMPLE"

R1_CROP_CANDIDATES = (
    ("C01", 1.00, 0.58, 0.18),
    ("C02", 1.00, 0.70, 0.22),
    ("C03", 1.00, 0.80, 0.26),
    ("C04", 1.10, 0.60, 0.16),
    ("C05", 1.10, 0.72, 0.20),
    ("C06", 1.10, 0.82, 0.24),
    ("C07", 1.16, 0.64, 0.14),
    ("C08", 1.16, 0.74, 0.20),
    ("C09", 1.16, 0.84, 0.28),
    ("C10", 1.22, 0.66, 0.12),
    ("C11", 1.22, 0.76, 0.18),
    ("C12", 1.24, 0.80, 0.16),
)

CRITIC_KEYS = (
    "creative_direction_fidelity",
    "agency_campaign_feel",
    "composition",
    "photo_graphic_integration",
    "typography",
    "commercial_storytelling",
    "brand_integration",
    "visual_depth",
    "premium_character",
    "whole_canvas_character",
    "readability",
    "architecture_fidelity",
    "publishability",
)
CRITIC_FLOORS = {
    "creative_direction_fidelity": 9,
    "agency_campaign_feel": 8,
    "composition": 9,
    "photo_graphic_integration": 9,
    "typography": 8,
    "commercial_storytelling": 8,
    "premium_character": 8,
    "whole_canvas_character": 9,
    "architecture_fidelity": 9,
}
MASS_KEYS = (
    "brand_mass",
    "headline_mass",
    "offer_mass",
    "CTA_mass",
    "graphic_field_mass",
    "photo_mass",
    "negative_space_mass",
)
MASS_LIMITS = {
    "headline_mass": 0.15,
    "offer_mass": 0.15,
    "graphic_field_mass": 0.12,
}


def _ncc(a: Image.Image, b: Image.Image) -> float:
    pa = list(a.convert("L").getdata())
    pb = list(b.convert("L").getdata())
    ma = sum(pa) / max(1, len(pa))
    mb = sum(pb) / max(1, len(pb))
    num = da = db = 0.0
    for x, y in zip(pa, pb):
        dx, dy = x - ma, y - mb
        num += dx * dy
        da += dx * dx
        db += dy * dy
    return num / max(1e-6, math.sqrt(da * db))


def _spire_x(image: Image.Image) -> float:
    small = image.convert("L").resize((40, 50), Image.Resampling.BOX)
    px = small.load()
    best_x, best = 0.58, -1.0
    for x in range(14, 36):
        col = [px[x, y] for y in range(4, 38)]
        energy = sum(abs(col[i] - col[i - 1]) for i in range(1, len(col))) / max(1, len(col))
        if energy > best:
            best = energy
            best_x = x / max(small.width - 1, 1)
    return round(best_x, 4)


def _right_mass(image: Image.Image) -> float:
    w, h = image.size
    crop = image.convert("L").crop((int(w * 0.48), 0, w, int(h * 0.82)))
    return round(ImageStat.Stat(crop).mean[0] / 255.0, 4)


def cover_zoom_crop(
    source: Image.Image,
    *,
    zoom: float,
    cx: float,
    cy: float,
    target: tuple[int, int] = CANVAS_4X5,
) -> tuple[Image.Image, dict[str, Any]]:
    src = source.convert("RGB")
    tw, th = target
    sw, sh = src.size
    cover = max(tw / max(sw, 1), th / max(sh, 1))
    scale = cover * max(1.0, float(zoom))
    nw = max(tw, int(round(sw * scale)))
    nh = max(th, int(round(sh * scale)))
    scaled = src.resize((nw, nh), Image.Resampling.LANCZOS)
    left = int(round((nw - tw) * max(0.0, min(1.0, cx))))
    top = int(round((nh - th) * max(0.0, min(1.0, cy))))
    left = max(0, min(left, nw - tw))
    top = max(0, min(top, nh - th))
    crop = scaled.crop((left, top, left + tw, top + th))
    return crop, {
        "source_crop": [round(left / scale, 2), round(top / scale, 2), round((left + tw) / scale, 2), round((top + th) / scale, 2)],
        "source_scale": round(scale, 6),
        "scale_x": round(scale, 6),
        "scale_y": round(scale, 6),
        "non_uniform_scale": False,
        "zoom": round(float(zoom), 4),
        "centering": [round(cx, 3), round(cy, 3)],
        "canvas_size": [tw, th],
        "source_size": [sw, sh],
        "source_position": [left, top],
    }


def score_crop_candidate(concept: Image.Image, crop: Image.Image) -> dict[str, float]:
    tw, th = CANVAS_4X5
    ref = concept.convert("RGB").resize((tw, th), Image.Resampling.LANCZOS)
    x0 = int(tw * 0.46)
    a = ref.crop((x0, 0, tw, th)).resize((48, 72), Image.Resampling.BOX)
    b = crop.crop((x0, 0, tw, th)).resize((48, 72), Image.Resampling.BOX)
    photo = _ncc(a, b)
    spire_c = _spire_x(ref)
    spire_p = _spire_x(crop)
    spire_pos = max(0.0, 1.0 - abs(spire_c - spire_p) * 3.2)
    mass_c = _right_mass(ref)
    mass_p = _right_mass(crop)
    arch_mass = max(0.0, 1.0 - abs(mass_c - mass_p) * 2.4)
    right_mass = mass_p
    field_rel = photo
    gravity = 1.0 - min(1.0, abs(spire_p - 0.62) * 2.0)
    overall = 0.28 * photo + 0.22 * spire_pos + 0.18 * arch_mass + 0.16 * field_rel + 0.16 * gravity
    return {
        "spire_position": round(spire_pos * 10, 2),
        "spire_scale": round(max(0.0, 1.0 - abs(spire_c - spire_p)) * 10, 2),
        "architecture_mass": round(arch_mass * 10, 2),
        "right_photo_mass": round(min(10.0, right_mass * 14), 2),
        "field_photo_relationship": round(max(0.0, (photo + 1) * 5), 2),
        "overall_visual_gravity": round(overall * 10, 2),
        "ncc": round(photo, 4),
        "spire_x": spire_p,
        "total": round(overall, 4),
    }


def search_day007_crops(concept: Image.Image, source: Image.Image) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None
    for cid, zoom, cx, cy in R1_CROP_CANDIDATES:
        crop, transform = cover_zoom_crop(source, zoom=zoom, cx=cx, cy=cy)
        graded = apply_photographic_grade(crop, dict(LOCKED_GRADE))
        scores = score_crop_candidate(concept, graded)
        item = {
            "id": cid,
            "zoom": zoom,
            "centering": [cx, cy],
            "transform": transform,
            "scores": scores,
            "crop": graded,
        }
        rows.append(item)
        if best is None or scores["total"] > best["scores"]["total"]:
            best = item
    assert best is not None
    assert len(rows) >= 12
    return {
        "candidates": [{k: v for k, v in row.items() if k != "crop"} | {"has_image": True} for row in rows],
        "selected": {k: v for k, v in best.items() if k != "crop"},
        "images": {row["id"]: row["crop"] for row in rows},
        "selected_image": best["crop"],
        "selected_id": best["id"],
        "count": len(rows),
        "source_asset_id": DAY007_ASSET_ID,
        "filename": DAY007_FILENAME,
        "generated_architecture": False,
        "uniform_scale": True,
    }


def r1_field_specs(structure: dict[str, Any]) -> list[dict[str, Any]]:
    poly = structure["dark_field_geometry"]["polyline_x"]
    marker = structure["precision_marker"]
    return [
        field_spec(
            "photo_overlay_field",
            role="dark_editorial_field",
            polyline_x=poly,
            strength=0.96,
            feather=0.055,
            blur=8,
            bleed=0.08,
        ),
        field_spec(
            "feathered_tonal_field",
            role="left_core_density",
            polyline_x=[max(0.0, v * 0.62) for v in poly],
            strength=0.22,
            feather=0.06,
            blur=14,
            bleed=0.0,
        ),
        field_spec("curved_rule", role="main_arc", polyline_x=structure["pixel_edge"]["arc_polyline_x"], stroke=3),
        field_spec("radial_tick_sequence", role="measurement_ticks", polyline_x=structure["pixel_edge"]["arc_polyline_x"], ticks=15),
        field_spec("precision_marker", role="arc_node", x=marker["x"], y=marker["y"], r=0.006),
    ]


def render_r1_arc(size: tuple[int, int], structure: dict[str, Any], field_mask: Image.Image) -> Image.Image:
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = size
    xs = structure["pixel_edge"]["arc_polyline_x"]
    pts = [(int(w * float(x)), int(h * i / max(len(xs) - 1, 1))) for i, x in enumerate(xs)]
    if len(pts) >= 2:
        draw.line(pts, fill=(*GOLD, 230), width=3, joint="curve")
    step = max(2, len(pts) // 16)
    for i in range(step, len(pts) - step, step):
        p0, p1 = pts[max(0, i - 2)], pts[min(len(pts) - 1, i + 2)]
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        mag = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / mag, dx / mag
        if nx > 0:
            nx, ny = -nx, -ny
        length = 18 if i // step % 3 else 28
        draw.line((pts[i][0], pts[i][1], pts[i][0] + nx * length, pts[i][1] + ny * length), fill=(*GOLD, 210), width=1)
    mx = int(w * float(structure["precision_marker"]["x"]))
    my = int(h * 0.42)
    r = int(min(w, h) * 0.006)
    draw.ellipse((mx - r, my - r, mx + r, my + r), fill=(244, 239, 228, 235), outline=(*GOLD, 230), width=1)
    clip = field_mask.convert("L").filter(ImageFilter.MaxFilter(15))
    r_ch, g_ch, b_ch, a_ch = overlay.split()
    overlay.putalpha(ImageChops.multiply(a_ch, clip))
    return overlay


def match_field_density(concept: Image.Image, photo: Image.Image, structure: dict[str, Any]) -> dict[str, Any]:
    fields = r1_field_specs(structure)
    ref_mask = dark_field_mask_from_concept(concept)
    core = ref_mask.point(lambda v: 255 if v > 140 else 0)
    ref_luma = ImageStat.Stat(Image.composite(concept.convert("L"), Image.new("L", concept.size, 0), core)).mean[0]
    chosen = None
    for darken, mix in ((0.20, 0.78), (0.24, 0.70), (0.28, 0.62)):
        applied = apply_structured_field_specs(
            photo,
            None,
            fields,
            charcoal=(16, 18, 22),
            darken=darken,
            charcoal_mix=mix,
        )
        prod_luma = ImageStat.Stat(Image.composite(applied["image"].convert("L"), Image.new("L", photo.size, 0), core.resize(photo.size))).mean[0]
        delta = abs(prod_luma - ref_luma)
        pack = {"darken": darken, "charcoal_mix": mix, "applied": applied, "ref_luma": round(ref_luma, 2), "prod_luma": round(prod_luma, 2), "delta": round(delta, 2)}
        if chosen is None or delta < chosen["delta"]:
            chosen = pack
    assert chosen is not None
    return chosen


def compose_concept3_r1(
    photo: Image.Image,
    *,
    concept: Image.Image,
    structure: dict[str, Any],
    fonts: dict[str, Any],
    logo_rgba: Image.Image,
    occupancy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    w, h = CANVAS_4X5
    photo = photo.convert("RGB").resize((w, h), Image.Resampling.LANCZOS)
    density = match_field_density(concept.convert("RGB").resize((w, h), Image.Resampling.LANCZOS), photo, structure)
    applied = density["applied"]
    fielded = applied["image"]
    vectors = render_r1_arc((w, h), structure, applied["mask"])
    canvas = fielded.convert("RGBA")
    canvas.alpha_composite(vectors)
    draw = ImageDraw.Draw(canvas)

    ox = int(w * 0.055)
    display = font_for_role(fonts, "DISPLAY_SERIF", max(48, int(h * 0.052)))
    display_sm = font_for_role(fonts, "DISPLAY_SERIF", max(44, int(h * 0.048)))
    discount_font = font_for_role(fonts, "DISPLAY_SERIF", max(56, int(h * 0.072)))
    label_font = font_for_role(fonts, "EDITORIAL_SANS", max(14, int(h * 0.017)))
    price_font = font_for_role(fonts, "DISPLAY_SERIF", max(32, int(h * 0.040)))
    currency_font = font_for_role(fonts, "EDITORIAL_SANS", max(14, int(h * 0.018)))
    unit_num = font_for_role(fonts, "DISPLAY_SERIF", max(22, int(h * 0.026)))
    unit_word = font_for_role(fonts, "EDITORIAL_SANS", max(16, int(h * 0.018)))
    cta_font = font_for_role(fonts, "CTA", max(13, int(h * 0.015)))
    brand_font = font_for_role(fonts, "DISPLAY_SERIF", max(13, int(h * 0.017)))
    closure_font = font_for_role(fonts, "EDITORIAL_SANS", max(11, int(h * 0.013)))

    lw, lh = int(w * 0.10), int(h * 0.078)
    fitted = _fit_logo(logo_rgba, lw, lh).convert("RGBA")
    gold_logo = Image.new("RGBA", fitted.size, (*GOLD, 0))
    gold_logo.putalpha(fitted.getchannel("A"))
    logo_px = _paste_fitted_logo(canvas, gold_logo, ox, int(h * 0.038))
    caption = _draw_tracked(draw, (ox, logo_px[3] + 8), BRAND_CAPTION, brand_font, GOLD, tracking=280, anchor="lt")

    hy = int(h * 0.175)
    line1 = _draw_tracked(draw, (ox, hy), "ALIRKEN", display, IVORY, tracking=24, anchor="lt")
    line2 = _draw_tracked(draw, (ox, line1[3] + 4), "KAZAN", display_sm, IVORY, tracking=16, anchor="lt")
    rule_y = line2[3] + 8
    draw.line((ox, rule_y, max(line1[2], line2[2]), rule_y), fill=GOLD, width=2)
    headline = (min(line1[0], line2[0]), line1[1], max(line1[2], line2[2]), rule_y + 2)
    campaign = {"schema": "TypographicCompositionEngineV1", "headline": headline, "first": line1, "last": line2, "line_break": ["ALIRKEN", "KAZAN"]}
    if (headline[3] - headline[1]) / h < 0.03:
        raise RuntimeError("R1 headline height must be >= 0.03")

    oy = headline[3] + int(h * 0.028)
    disc = render_percent(draw, origin=(ox, oy), text=REQUIRED_FACTS["discount"], font=discount_font, fill=GOLD, alignment="left")
    label = _draw_tracked(draw, (ox, disc[3] + 6), REQUIRED_FACTS["discount_label"], label_font, IVORY, tracking=240, anchor="lt")
    r2 = label[3] + 14
    draw.line((ox, r2, max(disc[2], label[2], headline[2]), r2), fill=GOLD, width=1)
    price = render_price(
        draw,
        origin=(ox, r2 + int(h * 0.020)),
        text=REQUIRED_FACTS["list_price"],
        number_font=price_font,
        currency_font=currency_font,
        fill=GOLD,
        alignment="left",
        tracking=10.0,
    )
    r3 = price[3] + 14
    draw.line((ox, r3, price[2], r3), fill=GOLD, width=1)
    unit_a = _draw_tracked(draw, (ox, r3 + int(h * 0.018)), REQUIRED_FACTS["unit"], unit_num, GOLD, tracking=8, anchor="lt")
    unit_b = _draw_tracked(draw, (unit_a[2] + 12, r3 + int(h * 0.022)), REQUIRED_FACTS["unit_label"], unit_word, IVORY, tracking=180, anchor="lt")
    unit = (min(unit_a[0], unit_b[0]), min(unit_a[1], unit_b[1]), max(unit_a[2], unit_b[2]), max(unit_a[3], unit_b[3]))

    cy = unit[3] + int(h * 0.055)
    cta_text = _draw_tracked(draw, (ox + 18, cy), REQUIRED_FACTS["cta"], cta_font, IVORY, tracking=240, anchor="lt")
    cta = (cta_text[0] - 18, cta_text[1] - 11, cta_text[2] + 18, cta_text[3] + 11)
    draw.rectangle(cta, outline=GOLD, width=1)

    closure = _draw_tracked(
        draw,
        (w // 2, int(h * 0.915)),
        APPROVED_BOTTOM_COPY,
        closure_font,
        IVORY,
        tracking=320,
        anchor="mt",
    )
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
    return {
        "schema": "ApprovedConcept3ReconstructionR1",
        "compositor": "ApprovedConcept3ReconstructionR1",
        "parent_asset_id": PARENT_61_ASSET_ID,
        "parent_spec_id": PARENT_61_SPEC_ID,
        "reconstruction_mode": "APPROVED_CONCEPT_3",
        "classified_as": None,
        "image": canvas.convert("RGB"),
        "fielded": fielded,
        "field_mask": applied["mask"],
        "graphic_fields": r1_field_specs(structure),
        "foundation": photo,
        "objects": objects,
        "groups_v2": groups_from_objects(objects, mode="APPROVED_CONCEPT_3"),
        "relationship_graph": concept3_relationship_graph(),
        "gravity": compositional_gravity(occupancy or {}, objects),
        "reading_flow": reading_flow(objects),
        "typography": campaign,
        "cta_treatment": "restrained_outlined_editorial",
        "pill": False,
        "button_rectangle": False,
        "real_logo": True,
        "bottom_copy_status": "APPROVED",
        "bottom_copy": APPROVED_BOTTOM_COPY,
        "canvas": [w, h],
        "field_density": {"darken": density["darken"], "charcoal_mix": density["charcoal_mix"], "ref_luma": density["ref_luma"], "prod_luma": density["prod_luma"]},
    }


def box_area(bounds: dict[str, Any] | None) -> float:
    if not isinstance(bounds, dict):
        return 0.0
    return max(0.0, float(bounds.get("w") or 0) * float(bounds.get("h") or 0))


def visual_mass_match(concept: Image.Image, r1: Image.Image, structure: dict[str, Any], objects: dict[str, Any], field_mask: Image.Image) -> dict[str, Any]:
    ref_mask = dark_field_mask_from_concept(concept)
    groups = structure.get("groups") or {}
    concept_mass = {
        "brand_mass": box_area(groups.get("brand_group")),
        "headline_mass": box_area(groups.get("campaign_group")),
        "offer_mass": box_area(groups.get("offer_group")),
        "CTA_mass": box_area(groups.get("action_group")),
        "graphic_field_mass": round(sum(1 for v in ref_mask.getdata() if v > 40) / max(1, ref_mask.size[0] * ref_mask.size[1]), 4),
    }
    concept_mass["photo_mass"] = round(1.0 - concept_mass["graphic_field_mass"], 4)
    concept_mass["negative_space_mass"] = round(max(0.0, 0.18), 4)
    r1_mass = {
        "brand_mass": box_area((objects.get("project_logo") or {}).get("bounds")) + box_area((objects.get("brand_caption") or {}).get("bounds")),
        "headline_mass": box_area((objects.get("headline") or {}).get("bounds")),
        "offer_mass": sum(box_area((objects.get(k) or {}).get("bounds")) for k in ("discount", "discount_label", "price", "unit_type")),
        "CTA_mass": box_area((objects.get("cta") or {}).get("bounds")),
        "graphic_field_mass": round(sum(1 for v in field_mask.convert("L").getdata() if v > 40) / max(1, field_mask.size[0] * field_mask.size[1]), 4),
    }
    r1_mass["photo_mass"] = round(1.0 - r1_mass["graphic_field_mass"], 4)
    r1_mass["negative_space_mass"] = round(max(0.0, 0.18), 4)
    deltas = {}
    for key in MASS_KEYS:
        a, b = float(concept_mass[key]), float(r1_mass[key])
        deltas[f"{key}_delta"] = round(abs(a - b) / max(a, 1e-6), 4)
    overall = sum(deltas[f"{k}_delta"] for k in ("headline_mass", "offer_mass", "graphic_field_mass", "photo_mass")) / 4
    gates = {
        "headline_mass_delta": deltas["headline_mass_delta"] <= 0.15,
        "offer_mass_delta": deltas["offer_mass_delta"] <= 0.15,
        "graphic_field_mass_delta": deltas["graphic_field_mass_delta"] <= 0.12,
        "overall_visual_mass_delta": overall <= 0.10,
    }
    return {
        "schema": "ConceptVisualMassMatcherV1",
        "concept": concept_mass,
        "r1": r1_mass,
        "deltas": {**deltas, "overall_visual_mass_delta": round(overall, 4)},
        "gates": gates,
        "pass": all(gates.values()),
        "canvas": [concept.size[0], concept.size[1]],
    }


def request_r1_critics(concept: Image.Image, production: Image.Image) -> tuple[dict[str, Any], dict[str, Any], int]:
    keys = list(FIDELITY_KEYS) + list(CRITIC_KEYS)
    content = [
        _text(
            "Compare APPROVED CONCEPT 3 (image 1) with R1 STRUCTURED RECONSTRUCTION (image 2). "
            "Do not compare against any 5.x design. Do not inflate scores. Score 0-10 for: "
            + ", ".join(keys)
            + ". architecture_fidelity means real Temple photography is used — do not penalize "
            "refusal of the draft's invented landmarks. Ask: does this still feel like the SAME "
            "professionally art-directed campaign? JSON only."
        ),
        _text("IMAGE 1 — APPROVED CONCEPT 3"),
        _img(concept, quality=82),
        _text("IMAGE 2 — R1 STRUCTURED MASTER"),
        _img(production, quality=82),
    ]
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 1800,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Art director scoring reconstruction fidelity. JSON only. Do not redesign."},
                {"role": "user", "content": content},
            ],
        }
    )
    scores = parsed.get("scores") if isinstance(parsed.get("scores"), dict) else parsed
    fidelity_scores = {k: round(_num(scores.get(k), 0), 2) for k in FIDELITY_KEYS}
    critic_scores = {k: round(_num(scores.get(k), 0), 2) for k in CRITIC_KEYS}
    failed = [k for k, floor in FIDELITY_FLOORS.items() if fidelity_scores.get(k, 0) < floor]
    critic_failed = [k for k, floor in CRITIC_FLOORS.items() if critic_scores.get(k, 0) < floor]
    fidelity = {
        "schema": "ApprovedConceptReconstructionFidelityV1",
        "scores": fidelity_scores,
        "floors": FIDELITY_FLOORS,
        "failed": failed,
        "pass": not failed,
        "notes": str(parsed.get("notes") or ""),
    }
    critic = {
        "schema": "FreshVisualCriticR1",
        "scores": critic_scores,
        "floors": CRITIC_FLOORS,
        "failed": critic_failed,
        "pass": not critic_failed,
        "same_campaign": bool(parsed.get("same_campaign") if "same_campaign" in parsed else not critic_failed),
        "notes": str(parsed.get("notes") or ""),
    }
    return fidelity, critic, calls
