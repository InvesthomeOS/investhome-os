"""Phase 12.6 — native COPY_ONLY revision of last-units badge copy.

Son Daireler! → Son Fırsatlar! is reconstructed independently on each
format master. Does not invent the badge. Does not derive one format
from another. No GPT Image. No Ideogram.
"""

from __future__ import annotations

import html as html_lib
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw

from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.phase5_design_scene import render_html_to_png
from investhome_api.services.creative_director.phase10_0_r1_price_revise import dilate_mask
from investhome_api.services.creative_director.phase12_5_price_revise import luma

OLD_COPY = "Son Daireler!"
NEW_COPY = "Son Fırsatlar!"

# Format-owned search windows. Not derived from a sibling format.
SEARCH = {
    "4:5": (0.10, 0.36, 0.58, 0.68),
    "9:16": (0.00, 0.48, 0.58, 0.84),
    "1:1": (0.42, 0.00, 1.00, 0.52),
}


def is_light_grey(pixel: tuple[int, int, int]) -> bool:
    r, g, b = pixel[:3]
    chroma = max(r, g, b) - min(r, g, b)
    lum = luma(pixel)
    return 110 <= lum <= 235 and chroma <= 32


def is_white_type(pixel: tuple[int, int, int]) -> bool:
    r, g, b = pixel[:3]
    chroma = max(r, g, b) - min(r, g, b)
    return luma(pixel) >= 205 and chroma <= 48


def is_tan(pixel: tuple[int, int, int]) -> bool:
    r, g, b = pixel[:3]
    return r >= 150 and 90 <= g <= 190 and b <= 135 and (r - b) >= 28 and (r - g) <= 60


def _window_px(image: Image.Image, fmt: str) -> tuple[int, int, int, int]:
    W, H = image.size
    l, t, r, b = SEARCH[fmt]
    return (int(l * W), int(t * H), int(r * W), int(b * H))


