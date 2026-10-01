"""Phase 10.0 — targeted PRICE_ONLY raster surgery on a locked Master.

Parent pixels are the source of truth. Only the price glyph territory is redrawn.
No generative image model. No full-master reconstruction.
"""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.phase5_creative_quality import _font
from investhome_api.services.creative_director.phase5_design_scene import font_face_css, render_html_to_png
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase9_0_compose import render_pair
from investhome_api.services.creative_director.phase9_1_r1_compose import INK_LIGHT, W, H
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY

CHROMA = "#00FF00"
CHROMA_RGB = (0, 255, 0)
PRICE_LEFT = 0.048
PRICE_TOP = 0.332
PRICE_SIZE_PX = 24
PRICE_TRACKING = 0.06
SEARCH = (0.040, 0.328, 0.22, 0.358)  # left, top, right, bottom — price line only, before CTA/unit
INK = tuple(int(INK_LIGHT.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))


def _luma(pixel: tuple[int, int, int]) -> int:
    return (299 * pixel[0] + 587 * pixel[1] + 114 * pixel[2]) // 1000


def _is_chroma(pixel: tuple[int, int, int]) -> bool:
    r, g, b = pixel
    return g >= 180 and g > r + 50 and g > b + 50


def price_layer_html(text: str, *, font_css: str, bg: str) -> str:
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8"/>
<style>
{font_css}
html,body{{margin:0;padding:0;width:{W}px;height:{H}px;overflow:hidden;background:{bg};}}
.price{{position:absolute;left:{PRICE_LEFT * 100:.1f}%;top:{PRICE_TOP * 100:.1f}%;margin:0;color:{INK_LIGHT};
  font-family:'Cormorant Garamond',serif;font-size:{PRICE_SIZE_PX}px;font-weight:500;letter-spacing:{PRICE_TRACKING}em;white-space:nowrap;}}
