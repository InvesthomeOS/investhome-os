"""PRICE_BLOCK_ONLY revision — parse NL and locally edit the price zone.

Never regenerates the full finished_ad. Baked prices are patched only inside
the detected price bbox; unmentioned pixels must stay identical.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import Any

from fastapi import HTTPException, status

from investhome_api.schemas.creative_director import RevisionOperation


_AMOUNT_RE = re.compile(
    r"(\d{1,3}(?:[.\s]\d{3})+|\d{3,})(?:\s*(?:USD|\$))?",
    re.IGNORECASE,
)
_GOLD = (196, 163, 90)
_WHITE = (245, 241, 234)
_LABEL = (232, 224, 210)


def _normalize_tr(text: str) -> str:
    return (text or "").replace("İ", "i").replace("I", "ı").lower()


def format_tr_usd(amount: int) -> str:
    raw = f"{amount:,}".replace(",", ".")
    return f"{raw} USD"


def parse_tr_amount(token: str) -> int | None:
    digits = re.sub(r"[^\d]", "", token or "")
    if not digits:
        return None
    try:
        value = int(digits)
    except ValueError:
        return None
    if value < 1000 or value > 99_999_999:
        return None
    return value


@dataclass
class PriceBlockIntent:
    list_amount: int
    launch_amount: int
    savings_amount: int
    list_strikethrough: bool = True
    list_label: str = "LİSTE FİYATI"
    launch_label: str = "LANSMAN FİYATI"
    savings_label: str = "KAZANCINIZ"
    scope: str = "PRICE_BLOCK_ONLY"
    raw_amounts: list[int] = field(default_factory=list)

    def operations(self) -> list[RevisionOperation]:
        ops = [
            RevisionOperation(
                target="price",
                action="replace_text",
                element_id="old-price",
                **{"from": None, "to": format_tr_usd(self.list_amount)},
                note="strikethrough list price",
                priority="exact_numeric",
                semantic_target="old_price",
            ),
            RevisionOperation(
                target="price",
                action="replace_text",
                element_id="new-price",
                **{"to": format_tr_usd(self.launch_amount)},
                note="launch price",
                priority="exact_numeric",
                semantic_target="new_price",
            ),
            RevisionOperation(
                target="price",
                action="replace_text",
                element_id="savings-price",
                **{"to": format_tr_usd(self.savings_amount)},
                note="savings under launch price",
                priority="exact_numeric",
                semantic_target="price",
            ),
        ]
        return ops

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "old_price": format_tr_usd(self.list_amount),
            "old_price_strikethrough": self.list_strikethrough,
            "new_price": format_tr_usd(self.launch_amount),
            "new_price_label": self.launch_label,
            "savings": format_tr_usd(self.savings_amount),
            "savings_label": self.savings_label,
            "list_label": self.list_label,
        }


def parse_price_block(instruction: str) -> PriceBlockIntent | None:
    """Semantic price-block intent from natural Turkish. None if not this command."""
    raw = instruction or ""
    low = _normalize_tr(raw)
    if not any(tok in low for tok in ("fiyat", "usd", "lansman", "kazanc")):
        return None
    if not any(tok in low for tok in ("üzerini çiz", "ustunu ciz", "üstü çiz", "strikethrough", "liste")):
        if "lansman fiyat" not in low and "kazanc" not in low:
            return None
    amounts: list[int] = []
    for match in _AMOUNT_RE.finditer(raw):
        value = parse_tr_amount(match.group(1))
        if value is not None and value not in amounts:
            amounts.append(value)
    if len(amounts) < 2:
        return None
    list_amount = amounts[0]
    launch_amount = amounts[1]
    savings_amount = amounts[2] if len(amounts) >= 3 else max(0, list_amount - launch_amount)
    strikethrough = any(
        tok in low
        for tok in ("üzerini çiz", "ustunu ciz", "üstü çiz", "ustu ciz", "strikethrough", "çiz")
    )
    return PriceBlockIntent(
        list_amount=list_amount,
        launch_amount=launch_amount,
        savings_amount=savings_amount,
        list_strikethrough=strikethrough or True,
        raw_amounts=amounts,
    )


def is_baked_price_ad(ctx: dict[str, Any] | None) -> bool:
    """Finished-ad raster is the visual source — price glyphs live in pixels."""
    ctx = ctx or {}
    if ctx.get("revision_engine_v2") is True or ctx.get("visual_foundation_asset_id"):
        return False
    if ctx.get("golden_native_v1") is True:
        return False
    mode = str(ctx.get("production_mode") or "")
    if mode in {"golden_native_v1", "editable_finished_ad"}:
        spec = ctx.get("design_spec") if isinstance(ctx.get("design_spec"), dict) else {}
        ids = {
            str(el.get("id") or "").lower()
            for el in (spec.get("elements") or [])
            if isinstance(el, dict)
        }
        if spec.get("revision_engine_v2") is True:
            return False
        if "old-price" in ids and "new-price" in ids:
            return False
    return True


def _load_font(size: int, *, bold: bool = False, serif: bool = False):
    from PIL import ImageFont

    if serif:
        names = (
            "DejaVuSerif-Bold.ttf" if bold else "DejaVuSerif.ttf",
            "LiberationSerif-Bold.ttf" if bold else "LiberationSerif-Regular.ttf",
            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        )
    else:
        names = (
            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
            "LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf",
        )
    roots = (
        "/usr/share/fonts/truetype/dejavu/",
        "/usr/share/fonts/truetype/liberation/",
        "/usr/share/fonts/TTF/",
    )
    for root in roots:
        for name in names:
            try:
                return ImageFont.truetype(f"{root}{name}", size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _spec_price_box(spec: dict[str, Any] | None, intent: PriceBlockIntent) -> tuple[int, int, int, int] | None:
    if not isinstance(spec, dict):
        return None
    hits: list[tuple[int, int, int, int]] = []
    needles = (
        str(intent.list_amount),
        format_tr_usd(intent.list_amount),
        "675.000",
        "liste",
        "fiyat",
    )
    for el in spec.get("elements") or []:
        if not isinstance(el, dict):
            continue
        content = str(el.get("content") or "").lower()
        eid = str(el.get("id") or "").lower()
        role = str(el.get("role") or "").lower()
        if not any(n.lower() in content or n.lower() in eid or n.lower() in role for n in needles):
            if eid not in {"old-price", "new-price", "price-frame"} and "price" not in role:
                continue
        x = int(el.get("x") or 0)
        y = int(el.get("y") or 0)
        w = int(el.get("width") or 0)
        h = int(el.get("height") or 0)
        if w > 8 and h > 8:
            hits.append((x, y, x + w, y + h))
    if not hits:
        return None
    x0 = min(b[0] for b in hits)
    y0 = min(b[1] for b in hits)
    x1 = max(b[2] for b in hits)
    y1 = max(b[3] for b in hits)
    return x0, y0, x1, y1


def _luma(r: int, g: int, b: int) -> float:
    return 0.299 * r + 0.587 * g + 0.114 * b


def _fail_closed(message: str, **extra: Any) -> None:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={"message": message, "scope": "PRICE_BLOCK_ONLY", **extra},
    )


def _bottom_dense_bbox(
    xs: list[int],
    ys: list[int],
    *,
    min_row: int,
) -> tuple[int, int, int, int] | None:
    from collections import Counter

    if len(xs) < 40:
        return None
    counts = Counter(ys)
    seeded = [y for y, count in counts.items() if count >= min_row]
    if not seeded:
        return min(xs), min(ys), max(xs) + 1, max(ys) + 1
    y_bottom = max(seeded)
    y_top = y_bottom
    y = y_bottom
    floor = max(6, min_row // 2)
    while (y - 1) in counts and counts[y - 1] >= floor and (y_bottom - (y - 1)) < 48:
        y -= 1
        y_top = y
    band_x = [x for x, yy in zip(xs, ys, strict=True) if y_top <= yy <= y_bottom]
    if len(band_x) < 30:
        return min(xs), min(ys), max(xs) + 1, max(ys) + 1
    band_y = [yy for yy in ys if y_top <= yy <= y_bottom]
    return min(band_x), min(band_y), max(band_x) + 1, max(band_y) + 1


def _union_box(
    a: tuple[int, int, int, int],
    b: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    return min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])


def _pad_box(
    box: tuple[int, int, int, int],
    *,
    pad: int,
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box
    return (
        max(0, x0 - pad),
        max(0, y0 - pad),
        min(width, x1 + pad),
        min(height, y1 + pad),
    )


def _scan_white_glyphs(
    image: Any,
    search: tuple[int, int, int, int],
    *,
    min_row: int,
) -> tuple[int, int, int, int] | None:
    rgb = image.convert("RGB")
    pixels = rgb.load()
    sx0, sy0, sx1, sy1 = search
    white_x: list[int] = []
    white_y: list[int] = []
    for y in range(sy0, sy1):
        for x in range(sx0, sx1):
            r, g, b = pixels[x, y]
            if _is_gold(r, g, b):
                continue
            if _luma(r, g, b) < 220:
                continue
            white_x.append(x)
            white_y.append(y)
    return _bottom_dense_bbox(white_x, white_y, min_row=min_row)


def _photo_start_y(image: Any, *, from_y: int) -> int:
    """First row that looks like photography rather than navy overlay."""
    rgb = image.convert("RGB")
    pixels = rgb.load()
    width, height = rgb.size
    x0, x1 = int(width * 0.20), int(width * 0.80)
    span = max(1, x1 - x0)
    start = max(from_y + 16, int(height * 0.36))
    consecutive = 0
    first: int | None = None
    for y in range(start, int(height * 0.70)):
        mid = 0
        for x in range(x0, x1):
            r, g, b = pixels[x, y]
            luma = _luma(r, g, b)
            if 50 <= luma < 200 and not _is_gold(r, g, b):
                mid += 1
        if mid > 0.45 * span:
            consecutive += 1
            if first is None:
                first = y
            if consecutive >= 6:
                return first
        else:
            consecutive = 0
            first = None
    return int(height * 0.42)


def _navy_gap_below(
    image: Any,
    glyph: tuple[int, int, int, int],
    photo_y: int,
) -> tuple[int, int] | None:
    """Rows of navy immediately below the list-price numerals, before USD/photo."""
    rgb = image.convert("RGB")
    pixels = rgb.load()
    width, _height = rgb.size
    gx0, _gy0, gx1, gy1 = glyph
    x0 = max(0, gx0 - 8)
    x1 = min(width, gx1 + 8)
    span = max(1, x1 - x0)
    y0 = gy1 + 4
    y1 = y0
    for y in range(y0, min(photo_y - 4, gy1 + 48)):
        dark = 0
        for x in range(x0, x1):
            r, g, b = pixels[x, y]
            if _is_gold(r, g, b):
                continue
            if _luma(r, g, b) < 45:
                dark += 1
        if dark < 0.70 * span:
            break
        y1 = y + 1
    if y1 - y0 < 16:
        return None
    return y0, y1


def locate_overlay_list_price(
    image: Any,
) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int], tuple[int, int, int, int]] | None:
    """List price in the upper stats band (AI-first overlay), not the bottom furniture zone."""
    from PIL import Image

    assert isinstance(image, Image.Image)
    width, height = image.size
    search = (
        int(width * 0.38),
        int(height * 0.26),
        int(width * 0.62),
        int(height * 0.34),
    )
    glyph = _scan_white_glyphs(image, search, min_row=18)
    if glyph is None:
        return None
    gx0, gy0, gx1, gy1 = glyph
    if gy0 > int(height * 0.45) or gy1 > int(height * 0.48):
        return None
    photo_y = _photo_start_y(image, from_y=gy1)
    gap = _navy_gap_below(image, glyph, photo_y)
    if gap is None:
        return None
    add_y0, add_y1 = gap
    if add_y1 > photo_y - 2:
        return None
    strike = _pad_box(glyph, pad=3, width=width, height=height)
    cx = (gx0 + gx1) // 2
    draw_w = min(int(width * 0.42), max(gx1 - gx0 + 24, int(width * 0.28)))
    add = (
        max(int(width * 0.30), cx - draw_w // 2),
        add_y0,
        min(int(width * 0.70), cx + draw_w // 2),
        add_y1,
    )
    draw = _union_box(strike, add)
    if draw[3] > photo_y - 2:
        return None
    if (draw[2] - draw[0]) * (draw[3] - draw[1]) > 0.12 * width * height:
        return None
    return draw, strike, glyph


def locate_price_zone(
    image: Any,
    *,
    spec: dict[str, Any] | None,
    intent: PriceBlockIntent,
) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int], tuple[int, int, int, int]]:
    """Return (draw_box, cleanup_box, glyph_box).

    Cleanup is the old baked 675.000 USD glyphs only. Draw is where new type may land.
    design_spec geometry is never used — it inflates the inpaint rectangle.
    """
    from PIL import Image

    del spec, intent
    assert isinstance(image, Image.Image)
    width, height = image.size
    rgb = image.convert("RGB")
    pixels = rgb.load()
    search = (
        int(width * 0.28),
        int(height * 0.86),
        int(width * 0.64),
        int(height * 0.995),
    )
    sx0, sy0, sx1, sy1 = search
    glyph = _scan_white_glyphs(image, search, min_row=12)
    if glyph is None:
        _fail_closed("PRICE_BLOCK_ONLY fail-closed — baked list price glyphs not found.")

    gx0, gy0, gx1, gy1 = glyph
    for y in range(gy1, min(sy1, gy1 + 18)):
        row_hits = 0
        for x in range(gx0, gx1):
            r, g, b = pixels[x, y]
            if _luma(r, g, b) >= 185 and not _is_gold(r, g, b):
                row_hits += 1
        if row_hits < 4:
            break
        gy1 = y + 1
    glyph = (gx0, gy0, gx1, gy1)

    lx0, ly0, lx1, ly1 = glyph
    label_y0 = max(sy0, ly0 - max(18, int(height * 0.038)))
    label_x: list[int] = []
    label_y: list[int] = []
    for y in range(label_y0, ly0):
        for x in range(max(sx0, lx0 - 8), min(sx1, lx1 + 8)):
            r, g, b = pixels[x, y]
            luma = _luma(r, g, b)
            if _is_gold(r, g, b) or luma >= 168:
                label_x.append(x)
                label_y.append(y)
    if len(label_x) >= 25:
        label_box = (min(label_x), min(label_y), max(label_x) + 1, max(label_y) + 1)
        if (label_box[3] - label_box[1]) <= 36:
            glyph = _union_box(glyph, label_box)

    cleanup = _pad_box(glyph, pad=5, width=width, height=height)
    cleanup = (
        cleanup[0],
        cleanup[1],
        cleanup[2],
        min(height, cleanup[3] + 8),
    )
    cw, ch = cleanup[2] - cleanup[0], cleanup[3] - cleanup[1]
    if cw * ch > 0.07 * width * height or ch > 0.12 * height or cw > 0.45 * width:
        _fail_closed(
            "PRICE_BLOCK_ONLY fail-closed — cleanup box too large to edit safely.",
            cleanup={"x0": cleanup[0], "y0": cleanup[1], "x1": cleanup[2], "y1": cleanup[3]},
        )

    cx = (cleanup[0] + cleanup[2]) // 2
    draw_w = min(int(width * 0.36), max(cw + 28, int(width * 0.26)))
    draw_h = min(int(height * 0.20), max(int(height * 0.175), ch + int(height * 0.12)))
    draw_x0 = max(int(width * 0.27), cx - draw_w // 2)
    draw_x1 = min(int(width * 0.73), cx + draw_w // 2)
    draw_y1 = min(height - 1, cleanup[3] + 4)
    draw_y0 = max(int(height * 0.74), draw_y1 - draw_h)
    draw_x0 = min(draw_x0, cleanup[0])
    draw_x1 = max(draw_x1, cleanup[2])
    draw_y0 = min(draw_y0, cleanup[1])
    draw_y1 = max(draw_y1, cleanup[3])
    draw = (draw_x0, draw_y0, draw_x1, draw_y1)
    dw, dh = draw[2] - draw[0], draw[3] - draw[1]
    if dw * dh > 0.18 * width * height:
        _fail_closed(
            "PRICE_BLOCK_ONLY fail-closed — draw box too large to edit safely.",
            zone={"x0": draw[0], "y0": draw[1], "x1": draw[2], "y1": draw[3]},
        )
    return draw, cleanup, glyph


def _is_gold(r: int, g: int, b: int) -> bool:
    return r > 180 and g > 140 and b < 140


def _build_glyph_mask(
    image: Any,
    cleanup: tuple[int, int, int, int],
) -> set[tuple[int, int]]:
    """Bright / gold type pixels inside the cleanup box, dilated 2px — not the furniture."""
    x0, y0, x1, y1 = cleanup
    rgb = image.convert("RGB")
    pixels = rgb.load()
    hits: set[tuple[int, int]] = set()
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b = pixels[x, y]
            luma = _luma(r, g, b)
            if _is_gold(r, g, b) and luma >= 130:
                hits.add((x, y))
            elif luma >= 205:
                hits.add((x, y))
    mask: set[tuple[int, int]] = set()
    for x, y in hits:
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                xx, yy = x + dx, y + dy
                if x0 <= xx < x1 and y0 <= yy < y1:
                    mask.add((xx, yy))
    if len(mask) < 40:
        _fail_closed("PRICE_BLOCK_ONLY fail-closed — baked glyph mask empty.")
    return mask


def _sample_local(original: Any, mask: set[tuple[int, int]], x: int, y: int):
    """Copy a nearby original non-glyph pixel. Prefer same-row to keep wood/ottoman grain."""
    px = original.load()
    width, height = original.size
    for radius in (1, 2, 3, 5, 8, 12):
        for dx in (radius, -radius):
            xx = x + dx
            if 0 <= xx < width and (xx, y) not in mask:
                return px[xx, y][:3]
        for dy in (radius, -radius):
            yy = y + dy
            if 0 <= yy < height and (x, yy) not in mask:
                return px[x, yy][:3]
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if max(abs(dx), abs(dy)) != radius:
                    continue
                xx, yy = x + dx, y + dy
                if xx < 0 or yy < 0 or xx >= width or yy >= height:
                    continue
                if (xx, yy) in mask:
                    continue
                return px[xx, yy][:3]
    return px[x, y][:3]


def _knockout_glyph_mask(working: Any, original: Any, mask: set[tuple[int, int]]) -> None:
    """Replace only glyph pixels with local original texture — never a row lerp."""
    px = working.load()
    for x, y in mask:
        fill = _sample_local(original, mask, x, y)
        pix = px[x, y]
        if len(pix) == 4:
            px[x, y] = fill + (pix[3],)
        else:
            px[x, y] = fill


def _assert_cleanup_texture(
    original: Any,
    working: Any,
    mask: set[tuple[int, int]],
    cleanup: tuple[int, int, int, int],
) -> None:
    """Fail-closed if furniture/floor pixels moved or a smear/patch appeared."""
    orig_px = original.load()
    new_px = working.load()
    width, height = original.size
    leaked_non_glyph = 0
    leftover_bright = 0
    x0, y0, x1, y1 = cleanup
    for y in range(height):
        for x in range(width):
            if orig_px[x, y] == new_px[x, y]:
                continue
            if (x, y) not in mask:
                leaked_non_glyph += 1
    if leaked_non_glyph > 0:
        _fail_closed(
            "PRICE_BLOCK_ONLY fail-closed — cleanup changed pixels outside the glyph mask. "
            "Existing finished-ad was not persisted.",
            leaked_pixels=leaked_non_glyph,
        )
    for y in range(y0, y1):
        for x in range(x0, x1):
            if (x, y) in mask:
                continue
            r, g, b = new_px[x, y][:3]
            if _luma(r, g, b) >= 190:
                leftover_bright += 1
    if leftover_bright > 12:
        _fail_closed(
            "PRICE_BLOCK_ONLY fail-closed — baked price glyphs still visible after cleanup.",
            leftover_bright=leftover_bright,
        )
    furniture_smear_rows = 0
    n = max(1, x1 - x0)
    for y in range(y0, y1):
        dark_changed = 0
        for x in range(x0, x1):
            if orig_px[x, y] == new_px[x, y]:
                continue
            if _luma(*orig_px[x, y][:3]) < 140:
                dark_changed += 1
        if dark_changed >= 0.45 * n:
            furniture_smear_rows += 1
    if furniture_smear_rows >= 8:
        _fail_closed(
            "PRICE_BLOCK_ONLY fail-closed — horizontal smear / repair patch detected. "
            "Existing finished-ad was not persisted.",
            smear_rows=furniture_smear_rows,
        )


def _draw_price_block(image: Any, box: tuple[int, int, int, int], intent: PriceBlockIntent) -> None:
    from PIL import ImageDraw

    draw = ImageDraw.Draw(image)
    x0, y0, x1, y1 = box
    zone_w = max(8, x1 - x0)
    zone_h = max(8, y1 - y0)
    cx = (x0 + x1) // 2
    max_text_w = zone_w - 10

    def _fonts(scale: float):
        return (
            _load_font(max(12, int(zone_h * 0.068 * scale))),
            _load_font(max(16, int(zone_h * 0.118 * scale)), bold=True, serif=True),
            _load_font(max(18, int(zone_h * 0.145 * scale)), bold=True, serif=True),
            _load_font(max(16, int(zone_h * 0.118 * scale)), bold=True, serif=True),
        )

    scale = 1.0
    lines: list[tuple[str, Any, tuple[int, int, int], bool]] = []
    heights: list[int] = []
    for _ in range(8):
        label_font, list_font, launch_font, savings_font = _fonts(scale)
        lines = [
            (intent.list_label, label_font, _LABEL, False),
            (format_tr_usd(intent.list_amount), list_font, _WHITE, intent.list_strikethrough),
            (intent.launch_label, label_font, _LABEL, False),
            (format_tr_usd(intent.launch_amount), launch_font, _GOLD, False),
            (intent.savings_label, label_font, _LABEL, False),
            (format_tr_usd(intent.savings_amount), savings_font, _GOLD, False),
        ]
        heights = []
        too_wide = False
        for text, font, _color, _strike in lines:
            bbox = draw.textbbox((0, 0), text, font=font)
            heights.append(bbox[3] - bbox[1])
            if (bbox[2] - bbox[0]) > max_text_w:
                too_wide = True
        gap = max(2, int(zone_h * 0.014 * scale))
        total_h = sum(heights) + gap * (len(lines) - 1)
        if not too_wide and total_h <= zone_h - 8:
            break
        scale *= 0.88

    gap = max(2, int(zone_h * 0.014 * scale))
    total_h = sum(heights) + gap * (len(lines) - 1)
    y = y0 + max(4, (zone_h - total_h) // 2)
    for (text, font, color, strike), h in zip(lines, heights, strict=True):
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        x = max(x0 + 2, min(cx - tw // 2, x1 - tw - 2))
        draw.text((x, y), text, font=font, fill=color)
        if strike:
            ly = y + int(h * 0.55)
            x_line0 = max(x0 + 2, x - 2)
            x_line1 = min(x1 - 3, x + tw + 2)
            draw.line((x_line0, ly, x_line1, ly), fill=color, width=max(2, h // 10))
        y += h + gap


def _draw_overlay_launch_savings(
    image: Any,
    box: tuple[int, int, int, int],
    intent: PriceBlockIntent,
) -> None:
    """Compact launch + savings in the navy gap. Does not redraw the list price."""
    from PIL import ImageDraw

    draw = ImageDraw.Draw(image)
    x0, y0, x1, y1 = box
    zone_w = max(8, x1 - x0)
    zone_h = max(8, y1 - y0)
    cx = (x0 + x1) // 2
    launch = format_tr_usd(intent.launch_amount)
    savings = f"{intent.savings_label} {format_tr_usd(intent.savings_amount)}"
    if zone_h < 28:
        font = _load_font(max(11, min(16, zone_h - 4)), bold=True, serif=True)
        text = f"{launch}   {savings}"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = max(x0 + 2, min(cx - tw // 2, x1 - tw - 2))
        y = y0 + max(1, (zone_h - th) // 2)
        draw.text((x, y), text, font=font, fill=_GOLD)
        return
    scale = 1.0
    for _ in range(6):
        amount_font = _load_font(max(12, int(zone_h * 0.42 * scale)), bold=True, serif=True)
        label_font = _load_font(max(10, int(zone_h * 0.28 * scale)), bold=True)
        b1 = draw.textbbox((0, 0), launch, font=amount_font)
        b2 = draw.textbbox((0, 0), savings, font=label_font)
        total_h = (b1[3] - b1[1]) + (b2[3] - b2[1]) + 2
        too_wide = (b1[2] - b1[0]) > zone_w - 8 or (b2[2] - b2[0]) > zone_w - 8
        if not too_wide and total_h <= zone_h - 2:
            break
        scale *= 0.88
    y = y0 + 1
    for text, font in ((launch, amount_font), (savings, label_font)):
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = max(x0 + 2, min(cx - tw // 2, x1 - tw - 2))
        draw.text((x, y), text, font=font, fill=_GOLD)
        y += th + 1


def _stroke_list_price(image: Any, glyph: tuple[int, int, int, int]) -> None:
    from PIL import ImageDraw

    draw = ImageDraw.Draw(image)
    gx0, gy0, gx1, gy1 = glyph
    mid_y = gy0 + int((gy1 - gy0) * 0.55)
    width = max(2, (gy1 - gy0) // 10)
    draw.line((gx0, mid_y, gx1 - 1, mid_y), fill=_WHITE, width=width)


def _assert_hero_unchanged(original: Any, working: Any, photo_y: int) -> None:
    orig_px = original.load()
    new_px = working.load()
    width, height = original.size
    leaked = 0
    for y in range(max(0, photo_y), height):
        for x in range(width):
            if orig_px[x, y] != new_px[x, y]:
                leaked += 1
    if leaked > 0:
        _fail_closed(
            "PRICE_BLOCK_ONLY fail-closed — hero / background pixels changed. "
            "Existing finished-ad was not persisted.",
            leaked_pixels=leaked,
            photo_y=photo_y,
        )


def apply_overlay_price_edit(
    source_bytes: bytes,
    *,
    intent: PriceBlockIntent,
) -> tuple[bytes, dict[str, Any]]:
    """Strikethrough baked list price in place; add launch + savings in navy gap. GPT=0."""
    from PIL import Image

    original = Image.open(io.BytesIO(source_bytes)).convert("RGBA")
    working = original.copy()
    located = locate_overlay_list_price(working)
    if located is None:
        _fail_closed("PRICE_BLOCK_ONLY fail-closed — overlay list price glyphs not found.")
    draw_box, strike_box, glyph_box = located
    photo_y = _photo_start_y(working, from_y=glyph_box[3])
    _stroke_list_price(working, glyph_box)
    add_box = (draw_box[0], strike_box[3], draw_box[2], draw_box[3])
    if add_box[3] - add_box[1] < 16:
        _fail_closed("PRICE_BLOCK_ONLY fail-closed — no navy gap to add launch/savings.")
    _draw_overlay_launch_savings(working, add_box, intent)

    orig_px = original.load()
    new_px = working.load()
    width, height = original.size
    x0, y0, x1, y1 = draw_box
    for y in range(height):
        for x in range(width):
            if x0 <= x < x1 and y0 <= y < y1:
                continue
            if orig_px[x, y] != new_px[x, y]:
                new_px[x, y] = orig_px[x, y]
    _assert_hero_unchanged(original, working, photo_y)
    out = io.BytesIO()
    working.convert("RGB").save(out, format="PNG", optimize=True)
    trace = {
        "scope": "PRICE_BLOCK_ONLY",
        "baked": True,
        "method": "overlay_list_price_strikethrough",
        "provider_calls": 0,
        "zone": {"x0": x0, "y0": y0, "x1": x1, "y1": y1},
        "cleanup_box": {
            "x0": strike_box[0],
            "y0": strike_box[1],
            "x1": strike_box[2],
            "y1": strike_box[3],
        },
        "glyph_zone": {
            "x0": glyph_box[0],
            "y0": glyph_box[1],
            "x1": glyph_box[2],
            "y1": glyph_box[3],
        },
        "photo_y": photo_y,
        "intent": intent.to_dict(),
    }
    return out.getvalue(), trace


def apply_local_price_zone(
    source_bytes: bytes,
    *,
    spec: dict[str, Any] | None,
    intent: PriceBlockIntent,
) -> tuple[bytes, dict[str, Any]]:
    """Cleanup old glyphs only; draw new type in a separate box. Outside pixels identical."""
    from PIL import Image

    original = Image.open(io.BytesIO(source_bytes)).convert("RGBA")
    probe = original.convert("RGB")
    width, height = probe.size
    bottom_search = (
        int(width * 0.28),
        int(height * 0.86),
        int(width * 0.64),
        int(height * 0.995),
    )
    if _scan_white_glyphs(probe, bottom_search, min_row=12) is None:
        return apply_overlay_price_edit(source_bytes, intent=intent)

    working = original.copy()
    draw_box, cleanup_box, glyph_box = locate_price_zone(working, spec=spec, intent=intent)
    mask = _build_glyph_mask(working, cleanup_box)
    _knockout_glyph_mask(working, original, mask)
    _assert_cleanup_texture(original, working, mask, cleanup_box)
    x0, y0, x1, y1 = draw_box
    _draw_price_block(working, draw_box, intent)

    orig_px = original.load()
    new_px = working.load()
    width, height = original.size
    leaked = 0
    for y in range(height):
        for x in range(width):
            if x0 <= x < x1 and y0 <= y < y1:
                continue
            if orig_px[x, y] != new_px[x, y]:
                leaked += 1
    if leaked > 0:
        _fail_closed(
            "PRICE_BLOCK_ONLY fail-closed — edit leaked outside the price zone. "
            "Existing finished-ad was not persisted.",
            leaked_pixels=leaked,
        )
    out = io.BytesIO()
    working.convert("RGB").save(out, format="PNG", optimize=True)
    trace = {
        "scope": "PRICE_BLOCK_ONLY",
        "baked": True,
        "zone": {"x0": x0, "y0": y0, "x1": x1, "y1": y1},
        "cleanup_box": {
            "x0": cleanup_box[0],
            "y0": cleanup_box[1],
            "x1": cleanup_box[2],
            "y1": cleanup_box[3],
        },
        "glyph_zone": {
            "x0": glyph_box[0],
            "y0": glyph_box[1],
            "x1": glyph_box[2],
            "y1": glyph_box[3],
        },
        "glyph_mask_pixels": len(mask),
        "provider_calls": 0,
        "method": "local_price_zone_glyph_mask",
        "intent": intent.to_dict(),
    }
    return out.getvalue(), trace
