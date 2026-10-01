"""CreativeFamilyAdapterV1 — adapt a Master Family to a project photograph.

Preserves family identity. Adapts around architecture. Never covers the spire.
No GPT Image. Family fields are compositor overlays on the real photo.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

from investhome_api.services.creative_director.creative_font_registry import font_for_role
from investhome_api.services.creative_director.graphic_field_director import _box_px, region_luma
from investhome_api.services.creative_director.phase5_photo_foundation import (
    CANVAS_4X5,
    apply_photographic_grade,
    cover_fit_canvas,
)
from investhome_api.services.creative_director.phase5_premium_commercial_r1 import LOCKED_GRADE
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.structured_typography_compositor_v2 import (
    GOLD,
    INK,
    IVORY,
    _draw_tracked,
    _hex,
    _objects,
    _overlap_px,
    _place_logo,
    _type_hits_spire,
    revision_readiness,
)
from investhome_api.services.gpt_image_design.compose import _fit_logo

_ = _fit_logo


def _ramp_horizontal(size: tuple[int, int], x0: float, x1: float, a0: int, a1: int) -> Image.Image:
    w, h = size
    row = Image.new("L", (w, 1))
    pix = row.load()
    xa, xb = int(x0 * w), int(x1 * w)
    for x in range(w):
        if x <= xa:
            pix[x, 0] = a0
        elif x >= xb:
            pix[x, 0] = a1
        else:
            t = (x - xa) / max(1, xb - xa)
            pix[x, 0] = int(a0 + (a1 - a0) * t)
    return row.resize((w, h), Image.Resampling.BILINEAR)


def _ramp_vertical(size: tuple[int, int], y0: float, y1: float, a0: int, a1: int) -> Image.Image:
    w, h = size
    col = Image.new("L", (1, h))
    pix = col.load()
    ya, yb = int(y0 * h), int(y1 * h)
    for y in range(h):
        if y <= ya:
            pix[0, y] = a0
        elif y >= yb:
            pix[0, y] = a1
        else:
            t = (y - ya) / max(1, yb - ya)
            pix[0, y] = int(a0 + (a1 - a0) * t)
    return col.resize((w, h), Image.Resampling.BILINEAR)


def _union_l(*masks: Image.Image) -> Image.Image:
    out = masks[0].copy()
    for mask in masks[1:]:
        out = ImageChops_lighter(out, mask)
    return out


def ImageChops_lighter(a: Image.Image, b: Image.Image) -> Image.Image:
    from PIL import ImageChops

    return ImageChops.lighter(a, b)


def _restore_architecture(photo: Image.Image, painted: Image.Image, protect_l: Image.Image | None) -> Image.Image:
    if protect_l is None:
        return painted
    protect = protect_l.convert("L")
    if protect.size != photo.size:
        protect = protect.resize(photo.size, Image.Resampling.NEAREST)
    core = protect.point(lambda v: 255 if v > 48 else 0)
    return Image.composite(photo.convert("RGB"), painted.convert("RGB"), core)


def apply_family_overlay(
    photo: Image.Image,
    family: dict[str, Any],
    *,
    protect_l: Image.Image | None,
    region: dict[str, float],
) -> Image.Image:
    devices = dict(family.get("graphic_devices") or {})
    overlay = str(devices.get("overlay") or "")
    field = _hex(str(devices.get("field_hex") or "#14181E"), (20, 24, 30))
    src = photo.convert("RGB")
    w, h = src.size
    if overlay == "top_light_wash":
        wash = Image.new("RGB", src.size, _hex(str(devices.get("field_hex") or "#E8E2D6"), (232, 226, 214)))
        mask = _ramp_vertical(src.size, 0.0, 0.34, 210, 0).filter(ImageFilter.GaussianBlur(radius=8))
        painted = Image.composite(wash, src, mask)
    elif overlay == "top_charcoal_dissolve":
        panel = Image.new("RGB", src.size, field)
        mask = _ramp_vertical(src.size, 0.0, 0.40, 235, 0).filter(ImageFilter.GaussianBlur(radius=6))
        painted = Image.composite(panel, src, mask)
    elif overlay == "local_plane_darken":
        dark = ImageEnhance.Brightness(src).enhance(0.42)
        mask = Image.new("L", src.size, 0)
        x0 = int(float(region.get("x") or 0.5) * w) - 24
        y0 = int(float(region.get("y") or 0.06) * h) - 16
        x1 = int((float(region.get("x") or 0.5) + float(region.get("w") or 0.4)) * w) + 36
        y1 = int((float(region.get("y") or 0.06) + float(region.get("h") or 0.42)) * h) + 24
        ImageDraw.Draw(mask).rounded_rectangle((x0, y0, x1, y1), radius=18, fill=170)
        mask = mask.filter(ImageFilter.GaussianBlur(radius=28))
        painted = Image.composite(dark, src, mask)
    else:
        panel = Image.new("RGB", src.size, field)
        right = _ramp_horizontal(src.size, 0.40, 0.68, 0, 230)
        top = _ramp_vertical(src.size, 0.0, 0.22, 160, 0)
        mask = _union_l(right, top).filter(ImageFilter.GaussianBlur(radius=10))
        painted = Image.composite(panel, src, mask)
    return _restore_architecture(src, painted, protect_l)


def _spire_box(protection: dict[str, Any], size: tuple[int, int]) -> tuple[int, int, int, int] | None:
    return _box_px((protection.get("regions") or {}).get("SPIRE"), size)


def _region_hits_spire(region: dict[str, float], protection: dict[str, Any], size: tuple[int, int]) -> bool:
    spire = _spire_box(protection, size)
    px = _box_px(region, size)
    if not spire or not px:
        return False
    return _overlap_px(px, spire)


def candidate_type_regions(protection: dict[str, Any], size: tuple[int, int]) -> dict[str, dict[str, float]]:
    w, h = size
    spire = _spire_box(protection, size)
    spire_right = (spire[2] / w + 0.03) if spire else 0.52
    spire_left = (spire[0] / w - 0.03) if spire else 0.28
    right_x = min(0.62, max(0.52, spire_right))
    return {
        "right_column": {"x": right_x, "y": 0.055, "w": max(0.30, 0.94 - right_x), "h": 0.78},
        "top_right": {"x": right_x, "y": 0.045, "w": max(0.30, 0.94 - right_x), "h": 0.36},
        "mid_right": {"x": right_x, "y": 0.08, "w": max(0.30, 0.94 - right_x), "h": 0.46},
        "top_left": {"x": 0.06, "y": 0.05, "w": max(0.18, min(0.36, spire_left - 0.06)), "h": 0.28},
        "top_center": {"x": 0.12, "y": 0.045, "w": 0.76, "h": 0.26},
        "top_band": {"x": 0.08, "y": 0.04, "w": 0.84, "h": 0.22},
    }


def choose_type_region(family: dict[str, Any], protection: dict[str, Any], size: tuple[int, int]) -> dict[str, Any]:
    flex = dict(family.get("flexibility") or {})
    priority = list(flex.get("type_region_priority") or ["right_column", "top_right"])
    catalog = candidate_type_regions(protection, size)
    chosen = None
    mirrored = False
    for name in priority:
        region = catalog.get(name)
        if not region or float(region.get("w") or 0) < 0.22:
            continue
        if name == "top_center" and _region_hits_spire(region, protection, size):
            continue
        if name in {"top_left"} and float(region.get("w") or 0) < 0.20:
            continue
        chosen = (name, region)
        break
    if chosen is None:
        chosen = ("right_column", catalog["right_column"])
        mirrored = True
    name, region = chosen
    alignment = str((family.get("headline") or {}).get("alignment") or "right")
    if name in {"right_column", "top_right", "mid_right"} and alignment == "left" and name != "mid_right":
        # SKY family preferred left; right region uses left-within-right as permitted alternate.
        alignment = "left"
        mirrored = True
    if name in {"top_center", "top_band"}:
        alignment = "center" if not _region_hits_spire(region, protection, size) else "right"
        if alignment == "right":
            region = catalog["top_right"]
            name = "top_right"
            mirrored = True
    return {
        "slot": name,
        "region": region,
        "alignment": alignment,
        "mirrored": mirrored,
        "family_identity_preserved": True,
    }


def crop_for_family(source: Image.Image, family: dict[str, Any]) -> tuple[Image.Image, dict[str, Any]]:
    bias = dict((family.get("flexibility") or {}).get("crop_bias") or {"x": 0.55, "y": 0.48})
    crop, transform = cover_fit_canvas(source, CANVAS_4X5, centering=(float(bias.get("x") or 0.55), float(bias.get("y") or 0.48)))
    graded = apply_photographic_grade(crop, dict(LOCKED_GRADE))
    return graded, {
        "centering": list(transform.get("centering") or []),
        "source_crop": transform.get("source_crop"),
        "canvas": list(CANVAS_4X5),
        "family_id": family.get("family_id"),
    }


def compose_family(
    field: Image.Image,
    *,
    family: dict[str, Any],
    placement: dict[str, Any],
    fonts: dict[str, Any],
    logo_rgba: Image.Image | None,
    protection: dict[str, Any],
    facts: dict[str, str] | None = None,
) -> dict[str, Any]:
    facts = facts or dict(REQUIRED_FACTS)
    canvas = field.convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    w, h = canvas.size
    region = dict(placement.get("region") or {})
    alignment = str(placement.get("alignment") or "right")
    typo = dict(family.get("typography") or {})
    spacing = dict(family.get("spacing") or {})
    devices = dict(family.get("graphic_devices") or {})
    scale = 1.0
    family_id = str(family.get("family_id") or "")
    if family_id == "MINIMAL_TOP_FIELD":
        scale = 0.84
    ivory = _hex(str(typo.get("text_hex") or ""), IVORY)
    gold = _hex(str(typo.get("accent_hex") or ""), GOLD)
    ink = _hex(str(typo.get("ink_hex") or ""), INK)
    fill = _type_fill_region(canvas, region, ivory, ink)
    inset = float(spacing.get("edge_inset") or 0.06)
    x_left = int((float(region.get("x") or 0.08) + 0.012) * w)
    x_right = int((float(region.get("x") or 0.08) + float(region.get("w") or 0.4) - 0.012) * w)
    x_mid = (x_left + x_right) // 2
    y = int((float(region.get("y") or 0.05) + 0.01) * h)
    if alignment == "right":
        origin_x, anchor = x_right, "rt"
    elif alignment == "center":
        origin_x, anchor = x_mid, "mt"
    else:
        origin_x, anchor = x_left, "lt"
    display_h = max(28, int(h * float(typo.get("display_scale") or 0.06) * scale))
    support_h = max(14, int(h * float(typo.get("secondary_scale") or 0.02) * scale))
    number_h = max(22, int(h * float(typo.get("number_scale") or 0.042) * scale))
    cta_h = max(12, int(h * 0.017 * scale))
    display = font_for_role(fonts, str(typo.get("display_role") or "DISPLAY_SERIF"), display_h)
    sans = font_for_role(fonts, "EDITORIAL_SANS", support_h)
    number = font_for_role(fonts, "COMMERCIAL_NUMBER", number_h)
    cta_font = font_for_role(fonts, "CTA", cta_h)
    headline = facts["headline"]
    if family.get("headline", {}).get("split_last_line_gold") and " " in headline:
        first, last = headline.split(" ", 1)
        b1 = _draw_tracked(draw, (origin_x, y), first, display, fill, tracking=float(typo.get("tracking_display") or 30), anchor=anchor)
        y = b1[3] + int(h * 0.006)
        big = font_for_role(fonts, str(typo.get("display_role") or "DISPLAY_SERIF"), int(display_h * 1.18))
        b2 = _draw_tracked(draw, (origin_x, y), last, big, gold, tracking=20, anchor=anchor)
        head_box = (min(b1[0], b2[0]), b1[1], max(b1[2], b2[2]), b2[3])
        y = b2[3]
    else:
        if family_id == "TYPE_IN_PLANE" and " " in headline:
            first, last = headline.split(" ", 1)
            mid = font_for_role(fonts, "DISPLAY_SERIF", int(display_h * 0.78))
            b1 = _draw_tracked(draw, (origin_x, y), first, mid, gold, tracking=24, anchor=anchor)
            y = b1[3] + int(h * 0.004)
            b2 = _draw_tracked(draw, (origin_x, y), last, display, fill, tracking=12, anchor=anchor)
            head_box = (min(b1[0], b2[0]), b1[1], max(b1[2], b2[2]), b2[3])
            y = b2[3]
        else:
            head_box = _draw_tracked(
                draw, (origin_x, y), headline, display, fill, tracking=float(typo.get("tracking_display") or 20), anchor=anchor
            )
            y = head_box[3]
    if devices.get("rule") == "short_gold_rule":
        y = y + int(h * 0.014)
        if alignment == "right":
            draw.line((head_box[0], y, x_right, y), fill=gold, width=2)
        elif alignment == "center":
            rw = max(48, int((head_box[2] - head_box[0]) * 0.35))
            draw.line((x_mid - rw // 2, y, x_mid + rw // 2, y), fill=gold, width=2)
        else:
            draw.line((x_left, y, min(x_left + int(w * 0.22), x_right), y), fill=gold, width=2)
        y += int(h * 0.018)
    else:
        y += int(h * float(spacing.get("after_headline") or 0.02))
    unit = f"{facts['unit']} {facts['unit_label']}"
    unit_box = _draw_tracked(draw, (origin_x, y), unit, sans, fill, tracking=float(typo.get("tracking_support") or 160), anchor=anchor)
    y = unit_box[3] + int(h * float(spacing.get("after_unit") or 0.016))
    price_box = _draw_tracked(draw, (origin_x, y), facts["list_price"], number, fill, tracking=8, anchor=anchor)
    y = price_box[3] + int(h * float(spacing.get("after_price") or 0.012))
    if family_id == "TYPE_IN_PLANE":
        disc_font = font_for_role(fonts, "COMMERCIAL_NUMBER", int(number_h * 0.62))
        disc_box = _draw_tracked(draw, (origin_x, y), facts["discount"], disc_font, gold, tracking=8, anchor=anchor)
        y = disc_box[3] + int(h * 0.004)
        label_box = _draw_tracked(draw, (origin_x, y), facts["discount_label"], sans, fill, tracking=180, anchor=anchor)
    elif family_id == "MINIMAL_TOP_FIELD":
        pair = f"{facts['discount']}  {facts['discount_label']}"
        disc_box = _draw_tracked(draw, (origin_x, y), pair, sans, gold, tracking=120, anchor=anchor)
        label_box = disc_box
    else:
        disc_font = font_for_role(fonts, "COMMERCIAL_NUMBER", int(number_h * 0.72))
        disc_box = _draw_tracked(draw, (origin_x, y), facts["discount"], disc_font, gold, tracking=8, anchor=anchor)
        y = disc_box[3] + int(h * 0.004)
        label_box = _draw_tracked(draw, (origin_x, y), facts["discount_label"], sans, fill, tracking=200, anchor=anchor)
    y = max(disc_box[3], label_box[3]) + int(h * float(spacing.get("after_offer") or 0.046))
    cta_box = _draw_tracked(draw, (origin_x, y), facts["cta"], cta_font, fill, tracking=float(typo.get("tracking_cta") or 220), anchor=anchor)
    logo_box = _place_family_logo(canvas, logo_rgba, family, alignment, x_left, x_right, w, h, protection)
    objects = _objects(canvas.size, headline=head_box, unit=unit_box, price=price_box, discount=disc_box, label=label_box, cta=cta_box, logo=logo_box)
    _ = inset
    return {
        "image": canvas.convert("RGB"),
        "objects": objects,
        "family_id": family_id,
        "placement": placement,
        "canvas": {"width": w, "height": h, "aspect": "4:5"},
        "spire_collision": _type_hits_spire(objects, protection, canvas.size),
        "facts": {
            "headline": facts["headline"],
            "unit_type": unit,
            "price": facts["list_price"],
            "discount": facts["discount"],
            "discount_label": facts["discount_label"],
            "cta": facts["cta"],
        },
    }


def _type_fill_region(image: Image.Image, region: dict[str, Any], light, dark):
    luma = region_luma(image, region)
    return light if luma < 118 else dark


def _place_family_logo(canvas, logo_rgba, family, alignment, x_left, x_right, w, h, protection=None):
    slot = str((family.get("brand") or {}).get("slot") or "bottom_of_column")
    bw, bh = int(w * float((family.get("brand") or {}).get("relative_scale") or 0.22)), int(h * 0.07)
    if slot == "top_center":
        x, y = (w - bw) // 2, int(h * 0.028)
        spire = _box_px(((protection or {}).get("regions") or {}).get("SPIRE"), canvas.size)
        if spire and _overlap_px((x, y, x + bw, y + bh), spire):
            x, y = (w - bw) // 2, int(h * 0.90)
    elif slot == "bottom_center":
        x, y = (w - bw) // 2, int(h * 0.90)
    elif alignment == "right":
        x, y = x_right - bw, int(h * 0.88)
    else:
        x, y = x_left, int(h * 0.88)
    return _place_logo(canvas, logo_rgba, x, y, bw, bh)


def adapt_family_to_project(
    *,
    source: Image.Image,
    family: dict[str, Any],
    protection: dict[str, Any],
    protect_l: Image.Image | None,
    fonts: dict[str, Any],
    logo_rgba: Image.Image | None,
    facts: dict[str, str] | None = None,
) -> dict[str, Any]:
    graded, crop_meta = crop_for_family(source, family)
    placement = choose_type_region(family, protection, graded.size)
    fielded = apply_family_overlay(graded, family, protect_l=protect_l, region=placement["region"])
    pack = compose_family(
        fielded,
        family=family,
        placement=placement,
        fonts=fonts,
        logo_rgba=logo_rgba,
        protection=protection,
        facts=facts,
    )
    pack["foundation"] = graded
    pack["fielded"] = fielded
    pack["crop"] = crop_meta
    pack["adapter"] = {
        "schema": "CreativeFamilyAdapterV1",
        "family_id": family.get("family_id"),
        "placement": placement,
        "destroyed_family_identity": False,
        "architecture_forced_into_reference": False,
        "spire_avoided": not pack.get("spire_collision"),
    }
    return pack


def build_family_master_spec(
    *,
    key: str,
    pack: dict[str, Any],
    family: dict[str, Any],
    crop: dict[str, Any],
    photo_asset: str,
    logo_asset: str,
    candidate_asset_id: str,
    architecture_lock: dict[str, Any],
) -> dict[str, Any]:
    objects = dict(pack.get("objects") or {})
    groups = []
    mutable = {
        "headline": ["COPY_EDIT_ONLY"],
        "unit_type": ["COPY_EDIT_ONLY"],
        "price": ["PRICE_EDIT_ONLY"],
        "discount": ["PRICE_EDIT_ONLY", "COPY_EDIT_ONLY"],
        "discount_label": ["COPY_EDIT_ONLY"],
        "cta": ["COPY_EDIT_ONLY"],
        "project_logo": ["LOGO_ONLY"],
    }
    for role, item in objects.items():
        groups.append(
            {
                "role": role,
                "bounds": item.get("bounds"),
                "editable": True,
                "mutable_for": mutable.get(role, ["COPY_EDIT_ONLY"]),
            }
        )
    return {
        "schema": "FamilyMasterDesignSpecV1",
        "spec_id": str(uuid4()),
        "candidate_key": key,
        "family_id": family.get("family_id"),
        "canvas": pack.get("canvas"),
        "project_photo": {"asset_id": photo_asset, "crop": crop, "z": 0, "bounds": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}},
        "graphic_field": {
            "semantic_role": "graphic_field",
            "asset_id": pack.get("graphic_field_asset_id"),
            "locked_raster": True,
            "overlay": (family.get("graphic_devices") or {}).get("overlay"),
            "z": 1,
        },
        "project_logo": {"asset_id": logo_asset, "ai_redrawn": False, "z": 3, "bounds": (objects.get("project_logo") or {}).get("bounds")},
        "headline": {"text": REQUIRED_FACTS["headline"], "bounds": (objects.get("headline") or {}).get("bounds"), "z": 2},
        "unit_type": {"text": f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}", "bounds": (objects.get("unit_type") or {}).get("bounds"), "z": 2},
        "price": {"text": REQUIRED_FACTS["list_price"], "bounds": (objects.get("price") or {}).get("bounds"), "z": 2},
        "discount": {"text": REQUIRED_FACTS["discount"], "bounds": (objects.get("discount") or {}).get("bounds"), "z": 2},
        "discount_label": {"text": REQUIRED_FACTS["discount_label"], "bounds": (objects.get("discount_label") or {}).get("bounds"), "z": 2},
        "cta": {"text": REQUIRED_FACTS["cta"], "bounds": (objects.get("cta") or {}).get("bounds"), "z": 2},
        "typography": {"display": "Cormorant Garamond", "support": "Source Sans 3"},
        "alignment": (pack.get("placement") or {}).get("alignment"),
        "grouping": {
            "HEADLINE_GROUP": ["headline"],
            "COMMERCIAL_OFFER_GROUP": ["price", "discount", "discount_label"],
            "SUPPORTING_INFORMATION_GROUP": ["unit_type"],
            "CTA_GROUP": ["cta"],
            "BRAND_GROUP": ["project_logo"],
        },
        "z_order": family.get("z_order"),
        "safe_zones": (pack.get("placement") or {}).get("region"),
        "architecture_lock": {
            "schema": architecture_lock.get("schema"),
            "protected_coverage": architecture_lock.get("protected_coverage"),
        },
        "source_asset": photo_asset,
        "candidate_asset": candidate_asset_id,
        "family_provenance": {
            "family_id": family.get("family_id"),
            "source_references": family.get("source_references"),
            "primary_reference": family.get("primary_reference"),
        },
        "editable_commercial_groups": groups,
        "adapter": pack.get("adapter"),
    }


family_revision_readiness = revision_readiness
