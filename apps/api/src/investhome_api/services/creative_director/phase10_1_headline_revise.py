"""Phase 10.1 — HEADLINE_ONLY clean recomposition from locked Master 03.

Recover the ALIRKEN / KAZAN territory, then rasterize
ŞİMDİ YATIRIM ZAMANI as fresh Chromium typography inside the existing
headline field. Do not paint new glyphs over old glyphs.
"""

from __future__ import annotations

import html as html_lib
from typing import Any

from PIL import Image, ImageChops, ImageDraw

from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.phase5_creative_quality import _font
from investhome_api.services.creative_director.phase5_design_scene import font_face_css, render_html_to_png
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase9_0_compose import render_pair
from investhome_api.services.creative_director.phase9_1_r1_compose import H, INK_LIGHT, OPEN_TOP_X, W
from investhome_api.services.creative_director.phase10_0_price_revise import CHROMA, glyph_mask, mask_bbox, pixel_delta_outside, render_pixel_diff
from investhome_api.services.creative_director.phase10_0_r1_price_revise import (
    _luma,
    _png_data_uri,
    align_mask_to_parent,
    dilate_mask,
)
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY

HEADLINE_LEFT = 0.045
HEADLINE_TOP = 0.120
LINE2_TOP = 0.190
HEADLINE_SIZE = 74
HEADLINE_TRACKING = 0.035
HEADLINE_LH = 0.94
LOC_TOP = 0.092
COMMERCIAL_TOP = 0.276
MIN_SIZE = 56
STAMP_LUMA_GAP = 28
TYPE_LUMA = 190
AA_LUMA = 130
AA_WARMTH = 16


def warmth(pixel: tuple[int, int, int]) -> int:
    return pixel[0] - pixel[2]


def is_ivory_type(pixel: tuple[int, int, int]) -> bool:
    r, g, b = pixel
    return _luma(pixel) >= TYPE_LUMA and r >= 200 and warmth(pixel) >= 18


def is_type_or_aa(pixel: tuple[int, int, int]) -> bool:
    if is_ivory_type(pixel):
        return True
    return _luma(pixel) >= AA_LUMA and warmth(pixel) >= AA_WARMTH


def classify_pixel(pixel: tuple[int, int, int]) -> str:
    lum = _luma(pixel)
    if lum < 85:
        return "curtain"
    if lum >= 140 and warmth(pixel) < 18:
        return "wall"
    return "ceiling"


def inpaint_from_boundary(parent: Image.Image, hole: Image.Image) -> Image.Image:
    """Reconstruct glyph strokes from ORIGINAL nearby surfaces only.

    Type and its antialiasing are never used as samples. Dark curtain columns
    are filled vertically so slats continue; ceiling/wall use a local mean.
    """
    src = parent.convert("RGB")
    out = src.copy()
    sp, px = src.load(), out.load()
    w, h = out.size
    box = hole.getbbox()
    if box is None:
        return out
    x0, y0, x1, y1 = box
    work = hole.convert("L").copy()
    ml = work.load()

    def usable(xx: int, yy: int) -> bool:
        if not (0 <= xx < w and 0 <= yy < h):
            return False
        if ml[xx, yy] >= 128:
            return False
        return not is_type_or_aa(sp[xx, yy])

    for x in range(x0, x1):
        y = y0
        while y < y1:
            if ml[x, y] < 128:
                y += 1
                continue
            y_a = y
            while y < y1 and ml[x, y] >= 128:
                y += 1
            y_b = y
            above = y_a - 1
            below = y_b
            while above >= 0 and not usable(x, above):
                above -= 1
            while below < h and not usable(x, below):
                below += 1
            if above < 0 or below >= h:
                continue
            if classify_pixel(sp[x, above]) != "curtain" or classify_pixel(sp[x, below]) != "curtain":
                continue
            a = sp[x, above]
            bcol = sp[x, below]
            span = max(below - above, 1)
            for yy in range(y_a, y_b):
                t = (yy - above) / span
                px[x, yy] = (
                    int(a[0] * (1 - t) + bcol[0] * t),
                    int(a[1] * (1 - t) + bcol[1] * t),
                    int(a[2] * (1 - t) + bcol[2] * t),
                )
                ml[x, yy] = 0

    radius = 16

    for y in range(y0, y1):
        for x in range(x0, x1):
            if ml[x, y] < 128:
                continue
            buckets = {"curtain": [0.0, 0.0, 0.0, 0.0], "wall": [0.0, 0.0, 0.0, 0.0], "ceiling": [0.0, 0.0, 0.0, 0.0]}
            rad = radius
            found = False
            while not found and rad <= 40:
                rr2 = rad * rad
                for yy in range(max(0, y - rad), min(h, y + rad + 1)):
                    dy = yy - y
                    for xx in range(max(0, x - rad), min(w, x + rad + 1)):
                        dx = xx - x
                        dist = dx * dx + dy * dy
                        if dist == 0 or dist > rr2 or not usable(xx, yy):
                            continue
                        wgt = 1.0 / (1.0 + dist)
                        r, g, b = sp[xx, yy]
                        bucket = buckets[classify_pixel((r, g, b))]
                        bucket[0] += r * wgt
                        bucket[1] += g * wgt
                        bucket[2] += b * wgt
                        bucket[3] += wgt
                        found = True
                rad += 8
            best = max(buckets.items(), key=lambda item: item[1][3])
            wsum = best[1][3]
            if wsum > 0:
                px[x, y] = (int(best[1][0] / wsum), int(best[1][1] / wsum), int(best[1][2] / wsum))
            else:
                sample = None
                for rad in range(1, 80):
                    for dx, dy in ((0, -rad), (0, rad), (-rad, 0), (rad, 0), (-rad, -rad), (rad, -rad), (-rad, rad), (rad, rad)):
                        if usable(x + dx, y + dy):
                            sample = sp[x + dx, y + dy]
                            break
                    if sample is not None:
                        break
                if sample is not None:
                    px[x, y] = sample
    return out


