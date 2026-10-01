"""AdaptiveCompositionEngineV1 — rebuild family logic around the actual photograph.

Does not transform normalized reference coordinates onto Day_004.
GPT Image is not used. Architecture pixels remain source pixels.
"""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

from investhome_api.services.creative_director.commercial_offer_composer import (
    measure_production_copy,
    offer_layout,
)
from investhome_api.services.creative_director.creative_collision_engine import evaluate_collisions
from investhome_api.services.creative_director.creative_contrast_engine import approved_fills, evaluate_objects, sample_background
from investhome_api.services.creative_director.creative_family_adapter import _ramp_horizontal, _ramp_vertical, _union_l
from investhome_api.services.creative_director.family_composition_constraints import family_constraints
from investhome_api.services.creative_director.phase5_photo_foundation import (
    CANVAS_4X5,
    apply_photographic_grade,
    cover_fit_canvas,
)
from investhome_api.services.creative_director.phase5_premium_commercial_r1 import LOCKED_GRADE
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.photo_occupancy_map import build_photo_occupancy_map
from investhome_api.services.creative_director.structured_typography_compositor_v2 import (
    GOLD,
    INK,
    IVORY,
    _draw_tracked,
    _hex,
    _objects,
    _place_logo,
    turkish_copy_is_valid,
)

MAX_SOLVE_ITERS = 10
EDGE = 0.055


def _allow_mask(hard: Image.Image, blur: float = 22.0) -> Image.Image:
    inv = hard.convert("L").point(lambda v: 0 if v > 40 else 255)
    feather = inv.filter(ImageFilter.GaussianBlur(radius=blur))
    return ImageChops.multiply(feather, inv)


def _apply_edge_field(
    photo: Image.Image,
    occupancy: dict[str, Any],
    *,
    color: tuple[int, int, int],
    mode: str,
    strength: int = 220,
) -> Image.Image:
    src = photo.convert("RGB")
    hard = (occupancy.get("layers") or {}).get("hard_protected")
    allow = _allow_mask(hard if isinstance(hard, Image.Image) else Image.new("L", src.size, 0))
    if mode in {"EXPANDED_FIELD", "NORMAL"}:
        right = _ramp_horizontal(src.size, 0.50, 0.82, 0, strength)
        top = _ramp_vertical(src.size, 0.0, 0.30, int(strength * 0.85), 0)
        ramp = _union_l(right, top)
    elif mode == "MIRRORED":
        left = _ramp_horizontal(src.size, 0.18, 0.50, strength, 0)
        top = _ramp_vertical(src.size, 0.0, 0.30, int(strength * 0.85), 0)
        ramp = _union_l(left, top)
    elif mode == "HORIZONTAL_SPLIT":
        ramp = _ramp_vertical(src.size, 0.0, 0.40, strength, 0)
    else:
        ramp = _ramp_vertical(src.size, 0.0, 0.26, int(strength * 0.7), 0)
    mask = ImageChops.multiply(ramp, allow).filter(ImageFilter.GaussianBlur(radius=10))
    panel = Image.new("RGB", src.size, color)
    return Image.composite(panel, src, mask)


def _apply_sky_wash(photo: Image.Image, occupancy: dict[str, Any], color: tuple[int, int, int]) -> Image.Image:
    src = photo.convert("RGB")
    hard = (occupancy.get("layers") or {}).get("hard_protected")
    allow = _allow_mask(hard if isinstance(hard, Image.Image) else Image.new("L", src.size, 0), blur=18)
    ramp = _ramp_vertical(src.size, 0.0, 0.34, 200, 0)
    mask = ImageChops.multiply(ramp, allow).filter(ImageFilter.GaussianBlur(radius=12))
    wash = Image.new("RGB", src.size, color)
    return Image.composite(wash, src, mask)


