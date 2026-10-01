"""Immutable Day_007 photographic object. Crop, scale, mask, grade. Never rewrite pixels."""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageOps

from investhome_api.services.creative_director.commercial_number_renderer import render_percent, render_price
from investhome_api.services.creative_director.creative_font_registry import build_font_registry, font_for_role
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5, apply_photographic_grade
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase7_2_doctrine import PHOTO_MAX_MASS, PHOTO_MIN_MASS
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY, _draw_tracked
from investhome_api.services.gpt_image_design.compose import _fit_logo

W, H = CANVAS_4X5
SLOT_FILL = (186, 28, 118)

SEEDED_LAYOUTS: dict[str, dict[str, Any]] = {
    "A": {
        "photo_role": "full_height_photographic_plane",
        "photo_shape": "rect",
        "photo_box": {"x": 0.40, "y": 0.0, "w": 0.60, "h": 0.88},
        "centering": (0.68, 0.18),
        "brand_box": {"x": 0.055, "y": 0.045, "w": 0.28, "h": 0.11},
        "headline": {"x": 0.055, "y": 0.20, "w": 0.32, "h": 0.07},
        "offer": {"x": 0.055, "y": 0.30, "w": 0.32, "h": 0.12},
        "price": {"x": 0.055, "y": 0.45, "w": 0.32, "h": 0.10},
        "unit": {"x": 0.055, "y": 0.57, "w": 0.28, "h": 0.06},
        "cta": {"x": 0.055, "y": 0.70, "w": 0.26, "h": 0.055},
        "closure": {"x": 0.12, "y": 0.915, "w": 0.76, "h": 0.05},
        "grade": {"warmth": 0.18, "contrast": 1.04, "brightness": 0.98},
    },
    "B": {
        "photo_role": "architectural_window",
        "photo_shape": "rounded",
        "photo_box": {"x": 0.07, "y": 0.07, "w": 0.86, "h": 0.48},
        "centering": (0.62, 0.16),
        "brand_box": {"x": 0.07, "y": 0.58, "w": 0.22, "h": 0.09},
        "headline": {"x": 0.32, "y": 0.58, "w": 0.60, "h": 0.07},
        "offer": {"x": 0.07, "y": 0.70, "w": 0.40, "h": 0.10},
        "price": {"x": 0.50, "y": 0.70, "w": 0.42, "h": 0.10},
        "unit": {"x": 0.07, "y": 0.82, "w": 0.28, "h": 0.05},
        "cta": {"x": 0.62, "y": 0.82, "w": 0.30, "h": 0.055},
        "closure": {"x": 0.14, "y": 0.92, "w": 0.72, "h": 0.05},
        "grade": {"warmth": 0.12, "contrast": 1.06, "brightness": 1.0},
    },
    "C": {
        "photo_role": "offset_photographic_cutout",
        "photo_shape": "ellipse",
        "photo_box": {"x": 0.08, "y": 0.16, "w": 0.52, "h": 0.70},
        "centering": (0.70, 0.20),
        "brand_box": {"x": 0.64, "y": 0.07, "w": 0.30, "h": 0.11},
        "headline": {"x": 0.64, "y": 0.24, "w": 0.31, "h": 0.08},
        "offer": {"x": 0.64, "y": 0.36, "w": 0.31, "h": 0.12},
        "price": {"x": 0.64, "y": 0.51, "w": 0.31, "h": 0.10},
        "unit": {"x": 0.64, "y": 0.64, "w": 0.28, "h": 0.06},
        "cta": {"x": 0.64, "y": 0.76, "w": 0.28, "h": 0.055},
        "closure": {"x": 0.14, "y": 0.915, "w": 0.72, "h": 0.05},
        "grade": {"warmth": 0.22, "contrast": 1.03, "brightness": 0.97},
    },
}


def _box(raw: Any, fallback: dict[str, float]) -> dict[str, float]:
    src = raw if isinstance(raw, dict) else {}
    return {
        "x": max(0.0, min(0.92, float(src.get("x", fallback["x"])))),
        "y": max(0.0, min(0.94, float(src.get("y", fallback["y"])))),
        "w": max(0.12, min(0.92, float(src.get("w", fallback["w"])))),
        "h": max(0.05, min(0.92, float(src.get("h", fallback["h"])))),
    }


def _px(box: dict[str, float]) -> tuple[int, int, int, int]:
    x0 = int(round(box["x"] * W))
    y0 = int(round(box["y"] * H))
    x1 = min(W, int(round((box["x"] + box["w"]) * W)))
    y1 = min(H, int(round((box["y"] + box["h"]) * H)))
    return x0, y0, max(x0 + 8, x1), max(y0 + 8, y1)


