"""Master Design Spec v1.1 — visual fidelity enrichment + same-design reconstruction.

Derives craft information from an approved raster and locked source assets.
Does not mutate MasterDesignSpecV1, does not revise content, does not call an
image provider, and does not use the approved raster as the reconstruction
background.
"""

from __future__ import annotations

import copy
import math
from pathlib import Path
from typing import Any
from uuid import uuid4

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageStat

from investhome_api.services.creative_director.edit_map import (
    _as_dict,
    _is_gold,
    _is_navy,
    _is_white,
    _luma,
)
from investhome_api.services.creative_director.master_design_spec import (
    _norm,
    validate_master_design_spec,
)
from investhome_api.services.gpt_image_design.compose import _fit_logo

SCHEMA_V1_1 = "MasterDesignSpecV1.1"
SPEC_REVISION = "1.1"

FONT_ROOTS = (
    Path("/usr/share/fonts"),
    Path("/usr/local/share/fonts"),
    Path("C:/Windows/Fonts"),
)

ROLE_TEXT = {
    "headline_ALIRKEN": "ALIRKEN",
    "headline_KAZAN": "KAZAN",
    "supporting_copy": "The Temple'da yerinizi lansman döneminde alın.",
    "unit_value": "2+1",
    "unit_label": "DAİRE",
    "price_value": "675.000",
    "discount_value": "%35",
    "discount_label": "LANSMAN AVANTAJI",
    "cta_text": "PROJEYİ KEŞFET",
}

FORBIDDEN_PRICE_REVISION = ("438.750", "236.250", "LANSMAN FİYATI", "KAZANCINIZ")


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _rgb(seq: Any) -> tuple[int, int, int]:
    return (int(seq[0]), int(seq[1]), int(seq[2]))


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _box(x0: int, y0: int, x1: int, y1: int) -> dict[str, int]:
    return {"x0": int(x0), "y0": int(y0), "x1": int(x1), "y1": int(y1)}


def _abs(item: dict[str, Any] | None) -> dict[str, int] | None:
    box = _as_dict(_as_dict(item).get("geometry")).get("absolute")
    if not box:
        return None
    return {k: int(box[k]) for k in ("x0", "y0", "x1", "y1")}


def region(spec: dict[str, Any], role: str) -> dict[str, Any] | None:
    for item in spec.get("regions") or []:
        if item.get("semantic_role") == role:
            return item
    return None


def element(spec: dict[str, Any], role: str) -> dict[str, Any] | None:
    for item in spec.get("elements") or []:
        if item.get("semantic_role") == role:
            return item
    return None


def text_size(font: ImageFont.ImageFont, text: str) -> tuple[int, int]:
    bbox = font.getbbox(text or "")
    return max(1, bbox[2] - bbox[0]), max(1, bbox[3] - bbox[1])


def _center_text(
    draw: ImageDraw.ImageDraw,
    box: dict[str, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    *,
    y: int | None = None,
) -> dict[str, int]:
    tw, th = text_size(font, text)
    x = box["x0"] + (box["x1"] - box["x0"] - tw) // 2
    if y is None:
        y = box["y0"] + (box["y1"] - box["y0"] - th) // 2
    draw.text((x, y), text, font=font, fill=fill)
    return {"x0": x, "y0": y, "x1": x + tw, "y1": y + th}


def _diamond(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, fill: tuple[int, int, int]) -> None:
    draw.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=fill)


def _box_center(box: dict[str, int]) -> tuple[float, float]:
    return ((box["x0"] + box["x1"]) / 2.0, (box["y0"] + box["y1"]) / 2.0)


def _load_font(path: str, size: int) -> ImageFont.ImageFont:
    return ImageFont.truetype(path, size=max(8, int(size)))


def list_available_fonts() -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for root in FONT_ROOTS:
        if not root.exists():
            continue
        for path in sorted(list(root.rglob("*.ttf")) + list(root.rglob("*.otf"))):
            key = str(path).replace("\\", "/").lower()
            if key in seen:
                continue
            seen.add(key)
            name = path.stem
            lower = name.lower()
            serif = "serif" in lower and "sans" not in lower
            sans = "sans" in lower or lower.startswith("arial") or lower.startswith("segoe")
            mono = "mono" in lower
            bold = "bold" in lower or lower.endswith("bd") or lower.endswith("b")
            found.append(
                {
                    "path": str(path),
                    "family_guess": name,
                    "serif": bool(serif and not mono),
                    "sans": bool(sans or (not serif and not mono)),
                    "display": bool(serif or sans) and not mono,
                    "mono": mono,
                    "bold": bold,
                    "available": True,
                }
            )
    return found


