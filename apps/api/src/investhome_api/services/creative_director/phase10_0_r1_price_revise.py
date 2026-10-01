"""Phase 10.0-R1 — clean PRICE_ONLY replacement from the locked Master.

Recover the underlying price-territory background, remove 675.000 USD
completely, then rasterize 750.000 USD as fresh Chromium typography.
Do not paint new glyphs over old glyphs.
"""

from __future__ import annotations

import base64
import io
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.phase5_creative_quality import _font
from investhome_api.services.creative_director.phase5_design_scene import font_face_css, render_html_to_png
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase9_0_compose import render_pair
from investhome_api.services.creative_director.phase9_1_r1_compose import INK_LIGHT, W, H
from investhome_api.services.creative_director.phase10_0_price_revise import (
    PRICE_LEFT,
    PRICE_SIZE_PX,
    PRICE_TOP,
    PRICE_TRACKING,
    glyph_mask,
    mask_bbox,
    pixel_delta_outside,
    render_pixel_diff,
    render_price_layer,
    render_territory,
)
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY

HOLE_DILATE = 5
RESIDUE_LUMA = 110
UNIT_GUARD_PAD = 6
CTA_TOP = 0.362


def _png_data_uri(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="PNG", optimize=False)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _luma(pixel: tuple[int, int, int]) -> int:
    return (299 * pixel[0] + 587 * pixel[1] + 114 * pixel[2]) // 1000


def align_mask_to_parent(parent: Image.Image, mask: Image.Image, window: tuple[int, int, int, int], max_shift: int = 4) -> Image.Image:
    px = parent.convert("RGB").load()
    x0, y0, x1, y1 = window
    best_dx = 0
    best_dy = 0
    best = -1
    for dy in range(-max_shift, max_shift + 1):
        for dx in range(-max_shift, max_shift + 1):
            shifted = ImageChops.offset(mask, dx, dy)
            sm = shifted.load()
            score = 0
            for y in range(y0, y1):
                for x in range(x0, x1):
                    if sm[x, y] >= 128 and _luma(px[x, y]) >= 100:
                        score += 1
            if score > best:
                best = score
                best_dx, best_dy = dx, dy
    return ImageChops.offset(mask, best_dx, best_dy)


def parent_glyph_hole(parent: Image.Image, window: tuple[int, int, int, int]) -> Image.Image:
    """Catch parent AA the chroma mask missed. Ivory only, not slat highlights."""
    hole = Image.new("L", parent.size, 0)
    px = parent.convert("RGB").load()
    m = hole.load()
    x0, y0, x1, y1 = window
    for y in range(y0, y1):
        for x in range(x0, x1):
            if _luma(px[x, y]) >= 130:
                m[x, y] = 255
    return dilate_mask(hole, 3)


def dilate_mask(mask: Image.Image, size: int = HOLE_DILATE) -> Image.Image:
    out = mask.convert("L")
    if size >= 3:
        out = out.filter(ImageFilter.MaxFilter(size if size % 2 else size + 1))
    return out


def inpaint_holes(parent: Image.Image, hole: Image.Image) -> Image.Image:
    """Reconstruct glyph holes along vertical columns so curtain/slat grain continues."""
    out = parent.convert("RGB").copy()
    px = out.load()
    m = hole.convert("L").load()
    w, h = out.size
    for x in range(w):
        y = 0
        while y < h:
            if m[x, y] < 128:
                y += 1
                continue
            y0 = y
            while y < h and m[x, y] >= 128:
                y += 1
            y1 = y
            above = y0 - 1
            below = y1
            while above >= 0 and m[x, above] >= 128:
                above -= 1
            while below < h and m[x, below] >= 128:
                below += 1
            if above < 0 and below >= h:
                continue
            if above < 0:
                fill = px[x, below]
                for yy in range(y0, y1):
                    px[x, yy] = fill
            elif below >= h:
                fill = px[x, above]
                for yy in range(y0, y1):
                    px[x, yy] = fill
            else:
                a = px[x, above]
                b = px[x, below]
                span = max(below - above, 1)
                for yy in range(y0, y1):
                    t = (yy - above) / span
                    px[x, yy] = (
                        int(a[0] * (1 - t) + b[0] * t),
                        int(a[1] * (1 - t) + b[1] * t),
                        int(a[2] * (1 - t) + b[2] * t),
                    )
    return out