def ivory_residue_report(clean: Image.Image, hole: Image.Image) -> dict[str, Any]:
    rgb = clean.convert("RGB")
    hmask = hole.convert("L")
    px, mx = rgb.load(), hmask.load()
    leftover = 0
    n = 0
    luma_sum = 0
    for y in range(rgb.size[1]):
        for x in range(rgb.size[0]):
            if mx[x, y] < 128:
                continue
            n += 1
            pixel = px[x, y]
            luma_sum += _luma(pixel)
            if is_ivory_type(pixel):
                leftover += 1
    mean = (luma_sum / n) if n else 0.0
    return {
        "hole_pixels": n,
        "ivory_residue_pixels": leftover,
        "mean_luma_in_holes": round(mean, 2),
        "pass": leftover == 0,
    }

# Stay below WASHINGTON D.C., above %35, left of the Looking Chamber opening.
SAFE = (
    int(round(0.038 * W)),
    int(round(0.108 * H)),
    int(round((OPEN_TOP_X - 0.028) * W)),
    int(round((COMMERCIAL_TOP - 0.010) * H)),
)


def _rect_mask(size: tuple[int, int], box: tuple[int, int, int, int]) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rectangle([box[0], box[1], box[2] - 1, box[3] - 1], fill=255)
    return mask


def _stack_html(
    lines: list[str],
    *,
    size: int,
    lh: float,
    tracking: float,
    left: float,
    top: float,
    font_css: str,
    bg: str,
    color: str = INK_LIGHT,
) -> str:
    body = "<br>".join(html_lib.escape(line) for line in lines)
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8"/>
<style>
{font_css}
html,body{{margin:0;padding:0;width:{W}px;height:{H}px;overflow:hidden;background:{bg};}}
.hl{{position:absolute;left:{left * 100:.2f}%;top:{top * 100:.2f}%;margin:0;padding:0;color:{color};
  font-family:'Cormorant Garamond',serif;font-weight:500;font-size:{size}px;line-height:{lh};
  letter-spacing:{tracking}em;white-space:nowrap;}}
</style>
</head>
<body>
<p class="hl">{body}</p>
</body>
</html>
"""


def _old_html(*, font_css: str, bg: str) -> str:
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8"/>
<style>
{font_css}
html,body{{margin:0;padding:0;width:{W}px;height:{H}px;overflow:hidden;background:{bg};}}
.line1,.line2{{position:absolute;left:{HEADLINE_LEFT * 100:.1f}%;margin:0;padding:0;color:{INK_LIGHT};
  font-family:'Cormorant Garamond',serif;font-weight:500;font-size:{HEADLINE_SIZE}px;line-height:{HEADLINE_LH};
  letter-spacing:{HEADLINE_TRACKING}em;white-space:nowrap;}}
.line1{{top:{HEADLINE_TOP * 100:.1f}%;}}
.line2{{top:{LINE2_TOP * 100:.1f}%;}}
</style>
</head>
<body>
<p class="line1">ALIRKEN</p>
<p class="line2">KAZAN</p>
</body>
</html>
"""


