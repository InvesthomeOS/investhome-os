"""PhotoOccupancyMapV1 — meaningful geometry on the actual photograph.

Not one rectangular architecture mask. Collision and field placement use these
layers. Architecture pixels stay source pixels.
"""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat

from investhome_api.services.creative_director.project_architecture_lock import derive_architecture_mask

LAYER_COLORS = {
    "hard_protected": (200, 36, 48),
    "soft_occupied": (220, 120, 40),
    "preferred_negative_space": (48, 110, 210),
    "graphically_extendable": (140, 70, 190),
    "text_safe": (40, 170, 90),
    "logo_safe": (40, 190, 190),
    "cta_safe": (220, 190, 50),
    "commercial_safe": (90, 210, 130),
}


def _coverage(mask: Image.Image, threshold: int = 128) -> float:
    hist = mask.convert("L").histogram()
    total = max(1, sum(hist))
    return round(sum(hist[threshold:]) / total, 4)


def _largest_component_bbox(mask: Image.Image, *, threshold: int = 100, grid: tuple[int, int] = (54, 68)) -> dict[str, float] | None:
    gw, gh = grid
    small = mask.convert("L").resize((gw, gh), Image.Resampling.BOX)
    px = small.load()
    seen = [[False] * gw for _ in range(gh)]
    best_n = 0
    best: dict[str, float] | None = None
    for y in range(gh):
        for x in range(gw):
            if seen[y][x] or int(px[x, y]) < threshold:
                continue
            stack = [(x, y)]
            seen[y][x] = True
            cells: list[tuple[int, int]] = []
            while stack:
                cx, cy = stack.pop()
                cells.append((cx, cy))
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if 0 <= nx < gw and 0 <= ny < gh and not seen[ny][nx] and int(px[nx, ny]) >= threshold:
                        seen[ny][nx] = True
                        stack.append((nx, ny))
            if len(cells) > best_n:
                best_n = len(cells)
                xs = [c[0] for c in cells]
                ys = [c[1] for c in cells]
                best = {
                    "x": round(min(xs) / gw, 4),
                    "y": round(min(ys) / gh, 4),
                    "w": round((max(xs) + 1 - min(xs)) / gw, 4),
                    "h": round((max(ys) + 1 - min(ys)) / gh, 4),
                    "area": round(len(cells) / float(gw * gh), 4),
                }
    return best


def _sky_mask(src: Image.Image) -> Image.Image:
    w, h = src.size
    rgb = src.convert("RGB")
    gray = rgb.convert("L")
    out = Image.new("L", src.size, 0)
    sp, gp, op = rgb.load(), gray.load(), out.load()
    for y in range(h):
        yn = y / max(h - 1, 1)
        if yn > 0.58:
            continue
        for x in range(w):
            r, g, b = sp[x, y]
            lval = int(gp[x, y])
            sat = max(r, g, b) - min(r, g, b)
            if yn < 0.52 and lval > 165 and sat < 48:
                op[x, y] = 255
            elif yn < 0.22 and lval > 178 and sat < 40:
                op[x, y] = 220
    return out.filter(ImageFilter.MedianFilter(3))


def _bbox_from_mask(mask: Image.Image, *, threshold: int = 96, grid: tuple[int, int] = (68, 85)) -> dict[str, float] | None:
    small = mask.convert("L").resize(grid, Image.Resampling.BOX)
    px = small.load()
    gw, gh = small.size
    xs: list[int] = []
    ys: list[int] = []
    for y in range(gh):
        for x in range(gw):
            if int(px[x, y]) >= threshold:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return {
        "x": round(min(xs) / gw, 4),
        "y": round(min(ys) / gh, 4),
        "w": round((max(xs) + 1 - min(xs)) / gw, 4),
        "h": round((max(ys) + 1 - min(ys)) / gh, 4),
    }


def _sky_bands(sky: Image.Image, hard: Image.Image, centroid: float) -> dict[str, dict[str, float] | None]:
    gw, gh = 54, 68
    sky_s = sky.convert("L").resize((gw, gh), Image.Resampling.BOX)
    hard_s = hard.convert("L").resize((gw, gh), Image.Resampling.BOX)
    sp, hp = sky_s.load(), hard_s.load()
    cut = max(8, min(gw - 8, int(centroid * gw)))
    bands: dict[str, dict[str, float] | None] = {}
    for side, x0, x1 in (("left", 0, cut), ("right", cut, gw)):
        width = max(1, x1 - x0)
        last = 0
        for y in range(int(gh * 0.48)):
            sky_n = hard_n = 0
            for x in range(x0, x1):
                if int(sp[x, y]) >= 100:
                    sky_n += 1
                if int(hp[x, y]) >= 100:
                    hard_n += 1
            if sky_n / width >= 0.28 and hard_n / width <= 0.06:
                last = y
            elif y > 4:
                break
        if last < 6:
            bands[side] = None
            continue
        good: list[int] = []
        rows = last + 1
        for x in range(x0, x1):
            ok = 0
            for y in range(rows):
                if int(sp[x, y]) >= 100 and int(hp[x, y]) < 80:
                    ok += 1
            if ok == rows:
                good.append(x)
        if len(good) < 6:
            bands[side] = None
            continue
        bands[side] = {
            "x": round(min(good) / gw, 4),
            "y": 0.02,
            "w": round((max(good) + 1 - min(good)) / gw, 4),
            "h": round(rows / gh, 4),
            "area": round((len(good) * rows) / float(gw * gh), 4),
        }
    return bands