def clamp_photo_mass(box: dict[str, float]) -> dict[str, float]:
    out = dict(box)
    area = max(0.01, out["w"] * out["h"])
    if area < PHOTO_MIN_MASS:
        scale = (PHOTO_MIN_MASS / area) ** 0.5
        out["w"] = min(0.92, out["w"] * scale)
        out["h"] = min(0.92, out["h"] * scale)
    area = max(0.01, out["w"] * out["h"])
    if area > PHOTO_MAX_MASS:
        scale = (PHOTO_MAX_MASS / area) ** 0.5
        out["w"] *= scale
        out["h"] *= scale
    if out["x"] + out["w"] > 1.0:
        out["x"] = max(0.0, 1.0 - out["w"])
    if out["y"] + out["h"] > 0.90:
        out["y"] = max(0.0, 0.90 - out["h"])
    return out


def photo_percentage(box: dict[str, float]) -> float:
    return round(float(box["w"] * box["h"]), 4)


def _overlap_area(a: dict[str, float], b: dict[str, float]) -> float:
    ix = max(0.0, min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"]))
    iy = max(0.0, min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"]))
    return ix * iy


def merge_layout(candidate_id: str, raw: dict[str, Any] | None) -> dict[str, Any]:
    seed = dict(SEEDED_LAYOUTS[candidate_id])
    data = dict(raw or {})
    seed["photo_box"] = clamp_photo_mass(dict(seed["photo_box"]))
    photo = seed["photo_box"]
    if data.get("visual_idea"):
        seed["visual_idea"] = str(data.get("visual_idea"))
    for key in ("brand_box", "headline", "offer", "price", "unit", "cta", "closure"):
        proposed = _box(data.get(key), seed[key])
        if _overlap_area(proposed, photo) > 0.35 * proposed["w"] * proposed["h"]:
            proposed = dict(seed[key])
        seed[key] = proposed
    return seed


def render_slot_map(layout: dict[str, Any]) -> Image.Image:
    canvas = Image.new("RGB", CANVAS_4X5, (14, 16, 22))
    draw = ImageDraw.Draw(canvas)
    box = _px(layout["photo_box"])
    shape = layout.get("photo_shape") or "rect"
    if shape == "ellipse":
        draw.ellipse(box, fill=SLOT_FILL, outline=(201, 168, 92), width=6)
    elif shape == "rounded":
        draw.rounded_rectangle(box, radius=max(18, (box[2] - box[0]) // 28), fill=SLOT_FILL, outline=(201, 168, 92), width=6)
    else:
        draw.rectangle(box, fill=SLOT_FILL, outline=(201, 168, 92), width=6)
    brand = _px(layout["brand_box"])
    draw.rectangle(brand, outline=(180, 176, 168), width=2)
    return canvas


def _object_mask(size: tuple[int, int], shape: str) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    inset = (1, 1, size[0] - 2, size[1] - 2)
    if shape == "ellipse":
        draw.ellipse(inset, fill=255)
    elif shape == "rounded":
        draw.rounded_rectangle(inset, radius=max(16, min(size) // 18), fill=255)
    else:
        draw.rectangle(inset, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(radius=1.2))


def place_photo_object(
    canvas: Image.Image,
    source: Image.Image,
    layout: dict[str, Any],
) -> tuple[Image.Image, dict[str, Any]]:
    box = layout["photo_box"]
    x0, y0, x1, y1 = _px(box)
    tw, th = x1 - x0, y1 - y0
    centering = layout.get("centering") or (0.68, 0.20)
    crop = ImageOps.fit(source.convert("RGB"), (tw, th), method=Image.Resampling.LANCZOS, centering=centering)
    crop = apply_photographic_grade(crop, dict(layout.get("grade") or {}))
    mask = _object_mask((tw, th), str(layout.get("photo_shape") or "rect"))
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sh = Image.new("L", (tw, th), 0)
    sh.paste(mask.point(lambda p: int(p * 0.55)))
    sh = sh.filter(ImageFilter.GaussianBlur(radius=max(8, min(tw, th) * 0.04)))
    shadow.paste((0, 0, 0, 160), (x0 + 10, y0 + 14), sh)
    out = Image.alpha_composite(canvas.convert("RGBA"), shadow)
    layer = Image.new("RGBA", out.size, (0, 0, 0, 0))
    layer.paste(crop.convert("RGBA"), (x0, y0), mask)
    out = Image.alpha_composite(out, layer)
    meta = {
        "source": "REAL_DAY_007",
        "box": [x0, y0, x1, y1],
        "shape": layout.get("photo_shape"),
        "role": layout.get("photo_role"),
        "percentage": photo_percentage(box),
        "internal_generated_pixels": 0,
        "geometry_modification": 0,
        "transforms": ["uniform_scale", "crop", "position", "mask", "color_grade", "shadow_outside"],
    }
    return out.convert("RGB"), meta


def paste_real_logo(canvas: Image.Image, logo_rgba: Image.Image, layout: dict[str, Any]) -> Image.Image:
    x0, y0, x1, y1 = _px(layout["brand_box"])
    mark = _fit_logo(logo_rgba, max(8, x1 - x0), max(8, y1 - y0))
    gold = Image.new("RGBA", mark.size, (212, 184, 122, 0))
    gold.putalpha(mark.getchannel("A"))
    out = canvas.convert("RGBA")
    layer = Image.new("RGBA", out.size, (0, 0, 0, 0))
    layer.paste(gold, (x0, y0), gold)
    return Image.alpha_composite(out, layer).convert("RGB")


def _fit_size(font_fn, text: str, max_w: int, start: int, floor: int = 18) -> Any:
    size = start
    font = font_fn(size)
    while size > floor and font.getlength(text) > max_w:
        size -= 2
        font = font_fn(size)
    return font


def paint_campaign_content(canvas: Image.Image, layout: dict[str, Any]) -> Image.Image:
    registry = build_font_registry()
    out = canvas.convert("RGB")
    draw = ImageDraw.Draw(out)

    def face(role: str, size: int):
        return font_for_role(registry, role, size)

    hx0, hy0, hx1, hy1 = _px(layout["headline"])
    hfont = _fit_size(lambda s: face("DISPLAY_SANS", s), REQUIRED_FACTS["headline"], hx1 - hx0, min(48, hy1 - hy0))
    draw.text((hx0, hy0), REQUIRED_FACTS["headline"], font=hfont, fill=IVORY)

    ox0, oy0, ox1, oy1 = _px(layout["offer"])
    pfont = face("COMMERCIAL_NUMBER", min(92, oy1 - oy0 + 8))
    lfont = face("BODY", min(22, max(16, (oy1 - oy0) // 3)))
    percent_box = render_percent(
        draw,
        origin=(ox0, oy0),
        text=REQUIRED_FACTS["discount"],
        font=pfont,
        fill=GOLD,
        alignment="left",
    )
    draw.text((percent_box[2] + 12, oy0 + 18), REQUIRED_FACTS["discount_label"], font=lfont, fill=IVORY)

    px0, py0, px1, py1 = _px(layout["price"])
    nfont = _fit_size(lambda s: face("COMMERCIAL_NUMBER", s), REQUIRED_FACTS["list_price"], px1 - px0, min(72, py1 - py0 + 10))
    cfont = face("BODY", max(16, int(getattr(nfont, "size", 36) * 0.38)))
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
        min(40, uy1 - uy0 + 6),
    )
    draw.text((ux0, uy0), f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}", font=ufont, fill=IVORY)

    cx0, cy0, cx1, cy1 = _px(layout["cta"])
    pad = 10
    draw.rectangle((cx0, cy0, cx1, cy1), outline=GOLD, width=2)
    cta_font = _fit_size(lambda s: face("CTA", s), REQUIRED_FACTS["cta"], cx1 - cx0 - 20, min(22, cy1 - cy0 - 8))
    draw.text((cx0 + pad, cy0 + pad), REQUIRED_FACTS["cta"], font=cta_font, fill=IVORY)

    ex0, ey0, ex1, ey1 = _px(layout["closure"])
    efont = face("BODY", 16)
    _draw_tracked(draw, ((ex0 + ex1) / 2, ey0), APPROVED_BOTTOM_COPY, efont, IVORY, tracking=180, anchor="mt")
    return out


def compose_candidate(
    *,
    graphic_canvas: Image.Image,
    photo: Image.Image,
    logo_rgba: Image.Image,
    layout: dict[str, Any],
) -> tuple[Image.Image, dict[str, Any]]:
    base = graphic_canvas.convert("RGB")
    if base.size != CANVAS_4X5:
        base = base.resize(CANVAS_4X5, Image.Resampling.LANCZOS)
    placed, photo_meta = place_photo_object(base, photo, layout)
    branded = paste_real_logo(placed, logo_rgba, layout)
    final = paint_campaign_content(branded, layout)
    photo_meta["generated_logo_pixels"] = 0
    photo_meta["duplicate_temple_logo"] = False
    return final, photo_meta