def render_headline_layer(lines: list[str], *, size: int, lh: float, tracking: float, left: float, top: float, font_css: str, bg: str = CHROMA) -> Image.Image:
    html = _stack_html(lines, size=size, lh=lh, tracking=tracking, left=left, top=top, font_css=font_css, bg=bg)
    return render_html_to_png(html, width=W, height=H).convert("RGB")


def render_old_headline_layer(*, font_css: str, bg: str = CHROMA) -> Image.Image:
    return render_html_to_png(_old_html(font_css=font_css, bg=bg), width=W, height=H).convert("RGB")


def _fits(box: tuple[int, int, int, int], safe: tuple[int, int, int, int] = SAFE) -> bool:
    return box[0] >= safe[0] - 6 and box[1] >= safe[1] and box[2] <= safe[2] and box[3] <= safe[3]


def choose_headline_layout(font_css: str) -> dict[str, Any]:
    """Largest native stacked arrangement that stays inside the existing headline field."""
    attempts: list[dict[str, Any]] = [
        {"lines": ["ŞİMDİ", "YATIRIM", "ZAMANI"], "size": 74, "lh": 0.86, "tracking": 0.035, "left": HEADLINE_LEFT, "top": HEADLINE_TOP},
        {"lines": ["ŞİMDİ", "YATIRIM", "ZAMANI"], "size": 72, "lh": 0.88, "tracking": 0.035, "left": HEADLINE_LEFT, "top": HEADLINE_TOP},
        {"lines": ["ŞİMDİ", "YATIRIM", "ZAMANI"], "size": 68, "lh": 0.90, "tracking": 0.030, "left": HEADLINE_LEFT, "top": HEADLINE_TOP},
        {"lines": ["ŞİMDİ", "YATIRIM", "ZAMANI"], "size": 64, "lh": 0.90, "tracking": 0.028, "left": HEADLINE_LEFT, "top": HEADLINE_TOP},
        {"lines": ["ŞİMDİ", "YATIRIM ZAMANI"], "size": 62, "lh": 0.92, "tracking": 0.020, "left": HEADLINE_LEFT, "top": HEADLINE_TOP},
        {"lines": ["ŞİMDİ YATIRIM", "ZAMANI"], "size": 60, "lh": 0.92, "tracking": 0.018, "left": HEADLINE_LEFT, "top": HEADLINE_TOP},
        {"lines": ["ŞİMDİ", "YATIRIM", "ZAMANI"], "size": MIN_SIZE, "lh": 0.90, "tracking": 0.020, "left": HEADLINE_LEFT, "top": HEADLINE_TOP},
    ]
    tried: list[dict[str, Any]] = []
    for spec in attempts:
        layer = render_headline_layer(
            spec["lines"],
            size=spec["size"],
            lh=spec["lh"],
            tracking=spec["tracking"],
            left=spec["left"],
            top=spec["top"],
            font_css=font_css,
        )
        box = mask_bbox(glyph_mask(layer))
        record = {**spec, "bbox": list(box), "fits": _fits(box), "authority": spec["size"] / HEADLINE_SIZE}
        tried.append(record)
        if record["fits"] and spec["size"] >= MIN_SIZE:
            record["layer"] = layer
            record["structure"] = " / ".join(spec["lines"])
            record["tried"] = [{k: v for k, v in item.items() if k != "layer"} for item in tried]
            return record
    raise RuntimeError("new headline cannot fit inside the existing headline territory without moving other campaign elements")


def turkish_glyph_report(font_css: str) -> dict[str, Any]:
    """Ş and İ must be real glyphs, not S/I fallbacks or missing-glyph boxes."""

    def _mask(text: str) -> Image.Image:
        layer = render_headline_layer([text], size=74, lh=1.0, tracking=0.0, left=0.05, top=0.12, font_css=font_css)
        return glyph_mask(layer)

    s_mask = _mask("S")
    s_cedilla = _mask("Ş")
    i_mask = _mask("I")
    i_dot = _mask("İ")
    simdi = _mask("ŞİMDİ")
    diff_s = ImageChops.difference(s_mask, s_cedilla).getbbox() is not None
    diff_i = ImageChops.difference(i_mask, i_dot).getbbox() is not None
    simdi_box = mask_bbox(simdi)
    full = _mask("ŞİMDİ YATIRIM ZAMANI")
    full_box = mask_bbox(full)
    ok = diff_s and diff_i and (simdi_box[2] - simdi_box[0]) > 80 and (full_box[2] - full_box[0]) > 160
    return {
        "S_vs_Scedilla_distinct": diff_s,
        "I_vs_Idot_distinct": diff_i,
        "simdi_bbox": list(simdi_box),
        "full_bbox": list(full_box),
        "pass": ok,
    }