def _apply_local_plane(photo: Image.Image, occupancy: dict[str, Any], region: dict[str, float]) -> Image.Image:
    src = photo.convert("RGB")
    w, h = src.size
    hard = (occupancy.get("layers") or {}).get("hard_protected")
    allow = _allow_mask(hard if isinstance(hard, Image.Image) else Image.new("L", src.size, 0), blur=16)
    dark = ImageEnhance.Brightness(src).enhance(0.46)
    mask = Image.new("L", src.size, 0)
    x0 = int(float(region.get("x") or 0.08) * w)
    y0 = int(float(region.get("y") or 0.06) * h)
    x1 = int((float(region.get("x") or 0.08) + float(region.get("w") or 0.4)) * w)
    y1 = int((float(region.get("y") or 0.06) + float(region.get("h") or 0.46)) * h)
    ImageDraw.Draw(mask).rounded_rectangle((x0 - 12, y0 - 10, x1 + 18, y1 + 16), radius=36, fill=175)
    mask = ImageChops.multiply(mask.filter(ImageFilter.GaussianBlur(radius=32)), allow)
    return Image.composite(dark, src, mask)


def occupancy_aware_crop(source: Image.Image, family: dict[str, Any]) -> tuple[Image.Image, dict[str, Any], dict[str, Any]]:
    family_id = str(family.get("family_id") or "")
    from investhome_api.services.creative_director.photo_family_eligibility import _dark_quiet_plane

    ys = {
        "EDITORIAL_DARK_FIELD": (0.24, 0.32, 0.40),
        "SKY_EDITORIAL": (0.20, 0.28, 0.36),
        "TYPE_IN_PLANE": (0.34, 0.44, 0.52),
        "MINIMAL_TOP_FIELD": (0.22, 0.32, 0.62),
    }.get(family_id, (0.30, 0.42, 0.52))
    xs = (0.38, 0.50, 0.58) if family_id == "EDITORIAL_DARK_FIELD" else (0.55,)
    best: tuple[float, Image.Image, dict[str, Any], dict[str, Any]] | None = None
    for x in xs:
        for y in ys:
            crop, transform = cover_fit_canvas(source, CANVAS_4X5, centering=(float(x), float(y)))
            graded = apply_photographic_grade(crop, dict(LOCKED_GRADE))
            occ = build_photo_occupancy_map(graded)
            sky = float(occ.get("sky_area") or 0)
            text = float((occ.get("coverage") or {}).get("text_safe") or 0)
            ext = float((occ.get("coverage") or {}).get("graphically_extendable") or 0)
            hard = float((occ.get("coverage") or {}).get("hard_protected") or 0)
            plane = _dark_quiet_plane(graded, occ)
            occ["dark_plane"] = plane
            score = sky * 2.2 + text * 1.4 + ext * 0.8
            if family_id == "TYPE_IN_PLANE":
                score = text * 2.0 + sky * 1.1
            if family_id == "EDITORIAL_DARK_FIELD":
                score = float(plane.get("area") or 0) * 8.0 + float(plane.get("height") or 0) * 3.0 + float(plane.get("width") or 0)
                if plane.get("edge"):
                    score += 2.0
                score -= hard * 0.4
            if hard < 0.08:
                score -= 1.0
            if best is None or score > best[0]:
                best = (
                    score,
                    graded,
                    {
                        "centering": [float(x), float(y)],
                        "source_crop": transform.get("source_crop"),
                        "canvas": list(CANVAS_4X5),
                        "score": round(score, 4),
                    },
                    occ,
                )
    assert best is not None
    return best[1], best[2], best[3]


def _hard_clear_column(occupancy: dict[str, Any], plane: dict[str, Any], size: tuple[int, int]) -> dict[str, float]:
    w, h = size
    x0 = max(0, int(float(plane.get("x") or 0.04) * w))
    y0 = max(0, int(float(plane.get("y") or 0.04) * h))
    y1 = min(h, int((float(plane.get("y") or 0.04) + float(plane.get("height") or plane.get("h") or 0.4)) * h))
    x1 = min(w, x0 + int(min(0.42, float(plane.get("width") or 0.42)) * w))
    hard = (occupancy.get("layers") or {}).get("hard_protected")
    if isinstance(hard, Image.Image) and x1 > x0 + 8 and y1 > y0 + 8:
        hp = hard.convert("L")
        min_w = int(0.18 * w)
        while x1 - x0 > min_w:
            crop = hp.crop((x0, y0, x1, y1))
            hist = crop.histogram()
            total = max(1, sum(hist))
            if sum(hist[96:]) / total < 0.045:
                break
            x1 -= max(8, int(0.02 * w))
    return {
        "x": round(x0 / w, 4),
        "y": round(y0 / h, 4),
        "w": round(max(0.16, (x1 - x0) / w), 4),
        "h": round(max(0.22, (y1 - y0) / h), 4),
        "area": float(plane.get("area") or 0),
        "field_source": "dark_quiet_plane",
        "side": "left" if x0 / w < 0.22 else "right",
    }


