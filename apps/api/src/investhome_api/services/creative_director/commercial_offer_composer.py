"""CommercialOfferComposerV1 — price, advantage, label, unit as one designed system."""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw, ImageFont

from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.structured_typography_compositor_v2 import _draw_tracked


def measure_tracked(text: str, font: ImageFont.ImageFont, tracking: float = 0) -> tuple[int, int]:
    size = float(getattr(font, "size", 32) or 32)
    gap = tracking / 1000.0 * size
    widths = [font.getlength(ch) for ch in text]
    total = sum(widths) + gap * max(0, len(text) - 1)
    bbox = font.getbbox(text)
    height = max(int(bbox[3] - bbox[1]), int(size * 0.82))
    return int(total + 0.5), height


def measure_production_copy(
    *,
    fonts: dict[str, Any],
    family: dict[str, Any],
    canvas: tuple[int, int],
    scale: float,
) -> dict[str, Any]:
    from investhome_api.services.creative_director.creative_font_registry import font_for_role

    w, h = canvas
    typo = dict(family.get("typography") or {})
    family_id = str(family.get("family_id") or "")
    display_h = max(28, int(h * float(typo.get("display_scale") or 0.07) * scale))
    support_h = max(14, int(h * float(typo.get("secondary_scale") or 0.02) * scale))
    number_h = max(26, int(h * float(typo.get("number_scale") or 0.046) * scale))
    if family_id == "TYPE_IN_PLANE":
        number_h = max(number_h, int(display_h * 0.92))
    cta_h = max(13, int(h * 0.018 * scale))
    display = font_for_role(fonts, str(typo.get("display_role") or "DISPLAY_SERIF"), display_h)
    display_gold = font_for_role(fonts, str(typo.get("display_role") or "DISPLAY_SERIF"), int(display_h * 1.16))
    sans = font_for_role(fonts, "EDITORIAL_SANS", support_h)
    number = font_for_role(fonts, "COMMERCIAL_NUMBER", number_h)
    discount_font = font_for_role(fonts, "COMMERCIAL_NUMBER", max(22, int(number_h * 0.78)))
    cta_font = font_for_role(fonts, "CTA", cta_h)
    headline = REQUIRED_FACTS["headline"]
    first, last = (headline.split(" ", 1) + [""])[:2]
    unit = f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}"
    lines = {
        "headline": {"text": headline, "font": display, "tracking": float(typo.get("tracking_display") or 20)},
        "headline_first": {"text": first, "font": display, "tracking": float(typo.get("tracking_display") or 30)},
        "headline_last": {"text": last, "font": display_gold, "tracking": 20.0},
        "unit_type": {"text": unit, "font": sans, "tracking": float(typo.get("tracking_support") or 160)},
        "price": {"text": REQUIRED_FACTS["list_price"], "font": number, "tracking": 8.0},
        "discount": {"text": REQUIRED_FACTS["discount"], "font": discount_font, "tracking": 8.0},
        "discount_label": {"text": REQUIRED_FACTS["discount_label"], "font": sans, "tracking": 180.0},
        "cta": {"text": REQUIRED_FACTS["cta"], "font": cta_font, "tracking": float(typo.get("tracking_cta") or 220)},
    }
    measured = {}
    for key, spec in lines.items():
        mw, mh = measure_tracked(spec["text"], spec["font"], spec["tracking"])
        measured[key] = {
            **spec,
            "width": mw,
            "height": mh,
            "placeholder": False,
        }
        if mw < 24 or mh < 10:
            raise RuntimeError(f"typography metric too small for {key}: {mw}x{mh}")
    measured["fonts"] = {
        "display_h": display_h,
        "support_h": support_h,
        "number_h": number_h,
        "cta_h": cta_h,
        "scale": scale,
    }
    return measured