def plate_html(
    *,
    bg_uri: str,
    lines: list[str],
    width: int,
    height: int,
    left_px: float,
    top_px: float,
    size: int,
    lh: float,
    tracking: float,
    font_css: str,
) -> str:
    body = "<br>".join(html_lib.escape(line) for line in lines)
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8"/>
<style>
{font_css}
html,body{{margin:0;padding:0;width:{width}px;height:{height}px;overflow:hidden;background:#000;}}
.bg{{position:absolute;left:0;top:0;width:{width}px;height:{height}px;display:block;}}
.hl{{position:absolute;left:{left_px:.3f}px;top:{top_px:.3f}px;margin:0;padding:0;color:{INK_LIGHT};
  font-family:'Cormorant Garamond',serif;font-weight:500;font-size:{size}px;line-height:{lh};
  letter-spacing:{tracking}em;white-space:nowrap;}}
</style>
</head>
<body>
<img class="bg" alt="" src="{bg_uri}"/>
<p class="hl">{body}</p>
</body>
</html>
"""


def render_plate(
    bg: Image.Image,
    lines: list[str],
    *,
    left_px: float,
    top_px: float,
    size: int,
    lh: float,
    tracking: float,
    font_css: str,
) -> Image.Image:
    tw, th = bg.size
    html = plate_html(
        bg_uri=_png_data_uri(bg),
        lines=lines,
        width=tw,
        height=th,
        left_px=left_px,
        top_px=top_px,
        size=size,
        lh=lh,
        tracking=tracking,
        font_css=font_css,
    )
    return render_html_to_png(html, width=tw, height=th).convert("RGB")


def stamp_type(clean_crop: Image.Image, plate: Image.Image) -> Image.Image:
    region = clean_crop.copy()
    rp, pp, cp = region.load(), plate.load(), clean_crop.load()
    for y in range(region.size[1]):
        for x in range(region.size[0]):
            if _luma(pp[x, y]) > _luma(cp[x, y]) + STAMP_LUMA_GAP:
                rp[x, y] = pp[x, y]
    return region


def apply_clean_headline_revision(parent: Image.Image, *, old_copy: str, new_copy: str) -> tuple[Image.Image, dict[str, Any]]:
    if parent.size != CANVAS_4X5:
        raise RuntimeError(f"locked master canvas must be {CANVAS_4X5}")
    if old_copy != "ALIRKEN KAZAN" or new_copy != "ŞİMDİ YATIRIM ZAMANI":
        raise RuntimeError("Phase 10.1 contract is ALIRKEN KAZAN → ŞİMDİ YATIRIM ZAMANI")
    registry = build_font_registry()
    font_css = font_face_css(registry)
    glyphs = turkish_glyph_report(font_css)
    if not glyphs["pass"]:
        raise RuntimeError("Turkish glyphs Ş/İ did not rasterize as distinct campaign type")

    old_layer = render_old_headline_layer(font_css=font_css)
    old_mask = glyph_mask(old_layer)
    old_box = mask_bbox(old_mask)
    pad = 8
    window = (
        max(SAFE[0], old_box[0] - pad),
        max(SAFE[1], old_box[1] - pad),
        min(SAFE[2], old_box[2] + pad),
        min(SAFE[3], old_box[3] + pad),
    )
    aligned = align_mask_to_parent(parent, old_mask, window, max_shift=6)
    hole = dilate_mask(aligned, 6)
    aa = Image.new("L", parent.size, 0)
    ap, pp = aa.load(), parent.convert("RGB").load()
    near = dilate_mask(aligned, 14)
    nm = near.load()
    for y in range(window[1], window[3]):
        for x in range(window[0], window[2]):
            if nm[x, y] >= 128 and is_type_or_aa(pp[x, y]):
                ap[x, y] = 255
    hole = ImageChops.lighter(hole, aa)
    hole = ImageChops.multiply(hole, _rect_mask(parent.size, window))

    layout = choose_headline_layout(font_css)
    new_box = tuple(layout["bbox"])
    territory = (
        min(window[0], new_box[0] - 4, old_box[0] - 4),
        min(window[1], new_box[1] - 4, old_box[1] - 4),
        max(window[2], new_box[2] + 4, old_box[2] + 4),
        max(window[3], new_box[3] + 4, old_box[3] + 4),
    )
    territory = (
        max(SAFE[0], territory[0]),
        max(SAFE[1], territory[1]),
        min(SAFE[2], territory[2]),
        min(SAFE[3], territory[3]),
    )
    if not _fits(tuple(layout["bbox"])):
        raise RuntimeError("chosen headline layout escaped the headline territory")

    hole = ImageChops.multiply(hole, _rect_mask(parent.size, territory))
    clean_full = inpaint_from_boundary(parent, hole)
    residue = ivory_residue_report(clean_full, hole)
    if not residue["pass"]:
        hole = ImageChops.multiply(dilate_mask(hole, 7), _rect_mask(parent.size, territory))
        clean_full = inpaint_from_boundary(parent, hole)
        residue = ivory_residue_report(clean_full, hole)

    original_crop = parent.crop(territory)
    clean_crop = clean_full.crop(territory)
    left_px = HEADLINE_LEFT * W - territory[0]
    top_px = layout["top"] * H - territory[1]
    plate = render_plate(
        clean_crop,
        layout["lines"],
        left_px=left_px,
        top_px=top_px,
        size=layout["size"],
        lh=layout["lh"],
        tracking=layout["tracking"],
        font_css=font_css,
    )
    stamped = stamp_type(clean_crop, plate)
    child = parent.copy()
    # Reconstruct only the headline territory from the clean plate + new type.
    child.paste(clean_full.crop(territory), (territory[0], territory[1]))
    child.paste(stamped, (territory[0], territory[1]))
    delta = pixel_delta_outside(parent, child, territory)
    layout_public = {k: v for k, v in layout.items() if k not in {"layer", "tried"}}
    layout_public["tried"] = layout.get("tried")
    meta = {
        "old_copy": old_copy,
        "new_copy": new_copy,
        "method": "inpaint_old_headline_then_chromium_type_on_clean_plate",
        "territory": list(territory),
        "safe_box": list(SAFE),
        "old_glyph_bbox": list(old_box),
        "new_glyph_bbox": list(new_box),
        "layout": layout_public,
        "turkish_glyphs": glyphs,
        "residue": residue,
        "pixel_delta": delta,
        "font_family": "Cormorant Garamond",
        "gpt_image_calls": 0,
        "source": "LOCKED_MASTER_03",
        "layout_adjusted": layout["size"] != HEADLINE_SIZE or layout["lines"] != ["ŞİMDİ", "YATIRIM", "ZAMANI"],
    }
    meta["extras"] = {
        "original_crop": original_crop,
        "clean_full": clean_full,
        "clean_crop": clean_crop,
        "new_plate": plate,
        "hole": hole,
    }
    return child, meta


def render_labeled_crop(image: Image.Image, title: str, size: tuple[int, int] = (1088, 1360)) -> Image.Image:
    canvas = Image.new("RGB", size, (14, 12, 10))
    draw = ImageDraw.Draw(canvas)
    draw.text((48, 36), title, font=_font(22), fill=GOLD)
    tile = image.copy()
    tile.thumbnail((992, 1180), Image.Resampling.NEAREST)
    canvas.paste(tile.convert("RGB"), (48, 90))
    return canvas


def render_25_preview(child: Image.Image) -> Image.Image:
    small = child.resize((W // 4, H // 4), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (1088, 1360), (14, 12, 10))
    draw = ImageDraw.Draw(canvas)
    draw.text((48, 36), "08  25% LEGIBILITY  —  ŞİMDİ YATIRIM ZAMANI", font=_font(20), fill=GOLD)
    x = (1088 - small.size[0]) // 2
    y = (1360 - small.size[1]) // 2
    canvas.paste(small.convert("RGB"), (x, y))
    draw.text((x, y + small.size[1] + 24), "272 × 340   (25% of 1088 × 1360)", font=_font(16), fill=IVORY)
    return canvas


def render_parent_vs_child(parent: Image.Image, child: Image.Image) -> Image.Image:
    return render_pair(parent, child, "PARENT  LOCKED  ALIRKEN KAZAN", "CHILD  DRAFT  ŞİMDİ YATIRIM ZAMANI", "06  PARENT vs CHILD")


def render_review_board(parent: Image.Image, child: Image.Image, preview: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 980), (14, 12, 10))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 16), "09  HUMAN REVIEW BOARD  —  HEADLINE_ONLY  DRAFT", font=_font(18), fill=GOLD)
    x = 36
    for label, image in (("LOCKED MASTER", parent), ("COPY REVISION CHILD", child), ("25% LEGIBILITY", preview)):
        tile = image.copy()
        tile.thumbnail((580, 840), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 920), label, font=_font(16), fill=IVORY)
        x += 620
    return canvas
