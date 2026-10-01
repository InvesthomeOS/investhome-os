"""THE_REGISTER scene integration — luminous atmosphere contact, not vellum paper.

Uses SceneMaterialIntegrationV2 match/analyze. ContactOcclusionModelV1 adapted
to a mineral light column instead of a cream paper plate.
"""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.project_object_extraction_v2 import _lum
from investhome_api.services.creative_director.scene_material_integration_v2 import (
    analyze_field,
    match_object_to_field,
)

W, H = CANVAS_4X5


def punch_residual_sky(obj: Image.Image) -> Image.Image:
    """Remove leftover photographic sky. Does not invent architecture pixels."""
    rgba = obj.convert("RGBA")
    px = rgba.load()
    w, h = rgba.size
    for y in range(h):
        yn = y / max(h - 1, 1)
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 8:
                continue
            sky = b >= r + 10 and b >= g + 4 and _lum(r, g, b) > 88
            pale_fringe = _lum(r, g, b) > 205 and (max(r, g, b) - min(r, g, b)) < 16 and b >= r - 2 and a < 250
            cool_crown = yn < 0.12 and b > r + 4 and _lum(r, g, b) > 70
            if sky or cool_crown or (yn < 0.28 and pale_fringe):
                px[x, y] = (r, g, b, 0)
    alpha = rgba.split()[-1]
    bbox = alpha.getbbox()
    return rgba.crop(bbox) if bbox else rgba


def lantern_preserved(obj: Image.Image) -> dict[str, Any]:
    """Day_009 crown is the right-hand lantern, not a full-width top band."""
    alpha = obj.split()[-1]
    w, h = obj.size
    band_h = max(8, int(h * 0.12))
    top = alpha.crop((int(w * 0.38), 0, w, band_h))
    bbox = top.getbbox()
    coverage = 0.0
    width_ratio = 0.0
    if bbox is not None:
        coverage = sum(top.getdata()) / (255.0 * top.size[0] * top.size[1])
        width_ratio = (bbox[2] - bbox[0]) / max(w, 1)
    preserved = coverage > 0.01 and width_ratio < 0.62
    return {"coverage": round(coverage, 4), "width_ratio": round(width_ratio, 4), "preserved": preserved}


def luminous_column_mask(field: Image.Image) -> Image.Image:
    """Brighter vertical shaft in the generated atmosphere — not a cream-paper heuristic."""
    rgb = field.convert("RGB")
    w, h = rgb.size
    lum = rgb.convert("L")
    lp = lum.load()
    mask = Image.new("L", (w, h), 0)
    mp = mask.load()
    # Column is the brighter central band; contact lives in the lower half.
    xs = list(range(int(w * 0.18), int(w * 0.82), 3))
    ys = list(range(int(h * 0.22), h, 2))
    samples = [lp[x, y] for y in ys for x in xs]
    samples.sort()
    floor = samples[int(len(samples) * 0.42)] if samples else 90
    for y in range(h):
        for x in range(w):
            v = lp[x, y]
            cx = abs((x / max(w - 1, 1)) - 0.52)
            if v >= floor - 8 and cx < 0.38:
                strength = min(255, int((v - (floor - 18)) * 2.2))
                fall = max(0.35, 1.0 - cx * 1.8)
                mp[x, y] = int(strength * fall)
    return mask.filter(ImageFilter.GaussianBlur(6))