def _split_left_right(mask: Image.Image, *, split_x: float, threshold: int = 96) -> tuple[Image.Image, Image.Image]:
    w, h = mask.size
    left = Image.new("L", (w, h), 0)
    right = Image.new("L", (w, h), 0)
    cut = int(split_x * w)
    left.paste(mask.crop((0, 0, cut, h)), (0, 0))
    right.paste(mask.crop((cut, 0, w, h)), (cut, 0))
    if threshold > 0:
        left = left.point(lambda v, t=threshold: 255 if v >= t else 0)
        right = right.point(lambda v, t=threshold: 255 if v >= t else 0)
    return left, right


def _band(size: tuple[int, int], y0: float, y1: float, fill: int = 255) -> Image.Image:
    w, h = size
    out = Image.new("L", size, 0)
    ImageDraw.Draw(out).rectangle((0, int(y0 * h), w, int(y1 * h)), fill=fill)
    return out


def _mass_x(mask: Image.Image, threshold: int = 128) -> float:
    small = mask.convert("L").resize((48, 60), Image.Resampling.BOX)
    px = small.load()
    acc = 0.0
    weight = 0.0
    gw, gh = small.size
    for y in range(gh):
        for x in range(gw):
            v = int(px[x, y])
            if v >= threshold:
                acc += x * v
                weight += v
    if weight <= 0:
        return 0.5
    return acc / weight / max(gw - 1, 1)


def build_photo_occupancy_map(
    photo: Image.Image,
    *,
    protection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    src = photo.convert("RGB")
    w, h = src.size
    architecture = derive_architecture_mask(src).convert("L")
    gray = src.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    sky = _sky_mask(src)
    # HARD is the building silhouette. Sky is never hard, even if the
    # architecture detector over-preserved it.
    hard = ImageChops.subtract(architecture.point(lambda v: 255 if v > 48 else 0), sky)
    hard = hard.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    not_hard = hard.point(lambda v: 0 if v > 40 else 255)

    dilated = hard.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(radius=4))
    fringe = ImageChops.subtract(dilated.point(lambda v: 255 if v > 40 else 0), hard)
    street = ImageChops.multiply(
        _band(src.size, 0.78, 1.0),
        gray.point(lambda v: 255 if v < 110 else 0),
    )
    street = ImageChops.subtract(street, hard)
    trees = Image.new("L", src.size, 0)
    rgb = src.load()
    tp = trees.load()
    for y in range(int(h * 0.42), h, 3):
        for x in range(0, w, 3):
            r, g, b = rgb[x, y]
            if g > r + 12 and g > b + 6 and g > 70:
                tp[x, y] = 200
    trees = trees.filter(ImageFilter.MaxFilter(5))
    trees = ImageChops.subtract(trees, hard)
    soft = ImageChops.lighter(ImageChops.lighter(fringe, street), trees)

    quiet = ImageChops.multiply(
        gray.point(lambda v: 255 if 70 < v < 165 else 0),
        edges.point(lambda v: 255 if v < 28 else 0),
    )
    quiet = ImageChops.multiply(quiet, not_hard)
    negative = ImageChops.lighter(sky, ImageChops.multiply(quiet, _band(src.size, 0.0, 0.62)))

    edge_right = Image.new("L", src.size, 0)
    ImageDraw.Draw(edge_right).rectangle((int(w * 0.58), 0, w, int(h * 0.55)), fill=255)
    edge_left = Image.new("L", src.size, 0)
    ImageDraw.Draw(edge_left).rectangle((0, 0, int(w * 0.28), int(h * 0.48)), fill=255)
    edge_top = _band(src.size, 0.0, 0.30)
    extendable = ImageChops.multiply(
        ImageChops.lighter(ImageChops.lighter(edge_right, edge_left), edge_top),
        not_hard,
    )
    extendable = ImageChops.lighter(extendable, sky)

    text_safe = ImageChops.multiply(negative, _band(src.size, 0.0, 0.58))
    text_safe = ImageChops.subtract(text_safe, hard)
    text_safe = text_safe.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(5))

    logo_bottom = ImageChops.multiply(_band(src.size, 0.84, 0.96), not_hard)
    logo_top = ImageChops.multiply(_band(src.size, 0.02, 0.12), not_hard)
    logo_safe = ImageChops.lighter(logo_bottom, logo_top)

    street_noise = ImageChops.lighter(street, ImageChops.multiply(_band(src.size, 0.82, 1.0), edges.point(lambda v: 255 if v > 36 else 0)))
    cta_safe = ImageChops.multiply(text_safe, _band(src.size, 0.18, 0.78))
    cta_safe = ImageChops.subtract(cta_safe, street_noise)
    commercial_safe = ImageChops.multiply(text_safe, _band(src.size, 0.08, 0.70))

    centroid = _mass_x(hard)
    sky_left, sky_right = _split_left_right(sky, split_x=centroid)
    text_left, text_right = _split_left_right(text_safe, split_x=centroid)
    pockets = _sky_bands(sky, hard, centroid)

    layers = {
        "hard_protected": hard,
        "soft_occupied": soft,
        "preferred_negative_space": negative,
        "graphically_extendable": extendable,
        "text_safe": text_safe,
        "logo_safe": logo_safe,
        "cta_safe": cta_safe,
        "commercial_safe": commercial_safe,
        "sky": sky,
        "sky_left": sky_left,
        "sky_right": sky_right,
        "text_left": text_left,
        "text_right": text_right,
        "street": street,
        "not_hard": not_hard,
        "collision_core": hard.filter(ImageFilter.MinFilter(5)),
    }
    regions = {
        "hard_protected": _bbox_from_mask(hard),
        "soft_occupied": _bbox_from_mask(soft, threshold=64),
        "preferred_negative_space": _bbox_from_mask(negative),
        "graphically_extendable": _bbox_from_mask(extendable, threshold=64),
        "text_safe": _bbox_from_mask(text_safe),
        "logo_safe": _bbox_from_mask(logo_safe, threshold=64),
        "cta_safe": _bbox_from_mask(cta_safe, threshold=64),
        "commercial_safe": _bbox_from_mask(commercial_safe),
        "sky_left": _bbox_from_mask(sky_left, threshold=64),
        "sky_right": _bbox_from_mask(sky_right, threshold=64),
        "text_left": pockets.get("left"),
        "text_right": pockets.get("right"),
        "pocket_left": pockets.get("left"),
        "pocket_right": pockets.get("right"),
    }
    _ = protection
    return {
        "schema": "PhotoOccupancyMapV1",
        "size": [w, h],
        "architecture_centroid_x": round(centroid, 4),
        "coverage": {
            "hard_protected": _coverage(hard),
            "soft_occupied": _coverage(soft, 64),
            "preferred_negative_space": _coverage(negative),
            "graphically_extendable": _coverage(extendable, 64),
            "text_safe": _coverage(text_safe),
            "sky_left": _coverage(sky_left, 64),
            "sky_right": _coverage(sky_right, 64),
        },
        "regions": regions,
        "pockets": pockets,
        "sky_area": _coverage(sky),
        "layers": layers,
        "note": "HARD is the building silhouette. SPIRE rectangles are routing hints, not collision geometry.",
    }