def scrub_bright_leftovers(image: Image.Image, hole: Image.Image, *, luma_cap: int = RESIDUE_LUMA) -> Image.Image:
    out = image.convert("RGB").copy()
    px = out.load()
    m = hole.convert("L").load()
    w, h = out.size
    for y in range(h):
        for x in range(w):
            if m[x, y] < 128 or _luma(px[x, y]) < luma_cap:
                continue
            sample = None
            for k in range(1, 24):
                yu, yd = y - k, y + k
                if yu >= 0 and m[x, yu] < 128 and _luma(px[x, yu]) < luma_cap:
                    sample = px[x, yu]
                    break
                if yd < h and m[x, yd] < 128 and _luma(px[x, yd]) < luma_cap:
                    sample = px[x, yd]
                    break
            if sample is None:
                for k in range(1, 16):
                    xl, xr = x - k, x + k
                    if xl >= 0 and _luma(px[xl, y]) < luma_cap:
                        sample = px[xl, y]
                        break
                    if xr < w and _luma(px[xr, y]) < luma_cap:
                        sample = px[xr, y]
                        break
            if sample is not None:
                px[x, y] = sample
    return out
    return out


def residue_report(clean: Image.Image, hole: Image.Image) -> dict[str, Any]:
    rgb = clean.convert("RGB")
    h = hole.convert("L")
    px, mx = rgb.load(), h.load()
    bright = 0
    n = 0
    luma_sum = 0
    for y in range(rgb.size[1]):
        for x in range(rgb.size[0]):
            if mx[x, y] < 128:
                continue
            n += 1
            lum = _luma(px[x, y])
            luma_sum += lum
            if lum >= RESIDUE_LUMA:
                bright += 1
    mean = (luma_sum / n) if n else 0.0
    return {
        "hole_pixels": n,
        "bright_residue_pixels": bright,
        "mean_luma_in_holes": round(mean, 2),
        "pass": bright == 0,
    }


