"""Phase 12.5 — native PRICE_ONLY revision by swapping original 5/7 glyphs.

357.000 → 375.000 uses each format's own raster digits. Does not invent a
price plate. Does not derive one format from another. No GPT Image.
"""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageChops, ImageDraw

OLD_DIGITS = "357"
NEW_DIGITS = "375"
OLD_VALUE = "357.000"
NEW_VALUE = "375.000"


def luma(pixel: tuple[int, int, int]) -> int:
    return (299 * pixel[0] + 587 * pixel[1] + 114 * pixel[2]) // 1000


def _bbox_where(image: Image.Image, predicate) -> tuple[int, int, int, int] | None:
    px = image.load()
    xs: list[int] = []
    ys: list[int] = []
    for y in range(image.size[1]):
        for x in range(image.size[0]):
            if predicate(px[x, y]):
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return (min(xs), min(ys), max(xs) + 1, max(ys) + 1)


def _crop(image: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    x0, y0, x1, y1 = box
    return image.crop((x0, y0, x1, y1))


def _median_color(image: Image.Image, mask: Image.Image | None = None) -> tuple[int, int, int]:
    px = image.convert("RGB").load()
    mx = mask.convert("L").load() if mask is not None else None
    rs, gs, bs = [], [], []
    for y in range(image.size[1]):
        for x in range(image.size[0]):
            if mx is not None and mx[x, y] >= 128:
                continue
            r, g, b = px[x, y]
            rs.append(r)
            gs.append(g)
            bs.append(b)
    if not rs:
        return (255, 255, 255)
    rs.sort()
    gs.sort()
    bs.sort()
    mid = len(rs) // 2
    return (rs[mid], gs[mid], bs[mid])


def _ink_mask(image: Image.Image, *, dark_on_light: bool, dark=90, light=200) -> Image.Image:
    mask = Image.new("L", image.size, 0)
    px = image.load()
    m = mask.load()
    for y in range(image.size[1]):
        for x in range(image.size[0]):
            lum = luma(px[x, y])
            if dark_on_light:
                m[x, y] = 255 if lum <= dark else 0
            else:
                m[x, y] = 255 if lum >= light else 0
    return mask


def _col_profile(mask: Image.Image) -> list[int]:
    m = mask.load()
    w, h = mask.size
    return [sum(1 for y in range(h) if m[x, y] >= 128) for x in range(w)]


def _runs(profile: list[int], min_ink: int) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    x = 0
    n = len(profile)
    while x < n:
        if profile[x] < min_ink:
            x += 1
            continue
        x0 = x
        while x < n and profile[x] >= min_ink:
            x += 1
        runs.append((x0, x))
    return runs


def _row_range(mask: Image.Image) -> tuple[int, int]:
    m = mask.load()
    w, h = mask.size
    ys = [y for y in range(h) if any(m[x, y] >= 128 for x in range(w))]
    if not ys:
        raise RuntimeError("no ink rows in PRICE territory")
    pad = 1
    return (max(0, min(ys) - pad), min(h, max(ys) + 1 + pad))


def _digits_before_period(runs: list[tuple[int, int]]) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
    if len(runs) < 5:
        raise RuntimeError(f"PRICE line did not segment into characters: {runs}")
    widths = [x1 - x0 for x0, x1 in runs]
    median_w = sorted(widths)[len(widths) // 2]
    period_idx = None
    for i, width in enumerate(widths):
        if 2 <= width <= max(4, int(median_w * 0.45)) and i >= 3:
            period_idx = i
            break
    if period_idx is None:
        period_idx = next((i for i, width in enumerate(widths) if width <= max(5, int(median_w * 0.5)) and i >= 3), None)
    if period_idx is None or period_idx < 3:
        raise RuntimeError(f"could not find thousands-separator in PRICE runs: {runs}")
    three = runs[period_idx - 3 : period_idx]
    if len(three) != 3:
        raise RuntimeError("could not isolate the three digits before the period")
    return three[0], three[1], three[2]


def _longest_bright_run(px, y: int, width: int, luma_min: int) -> tuple[int, int, int]:
    best = (0, 0, 0)
    x = 0
    while x < width:
        if luma(px[x, y]) < luma_min:
            x += 1
            continue
        x0 = x
        while x < width and luma(px[x, y]) >= luma_min:
            x += 1
        length = x - x0
        if length > best[0]:
            best = (length, x0, x)
    return best


def locate_story_price_line(image: Image.Image) -> dict[str, Any]:
    W, H = image.size
    ox, oy = int(0.08 * W), int(0.18 * H)
    x1s, y1s = int(0.92 * W), int(0.32 * H)
    search = image.crop((ox, oy, x1s, y1s))
    px = search.load()
    sw, sh = search.size
    row_bright = []
    row_x = []
    for y in range(sh):
        xs = [x for x in range(sw) if luma(px[x, y]) >= 210]
        row_bright.append(len(xs))
        row_x.append((min(xs), max(xs) + 1) if xs else (0, 0))
    thresh = int(sw * 0.28)
    y = 0
    bands: list[tuple[int, int, int, int, int]] = []
    while y < sh:
        if row_bright[y] < thresh:
            y += 1
            continue
        y0 = y
        xa, xb = row_x[y]
        while y < sh and row_bright[y] >= thresh:
            xa = min(xa, row_x[y][0])
            xb = max(xb, row_x[y][1])
            y += 1
        bands.append((y0, y, xa, xb, y - y0))
    if not bands:
        raise RuntimeError("Story PRICE plate (white bar) was not found")
    y0, y1, xa, xb, _ = max(bands, key=lambda t: t[4] * (t[3] - t[2]))
    inset_x, inset_y = 10, 4
    local = (
        ox + xa + inset_x,
        oy + y0 + inset_y,
        ox + xb - inset_x,
        oy + y1 - inset_y,
    )
    crop = _crop(image, local)
    mask = _ink_mask(crop, dark_on_light=True, dark=110)
    y_text0, y_text1 = _row_range(mask)
    line = crop.crop((0, y_text0, crop.size[0], y_text1))
    line_mask = mask.crop((0, y_text0, crop.size[0], y_text1))
    abs_line = (local[0], local[1] + y_text0, local[2], local[1] + y_text1)
    return {
        "mode": "dark_on_light",
        "plate": (ox + xa, oy + y0, ox + xb, oy + y1),
        "line": abs_line,
        "crop": line,
        "mask": line_mask,
        "origin": (abs_line[0], abs_line[1]),
    }


def locate_square_price_line(image: Image.Image) -> dict[str, Any]:
    """$357.000'dan sits on the tan card, below the %40 pill. Window is format-owned."""
    W, H = image.size
    local = (int(0.06 * W), int(0.56 * H), int(0.42 * W), int(0.68 * H))
    crop = _crop(image, local)
    mask = _ink_mask(crop, dark_on_light=False, light=230)
    w, h = crop.size
    m = mask.load()
    row_ink = [sum(1 for x in range(w) if m[x, y] >= 128) for y in range(h)]
    solid = int(w * 0.32)
    glyph_min = 20
    bands: list[tuple[int, int]] = []
    y = 0
    while y < h:
        if not (glyph_min <= row_ink[y] < solid):
            y += 1
            continue
        y0 = y
        while y < h and glyph_min <= row_ink[y] < solid:
            y += 1
        if (y - y0) >= 12:
            bands.append((y0, y))
    if not bands:
        raise RuntimeError("Square PRICE glyph band was not found under the %40 pill")
    y_text0, y_text1 = bands[0]
    pad = 2
    y_text0 = max(0, y_text0 - pad)
    y_text1 = min(h, y_text1 + pad)
    line = crop.crop((0, y_text0, w, y_text1))
    line_mask = mask.crop((0, y_text0, w, y_text1))
    abs_line = (local[0], local[1] + y_text0, local[2], local[1] + y_text1)
    return {
        "mode": "light_on_dark",
        "plate": local,
        "line": abs_line,
        "crop": line,
        "mask": line_mask,
        "origin": (abs_line[0], abs_line[1]),
    }


def segment_357(located: dict[str, Any]) -> dict[str, Any]:
    mask = located["mask"]
    profile = _col_profile(mask)
    min_ink = 2
    runs = _runs(profile, min_ink=min_ink)
    d3, d5, d7 = _digits_before_period(runs)
    y0, y1 = 0, mask.size[1]
    ox, oy = located["origin"]
    digits = {
        "3": (ox + d3[0], oy + y0, ox + d3[1], oy + y1),
        "5": (ox + d5[0], oy + y0, ox + d5[1], oy + y1),
        "7": (ox + d7[0], oy + y0, ox + d7[1], oy + y1),
    }
    gap35 = d5[0] - d3[1]
    gap57 = d7[0] - d5[1]
    return {
        "runs": runs,
        "digits": digits,
        "gap35": gap35,
        "gap57": gap57,
        "line": located["line"],
        "plate": located["plate"],
        "mode": located["mode"],
    }


def _fill_rect(image: Image.Image, box: tuple[int, int, int, int], color: tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(image)
    draw.rectangle((box[0], box[1], box[2] - 1, box[3] - 1), fill=color)


def swap_357_to_375(parent: Image.Image, located: dict[str, Any]) -> tuple[Image.Image, dict[str, Any]]:
    seg = segment_357(located)
    digits = seg["digits"]
    b3, b5, b7 = digits["3"], digits["5"], digits["7"]
    child = parent.convert("RGB").copy()
    plate_crop = _crop(parent, located["line"])
    bg = _median_color(plate_crop, located["mask"])
    glyph5 = _crop(parent, b5)
    glyph7 = _crop(parent, b7)
    clear = (b5[0], min(b5[1], b7[1]), b7[2], max(b5[3], b7[3]))
    _fill_rect(child, clear, bg)
    x7 = b5[0]
    y7 = b5[1]
    child.paste(glyph7, (x7, y7))
    x5 = x7 + (b7[2] - b7[0]) + max(seg["gap57"], 0)
    y5 = b7[1]
    child.paste(glyph5, (x5, y5))
    territory = (
        min(b5[0], x7, x5) - 1,
        min(b5[1], b7[1]) - 1,
        max(b7[2], x5 + glyph5.size[0]) + 1,
        max(b5[3], b7[3]) + 1,
    )
    territory = (
        max(0, territory[0]),
        max(0, territory[1]),
        min(child.size[0], territory[2]),
        min(child.size[1], territory[3]),
    )
    return child, {
        "digits": {k: list(v) for k, v in digits.items()},
        "runs": seg["runs"],
        "gap35": seg["gap35"],
        "gap57": seg["gap57"],
        "background": list(bg),
        "territory": list(territory),
        "plate": list(located["plate"]),
        "line": list(located["line"]),
        "mode": located["mode"],
        "placed": {"7": [x7, y7], "5": [x5, y5]},
    }


def pixel_delta_outside(parent: Image.Image, child: Image.Image, box: tuple[int, int, int, int]) -> dict[str, Any]:
    a = parent.convert("RGB")
    b = child.convert("RGB")
    if a.size != b.size:
        raise RuntimeError("parent/child canvas mismatch")
    diff = ImageChops.difference(a, b)
    px = diff.load()
    w, h = a.size
    x0, y0, x1, y1 = box
    outside = 0
    inside = 0
    max_out = 0
    for y in range(h):
        for x in range(w):
            d = max(px[x, y])
            if not d:
                continue
            if x0 <= x < x1 and y0 <= y < y1:
                inside += 1
            else:
                outside += 1
                max_out = max(max_out, d)
    return {
        "outside_changed_pixels": outside,
        "inside_changed_pixels": inside,
        "outside_max_channel_delta": max_out,
        "territory": list(box),
        "pass": outside == 0 and max_out == 0,
    }


def apply_feed_price_revision(parent: Image.Image) -> tuple[Image.Image | None, dict[str, Any]]:
    _ = parent
    meta = {
        "format": "4:5",
        "status": "SKIPPED_TARGET_NOT_PRESENT",
        "reason": "PRICE territory absent — ORNEK_00012 has no $357.000 plate. Not invented.",
        "old_value": OLD_VALUE,
        "new_value": NEW_VALUE,
        "pixel_delta": {
            "outside_changed_pixels": 0,
            "inside_changed_pixels": 0,
            "pass": True,
            "note": "no PRICE reconstruction attempted",
        },
    }
    return None, meta


def apply_story_price_revision(parent: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    located = locate_story_price_line(parent)
    child, meta = swap_357_to_375(parent, located)
    delta = pixel_delta_outside(parent, child, tuple(meta["territory"]))
    meta["pixel_delta"] = delta
    meta["format"] = "9:16"
    meta["old_value"] = OLD_VALUE
    meta["new_value"] = NEW_VALUE
    return child, meta


def apply_square_price_revision(parent: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    located = locate_square_price_line(parent)
    child, meta = swap_357_to_375(parent, located)
    delta = pixel_delta_outside(parent, child, tuple(meta["territory"]))
    meta["pixel_delta"] = delta
    meta["format"] = "1:1"
    meta["old_value"] = OLD_VALUE
    meta["new_value"] = NEW_VALUE
    return child, meta


def render_pixel_diff(parent: Image.Image, child: Image.Image, box: tuple[int, int, int, int] | None = None) -> Image.Image:
    diff = ImageChops.difference(parent.convert("RGB"), child.convert("RGB"))
    boosted = diff.point(lambda v: min(255, v * 8))
    if box:
        draw = ImageDraw.Draw(boosted)
        draw.rectangle((box[0], box[1], box[2] - 1, box[3] - 1), outline=(255, 0, 0))
    return boosted
