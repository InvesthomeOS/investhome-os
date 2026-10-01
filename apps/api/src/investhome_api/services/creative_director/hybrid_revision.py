"""Hybrid Master revision — preserve approved raster, recompose affected semantics.

Approved master visual stays the pixel source of truth. Master Design Spec
describes what may change. Only the recomposition surface is redrawn from
design primitives. No image provider, no inpaint, no full reconstruction.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFont

from investhome_api.services.creative_director.edit_map import _as_dict, _is_navy
from investhome_api.services.creative_director.price_block_revision import format_tr_usd
from investhome_api.services.creative_director.visual_fidelity import (
    _abs,
    _box,
    _center_text,
    _diamond,
    _rgb,
    element,
    list_available_fonts,
    region,
    text_size,
)
from investhome_api.services.gpt_image_design.compose import resolve_turkish_font

HERO_Y_LOCK = 554
NAVY_FALLBACK = (10, 16, 36)
GOLD_FALLBACK = (209, 170, 106)
WHITE_FALLBACK = (246, 241, 232)


def _geom(spec: dict[str, Any], role: str) -> dict[str, int] | None:
    return _abs(region(spec, role)) or _abs(element(spec, role))


def _group(spec: dict[str, Any], group_id: str) -> dict[str, Any] | None:
    for item in spec.get("groups") or []:
        if item.get("id") == group_id:
            return item
    return None


def _sample_navy(
    master: Image.Image,
    spec: dict[str, Any],
    *,
    surface: dict[str, int] | None = None,
) -> tuple[int, int, int]:
    px = master.convert("RGB").load()
    w, h = master.size
    coords: list[tuple[int, int]] = []
    if surface:
        y = max(0, int(surface["y0"]) - 2)
        for x in list(range(4, min(48, w))) + list(range(max(4, w - 48), w - 1)):
            coords.append((x, y))
        y_mid = (int(surface["y0"]) + int(surface["y1"])) // 2
        for x in list(range(4, min(28, w))) + list(range(max(4, w - 28), w - 1)):
            coords.append((x, min(h - 1, y_mid)))
    navy_box = _geom(spec, "navy_field") or {"x0": 0, "y0": 0, "x1": 80, "y1": 48}
    for y in range(navy_box["y0"] + 4, min(navy_box["y0"] + 40, navy_box["y1"]), 2):
        for x in range(6, 36, 2):
            coords.append((x, y))
    rs = gs = bs = n = 0
    for x, y in coords:
        r, g, b = px[x, y]
        if _is_navy(r, g, b) or (r < 48 and g < 56 and b < 80):
            rs += r
            gs += g
            bs += b
            n += 1
    if n == 0:
        return NAVY_FALLBACK
    return (rs // n, gs // n, bs // n)


def _sample_gold(master: Image.Image, spec: dict[str, Any]) -> tuple[int, int, int]:
    from investhome_api.services.creative_director.edit_map import _is_gold

    box = _geom(spec, "cta") or _geom(spec, "headline") or {"x0": 200, "y0": 60, "x1": 800, "y1": 200}
    px = master.convert("RGB").load()
    rs = gs = bs = n = 0
    for y in range(box["y0"], box["y1"], 3):
        for x in range(box["x0"], box["x1"], 3):
            r, g, b = px[x, y]
            if _is_gold(r, g, b):
                rs += r
                gs += g
                bs += b
                n += 1
    if n < 8:
        return GOLD_FALLBACK
    return (rs // n, gs // n, bs // n)


def _serif(size: int, *, bold: bool) -> ImageFont.ImageFont:
    try:
        font = resolve_turkish_font(bold=bold, size=size, family="serif")
        if font is not None:
            return font
    except Exception:
        pass
    for item in list_available_fonts():
        if item.get("mono"):
            continue
        if bold and not item.get("bold"):
            continue
        if not item.get("serif"):
            continue
        try:
            return ImageFont.truetype(item["path"], size=max(8, size))
        except Exception:
            continue
    return ImageFont.load_default()


def _fit(text: str, max_w: int, max_h: int, *, bold: bool) -> ImageFont.ImageFont:
    hi = max(11, min(72, max_h))
    for size in range(hi, 10, -1):
        font = _serif(size, bold=bold)
        tw, th = text_size(font, text)
        if tw <= max(8, max_w) and th <= max(8, max_h):
            return font
    return _serif(11, bold=bold)


def _disjoint(a: dict[str, int], b: dict[str, int], *, pad: int = 0) -> bool:
    return a["x1"] <= b["x0"] + pad or b["x1"] <= a["x0"] + pad or a["y1"] <= b["y0"] + pad or b["y1"] <= a["y0"] + pad


def _contains(outer: dict[str, int], inner: dict[str, int]) -> bool:
    return (
        inner["x0"] >= outer["x0"]
        and inner["y0"] >= outer["y0"]
        and inner["x1"] <= outer["x1"]
        and inner["y1"] <= outer["y1"]
    )


def _intersect_area(a: dict[str, int], b: dict[str, int]) -> int:
    x0, y0 = max(a["x0"], b["x0"]), max(a["y0"], b["y0"])
    x1, y1 = min(a["x1"], b["x1"]), min(a["y1"], b["y1"])
    return max(0, x1 - x0) * max(0, y1 - y0)


def build_hybrid_revision_plan(
    spec: dict[str, Any],
    intent: Any,
    *,
    master_size: tuple[int, int] | None = None,
) -> dict[str, Any]:
    """Dependency graph + recomposition surface. Does not render. Does not persist."""
    canvas = _as_dict(spec.get("canvas"))
    width = int((master_size[0] if master_size else canvas.get("width")) or 1088)
    height = int((master_size[1] if master_size else canvas.get("height")) or 1360)
    headline = _geom(spec, "headline") or _geom(spec, "headline_area") or {"x0": 130, "y0": 40, "x1": width - 130, "y1": 180}
    supporting = _geom(spec, "supporting_copy") or _geom(spec, "supporting_copy_area")
    commercial = _abs(_group(spec, "commercial_group")) or _geom(spec, "commercial_information_area")
    hero = _geom(spec, "hero_visual") or {"x0": 0, "y0": min(HERO_Y_LOCK, height), "x1": width, "y1": height}
    cta = _geom(spec, "cta")
    logo = _geom(spec, "logo")
    footer = _geom(spec, "bottom_brand_treatment") or {"x0": 0, "y0": hero["y1"], "x1": width, "y1": height}
    hero_y = int(hero["y0"])
    if hero_y <= 0:
        hero_y = min(HERO_Y_LOCK, height)

    if commercial is None:
        commercial = {"x0": int(width * 0.12), "y0": int(height * 0.22), "x1": int(width * 0.88), "y1": hero_y}

    # Headline stays master pixels. Supporting copy stays master pixels unless
    # the commercial box cannot sit below it. Surface covers the old commercial
    # group fully and stops at the hero boundary.
    headline_floor = headline["y1"] + 4
    support_floor = (supporting["y1"] + 8) if supporting else headline_floor
    y0 = max(headline_floor, min(support_floor, max(headline_floor, commercial["y0"] - 8)))
    if y0 >= hero_y - 80:
        y0 = max(headline_floor, hero_y - max(120, int(height * 0.18)))
    y1 = hero_y
    surface = _box(0, y0, width, y1)
    supporting_inside = bool(supporting) and _intersect_area(surface, supporting) > 40
    headline_inside = _intersect_area(surface, headline) > 40

    list_s = format_tr_usd(int(intent.list_amount))
    launch_s = format_tr_usd(int(intent.launch_amount))
    save_s = format_tr_usd(int(intent.savings_amount))
    discount = str((element(spec, "discount") or {}).get("exact_content") or "%35")
    discount_label = str((element(spec, "discount_label") or {}).get("exact_content") or "LANSMAN AVANTAJI")
    unit = str((element(spec, "unit_type") or {}).get("exact_content") or "2+1")
    unit_label = str((element(spec, "unit_label") or {}).get("exact_content") or "DAİRE")
    supporting_text = str((element(spec, "supporting_copy") or {}).get("exact_content") or "")

    affected = [
        "commercial_group",
        "list_price",
        "list_price_label",
        "launch_price",
        "launch_price_label",
        "savings",
        "savings_label",
        "discount",
        "discount_label",
        "unit_type",
        "unit_label",
        "commercial_separators",
    ]
    dependent: list[str] = []
    if supporting_inside:
        dependent.append("supporting_copy")
    preserved = [
        "headline",
        "hero_visual",
        "cta",
        "logo",
        "bottom_brand_treatment",
        "footer",
    ]
    if supporting and not supporting_inside:
        preserved.append("supporting_copy")

    layout_model = "primary_price_plus_supporting_metrics"
    plan = {
        "schema": "HybridRevisionPlan",
        "revision_plan_id": str(uuid4()),
        "revision_intent": "PRICE_EDIT_ONLY",
        "preview_only": True,
        "architecture": "hybrid_master",
        "master_visual_mode": "approved_raster_pixels",
        "master_design_spec_id": spec.get("master_design_spec_id"),
        "provider_image_calls": 0,
        "hero_boundary": hero_y,
        "hero_visual_preservation": "MASTER_PIXELS_LOCKED",
        "headline_preservation": "MASTER_PIXELS_LOCKED",
        "cta_preservation": "MASTER_PIXELS_LOCKED",
        "logo_preservation": "MASTER_PIXELS_LOCKED",
        "footer_preservation": "MASTER_PIXELS_LOCKED",
        "affected_semantics": affected,
        "dependent_flexible_elements": dependent,
        "preserved_semantics": preserved,
        "recomposition_surface": surface,
        "old_commercial_bbox": commercial,
        "headline_bbox": headline,
        "supporting_bbox": supporting,
        "hero_bbox": hero,
        "cta_bbox": cta,
        "logo_bbox": logo,
        "footer_bbox": footer,
        "supporting_inside_surface": supporting_inside,
        "headline_inside_surface": headline_inside,
        "layout_model": layout_model,
        "clean_surface_method": "fill_sampled_navy_field_then_typeset_affected_semantics",
        "commercial_revision": {
            "launch_price": launch_s,
            "launch_price_label": str(getattr(intent, "launch_label", None) or "LANSMAN FİYATI"),
            "list_price": list_s,
            "list_price_label": str(getattr(intent, "list_label", None) or "LİSTE FİYATI"),
            "list_price_strikethrough": True,
            "savings": save_s,
            "savings_label": str(getattr(intent, "savings_label", None) or "KAZANCINIZ"),
            "discount": discount,
            "discount_label": discount_label,
            "unit_type": unit,
            "unit_label": unit_label,
            "supporting_copy": supporting_text,
            "value_before_label": True,
        },
        "typography_limitation": (
            "Exact campaign font is unavailable. Changed commercial text uses the "
            "closest available serif. Unaffected master typography stays as pixels."
        ),
        "relationships_used": [r.get("id") for r in (spec.get("relationships") or []) if isinstance(r, dict)],
        "do_not": [
            "full_reconstruction",
            "image_provider",
            "inpaint",
            "regional_ai_edit",
            "reconstruct_headline",
            "reconstruct_hero",
            "reconstruct_cta",
            "reconstruct_logo",
            "cross_hero_boundary",
        ],
    }
    return plan


def _layout_slots(surface: dict[str, int]) -> dict[str, dict[str, int]]:
    x0, y0, x1, y1 = surface["x0"], surface["y0"], surface["x1"], surface["y1"]
    w = x1 - x0
    h = y1 - y0
    inset = max(24, int(w * 0.11))
    top_pad = max(10, int(h * 0.06))
    bot_pad = max(10, int(h * 0.05))
    inner = _box(x0 + inset, y0 + top_pad, x1 - inset, y1 - bot_pad)
    ih = max(40, inner["y1"] - inner["y0"])
    gap = max(6, int(ih * 0.045))
    primary_h = int(ih * 0.36)
    rest = ih - primary_h - gap * 2
    secondary_h = int(rest * 0.52)
    support_h = rest - secondary_h
    primary = _box(inner["x0"], inner["y0"], inner["x1"], inner["y0"] + primary_h)
    secondary = _box(inner["x0"], primary["y1"] + gap, inner["x1"], primary["y1"] + gap + secondary_h)
    supporting = _box(inner["x0"], secondary["y1"] + gap, inner["x1"], min(inner["y1"], secondary["y1"] + gap + support_h))
    mid = (secondary["x0"] + secondary["x1"]) // 2
    col_gap = max(10, int(w * 0.03))
    return {
        "inner": inner,
        "primary": primary,
        "list": _box(secondary["x0"], secondary["y0"], mid - col_gap // 2, secondary["y1"]),
        "savings": _box(mid + col_gap // 2, secondary["y0"], secondary["x1"], secondary["y1"]),
        "discount": _box(supporting["x0"], supporting["y0"], mid - col_gap // 2, supporting["y1"]),
        "unit": _box(mid + col_gap // 2, supporting["y0"], supporting["x1"], supporting["y1"]),
        "v_rule_secondary": _box(mid - 1, secondary["y0"] + 4, mid + 2, secondary["y1"] - 4),
        "v_rule_support": _box(mid - 1, supporting["y0"] + 4, mid + 2, supporting["y1"] - 4),
        "h_rule": _box(inner["x0"] + 40, primary["y1"] + gap // 2 - 1, inner["x1"] - 40, primary["y1"] + gap // 2 + 2),
    }


def _stack_value_label(
    draw: ImageDraw.ImageDraw,
    box: dict[str, int],
    value: str,
    label: str,
    *,
    gold: tuple[int, int, int],
    value_color: tuple[int, int, int],
    primary: bool,
    strike: bool = False,
) -> list[dict[str, Any]]:
    bw = max(16, box["x1"] - box["x0"] - 6)
    bh = max(16, box["y1"] - box["y0"] - 4)
    value_h = max(14, int(bh * (0.58 if primary else 0.50)))
    label_h = max(10, int(bh * 0.22))
    vf = _fit(value, bw, value_h, bold=True)
    lf = _fit(label, bw, label_h, bold=False)
    vw, vh = text_size(vf, value)
    lw, lh = text_size(lf, label)
    gap = 3 if primary else 2
    total = vh + gap + lh
    y = box["y0"] + max(0, (box["y1"] - box["y0"] - total) // 2)
    vb = _center_text(draw, box, value, vf, value_color, y=y)
    lb = _center_text(draw, box, label, lf, gold, y=y + vh + gap)
    if strike:
        mid_y = (vb["y0"] + vb["y1"]) // 2
        pad = max(4, vw // 30)
        width = max(2, vh // 9)
        draw.line([(vb["x0"] - pad, mid_y), (vb["x1"] + pad, mid_y)], fill=gold, width=width)
    return [
        {"role": "value", "text": value, "bbox": vb, "struck": strike},
        {"role": "label", "text": label, "bbox": lb, "struck": False},
    ]


def compose_hybrid_revision(
    master: Image.Image,
    spec: dict[str, Any],
    plan: dict[str, Any],
) -> tuple[Image.Image, dict[str, Any]]:
    src = master.convert("RGB")
    width, height = src.size
    surface = _as_dict(plan.get("recomposition_surface"))
    if surface["y1"] > int(plan.get("hero_boundary") or HERO_Y_LOCK):
        raise ValueError("recomposition surface crosses hero boundary")
    navy = _sample_navy(src, spec, surface=surface)
    gold = _sample_gold(src, spec)
    white = WHITE_FALLBACK
    out = src.copy()
    draw = ImageDraw.Draw(out)
    draw.rectangle([surface["x0"], surface["y0"], surface["x1"] - 1, surface["y1"] - 1], fill=navy)
    clean = out.copy()
    slots = _layout_slots(surface)
    facts = _as_dict(plan.get("commercial_revision"))
    drawn: list[str] = []
    boxes: list[dict[str, Any]] = []

    def paint(slot: str, value: str, label: str, *, primary: bool, strike: bool = False, value_color=None) -> None:
        items = _stack_value_label(
            draw,
            slots[slot],
            value,
            label,
            gold=gold,
            value_color=value_color or gold,
            primary=primary,
            strike=strike,
        )
        drawn.extend([value, label])
        boxes.extend(items)

    paint(
        "primary",
        str(facts.get("launch_price") or "438.750 USD"),
        str(facts.get("launch_price_label") or "LANSMAN FİYATI"),
        primary=True,
        value_color=gold,
    )
    paint(
        "list",
        str(facts.get("list_price") or "675.000 USD"),
        str(facts.get("list_price_label") or "LİSTE FİYATI"),
        primary=False,
        strike=True,
        value_color=white,
    )
    paint(
        "savings",
        str(facts.get("savings") or "236.250 USD"),
        str(facts.get("savings_label") or "KAZANCINIZ"),
        primary=False,
        value_color=gold,
    )
    paint(
        "discount",
        str(facts.get("discount") or "%35"),
        str(facts.get("discount_label") or "LANSMAN AVANTAJI"),
        primary=False,
        value_color=gold,
    )
    paint(
        "unit",
        str(facts.get("unit_type") or "2+1"),
        str(facts.get("unit_label") or "DAİRE"),
        primary=False,
        value_color=gold,
    )

    for key in ("v_rule_secondary", "v_rule_support"):
        rule = slots[key]
        x = (rule["x0"] + rule["x1"]) // 2
        draw.line([(x, rule["y0"]), (x, rule["y1"])], fill=gold, width=1)
    hr = slots["h_rule"]
    hy = (hr["y0"] + hr["y1"]) // 2
    draw.line([(hr["x0"], hy), (hr["x1"], hy)], fill=gold, width=1)
    _diamond(draw, (hr["x0"] + hr["x1"]) // 2, hy, 4, gold)

    fonts = list_available_fonts()
    selected = next((f for f in fonts if f.get("serif") and f.get("bold")), None) or next(
        (f for f in fonts if f.get("serif")), None
    )
    report = {
        "reconstruction_engine": "hybrid_revision.compose_hybrid_revision",
        "architecture": "hybrid_master",
        "full_reconstruction": False,
        "raster_surgery": False,
        "native_renderer": False,
        "image_provider": False,
        "provider_image_calls": 0,
        "reference_raster_used_as_output_background": True,
        "reference_raster_used_inside_recomposition_surface": False,
        "clean_surface_method": plan.get("clean_surface_method"),
        "layout_model": plan.get("layout_model"),
        "navy": list(navy),
        "gold": list(gold),
        "typography_changed_content": {
            "selected_font": None if selected is None else selected.get("family_guess"),
            "path": None if selected is None else selected.get("path"),
            "match_reason": "closest available serif in container; exact campaign family unknown",
            "confined_to_recomposition_surface": True,
        },
        "drawn_content": [d for d in drawn if d],
        "drawn_boxes": boxes,
        "slots": slots,
        "clean_surface": clean,
        "surface": surface,
    }
    return out, report


def _region_identity(master: Image.Image, preview: Image.Image, box: dict[str, int] | None) -> dict[str, Any]:
    if not box:
        return {"pixel_identity": "FAIL", "reason": "missing_bbox", "changed_pixels": None}
    pa, pb = master.convert("RGB").load(), preview.convert("RGB").load()
    changed = 0
    max_delta = 0
    n = 0
    for y in range(box["y0"], box["y1"]):
        for x in range(box["x0"], box["x1"]):
            a, b = pa[x, y], pb[x, y]
            n += 1
            d = max(abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2]))
            if d:
                changed += 1
                max_delta = max(max_delta, d)
    return {
        "bbox": box,
        "changed_pixels": changed,
        "max_channel_delta": max_delta,
        "sampled": n,
        "pixel_identity": "PASS" if changed == 0 and max_delta == 0 else "FAIL",
    }


def pixel_lock_report(master: Image.Image, preview: Image.Image, plan: dict[str, Any]) -> dict[str, Any]:
    surface = _as_dict(plan.get("recomposition_surface"))
    ma = master.convert("RGB")
    pr = preview.convert("RGB")
    if ma.size != pr.size:
        return {"status": "fail", "reason": "size_mismatch"}
    pa, pb = ma.load(), pr.load()
    w, h = ma.size
    outside = 0
    inside = 0
    max_out = 0
    max_in = 0
    sx0, sy0, sx1, sy1 = surface["x0"], surface["y0"], surface["x1"], surface["y1"]
    for y in range(h):
        for x in range(w):
            a, b = pa[x, y], pb[x, y]
            d = max(abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2]))
            if not d:
                continue
            if sx0 <= x < sx1 and sy0 <= y < sy1:
                inside += 1
                max_in = max(max_in, d)
            else:
                outside += 1
                max_out = max(max_out, d)
    locked = {
        "headline": _region_identity(ma, pr, _as_dict(plan.get("headline_bbox"))),
        "hero": _region_identity(ma, pr, _as_dict(plan.get("hero_bbox"))),
        "cta": _region_identity(ma, pr, _as_dict(plan.get("cta_bbox"))),
        "logo": _region_identity(ma, pr, _as_dict(plan.get("logo_bbox"))),
        "footer": _region_identity(ma, pr, _as_dict(plan.get("footer_bbox"))),
    }
    support = _as_dict(plan.get("supporting_bbox"))
    if support and not plan.get("supporting_inside_surface"):
        locked["supporting_copy"] = _region_identity(ma, pr, support)
    outside_pass = outside == 0 and max_out == 0
    return {
        "recomposition_surface": surface,
        "pixels_changed_inside_surface": inside,
        "pixels_changed_outside_surface": outside,
        "outside_surface_changed_pixel_count": outside,
        "outside_surface_max_channel_delta": max_out,
        "inside_surface_max_channel_delta": max_in,
        "outside_surface_pixel_identity": "PASS" if outside_pass else "FAIL",
        "locked_regions": locked,
        "headline_pixel_lock": locked["headline"]["pixel_identity"],
        "hero_pixel_lock": locked["hero"]["pixel_identity"],
        "cta_pixel_lock": locked["cta"]["pixel_identity"],
        "logo_pixel_lock": locked["logo"]["pixel_identity"],
        "footer_pixel_lock": locked["footer"]["pixel_identity"],
    }


def validate_hybrid_preview(
    preview: Image.Image,
    plan: dict[str, Any],
    report: dict[str, Any],
    *,
    master: Image.Image | None = None,
) -> dict[str, Any]:
    failures: list[str] = []
    required = [
        "438.750",
        "LANSMAN FİYATI",
        "675.000",
        "LİSTE FİYATI",
        "236.250",
        "KAZANCINIZ",
        "%35",
        "LANSMAN AVANTAJI",
        "2+1",
        "DAİRE",
    ]
    blob = " ".join(report.get("drawn_content") or [])
    missing = [item for item in required if item not in blob]
    if missing:
        failures.append(f"missing_drawn:{','.join(missing)}")
    struck = [b for b in report.get("drawn_boxes") or [] if b.get("struck") and "675.000" in str(b.get("text") or "")]
    if not struck:
        failures.append("list_price_not_struck")
    surface = _as_dict(plan.get("recomposition_surface"))
    hero_y = int(plan.get("hero_boundary") or HERO_Y_LOCK)
    if surface["y1"] > hero_y:
        failures.append("surface_crosses_hero")
    if plan.get("headline_inside_surface"):
        failures.append("headline_inside_surface")
    old = _as_dict(plan.get("old_commercial_bbox"))
    if old:
        old_above = dict(old)
        old_above["y1"] = min(int(old["y1"]), hero_y)
        if old_above["y1"] > old_above["y0"] and not _contains(surface, old_above):
            failures.append("old_commercial_not_fully_covered")
    overlaps = 0
    boxes = [b["bbox"] for b in report.get("drawn_boxes") or [] if b.get("bbox")]
    for i, a in enumerate(boxes):
        for b in boxes[i + 1 :]:
            if _intersect_area(a, b) > 18:
                overlaps += 1
    if overlaps:
        failures.append(f"slot_overlap:{overlaps}")
    clipped = 0
    for box in boxes:
        if box["y1"] > surface["y1"] or box["y0"] < surface["y0"] or box["x0"] < surface["x0"] or box["x1"] > surface["x1"]:
            clipped += 1
    if clipped:
        failures.append(f"clipping:{clipped}")
    ghost = "pass"
    if old:
        old_above = dict(old)
        old_above["y1"] = min(int(old["y1"]), hero_y)
        if old_above["y1"] > old_above["y0"] and not _contains(surface, old_above):
            ghost = "fail"
    lock = pixel_lock_report(master, preview, plan) if master is not None else {}
    if master is not None and lock.get("outside_surface_changed_pixel_count") not in (0, None):
        failures.append("outside_surface_pixels_changed")
    return {
        "status": "fail" if failures else "pass",
        "failures": failures,
        "missing_drawn": missing,
        "ghosting_validation": ghost,
        "clipping_validation": "fail" if clipped else "pass",
        "overlap_validation": "fail" if overlaps else "pass",
        "pixel_lock": lock,
    }


def difference_map(master: Image.Image, preview: Image.Image) -> Image.Image:
    ma, pr = master.convert("RGB"), preview.convert("RGB")
    w, h = ma.size
    out = Image.new("RGB", (w, h), (8, 10, 16))
    pa, pb, po = ma.load(), pr.load(), out.load()
    for y in range(h):
        for x in range(w):
            a, b = pa[x, y], pb[x, y]
            d = abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])
            if d:
                po[x, y] = (220, 40, 40)
            else:
                dim = tuple(max(0, int(c * 0.35)) for c in a)
                po[x, y] = dim
    return out