def occupancy_to_json(occupancy: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in occupancy.items() if k != "layers"}


def render_occupancy_map(photo: Image.Image, occupancy: dict[str, Any]) -> Image.Image:
    src = photo.convert("RGB").resize((720, 900), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (1480, 980), (12, 14, 20))
    canvas.paste(src, (36, 50))
    overlay = src.convert("RGBA")
    order = (
        "soft_occupied",
        "preferred_negative_space",
        "graphically_extendable",
        "text_safe",
        "hard_protected",
    )
    layers = occupancy.get("layers") or {}
    for name in order:
        mask = layers.get(name)
        if not isinstance(mask, Image.Image):
            continue
        color = LAYER_COLORS.get(name, (180, 180, 180))
        tint = Image.new("RGBA", src.size, (*color, 72))
        m = mask.convert("L").resize(src.size, Image.Resampling.BILINEAR)
        overlay = Image.composite(Image.alpha_composite(overlay, tint), overlay, m)
    canvas.paste(overlay.convert("RGB"), (36, 50))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 16), "DAY_004 OCCUPANCY MAP  —  silhouette, not a fat SPIRE rectangle", fill=(201, 168, 92))
    y = 50
    x = 780
    for name, color in LAYER_COLORS.items():
        cov = (occupancy.get("coverage") or {}).get(name)
        if cov is None and name == "preferred_negative_space":
            cov = (occupancy.get("coverage") or {}).get("preferred_negative_space")
        draw.rectangle((x, y, x + 28, y + 18), fill=color)
        label = name.replace("_", " ")
        extra = f"  {cov:.3f}" if isinstance(cov, float) else ""
        draw.text((x + 40, y), f"{label}{extra}", fill=(220, 216, 208))
        y += 28
    draw.text((x, y + 12), f"sky area {occupancy.get('sky_area')}", fill=(180, 176, 168))
    draw.text((x, y + 36), f"centroid x {occupancy.get('architecture_centroid_x')}", fill=(180, 176, 168))
    draw.text((x, y + 70), "HARD: spire / roof / facade / silhouette", fill=(220, 216, 208))
    draw.text((x, y + 94), "SOFT: fringe, street, cars, trees", fill=(220, 216, 208))
    draw.text((x, y + 118), "FIELD may extend only into extendable ∩ not HARD", fill=(220, 216, 208))
    return canvas


def mean_luma(image: Image.Image, box: tuple[int, int, int, int] | None = None) -> float:
    crop = image.convert("L") if box is None else image.convert("L").crop(box)
    if crop.size[0] < 2 or crop.size[1] < 2:
        return 128.0
    return float(ImageStat.Stat(crop).mean[0])