def _region_or(occupancy: dict[str, Any], *names: str) -> dict[str, float]:
    regions = occupancy.get("regions") or {}
    for name in names:
        box = regions.get(name)
        if isinstance(box, dict) and float(box.get("w") or 0) >= 0.16:
            return dict(box)
    return {"x": 0.08, "y": 0.06, "w": 0.34, "h": 0.36}


def _pocket(occupancy: dict[str, Any], side: str) -> dict[str, float]:
    pockets = occupancy.get("pockets") or {}
    box = pockets.get(side)
    if isinstance(box, dict) and float(box.get("w") or 0) >= 0.14:
        return dict(box)
    return _region_or(occupancy, f"text_{side}", f"sky_{side}", "graphically_extendable")


def _origin_for_mode(
    *,
    occupancy: dict[str, Any],
    constraints: dict[str, Any],
    mode: str,
    size: tuple[int, int],
    stack_h: int,
    max_line_w: int,
) -> tuple[int, int, str, dict[str, float]]:
    w, h = size
    family_id = str(constraints.get("family_id") or "")
    inset = int(EDGE * w)
    alignment = str(constraints.get("default_alignment") or "right")
    if mode == "MIRRORED":
        alignment = str(constraints.get("mirror_alignment") or ("left" if alignment == "right" else "right"))
    side = "right" if alignment == "right" else "left"
    if family_id == "SKY_EDITORIAL" and mode != "MIRRORED":
        side = "left"
        alignment = "left"
    plane = occupancy.get("dark_plane") if isinstance(occupancy.get("dark_plane"), dict) else None
    if family_id == "EDITORIAL_DARK_FIELD" and isinstance(plane, dict) and float(plane.get("area") or 0) >= 0.12:
        region = _hard_clear_column(occupancy, plane, (w, h))
        alignment = "left" if region["side"] == "left" else "right"
        x0 = int(region["x"] * w)
        x1 = int((region["x"] + region["w"]) * w)
        y0 = int(region["y"] * h)
        y1 = int((region["y"] + region["h"]) * h)
        if alignment == "right":
            x = min(w - inset, x1 - 8)
        else:
            x = max(inset, x0 + 8)
        y = max(int(h * 0.04), y0 + 6)
        if y + stack_h > y1 - 8:
            y = max(int(h * 0.04), y1 - 8 - stack_h)
        region = {**region, "usable_width": max(0.12, (x1 - x0) / w), "usable_height": max(0.10, (y1 - y0) / h)}
        _ = max_line_w
        return x, y, alignment, region
    region = _pocket(occupancy, side)
    if float(region.get("w") or 0) < 0.16:
        other = "left" if side == "right" else "right"
        region = _pocket(occupancy, other)
        side = other
        alignment = "left" if side == "left" else "right"
    x0 = int(float(region.get("x") or 0.06) * w)
    x1 = int((float(region.get("x") or 0.06) + float(region.get("w") or 0.3)) * w)
    y0 = int(float(region.get("y") or 0.05) * h)
    y1 = int((float(region.get("y") or 0.05) + float(region.get("h") or 0.22)) * h)
    if alignment == "right":
        x = min(w - inset, x1 - 8)
    else:
        x = max(inset, x0 + 8)
    y = max(int(h * 0.04), y0 + 6)
    if y + stack_h > y1 - 8:
        y = max(int(h * 0.04), y1 - 8 - stack_h)
    region = {**region, "usable_width": max(0.12, (x1 - x0) / w), "usable_height": max(0.10, (y1 - y0) / h), "side": side}
    _ = max_line_w
    return x, y, alignment, region