</style>
</head>
<body>
<p class="price">{text}</p>
</body>
</html>
"""


def render_price_layer(text: str, *, font_css: str, bg: str = CHROMA) -> Image.Image:
    return render_html_to_png(price_layer_html(text, font_css=font_css, bg=bg), width=W, height=H).convert("RGB")


def glyph_mask(layer: Image.Image) -> Image.Image:
    mask = Image.new("L", layer.size, 0)
    src = layer.load()
    dst = mask.load()
    for y in range(layer.size[1]):
        for x in range(layer.size[0]):
            if not _is_chroma(src[x, y]):
                dst[x, y] = 255
    return mask.filter(ImageFilter.MaxFilter(3))


def mask_bbox(mask: Image.Image) -> tuple[int, int, int, int]:
    box = mask.getbbox()
    if box is None:
        raise RuntimeError("price glyphs were not rasterized")
    return box


def search_window(size: tuple[int, int] = CANVAS_4X5) -> tuple[int, int, int, int]:
    w, h = size
    return (
        int(round(SEARCH[0] * w)),
        int(round(SEARCH[1] * h)),
        int(round(SEARCH[2] * w)),
        int(round(SEARCH[3] * h)),
    )


def locate_price_on_parent(parent: Image.Image, glyph_width: int) -> tuple[int, int, int, int]:
    """Bright-ivory cluster inside the locked price window, clipped to glyph width."""
    rgb = parent.convert("RGB")
    x0, y0, x1, y1 = search_window(rgb.size)
    px = rgb.load()
    xs: list[int] = []
    ys: list[int] = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            if _luma(px[x, y]) >= 118:
                xs.append(x)
                ys.append(y)
    if not xs:
        raise RuntimeError("could not locate price territory on the locked master")
    found = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)
    gw = max(8, int(glyph_width))
    # Split unit off: keep left cluster matching the price-only glyph width, plus 6px pad.
    right = min(found[2], found[0] + gw + 8)
    # Prefer a gap before 2+1 if present.
    col_counts = []
    for x in range(found[0], found[2]):
        n = 0
        for y in range(found[1], found[3]):
            if _luma(px[x, y]) >= 118:
                n += 1
        col_counts.append((x, n))
    gap = next((x for x, n in col_counts if n <= 1 and x > found[0] + int(gw * 0.55)), None)
    if gap is not None:
        right = min(right, gap)
    return (found[0], found[1], max(found[0] + 8, right), found[3])


def inpaint_mask(canvas: Image.Image, mask: Image.Image) -> Image.Image:
    out = canvas.convert("RGB").copy()
    src = out.load()
    m = mask.convert("L").load()
    w, h = out.size
    for y in range(h):
        for x in range(w):
            if m[x, y] < 128:
                continue
            sample = None
            for k in range(1, 48):
                xl = x - k
                xr = x + k
                if xl >= 0 and m[xl, y] < 128:
                    sample = src[xl, y]
                    break
                if xr < w and m[xr, y] < 128:
                    sample = src[xr, y]
                    break
            if sample is None:
                yu = max(0, y - 1)
                sample = src[x, yu]
            src[x, y] = sample
    return out


def composite_glyphs(base: Image.Image, layer: Image.Image, mask: Image.Image) -> Image.Image:
    out = base.convert("RGB").copy()
    bp = out.load()
    lp = layer.load()
    mp = mask.convert("L").load()
    w, h = out.size
    for y in range(h):
        for x in range(w):
            cover = mp[x, y]
            if cover < 8:
                continue
            r, g, b = lp[x, y]
            if _is_chroma((r, g, b)):
                continue
            if cover >= 240:
                bp[x, y] = (r, g, b)
                continue
            t = cover / 255.0
            pr, pg, pb = bp[x, y]
            bp[x, y] = (
                int(pr * (1 - t) + r * t),
                int(pg * (1 - t) + g * t),
                int(pb * (1 - t) + b * t),
            )
    return out


def pixel_delta_outside(parent: Image.Image, child: Image.Image, box: tuple[int, int, int, int]) -> dict[str, Any]:
    a = parent.convert("RGB")
    b = child.convert("RGB")
    if a.size != b.size:
        raise RuntimeError("parent/child canvas mismatch")
    pa, pb = a.load(), b.load()
    w, h = a.size
    x0, y0, x1, y1 = box
    outside = 0
    inside = 0
    max_out = 0
    changed: list[tuple[int, int]] = []
    for y in range(h):
        for x in range(w):
            d = max(abs(pa[x, y][i] - pb[x, y][i]) for i in range(3))
            if not d:
                continue
            if x0 <= x < x1 and y0 <= y < y1:
                inside += 1
            else:
                outside += 1
                max_out = max(max_out, d)
                if len(changed) < 12:
                    changed.append((x, y))
    return {
        "outside_changed_pixels": outside,
        "inside_changed_pixels": inside,
        "outside_max_channel_delta": max_out,
        "outside_sample": changed,
        "territory": list(box),
        "pass": outside == 0 and max_out == 0,
    }


def apply_price_only(
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
    old_mask = glyph_mask(old_layer)
    new_mask = glyph_mask(new_layer)
    old_box = mask_bbox(old_mask)
    new_box = mask_bbox(new_mask)
    pad = 3
    territory = (
        min(old_box[0], new_box[0]) - pad,
        min(old_box[1], new_box[1]) - pad,
        max(old_box[2], new_box[2]) + pad,
        max(old_box[3], new_box[3]) + pad,
    )
    window = search_window(parent.size)
    territory = (
        max(window[0], territory[0]),
        max(window[1], territory[1]),
        min(window[2], territory[2]),
        min(window[3], territory[3]),
    )
    located = list(old_box)
    dx = 0
    dy = 0
    erase = Image.new("L", parent.size, 0)
    erase.paste(old_mask)
    clip = Image.new("L", parent.size, 0)
    ImageDraw.Draw(clip).rectangle(
        [territory[0], territory[1], territory[2] - 1, territory[3] - 1],
        fill=255,
    )
    erase = ImageChops.multiply(erase, clip)
    new_mask = ImageChops.multiply(new_mask, clip)
    cleaned = inpaint_mask(parent, erase)
    child = composite_glyphs(cleaned, new_layer, new_mask)
    delta = pixel_delta_outside(parent, child, territory)
    meta = {
        "old_value": old_value,
        "new_value": new_value,
        "css": {"left": PRICE_LEFT, "top": PRICE_TOP, "size_px": PRICE_SIZE_PX, "tracking_em": PRICE_TRACKING},
        "located": list(located),
        "old_glyph_bbox": list(old_box),
        "new_glyph_bbox": list(new_box),
        "territory": list(territory),
        "offset": [dx, dy],
        "layout_adjusted": False,
        "method": "parent_raster_copy + chroma_glyph_replace",
        "pixel_delta": delta,
        "font_family": "Cormorant Garamond",
        "gpt_image_calls": 0,
    }
    return child, meta


def render_territory(parent: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    canvas = parent.convert("RGB").copy()
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([box[0], box[1], box[2] - 1, box[3] - 1], outline=(232, 196, 120), width=2)
    return canvas


def render_pixel_diff(parent: Image.Image, child: Image.Image) -> Image.Image:
    a = parent.convert("RGB")
    b = child.convert("RGB")
    out = Image.new("RGB", a.size, (10, 10, 12))
    pa, pb, po = a.load(), b.load(), out.load()
    w, h = a.size
    for y in range(h):
        for x in range(w):
            d = max(abs(pa[x, y][i] - pb[x, y][i]) for i in range(3))
            if d:
                po[x, y] = (220, 48, 40)
            else:
                r, g, bl = pa[x, y]
                po[x, y] = (r // 6, g // 6, bl // 6)
    return out


def render_parse_board(parsed: dict[str, Any]) -> Image.Image:
    canvas = Image.new("RGB", (1088, 1360), (14, 12, 10))
    draw = ImageDraw.Draw(canvas)
    draw.text((48, 48), "02  NATURAL-LANGUAGE PARSE", font=_font(22), fill=GOLD)
    rows = [
        f"USER  {parsed.get('user_command')}",
        f"REVISION TYPE  {parsed.get('revision_type')}",
        f"OLD VALUE  {parsed.get('old_value')}",
        f"NEW VALUE  {parsed.get('new_value')}",
        f"PRESERVE EVERYTHING ELSE  {parsed.get('preserve_everything_else')}",
        f"PARSE  {'PASS' if parsed.get('pass') else 'FAIL'}",
        f"ROUTER INTENT  {parsed.get('router_intent')}",
        "No technical command was required.",
    ]
    y = 140
    for row in rows:
        draw.text((48, y), row[:78], font=_font(18), fill=IVORY)
        y += 48
    return canvas


def render_validation_board(rows: list[str]) -> Image.Image:
    canvas = Image.new("RGB", (1088, 1360), (14, 12, 10))
    draw = ImageDraw.Draw(canvas)
    draw.text((48, 48), "07  REVISION VALIDATION", font=_font(22), fill=GOLD)
    y = 130
    for row in rows:
        draw.text((48, y), row[:78], font=_font(18), fill=IVORY)
        y += 42
    return canvas


def render_review_board(parent: Image.Image, child: Image.Image, diff: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 980), (14, 12, 10))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 16), "08  HUMAN REVIEW BOARD  —  PRICE_ONLY CHILD  DRAFT", font=_font(18), fill=GOLD)
    x = 36
    for label, image in (("PARENT  LOCKED", parent), ("CHILD  750.000 USD", child), ("PIXEL DIFF", diff)):
        tile = image.copy()
        tile.thumbnail((580, 840), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 920), label, font=_font(16), fill=IVORY)
        x += 620
    return canvas


def render_parent_child(parent: Image.Image, child: Image.Image) -> Image.Image:
    return render_pair(parent, child, "PARENT  675.000 USD  LOCKED", "CHILD  750.000 USD  DRAFT", "05  PARENT vs CHILD")
