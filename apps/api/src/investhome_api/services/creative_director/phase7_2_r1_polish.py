"""Phase 7.2-R1 — optical polish of Candidate C. Not a redesign."""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageStat

from investhome_api.services.creative_director.commercial_number_renderer import render_percent, render_price
from investhome_api.services.creative_director.creative_font_registry import build_font_registry, font_for_role
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase7_2_photo_object import (
    W,
    H,
    _fit_size,
    _px,
    paste_real_logo,
    photo_percentage,
    place_photo_object,
)
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY, _draw_tracked

PARENT_C_ASSET_ID = "3d0ae3c4-5394-44bf-85f9-551337875b3c"

# Offset ellipse kept. Mass 0.55 * 0.82 = 0.451 (42–48%).
C_R1_LAYOUT: dict[str, Any] = {
    "photo_role": "offset_photographic_cutout",
    "photo_shape": "ellipse",
    "photo_box": {"x": 0.045, "y": 0.085, "w": 0.55, "h": 0.82},
    "centering": (0.64, 0.14),
    "brand_box": {"x": 0.62, "y": 0.075, "w": 0.30, "h": 0.10},
    "headline": {"x": 0.62, "y": 0.22, "w": 0.34, "h": 0.07},
    "offer": {"x": 0.62, "y": 0.32, "w": 0.34, "h": 0.16},
    "price": {"x": 0.62, "y": 0.52, "w": 0.34, "h": 0.08},
    "unit": {"x": 0.62, "y": 0.61, "w": 0.30, "h": 0.05},
    "cta": {"x": 0.62, "y": 0.74, "w": 0.28, "h": 0.048},
    "closure": {"x": 0.18, "y": 0.928, "w": 0.64, "h": 0.04},
    "grade": {"warmth": 0.16, "contrast": 1.05, "brightness": 0.99},
}


def quiet_commercial_column(parent: Image.Image) -> Image.Image:
    """Feather C's right type/logo stack back into the charcoal field. Keep left gold language."""
    rgb = parent.convert("RGB")
    sample = rgb.crop((int(W * 0.88), int(H * 0.48), int(W * 0.96), int(H * 0.58)))
    mean = tuple(int(v) for v in ImageStat.Stat(sample).mean[:3])
    if sum(mean) > 140:
        mean = (16, 16, 20)
    field = Image.new("RGB", rgb.size, mean)
    mask = Image.new("L", rgb.size, 0)
    ImageDraw.Draw(mask).rectangle((int(W * 0.575), int(H * 0.02), W, int(H * 0.90)), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=22))
    return Image.composite(field, rgb, mask)


def stroke_ellipse(canvas: Image.Image, layout: dict[str, Any]) -> Image.Image:
    x0, y0, x1, y1 = _px(layout["photo_box"])
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.ellipse((x0 - 2, y0 - 2, x1 + 2, y1 + 2), outline=(*GOLD, 230), width=3)
    return Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")