def offer_layout(
    *,
    origin: tuple[int, int],
    alignment: str,
    metrics: dict[str, Any],
    spacing: dict[str, Any],
    canvas: tuple[int, int],
    family_id: str,
    include_headline: bool = False,
) -> dict[str, Any]:
    """Pixel positions for the commercial system. Headline is optional so the engine can stack it first."""
    ox, y = origin
    _w, h = canvas
    anchor = "rt" if alignment == "right" else "mt" if alignment == "center" else "lt"
    boxes: dict[str, tuple[int, int, int, int]] = {}
    order: list[str] = []

    def place(role: str, gap_after: float) -> tuple[int, int, int, int]:
        nonlocal y
        item = metrics[role]
        tw, th = int(item["width"]), int(item["height"])
        if alignment == "right":
            box = (ox - tw, y, ox, y + th)
        elif alignment == "center":
            box = (ox - tw // 2, y, ox + tw // 2, y + th)
        else:
            box = (ox, y, ox + tw, y + th)
        boxes[role] = box
        order.append(role)
        y = box[3] + int(h * gap_after)
        return box

    if include_headline:
        if family_id in {"EDITORIAL_DARK_FIELD", "TYPE_IN_PLANE"}:
            place("headline_first", 0.006)
            place("headline_last", float(spacing.get("after_headline") or 0.02))
        else:
            place("headline", float(spacing.get("after_headline") or 0.02))
    unit_box = place("unit_type", float(spacing.get("after_unit") or 0.016))
    price_box = place("price", float(spacing.get("after_price") or 0.012))
    disc = metrics["discount"]
    label = metrics["discount_label"]
    dw, dh = int(disc["width"]), int(disc["height"])
    lw, lh = int(label["width"]), int(label["height"])
    if family_id == "SKY_EDITORIAL":
        gap = 18
        pair_w = dw + gap + lw
        if alignment == "right":
            x0 = ox - pair_w
        elif alignment == "center":
            x0 = ox - pair_w // 2
        else:
            x0 = ox
        disc_box = (x0, y, x0 + dw, y + dh)
        label_box = (x0 + dw + gap, y + max(0, dh - lh), x0 + pair_w, y + max(dh, lh))
        boxes["discount"] = disc_box
        boxes["discount_label"] = label_box
        y = max(disc_box[3], label_box[3]) + int(h * float(spacing.get("after_offer") or 0.04))
    else:
        disc_box = place("discount", 0.006)
        label_box = place("discount_label", float(spacing.get("after_offer") or 0.04))
    group = (
        min(unit_box[0], price_box[0], disc_box[0], label_box[0]),
        unit_box[1],
        max(unit_box[2], price_box[2], disc_box[2], label_box[2]),
        max(unit_box[3], price_box[3], disc_box[3], label_box[3]),
    )
    hierarchy = {
        "price_prominence": price_box[3] - price_box[1],
        "discount_height": disc_box[3] - disc_box[1],
        "discount_not_tiny": (disc_box[3] - disc_box[1]) >= max(20, int(0.45 * (price_box[3] - price_box[1]))),
        "grouped": (label_box[1] - disc_box[3]) <= int(h * 0.03) or abs(label_box[1] - disc_box[1]) <= int(h * 0.02),
    }
    return {
        "schema": "CommercialOfferComposerV1",
        "alignment": alignment,
        "anchor": anchor,
        "boxes": boxes,
        "group_px": group,
        "cursor_y": y,
        "origin": origin,
        "hierarchy": hierarchy,
        "pass": bool(hierarchy["discount_not_tiny"] and hierarchy["grouped"] and (price_box[3] - price_box[1]) >= 26),
    }


def draw_line(
    draw: ImageDraw.ImageDraw,
    *,
    origin_x: int,
    y: int,
    role_metrics: dict[str, Any],
    fill: tuple[int, int, int],
    alignment: str,
) -> tuple[int, int, int, int]:
    return _draw_tracked(
        draw,
        (origin_x, y),
        role_metrics["text"],
        role_metrics["font"],
        fill,
        tracking=float(role_metrics.get("tracking") or 0),
        anchor="rt" if alignment == "right" else "mt" if alignment == "center" else "lt",
    )


def render_commercial_proof(image: Image.Image, objects: dict[str, dict[str, Any]], key: str) -> Image.Image:
    roles = ("unit_type", "price", "discount", "discount_label")
    boxes = []
    for role in roles:
        px = (objects.get(role) or {}).get("px")
        if isinstance(px, (list, tuple)) and len(px) == 4:
            boxes.append(tuple(int(v) for v in px))
    if not boxes:
        return Image.new("RGB", (640, 240), (12, 14, 20))
    x0 = max(0, min(b[0] for b in boxes) - 24)
    y0 = max(0, min(b[1] for b in boxes) - 24)
    x1 = min(image.size[0], max(b[2] for b in boxes) + 24)
    y1 = min(image.size[1], max(b[3] for b in boxes) + 24)
    crop = image.convert("RGB").crop((x0, y0, x1, y1))
    canvas = Image.new("RGB", (max(720, crop.width + 40), crop.height + 70), (12, 14, 20))
    canvas.paste(crop, (20, 44))
    draw = ImageDraw.Draw(canvas)
    draw.text((20, 12), f"{key}  COMMERCIAL GROUP  —  one system, not floating labels", fill=(201, 168, 92))
    return canvas


def offer_layout_v2(
    *,
    origin: tuple[int, int],
    metrics: dict[str, Any],
    canvas: tuple[int, int],
    geometry: str = "stacked_statement",
) -> dict[str, Any]:
    """One designed commercial statement. Not four independent text objects."""
    ox, oy = origin
    _w, h = canvas
    disc = metrics["discount"]
    label = metrics["discount_label"]
    price = metrics["price"]
    dw, dh = int(disc["width"]), int(disc["height"])
    lw, lh = int(label["width"]), int(label["height"])
    pw, ph = int(price["width"]), int(price["height"])
    gap = max(6, int(h * 0.008))
    if geometry == "paired_row":
        disc_box = (ox, oy, ox + dw, oy + dh)
        label_box = (ox, disc_box[3] + 4, ox + lw, disc_box[3] + 4 + lh)
        pair_r = max(disc_box[2], label_box[2])
        rule = (pair_r + int(_w * 0.016), oy + 4, pair_r + int(_w * 0.016) + 2, max(label_box[3], oy + ph))
        price_x = rule[2] + int(_w * 0.018)
        price_y = oy + max(0, (max(dh + 4 + lh, ph) - ph) // 2)
        price_box = (price_x, price_y, price_x + pw, price_y + ph)
    else:
        disc_box = (ox, oy, ox + dw, oy + dh)
        label_box = (ox, disc_box[3] + 4, ox + lw, disc_box[3] + 4 + lh)
        price_box = (ox, label_box[3] + gap, ox + pw, label_box[3] + gap + ph)
        rule = (ox, label_box[3] + 2, max(disc_box[2], label_box[2], price_box[2]), label_box[3] + 3)
    group = (
        min(disc_box[0], label_box[0], price_box[0]),
        min(disc_box[1], label_box[1], price_box[1]),
        max(disc_box[2], label_box[2], price_box[2]),
        max(disc_box[3], label_box[3], price_box[3]),
    )
    return {
        "schema": "CommercialOfferComposerV2",
        "primary_commercial_anchor": "discount",
        "secondary_commercial_fact": "price",
        "supporting_descriptor": "discount_label",
        "relationship_geometry": geometry,
        "scale_ratio": round(dh / max(ph, 1), 3),
        "spacing_rhythm": gap,
        "shared_alignment": "left",
        "shared_graphic_device": "editorial_rule",
        "boxes": {"discount": disc_box, "discount_label": label_box, "price": price_box},
        "rule_px": rule,
        "group_px": group,
        "independent_objects": False,
    }
