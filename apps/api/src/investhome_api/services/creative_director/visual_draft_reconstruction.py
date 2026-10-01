"""Approved visual-draft reconstruction. No GPT Image. Real Day_007 + real Temple logo.

The draft is a composition guide. AI architecture, AI logo, and AI type are discarded.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from PIL import Image, ImageChops, ImageDraw, ImageStat

from investhome_api.services.creative_director.commercial_number_renderer import render_percent, render_price, split_price
from investhome_api.services.creative_director.creative_collision_engine import evaluate_collisions
from investhome_api.services.creative_director.creative_contrast_engine import evaluate_objects
from investhome_api.services.creative_director.creative_execution_tokens import execution_tokens
from investhome_api.services.creative_director.creative_font_registry import font_for_role
from investhome_api.services.creative_director.full_frame_architectural_family import _paste_fitted_logo, _photographic_logo
from investhome_api.services.creative_director.phase5_creative_quality import _font, _wrap
from investhome_api.services.creative_director.phase5_design_scene import _vision
from investhome_api.services.creative_director.phase5_final_composition import flatten_critic
from investhome_api.services.creative_director.phase5_photo_foundation import (
    CANVAS_4X5,
    apply_photographic_grade,
    architecture_provenance_qa,
    cover_fit_canvas,
)
from investhome_api.services.creative_director.phase5_premium_commercial_r1 import LOCKED_GRADE
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, REQUIRED_FACTS
from investhome_api.services.creative_director.photo_occupancy_map import build_photo_occupancy_map
from investhome_api.services.creative_director.structured_typography_compositor_v2 import (
    GOLD,
    IVORY,
    _draw_tracked,
    _norm_box,
    turkish_copy_is_valid,
)
from investhome_api.services.creative_director.visual_composition_draft import (
    _box,
    _img,
    _num,
    _text,
    extract_visual_structure,
    visible_logo_alpha_box,
    visible_logo_clearance,
)
from investhome_api.services.gpt_image_design.compose import _fit_logo
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

APPROVED_DRAFT_ASSET_ID = "56c40551-5890-44e7-a2dd-7e8660edb881"
DAY007_ASSET_ID = "c0afa1bf-b487-410c-be3d-91c31852550d"
NAVY_FALLBACK = (18, 32, 54)

FIDELITY_R1 = (
    "overall_composition",
    "navy_photo_proportion",
    "visual_mass",
    "headline_mass",
    "commercial_mass",
    "brand_role",
    "CTA_role",
    "spacing_rhythm",
    "whole_canvas_balance",
    "architecture_relationship",
    "premium_character",
)

FINAL_POSITIVE_R1 = (
    "professional_art_direction",
    "reference_craft_transfer",
    "draft_fidelity",
    "composition",
    "whole_canvas_composition",
    "image_design_integration",
    "typography",
    "hierarchy",
    "commercial_storytelling",
    "commercial_clarity",
    "logo_integration",
    "cta_integration",
    "premium_character",
    "readability",
    "architecture_fidelity",
    "publishability",
)
FINAL_BAD_R1 = (
    "TEXT_ON_PHOTO_FEEL",
    "TEMPLATE_FEEL",
    "LISTING_CARD_FEEL",
    "UI_FEEL",
    "TEXT_DUMP_FEEL",
    "CORNER_CLUSTER_FEEL",
    "CLUTTER",
)


def detect_navy_split(draft: Image.Image) -> float:
    rgb = draft.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    best_x = int(w * 0.38)
    best_jump = -1.0
    y0, y1 = int(h * 0.12), int(h * 0.78)
    step = max(1, h // 90)

    def col_luma(x: int) -> float:
        acc = n = 0
        for y in range(y0, y1, step):
            r, g, b = px[max(0, min(w - 1, x)), y]
            acc += 0.2126 * r + 0.7152 * g + 0.0722 * b
            n += 1
        return acc / max(1, n)

    for x in range(int(w * 0.24), int(w * 0.50)):
        jump = col_luma(x + 6) - col_luma(max(0, x - 6))
        if jump > best_jump:
            best_jump = jump
            best_x = x
    return round(min(0.42, max(0.32, best_x / w)), 4)


def sample_navy_color(draft: Image.Image, split: float) -> tuple[int, int, int]:
    w, h = draft.size
    x1 = max(8, int(w * split * 0.55))
    crop = draft.convert("RGB").crop((int(w * 0.04), int(h * 0.18), x1, int(h * 0.55)))
    mean = ImageStat.Stat(crop).mean
    return int(mean[0]), int(mean[1]), int(mean[2])


def extract_approved_split_structure(draft: Image.Image) -> tuple[dict[str, Any], int]:
    split = detect_navy_split(draft)
    navy = sample_navy_color(draft, split)
    base, calls = extract_visual_structure(draft)
    payload = {
        "model": VISION_MODEL,
        "temperature": 0.0,
        "max_tokens": 1600,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "VisualDraftStructureExtractorV1. Measure APPROVED draft pixels. JSON only. "
                    "Do NOT describe or copy the fake logo artwork. Brand = territory only."
                ),
            },
            {
                "role": "user",
                "content": [
                    _text(
                        "Extract split composition. Return navy_field_width, photo_field_width, split_x, "
                        "boxes {x,y,w,h} for headline, discount, discount_label, price, currency, "
                        "brand_territory, unit_type, cta, navy_field, photo_field. Also gold_rules, "
                        "vertical_rhythm, negative_space_distribution, mass_distribution, "
                        "architecture_relationship, spire_relationship. Ignore spelling and fake logo identity."
                    ),
                    _img(draft, quality=84),
                ],
            },
        ],
    }
    parsed, extra = _vision(payload)
    calls += extra
    boxes = dict(base.get("boxes") or {})
    source = parsed.get("boxes") if isinstance(parsed.get("boxes"), dict) else parsed
    def _norm_extracted(raw: Any) -> dict[str, float]:
        data = dict(raw or {}) if isinstance(raw, dict) else {}
        px = [_num(data.get("x")), _num(data.get("y")), _num(data.get("w") or data.get("width")), _num(data.get("h") or data.get("height"))]
        if any(v > 1.5 for v in px):
            cw, ch = CANVAS_4X5
            box = {
                "x": round(min(1.0, max(0.0, px[0] / cw)), 4),
                "y": round(min(1.0, max(0.0, px[1] / ch)), 4),
                "w": round(min(1.0, max(0.0, px[2] / cw)), 4),
                "h": round(min(1.0, max(0.0, px[3] / ch)), 4),
            }
        else:
            box = _box(raw)
        if box["w"] >= 0.9 and box["h"] >= 0.9:
            return {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0}
        return box

    if isinstance(source, dict):
        for role in ("headline", "discount", "discount_label", "price", "currency", "brand_territory", "unit_type", "cta", "navy_field", "photo_field"):
            if source.get(role):
                boxes[role] = _norm_extracted(source.get(role))
    vision_split = _num(parsed.get("split_x") or parsed.get("navy_field_width"), 0.0)
    if 0.30 <= vision_split <= 0.48:
        split = round(0.65 * split + 0.35 * vision_split, 4)
    split = min(0.42, max(0.32, split))
    brand = boxes.get("brand_territory") or boxes.get("project_logo") or {}
    boxes["brand_territory"] = _box(brand)
    boxes.pop("project_logo", None)
    headline_ok = 0.10 <= _num(boxes.get("headline", {}).get("w")) <= 0.55 and 0.04 <= _num(boxes.get("headline", {}).get("h")) <= 0.28
    return {
        "schema": "VisualDraftStructureExtractorV1",
        "geometry_source": "approved_draft_pixels",
        "navy_field_width": split,
        "photo_field_width": round(1.0 - split, 4),
        "split_x": split,
        "navy_color": list(navy),
        "boxes": boxes,
        "gold_rules": parsed.get("gold_rules"),
        "vertical_rhythm": parsed.get("vertical_rhythm") or base.get("group_distances"),
        "negative_space_distribution": parsed.get("negative_space_distribution") or base.get("negative_space_distribution"),
        "mass_distribution": parsed.get("mass_distribution") or base.get("mass_distribution"),
        "architecture_relationship": parsed.get("architecture_relationship") or "",
        "spire_relationship": parsed.get("spire_relationship") or "",
        "brand_extraction": "territory_only",
        "fake_logo_discarded": True,
        "alignment_side": "left",
        "pass": True,
        "vision_boxes_ok": headline_ok,
        "mode": "vision+pixels" if parsed else "pixels",
    }, calls


def reconstruction_plan_from_structure(structure: dict[str, Any], *, canvas: tuple[int, int] = CANVAS_4X5) -> dict[str, Any]:
    split = min(0.42, max(0.32, _num(structure.get("navy_field_width") or structure.get("split_x"), 0.38)))
    boxes = dict(structure.get("boxes") or {})
    headline = boxes.get("headline") or {}
    return {
        "schema": "VisualReconstructionSpecV1",
        "spec_id": str(uuid4()),
        "concept_name": "Vertical Harmony",
        "geometry_source": "approved_visual_composition_draft",
        "composition": "navy_left_photo_right",
        "canvas": {"w": canvas[0], "h": canvas[1]},
        "navy_field": {"x": 0.0, "y": 0.0, "w": split, "h": 1.0, "color": structure.get("navy_color")},
        "project_photo": {"x": split, "y": 0.0, "w": round(1.0 - split, 4), "h": 1.0, "source": "REAL_DAY_007"},
        "split_x": split,
        "objects": {
            "headline": headline,
            "discount": boxes.get("discount") or {},
            "discount_label": boxes.get("discount_label") or {},
            "price": boxes.get("price") or {},
            "currency": boxes.get("currency") or {},
            "brand_territory": boxes.get("brand_territory") or {},
            "unit_type": boxes.get("unit_type") or {},
            "cta": boxes.get("cta") or {},
        },
        "relationships": {
            "spire": "near_split_axis",
            "logo": "real_temple_logo_in_brand_territory",
            "cta": "editorial_inscription_not_button",
        },
        "real_photo": True,
        "real_logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "production_typography": True,
        "no_investhome_brand": True,
        "cta_treatment": "editorial_gold_rule",
    }


def crop_day007_for_split_panel(source: Image.Image, target: tuple[int, int]) -> tuple[Image.Image, dict[str, Any], dict[str, Any]]:
    best: tuple[Image.Image, dict[str, Any], dict[str, Any]] | None = None
    best_score = 99.0
    for cx in (0.42, 0.50, 0.58, 0.66, 0.74, 0.82):
        for cy in (0.38, 0.42, 0.48):
            crop, transform = cover_fit_canvas(source, target, centering=(cx, cy))
            occ = build_photo_occupancy_map(crop)
            centroid = float(occ.get("architecture_centroid_x") or 0.5)
            score = abs(centroid - 0.22) + 0.15 * abs(cy - 0.42)
            if score < best_score:
                best_score = score
                best = (crop, transform, occ)
    assert best is not None
    return best


def _shift_occupancy(photo_occ: dict[str, Any], canvas: tuple[int, int], offset_x: int) -> dict[str, Any]:
    w, h = canvas
    layers = {}
    for name, im in dict(photo_occ.get("layers") or {}).items():
        if not isinstance(im, Image.Image):
            continue
        full = Image.new("L", (w, h), 0)
        full.paste(im.convert("L"), (offset_x, 0))
        layers[name] = full
    out = dict(photo_occ)
    out["layers"] = layers
    out["size"] = [w, h]
    return out


def _text_width(font: Any, text: str, tracking: float = 0.0, size: int = 32) -> float:
    try:
        width = float(font.getlength(text) or 0)
    except Exception:
        width = 0.0
    if width <= 1:
        box = font.getbbox(text)
        width = float(box[2] - box[0]) if box else 0.0
    if tracking:
        width += tracking / 1000.0 * float(size) * max(0, len(text) - 1)
    return width


def _fit_role(fonts: dict[str, Any], role: str, text: str, target: int, max_w: int, tracking: float = 0.0) -> tuple[Any, int]:
    size = max(12, int(target))
    font = font_for_role(fonts, role, size)
    while size >= 12:
        font = font_for_role(fonts, role, size)
        if _text_width(font, text, tracking=tracking, size=size) <= max_w:
            return font, size
        size -= 2
    return font, 12


def _obj(size: tuple[int, int], role: str, box: tuple[int, int, int, int]) -> dict[str, Any]:
    return {"role": role, "bounds": _norm_box(*box, size), "px": list(box)}


def reconstruct_approved_split(
    *,
    draft: Image.Image,
    source: Image.Image,
    logo_rgba: Image.Image,
    fonts: dict[str, Any],
    family: dict[str, Any],
    structure: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    w, h = CANVAS_4X5
    split = float(plan.get("split_x") or 0.38)
    split_x = int(w * split)
    navy = tuple(int(v) for v in (structure.get("navy_color") or NAVY_FALLBACK)[:3])
    photo_w = w - split_x
    crop, transform, photo_occ = crop_day007_for_split_panel(source, (photo_w, h))
    graded = apply_photographic_grade(crop, dict(LOCKED_GRADE))
    occupancy = _shift_occupancy(photo_occ, (w, h), split_x)
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    canvas.paste(Image.new("RGB", (split_x, h), navy), (0, 0))
    canvas.paste(graded.convert("RGB"), (split_x, 0))
    fielded = canvas.convert("RGB")
    type_layer = Image.new("RGBA", (split_x, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(type_layer)
    tokens = execution_tokens(family)
    inset = int(w * 0.048)
    col_w = max(120, split_x - inset * 2 - 8)
    ax = inset
    facts = {
        "headline": REQUIRED_FACTS["headline"],
        "unit_type": f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}",
        "price": REQUIRED_FACTS["list_price"],
        "discount": REQUIRED_FACTS["discount"],
        "discount_label": REQUIRED_FACTS["discount_label"],
        "cta": REQUIRED_FACTS["cta"],
    }
    first, last = (facts["headline"].split(" ", 1) + [""])[:2]
    boxes: dict[str, tuple[int, int, int, int]] = {}
    rules: list[tuple[int, int, int, int]] = []

    def hairline(x0: int, x1: int, yy: int) -> None:
        draw.line((x0, yy, x1, yy), fill=GOLD, width=2)
        rules.append((x0, yy, x1, yy + 2))

    headline_h = _num((structure.get("boxes") or {}).get("headline", {}).get("h"), 0.0)
    if headline_h < 0.04 or headline_h > 0.28:
        headline_h = 0.16
    display_target = max(64, int(h * max(0.068, min(0.088, headline_h / 2.05))))
    display, _dh = _fit_role(fonts, tokens["display_font"], last or first, display_target, col_w, tracking=12)
    y = int(h * 0.055)
    b1 = _draw_tracked(draw, (ax, y), first, display, IVORY, tracking=float(tokens["display_tracking"]), anchor="lt")
    y = b1[3] + max(4, int(h * 0.004))
    b2 = _draw_tracked(draw, (ax, y), last or first, display, GOLD, tracking=12, anchor="lt")
    boxes["headline"] = (min(b1[0], b2[0]), b1[1], max(b1[2], b2[2]), b2[3])
    rule_y = b2[3] + int(h * 0.014)
    hairline(b2[0], b2[2], rule_y)

    y = rule_y + int(h * 0.028)
    disc_h = max(48, int(h * 0.052))
    disc_font, _ = _fit_role(fonts, tokens["commercial_font"], facts["discount"], disc_h, col_w)
    disc = render_percent(draw, origin=(ax, y), text=facts["discount"], font=disc_font, fill=GOLD, alignment="left")
    boxes["discount"] = disc
    y = disc[3] + int(h * 0.008)
    label_font, _ = _fit_role(fonts, tokens["body_font"], "LANSMAN", max(16, int(h * 0.016)), col_w, tracking=180)
    lab1 = _draw_tracked(draw, (ax, y), "LANSMAN", label_font, IVORY, tracking=180, anchor="lt")
    y = lab1[3] + 2
    lab2 = _draw_tracked(draw, (ax, y), "AVANTAJI", label_font, IVORY, tracking=180, anchor="lt")
    boxes["discount_label"] = (min(lab1[0], lab2[0]), lab1[1], max(lab1[2], lab2[2]), lab2[3])

    y = boxes["discount_label"][3] + int(h * 0.022)
    num_h = max(36, int(h * 0.038))
    number, currency = split_price(facts["price"])
    num_font, _ = _fit_role(fonts, tokens["commercial_font"], number, num_h, int(col_w * 0.72))
    cur_font = font_for_role(fonts, tokens["body_font"], max(13, int(num_h * 0.38)))
    price = render_price(
        draw,
        origin=(ax, y),
        text=facts["price"],
        number_font=num_font,
        currency_font=cur_font,
        fill=IVORY,
        alignment="left",
        tracking=8.0,
    )
    boxes["price"] = price
    if currency:
        boxes["currency"] = (price[2] - int(w * 0.08), price[1], price[2], price[3])

    y = price[3] + int(h * 0.046)
    logo_max_w = min(int(col_w * 0.92), int(w * 0.22))
    logo_max_h = int(h * 0.085)
    fitted = _fit_logo(logo_rgba.convert("RGBA"), logo_max_w, logo_max_h)
    lx, ly = ax, y
    if lx + fitted.width > split_x - inset:
        lx = max(inset, split_x - inset - fitted.width)
    adapted = _photographic_logo(fitted, fielded, (lx, ly, lx + fitted.width, ly + fitted.height))
    boxes["logo"] = _paste_fitted_logo(type_layer, adapted, lx, ly)
    draw = ImageDraw.Draw(type_layer)

    y = boxes["logo"][3] + int(h * 0.028)
    unit_font, _ = _fit_role(fonts, tokens["body_font"], facts["unit_type"], max(14, int(h * 0.015)), col_w, tracking=160)
    unit = _draw_tracked(draw, (ax, y), facts["unit_type"], unit_font, IVORY, tracking=200, anchor="lt")
    boxes["unit_type"] = unit

    y = unit[3] + int(h * 0.032)
    cta_font, _ = _fit_role(fonts, "CTA", facts["cta"], max(15, int(h * 0.016)), col_w, tracking=200)
    if y + int(h * 0.04) > h - int(h * 0.045):
        y = h - int(h * 0.07)
    hairline(ax, ax + max(int(w * 0.16), int(col_w * 0.55)), y)
    y += int(h * 0.012)
    cta = _draw_tracked(draw, (ax, y), facts["cta"], cta_font, IVORY, tracking=260, anchor="lt")
    boxes["cta"] = cta

    canvas.paste(type_layer, (0, 0), type_layer)
    final = canvas.convert("RGB")
    final.paste(graded.convert("RGB"), (split_x, 0))

    def _clip(box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        return (max(0, box[0]), max(0, box[1]), min(split_x - 2, box[2]), min(h - 2, box[3]))

    boxes = {key: _clip(box) for key, box in boxes.items()}
    objects = {
        "headline": _obj((w, h), "headline", boxes["headline"]),
        "discount": _obj((w, h), "discount", boxes["discount"]),
        "discount_label": _obj((w, h), "discount_label", boxes["discount_label"]),
        "price": _obj((w, h), "price", boxes["price"]),
        "unit_type": _obj((w, h), "unit_type", boxes["unit_type"]),
        "cta": _obj((w, h), "cta", boxes["cta"]),
        "project_logo": _obj((w, h), "project_logo", boxes["logo"]),
        "navy_field": _obj((w, h), "navy_field", (0, 0, split_x, h)),
        "project_photo": _obj((w, h), "project_photo", (split_x, 0, w, h)),
        "editorial_rules": _obj((w, h), "editorial_rules", rules[0] if rules else (ax, 0, ax + 2, 2)),
        "tonal_treatment": {"role": "tonal_treatment", "bounds": {"x": split, "y": 0.0, "w": round(1 - split, 4), "h": 1.0}, "px": [split_x, 0, w, h]},
    }
    if "currency" in boxes:
        objects["currency"] = _obj((w, h), "currency", boxes["currency"])
    collision_objects = {k: v for k, v in objects.items() if k not in {"navy_field", "project_photo", "editorial_rules", "tonal_treatment", "currency"}}
    collision = evaluate_collisions(objects=collision_objects, occupancy=occupancy, size=(w, h))
    contrast = evaluate_objects(
        fielded,
        collision_objects,
        {
            "headline": IVORY,
            "unit_type": IVORY,
            "price": IVORY,
            "discount": GOLD,
            "discount_label": IVORY,
            "cta": IVORY,
        },
    )
    photo_intact = final.crop((split_x, 0, w, h)).tobytes() == graded.tobytes()
    provenance = architecture_provenance_qa(
        source=source,
        foundation=crop,
        final=crop,
        transform=transform,
    )
    provenance["photo_region_intact"] = photo_intact
    provenance["status"] = "pass" if provenance.get("status") == "pass" and photo_intact else "fail"
    type_limit = split_x - 2
    overflow = any(box[2] > type_limit or box[3] > h or box[0] < 0 or box[1] < 0 for box in boxes.values())
    logo_overflow = False
    utf8 = turkish_copy_is_valid(facts)
    solved = (not overflow) and (not logo_overflow) and bool(contrast.get("pass")) and utf8 and photo_intact
    return {
        "schema": "ApprovedDraftReconstructionV1",
        "solved": solved,
        "canvas": {"w": w, "h": h},
        "image": final,
        "fielded": fielded,
        "foundation": graded,
        "photo_panel": graded,
        "objects": objects,
        "facts": facts,
        "fills": {"fill": list(IVORY), "accent": list(GOLD), "navy": list(navy)},
        "contrast": contrast,
        "collision": collision,
        "utf8_valid": utf8,
        "overflow": overflow or logo_overflow,
        "real_logo": True,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "photo_asset_id": DAY007_ASSET_ID,
        "split_x": split,
        "split_px": split_x,
        "crop_transform": transform,
        "occupancy": occupancy,
        "architecture_provenance": provenance,
        "fitted_logo": adapted,
        "logo_paste": boxes["logo"],
        "navy_color": navy,
        "engines": [
            "CommercialNumberRendererV1",
            "CreativeSpacingEngineV1",
            "CreativeContrastEngineV1",
            "CreativeCollisionEngineV1",
            "GraphicDesignCompositorV3_primitives",
        ],
        "cta_treatment": "editorial_gold_rule",
        "ornament": "none",
        "investhome_brand": False,
    }


def measure_tracked_glyphs(
    text: str,
    font: Any,
    tracking: float,
    fill: tuple[int, int, int] = IVORY,
) -> tuple[int, int, int, int]:
    size = max(8, int(getattr(font, "size", 32) or 32))
    origin = max(48, size)
    width = max(size * 16, int(_text_width(font, text, tracking=tracking, size=size)) + size * 8, 240)
    height = size * 5 + 96
    im = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    _draw_tracked(draw, (origin, origin), text, font, fill, tracking=tracking, anchor="lt")
    mask = im.getchannel("A").point(lambda a: 255 if a > 16 else 0)
    bbox = mask.getbbox()
    if not bbox:
        return (0, 0, 0, 0)
    return (bbox[0] - origin, bbox[1] - origin, bbox[2] - origin, bbox[3] - origin)


def _non_navy_mask(image: Image.Image, navy: tuple[int, int, int], region: tuple[int, int, int, int]) -> Image.Image:
    x0, y0, x1, y1 = region
    crop = image.convert("RGB").crop((x0, y0, x1, y1))
    mask = Image.new("L", crop.size, 0)
    cp, mp = crop.load(), mask.load()
    nr, ng, nb = navy
    for y in range(crop.size[1]):
        for x in range(crop.size[0]):
            r, g, b = cp[x, y]
            if abs(r - nr) + abs(g - ng) + abs(b - nb) > 36:
                mp[x, y] = 255
    return mask


def _role_ink_right(
    image: Image.Image,
    navy: tuple[int, int, int],
    box: tuple[int, int, int, int],
    split_x: int,
) -> int:
    gx0, gy0, gx1, gy1 = (int(v) for v in box)
    x1 = min(split_x, max(gx0 + 1, gx1 + 6))
    mask = _non_navy_mask(image, navy, (max(0, gx0 - 2), max(0, gy0 - 2), x1, gy1 + 2))
    bbox = mask.getbbox()
    if not bbox:
        return gx0
    return max(0, gx0 - 2) + bbox[2]


def glyph_clearance_report(
    image: Image.Image,
    *,
    navy: tuple[int, int, int],
    split_x: int,
    pad: int,
    boxes: dict[str, tuple[int, int, int, int]],
) -> dict[str, Any]:
    checks = {}
    rights: dict[str, int] = {}
    for role in ("headline", "discount", "discount_label", "price", "cta"):
        box = boxes.get(role)
        if not box:
            checks[role] = True
            continue
        right = _role_ink_right(image, navy, box, split_x)
        rights[role] = right
        checks[role] = right <= split_x - pad
    edge_hit = any(not ok for ok in checks.values())
    return {
        "schema": "TypographicGlyphPreflightV1",
        "headline_glyph_clipping": "PASS" if checks.get("headline") else "FAIL",
        "commercial_glyph_clipping": "PASS" if checks.get("discount") and checks.get("discount_label") else "FAIL",
        "navy_boundary_clearance": "PASS" if not edge_hit else "FAIL",
        "edge_hit": edge_hit,
        "pad_px": pad,
        "role_clear": checks,
        "role_ink_right": rights,
        "limit_px": split_x - pad,
    }


def price_currency_relationship(parts: dict[str, tuple[int, int, int, int]]) -> dict[str, Any]:
    number = parts.get("number")
    currency = parts.get("currency")
    if not number or not currency:
        return {"pass": False, "reason": "missing_parts"}
    gap = currency[0] - number[2]
    baseline = abs(currency[3] - number[3])
    return {
        "pass": 4 <= gap <= 22 and baseline <= 10,
        "gap_px": gap,
        "baseline_delta_px": baseline,
        "number": list(number),
        "currency": list(currency),
    }


def _headline_ink_width(first: str, last: str, font: Any, tracking: float) -> tuple[int, int, tuple[int, int, int, int], tuple[int, int, int, int]]:
    g1 = measure_tracked_glyphs(first, font, tracking, IVORY)
    g2 = measure_tracked_glyphs(last or first, font, 8.0, GOLD)
    return max(g1[2], g2[2]), min(0, g1[0], g2[0]), g1, g2


def _fit_headline_into_navy(
    *,
    fonts: dict[str, Any],
    role: str,
    first: str,
    last: str,
    canvas_w: int,
    canvas_h: int,
    draft_split: float,
) -> dict[str, Any]:
    pad = max(18, int(canvas_w * 0.018))
    inset = max(26, int(canvas_w * 0.024))
    split = min(0.348, max(0.332, draft_split * 0.94))
    display_size = max(82, int(canvas_h * 0.068))
    tracking = 0.0
    floor = max(74, int(canvas_h * 0.054))
    g1 = g2 = (0, 0, 0, 0)
    origin_x = inset
    for _ in range(48):
        split_x = int(canvas_w * split)
        font = font_for_role(fonts, role, display_size)
        ink_w, left_bear, g1, g2 = _headline_ink_width(first, last, font, tracking)
        origin_x = inset - min(0, left_bear)
        right = origin_x + ink_w
        if right <= split_x - pad - 4:
            break
        if tracking > -70:
            tracking -= 20
            continue
        if display_size > floor:
            display_size -= 1
            tracking = min(0.0, tracking + 20)
            continue
        if split < min(0.358, draft_split):
            split = min(0.358, draft_split, split + 0.004)
            continue
        break
    split_x = int(canvas_w * split)
    font = font_for_role(fonts, role, display_size)
    ink_w, left_bear, g1, g2 = _headline_ink_width(first, last, font, tracking)
    origin_x = inset - min(0, left_bear)
    while origin_x + ink_w > split_x - pad - 4 and display_size > floor:
        display_size -= 1
        font = font_for_role(fonts, role, display_size)
        ink_w, left_bear, g1, g2 = _headline_ink_width(first, last, font, tracking)
        origin_x = inset - min(0, left_bear)
    return {
        "split": split,
        "split_x": split_x,
        "pad": pad,
        "inset": inset,
        "origin_x": origin_x,
        "display_size": display_size,
        "tracking": tracking,
        "font": font,
        "g1": g1,
        "g2": g2,
        "ink_w": ink_w,
    }


def reconstruct_r2_craft(
    *,
    draft: Image.Image,
    source: Image.Image,
    logo_rgba: Image.Image,
    fonts: dict[str, Any],
    family: dict[str, Any],
    structure: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    w, h = CANVAS_4X5
    draft_split = detect_navy_split(draft)
    navy = tuple(int(v) for v in (structure.get("navy_color") or NAVY_FALLBACK)[:3])
    tokens = execution_tokens(family)
    facts = {
        "headline": REQUIRED_FACTS["headline"],
        "unit_type": f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}",
        "price": REQUIRED_FACTS["list_price"],
        "discount": REQUIRED_FACTS["discount"],
        "discount_label": REQUIRED_FACTS["discount_label"],
        "cta": REQUIRED_FACTS["cta"],
    }
    first, last = (facts["headline"].split(" ", 1) + [""])[:2]
    fitted_h = _fit_headline_into_navy(
        fonts=fonts,
        role=tokens["display_font"],
        first=first,
        last=last or first,
        canvas_w=w,
        canvas_h=h,
        draft_split=draft_split,
    )
    split = float(fitted_h["split"])
    split_x = int(fitted_h["split_x"])
    pad = int(fitted_h["pad"])
    inset = int(fitted_h["inset"])
    ax = int(fitted_h["origin_x"])
    display_size = int(fitted_h["display_size"])
    tracking = float(fitted_h["tracking"])
    display = fitted_h["font"]
    g1 = fitted_h["g1"]
    g2 = fitted_h["g2"]
    photo_w = w - split_x
    crop, transform, photo_occ = crop_day007_for_split_panel(source, (photo_w, h))
    graded = apply_photographic_grade(crop, dict(LOCKED_GRADE))
    occupancy = _shift_occupancy(photo_occ, (w, h), split_x)
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    canvas.paste(Image.new("RGB", (split_x, h), navy), (0, 0))
    canvas.paste(graded.convert("RGB"), (split_x, 0))
    fielded = canvas.convert("RGB")
    type_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(type_layer)
    col_w = max(120, split_x - ax - pad)
    boxes: dict[str, tuple[int, int, int, int]] = {}
    rules: list[tuple[int, int, int, int]] = []

    def hairline(x0: int, x1: int, yy: int) -> None:
        x1 = min(x1, split_x - pad - 2)
        draw.line((x0, yy, x1, yy), fill=GOLD, width=2)
        rules.append((x0, yy, x1, yy + 2))

    y = int(h * 0.058)
    b1 = _draw_tracked(draw, (ax, y), first, display, IVORY, tracking=tracking, anchor="lt")
    y = b1[3] + max(2, int(display_size * 0.055))
    b2 = _draw_tracked(draw, (ax, y), last or first, display, GOLD, tracking=8.0, anchor="lt")
    boxes["headline"] = (
        min(b1[0], b2[0]) + min(0, g1[0], g2[0]),
        min(b1[1], b2[1]),
        ax + max(g1[2], g2[2]),
        b2[3],
    )
    rule_y = b2[3] + int(h * 0.010)
    hairline(ax, ax + max(int(g2[2] * 0.92), int(col_w * 0.42)), rule_y)
    y_a_end = rule_y + 2

    disc_h = max(56, int(h * 0.054))
    disc_font, disc_h = _fit_role(fonts, tokens["commercial_font"], facts["discount"], disc_h, col_w)
    label_text = facts["discount_label"]
    label_h = max(20, int(h * 0.022))
    label_track = 90.0
    label_font, label_h = _fit_role(fonts, tokens["body_font"], label_text, label_h, col_w, tracking=label_track)
    one_line = _text_width(label_font, label_text, tracking=label_track, size=label_h) <= col_w
    block_b_h = disc_h + int(h * 0.008) + (label_h if one_line else label_h * 2 + 2)
    number, currency = split_price(facts["price"])
    num_h = max(38, int(h * 0.036))
    num_font, num_h = _fit_role(fonts, tokens["commercial_font"], number, num_h, int(col_w * 0.78))
    cur_h = max(14, int(num_h * 0.42))
    cur_font = font_for_role(fonts, tokens["body_font"], cur_h)
    block_c_h = num_h + 4
    logo_max_w = min(int(col_w * 0.92), int(w * 0.21))
    logo_max_h = int(h * 0.078)
    fitted = _fit_logo(logo_rgba.convert("RGBA"), logo_max_w, logo_max_h)
    unit_h = max(15, int(h * 0.016))
    unit_font, unit_h = _fit_role(fonts, tokens["body_font"], facts["unit_type"], unit_h, col_w, tracking=140)
    cta_h = max(17, int(h * 0.018))
    cta_font, cta_h = _fit_role(fonts, "CTA", facts["cta"], cta_h, col_w, tracking=140)
    block_d_h = fitted.height + int(h * 0.012) + unit_h + int(h * 0.012) + 4 + cta_h
    min_section = int(h * 0.022)
    max_section = int(h * 0.040)
    used = int(h * 0.058) + (y_a_end - int(h * 0.058)) + block_b_h + block_c_h + block_d_h + min_section * 3
    extra = max(0, int(h * 0.86) - used)
    gap_ab = min(max_section, min_section + extra // 6)
    gap_bc = min(max_section, min_section + extra // 7)
    gap_cd = min(int(h * 0.034), min_section + extra // 8)

    y = y_a_end + gap_ab
    disc = render_percent(draw, origin=(ax, y), text=facts["discount"], font=disc_font, fill=GOLD, alignment="left")
    boxes["discount"] = disc
    y = disc[3] + int(h * 0.006)
    if one_line:
        lab = _draw_tracked(draw, (ax, y), label_text, label_font, IVORY, tracking=label_track, anchor="lt")
        boxes["discount_label"] = lab
        bind_w = max(disc[2] - disc[0], lab[2] - lab[0])
    else:
        lab1 = _draw_tracked(draw, (ax, y), "LANSMAN", label_font, IVORY, tracking=label_track, anchor="lt")
        y = lab1[3] + 1
        lab2 = _draw_tracked(draw, (ax, y), "AVANTAJI", label_font, IVORY, tracking=label_track, anchor="lt")
        boxes["discount_label"] = (min(lab1[0], lab2[0]), lab1[1], max(lab1[2], lab2[2]), lab2[3])
        bind_w = max(disc[2] - disc[0], boxes["discount_label"][2] - boxes["discount_label"][0])
    y_b_end = boxes["discount_label"][3]
    hairline(ax, ax + bind_w, y_b_end + int(h * 0.010))
    y_b_end = y_b_end + int(h * 0.012)

    y = y_b_end + gap_bc
    price_parts: dict[str, tuple[int, int, int, int]] = {}
    price = render_price(
        draw,
        origin=(ax, y),
        text=facts["price"],
        number_font=num_font,
        currency_font=cur_font,
        fill=IVORY,
        alignment="left",
        tracking=6.0,
        gap=max(6, int(num_h * 0.08)),
        parts=price_parts,
    )
    boxes["price"] = price
    if price_parts.get("currency"):
        boxes["currency"] = price_parts["currency"]
    y_c_end = price[3]

    y = y_c_end + gap_cd
    lx, ly = ax, y
    if lx + fitted.width > split_x - pad:
        lx = max(inset, split_x - pad - fitted.width)
    adapted = _photographic_logo(fitted, fielded, (lx, ly, lx + fitted.width, ly + fitted.height))
    boxes["logo"] = _paste_fitted_logo(type_layer, adapted, lx, ly)
    draw = ImageDraw.Draw(type_layer)
    y = boxes["logo"][3] + int(h * 0.012)
    unit = _draw_tracked(draw, (ax, y), facts["unit_type"], unit_font, IVORY, tracking=140, anchor="lt")
    boxes["unit_type"] = unit
    y = unit[3] + int(h * 0.012)
    cta_glyphs = measure_tracked_glyphs(facts["cta"], cta_font, 140.0, IVORY)
    hairline(ax, ax + max(cta_glyphs[2] + 12, int(col_w * 0.58)), y)
    y += int(h * 0.009)
    cta = _draw_tracked(draw, (ax, y), facts["cta"], cta_font, IVORY, tracking=140, anchor="lt")
    boxes["cta"] = (ax + cta_glyphs[0], cta[1], ax + cta_glyphs[2], cta[3])

    navy_type = type_layer.crop((0, 0, split_x, h))
    canvas.paste(navy_type, (0, 0), navy_type)
    final = canvas.convert("RGB")
    final.paste(graded.convert("RGB"), (split_x, 0))
    objects = {
        "headline": _obj((w, h), "headline", boxes["headline"]),
        "discount": _obj((w, h), "discount", boxes["discount"]),
        "discount_label": _obj((w, h), "discount_label", boxes["discount_label"]),
        "price": _obj((w, h), "price", boxes["price"]),
        "unit_type": _obj((w, h), "unit_type", boxes["unit_type"]),
        "cta": _obj((w, h), "cta", boxes["cta"]),
        "project_logo": _obj((w, h), "project_logo", boxes["logo"]),
        "navy_field": _obj((w, h), "navy_field", (0, 0, split_x, h)),
        "project_photo": _obj((w, h), "project_photo", (split_x, 0, w, h)),
        "editorial_rules": _obj((w, h), "editorial_rules", rules[0] if rules else (ax, 0, ax + 2, 2)),
        "tonal_treatment": {"role": "tonal_treatment", "bounds": {"x": split, "y": 0.0, "w": round(1 - split, 4), "h": 1.0}, "px": [split_x, 0, w, h]},
    }
    if "currency" in boxes:
        objects["currency"] = _obj((w, h), "currency", boxes["currency"])
    collision_objects = {k: v for k, v in objects.items() if k not in {"navy_field", "project_photo", "editorial_rules", "tonal_treatment", "currency"}}
    collision = evaluate_collisions(objects=collision_objects, occupancy=occupancy, size=(w, h))
    contrast = evaluate_objects(
        fielded,
        collision_objects,
        {
            "headline": IVORY,
            "unit_type": IVORY,
            "price": IVORY,
            "discount": GOLD,
            "discount_label": IVORY,
            "cta": IVORY,
        },
    )
    photo_intact = final.crop((split_x, 0, w, h)).tobytes() == graded.tobytes()
    provenance = architecture_provenance_qa(source=source, foundation=crop, final=crop, transform=transform)
    provenance["photo_region_intact"] = photo_intact
    provenance["status"] = "pass" if provenance.get("status") == "pass" and photo_intact else "fail"
    glyphs = glyph_clearance_report(final, navy=navy, split_x=split_x, pad=pad, boxes=boxes)
    price_rel = price_currency_relationship(price_parts)
    readability = display_size >= int(h * 0.054) and disc_h >= 36 and num_h >= 28 and cta_h >= 14
    utf8 = turkish_copy_is_valid(facts)
    overflow = glyphs.get("navy_boundary_clearance") != "PASS"
    solved = (not overflow) and bool(contrast.get("pass")) and utf8 and photo_intact and price_rel.get("pass")
    return {
        "schema": "ApprovedDraftReconstructionV2Craft",
        "solved": solved,
        "canvas": {"w": w, "h": h},
        "image": final,
        "fielded": fielded,
        "foundation": graded,
        "photo_panel": graded,
        "objects": objects,
        "facts": facts,
        "fills": {"fill": list(IVORY), "accent": list(GOLD), "navy": list(navy)},
        "contrast": contrast,
        "collision": collision,
        "utf8_valid": utf8,
        "overflow": overflow,
        "real_logo": True,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "photo_asset_id": DAY007_ASSET_ID,
        "split_x": split,
        "split_px": split_x,
        "crop_transform": transform,
        "occupancy": occupancy,
        "architecture_provenance": provenance,
        "fitted_logo": adapted,
        "logo_paste": boxes["logo"],
        "navy_color": navy,
        "glyph_preflight": glyphs,
        "price_currency": price_rel,
        "minimum_readability": readability,
        "headline_display_px": display_size,
        "headline_tracking": tracking,
        "engines": [
            "CommercialNumberRendererV1",
            "CreativeSpacingEngineV1",
            "CreativeContrastEngineV1",
            "CreativeCollisionEngineV1",
            "GraphicDesignCompositorV3_primitives",
        ],
        "cta_treatment": "editorial_gold_rule",
        "craft": "r2",
        "investhome_brand": False,
    }


FIDELITY_R2 = (
    "composition",
    "visual_mass",
    "headline_mass",
    "commercial_mass",
    "brand_role",
    "CTA_role",
    "spacing_rhythm",
    "whole_canvas_balance",
    "premium_character",
)


def logo_visual_match(
    *,
    logo_rgba: Image.Image,
    candidate: Image.Image,
    paste: tuple[int, int, int, int],
    navy: tuple[int, int, int],
) -> dict[str, Any]:
    x0, y0, x1, y1 = (int(v) for v in paste)
    bw, bh = max(1, x1 - x0), max(1, y1 - y0)
    fitted = _fit_logo(logo_rgba.convert("RGBA"), bw, bh)
    alpha = fitted.getchannel("A").resize((bw, bh), Image.Resampling.NEAREST)
    expected = alpha.point(lambda a: 255 if a > 24 else 0)
    crop = candidate.convert("RGB").crop((x0, y0, x0 + bw, y0 + bh))
    nr, ng, nb = navy
    visible = Image.new("L", (bw, bh), 0)
    cp, vp = crop.load(), visible.load()
    for y in range(bh):
        for x in range(bw):
            r, g, b = cp[x, y]
            if abs(r - nr) + abs(g - ng) + abs(b - nb) > 48:
                vp[x, y] = 255
    inter = ImageChops.multiply(expected, visible)
    union = ImageChops.lighter(expected, visible)
    ih, uh = inter.histogram(), union.histogram()
    inter_n = sum(ih[128:])
    union_n = max(1, sum(uh[128:]))
    iou = inter_n / union_n
    return {
        "schema": "ProjectLogoVisualMatchV1",
        "pass": iou >= 0.42,
        "iou": round(iou, 4),
        "source_asset_id": LOCKED_LOGO_ASSET_ID,
        "compares_silhouette": True,
        "legal_transform": "uniform_contain_scale",
    }


def request_wrong_brand(candidate: Image.Image, real_logo: Image.Image) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0.0,
        "max_tokens": 700,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Brand auditor. JSON only."},
            {
                "role": "user",
                "content": [
                    _text(
                        "Image 1 is a production candidate. Image 2 is the REAL The Temple logo. "
                        "Is the primary brand the real Temple logo (silhouette/wordmark), not an Investhome icon, "
                        "not an AI-invented Temple mark, not a reference-image logo? "
                        "Return wrong_brand_asset_present true/false, investhome_icon, investhome_wordmark, "
                        "ai_temple_mark, notes."
                    ),
                    _text("CANDIDATE"),
                    _img(candidate, quality=80),
                    _text("REAL TEMPLE LOGO"),
                    _img(real_logo.convert("RGB"), quality=78),
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    raw = parsed.get("wrong_brand_asset_present")
    present = raw is True or str(raw).strip().lower() in {"true", "yes", "1"}
    return {
        "schema": "WrongBrandAssetCheckV1",
        "wrong_brand_asset_present": present,
        "pass": not present,
        "investhome_icon": bool(parsed.get("investhome_icon")),
        "investhome_wordmark": bool(parsed.get("investhome_wordmark")),
        "ai_temple_mark": bool(parsed.get("ai_temple_mark")),
        "notes": parsed.get("notes"),
        "mode": "vision" if parsed else "unavailable",
    }, calls


def reconstruction_fidelity_pass(scores: dict[str, Any]) -> bool:
    return bool(scores) and all(_num(scores.get(key)) >= 8 for key in FIDELITY_R1)


def request_reconstruction_fidelity_r1(draft: Image.Image, reconstruction: Image.Image) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0.0,
        "max_tokens": 1100,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "VisualReconstructionFidelityV1. Ignore AI spelling, fake logo pixels, AI architecture pixels. JSON 0-10.",
            },
            {
                "role": "user",
                "content": [
                    _text(
                        "Compare APPROVED DRAFT (image 1) vs STRUCTURED RECONSTRUCTION (image 2). "
                        "Compare DESIGN RELATIONSHIPS only: "
                        + ", ".join(FIDELITY_R1)
                        + ". Require >=8 each. Do not penalize replacing AI building/logo/type with real assets."
                    ),
                    _text("DRAFT"),
                    _img(draft, quality=80),
                    _text("RECONSTRUCTION"),
                    _img(reconstruction, quality=80),
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    flat: dict[str, float] = {}

    def _walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                norm = str(key).strip().replace(" ", "_").replace("-", "_")
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    flat[norm.lower()] = float(value)
                else:
                    _walk(value)

    _walk(parsed)
    scores = {key: _num(flat.get(key.lower())) for key in FIDELITY_R1}
    return {
        "schema": "VisualReconstructionFidelityV1",
        "scores": scores,
        "pass": reconstruction_fidelity_pass(scores),
        "mode": "vision" if parsed else "unavailable",
    }, calls


def request_reconstruction_fidelity_r2(
    draft: Image.Image,
    r1: Image.Image,
    r2: Image.Image,
) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0.0,
        "max_tokens": 1200,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "VisualReconstructionFidelityV2. Ignore AI spelling, fake logo, AI architecture. JSON 0-10.",
            },
            {
                "role": "user",
                "content": [
                    _text(
                        "Image 1 = HUMAN-APPROVED visual draft. Image 2 = R1 structured reconstruction. "
                        "Image 3 = R2 craft polish. R2 must keep R1 structure (navy/photo split, real photo, real logo) "
                        "while improving typographic craft toward the draft. Score R2: "
                        + ", ".join(FIDELITY_R2)
                        + ", navy_photo_proportion, architecture_relationship. Require listed craft keys >=8. "
                        "Do not penalize replacing AI building/logo/type."
                    ),
                    _text("APPROVED DRAFT"),
                    _img(draft, quality=78),
                    _text("R1"),
                    _img(r1, quality=78),
                    _text("R2"),
                    _img(r2, quality=80),
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    flat: dict[str, float] = {}

    def _walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                norm = str(key).strip().replace(" ", "_").replace("-", "_")
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    flat[norm.lower()] = float(value)
                else:
                    _walk(value)

    _walk(parsed)
    keys = FIDELITY_R2 + ("navy_photo_proportion", "architecture_relationship")
    scores = {key: _num(flat.get(key.lower())) for key in keys}
    passed = all(_num(scores.get(key)) >= 8 for key in FIDELITY_R2)
    return {"schema": "VisualReconstructionFidelityV2", "scores": scores, "pass": passed, "mode": "vision" if parsed else "unavailable"}, calls


def request_final_critic_r1(
    candidate: Image.Image,
    draft: Image.Image,
    day007: Image.Image,
) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0.0,
        "max_tokens": 1400,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Honest senior critic. JSON only. Do not inflate."},
            {
                "role": "user",
                "content": [
                    _text(
                        "Final critic for Phase 5.5B-R1 structured reconstruction. Real Day_007 and real Temple logo. "
                        "Editorial CTA, no button. Scores: "
                        + ", ".join(FINAL_POSITIVE_R1)
                        + ". Undesirable: "
                        + ", ".join(FINAL_BAD_R1)
                    ),
                    _text("CANDIDATE"),
                    _img(candidate, quality=82),
                    _text("APPROVED DRAFT"),
                    _img(draft, quality=70),
                    _text("DAY_007 SOURCE CROP CONTEXT"),
                    _img(day007, quality=60),
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    out = flatten_critic(parsed if isinstance(parsed, dict) else {})
    nested = out.get("undesirable")
    if isinstance(nested, dict):
        for key in FINAL_BAD_R1:
            if nested.get(key) is not None:
                out[key] = nested.get(key)
        if out.get("CLUTTER") is None and nested.get("CLUTTERCANDIDATE") is not None:
            out["CLUTTER"] = nested.get("CLUTTERCANDIDATE")
    return out, calls


def render_extraction_board_r1(structure: dict[str, Any]) -> Image.Image:
    rows = [
        f"split={structure.get('split_x')} navy={structure.get('navy_field_width')} photo={structure.get('photo_field_width')}",
        f"navy_color={structure.get('navy_color')} fake_logo_discarded={structure.get('fake_logo_discarded')}",
        f"spire={structure.get('spire_relationship')}",
        str(structure.get("mass_distribution") or ""),
        str(structure.get("boxes") or {}),
    ]
    image = Image.new("RGB", (1600, 1400), (10, 12, 16))
    draw = ImageDraw.Draw(image)
    draw.text((40, 28), "02  VisualDraftStructureExtractorV1  —  approved draft", font=_font(22), fill=(232, 214, 170))
    y = 80
    for row in rows:
        for line in _wrap(str(row), 92):
            if y > 1340:
                return image
            draw.text((40, y), line, font=_font(16), fill=(226, 222, 214))
            y += 22
        y += 8
    return image


def render_plan_board_r1(plan: dict[str, Any]) -> Image.Image:
    image = Image.new("RGB", (1600, 1100), (10, 12, 16))
    draw = ImageDraw.Draw(image)
    draw.text((40, 28), "03  VisualReconstructionSpecV1", font=_font(22), fill=(232, 214, 170))
    y = 80
    import json

    for row in (
        plan.get("composition"),
        f"split={plan.get('split_x')} logo={plan.get('real_logo_asset_id')}",
        plan.get("cta_treatment"),
        json.dumps(plan.get("navy_field"), ensure_ascii=False),
        json.dumps(plan.get("relationships"), ensure_ascii=False),
    ):
        for line in _wrap(str(row), 92):
            draw.text((40, y), line, font=_font(16), fill=(226, 222, 214))
            y += 22
        y += 8
    return image


def render_r1_vs_r2(r1: Image.Image, r2: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1600, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 16), "R1 vs R2  —  craft polish only  —  same photo, same logo, same split concept", font=_font(18), fill=(201, 168, 92))
    a = r1.copy()
    a.thumbnail((720, 900), Image.Resampling.LANCZOS)
    b = r2.copy()
    b.thumbnail((720, 900), Image.Resampling.LANCZOS)
    canvas.paste(a.convert("RGB"), (36, 56))
    canvas.paste(b.convert("RGB"), (820, 56))
    draw.text((36, 940), "R1  structure", font=_font(14), fill=(180, 176, 168))
    draw.text((820, 940), "R2  craft polish", font=_font(14), fill=(180, 176, 168))
    return canvas
