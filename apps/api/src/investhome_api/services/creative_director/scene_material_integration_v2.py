"""SceneMaterialIntegrationV2 + ContactOcclusionModelV1.

Non-destructive tonal adaptation of a real project object to a generated
non-project field. Shadows exist only where composition gives them a reason.
No generative relighting. No new architectural pixels.
"""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageStat

from investhome_api.services.creative_director.phase5_photo_foundation import apply_photographic_grade

SCHEMA = "SceneMaterialIntegrationV2"
CONTACT_SCHEMA = "ContactOcclusionModelV1"


def _lum_image(rgb: Image.Image) -> Image.Image:
    return rgb.convert("L")


def analyze_field(field: Image.Image) -> dict[str, Any]:
    rgb = field.convert("RGB")
    w, h = rgb.size
    upper = rgb.crop((0, 0, int(w * 0.45), int(h * 0.38)))
    mid = rgb.crop((int(w * 0.18), int(h * 0.18), int(w * 0.82), int(h * 0.58)))
    paper = rgb.crop((int(w * 0.16), int(h * 0.58), int(w * 0.84), int(h * 0.94)))
    def stats(im: Image.Image) -> dict[str, float]:
        r, g, b = im.split()
        rs, gs, bs = ImageStat.Stat(r).mean[0], ImageStat.Stat(g).mean[0], ImageStat.Stat(b).mean[0]
        lum = 0.2126 * rs + 0.7152 * gs + 0.0722 * bs
        temp = (rs - bs) / max(lum, 1.0)
        return {"lum": round(lum, 2), "temp": round(temp, 4), "r": round(rs, 1), "g": round(gs, 1), "b": round(bs, 1)}
    u, m, p = stats(upper), stats(mid), stats(paper)
    # Upper-left brighter than lower-right => light from UL.
    direction = "upper_left" if u["lum"] >= m["lum"] else "diffuse"
    return {
        "upper_left": u,
        "object_zone": m,
        "paper": p,
        "light_direction": direction,
        "environment": "museum_editorial" if m["lum"] < 95 else "bright_editorial",
    }


def analyze_object(obj: Image.Image) -> dict[str, Any]:
    rgb = obj.convert("RGB")
    alpha = obj.split()[-1] if obj.mode == "RGBA" else Image.new("L", obj.size, 255)
    hard = alpha.point(lambda v: 255 if v > 140 else 0)
    r, g, b = rgb.split()
    def masked_mean(ch: Image.Image) -> float:
        acc = n = 0.0
        cp, hp = ch.load(), hard.load()
        w, h = ch.size
        for y in range(0, h, 3):
            for x in range(0, w, 3):
                if hp[x, y] > 128:
                    acc += cp[x, y]
                    n += 1
        return acc / max(n, 1)
    rs, gs, bs = masked_mean(r), masked_mean(g), masked_mean(b)
    lum = 0.2126 * rs + 0.7152 * gs + 0.0722 * bs
    temp = (rs - bs) / max(lum, 1.0)
    return {"lum": round(lum, 2), "temp": round(temp, 4), "r": round(rs, 1), "g": round(gs, 1), "b": round(bs, 1)}


def match_object_to_field(obj: Image.Image, field_stats: dict[str, Any]) -> tuple[Image.Image, dict[str, Any]]:
    """Same photograph. Exposure, white balance, highlight pull. No new pixels."""
    obj_stats = analyze_object(obj)
    zone = dict(field_stats.get("object_zone") or {})
    target_lum = float(zone.get("lum") or 70.0) * 1.35
    exposure = max(0.74, min(0.96, target_lum / max(obj_stats["lum"], 1.0)))
    field_temp = float(zone.get("temp") or 0.12)
    warmth = max(-0.08, min(0.16, (field_temp - obj_stats["temp"]) * 0.55))
    treatment = {
        "warmth": round(warmth, 3),
        "contrast": 1.04,
        "brightness": round(exposure, 3),
        "vignette": 0.06 if field_stats.get("environment") == "museum_editorial" else 0.0,
    }
    rgb = apply_photographic_grade(obj.convert("RGB"), treatment)
    # Pull daylight highlights toward museum ambient without inventing façade detail.
    hi = ImageEnhance.Brightness(rgb).enhance(0.97)
    rgb = Image.blend(rgb, hi, 0.35)
    out = obj.convert("RGBA")
    out = Image.merge("RGBA", (*rgb.split(), out.split()[-1]))
    return out, {
        "object_before": obj_stats,
        "field": field_stats,
        "treatment": treatment,
        "generative_relight": False,
        "architecture_pixels_invented": 0,
    }