def plate_html(
    *,
    bg_uri: str,
    text: str | None,
    width: int,
    height: int,
    text_left: float,
    text_top: float,
    font_css: str,
) -> str:
    price = f'<p class="price">{text}</p>' if text else ""
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8"/>
<style>
{font_css}
html,body{{margin:0;padding:0;width:{width}px;height:{height}px;overflow:hidden;background:#000;}}
.bg{{position:absolute;left:0;top:0;width:{width}px;height:{height}px;display:block;image-rendering:auto;}}
.price{{position:absolute;left:{text_left:.3f}px;top:{text_top:.3f}px;margin:0;color:{INK_LIGHT};
  font-family:'Cormorant Garamond',serif;font-size:{PRICE_SIZE_PX}px;font-weight:500;
  letter-spacing:{PRICE_TRACKING}em;white-space:nowrap;}}
</style>
</head>
<body>
<img class="bg" alt="" src="{bg_uri}"/>
{price}
</body>
</html>
"""


def render_plate(bg: Image.Image, text: str | None, *, text_left: float, text_top: float, font_css: str) -> Image.Image:
    tw, th = bg.size
    html = plate_html(
        bg_uri=_png_data_uri(bg),
        text=text,
        width=tw,
        height=th,
        text_left=text_left,
        text_top=text_top,
        font_css=font_css,
    )
    return render_html_to_png(html, width=tw, height=th).convert("RGB")


def _rect_mask(size: tuple[int, int], box: tuple[int, int, int, int]) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rectangle([box[0], box[1], box[2] - 1, box[3] - 1], fill=255)
    return mask
    mask = Image.new("L", a.size, 0)
    pa, pb, pm = a.convert("RGB").load(), b.convert("RGB").load(), mask.load()
    for y in range(a.size[1]):
        for x in range(a.size[0]):
            d = max(abs(pa[x, y][i] - pb[x, y][i]) for i in range(3))
            if d >= threshold:
                pm[x, y] = 255
    return mask.filter(ImageFilter.MaxFilter(3))


def apply_clean_price_revision(
    parent: Image.Image,
    *,
    old_value: str,
    new_value: str,
) -> tuple[Image.Image, dict[str, Any]]:
    if parent.size != CANVAS_4X5:
        raise RuntimeError(f"locked master canvas must be {CANVAS_4X5}")
    registry = build_font_registry()
    font_css = font_face_css(registry)
    old_layer = render_price_layer(old_value, font_css=font_css)
    new_layer = render_price_layer(new_value, font_css=font_css)
    old_tight = glyph_mask(old_layer)
    new_mask_full = glyph_mask(new_layer)
    tight_box = mask_bbox(old_tight)
    new_box = mask_bbox(new_mask_full)
    unit_guard = tight_box[2] + UNIT_GUARD_PAD
    cta_y = int(round(CTA_TOP * H)) - 4
    pad = 4
    window = (
        min(tight_box[0], new_box[0]) - pad,
        min(tight_box[1], new_box[1]) - pad,
        min(unit_guard, max(tight_box[2], new_box[2]) + pad),
        min(cta_y, max(tight_box[3], new_box[3]) + pad),
    )
    aligned = align_mask_to_parent(parent, old_tight, window)
    hole = dilate_mask(aligned, HOLE_DILATE)
    extra = parent_glyph_hole(parent, window)
    hole = ImageChops.lighter(hole, extra)
    hole = ImageChops.multiply(hole, _rect_mask(parent.size, window))
    old_box = mask_bbox(hole) if hole.getbbox() else tight_box
    territory = (
        min(window[0], old_box[0]),
        min(window[1], old_box[1]),
        min(unit_guard, max(window[2], old_box[2])),
        min(cta_y, max(window[3], old_box[3])),
    )
    clean_full = inpaint_holes(parent, hole)
    aligned_hole = dilate_mask(aligned, HOLE_DILATE)
    clean_full = scrub_bright_leftovers(clean_full, aligned_hole)
    residue = residue_report(clean_full, aligned_hole)
    if not residue["pass"]:
        hole = dilate_mask(hole, 5)
        hole = ImageChops.multiply(hole, _rect_mask(parent.size, territory))
        clean_full = inpaint_holes(parent, hole)
        clean_full = scrub_bright_leftovers(clean_full, hole)
        residue = residue_report(clean_full, aligned_hole)
    original_crop = parent.crop(territory)
    clean_crop = clean_full.crop(territory)
    text_left = PRICE_LEFT * W - territory[0]
    text_top = PRICE_TOP * H - territory[1]
    priced_plate = render_plate(clean_crop, new_value, text_left=text_left, text_top=text_top, font_css=font_css)
    child = clean_full.copy()
    region = child.crop(territory)
    rp, pp, cp = region.load(), priced_plate.load(), clean_crop.load()
    for y in range(region.size[1]):
        for x in range(region.size[0]):
            # Stamp only native type: ivory is far brighter than the reconstructed plate.
            if _luma(pp[x, y]) > _luma(cp[x, y]) + 32:
                rp[x, y] = pp[x, y]
    child.paste(region, (territory[0], territory[1]))
    delta = pixel_delta_outside(parent, child, territory)
    meta = {
        "old_value": old_value,
        "new_value": new_value,
        "method": "inpaint_old_glyphs_then_chromium_price_on_clean_plate",
        "territory": list(territory),
        "old_glyph_bbox": list(old_box),
        "new_glyph_bbox": list(new_box),
        "unit_guard": unit_guard,
        "layout_adjusted": False,
        "residue": residue,
        "pixel_delta": delta,
        "font_family": "Cormorant Garamond",
        "gpt_image_calls": 0,
        "source": "LOCKED_MASTER_03",
    }
    extras = {
        "original_crop": original_crop,
        "clean_full": clean_full,
        "clean_crop": clean_crop,
        "new_plate": priced_plate,
        "hole": hole,
    }
    meta["extras"] = extras
    return child, meta


def render_labeled_crop(image: Image.Image, title: str, size: tuple[int, int] = (1088, 1360)) -> Image.Image:
    canvas = Image.new("RGB", size, (14, 12, 10))
    draw = ImageDraw.Draw(canvas)
    draw.text((48, 36), title, font=_font(22), fill=GOLD)
    tile = image.copy()
    tile.thumbnail((992, 1180), Image.Resampling.NEAREST)
    canvas.paste(tile.convert("RGB"), (48, 90))
    return canvas


def render_200_inspection(parent: Image.Image, child: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    x0, y0, x1, y1 = box
    pad = 18
    crop_box = (max(0, x0 - pad), max(0, y0 - pad), min(parent.size[0], x1 + pad), min(parent.size[1], y1 + pad))
    cw, ch = crop_box[2] - crop_box[0], crop_box[3] - crop_box[1]
    left = parent.crop(crop_box).resize((cw * 2, ch * 2), Image.Resampling.NEAREST)
    right = child.crop(crop_box).resize((cw * 2, ch * 2), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (1760, 900), (14, 12, 10))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "07  200% PRICE INSPECTION", font=_font(20), fill=GOLD)
    x = 36
    for label, tile in (("ORIGINAL  675.000 USD", left), ("R1  750.000 USD", right)):
        fit = tile.copy()
        fit.thumbnail((820, 760), Image.Resampling.NEAREST)
        canvas.paste(fit.convert("RGB"), (x, 64))
        draw.text((x, 850), label, font=_font(16), fill=IVORY)
        x += 860
    return canvas


def render_r1_review(parent: Image.Image, child: Image.Image, zoom: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 980), (14, 12, 10))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 16), "09  HUMAN REVIEW BOARD  —  PRICE_ONLY R1  DRAFT", font=_font(18), fill=GOLD)
    x = 36
    for label, image in (("LOCKED MASTER", parent), ("R1 CHILD", child), ("200% INSPECTION", zoom)):
        tile = image.copy()
        tile.thumbnail((580, 840), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 920), label, font=_font(16), fill=IVORY)
        x += 620
    return canvas


def render_parent_vs_r1(parent: Image.Image, child: Image.Image) -> Image.Image:
    return render_pair(parent, child, "PARENT  LOCKED  675.000 USD", "R1  DRAFT  750.000 USD", "06  PARENT vs R1")