def _connected_components(mask: Image.Image, *, min_area: int) -> list[dict[str, Any]]:
    w, h = mask.size
    m = mask.load()
    seen = [[False] * w for _ in range(h)]
    blobs: list[dict[str, Any]] = []
    for y0 in range(h):
        for x0 in range(w):
            if seen[y0][x0] or m[x0, y0] < 128:
                continue
            stack = [(x0, y0)]
            seen[y0][x0] = True
            xs: list[int] = []
            ys: list[int] = []
            sx = sy = 0
            while stack:
                x, y = stack.pop()
                xs.append(x)
                ys.append(y)
                sx += x
                sy += y
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if nx < 0 or ny < 0 or nx >= w or ny >= h or seen[ny][nx]:
                        continue
                    if m[nx, ny] < 128:
                        continue
                    seen[ny][nx] = True
                    stack.append((nx, ny))
            area = len(xs)
            if area < min_area:
                continue
            cx = sx / area
            cy = sy / area
            radius = sorted(((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 for x, y in zip(xs, ys))[int(area * 0.92)]
            blobs.append(
                {
                    "area": area,
                    "cx": cx,
                    "cy": cy,
                    "r": max(radius, 8),
                    "bbox": (min(xs), min(ys), max(xs) + 1, max(ys) + 1),
                }
            )
    blobs.sort(key=lambda item: item["area"], reverse=True)
    return blobs


def locate_tan_circle(image: Image.Image, fmt: str) -> dict[str, Any] | None:
    ox0, oy0, ox1, oy1 = _window_px(image, fmt)
    crop = image.crop((ox0, oy0, ox1, oy1))
    scale = max(1, max(crop.size) // 420)
    small = crop.resize((max(1, crop.size[0] // scale), max(1, crop.size[1] // scale)), Image.Resampling.BOX)
    mask = Image.new("L", small.size, 0)
    px, m = small.convert("RGB").load(), mask.load()
    for y in range(small.size[1]):
        for x in range(small.size[0]):
            m[x, y] = 255 if is_tan(px[x, y]) else 0
    blobs = _connected_components(mask, min_area=max(40, (small.size[0] * small.size[1]) // 80))
    if not blobs:
        return None
    blob = blobs[0]
    cx = ox0 + blob["cx"] * scale
    cy = oy0 + blob["cy"] * scale
    radius = blob["r"] * scale * 1.04
    return {
        "cx": cx,
        "cy": cy,
        "r": radius,
        "search": (ox0, oy0, ox1, oy1),
        "bbox": (
            max(0, int(cx - radius) - 4),
            max(0, int(cy - radius) - 4),
            min(image.size[0], int(cx + radius) + 5),
            min(image.size[1], int(cy + radius) + 5),
        ),
    }


def _inside_circle(x: int, y: int, cx: float, cy: float, r: float) -> bool:
    return (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= r * r


def _grey_overlap_mask(image: Image.Image, circle: dict[str, Any]) -> Image.Image:
    """Exclude the overlapping early-delivery disc from last-units type detection."""
    x0, y0, x1, y1 = circle["bbox"]
    crop = image.crop((x0, y0, x1, y1))
    scale = max(1, max(crop.size) // 280)
    small = crop.resize((max(1, crop.size[0] // scale), max(1, crop.size[1] // scale)), Image.Resampling.BOX)
    mask = Image.new("L", small.size, 0)
    px, m = small.convert("RGB").load(), mask.load()
    for y in range(small.size[1]):
        for x in range(small.size[0]):
            m[x, y] = 255 if is_light_grey(px[x, y]) and not is_tan(px[x, y]) else 0
    blobs = _connected_components(mask, min_area=max(30, (small.size[0] * small.size[1]) // 30))
    out = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(out)
    cx = (circle["cx"] - x0) / scale
    for blob in blobs:
        if blob["cx"] >= cx - 4:
            continue
        if blob["area"] < (small.size[0] * small.size[1]) * 0.04:
            continue
        radius = blob["r"] * scale * 1.08
        gx = x0 + blob["cx"] * scale
        gy = y0 + blob["cy"] * scale
        draw.ellipse((gx - radius, gy - radius, gx + radius, gy + radius), fill=255)
    if out.getbbox():
        out = dilate_mask(out, 5)
    return out


def _white_on_tan(image: Image.Image, circle: dict[str, Any], grey: Image.Image | None = None) -> Image.Image:
    mask = Image.new("L", image.size, 0)
    px, m = image.convert("RGB").load(), mask.load()
    g = grey.convert("L").load() if grey is not None else None
    cx, cy, r = circle["cx"], circle["cy"], circle["r"]
    x0, y0, x1, y1 = circle["bbox"]
    for y in range(y0, y1):
        for x in range(x0, x1):
            if g is not None and g[x, y] >= 128:
                continue
            if not _inside_circle(x, y, cx, cy, r * 0.88):
                continue
            pixel = px[x, y]
            if not is_white_type(pixel):
                continue
            tan_n = 0
            for dy in range(-4, 5):
                yy = y + dy
                if yy < 0 or yy >= image.size[1]:
                    continue
                for dx in range(-4, 5):
                    xx = x + dx
                    if xx < 0 or xx >= image.size[0]:
                        continue
                    if g is not None and g[xx, yy] >= 128:
                        continue
                    if is_tan(px[xx, yy]):
                        tan_n += 1
            if tan_n >= 8:
                m[x, y] = 255
    return mask


def _text_bands(mask: Image.Image, circle: dict[str, Any]) -> list[tuple[int, int, int, int]]:
    m = mask.load()
    x0, y0, x1, y1 = circle["bbox"]
    rows: list[tuple[int, int, int]] = []
    for y in range(y0, y1):
        xs = [x for x in range(x0, x1) if m[x, y] >= 128]
        if len(xs) >= 6:
            rows.append((y, min(xs), max(xs) + 1))
    bands: list[tuple[int, int, int, int]] = []
    i = 0
    while i < len(rows):
        y_a, xa, xb = rows[i]
        y_b = y_a + 1
        i += 1
        while i < len(rows) and rows[i][0] <= y_b + 2:
            xa = min(xa, rows[i][1])
            xb = max(xb, rows[i][2])
            y_b = rows[i][0] + 1
            i += 1
        height = y_b - y_a
        width = xb - xa
        if height >= max(4, int(circle["r"] * 0.03)) and width >= max(16, int(circle["r"] * 0.25)) and height <= int(circle["r"] * 0.30):
            bands.append((xa, y_a, xb, y_b))
    bands.sort(key=lambda b: b[1])
    return bands


def locate_last_units_line(image: Image.Image, fmt: str) -> dict[str, Any] | None:
    circle = locate_tan_circle(image, fmt)
    if circle is None:
        return None
    grey = _grey_overlap_mask(image, circle)
    type_mask = _white_on_tan(image, circle, grey)
    bands = _text_bands(type_mask, circle)
    cy, r = circle["cy"], circle["r"]
    lower = [b for b in bands if b[1] >= cy - r * 0.20]
    if lower:
        bands = lower
    if not bands:
        return None
    target = bands[-1]
    keep = bands[:-1]
    pad_x = max(3, int((target[2] - target[0]) * 0.06))
    pad_y = max(2, int((target[3] - target[1]) * 0.16))
    line = (
        max(circle["bbox"][0], target[0] - pad_x),
        max(circle["bbox"][1], target[1] - pad_y),
        min(circle["bbox"][2], target[2] + pad_x),
        min(circle["bbox"][3], target[3] + pad_y),
    )
    return {
        "circle": circle,
        "line": line,
        "keep": keep,
        "type_mask": type_mask,
        "bands": bands,
        "format": fmt,
    }


def _median_tan(image: Image.Image, circle: dict[str, Any], hole: Image.Image) -> tuple[int, int, int]:
    px = image.convert("RGB").load()
    h = hole.convert("L").load()
    rs, gs, bs = [], [], []
    x0, y0, x1, y1 = circle["bbox"]
    cx, cy, r = circle["cx"], circle["cy"], circle["r"]
    for y in range(y0, y1):
        for x in range(x0, x1):
            if h[x, y] >= 128:
                continue
            if not _inside_circle(x, y, cx, cy, r * 0.86):
                continue
            pixel = px[x, y]
            if is_tan(pixel) and luma(pixel) < 180:
                rs.append(pixel[0])
                gs.append(pixel[1])
                bs.append(pixel[2])
    if not rs:
        return (196, 164, 112)
    rs.sort()
    gs.sort()
    bs.sort()
    mid = len(rs) // 2
    return (rs[mid], gs[mid], bs[mid])


def _sample_type_color(image: Image.Image, mask: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int, int]:
    px = image.convert("RGB").load()
    m = mask.convert("L").load()
    rs, gs, bs = [], [], []
    for y in range(box[1], box[3]):
        for x in range(box[0], box[2]):
            if m[x, y] < 128:
                continue
            pixel = px[x, y]
            if luma(pixel) >= 210:
                rs.append(pixel[0])
                gs.append(pixel[1])
                bs.append(pixel[2])
    if not rs:
        return (255, 255, 255)
    rs.sort()
    gs.sort()
    bs.sort()
    mid = len(rs) // 2
    return (rs[mid], gs[mid], bs[mid])


def recover_line(image: Image.Image, located: dict[str, Any]) -> tuple[Image.Image, Image.Image]:
    line = located["line"]
    type_mask = located["type_mask"]
    circle = located["circle"]
    hole = Image.new("L", image.size, 0)
    hp, mp = hole.load(), type_mask.load()
    px = image.convert("RGB").load()
    keep_bottom = max((b[3] for b in located["keep"]), default=line[1] - 8)
    tan_probe = _median_tan(image, circle, Image.new("L", image.size, 0))
    tan_luma = luma(tan_probe)
    shadow_floor = max(8, (line[3] - line[1]) // 3)
    y1 = min(image.size[1], line[3] + shadow_floor)
    x0 = max(0, line[0] - 4)
    x1 = min(image.size[0], line[2] + 4)
    for y in range(line[1], y1):
        if y <= keep_bottom + 1:
            continue
        for x in range(x0, x1):
            pixel = px[x, y]
            lum = luma(pixel)
            if mp[x, y] >= 128 or is_white_type(pixel):
                hp[x, y] = 255
            elif not is_tan(pixel) and lum >= 130:
                hp[x, y] = 255
            elif is_tan(pixel) and lum <= tan_luma - 8:
                hp[x, y] = 255
    radius = max(7, (line[3] - line[1]) // 5)
    if radius % 2 == 0:
        radius += 1
    hole = ImageChops.multiply(dilate_mask(hole, radius), _circle_mask(image.size, circle, inset=0.08))
    hm = hole.load()
    for y in range(0, keep_bottom + 2):
        for x in range(x0, x1):
            hm[x, y] = 0
    clean = image.convert("RGB").copy()
    tan = _median_tan(image, circle, hole)
    src, cp, hm = image.convert("RGB").load(), clean.load(), hole.load()
    box = hole.getbbox() or line
    w, h = image.size
    for y in range(box[1], box[3]):
        for x in range(box[0], box[2]):
            if hm[x, y] < 128:
                continue
            sample = None
            for dist in range(1, 28):
                for nx, ny in ((x, y - dist), (x, y + dist), (x - dist, y), (x + dist, y)):
                    if nx < 0 or ny < 0 or nx >= w or ny >= h:
                        continue
                    if hm[nx, ny] >= 128:
                        continue
                    pixel = src[nx, ny]
                    if is_tan(pixel) and luma(pixel) >= tan_luma - 6:
                        sample = pixel
                        break
                if sample is not None:
                    break
            cp[x, y] = sample if sample is not None else tan
    return clean, hole


def _circle_mask(size: tuple[int, int], circle: dict[str, Any], *, inset: float) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    cx, cy, r = circle["cx"], circle["cy"], circle["r"] * (1.0 - inset)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    return mask


def _sans_css() -> tuple[str, dict[str, Any]]:
    registry = build_font_registry()
    roles = dict(registry.get("roles") or {})
    spec = dict(roles.get("DISPLAY_SANS") or {}) or dict(roles.get("EDITORIAL_SANS") or {})
    path = spec.get("font_path")
    if not path or not Path(str(path)).is_file():
        raise RuntimeError("Phase 12.6 requires a campaign sans face")
    import base64

    payload = base64.b64encode(Path(str(path)).read_bytes()).decode("ascii")
    css = (
        f"@font-face{{font-family:'Campaign Sans';src:url('data:font/ttf;base64,{payload}') "
        f"format('truetype');font-weight:300 800;font-style:normal;font-display:block;}}"
    )
    return css, spec


def _line_html(
    *,
    width: int,
    height: int,
    text: str,
    size: int,
    tracking: float,
    color: tuple[int, int, int],
    bg: tuple[int, int, int],
    font_css: str,
) -> str:
    rgb = f"rgb({color[0]},{color[1]},{color[2]})"
    bgc = f"rgb({bg[0]},{bg[1]},{bg[2]})"
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8"/>
<style>
{font_css}
html,body{{margin:0;padding:0;width:{width}px;height:{height}px;overflow:hidden;background:{bgc};}}
.line{{position:absolute;left:0;right:0;top:50%;transform:translateY(-50%);margin:0;padding:0;
  text-align:center;color:{rgb};font-family:'Campaign Sans',sans-serif;font-weight:700;
  font-size:{size}px;letter-spacing:{tracking}em;line-height:1.0;white-space:nowrap;}}
</style>
</head>
<body>
<p class="line">{html_lib.escape(text)}</p>
</body>
</html>
"""


def _glyph_bbox(layer: Image.Image, bg: tuple[int, int, int]) -> tuple[int, int, int, int] | None:
    px = layer.load()
    xs: list[int] = []
    ys: list[int] = []
    for y in range(layer.size[1]):
        for x in range(layer.size[0]):
            r, g, b = px[x, y]
            if abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2]) > 40:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return (min(xs), min(ys), max(xs) + 1, max(ys) + 1)


def _chord_width(circle: dict[str, Any], y: float) -> float:
    dy = y - circle["cy"]
    r = circle["r"] * 0.78
    inside = r * r - dy * dy
    if inside <= 0:
        return 0.0
    return 2.0 * (inside ** 0.5)


def render_replacement_plate(
    *,
    width: int,
    height: int,
    font_css: str,
    color: tuple[int, int, int],
    bg: tuple[int, int, int],
    max_width: int,
    max_height: int,
    start_size: int,
) -> tuple[Image.Image, dict[str, Any]]:
    attempts: list[dict[str, Any]] = []
    chosen: dict[str, Any] | None = None
    sizes = list(range(start_size, max(9, int(start_size * 0.62)) - 1, -2))
    if start_size not in sizes:
        sizes.insert(0, start_size)
    trackings = (0.0, -0.02, -0.04, 0.01)
    for size in sizes:
        for tracking in trackings:
            html = _line_html(
                width=width,
                height=height,
                text=NEW_COPY,
                size=size,
                tracking=tracking,
                color=color,
                bg=bg,
                font_css=font_css,
            )
            layer = render_html_to_png(html, width=width, height=height).convert("RGB")
            box = _glyph_bbox(layer, bg)
            record = {"size": size, "tracking": tracking, "bbox": None if box is None else list(box)}
            attempts.append(record)
            if box is None:
                continue
            gw, gh = box[2] - box[0], box[3] - box[1]
            if gw <= max_width and gh <= max_height:
                chosen = {**record, "layer": layer, "box": box}
                break
        if chosen is not None:
            break
    if chosen is None:
        raise RuntimeError("Son Fırsatlar! could not fit inside the last-units badge")
    chosen["attempts"] = attempts
    return chosen["layer"], chosen


def stamp_plate(
    clean: Image.Image,
    plate: Image.Image,
    origin: tuple[int, int],
    *,
    circle: dict[str, Any],
    keep_bottom: int,
) -> tuple[Image.Image, tuple[int, int, int, int]]:
    out = clean.copy()
    op, pp, cp = out.load(), plate.load(), clean.load()
    clip = _circle_mask(clean.size, circle, inset=0.08)
    cl = clip.load()
    ox, oy = origin
    pw, ph = plate.size
    touched = [ox + pw, oy + ph, ox, oy]
    for y in range(ph):
        gy = oy + y
        if gy <= keep_bottom + 1:
            continue
        for x in range(pw):
            gx = ox + x
            if gx < 0 or gy < 0 or gx >= clean.size[0] or gy >= clean.size[1]:
                continue
            if cl[gx, gy] < 128:
                continue
            if luma(pp[x, y]) < 190:
                continue
            if luma(pp[x, y]) > luma(cp[gx, gy]) + 22:
                op[gx, gy] = pp[x, y]
                touched[0] = min(touched[0], gx)
                touched[1] = min(touched[1], gy)
                touched[2] = max(touched[2], gx + 1)
                touched[3] = max(touched[3], gy + 1)
    if touched[2] <= touched[0]:
        return out, (ox, oy, ox + pw, oy + ph)
    return out, (touched[0], touched[1], touched[2], touched[3])


def pixel_delta_outside(parent: Image.Image, child: Image.Image, box: tuple[int, int, int, int]) -> dict[str, Any]:
    a = parent.convert("RGB")
    b = child.convert("RGB")
    if a.size != b.size:
        raise RuntimeError("parent/child canvas mismatch")
    diff = ImageChops.difference(a, b)
    inside = diff.crop(box)
    inside_changed = sum(inside.convert("L").histogram()[1:])
    painted = diff.copy()
    ImageDraw.Draw(painted).rectangle([box[0], box[1], box[2] - 1, box[3] - 1], fill=(0, 0, 0))
    outside_hist = painted.convert("L").histogram()
    outside = sum(outside_hist[1:])
    max_out = max(ch[1] for ch in painted.getextrema())
    return {
        "outside_changed_pixels": outside,
        "inside_changed_pixels": inside_changed,
        "outside_max_channel_delta": max_out,
        "territory": list(box),
        "pass": outside == 0 and max_out == 0,
    }


def apply_last_units_copy_revision(parent: Image.Image, *, fmt: str) -> tuple[Image.Image | None, dict[str, Any]]:
    located = locate_last_units_line(parent, fmt)
    if located is None:
        return None, {
            "format": fmt,
            "status": "SKIPPED_TARGET_NOT_PRESENT",
            "reason": "Son Daireler! last-units line was not present on this format",
            "old_value": OLD_COPY,
            "new_value": NEW_COPY,
            "pixel_delta": {
                "outside_changed_pixels": 0,
                "inside_changed_pixels": 0,
                "pass": True,
                "note": "no COPY reconstruction attempted",
            },
        }
    clean, hole = recover_line(parent, located)
    line = located["line"]
    circle = located["circle"]
    color = _sample_type_color(parent, located["type_mask"], line)
    tan = _median_tan(parent, circle, hole)
    font_css, font_spec = _sans_css()
    start_size = max(12, int((line[3] - line[1]) * 0.92))
    mid_y = (line[1] + line[3]) / 2
    max_w = max(24, int(_chord_width(circle, mid_y)))
    keep_bottom = max((b[3] for b in located["keep"]), default=line[1])
    max_h = max(10, int(min(line[3] + (line[3] - line[1]) * 0.35, circle["cy"] + circle["r"] * 0.72) - keep_bottom - 3))
    plate_w = max(line[2] - line[0], max_w) + 16
    plate_h = max(line[3] - line[1] + 16, start_size + 18)
    origin = (
        int(round(circle["cx"] - plate_w / 2)),
        int(round(mid_y - plate_h / 2)),
    )
    origin = (
        max(0, min(parent.size[0] - plate_w, origin[0])),
        max(0, min(parent.size[1] - plate_h, origin[1])),
    )
    plate, layout = render_replacement_plate(
        width=plate_w,
        height=plate_h,
        font_css=font_css,
        color=color,
        bg=tan,
        max_width=max_w,
        max_height=min(max_h, plate_h - 4),
        start_size=min(start_size, plate_h - 8),
    )
    child, stamp_box = stamp_plate(clean, plate, origin, circle=circle, keep_bottom=keep_bottom)
    hole_box = hole.getbbox() or line
    new_box = tuple(layout["box"])
    territory = (
        min(line[0], hole_box[0], origin[0] + new_box[0], stamp_box[0]),
        min(line[1], hole_box[1], origin[1] + new_box[1], stamp_box[1]),
        max(line[2], hole_box[2], origin[0] + new_box[2], stamp_box[2]),
        max(line[3], hole_box[3], origin[1] + new_box[3], stamp_box[3]),
    )
    delta = pixel_delta_outside(parent, child, territory)
    meta = {
        "format": fmt,
        "status": "REVISED" if delta["pass"] else "FAIL",
        "reason": "TARGET_PRESENT",
        "old_value": OLD_COPY,
        "new_value": NEW_COPY,
        "territory": list(territory),
        "line": list(line),
        "circle": {"cx": circle["cx"], "cy": circle["cy"], "r": circle["r"], "bbox": list(circle["bbox"])},
        "layout": {k: v for k, v in layout.items() if k != "layer"},
        "font": {"path": font_spec.get("font_path"), "file": font_spec.get("file") or font_spec.get("family")},
        "type_color": list(color),
        "tan": list(tan),
        "pixel_delta": delta,
        "keep_lines": [list(b) for b in located["keep"]],
    }
    return child, meta


def apply_feed_copy_revision(parent: Image.Image) -> tuple[Image.Image | None, dict[str, Any]]:
    return apply_last_units_copy_revision(parent, fmt="4:5")


def apply_story_copy_revision(parent: Image.Image) -> tuple[Image.Image | None, dict[str, Any]]:
    return apply_last_units_copy_revision(parent, fmt="9:16")


def apply_square_copy_revision(parent: Image.Image) -> tuple[Image.Image | None, dict[str, Any]]:
    return apply_last_units_copy_revision(parent, fmt="1:1")