def _stack_height(metrics: dict[str, Any], family_id: str, spacing: dict[str, Any], canvas_h: int) -> int:
    keys = ("headline_first", "headline_last", "unit_type", "price", "discount", "discount_label", "cta")
    total = sum(int(metrics[k]["height"]) for k in keys if k in metrics)
    total += int(canvas_h * (float(spacing.get("after_headline") or 0.02) + float(spacing.get("after_unit") or 0.016) + float(spacing.get("after_price") or 0.012) + float(spacing.get("after_offer") or 0.04) + 0.04))
    return total


def _draw_lockup(
    canvas: Image.Image,
    *,
    family: dict[str, Any],
    origin: tuple[int, int],
    alignment: str,
    metrics: dict[str, Any],
    fills: dict[str, tuple[int, int, int]],
    occupancy: dict[str, Any],
    logo_rgba: Image.Image | None,
) -> dict[str, Any]:
    draw = ImageDraw.Draw(canvas)
    w, h = canvas.size
    family_id = str(family.get("family_id") or "")
    spacing = dict(family.get("spacing") or {})
    ox, y = origin
    fill = fills["fill"]
    accent = fills["accent"]
    boxes: dict[str, tuple[int, int, int, int]] = {}
    anchor = "rt" if alignment == "right" else "lt"

    def paint(metric_key: str, color: tuple[int, int, int], gap: float) -> tuple[int, int, int, int]:
        nonlocal y
        item = metrics[metric_key]
        box = _draw_tracked(
            draw,
            (ox, y),
            item["text"],
            item["font"],
            color,
            tracking=float(item.get("tracking") or 0),
            anchor=anchor,
        )
        y = box[3] + int(h * gap)
        return box

    if family_id == "EDITORIAL_DARK_FIELD":
        first = paint("headline_first", fill, 0.006)
        last = paint("headline_last", accent, 0.012)
        boxes["headline"] = (min(first[0], last[0]), first[1], max(first[2], last[2]), last[3])
        if alignment == "right":
            draw.line((last[0], y, ox, y), fill=accent, width=2)
        else:
            draw.line((ox, y, last[2], y), fill=accent, width=2)
        y += int(h * 0.016)
    elif family_id == "TYPE_IN_PLANE":
        first = paint("headline_first", accent, 0.004)
        last = paint("headline_last", fill, float(spacing.get("after_headline") or 0.018))
        boxes["headline"] = (min(first[0], last[0]), first[1], max(first[2], last[2]), last[3])
    else:
        first = paint("headline_first", fill, 0.005)
        last = paint("headline_last", fill, 0.012)
        boxes["headline"] = (min(first[0], last[0]), first[1], max(first[2], last[2]), last[3])
        if alignment == "right":
            draw.line((last[0], y, ox, y), fill=accent, width=2)
        else:
            draw.line((ox, y, min(ox + int(w * 0.22), last[2]), y), fill=accent, width=2)
        y += int(h * 0.016)

    offer = offer_layout(
        origin=(ox, y),
        alignment=alignment,
        metrics=metrics,
        spacing=spacing,
        canvas=canvas.size,
        family_id=family_id,
        include_headline=False,
    )
    for role, box in offer["boxes"].items():
        item = metrics[role]
        color = accent if role == "discount" else fill
        _draw_tracked(
            draw,
            (box[0], box[1]),
            item["text"],
            item["font"],
            color,
            tracking=float(item.get("tracking") or 0),
            anchor="lt",
        )
        boxes[role] = box
    y = int(offer["cursor_y"])
    cta_box = _draw_tracked(
        draw,
        (ox, y),
        metrics["cta"]["text"],
        metrics["cta"]["font"],
        fill,
        tracking=float(metrics["cta"].get("tracking") or 0),
        anchor="rt" if alignment == "right" else "lt",
    )
    boxes["cta"] = cta_box
    logo_box = _place_family_logo(canvas, logo_rgba, family, alignment, occupancy, boxes)
    boxes["logo"] = logo_box
    facts = {
        "headline": REQUIRED_FACTS["headline"],
        "unit_type": f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}",
        "price": REQUIRED_FACTS["list_price"],
        "discount": REQUIRED_FACTS["discount"],
        "discount_label": REQUIRED_FACTS["discount_label"],
        "cta": REQUIRED_FACTS["cta"],
    }
    objects = _objects(
        canvas.size,
        headline=boxes["headline"],
        unit=boxes["unit_type"],
        price=boxes["price"],
        discount=boxes["discount"],
        label=boxes["discount_label"],
        cta=boxes["cta"],
        logo=logo_box,
    )
    return {"objects": objects, "facts": facts, "offer": offer, "boxes": boxes, "alignment": alignment}