def register_object_layout(obj: Image.Image, canvas: tuple[int, int] = (W, H)) -> dict[str, int]:
    cw, ch = canvas
    oh = int(ch * 0.82)
    scale = oh / max(obj.size[1], 1)
    ow = max(1, int(obj.size[0] * scale))
    if ow > int(cw * 0.78):
        scale = (cw * 0.78) / max(obj.size[0], 1)
        ow = max(1, int(obj.size[0] * scale))
        oh = max(1, int(obj.size[1] * scale))
    x = max(int(cw * 0.22), (cw - ow) // 2 - 18)
    y = max(int(ch * 0.04), int(ch * 0.93) - oh)
    return {"x": x, "y": y, "w": ow, "h": oh}


def contact_occlusion_register(
    *,
    field: Image.Image,
    obj: Image.Image,
    layout: dict[str, int],
    field_stats: dict[str, Any],
) -> dict[str, Any]:
    """Atmosphere over feet + local contact in the luminous column. No silhouette drop."""
    canvas_w, canvas_h = field.size
    column = luminous_column_mask(field)
    placed = obj.resize((layout["w"], layout["h"]), Image.Resampling.LANCZOS)
    alpha = placed.split()[-1]
    band = Image.new("L", (canvas_w, canvas_h), 0)
    y0 = layout["y"] + int(layout["h"] * 0.70)
    ImageDraw.Draw(band).rectangle((0, y0, canvas_w, canvas_h), fill=255)
    stamp = Image.new("L", (canvas_w, canvas_h), 0)
    stamp.paste(alpha, (layout["x"], layout["y"]))
    contact = ImageChops.multiply(stamp, band)
    contact = ImageChops.multiply(contact, column)
    ambient = contact.filter(ImageFilter.GaussianBlur(radius=8)).point(lambda v: int(v * 0.32))
    dx, dy = (6, 12) if field_stats.get("light_direction") == "upper_left" else (0, 9)
    cast_src = Image.new("L", (canvas_w, canvas_h), 0)
    cast_src.paste(alpha, (layout["x"] + dx, layout["y"] + dy))
    cast = ImageChops.multiply(cast_src, column)
    cast = ImageChops.multiply(cast, band.filter(ImageFilter.GaussianBlur(16)))
    cast = cast.filter(ImageFilter.GaussianBlur(radius=10)).point(lambda v: int(v * 0.18))
    occlusion = Image.new("L", (canvas_w, canvas_h), 0)
    occ_y = layout["y"] + int(layout["h"] * 0.72)
    ImageDraw.Draw(occlusion).rectangle((0, occ_y, canvas_w, canvas_h), fill=255)
    occlusion = ImageChops.multiply(occlusion, column)
    overlay = field.convert("RGBA")
    overlay.putalpha(occlusion.point(lambda v: int(v * 0.72)))
    ambient_rgba = Image.new("RGBA", (canvas_w, canvas_h), (14, 10, 8, 0))
    ambient_rgba.putalpha(ambient)
    cast_rgba = Image.new("RGBA", (canvas_w, canvas_h), (10, 8, 6, 0))
    cast_rgba.putalpha(cast)
    model = {
        "schema": "ContactOcclusionModelV1",
        "depth_order": ("field", "object", "atmosphere_occlusion", "contact_shadow"),
        "field_in_front_of_object": "atmosphere_over_feet",
        "object_in_front_of_field": "architecture_over_mineral_light",
        "contact_feather_px": 8,
        "surface_contact": True,
        "local_ambient_shadow": True,
        "directional_cast_shadow": True,
        "cast_onto": "non_project_luminous_column",
        "cast_reason": f"field light {field_stats.get('light_direction')}",
        "full_silhouette_drop_shadow": False,
        "layout": dict(layout),
    }
    return {
        "model": model,
        "placed": placed,
        "overlay": overlay,
        "ambient": ambient_rgba,
        "cast": cast_rgba,
        "column": column,
    }


def integrate_register(field: Image.Image, obj: Image.Image) -> dict[str, Any]:
    field_rgb = field.convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    stats = analyze_field(field_rgb)
    matched, match_meta = match_object_to_field(obj.convert("RGBA"), stats)
    matched = punch_residual_sky(matched)
    layout = register_object_layout(matched, field_rgb.size)
    layers = contact_occlusion_register(field=field_rgb, obj=matched, layout=layout, field_stats=stats)
    plate = field_rgb.convert("RGBA")
    plate = Image.alpha_composite(plate, layers["ambient"])
    plate = Image.alpha_composite(plate, layers["cast"])
    plate.paste(layers["placed"], (layout["x"], layout["y"]), layers["placed"])
    plate = Image.alpha_composite(plate, layers["overlay"])
    return {
        "field": field_rgb,
        "matched": matched,
        "fused": plate.convert("RGB"),
        "placed": layers["placed"],
        "overlay": layers["overlay"],
        "ambient": layers["ambient"],
        "cast": layers["cast"],
        "column": layers["column"],
        "layout": layout,
        "stats": stats,
        "match": match_meta,
        "contact": layers["model"],
        "generated_architecture_pixels": 0,
    }
