"""StructuredTypographyCompositorV2 — OS owns all type, logo, and commercial groups."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFont

from investhome_api.services.creative_director.creative_font_registry import font_for_role
from investhome_api.services.creative_director.generative_master_director import MOJIBAKE_MARKERS
from investhome_api.services.creative_director.graphic_field_director import _box_px, region_luma
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.gpt_image_design.compose import _fit_logo

GOLD = (201, 168, 92)
IVORY = (244, 239, 228)
INK = (22, 26, 32)


def _hex(value: str, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    raw = (value or "").lstrip("#")
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    if len(raw) != 6:
        return fallback
    try:
        return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
    except ValueError:
        return fallback


def _draw_tracked(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    tracking: float = 0,
    *,
    anchor: str = "lt",
) -> tuple[int, int, int, int]:
    x, y = xy
    if tracking <= 0 and anchor == "lt":
        draw.text((x, y), text, font=font, fill=fill)
        bbox = draw.textbbox((x, y), text, font=font)
        return int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
    size = float(getattr(font, "size", 32) or 32)
    gap = tracking / 1000.0 * size
    widths = [font.getlength(ch) for ch in text]
    total = sum(widths) + gap * max(0, len(text) - 1)
    if anchor == "rt":
        x = x - total
    elif anchor == "mt":
        x = x - total / 2
    x0 = x
    for ch, w in zip(text, widths):
        draw.text((x, y), ch, font=font, fill=fill)
        x += w + gap
    bbox = draw.textbbox((x0, y), text, font=font)
    return int(x0), int(bbox[1]), int(x0 + total), int(bbox[3])


def _safe_column(
    protection: dict[str, Any],
    size: tuple[int, int],
    *,
    prefer: str,
) -> dict[str, float]:
    w, h = size
    spire = _box_px((protection.get("regions") or {}).get("SPIRE"), size)
    spire_right = (spire[2] / w + 0.03) if spire else 0.50
    if prefer == "right":
        x = max(0.52, spire_right)
        return {"x": min(x, 0.62), "y": 0.055, "w": max(0.30, 0.94 - min(x, 0.62)), "h": 0.86}
    if prefer == "top_center":
        return {"x": 0.10, "y": 0.05, "w": 0.80, "h": 0.28}
    return {"x": 0.07, "y": 0.055, "w": min(0.40, max(0.28, spire_right - 0.10)), "h": 0.42}


def _type_fill(field: Image.Image, box: dict[str, Any], light: tuple[int, int, int], dark: tuple[int, int, int]) -> tuple[int, int, int]:
    return light if region_luma(field, box) < 118 else dark


def _norm_box(x0: int, y0: int, x1: int, y1: int, size: tuple[int, int]) -> dict[str, float]:
    w, h = size
    return {
        "x": round(x0 / w, 4),
        "y": round(y0 / h, 4),
        "w": round(max(1, x1 - x0) / w, 4),
        "h": round(max(1, y1 - y0) / h, 4),
    }


def compose_typography_v2(
    field: Image.Image,
    *,
    systems: dict[str, Any],
    fonts: dict[str, Any],
    logo_rgba: Image.Image | None,
    protection: dict[str, Any],
    facts: dict[str, str] | None = None,
) -> dict[str, Any]:
    facts = facts or dict(REQUIRED_FACTS)
    canvas = field.convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    w, h = canvas.size
    key = str(systems.get("key") or "E1")
    primary = dict(systems.get("primary") or {})
    color = dict(primary.get("color_system") or {})
    gold = _hex(str(color.get("accent_color") or ""), GOLD)
    ivory = _hex(str(color.get("text_color") or ""), IVORY)
    objects: dict[str, dict[str, Any]] = {}
    if key == "E1":
        objects = _compose_e1(draw, canvas, fonts, logo_rgba, protection, facts, gold, ivory)
    elif key == "E2":
        objects = _compose_e2(draw, canvas, fonts, logo_rgba, protection, facts, gold, ivory)
    else:
        objects = _compose_e3(draw, canvas, fonts, logo_rgba, protection, facts, gold, ivory)
    return {
        "image": canvas.convert("RGB"),
        "objects": objects,
        "system_id": primary.get("system_id"),
        "key": key,
        "canvas": {"width": w, "height": h, "aspect": "4:5"},
        "spire_collision": _type_hits_spire(objects, protection, canvas.size),
        "facts": {
            "headline": facts["headline"],
            "unit_type": f"{facts['unit']} {facts['unit_label']}",
            "price": facts["list_price"],
            "discount": facts["discount"],
            "discount_label": facts["discount_label"],
            "cta": facts["cta"],
        },
    }


def _compose_e1(draw, canvas, fonts, logo_rgba, protection, facts, gold, ivory) -> dict[str, dict[str, Any]]:
    w, h = canvas.size
    col = _safe_column(protection, canvas.size, prefer="right")
    x_right = int((col["x"] + col["w"]) * w)
    y = int(col["y"] * h)
    fill = _type_fill(canvas, col, ivory, INK)
    display = font_for_role(fonts, "DISPLAY_SERIF", int(h * 0.072))
    display_lg = font_for_role(fonts, "DISPLAY_SERIF", int(h * 0.092))
    sans = font_for_role(fonts, "EDITORIAL_SANS", int(h * 0.022))
    number = font_for_role(fonts, "COMMERCIAL_NUMBER", int(h * 0.048))
    cta_font = font_for_role(fonts, "CTA", int(h * 0.018))
    b1 = _draw_tracked(draw, (x_right, y), "ALIRKEN", display, fill, tracking=40, anchor="rt")
    y = b1[3] + int(h * 0.008)
    b2 = _draw_tracked(draw, (x_right, y), "KAZAN", display_lg, gold, tracking=20, anchor="rt")
    rule_y = b2[3] + int(h * 0.018)
    draw.line((b2[0], rule_y, x_right, rule_y), fill=gold, width=2)
    y = rule_y + int(h * 0.028)
    unit = f"{facts['unit']} {facts['unit_label']}"
    b3 = _draw_tracked(draw, (x_right, y), unit, sans, fill, tracking=180, anchor="rt")
    y = b3[3] + int(h * 0.034)
    b4 = _draw_tracked(draw, (x_right, y), facts["list_price"], number, fill, tracking=20, anchor="rt")
    y = b4[3] + int(h * 0.016)
    disc = font_for_role(fonts, "COMMERCIAL_NUMBER", int(h * 0.036))
    b5 = _draw_tracked(draw, (x_right, y), facts["discount"], disc, gold, tracking=10, anchor="rt")
    y = b5[3] + int(h * 0.006)
    b6 = _draw_tracked(draw, (x_right, y), facts["discount_label"], sans, fill, tracking=220, anchor="rt")
    y = b6[3] + int(h * 0.055)
    b7 = _draw_tracked(draw, (x_right, y), facts["cta"], cta_font, fill, tracking=260, anchor="rt")
    logo_box = _place_logo(canvas, logo_rgba, x_right - int(w * 0.26), int(h * 0.88), int(w * 0.26), int(h * 0.07))
    return _objects(canvas.size, headline= _union(b1, b2), unit=b3, price=b4, discount=b5, label=b6, cta=b7, logo=logo_box)


def _compose_e2(draw, canvas, fonts, logo_rgba, protection, facts, gold, ivory) -> dict[str, dict[str, Any]]:
    w, h = canvas.size
    col = _safe_column(protection, canvas.size, prefer="right")
    x0 = int(col["x"] * w) + 8
    y = int(col["y"] * h)
    fill = _type_fill(canvas, col, ivory, INK)
    kicker = font_for_role(fonts, "EDITORIAL_SANS", int(h * 0.018))
    display = font_for_role(fonts, "DISPLAY_SERIF", int(h * 0.058))
    price_font = font_for_role(fonts, "COMMERCIAL_NUMBER", int(h * 0.07))
    disc_font = font_for_role(fonts, "COMMERCIAL_NUMBER", int(h * 0.042))
    sans = font_for_role(fonts, "EDITORIAL_SANS", int(h * 0.02))
    cta_font = font_for_role(fonts, "CTA", int(h * 0.018))
    b0 = _draw_tracked(draw, (x0, y), f"{facts['unit']} {facts['unit_label']}", kicker, fill, tracking=200)
    y = b0[3] + int(h * 0.012)
    b1 = _draw_tracked(draw, (x0, y), facts["headline"], display, fill, tracking=30)
    y = b1[3] + int(h * 0.028)
    b2 = _draw_tracked(draw, (x0, y), facts["list_price"], price_font, fill, tracking=8)
    y = b2[3] + int(h * 0.012)
    rule_x1 = min(canvas.size[0] - 24, x0 + int(w * 0.38))
    draw.line((x0, y, rule_x1, y), fill=gold, width=2)
    y += int(h * 0.018)
    b3 = _draw_tracked(draw, (x0, y), facts["discount"], disc_font, gold, tracking=8)
    y = b3[3] + int(h * 0.004)
    b4 = _draw_tracked(draw, (x0, y), facts["discount_label"], sans, fill, tracking=180)
    y = b4[3] + int(h * 0.05)
    b5 = _draw_tracked(draw, (x0, y), facts["cta"], cta_font, fill, tracking=220)
    logo_box = _place_logo(canvas, logo_rgba, x0, int(h * 0.88), int(w * 0.28), int(h * 0.07))
    return _objects(canvas.size, headline=b1, unit=b0, price=b2, discount=b3, label=b4, cta=b5, logo=logo_box)


def _compose_e3(draw, canvas, fonts, logo_rgba, protection, facts, gold, ivory) -> dict[str, dict[str, Any]]:
    w, h = canvas.size
    col = _safe_column(protection, canvas.size, prefer="top_center")
    # Keep type in the upper field; shift right if center collides with spire.
    spire = _box_px((protection.get("regions") or {}).get("SPIRE"), canvas.size)
    cx = w // 2
    if spire and spire[0] < cx < spire[2] and spire[1] < int(h * 0.22):
        col = _safe_column(protection, canvas.size, prefer="right")
        align = "rt"
        x = int((col["x"] + col["w"]) * w)
    else:
        align = "mt"
        x = cx
    y = int(0.06 * h)
    fill = _type_fill(canvas, col, ivory, INK)
    display = font_for_role(fonts, "DISPLAY_SERIF", int(h * 0.044))
    sans = font_for_role(fonts, "EDITORIAL_SANS", int(h * 0.018))
    number = font_for_role(fonts, "COMMERCIAL_NUMBER", int(h * 0.036))
    cta_font = font_for_role(fonts, "CTA", int(h * 0.016))
    b1 = _draw_tracked(draw, (x, y), facts["headline"], display, fill, tracking=80, anchor=align)
    y = b1[3] + int(h * 0.016)
    b2 = _draw_tracked(draw, (x, y), f"{facts['unit']} {facts['unit_label']}", sans, fill, tracking=160, anchor=align)
    y = b2[3] + int(h * 0.022)
    b3 = _draw_tracked(draw, (x, y), facts["list_price"], number, fill, tracking=12, anchor=align)
    y = b3[3] + int(h * 0.01)
    pair = f"{facts['discount']}  {facts['discount_label']}"
    b4 = _draw_tracked(draw, (x, y), pair, sans, gold, tracking=120, anchor=align)
    y = b4[3] + int(h * 0.028)
    b5 = _draw_tracked(draw, (x, y), facts["cta"], cta_font, fill, tracking=240, anchor=align)
    logo_box = _place_logo(canvas, logo_rgba, int(w * 0.36), int(h * 0.90), int(w * 0.28), int(h * 0.06))
    return _objects(canvas.size, headline=b1, unit=b2, price=b3, discount=b4, label=b4, cta=b5, logo=logo_box)


def _place_logo(canvas: Image.Image, logo_rgba: Image.Image | None, x: int, y: int, bw: int, bh: int) -> tuple[int, int, int, int]:
    box = (x, y, x + bw, y + bh)
    if logo_rgba is None:
        return box
    fitted = _fit_logo(logo_rgba, bw, bh)
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    layer.paste(fitted, (x, y), fitted)
    canvas.alpha_composite(layer)
    return (x, y, x + fitted.width, y + fitted.height)


def _union(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    return min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])


def _overlap_px(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def turkish_copy_is_valid(facts: dict[str, Any] | None) -> bool:
    """Deterministic UTF-8 check. Valid compositor facts must not be rejected by Vision."""
    blob = dict(facts or {})
    unit = str(blob.get("unit_type") or "")
    cta = str(blob.get("cta") or "")
    expected_unit = f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}"
    if unit != expected_unit or cta != REQUIRED_FACTS["cta"]:
        return False
    joined = "".join(str(v) for v in blob.values())
    if any(marker in joined for marker in MOJIBAKE_MARKERS):
        return False
    return "İ" in unit and "Ş" in cta


def _type_hits_spire(
    objects: dict[str, dict[str, Any]],
    protection: dict[str, Any],
    size: tuple[int, int],
    occupancy_l: Any = None,
) -> bool:
    mask = occupancy_l
    if mask is None:
        mask = protection.get("occupancy_hard_l")
    if mask is not None:
        from investhome_api.services.creative_director.creative_collision_engine import objects_hit_hard_occupancy

        return objects_hit_hard_occupancy(objects, mask)
    spire = _box_px((protection.get("regions") or {}).get("SPIRE"), size)
    if not spire:
        return False
    for role, item in objects.items():
        if role == "project_logo":
            continue
        px = item.get("px")
        if isinstance(px, (list, tuple)) and len(px) == 4 and _overlap_px(tuple(int(v) for v in px), spire):
            return True
    return False


def _objects(size, **boxes) -> dict[str, dict[str, Any]]:
    mapping = {
        "headline": "headline",
        "unit": "unit_type",
        "price": "price",
        "discount": "discount",
        "label": "discount_label",
        "cta": "cta",
        "logo": "project_logo",
    }
    out = {}
    for key, role in mapping.items():
        box = boxes.get(key)
        if not box:
            continue
        out[role] = {
            "role": role,
            "bounds": _norm_box(*box, size),
            "px": list(box),
        }
    return out


def build_master_spec(
    *,
    key: str,
    pack: dict[str, Any],
    systems: dict[str, Any],
    crop: dict[str, Any],
    photo_asset: str,
    logo_asset: str,
    graphic_field_asset_id: str,
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
        "schema": "GraphicFieldMasterDesignSpecV1",
        "spec_id": str(uuid4()),
        "candidate_key": key,
        "canvas": pack.get("canvas"),
        "project_photo": {"asset_id": photo_asset, "crop": crop, "z": 0, "bounds": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}},
        "graphic_field": {
            "asset_id": graphic_field_asset_id,
            "locked_raster": True,
            "z": 1,
            "bounds": ((systems.get("primary") or {}).get("canvas_system") or {}).get("graphic_field")
            or {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0},
        },
        "project_logo": {"asset_id": logo_asset, "ai_redrawn": False, "z": 3, "bounds": (objects.get("project_logo") or {}).get("bounds")},
        "headline": {"text": REQUIRED_FACTS["headline"], "bounds": (objects.get("headline") or {}).get("bounds"), "z": 2},
        "unit_type": {"text": f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}", "bounds": (objects.get("unit_type") or {}).get("bounds"), "z": 2},
        "price": {"text": REQUIRED_FACTS["list_price"], "bounds": (objects.get("price") or {}).get("bounds"), "z": 2},
        "discount": {"text": REQUIRED_FACTS["discount"], "bounds": (objects.get("discount") or {}).get("bounds"), "z": 2},
        "discount_label": {"text": REQUIRED_FACTS["discount_label"], "bounds": (objects.get("discount_label") or {}).get("bounds"), "z": 2},
        "cta": {"text": REQUIRED_FACTS["cta"], "bounds": (objects.get("cta") or {}).get("bounds"), "z": 2},
        "typography": {"display": "Cormorant Garamond", "support": "Source Sans 3"},
        "alignment": (systems.get("primary") or {}).get("alignment_system"),
        "grouping": {
            "HEADLINE_GROUP": ["headline"],
            "COMMERCIAL_OFFER_GROUP": ["price", "discount", "discount_label"],
            "SUPPORTING_INFORMATION_GROUP": ["unit_type"],
            "CTA_GROUP": ["cta"],
            "BRAND_GROUP": ["project_logo"],
        },
        "z_order": ["project_photo", "graphic_field", "verified_typography", "project_logo"],
        "relationships": {
            "price_discount": "designed commercial pair",
            "headline_to_offer": "shared content origin from executable system",
        },
        "safe_zones": (systems.get("primary") or {}).get("canvas_system"),
        "architecture_lock": {
            "schema": architecture_lock.get("schema"),
            "protected_coverage": architecture_lock.get("protected_coverage"),
            "composite_rule": architecture_lock.get("composite_rule"),
        },
        "source_asset": photo_asset,
        "graphic_field_asset": graphic_field_asset_id,
        "reference_system_provenance": {
            "system_id": systems.get("system_id"),
            "primary_filename": systems.get("primary_filename"),
            "secondary_filename": systems.get("secondary_filename"),
        },
        "editable_commercial_groups": groups,
    }


def revision_readiness(spec: dict[str, Any]) -> dict[str, Any]:
    def has(role: str, min_w: float = 0.10, min_h: float = 0.03) -> bool:
        item = spec.get(role) or {}
        box = item.get("bounds") if isinstance(item, dict) else None
        if not isinstance(box, dict):
            for group in spec.get("editable_commercial_groups") or []:
                if group.get("role") == role:
                    box = group.get("bounds")
                    break
        if not isinstance(box, dict):
            return False
        return float(box.get("w") or 0) >= min_w and float(box.get("h") or 0) >= min_h

    photo = bool((spec.get("project_photo") or {}).get("asset_id"))
    field_blob = spec.get("graphic_field") or spec.get("family_field") or {}
    field = bool(
        field_blob.get("asset_id")
        or field_blob.get("overlay")
        or field_blob.get("locked_raster")
        or field_blob.get("semantic_role") == "graphic_field"
    )
    checks = {
        "PRICE_EDIT_ONLY": "PASS" if has("price", 0.14, 0.03) else "FAIL",
        "COPY_EDIT_ONLY": "PASS" if has("headline", 0.16, 0.03) else "FAIL",
        "VISUAL_REPLACE_ONLY": "PASS" if photo and field and has("headline") else "FAIL",
    }
    return {
        "schema": "GraphicFieldRevisionReadinessV1",
        "revision_readiness": "PASS" if all(v == "PASS" for v in checks.values()) else "FAIL",
        "checks": checks,
        "executed": False,
        "note": "Static readiness only. Phase 5.5 was not executed.",
    }