def _place_family_logo(
    canvas: Image.Image,
    logo_rgba: Image.Image | None,
    family: dict[str, Any],
    alignment: str,
    occupancy: dict[str, Any],
    boxes: dict[str, tuple[int, int, int, int]],
) -> tuple[int, int, int, int]:
    w, h = canvas.size
    bw, bh = int(w * min(0.16, float((family.get("brand") or {}).get("relative_scale") or 0.16))), int(h * 0.045)
    slot = str((family.get("brand") or {}).get("slot") or "bottom_of_column")
    hard = (occupancy.get("layers") or {}).get("collision_core") or (occupancy.get("layers") or {}).get("hard_protected")
    candidates: list[tuple[int, int]] = []
    cta = boxes.get("cta")
    if cta:
        if alignment == "right":
            candidates.append((cta[2] - bw, min(h - bh - 12, cta[3] + 18)))
        else:
            candidates.append((cta[0], min(h - bh - 12, cta[3] + 18)))
    if slot == "top_center":
        candidates.append(((w - bw) // 2, int(h * 0.03)))
    col = boxes.get("headline") or boxes.get("price")
    if col:
        if alignment == "right":
            candidates.append((col[2] - bw, int(h * 0.88)))
        else:
            candidates.append((col[0], int(h * 0.88)))
    candidates.append(((w - bw) // 2, int(h * 0.90)))
    candidates.append((int(w * 0.07), int(h * 0.88)))
    candidates.append((int(w * 0.72), int(h * 0.88)))
    from investhome_api.services.creative_director.creative_collision_engine import box_hits_hard

    for x, y in candidates:
        box = (x, y, x + bw, y + bh)
        if isinstance(hard, Image.Image) and box_hits_hard(hard, box, min_pixels=10):
            continue
        overlaps = False
        for role, other in boxes.items():
            if role in {"headline", "price", "cta", "discount"} and other:
                if not (box[2] <= other[0] or other[2] <= box[0] or box[3] <= other[1] or other[3] <= box[1]):
                    overlaps = True
                    break
        if overlaps:
            continue
        return _place_logo(canvas, logo_rgba, x, y, bw, bh)
    x, y = candidates[-1]
    return _place_logo(canvas, logo_rgba, x, y, bw, bh)


def _field_for_mode(
    foundation: Image.Image,
    occupancy: dict[str, Any],
    family: dict[str, Any],
    mode: str,
    region: dict[str, float],
) -> Image.Image:
    family_id = str(family.get("family_id") or "")
    color = _hex(str((family.get("graphic_devices") or {}).get("field_hex") or ""), (20, 24, 30))
    wash = _hex(str((family.get("graphic_devices") or {}).get("field_hex") or "#E8E2D6"), (232, 226, 214))
    if family_id == "SKY_EDITORIAL":
        return _apply_sky_wash(foundation, occupancy, wash)
    if family_id == "TYPE_IN_PLANE":
        return _apply_local_plane(foundation, occupancy, region)
    if family_id == "EDITORIAL_DARK_FIELD" and str(region.get("field_source") or "") == "dark_quiet_plane":
        return _apply_local_plane(foundation, occupancy, region)
    return _apply_edge_field(foundation, occupancy, color=color, mode=mode)


def _preflight(
    *,
    pack: dict[str, Any],
    occupancy: dict[str, Any],
    foundation: Image.Image,
    fielded: Image.Image,
    final: Image.Image,
    fonts: dict[str, Any],
    family: dict[str, Any],
    fills: dict[str, tuple[int, int, int]],
) -> dict[str, Any]:
    from investhome_api.services.creative_director.graphic_field_director import protected_pixels_unchanged

    objects = pack["objects"]
    facts = pack["facts"]
    collision = evaluate_collisions(objects=objects, occupancy=occupancy, size=final.size)
    colors = {
        "headline": fills["fill"] if str(family.get("family_id")) != "EDITORIAL_DARK_FIELD" else fills["fill"],
        "unit_type": fills["fill"],
        "price": fills["number"],
        "discount": fills["accent"],
        "discount_label": fills["fill"],
        "cta": fills["fill"],
    }
    contrast = evaluate_objects(fielded, objects, colors)
    hard = (occupancy.get("layers") or {}).get("collision_core") or (occupancy.get("layers") or {}).get("hard_protected")
    arch_ok = True
    if isinstance(hard, Image.Image):
        arch_ok = protected_pixels_unchanged(foundation, fielded, hard) and protected_pixels_unchanged(foundation, final, hard)
    offer = pack.get("offer") or {}
    hierarchy_ok = bool((offer.get("hierarchy") or {}).get("discount_not_tiny", True) and (offer.get("pass") if "pass" in offer else True))
    utf8_ok = turkish_copy_is_valid(facts)
    font_ok = bool((fonts.get("roles") or {}).get("DISPLAY_SERIF"))
    semantic = all(facts.get(k) for k in ("headline", "unit_type", "price", "discount", "discount_label", "cta"))
    checks = {
        "architecture_clearance": "PASS" if arch_ok and not any("protected_architecture" in h for h in collision["hits"]) else "FAIL",
        "text_collision": "PASS" if collision["pass"] else "FAIL",
        "logo_collision": "PASS" if "logo_vs_protected_architecture" not in collision["hits"] and "headline_vs_logo" not in collision["hits"] else "FAIL",
        "cta_collision": "PASS" if not any(h.startswith("cta_") for h in collision["hits"]) else "FAIL",
        "contrast": "PASS" if contrast["pass"] else "FAIL",
        "commercial_hierarchy": "PASS" if hierarchy_ok else "FAIL",
        "canvas_bounds": "PASS" if not any("canvas_edge" in h for h in collision["hits"]) else "FAIL",
        "utf8": "PASS" if utf8_ok else "FAIL",
        "font_availability": "PASS" if font_ok else "FAIL",
        "semantic_completeness": "PASS" if semantic else "FAIL",
    }
    return {
        "schema": "AdaptiveCompositionPreflightV1",
        "checks": checks,
        "pass": all(v == "PASS" for v in checks.values()),
        "collision": collision,
        "contrast": contrast,
        "architecture_pixels_unchanged": arch_ok,
        "utf8_valid": utf8_ok,
    }


def compose_adaptive(
    *,
    source: Image.Image,
    family: dict[str, Any],
    fonts: dict[str, Any],
    logo_rgba: Image.Image | None,
    protection: dict[str, Any] | None = None,
    scale_order: tuple[float, ...] | None = None,
) -> dict[str, Any]:
    family_id = str(family.get("family_id") or "")
    constraints = family_constraints(family_id)
    foundation, crop, occupancy = occupancy_aware_crop(source, family)
    if protection:
        occupancy_protection = dict(protection)
        occupancy_protection["occupancy_hard_l"] = (occupancy.get("layers") or {}).get("hard_protected")
    else:
        occupancy_protection = {"occupancy_hard_l": (occupancy.get("layers") or {}).get("hard_protected")}
    modes = list(constraints.get("flex_modes") or ["NORMAL"])
    if family_id == "EDITORIAL_DARK_FIELD" and isinstance(occupancy.get("dark_plane"), dict) and float(
        (occupancy.get("dark_plane") or {}).get("area") or 0
    ) >= 0.12:
        modes = ["MIRRORED", "VERTICAL_STACK", "COMPRESSED"]
    scales = list(scale_order) if scale_order else [0.64, 0.72, 0.82, 0.92]
    attempts: list[tuple[float, str]] = []
    for scale in scales:
        for mode in modes:
            attempts.append((scale, mode))
    last: dict[str, Any] | None = None
    history: list[dict[str, Any]] = []
    for idx, (scale, mode) in enumerate(attempts[:MAX_SOLVE_ITERS], start=1):
        metrics = measure_production_copy(fonts=fonts, family=family, canvas=foundation.size, scale=scale)
        spacing = dict(family.get("spacing") or {})
        if mode in {"COMPRESSED", "VERTICAL_STACK"}:
            spacing = {k: (float(v) * 0.55 if isinstance(v, (int, float)) else v) for k, v in spacing.items()}
        stack_h = _stack_height(metrics, family_id, spacing, foundation.size[1])
        ox, oy, alignment, region = _origin_for_mode(
            occupancy=occupancy,
            constraints=constraints,
            mode=mode,
            size=foundation.size,
            stack_h=stack_h,
            max_line_w=int(metrics["price"]["width"]),
        )
        usable = int(float(region.get("usable_width") or 0.28) * foundation.size[0])
        widest = max(
            int(metrics["headline_first"]["width"]),
            int(metrics["headline_last"]["width"]),
            int(metrics["price"]["width"]),
            int(metrics["discount_label"]["width"]),
        )
        last_iter = idx >= min(MAX_SOLVE_ITERS, len(attempts))
        if widest > usable - 6 and not last_iter:
            history.append({"iteration": idx, "flex_mode": mode, "scale": scale, "alignment": alignment, "preflight_pass": False, "failed": ["pocket_width"]})
            continue
        usable_h = int(float(region.get("usable_height") or 0.22) * foundation.size[1])
        if stack_h > usable_h - 8 and not last_iter:
            history.append({"iteration": idx, "flex_mode": mode, "scale": scale, "alignment": alignment, "preflight_pass": False, "failed": ["pocket_height"]})
            continue
        fielded = _field_for_mode(foundation, occupancy, family, mode, region)
        sample_box = (max(0, ox - 80), oy, min(foundation.size[0], ox + 80), oy + 80)
        bg = sample_background(fielded, sample_box)
        fills = approved_fills(family_id, bg, family)
        canvas = fielded.convert("RGBA")
        fam = dict(family)
        fam["spacing"] = spacing
        pack = _draw_lockup(
            canvas,
            family=fam,
            origin=(ox, oy),
            alignment=alignment,
            metrics=metrics,
            fills=fills,
            occupancy=occupancy,
            logo_rgba=logo_rgba,
        )
        final = canvas.convert("RGB")
        pocket_x1 = int((float(region.get("x") or 0) + float(region.get("w") or 1)) * foundation.size[0])
        pocket_y1 = int((float(region.get("y") or 0) + float(region.get("h") or 1)) * foundation.size[1])
        overflow = False
        for role, item in dict(pack.get("objects") or {}).items():
            if role == "project_logo":
                continue
            px = item.get("px")
            if isinstance(px, (list, tuple)) and len(px) == 4:
                if int(px[2]) > pocket_x1 + 6 or int(px[3]) > pocket_y1 + 6:
                    overflow = True
                    break
        preflight = _preflight(
            pack=pack,
            occupancy=occupancy,
            foundation=foundation,
            fielded=fielded,
            final=final,
            fonts=fonts,
            family=family,
            fills=fills,
        )
        if overflow:
            preflight = dict(preflight)
            checks = dict(preflight.get("checks") or {})
            checks["architecture_clearance"] = "FAIL"
            checks["text_collision"] = "FAIL"
            preflight["checks"] = checks
            preflight["pass"] = False
        attempt = {
            "iteration": idx,
            "flex_mode": mode,
            "scale": scale,
            "alignment": alignment,
            "preflight_pass": preflight["pass"],
            "failed": [k for k, v in preflight["checks"].items() if v != "PASS"],
        }
        history.append(attempt)
        last = {
            "schema": "AdaptiveCompositionPlanV1",
            "family_id": family_id,
            "flex_mode": mode,
            "scale": scale,
            "alignment": alignment,
            "origin": {"x": ox, "y": oy},
            "region": region,
            "constraints": constraints,
            "metrics": {k: {"width": v.get("width"), "height": v.get("height"), "text": v.get("text")} for k, v in metrics.items() if isinstance(v, dict) and "width" in v},
            "crop": crop,
            "occupancy": occupancy,
            "protection": occupancy_protection,
            "image": final,
            "foundation": foundation,
            "fielded": fielded,
            "objects": pack["objects"],
            "facts": pack["facts"],
            "offer": pack.get("offer"),
            "fills": {k: list(v) for k, v in fills.items()},
            "preflight": preflight,
            "solve_history": history,
            "iterations": idx,
        }
        if preflight["pass"]:
            last["solved"] = True
            return last
    assert last is not None
    last["solved"] = False
    return last