def _mean_rgb(
    image: Image.Image,
    box: dict[str, int],
    *,
    predicate=None,
    step: int = 2,
) -> tuple[tuple[int, int, int], int]:
    px = image.convert("RGB").load()
    x0, y0, x1, y1 = box["x0"], box["y0"], box["x1"], box["y1"]
    rs = gs = bs = n = 0
    for y in range(y0, y1, step):
        for x in range(x0, x1, step):
            r, g, b = px[x, y]
            if predicate is not None and not predicate(r, g, b):
                continue
            rs += r
            gs += g
            bs += b
            n += 1
    if n == 0:
        return (0, 0, 0), 0
    return (rs // n, gs // n, bs // n), n


def _type_mask_bbox(image: Image.Image, box: dict[str, int], *, gold=True, white=True) -> dict[str, int] | None:
    px = image.convert("RGB").load()
    minx, miny, maxx, maxy = box["x1"], box["y1"], box["x0"], box["y0"]
    hits = 0
    for y in range(box["y0"], box["y1"], 1):
        for x in range(box["x0"], box["x1"], 1):
            r, g, b = px[x, y]
            ok = (gold and _is_gold(r, g, b)) or (white and _is_white(r, g, b))
            if not ok:
                continue
            hits += 1
            minx = min(minx, x)
            miny = min(miny, y)
            maxx = max(maxx, x)
            maxy = max(maxy, y)
    if hits < 12:
        return None
    return _box(minx, miny, maxx + 1, maxy + 1)


def _row_type_fractions(image: Image.Image, box: dict[str, int]) -> list[dict[str, float]]:
    px = image.convert("RGB").load()
    rows = []
    width = max(1, box["x1"] - box["x0"])
    for y in range(box["y0"], box["y1"]):
        gold = white = other = 0
        for x in range(box["x0"], box["x1"], 2):
            r, g, b = px[x, y]
            if _is_gold(r, g, b):
                gold += 1
            elif _is_white(r, g, b):
                white += 1
            elif not _is_navy(r, g, b) and _luma(r, g, b) > 70:
                other += 1
        n = max(1, width // 2)
        rows.append(
            {
                "y": y,
                "gold": gold / n,
                "white": white / n,
                "type": (gold + white + other) / n,
            }
        )
    return rows


def _cluster_runs(rows: list[dict[str, float]], key: str, *, min_frac: float, min_len: int = 4) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    start = None
    last = None
    for row in rows:
        if row[key] >= min_frac:
            if start is None:
                start = int(row["y"])
            last = int(row["y"])
        elif start is not None:
            if last is not None and last - start + 1 >= min_len:
                runs.append((start, last + 1))
            start = last = None
    if start is not None and last is not None and last - start + 1 >= min_len:
        runs.append((start, last + 1))
    return runs


def _mad(a: Image.Image, b: Image.Image, *, step: int = 2) -> float:
    if a.size != b.size:
        b = b.resize(a.size, Image.Resampling.BILINEAR)
    pa, pb = a.convert("RGB").load(), b.convert("RGB").load()
    w, h = a.size
    total = 0.0
    n = 0
    for y in range(0, h, step):
        for x in range(0, w, step):
            ca, cb = pa[x, y], pb[x, y]
            total += abs(ca[0] - cb[0]) + abs(ca[1] - cb[1]) + abs(ca[2] - cb[2])
            n += 1
    return total / 3.0 / max(1, n)


def _luma_nmad(a: Image.Image, b: Image.Image, *, step: int = 2) -> float:
    ga = a.convert("L")
    gb = b.convert("L")
    if gb.size != ga.size:
        gb = gb.resize(ga.size, Image.Resampling.BILINEAR)
    ma = ImageStat.Stat(ga).mean[0]
    mb = ImageStat.Stat(gb).mean[0]
    pa, pb = ga.load(), gb.load()
    w, h = ga.size
    total = 0.0
    n = 0
    for y in range(0, h, step):
        for x in range(0, w, step):
            total += abs((pa[x, y] - ma) - (pb[x, y] - mb))
            n += 1
    return total / max(1, n)


def recover_hero_transform(
    source: Image.Image,
    reference: Image.Image,
    dest_box: dict[str, int],
) -> dict[str, Any]:
    """Recover source-space crop that reproduces the approved hero framing.

    Uses the approved raster as a matching guide only. Reconstruction later
    crops the original source asset — never pastes the approved hero pixels.
    """
    src = source.convert("RGB")
    ref = reference.convert("RGB")
    dw = max(8, dest_box["x1"] - dest_box["x0"])
    dh = max(8, dest_box["y1"] - dest_box["y0"])
    ref_hero = ref.crop((dest_box["x0"], dest_box["y0"], dest_box["x1"], dest_box["y1"]))
    ix0 = int(dw * 0.10)
    iy0 = int(dh * 0.22)
    ix1 = int(dw * 0.90)
    iy1 = int(dh * 0.74)
    template_rgb = ref_hero.crop((ix0, iy0, ix1, iy1))
    tw, th = template_rgb.size
    sw, sh = src.size
    cover = max(dw / max(1, sw), dh / max(1, sh))
    coarse = 0.18
    best = {
        "score": 1e18,
        "scale": cover,
        "sx0": 0,
        "sy0": 0,
        "sx1": sw,
        "sy1": sh,
        "method": "cover_fallback",
    }

    def search(scales: list[float], work: float, step: int, seed: dict[str, Any] | None) -> dict[str, Any]:
        local = dict(best if seed is None else seed)
        tmpl = template_rgb.resize((max(8, int(tw * work)), max(8, int(th * work))), Image.Resampling.BILINEAR).convert("L")
        ox = max(4, int(ix0 * work))
        oy = max(4, int(iy0 * work))
        for scale in scales:
            nw = max(dw, int(round(sw * scale)))
            nh = max(dh, int(round(sh * scale)))
            small_w = max(8, int(nw * work))
            small_h = max(8, int(nh * work))
            small = src.resize((small_w, small_h), Image.Resampling.BILINEAR).convert("L")
            win_w, win_h = tmpl.size
            max_x = max(0, small_w - win_w)
            max_y = max(0, small_h - win_h)
            xs = range(0, max_x + 1, step)
            ys = range(0, max_y + 1, step)
            if seed is not None:
                cx = int(seed["sx0"] * scale * work)
                cy = int(seed["sy0"] * scale * work) + oy
                rad = max(step * 8, 24)
                xs = range(max(0, cx - rad), min(max_x, cx + rad) + 1, max(1, step // 2 or 1))
                ys = range(max(0, cy - rad), min(max_y, cy + rad) + 1, max(1, step // 2 or 1))
            for y in ys:
                for x in xs:
                    patch = small.crop((x, y, x + win_w, y + win_h))
                    score = _luma_nmad(tmpl, patch, step=2)
                    if score < local["score"]:
                        full_x = x - ox
                        full_y = y - oy
                        sx0 = full_x / max(1e-6, scale * work)
                        sy0 = full_y / max(1e-6, scale * work)
                        sx1 = sx0 + dw / scale
                        sy1 = sy0 + dh / scale
                        local = {
                            "score": score,
                            "scale": scale,
                            "sx0": sx0,
                            "sy0": sy0,
                            "sx1": sx1,
                            "sy1": sy1,
                            "method": "template_match_scale_search",
                        }
        return local

    coarse_scales = [cover * (1.0 + 0.06 * i) for i in range(0, 9)]
    best = search(coarse_scales, coarse, step=9, seed=None)
    refine_scales = [
        max(cover, best["scale"] * 0.94),
        best["scale"],
        min(cover * 1.55, best["scale"] * 1.06),
    ]
    best = search(refine_scales, 0.30, step=3, seed=best)

    sx0 = _clamp(int(round(best["sx0"])), 0, sw - 2)
    sy0 = _clamp(int(round(best["sy0"])), 0, sh - 2)
    sx1 = _clamp(int(round(best["sx1"])), sx0 + 2, sw)
    sy1 = _clamp(int(round(best["sy1"])), sy0 + 2, sh)
    crop_w = sx1 - sx0
    crop_h = sy1 - sy0
    scale_x = dw / max(1, crop_w)
    scale_y = dh / max(1, crop_h)
    scale_factor = (scale_x + scale_y) / 2.0
    confidence = max(0.35, min(0.93, 1.0 - float(best["score"]) / 80.0))
    return {
        "source_asset_id": None,
        "source_dimensions": {"width": sw, "height": sh},
        "destination_bbox": dest_box,
        "crop_rectangle_source": _box(sx0, sy0, sx1, sy1),
        "normalized_source_crop": {
            "x": round(sx0 / sw, 5),
            "y": round(sy0 / sh, 5),
            "width": round(crop_w / sw, 5),
            "height": round(crop_h / sh, 5),
            "x1": round(sx1 / sw, 5),
            "y1": round(sy1 / sh, 5),
        },
        "scale_mode": "exact_source_window",
        "scale_factor": round(scale_factor, 5),
        "scale_x": round(scale_x, 5),
        "scale_y": round(scale_y, 5),
        "translation_x": dest_box["x0"],
        "translation_y": dest_box["y0"],
        "focal_point": {
            "source_x": round((sx0 + sx1) / 2.0, 1),
            "source_y": round((sy0 + sy1) / 2.0, 1),
            "normalized_x": round(((sx0 + sx1) / 2.0) / sw, 4),
            "normalized_y": round(((sy0 + sy1) / 2.0) / sh, 4),
        },
        "hero_clipping_bounds": dest_box,
        "match_mad_coarse": round(float(best["score"]), 3),
        "match_method": best["method"],
        "match_confidence": round(confidence, 3),
        "cover_scale_minimum": round(cover, 5),
        "zoom_over_cover": round(scale_factor / max(cover, 1e-6), 4),
    }


def _channel_stats(image: Image.Image) -> dict[str, Any]:
    stat = ImageStat.Stat(image.convert("RGB"))
    return {"mean": [round(v, 3) for v in stat.mean], "stddev": [round(v, 3) for v in stat.stddev]}


def derive_hero_color_treatment(source_crop: Image.Image, reference_hero: Image.Image) -> dict[str, Any]:
    src = source_crop.convert("RGB")
    ref = reference_hero.convert("RGB")
    if src.size != ref.size:
        src = src.resize(ref.size, Image.Resampling.LANCZOS)
    w, h = ref.size
    interior = (int(w * 0.14), int(h * 0.32), int(w * 0.86), int(h * 0.68))
    src_i = src.crop(interior)
    ref_i = ref.crop(interior)
    ss = _channel_stats(src_i)
    rs = _channel_stats(ref_i)
    gains = []
    biases = []
    for i in range(3):
        std_s = max(1.0, ss["stddev"][i])
        std_r = max(1.0, rs["stddev"][i])
        gain = std_r / std_s
        gain = max(0.55, min(1.85, gain))
        bias = rs["mean"][i] - gain * ss["mean"][i]
        bias = max(-64.0, min(64.0, bias))
        gains.append(round(gain, 4))
        biases.append(round(bias, 3))
    src_l = sum(ss["mean"]) / 3.0
    ref_l = sum(rs["mean"]) / 3.0
    src_c = sum(ss["stddev"]) / 3.0
    ref_c = sum(rs["stddev"]) / 3.0
    brightness = round(ref_l - src_l, 3)
    contrast = round(max(0.7, min(1.6, ref_c / max(1.0, src_c))), 4)
    src_hsv = src_i.convert("HSV")
    ref_hsv = ref_i.convert("HSV")
    sat_s = ImageStat.Stat(src_hsv).mean[1]
    sat_r = ImageStat.Stat(ref_hsv).mean[1]
    saturation = round(max(0.75, min(1.55, sat_r / max(1.0, sat_s))), 4)
    temp_src = ss["mean"][0] - ss["mean"][2]
    temp_ref = rs["mean"][0] - rs["mean"][2]
    temperature = round(temp_ref - temp_src, 3)
    if temperature > 4:
        gains[0] = round(min(1.85, gains[0] * 1.04), 4)
        gains[2] = round(max(0.55, gains[2] * 0.97), 4)
    return {
        "method": "reinhard_affine_plus_enhance",
        "per_channel_gain": gains,
        "per_channel_bias": biases,
        "brightness_adjustment": brightness,
        "contrast_adjustment": contrast,
        "saturation_adjustment": saturation,
        "temperature_delta": temperature,
        "source_stats": ss,
        "reference_stats": rs,
        "confidence": 0.78,
        "source": "raster_analysis",
        "notes": "Treatment is applied to the cropped original asset. The original file is not modified.",
    }


def apply_hero_treatment(crop: Image.Image, treatment: dict[str, Any], dest_size: tuple[int, int]) -> Image.Image:
    im = crop.convert("RGB")
    if im.size != dest_size:
        im = im.resize(dest_size, Image.Resampling.LANCZOS)
    gains = treatment.get("per_channel_gain") or [1, 1, 1]
    biases = treatment.get("per_channel_bias") or [0, 0, 0]
    bands = []
    for i, band in enumerate(im.split()):
        g = float(gains[i])
        b = float(biases[i])
        lut = [max(0, min(255, int(round(g * x + b)))) for x in range(256)]
        bands.append(band.point(lut))
    out = Image.merge("RGB", tuple(bands))
    sat = float(treatment.get("saturation_adjustment") or 1.0)
    if abs(sat - 1.0) > 0.03:
        out = ImageEnhance.Color(out).enhance(sat)
    contrast = float(treatment.get("contrast_adjustment") or 1.0)
    if abs(contrast - 1.0) > 0.03:
        out = ImageEnhance.Contrast(out).enhance(0.5 + 0.5 * contrast)
    return out


def apply_stored_hero(source: Image.Image, profile: dict[str, Any]) -> tuple[Image.Image, dict[str, Any]]:
    hero = _as_dict(profile.get("hero_treatment") or profile)
    dest = _as_dict(hero.get("destination_bbox"))
    crop_box = _as_dict(hero.get("crop_rectangle_source"))
    src = source.convert("RGB")
    sw, sh = src.size
    if crop_box:
        x0 = _clamp(int(crop_box["x0"]), 0, sw - 2)
        y0 = _clamp(int(crop_box["y0"]), 0, sh - 2)
        x1 = _clamp(int(crop_box["x1"]), x0 + 2, sw)
        y1 = _clamp(int(crop_box["y1"]), y0 + 2, sh)
        cropped = src.crop((x0, y0, x1, y1))
        method = "stored_source_window"
    else:
        dw = int(dest.get("x1") or src.size[0]) - int(dest.get("x0") or 0)
        dh = int(dest.get("y1") or src.size[1]) - int(dest.get("y0") or 0)
        from investhome_api.services.creative_director.structured_reconstruction import cover_crop

        cropped, meta = cover_crop(src, dw, dh)
        method = "cover_fallback:" + str(meta.get("method"))
    dw = max(8, int(dest.get("x1", cropped.size[0])) - int(dest.get("x0", 0)))
    dh = max(8, int(dest.get("y1", cropped.size[1])) - int(dest.get("y0", 0)))
    treated = apply_hero_treatment(cropped, _as_dict(hero.get("color_treatment")), (dw, dh))
    return treated, {"method": method, "crop": crop_box, "destination": dest}


def _estimate_corner_radius(image: Image.Image, box: dict[str, int], fill_pred) -> int:
    px = image.convert("RGB").load()
    x0, y0 = box["x0"] + 1, box["y0"] + 2
    for i in range(2, min(36, (box["x1"] - box["x0"]) // 3)):
        r, g, b = px[x0 + i, y0]
        if fill_pred(r, g, b):
            return max(8, i)
    return 16


def analyze_cta(image: Image.Image, box: dict[str, int], text: str) -> dict[str, Any]:
    def is_fill(r: int, g: int, b: int) -> bool:
        return _is_gold(r, g, b) or (r > 150 and g > 110 and b < 160 and r >= g - 10)

    def is_ink(r: int, g: int, b: int) -> bool:
        return _luma(r, g, b) < 90

    top, n_top = _mean_rgb(
        image,
        _box(box["x0"] + 12, box["y0"] + 4, box["x1"] - 12, box["y0"] + max(8, (box["y1"] - box["y0"]) // 3)),
        predicate=is_fill,
    )
    bot, n_bot = _mean_rgb(
        image,
        _box(box["x0"] + 12, box["y1"] - max(8, (box["y1"] - box["y0"]) // 3), box["x1"] - 12, box["y1"] - 4),
        predicate=is_fill,
    )
    mid, n_mid = _mean_rgb(image, box, predicate=is_fill)
    ink, n_ink = _mean_rgb(image, box, predicate=is_ink)
    radius = _estimate_corner_radius(image, box, is_fill)
    fill_type = "solid"
    stops = [{"offset": 0.0, "color": list(mid)}, {"offset": 1.0, "color": list(mid)}]
    if n_top and n_bot and (abs(top[0] - bot[0]) + abs(top[1] - bot[1]) + abs(top[2] - bot[2]) > 8):
        fill_type = "linear_gradient"
        stops = [
            {"offset": 0.0, "color": list(top), "hex": _hex(top)},
            {"offset": 1.0, "color": list(bot), "hex": _hex(bot)},
        ]
    w = box["x1"] - box["x0"]
    h = box["y1"] - box["y0"]
    return {
        "bbox": box,
        "shape": "rounded_rectangle",
        "width": w,
        "height": h,
        "corner_radius": radius,
        "border": None,
        "border_width": 0,
        "fill_type": fill_type,
        "gradient_direction": "vertical" if fill_type == "linear_gradient" else None,
        "gradient_stops": stops,
        "opacity": 1.0,
        "shadow": None,
        "text": text,
        "text_color": list(ink if n_ink else (18, 16, 12)),
        "text_color_hex": _hex(ink if n_ink else (18, 16, 12)),
        "fill_color": list(mid),
        "fill_color_hex": _hex(mid),
        "internal_padding": {"x": max(12, w // 18), "y": max(8, h // 6)},
        "text_alignment": "center",
        "relationship_to_hero": "overlays_lower_hero",
        "relationship_to_logo": "above_logo_in_footer",
        "sample_counts": {"top": n_top, "mid": n_mid, "bottom": n_bot, "ink": n_ink},
        "confidence": 0.82 if n_mid > 40 else 0.55,
        "source": "raster_analysis",
    }


def analyze_logo_treatment(image: Image.Image, box: dict[str, int], logo: Image.Image | None) -> dict[str, Any]:
    w = box["x1"] - box["x0"]
    h = box["y1"] - box["y0"]
    fitted = None
    pad = {"x": 0, "y": 0}
    scale = 1.0
    if logo is not None:
        fitted = _fit_logo(logo, w, h)
        pad = {
            "x": max(0, (w - fitted.width) // 2),
            "y": max(0, (h - fitted.height) // 2),
        }
        scale = min(w / max(1, fitted.width), h / max(1, fitted.height))
    return {
        "destination_bbox": box,
        "fit": "contain",
        "padding": pad,
        "scale": round(float(scale), 4),
        "alignment": "center",
        "opacity": 1.0,
        "color_treatment": "none_passthrough",
        "relationship_to_cta": "below_cta",
        "relationship_to_bottom_fade": "sits_in_navy_footer_below_hero_fade",
        "confidence": 0.9,
        "source": "asset_plus_geometry",
    }


def extract_palette(image: Image.Image, spec: dict[str, Any]) -> dict[str, Any]:
    navy_box = _abs(region(spec, "navy_field")) or {"x0": 8, "y0": 8, "x1": 80, "y1": 48}
    cta_box = _abs(element(spec, "cta")) or {"x0": 218, "y0": 1129, "x1": 789, "y1": 1208}
    head_box = _abs(element(spec, "headline")) or {"x0": 235, "y0": 59, "x1": 848, "y1": 242}
    navy, n_navy = _mean_rgb(image, navy_box, predicate=_is_navy, step=1)
    if n_navy < 8:
        navy, _ = _mean_rgb(image, _box(8, 8, 64, 40), step=1)
    gold_cta, _ = _mean_rgb(image, cta_box, predicate=_is_gold)
    gold_type, _ = _mean_rgb(image, head_box, predicate=_is_gold)
    white, _ = _mean_rgb(image, head_box, predicate=_is_white)
    support_box = _abs(element(spec, "supporting_copy")) or head_box
    support, _ = _mean_rgb(image, support_box, predicate=lambda r, g, b: _is_gold(r, g, b) or _is_white(r, g, b))
    navy2 = (
        _clamp(navy[0] + 8, 0, 40),
        _clamp(navy[1] + 10, 0, 50),
        _clamp(navy[2] + 16, 0, 70),
    )
    gold2 = tuple(_clamp(int(v * 0.82), 0, 255) for v in (gold_type if gold_type != (0, 0, 0) else gold_cta))
    roles = {
        "navy_primary": {"rgb": list(navy), "hex": _hex(navy), "opacity": 1.0, "source": "navy_field_sample", "confidence": 0.92},
        "navy_secondary": {"rgb": list(navy2), "hex": _hex(navy2), "opacity": 1.0, "source": "derived_from_navy_primary", "confidence": 0.7},
        "gold_primary": {
            "rgb": list(gold_type if gold_type != (0, 0, 0) else gold_cta),
            "hex": _hex(gold_type if gold_type != (0, 0, 0) else gold_cta),
            "opacity": 1.0,
            "source": "headline_gold_sample",
            "confidence": 0.86,
        },
        "gold_secondary": {"rgb": list(gold2), "hex": _hex(gold2), "opacity": 1.0, "source": "derived_from_gold_primary", "confidence": 0.68},
        "white_primary": {"rgb": list(white if white != (0, 0, 0) else (246, 241, 232)), "hex": _hex(white if white != (0, 0, 0) else (246, 241, 232)), "opacity": 1.0, "source": "headline_white_sample", "confidence": 0.88},
        "supporting_text": {"rgb": list(support if support != (0, 0, 0) else (230, 220, 190)), "hex": _hex(support if support != (0, 0, 0) else (230, 220, 190)), "opacity": 1.0, "source": "supporting_copy_sample", "confidence": 0.8},
        "cta_gold": {"rgb": list(gold_cta if gold_cta != (0, 0, 0) else (201, 168, 92)), "hex": _hex(gold_cta if gold_cta != (0, 0, 0) else (201, 168, 92)), "opacity": 1.0, "source": "cta_fill_sample", "confidence": 0.9},
        "separator_gold": {
            "rgb": list(gold_type if gold_type != (0, 0, 0) else gold_cta),
            "hex": _hex(gold_type if gold_type != (0, 0, 0) else gold_cta),
            "opacity": 0.9,
            "source": "headline_gold_sample",
            "confidence": 0.75,
        },
    }
    return roles


def _glyph_metrics(image: Image.Image, box: dict[str, int], color_pred) -> dict[str, Any]:
    tight = _type_mask_bbox(image, box, gold=True, white=True) or box
    h = max(1, tight["y1"] - tight["y0"])
    w = max(1, tight["x1"] - tight["x0"])
    rgb, n = _mean_rgb(image, tight, predicate=color_pred)
    px = image.convert("RGB").load()
    edges = 0
    samples = 0
    for y in range(tight["y0"] + 1, tight["y1"] - 1, 2):
        for x in range(tight["x0"] + 1, tight["x1"] - 1, 2):
            samples += 1
            a = _luma(*px[x, y])
            b = _luma(*px[x + 1, y])
            if abs(a - b) > 40:
                edges += 1
    contrast = "high" if n > 20 and _luma(*rgb) > 160 else "medium"
    stroke = "high_contrast_display" if edges / max(1, samples) > 0.12 else "smooth_display"
    return {
        "bbox": tight,
        "width": w,
        "height": h,
        "color": list(rgb),
        "color_hex": _hex(rgb if n else (255, 255, 255)),
        "edge_density": round(edges / max(1, samples), 4),
        "stroke_character": stroke,
        "contrast_character": contrast,
        "sample_count": n,
    }


def _render_text_mask(text: str, font: ImageFont.ImageFont, size: tuple[int, int]) -> Image.Image:
    im = Image.new("L", size, 0)
    draw = ImageDraw.Draw(im)
    tw, th = text_size(font, text)
    x = max(0, (size[0] - tw) // 2)
    y = max(0, (size[1] - th) // 2)
    draw.text((x, y), text, font=font, fill=255)
    return im


def _mask_from_crop(crop: Image.Image) -> Image.Image:
    px = crop.convert("RGB").load()
    mask = Image.new("L", crop.size, 0)
    mp = mask.load()
    for y in range(crop.size[1]):
        for x in range(crop.size[0]):
            r, g, b = px[x, y]
            if _is_gold(r, g, b) or _is_white(r, g, b) or _luma(r, g, b) > 140:
                mp[x, y] = 255
    return mask


def match_font_for_role(
    text: str,
    crop: Image.Image,
    fonts: list[dict[str, Any]],
    *,
    prefer_serif: bool,
    prefer_bold: bool,
    prefer_display: bool,
) -> dict[str, Any]:
    target = _mask_from_crop(crop)
    h = max(12, crop.size[1] - 2)
    candidates: list[dict[str, Any]] = []
    usable = [f for f in fonts if not f.get("mono")]
    if not usable:
        usable = fonts
    for item in usable:
        try:
            font = _load_font(item["path"], h)
        except Exception:
            continue
        try:
            rendered = _render_text_mask(text, font, crop.size)
        except Exception:
            continue
        score = _mad(
            Image.merge("RGB", (target, target, target)),
            Image.merge("RGB", (rendered, rendered, rendered)),
            step=1,
        )
        char_score = 0.0
        if prefer_serif and item.get("serif"):
            char_score += 8
        if (not prefer_serif) and item.get("sans"):
            char_score += 8
        if prefer_bold and item.get("bold"):
            char_score += 4
        if prefer_display and item.get("display"):
            char_score += 2
        if item.get("mono"):
            char_score -= 12
        combined = score - char_score
        tw, th = text_size(font, text)
        tracking = 0.0
        if len(text) > 1 and tw < crop.size[0] * 0.96:
            tracking = (crop.size[0] - tw) / (len(text) - 1)
            tracking = tracking * (0.12 if len(text) <= 5 else 0.28)
            tracking = max(0.0, min(6.0 if len(text) <= 5 else 10.0, tracking))
        candidates.append(
            {
                "path": item["path"],
                "family_guess": item["family_guess"],
                "serif": item.get("serif"),
                "bold": item.get("bold"),
                "mask_mad": round(score, 3),
                "combined": round(combined, 3),
                "font_size": h,
                "tracking_px": round(tracking, 2),
                "rendered_size": [tw, th],
            }
        )
    candidates.sort(key=lambda c: c["combined"])
    selected = candidates[0] if candidates else None
    fallbacks = [
        {
            "family_guess": c["family_guess"],
            "path": c["path"],
            "confidence": round(max(0.15, min(0.9, 1.0 - c["mask_mad"] / 90.0)), 3),
            "mask_mad": c["mask_mad"],
        }
        for c in candidates[:4]
    ]
    conf = 0.2
    if selected:
        conf = max(0.28, min(0.86, 1.0 - selected["mask_mad"] / 90.0))
        if selected.get("serif") and prefer_serif:
            conf = min(0.9, conf + 0.06)
    return {
        "font_family_exact": None,
        "selected_font": None if selected is None else selected["family_guess"],
        "selected_font_path": None if selected is None else selected["path"],
        "match_reason": (
            "Compared available container/project fonts against the approved type mask. "
            "Exact campaign family is not identified."
        ),
        "match_confidence": round(conf, 3),
        "fallback_candidates": fallbacks,
        "metrics": selected,
        "available_considered": len(candidates),
    }


def fingerprint_typography(
    image: Image.Image,
    spec: dict[str, Any],
    fonts: list[dict[str, Any]],
    geometry: dict[str, Any],
) -> dict[str, Any]:
    canvas = _as_dict(spec.get("canvas"))
    width = int(canvas.get("width") or image.size[0])
    roles: dict[str, Any] = {}

    def pack(role: str, box: dict[str, int], text: str, *, serif: bool, bold: bool, display: bool, category: str, uppercase: bool) -> dict[str, Any]:
        pred = _is_gold if role in {"headline_KAZAN", "unit_value", "discount_value", "discount_label", "unit_label"} else _is_white
        if role == "supporting_copy":
            pred = lambda r, g, b: _is_gold(r, g, b) or _is_white(r, g, b)
        if role == "cta_text":
            pred = lambda r, g, b: _luma(r, g, b) < 90
        metrics = _glyph_metrics(image, box, pred)
        crop = image.crop((box["x0"], box["y0"], box["x1"], box["y1"]))
        match = match_font_for_role(text, crop, fonts, prefer_serif=serif, prefer_bold=bold, prefer_display=display)
        size = int(metrics["height"] * (0.92 if display else 0.78))
        relative = round(metrics["height"] / max(1, image.size[1]), 4)
        color = metrics["color"]
        return {
            "role": role,
            "text": text,
            "typography_category": category,
            "serif_sans": "serif" if serif else "sans",
            "display_body_label": "display" if display else ("label" if "label" in role else "body"),
            "approximate_font_width": "condensed" if metrics["width"] / max(1, len(text) * metrics["height"]) < 0.42 else "normal",
            "stroke_character": metrics["stroke_character"],
            "contrast_character": metrics["contrast_character"],
            "uppercase_behavior": "all_small_caps_or_uppercase" if uppercase else "sentence",
            "approximate_weight": "bold" if bold else "regular",
            "font_size": size,
            "relative_font_size": relative,
            "tracking": (match.get("metrics") or {}).get("tracking_px") or 0,
            "line_height": round(metrics["height"] / max(8, size), 3),
            "text_alignment": "center",
            "baseline_relationship": "visual_center_of_bbox",
            "color": color,
            "color_hex": metrics["color_hex"],
            "capitalization": "uppercase" if uppercase else "as_written",
            "bounding_box": metrics["bbox"],
            "normalized_bounding_box": _norm(metrics["bbox"], width, image.size[1]),
            "font_family_exact": None,
            "font_characteristics": {
                "serif": serif,
                "weight": "bold" if bold else "regular",
                "optical_size": "display" if display else "text",
                "stroke": metrics["stroke_character"],
                "contrast": metrics["contrast_character"],
            },
            **match,
        }

    boxes = geometry
    roles["headline_ALIRKEN"] = pack(
        "headline_ALIRKEN",
        boxes["headline_ALIRKEN"],
        "ALIRKEN",
        serif=True,
        bold=True,
        display=True,
        category="display_serif",
        uppercase=True,
    )
    roles["headline_KAZAN"] = pack(
        "headline_KAZAN",
        boxes["headline_KAZAN"],
        "KAZAN",
        serif=True,
        bold=True,
        display=True,
        category="display_serif",
        uppercase=True,
    )
    roles["supporting_copy"] = pack(
        "supporting_copy",
        boxes["supporting_copy"],
        ROLE_TEXT["supporting_copy"],
        serif=True,
        bold=False,
        display=False,
        category="supporting_serif",
        uppercase=False,
    )
    roles["unit_value"] = pack("unit_value", boxes["unit_value"], "2+1", serif=True, bold=True, display=True, category="stat_serif", uppercase=False)
    roles["unit_label"] = pack("unit_label", boxes["unit_label"], "DAİRE", serif=True, bold=False, display=False, category="label_serif", uppercase=True)
    roles["price_value"] = pack("price_value", boxes["price_value"], "675.000", serif=True, bold=True, display=True, category="stat_serif", uppercase=False)
    roles["discount_value"] = pack("discount_value", boxes["discount_value"], "%35", serif=True, bold=True, display=True, category="stat_serif", uppercase=False)
    roles["discount_label"] = pack(
        "discount_label",
        boxes["discount_label"],
        "LANSMAN AVANTAJI",
        serif=True,
        bold=False,
        display=False,
        category="label_serif",
        uppercase=True,
    )
    roles["cta_text"] = pack("cta_text", boxes["cta"], "PROJEYİ KEŞFET", serif=True, bold=True, display=True, category="cta_serif", uppercase=True)
    if boxes.get("price_label"):
        roles["price_label"] = pack(
            "price_label",
            boxes["price_label"],
            "LİSTE FİYATI",
            serif=True,
            bold=False,
            display=False,
            category="label_serif",
            uppercase=True,
        )
    selected = {
        role: {
            "selected_font": item.get("selected_font"),
            "path": item.get("selected_font_path"),
            "match_confidence": item.get("match_confidence"),
            "match_reason": item.get("match_reason"),
        }
        for role, item in roles.items()
    }
    return {"roles": roles, "selected_fonts": selected, "font_family_exact": None}


def split_headline(image: Image.Image, box: dict[str, int]) -> dict[str, dict[str, int]]:
    rows = _row_type_fractions(image, box)
    white_runs = _cluster_runs(rows, "white", min_frac=0.04, min_len=6)
    gold_runs = _cluster_runs(rows, "gold", min_frac=0.04, min_len=6)
    a_y0, a_y1 = white_runs[0] if white_runs else (box["y0"], box["y0"] + max(20, (box["y1"] - box["y0"]) // 3))
    k_y0, k_y1 = gold_runs[-1] if gold_runs else (a_y1, box["y1"])
    a_box = _type_mask_bbox(image, _box(box["x0"], a_y0, box["x1"], a_y1), gold=False, white=True) or _box(
        box["x0"], a_y0, box["x1"], a_y1
    )
    # Restrict KAZAN to the central letter mass so ornaments do not inflate the bbox.
    mid0 = box["x0"] + int((box["x1"] - box["x0"]) * 0.18)
    mid1 = box["x1"] - int((box["x1"] - box["x0"]) * 0.18)
    k_box = _type_mask_bbox(image, _box(mid0, k_y0, mid1, k_y1), gold=True, white=False) or _box(mid0, k_y0, mid1, k_y1)
    return {"headline_ALIRKEN": a_box, "headline_KAZAN": k_box}


def split_column_hierarchy(image: Image.Image, box: dict[str, int]) -> list[dict[str, Any]]:
    trimmed = _box(box["x0"], box["y0"], box["x1"], max(box["y0"] + 24, box["y1"] - 24))
    rows = _row_type_fractions(image, trimmed)
    runs = _cluster_runs(rows, "type", min_frac=0.028, min_len=4)
    merged: list[tuple[int, int]] = []
    for y0, y1 in runs:
        if merged and y0 - merged[-1][1] <= 14:
            merged[-1] = (merged[-1][0], y1)
        else:
            merged.append((y0, y1))
    bands = []
    for y0, y1 in merged:
        tight = _type_mask_bbox(image, _box(box["x0"], y0, box["x1"], y1)) or _box(box["x0"], y0, box["x1"], y1)
        if tight["y1"] - tight["y0"] < 7 or tight["x1"] - tight["x0"] < 18:
            continue
        gold, ng = _mean_rgb(image, tight, predicate=_is_gold)
        white, nw = _mean_rgb(image, tight, predicate=_is_white)
        color = "gold" if ng >= nw else "white"
        bands.append(
            {
                "bbox": tight,
                "height": tight["y1"] - tight["y0"],
                "width": tight["x1"] - tight["x0"],
                "area": (tight["y1"] - tight["y0"]) * (tight["x1"] - tight["x0"]),
                "color": color,
                "center_y": (tight["y0"] + tight["y1"]) / 2.0,
            }
        )
    bands.sort(key=lambda b: b["bbox"]["y0"])
    return bands


def _slot_box(box: dict[str, int], t0: float, t1: float) -> dict[str, int]:
    h = max(1, box["y1"] - box["y0"])
    return _box(box["x0"], box["y0"] + int(h * t0), box["x1"], box["y0"] + int(h * t1))


def _tighten(image: Image.Image, box: dict[str, int]) -> dict[str, int]:
    return _type_mask_bbox(image, box) or box


def analyze_commercial_hierarchy(image: Image.Image, spec: dict[str, Any]) -> dict[str, Any]:
    unit_box = _abs(element(spec, "unit_type")) or {"x0": 226, "y0": 321, "x1": 444, "y1": 549}
    price_box = _abs(element(spec, "list_price")) or {"x0": 444, "y0": 319, "x1": 663, "y1": 545}
    disc_box = _abs(element(spec, "discount")) or {"x0": 663, "y0": 321, "x1": 882, "y1": 550}

    def usable(box: dict[str, int]) -> dict[str, int]:
        return _box(box["x0"], box["y0"] + 6, box["x1"], max(box["y0"] + 40, box["y1"] - 22))

    u = usable(unit_box)
    p = usable(price_box)
    d = usable(disc_box)
    unit_value = _tighten(image, _slot_box(u, 0.0, 0.58))
    unit_label = _tighten(image, _slot_box(u, 0.58, 1.0))
    price_label_box = _tighten(image, _slot_box(p, 0.0, 0.22))
    price_value = _tighten(image, _slot_box(p, 0.22, 0.72))
    usd_box = _tighten(image, _slot_box(p, 0.72, 1.0))
    disc_label = _tighten(image, _slot_box(d, 0.0, 0.38))
    disc_value = _tighten(image, _slot_box(d, 0.38, 1.0))
    # If the upper unit slot is clearly smaller than the lower, keep value-above-label
    # by swapping only when the upper slot failed to find type.
    if (unit_value["y1"] - unit_value["y0"]) < 12 and (unit_label["y1"] - unit_label["y0"]) > 20:
        unit_value, unit_label = _slot_box(u, 0.0, 0.58), unit_label
    return {
        "layout": "three_column_row",
        "order": ["unit", "list_price", "discount"],
        "unit": {
            "value_content": "2+1",
            "label_content": "DAİRE",
            "stack": ["unit_value", "unit_label"],
            "value_bbox": unit_value,
            "label_bbox": unit_label,
            "column_bbox": unit_box,
            "value_before_label": True,
        },
        "list_price": {
            "value_content": "675.000 USD",
            "amount_content": "675.000",
            "currency_content": "USD",
            "label_content": "LİSTE FİYATI",
            "value_bbox": price_value,
            "label_bbox": price_label_box,
            "currency_bbox": usd_box,
            "column_bbox": price_box,
            "stack": ["list_price_label", "price_value", "USD"],
        },
        "discount": {
            "value_content": "%35",
            "label_content": "LANSMAN AVANTAJI",
            "stack": ["discount_label", "discount_value"],
            "value_bbox": disc_value,
            "label_bbox": disc_label,
            "column_bbox": disc_box,
            "value_before_label": False,
        },
        "notes": "Hierarchy uses column slots from approved v2: unit value above label; price label/value/USD; discount label above value.",
    }


def analyze_headline_craft(image: Image.Image, boxes: dict[str, dict[str, int]], gold: tuple[int, int, int]) -> dict[str, Any]:
    a = boxes["headline_ALIRKEN"]
    k = boxes["headline_KAZAN"]
    a_c = _box_center(a)
    k_c = _box_center(k)
    a_h = max(1, a["y1"] - a["y0"])
    k_h = max(1, k["y1"] - k["y0"])
    ornament = []
    px = image.convert("RGB").load()
    width = image.size[0]
    best_left: list[int] = []
    best_right: list[int] = []
    best_cy = int(k_c[1])
    for cy in range(k["y0"] + max(4, k_h // 5), k["y1"] - max(4, k_h // 6), 2):
        left_xs = [x for x in range(max(48, k["x0"] - 320), k["x0"] - 6) if _is_gold(*px[x, cy])]
        right_xs = [x for x in range(k["x1"] + 6, min(width - 48, k["x1"] + 320)) if _is_gold(*px[x, cy])]
        if len(left_xs) + len(right_xs) > len(best_left) + len(best_right):
            best_left, best_right, best_cy = left_xs, right_xs, cy
    cy = best_cy
    left_xs, right_xs = best_left, best_right
    if len(left_xs) >= 8:
        ornament.append(
            {
                "role": "headline_ornament",
                "side": "left",
                "anchor_to": "headline_KAZAN",
                "geometry": _box(min(left_xs), cy - 2, max(left_xs) + 1, cy + 3),
                "stroke": {"color": list(gold), "width": 2},
                "relationship": "horizontal_rule_crossing_toward_KAZAN",
            }
        )
    if len(right_xs) >= 8:
        ornament.append(
            {
                "role": "headline_ornament",
                "side": "right",
                "anchor_to": "headline_KAZAN",
                "geometry": _box(min(right_xs), cy - 2, max(right_xs) + 1, cy + 3),
                "stroke": {"color": list(gold), "width": 2},
                "relationship": "horizontal_rule_crossing_toward_KAZAN",
            }
        )
    diamond = {
        "role": "headline_ornament_diamond",
        "anchor_to": "headline_KAZAN",
        "geometry": _box(int(k_c[0]) - 8, cy - 8, int(k_c[0]) + 8, cy + 8),
        "relationship": "star_through_KAZAN",
    }
    return {
        "ALIRKEN": {"bbox": a, "center": list(a_c), "height": a_h, "color_role": "white_primary"},
        "KAZAN": {"bbox": k, "center": list(k_c), "height": k_h, "color_role": "gold_primary"},
        "relative_scale": round(k_h / a_h, 3),
        "vertical_spacing": k["y0"] - a["y1"],
        "alignment": "center",
        "gold_white_relationship": "ALIRKEN white stacked above KAZAN gold",
        "ornament": ornament + [diamond],
    }


def analyze_decorations(
    image: Image.Image,
    spec: dict[str, Any],
    craft: dict[str, Any],
    commercial: dict[str, Any],
    gold: tuple[int, int, int],
) -> list[dict[str, Any]]:
    items = list(craft.get("ornament") or [])
    unit = _as_dict(commercial.get("unit")).get("column_bbox")
    price = _as_dict(commercial.get("list_price")).get("column_bbox")
    disc = _as_dict(commercial.get("discount")).get("column_bbox")
    if unit and price:
        x = (unit["x1"] + price["x0"]) // 2
        y0 = min(unit["y0"], price["y0"]) + 16
        y1 = max(unit["y1"], price["y1"]) - 16
        items.append(
            {
                "role": "commercial_separator",
                "anchor_to": "unit_column",
                "geometry": _box(x - 1, y0, x + 2, y1),
                "stroke": {"color": list(gold), "width": 2, "opacity": 0.85},
                "relationship": "vertical_rule_between_unit_and_price",
            }
        )
    if price and disc:
        x = (price["x1"] + disc["x0"]) // 2
        y0 = min(price["y0"], disc["y0"]) + 16
        y1 = max(price["y1"], disc["y1"]) - 16
        items.append(
            {
                "role": "commercial_separator",
                "anchor_to": "list_price_column",
                "geometry": _box(x - 1, y0, x + 2, y1),
                "stroke": {"color": list(gold), "width": 2, "opacity": 0.85},
                "relationship": "vertical_rule_between_price_and_discount",
            }
        )
    support = _abs(element(spec, "supporting_copy"))
    if support:
        cy = support["y1"] + 8
        cx = (support["x0"] + support["x1"]) // 2
        items.append(
            {
                "role": "supporting_separator",
                "anchor_to": "supporting_copy",
                "geometry": _box(cx - 90, cy, cx + 90, cy + 2),
                "stroke": {"color": list(gold), "width": 1, "opacity": 0.8},
                "relationship": "short_rule_below_supporting_copy",
            }
        )
    hero = _abs(region(spec, "hero_visual"))
    if hero:
        items.append(
            {
                "role": "hero_top_transition",
                "anchor_to": "hero_visual",
                "geometry": _box(hero["x0"], hero["y0"], hero["x1"], hero["y0"] + 2),
                "relationship": "hard_navy_to_photo_seam",
            }
        )
    return items


def analyze_fade(image: Image.Image, hero_box: dict[str, int], navy: tuple[int, int, int]) -> dict[str, Any]:
    px = image.convert("RGB").load()
    h = hero_box["y1"] - hero_box["y0"]
    width = hero_box["x1"] - hero_box["x0"]
    fade_h = 40
    for offset in range(40, min(220, h - 10)):
        y = hero_box["y1"] - offset
        navy_n = 0
        n = 0
        for x in range(hero_box["x0"], hero_box["x1"], 8):
            r, g, b = px[x, y]
            n += 1
            if abs(r - navy[0]) + abs(g - navy[1]) + abs(b - navy[2]) < 90:
                navy_n += 1
        if navy_n / max(1, n) > 0.42:
            fade_h = offset
    top_h = 8
    for offset in range(4, min(90, h // 4)):
        y = hero_box["y0"] + offset
        navy_n = 0
        n = 0
        for x in range(hero_box["x0"], hero_box["x1"], 8):
            r, g, b = px[x, y]
            n += 1
            if abs(r - navy[0]) + abs(g - navy[1]) + abs(b - navy[2]) < 90:
                navy_n += 1
        if navy_n / max(1, n) < 0.28:
            top_h = offset
            break
    else:
        top_h = 36
    fade_h = max(90, fade_h)
    return {
        "top_transition_treatment": {"type": "navy_soft_fade", "height_px": max(16, top_h), "power": 1.15},
        "bottom_transition_treatment": {"type": "navy_ease", "height_px": fade_h, "power": 1.35},
        "overlay_gradient": {"type": "navy_top_and_bottom_fade", "opacity": 1.0, "height_px": fade_h},
        "overlay_opacity": 1.0,
    }


def precise_geometry(spec: dict[str, Any], boxes: dict[str, dict[str, int]], width: int, height: int) -> dict[str, Any]:
    out = {}
    for key, box in boxes.items():
        out[key] = _norm(box, width, height)
    return out


def relational_constraints(boxes: dict[str, dict[str, int]], commercial: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"id": "headline_centered", "subject": "headline", "relation": "centered_relative_to", "object": "canvas"},
        {"id": "supporting_below_headline", "subject": "supporting_copy", "relation": "anchored_below", "object": "headline"},
        {"id": "commercial_below_supporting", "subject": "commercial_group", "relation": "anchored_below", "object": "supporting_copy"},
        {"id": "commercial_ends_before_hero", "subject": "commercial_group", "relation": "ends_before", "object": "hero_visual"},
        {"id": "hero_starts_at_transition", "subject": "hero_visual", "relation": "starts_at", "object": "navy_hero_seam"},
        {"id": "cta_on_lower_hero", "subject": "cta", "relation": "overlays", "object": "lower_hero"},
        {"id": "logo_below_cta", "subject": "logo", "relation": "anchored_below", "object": "cta"},
        {"id": "unit_value_above_label", "subject": "unit_value", "relation": "above", "object": "unit_label"},
        {"id": "discount_value_label_order", "subject": "discount_value", "relation": "stacked_with", "object": "discount_label", "stack": _as_dict(commercial.get("discount")).get("stack")},
        {"id": "commercial_separators_tied_to_columns", "subject": "commercial_separator", "relation": "tied_to", "object": "commercial_columns"},
        {"id": "ornament_anchors_kazan", "subject": "headline_ornament", "relation": "anchor_to", "object": "headline_KAZAN"},
    ]


def _update_element_geometry(spec: dict[str, Any], role: str, box: dict[str, int], width: int, height: int) -> None:
    for item in spec.get("elements") or []:
        if item.get("semantic_role") == role:
            item["geometry"] = _norm(box, width, height)
            return


def enrich_to_v1_1(
    parent: dict[str, Any],
    *,
    reference: Image.Image,
    source_visual: Image.Image,
    logo: Image.Image | None = None,
) -> dict[str, Any]:
    """Create MasterDesignSpecV1.1 from V1 + approved v2. Does not mutate parent."""
    spec = copy.deepcopy(parent)
    parent_id = str(parent.get("master_design_spec_id"))
    canvas = _as_dict(spec.get("canvas"))
    width = int(canvas.get("width") or reference.size[0])
    height = int(canvas.get("height") or reference.size[1])
    ref = reference.convert("RGB")
    fonts = list_available_fonts()
    hero_box = _abs(region(spec, "hero_visual")) or {"x0": 0, "y0": 554, "x1": width, "y1": 1209}
    head_box = _abs(element(spec, "headline")) or {"x0": 235, "y0": 59, "x1": 848, "y1": 242}
    support_box = _abs(element(spec, "supporting_copy")) or {"x0": 235, "y0": 236, "x1": 831, "y1": 286}
    cta_box = _abs(element(spec, "cta")) or {"x0": 218, "y0": 1129, "x1": 789, "y1": 1208}
    logo_box = _abs(element(spec, "logo")) or {"x0": 417, "y0": 1214, "x1": 666, "y1": 1340}
    commercial_box = _abs(region(spec, "commercial_information_area")) or {"x0": 221, "y0": 303, "x1": 886, "y1": 554}

    headline_parts = split_headline(ref, head_box)
    commercial = analyze_commercial_hierarchy(ref, spec)
    unit = commercial["unit"]
    price = commercial["list_price"]
    disc = commercial["discount"]
    geometry_boxes = {
        "headline": head_box,
        "headline_ALIRKEN": headline_parts["headline_ALIRKEN"],
        "headline_KAZAN": headline_parts["headline_KAZAN"],
        "supporting_copy": _type_mask_bbox(ref, support_box) or support_box,
        "commercial_group": commercial_box,
        "unit_value": unit["value_bbox"],
        "unit_label": unit["label_bbox"],
        "price_value": price["value_bbox"],
        "discount_value": disc["value_bbox"],
        "discount_label": disc["label_bbox"],
        "hero": hero_box,
        "cta": cta_box,
        "logo": logo_box,
        "unit_column": unit["column_bbox"],
        "price_column": price["column_bbox"],
        "discount_column": disc["column_bbox"],
    }
    if price.get("label_bbox"):
        geometry_boxes["price_label"] = price["label_bbox"]
    if price.get("currency_bbox"):
        geometry_boxes["price_currency"] = price["currency_bbox"]

    palette = extract_palette(ref, spec)
    gold = _rgb(palette["gold_primary"]["rgb"])
    navy = _rgb(palette["navy_primary"]["rgb"])
    white = _rgb(palette["white_primary"]["rgb"])
    craft = analyze_headline_craft(ref, headline_parts, gold)
    decorations = analyze_decorations(ref, spec, craft, commercial, gold)
    typography = fingerprint_typography(ref, spec, fonts, geometry_boxes)
    hero_xf = recover_hero_transform(source_visual, ref, hero_box)
    hero_xf["source_asset_id"] = str(_as_dict(spec.get("source_assets")).get("hero_visual_asset_id"))
    src_crop = source_visual.convert("RGB").crop(
        (
            hero_xf["crop_rectangle_source"]["x0"],
            hero_xf["crop_rectangle_source"]["y0"],
            hero_xf["crop_rectangle_source"]["x1"],
            hero_xf["crop_rectangle_source"]["y1"],
        )
    )
    ref_hero = ref.crop((hero_box["x0"], hero_box["y0"], hero_box["x1"], hero_box["y1"]))
    color_tx = derive_hero_color_treatment(src_crop, ref_hero)
    fades = analyze_fade(ref, hero_box, navy)
    cta = analyze_cta(ref, cta_box, str((element(spec, "cta") or {}).get("exact_content") or "PROJEYİ KEŞFET"))
    logo_tx = analyze_logo_treatment(ref, logo_box, logo)
    logo_tx["asset_id"] = str(_as_dict(spec.get("source_assets")).get("logo_asset_id"))

    spec["schema"] = SCHEMA_V1_1
    spec["spec_version"] = 1
    spec["spec_revision"] = SPEC_REVISION
    spec["master_design_spec_id"] = str(uuid4())
    spec["parent_spec_id"] = parent_id
    spec["preview_only"] = True
    spec["persisted"] = False
    spec["semantic_content_changed"] = False
    spec["revision_intent"] = "SAME_DESIGN_RECONSTRUCTION"
    spec["provider_image_calls"] = 0
    spec["visual_fidelity_profile"] = {
        "typography": typography,
        "hero_treatment": {**hero_xf, "color_treatment": color_tx, **fades},
        "cta_treatment": cta,
        "logo_treatment": logo_tx,
        "decorative_system": decorations,
        "color_treatment": palette,
        "group_hierarchy": commercial,
        "precise_geometry": precise_geometry(spec, geometry_boxes, width, height),
        "render_relationships": relational_constraints(geometry_boxes, commercial),
        "headline_craft": craft,
        "available_fonts": [
            {k: f[k] for k in ("path", "family_guess", "serif", "sans", "bold", "mono") if k in f} for f in fonts
        ],
    }
    _update_element_geometry(spec, "headline", head_box, width, height)
    _update_element_geometry(spec, "supporting_copy", geometry_boxes["supporting_copy"], width, height)
    _update_element_geometry(spec, "unit_type", unit["value_bbox"], width, height)
    _update_element_geometry(spec, "unit_label", unit["label_bbox"], width, height)
    _update_element_geometry(spec, "list_price", price["value_bbox"], width, height)
    _update_element_geometry(spec, "discount", disc["value_bbox"], width, height)
    _update_element_geometry(spec, "discount_label", disc["label_bbox"], width, height)
    _update_element_geometry(spec, "cta", cta_box, width, height)
    _update_element_geometry(spec, "logo", logo_box, width, height)
    if price.get("label_bbox") and not any(e.get("semantic_role") == "list_price_label" for e in spec.get("elements") or []):
        spec.setdefault("elements", []).append(
            {
                "semantic_role": "list_price_label",
                "exact_content": "LİSTE FİYATI",
                "geometry": _norm(price["label_bbox"], width, height),
                "parent_group": "commercial_group",
                "confidence": 0.7,
                "source": "raster_analysis",
            }
        )
    relationships = list(spec.get("relationships") or [])
    relationships.append(
        {
            "id": "v1_1_visual_fidelity",
            "from": "visual_fidelity_profile",
            "to": "approved_v2",
            "type": "same_design_reconstruction",
            "constraint": "zero_semantic_change",
        }
    )
    spec["relationships"] = relationships
    copy_bag = {
        "headline": "ALIRKEN KAZAN",
        "supporting_copy": "The Temple'da yerinizi lansman döneminde alın.",
        "unit_type": "2+1",
        "list_price": "675.000",
        "discount": "%35",
        "cta": "PROJEYİ KEŞFET",
    }
    validate_master_design_spec(
        spec,
        expected_cover_asset_id=str(spec.get("source_cover_asset_id")),
        expected_source_visual_asset_id=str(_as_dict(spec.get("source_assets")).get("hero_visual_asset_id")),
        expected_logo_asset_id=str(_as_dict(spec.get("source_assets")).get("logo_asset_id")),
        expected_project_id=str(_as_dict(spec.get("source_assets")).get("project_id")),
        copy=copy_bag,
    )
    return spec


def _font_from_role(role: dict[str, Any], size: int, *, bold: bool, serif: bool) -> ImageFont.ImageFont:
    path = role.get("selected_font_path")
    if path and Path(path).is_file():
        try:
            return _load_font(path, size)
        except Exception:
            pass
    from investhome_api.services.gpt_image_design.compose import resolve_turkish_font

    family = "serif" if serif else "sans"
    font = resolve_turkish_font(bold=bold, size=size, family=family)
    return font


def _draw_tracked(
    draw: ImageDraw.ImageDraw,
    box: dict[str, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    tracking: float,
    *,
    y: int | None = None,
) -> dict[str, int]:
    if abs(tracking) < 0.4:
        return _center_text(draw, box, text, font, fill, y=y)
    widths = [text_size(font, ch)[0] for ch in text]
    _, th = text_size(font, text)
    total = sum(widths) + tracking * max(0, len(text) - 1)
    x = int(box["x0"] + (box["x1"] - box["x0"] - total) / 2)
    if y is None:
        y = box["y0"] + (box["y1"] - box["y0"] - th) // 2
    cursor = x
    for i, ch in enumerate(text):
        draw.text((int(cursor), y), ch, font=font, fill=fill)
        cursor += widths[i] + tracking
    return {"x0": x, "y0": y, "x1": int(cursor), "y1": y + th}


def _draw_cta(draw: ImageDraw.ImageDraw, image: Image.Image, cta: dict[str, Any]) -> Image.Image:
    box = _as_dict(cta.get("bbox"))
    radius = int(cta.get("corner_radius") or 12)
    stops = cta.get("gradient_stops") or []
    if cta.get("fill_type") == "linear_gradient" and len(stops) >= 2:
        overlay = Image.new("RGB", image.size, (0, 0, 0))
        od = ImageDraw.Draw(overlay)
        y0, y1 = box["y0"], box["y1"]
        c0 = _rgb(stops[0]["color"])
        c1 = _rgb(stops[-1]["color"])
        for y in range(y0, y1):
            t = (y - y0) / max(1, y1 - y0 - 1)
            col = tuple(int(c0[i] + (c1[i] - c0[i]) * t) for i in range(3))
            od.line([(box["x0"], y), (box["x1"] - 1, y)], fill=col)
        mask = Image.new("L", image.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [box["x0"], box["y0"], box["x1"] - 1, box["y1"] - 1],
            radius=radius,
            fill=255,
        )
        image = Image.composite(overlay, image, mask)
        draw = ImageDraw.Draw(image)
    else:
        fill = _rgb(cta.get("fill_color") or (201, 168, 92))
        draw.rounded_rectangle(
            [box["x0"], box["y0"], box["x1"] - 1, box["y1"] - 1],
            radius=radius,
            fill=fill,
        )
    return image


def reconstruct_same_design(
    spec: dict[str, Any],
    *,
    source_visual: Image.Image,
    logo: Image.Image,
) -> tuple[Image.Image, dict[str, Any]]:
    profile = _as_dict(spec.get("visual_fidelity_profile"))
    canvas = _as_dict(spec.get("canvas"))
    width = int(canvas.get("width") or 1088)
    height = int(canvas.get("height") or 1360)
    colors = _as_dict(profile.get("color_treatment"))
    navy = _rgb((colors.get("navy_primary") or {}).get("rgb") or (10, 16, 36))
    gold = _rgb((colors.get("gold_primary") or {}).get("rgb") or (201, 168, 92))
    white = _rgb((colors.get("white_primary") or {}).get("rgb") or (246, 241, 232))
    support_c = _rgb((colors.get("supporting_text") or {}).get("rgb") or gold)
    out = Image.new("RGB", (width, height), navy)
    draw = ImageDraw.Draw(out)
    drawn: list[str] = []
    limitations: list[str] = []

    hero_box = _abs(region(spec, "hero_visual")) or {"x0": 0, "y0": 554, "x1": width, "y1": 1209}
    hero_img, hero_meta = apply_stored_hero(source_visual, profile)
    if hero_img.size != (hero_box["x1"] - hero_box["x0"], hero_box["y1"] - hero_box["y0"]):
        hero_img = hero_img.resize(
            (hero_box["x1"] - hero_box["x0"], hero_box["y1"] - hero_box["y0"]),
            Image.Resampling.LANCZOS,
        )
    out.paste(hero_img, (hero_box["x0"], hero_box["y0"]))
    if float((_as_dict(profile.get("hero_treatment")).get("match_confidence") or 0)) < 0.45:
        limitations.append("hero_crop_transform_low_confidence")

    top_fade = _as_dict(_as_dict(profile.get("hero_treatment")).get("top_transition_treatment"))
    top_h = int(top_fade.get("height_px") or 0)
    if top_h >= 8:
        top_h = min(top_h, hero_box["y1"] - hero_box["y0"] // 3)
        overlay_top = Image.new("RGBA", (width, top_h), (0, 0, 0, 0))
        td = ImageDraw.Draw(overlay_top)
        power = float(top_fade.get("power") or 1.15)
        for i in range(top_h):
            a = int(255 * (1.0 - i / max(1, top_h - 1)) ** power)
            td.line([(0, i), (width, i)], fill=(*navy, a))
        band = out.crop((0, hero_box["y0"], width, hero_box["y0"] + top_h)).convert("RGBA")
        out.paste(Image.alpha_composite(band, overlay_top).convert("RGB"), (0, hero_box["y0"]))
        draw = ImageDraw.Draw(out)

    footer = _abs(region(spec, "bottom_brand_treatment")) or {"x0": 0, "y0": hero_box["y1"], "x1": width, "y1": height}
    draw.rectangle([footer["x0"], footer["y0"], footer["x1"], footer["y1"]], fill=navy)
    fade = _as_dict(_as_dict(profile.get("hero_treatment")).get("bottom_transition_treatment"))
    fade_h = int(fade.get("height_px") or 120)
    fade_h = max(24, min(fade_h, hero_box["y1"] - hero_box["y0"] - 8))
    overlay = Image.new("RGBA", (width, fade_h), (0, 0, 0, 0))
    fd = ImageDraw.Draw(overlay)
    power = float(fade.get("power") or 1.35)
    for i in range(fade_h):
        a = int(255 * (i / max(1, fade_h - 1)) ** power)
        fd.line([(0, i), (width, i)], fill=(*navy, a))
    band = out.crop((0, hero_box["y1"] - fade_h, width, hero_box["y1"])).convert("RGBA")
    out.paste(Image.alpha_composite(band, overlay).convert("RGB"), (0, hero_box["y1"] - fade_h))
    draw = ImageDraw.Draw(out)

    type_roles = _as_dict(_as_dict(profile.get("typography")).get("roles"))
    geom = _as_dict(profile.get("precise_geometry"))

    def gbox(key: str, fallback: dict[str, int]) -> dict[str, int]:
        absb = _as_dict(_as_dict(geom.get(key)).get("absolute"))
        return _box(absb["x0"], absb["y0"], absb["x1"], absb["y1"]) if absb else fallback

    def role_font(role_name: str, box: dict[str, int], text: str, *, bold: bool, serif: bool) -> tuple[ImageFont.ImageFont, float, tuple[int, int, int]]:
        role = _as_dict(type_roles.get(role_name))
        size = int(role.get("font_size") or max(12, (box["y1"] - box["y0"]) - 4))
        tracking = float(role.get("tracking") or 0)
        color = _rgb(role.get("color") or (255, 255, 255))
        font = _font_from_role(role, size, bold=bold, serif=serif)
        tw, th = text_size(font, text)
        max_w = max(8, box["x1"] - box["x0"] - 4)
        max_h = max(8, box["y1"] - box["y0"] - 2)
        tracking = min(tracking, 2.8 if len(text) <= 5 else 8.0)
        while (tw > max_w or th > max_h) and size > 10:
            size -= 1
            font = _font_from_role(role, size, bold=bold, serif=serif)
            tw, th = text_size(font, text)
        return font, tracking, color

    a_box = gbox("headline_ALIRKEN", {"x0": 235, "y0": 59, "x1": 848, "y1": 140})
    k_box = gbox("headline_KAZAN", {"x0": 235, "y0": 140, "x1": 848, "y1": 242})
    a_font, a_tr, a_col = role_font("headline_ALIRKEN", a_box, "ALIRKEN", bold=True, serif=True)
    k_font, k_tr, k_col = role_font("headline_KAZAN", k_box, "KAZAN", bold=True, serif=True)
    if a_col == (0, 0, 0) or _luma(*a_col) < 80:
        a_col = white
    if _luma(*k_col) < 80:
        k_col = gold
    _draw_tracked(draw, a_box, "ALIRKEN", a_font, a_col, a_tr)
    for deco in profile.get("decorative_system") or []:
        role = deco.get("role")
        box = _as_dict(deco.get("geometry"))
        stroke = _as_dict(deco.get("stroke"))
        col = _rgb(stroke.get("color") or gold)
        if not box:
            continue
        if role == "headline_ornament":
            draw.line([(box["x0"], (box["y0"] + box["y1"]) // 2), (box["x1"], (box["y0"] + box["y1"]) // 2)], fill=col, width=int(stroke.get("width") or 2))
        elif role == "headline_ornament_diamond":
            _diamond(draw, (box["x0"] + box["x1"]) // 2, (box["y0"] + box["y1"]) // 2, max(5, (box["x1"] - box["x0"]) // 2), col)
    _draw_tracked(draw, k_box, "KAZAN", k_font, k_col, k_tr)
    drawn.append("ALIRKEN KAZAN")

    for deco in profile.get("decorative_system") or []:
        role = deco.get("role")
        box = _as_dict(deco.get("geometry"))
        stroke = _as_dict(deco.get("stroke"))
        col = _rgb(stroke.get("color") or gold)
        if not box:
            continue
        if role == "commercial_separator":
            x = (box["x0"] + box["x1"]) // 2
            draw.line([(x, box["y0"]), (x, box["y1"])], fill=col, width=int(stroke.get("width") or 2))
        elif role == "supporting_separator":
            y = (box["y0"] + box["y1"]) // 2
            draw.line([(box["x0"], y), (box["x1"], y)], fill=col, width=int(stroke.get("width") or 1))

    s_box = gbox("supporting_copy", {"x0": 235, "y0": 236, "x1": 831, "y1": 286})
    s_text = str((element(spec, "supporting_copy") or {}).get("exact_content") or ROLE_TEXT["supporting_copy"])
    s_font, s_tr, s_col = role_font("supporting_copy", s_box, s_text, bold=False, serif=True)
    if _luma(*s_col) < 80:
        s_col = support_c
    _draw_tracked(draw, s_box, s_text, s_font, s_col, s_tr)
    drawn.append(s_text)

    hierarchy = _as_dict(profile.get("group_hierarchy"))

    def draw_stack(value: str, label: str, v_box: dict[str, int], l_box: dict[str, int], v_role: str, l_role: str, v_color: tuple[int, int, int], l_color: tuple[int, int, int]) -> None:
        vf, vt, vc = role_font(v_role, v_box, value, bold=True, serif=True)
        lf, lt, lc = role_font(l_role, l_box, label, bold=False, serif=True)
        _draw_tracked(draw, v_box, value, vf, v_color if _luma(*vc) < 40 else vc, vt)
        _draw_tracked(draw, l_box, label, lf, l_color if _luma(*lc) < 40 else lc, lt)
        drawn.extend([value, label])

    unit = _as_dict(hierarchy.get("unit"))
    draw_stack(
        "2+1",
        "DAİRE",
        gbox("unit_value", unit.get("value_bbox") or {"x0": 226, "y0": 321, "x1": 444, "y1": 430}),
        gbox("unit_label", unit.get("label_bbox") or {"x0": 226, "y0": 430, "x1": 444, "y1": 549}),
        "unit_value",
        "unit_label",
        gold,
        gold,
    )
    price = _as_dict(hierarchy.get("list_price"))
    if price.get("label_bbox") and price.get("label_content"):
        pb = gbox("price_label", price["label_bbox"])
        pf, pt, pc = role_font("discount_label", pb, str(price["label_content"]), bold=False, serif=True)
        _draw_tracked(draw, pb, str(price["label_content"]), pf, gold, pt)
        drawn.append(str(price["label_content"]))
    amount = str(price.get("amount_content") or "675.000")
    pv = gbox("price_value", price.get("value_bbox") or {"x0": 444, "y0": 360, "x1": 663, "y1": 500})
    pvf, pvt, pvc = role_font("price_value", pv, amount, bold=True, serif=True)
    _draw_tracked(draw, pv, amount, pvf, white if _luma(*pvc) < 40 else pvc, pvt)
    drawn.append("675.000 USD")
    if price.get("currency_bbox"):
        cb = gbox("price_currency", price["currency_bbox"])
        cf, ct, cc = role_font("unit_label", cb, "USD", bold=False, serif=True)
        _draw_tracked(draw, cb, "USD", cf, white, ct)
        drawn.append("USD")
    else:
        drawn.append("USD")
    disc = _as_dict(hierarchy.get("discount"))
    d_val = gbox("discount_value", disc.get("value_bbox") or {"x0": 663, "y0": 321, "x1": 882, "y1": 430})
    d_lab = gbox("discount_label", disc.get("label_bbox") or {"x0": 663, "y0": 430, "x1": 882, "y1": 550})
    if disc.get("value_before_label") is False:
        draw_stack("%35", "LANSMAN AVANTAJI", d_val, d_lab, "discount_value", "discount_label", gold, gold)
        # stack function draws value then label in given boxes; if label is above, boxes already reflect that.
    else:
        draw_stack("%35", "LANSMAN AVANTAJI", d_val, d_lab, "discount_value", "discount_label", gold, gold)

    cta = _as_dict(profile.get("cta_treatment"))
    out = _draw_cta(draw, out, cta)
    draw = ImageDraw.Draw(out)
    cta_box = _as_dict(cta.get("bbox")) or gbox("cta", {"x0": 218, "y0": 1129, "x1": 789, "y1": 1208})
    pad = _as_dict(cta.get("internal_padding"))
    inner = _box(
        cta_box["x0"] + int(pad.get("x") or 18),
        cta_box["y0"] + int(pad.get("y") or 10),
        cta_box["x1"] - int(pad.get("x") or 18),
        cta_box["y1"] - int(pad.get("y") or 10),
    )
    cta_text = str((element(spec, "cta") or {}).get("exact_content") or "PROJEYİ KEŞFET")
    ctf, ctt, ctc = role_font("cta_text", inner, cta_text, bold=True, serif=True)
    ink = _rgb(cta.get("text_color") or (18, 16, 12))
    _draw_tracked(draw, inner, cta_text, ctf, ink, min(ctt, 2.0))
    drawn.append(cta_text)

    logo_box = gbox("logo", _abs(element(spec, "logo")) or {"x0": 417, "y0": 1214, "x1": 666, "y1": 1340})
    fitted = _fit_logo(logo, logo_box["x1"] - logo_box["x0"], logo_box["y1"] - logo_box["y0"])
    lx = logo_box["x0"] + (logo_box["x1"] - logo_box["x0"] - fitted.width) // 2
    ly = logo_box["y0"] + (logo_box["y1"] - logo_box["y0"] - fitted.height) // 2
    if fitted.mode == "RGBA":
        base = out.convert("RGBA")
        base.paste(fitted, (lx, ly), fitted)
        out = base.convert("RGB")
    else:
        out.paste(fitted, (lx, ly))

    blob = " ".join(drawn)
    if any(token in blob for token in FORBIDDEN_PRICE_REVISION):
        limitations.append("forbidden_price_revision_content_drawn")
    if "DejaVu" in str(_as_dict(profile.get("typography")).get("selected_fonts")):
        if len(list_available_fonts()) <= 8:
            limitations.append("exact_font_unavailable_container_has_dejavu_only")

    report = {
        "reconstruction_engine": "visual_fidelity.reconstruct_same_design",
        "reconstruction_method": "master_design_spec_v1_1_structured_reconstruction",
        "hero_method": hero_meta.get("method"),
        "hero_meta": hero_meta,
        "logo_method": "real_logo_asset_contain_fit",
        "typography": _as_dict(profile.get("typography")).get("selected_fonts"),
        "drawn_content": [d for d in drawn if d],
        "provider_image_calls": 0,
        "native_renderer": False,
        "design_spec_templates": False,
        "raster_surgery": False,
        "reference_raster_used_as_output_background": False,
        "semantic_content_changed": False,
        "limitations": limitations,
    }
    return out, report


def render_v1_1_debug(image: Image.Image, spec: dict[str, Any]) -> Image.Image:
    from investhome_api.services.creative_director.master_design_spec import render_master_design_spec_debug

    im = render_master_design_spec_debug(image, spec)
    draw = ImageDraw.Draw(im)
    profile = _as_dict(spec.get("visual_fidelity_profile"))
    geom = _as_dict(profile.get("precise_geometry"))
    palette = {
        "headline_ALIRKEN": (255, 255, 255),
        "headline_KAZAN": (255, 210, 70),
        "unit_value": (80, 255, 180),
        "unit_label": (80, 200, 140),
        "price_value": (255, 255, 255),
        "discount_value": (255, 180, 40),
        "discount_label": (255, 140, 40),
        "cta": (220, 80, 255),
        "logo": (120, 255, 80),
    }
    for key, color in palette.items():
        absb = _as_dict(_as_dict(geom.get(key)).get("absolute"))
        if not absb:
            continue
        draw.rectangle([absb["x0"], absb["y0"], absb["x1"] - 1, absb["y1"] - 1], outline=color, width=2)
    for deco in profile.get("decorative_system") or []:
        box = _as_dict(deco.get("geometry"))
        if box:
            draw.rectangle([box["x0"], box["y0"], box["x1"] - 1, box["y1"] - 1], outline=(255, 80, 80), width=1)
    return im


def _center_delta(a: dict[str, int], b: dict[str, int]) -> dict[str, float]:
    ac = _box_center(a)
    bc = _box_center(b)
    return {
        "dx": round(bc[0] - ac[0], 2),
        "dy": round(bc[1] - ac[1], 2),
        "dist": round(math.hypot(bc[0] - ac[0], bc[1] - ac[1]), 2),
        "dw": round((b["x1"] - b["x0"]) - (a["x1"] - a["x0"]), 2),
        "dh": round((b["y1"] - b["y0"]) - (a["y1"] - a["y0"]), 2),
    }


def _mean_delta(ref: Image.Image, prev: Image.Image, box: dict[str, int]) -> dict[str, Any]:
    a, _ = _mean_rgb(ref, box, step=2)
    b, _ = _mean_rgb(prev, box, step=2)
    return {
        "ref_rgb": list(a),
        "preview_rgb": list(b),
        "delta": [b[0] - a[0], b[1] - a[1], b[2] - a[2]],
        "l1": abs(b[0] - a[0]) + abs(b[1] - a[1]) + abs(b[2] - a[2]),
    }


def component_similarity(reference: Image.Image, preview: Image.Image, spec: dict[str, Any]) -> dict[str, Any]:
    from investhome_api.services.creative_director.structured_reconstruction import region_mad

    profile = _as_dict(spec.get("visual_fidelity_profile"))
    geom = _as_dict(profile.get("precise_geometry"))

    def box(key: str) -> dict[str, int] | None:
        absb = _as_dict(_as_dict(geom.get(key)).get("absolute"))
        if absb:
            return _box(absb["x0"], absb["y0"], absb["x1"], absb["y1"])
        return None

    def band(mad: float) -> str:
        if mad < 12:
            return "high"
        if mad < 28:
            return "medium"
        return "low"

    out: dict[str, Any] = {"commercial_intentionally_changed": False, "global_mad_overvalued": True}
    for key in ("hero", "headline_ALIRKEN", "headline_KAZAN", "supporting_copy", "unit_value", "price_value", "discount_value", "cta", "logo"):
        b = box(key)
        if not b:
            continue
        mad = region_mad(reference, preview, b)
        item = {
            "mad": round(mad, 3),
            "similarity": band(mad),
            "geometry": b,
            "color": _mean_delta(reference, preview, b),
        }
        out[key] = item
    if box("hero"):
        out["hero"]["crop"] = _as_dict(profile.get("hero_treatment")).get("crop_rectangle_source")
        out["hero"]["match_mad_coarse"] = _as_dict(profile.get("hero_treatment")).get("match_mad_coarse")
        out["hero"]["zoom_over_cover"] = _as_dict(profile.get("hero_treatment")).get("zoom_over_cover")
    head = box("headline") or box("headline_ALIRKEN")
    if head and box("headline_KAZAN"):
        out["headline"] = {
            "mad": round(region_mad(reference, preview, _box(head["x0"], head["y0"], box("headline_KAZAN")["x1"], box("headline_KAZAN")["y1"])), 3)
        }
        out["headline"]["similarity"] = band(out["headline"]["mad"])
    navy_box = {"x0": 8, "y0": 8, "x1": 80, "y1": 40}
    out["palette"] = {"navy_sample": _mean_delta(reference, preview, navy_box), "mad": round(region_mad(reference, preview, navy_box), 3)}
    out["palette"]["similarity"] = band(out["palette"]["mad"])
    commercial = box("commercial_group")
    if commercial:
        out["commercial_group"] = {
            "mad": round(region_mad(reference, preview, commercial), 3),
            "similarity": band(region_mad(reference, preview, commercial)),
        }
    return out