def paint_polished_story(canvas: Image.Image, layout: dict[str, Any]) -> Image.Image:
    registry = build_font_registry()
    out = canvas.convert("RGB")
    draw = ImageDraw.Draw(out)

    def face(role: str, size: int):
        return font_for_role(registry, role, size)

    hx0, hy0, hx1, hy1 = _px(layout["headline"])
    hfont = _fit_size(lambda s: face("DISPLAY_SANS", s), REQUIRED_FACTS["headline"], hx1 - hx0, 42, floor=22)
    draw.text((hx0, hy0), REQUIRED_FACTS["headline"], font=hfont, fill=IVORY)

    ox0, oy0, ox1, oy1 = _px(layout["offer"])
    pfont = face("COMMERCIAL_NUMBER", min(86, oy1 - oy0 - 18))
    percent_box = render_percent(
        draw,
        origin=(ox0, oy0),
        text=REQUIRED_FACTS["discount"],
        font=pfont,
        fill=GOLD,
        alignment="left",
    )
    lfont = face("BODY", 18)
    _draw_tracked(
        draw,
        (ox0, percent_box[3] + 6),
        REQUIRED_FACTS["discount_label"],
        lfont,
        IVORY,
        tracking=90,
        anchor="lt",
    )

    px0, py0, px1, py1 = _px(layout["price"])
    nfont = _fit_size(lambda s: face("COMMERCIAL_NUMBER", s), REQUIRED_FACTS["list_price"], px1 - px0, 48, floor=28)
    cfont = face("BODY", max(14, int(getattr(nfont, "size", 36) * 0.36)))
    render_price(
        draw,
        origin=(px0, py0),
        text=REQUIRED_FACTS["list_price"],
        number_font=nfont,
        currency_font=cfont,
        fill=GOLD,
        alignment="left",
    )

    ux0, uy0, ux1, uy1 = _px(layout["unit"])
    ufont = _fit_size(
        lambda s: face("EDITORIAL_SERIF", s),
        f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}",
        ux1 - ux0,
        28,
        floor=18,
    )
    draw.text((ux0, uy0), f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}", font=ufont, fill=IVORY)

    cx0, cy0, cx1, cy1 = _px(layout["cta"])
    cta_font = _fit_size(lambda s: face("CTA", s), REQUIRED_FACTS["cta"], cx1 - cx0, 18, floor=14)
    _draw_tracked(draw, (cx0, cy0 + 8), REQUIRED_FACTS["cta"], cta_font, IVORY, tracking=40, anchor="lt")
    bbox = draw.textbbox((cx0, cy0 + 8), REQUIRED_FACTS["cta"], font=cta_font)
    draw.line((cx0, bbox[3] + 6, min(cx1, bbox[2] + 8), bbox[3] + 6), fill=GOLD, width=1)

    ex0, ey0, ex1, ey1 = _px(layout["closure"])
    efont = face("BODY", 14)
    _draw_tracked(draw, ((ex0 + ex1) / 2, ey0), APPROVED_BOTTOM_COPY, efont, (200, 196, 188), tracking=220, anchor="mt")
    return out


def polish_candidate_c(
    *,
    parent: Image.Image,
    photo: Image.Image,
    logo_rgba: Image.Image,
) -> tuple[Image.Image, dict[str, Any]]:
    layout = dict(C_R1_LAYOUT)
    quiet = quiet_commercial_column(parent)
    placed, photo_meta = place_photo_object(quiet, photo, layout)
    stroked = stroke_ellipse(placed, layout)
    branded = paste_real_logo(stroked, logo_rgba, layout)
    final = paint_polished_story(branded, layout)
    photo_meta["generated_logo_pixels"] = 0
    photo_meta["duplicate_temple_logo"] = False
    photo_meta["generated_the_temple_wordmark"] = 0
    photo_meta["percentage_before"] = 0.364
    photo_meta["percentage"] = photo_percentage(layout["photo_box"])
    photo_meta["layout"] = layout
    return final, photo_meta


def render_reading_flow(image: Image.Image, layout: dict[str, Any]) -> Image.Image:
    canvas = image.convert("RGB").copy()
    draw = ImageDraw.Draw(canvas)
    steps = (
        ("1  HEADLINE", layout["headline"], (236, 230, 218)),
        ("2  OFFER", layout["offer"], GOLD),
        ("3  PRICE", layout["price"], GOLD),
        ("4  UNIT", layout["unit"], (236, 230, 218)),
        ("5  CTA", layout["cta"], GOLD),
    )
    for label, box, color in steps:
        x0, y0, x1, y1 = _px(box)
        draw.rectangle((x0 - 4, y0 - 4, x1 + 4, y1 + 4), outline=color, width=2)
        draw.text((x0, max(8, y0 - 22)), label, fill=color)
    bx0, by0, bx1, by1 = _px(layout["brand_box"])
    draw.rectangle((bx0 - 4, by0 - 4, bx1 + 4, by1 + 4), outline=(140, 190, 190), width=2)
    draw.text((bx0, max(8, by0 - 22)), "BRAND", fill=(140, 190, 190))
    px0, py0, px1, py1 = _px(layout["photo_box"])
    draw.ellipse((px0, py0, px1, py1), outline=(80, 200, 120), width=2)
    return canvas