def paper_luminance_mask(field: Image.Image) -> Image.Image:
    rgb = field.convert("RGB")
    w, h = rgb.size
    mask = Image.new("L", (w, h), 0)
    px, mp = rgb.load(), mask.load()
    for y in range(int(h * 0.48), h):
        for x in range(w):
            r, g, b = px[x, y]
            lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
            if lum > 128 and r > 118 and g > 108 and b < r + 12 and abs(r - g) < 36:
                mp[x, y] = 255
    return mask.filter(ImageFilter.MaxFilter(11)).filter(ImageFilter.MinFilter(7)).filter(ImageFilter.GaussianBlur(1.2))


def contact_occlusion_model(
    *,
    field: Image.Image,
    obj: Image.Image,
    layout: dict[str, int],
    field_stats: dict[str, Any],
) -> dict[str, Any]:
    """Physical contact on the paper surface. Not a full-silhouette drop shadow."""
    W, H = field.size
    paper = paper_luminance_mask(field)
    placed = obj.resize((layout["w"], layout["h"]), Image.Resampling.LANCZOS)
    alpha = placed.split()[-1]
    # Contact band: lowest 18% of the object, intersected with paper.
    band = Image.new("L", (W, H), 0)
    y0 = layout["y"] + int(layout["h"] * 0.82)
    ImageDraw.Draw(band).rectangle((0, y0, W, H), fill=255)
    stamp = Image.new("L", (W, H), 0)
    stamp.paste(alpha, (layout["x"], layout["y"]))
    contact = ImageChops.multiply(stamp, band)
    contact = ImageChops.multiply(contact, paper)
    ambient = contact.filter(ImageFilter.GaussianBlur(radius=7)).point(lambda v: int(v * 0.28))
    dx, dy = (10, 14) if field_stats.get("light_direction") == "upper_left" else (0, 10)
    cast_src = Image.new("L", (W, H), 0)
    cast_src.paste(alpha, (layout["x"] + dx, layout["y"] + dy))
    cast = ImageChops.multiply(cast_src, paper)
    cast = ImageChops.multiply(cast, band.filter(ImageFilter.GaussianBlur(18)))
    cast = cast.filter(ImageFilter.GaussianBlur(radius=11)).point(lambda v: int(v * 0.22))
    occlusion = Image.new("L", (W, H), 0)
    occ_y = layout["y"] + int(layout["h"] * 0.72)
    ImageDraw.Draw(occlusion).rectangle((0, occ_y, W, H), fill=255)
    occlusion = ImageChops.multiply(occlusion, paper)
    overlay = field.convert("RGBA")
    overlay.putalpha(occlusion)
    ambient_rgba = Image.new("RGBA", (W, H), (16, 12, 10, 0))
    ambient_rgba.putalpha(ambient)
    cast_rgba = Image.new("RGBA", (W, H), (12, 10, 8, 0))
    cast_rgba.putalpha(cast)
    model = {
        "schema": CONTACT_SCHEMA,
        "depth_order": ("field", "object", "paper_occlusion", "contact_shadow"),
        "field_in_front_of_object": "paper_over_feet",
        "object_in_front_of_field": "architecture_over_charcoal",
        "contact_feather_px": 7,
        "surface_contact": True,
        "local_ambient_shadow": True,
        "directional_cast_shadow": True,
        "cast_onto": "non_project_paper",
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
        "paper": paper,
    }


def object_layout(obj: Image.Image, paper: Image.Image, canvas: tuple[int, int]) -> dict[str, int]:
    W, H = canvas
    hard = paper.point(lambda v: 255 if v > 140 else 0)
    box = hard.getbbox() or (int(W * 0.18), int(H * 0.62), int(W * 0.82), int(H * 0.92))
    py0 = box[1]
    oh = int(H * 0.60)
    scale = oh / max(obj.size[1], 1)
    ow = max(1, int(obj.size[0] * scale))
    if ow > int(W * 0.80):
        scale = (W * 0.80) / max(obj.size[0], 1)
        ow = max(1, int(obj.size[0] * scale))
        oh = max(1, int(obj.size[1] * scale))
    x = (W - ow) // 2
    y = max(int(H * 0.06), py0 - int(oh * 0.68))
    return {"x": x, "y": y, "w": ow, "h": oh}


def integrate_object_into_field(field: Image.Image, obj: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    field_rgb = field.convert("RGB")
    stats = analyze_field(field_rgb)
    matched, match_meta = match_object_to_field(obj.convert("RGBA"), stats)
    paper = paper_luminance_mask(field_rgb)
    layout = object_layout(matched, paper, field_rgb.size)
    layers = contact_occlusion_model(field=field_rgb, obj=matched, layout=layout, field_stats=stats)
    plate = field_rgb.convert("RGBA")
    plate.paste(layers["placed"], (layout["x"], layout["y"]), layers["placed"])
    plate = Image.alpha_composite(plate, layers["overlay"])
    plate = Image.alpha_composite(plate, layers["ambient"])
    plate = Image.alpha_composite(plate, layers["cast"])
    meta = {
        "schema": SCHEMA,
        "match": match_meta,
        "contact": layers["model"],
        "generated_architecture_pixels": 0,
    }
    return plate.convert("RGB"), meta
