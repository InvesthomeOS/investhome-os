"""ProjectObjectExtractionV2 — matting + color decontamination, no AI redraw.

V1/R1 binary sky-punch + erode + blur left pale sky mixed into the silhouette.
V2 builds a trimap, reconstructs edge alpha, and unmixes background color from
the contour. Source architecture pixels stay real.
"""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw, ImageFilter

from investhome_api.services.creative_director.phase11_6_strategy import DAY003_ASSET_ID, DAY003_FILENAME
from investhome_api.services.creative_director.project_architecture_lock import derive_architecture_mask

SCHEMA = "ProjectObjectExtractionV2"
CROP_BOX = {"left": 0.39, "top": 0.00, "width": 0.46, "height": 0.80}
EDGE_BACKGROUNDS = {
    "white": (245, 245, 243),
    "black": (8, 8, 8),
    "charcoal": (42, 40, 38),
    "paper": (214, 198, 172),
    "gray": (128, 126, 122),
}


def _lum(r: int, g: int, b: int) -> float:
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _is_sky(r: int, g: int, b: int, yn: float) -> bool:
    lum = _lum(r, g, b)
    sat = max(r, g, b) - min(r, g, b)
    if b >= r + 8 and b >= g + 2 and lum > 96:
        return True
    if yn < 0.58 and lum > 158 and sat < 26 and b >= r - 3:
        return True
    if lum > 210 and sat < 18 and b >= g - 4:
        return True
    return False


def crop_project_window(
    source: Image.Image,
    crop_box: dict[str, float] | None = None,
) -> tuple[Image.Image, dict[str, Any]]:
    box = dict(crop_box or CROP_BOX)
    sw, sh = source.size
    left = int(sw * float(box["left"]))
    top = int(sh * float(box["top"]))
    width = max(1, int(sw * float(box["width"])))
    height = max(1, int(sh * float(box["height"])))
    left = min(max(0, left), max(0, sw - width))
    top = min(max(0, top), max(0, sh - height))
    window = source.crop((left, top, left + width, top + height))
    return window, {"crop_box": box, "source_size": [sw, sh], "window_size": list(window.size)}


def _sky_mask(rgb: Image.Image) -> Image.Image:
    w, h = rgb.size
    mask = Image.new("L", (w, h), 0)
    px, mp = rgb.load(), mask.load()
    for y in range(h):
        yn = y / max(h - 1, 1)
        for x in range(w):
            r, g, b = px[x, y]
            if _is_sky(r, g, b, yn):
                mp[x, y] = 255
    return mask


def _trimap(fg_binary: Image.Image) -> Image.Image:
    """0 = BG, 128 = unknown, 255 = FG. 2px unknown band. No post-sky dilation of FG."""
    core = fg_binary.filter(ImageFilter.MinFilter(3))
    unknown = Image.new("L", fg_binary.size, 0)
    dilated = fg_binary.filter(ImageFilter.MaxFilter(5))
    cp, dp, up = core.load(), dilated.load(), unknown.load()
    w, h = fg_binary.size
    trimap = Image.new("L", (w, h), 0)
    tp = trimap.load()
    for y in range(h):
        for x in range(w):
            if cp[x, y] > 128:
                tp[x, y] = 255
            elif dp[x, y] > 128:
                tp[x, y] = 128
                up[x, y] = 255
            else:
                tp[x, y] = 0
    return trimap


def _sample_bg(rgb: Image.Image, sky: Image.Image) -> tuple[float, float, float]:
    px, sp = rgb.load(), sky.load()
    w, h = rgb.size
    rs = gs = bs = n = 0.0
    for y in range(0, max(1, int(h * 0.45)), 3):
        for x in range(0, w, 4):
            if sp[x, y] > 128:
                r, g, b = px[x, y]
                rs += r
                gs += g
                bs += b
                n += 1
    if n < 8:
        return (176.0, 196.0, 214.0)
    return (rs / n, gs / n, bs / n)


def _sample_fg_interior(rgb: Image.Image, core: Image.Image) -> tuple[float, float, float]:
    px, cp = rgb.load(), core.load()
    w, h = rgb.size
    rs = gs = bs = n = 0.0
    for y in range(int(h * 0.12), int(h * 0.70), 4):
        for x in range(int(w * 0.20), int(w * 0.80), 4):
            if cp[x, y] > 200:
                r, g, b = px[x, y]
                rs += r
                gs += g
                bs += b
                n += 1
    if n < 8:
        return (168.0, 154.0, 132.0)
    return (rs / n, gs / n, bs / n)


def _unmix(c: tuple[int, int, int], alpha: float, bg: tuple[float, float, float]) -> tuple[int, int, int]:
    a = max(alpha, 0.04)
    out = []
    for i in range(3):
        f = (c[i] - (1.0 - a) * bg[i]) / a
        out.append(max(0, min(255, int(round(f)))))
    return (out[0], out[1], out[2])


def _reconstruct_edges(
    rgb: Image.Image,
    trimap: Image.Image,
    bg: tuple[float, float, float],
    fg_mean: tuple[float, float, float],
) -> Image.Image:
    w, h = rgb.size
    rgba = rgb.convert("RGBA")
    rp, gp, bp, ap = rgba.split()
    rpx, gpx, bpx, apx = rp.load(), gp.load(), bp.load(), ap.load()
    tp = trimap.load()
    px = rgb.load()

    def dist(c: tuple[int, int, int], ref: tuple[float, float, float]) -> float:
        return abs(c[0] - ref[0]) + abs(c[1] - ref[1]) + abs(c[2] - ref[2])

    for y in range(h):
        yn = y / max(h - 1, 1)
        for x in range(w):
            t = int(tp[x, y])
            if t == 0:
                apx[x, y] = 0
                continue
            if t == 255:
                apx[x, y] = 255
                continue
            c = px[x, y]
            if _is_sky(c[0], c[1], c[2], yn):
                apx[x, y] = 0
                continue
            db = dist(c, bg) + 1.0
            df = dist(c, fg_mean) + 1.0
            alpha = db / (db + df)
            if c[2] >= c[0] + 6 and _lum(*c) > 110:
                alpha *= 0.15
            alpha = max(0.0, min(1.0, alpha))
            if alpha < 0.12:
                apx[x, y] = 0
                continue
            fr, fg, fb = _unmix(c, alpha, bg)
            rpx[x, y], gpx[x, y], bpx[x, y] = fr, fg, fb
            apx[x, y] = int(round(alpha * 255))

    # Decontaminate opaque contour: FG pixels that touch transparency still hold mixed sky.
    for y in range(h):
        yn = y / max(h - 1, 1)
        for x in range(w):
            if int(apx[x, y]) < 250:
                continue
            edge = False
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-2, 0), (2, 0), (0, -2), (0, 2)):
                nx, ny = x + dx, y + dy
                if nx < 0 or ny < 0 or nx >= w or ny >= h or int(apx[nx, ny]) < 40:
                    edge = True
                    break
            if not edge:
                continue
            c = (int(rpx[x, y]), int(gpx[x, y]), int(bpx[x, y]))
            if _is_sky(c[0], c[1], c[2], yn):
                apx[x, y] = 0
                continue
            db = dist(c, bg) + 1.0
            df = dist(c, fg_mean) + 1.0
            mix = df / (db + df)
            # mix near 1 => pixel is close to background color while marked opaque.
            if mix > 0.42:
                alpha = max(0.35, 1.0 - mix)
                fr, fg, fb = _unmix(c, alpha, bg)
                rpx[x, y], gpx[x, y], bpx[x, y] = fr, fg, fb
                apx[x, y] = int(round(alpha * 255))
            else:
                fr, fg, fb = _unmix(c, 0.92, bg)
                rpx[x, y] = (c[0] * 3 + fr) // 4
                gpx[x, y] = (c[1] * 3 + fg) // 4
                bpx[x, y] = (c[2] * 3 + fb) // 4

    rgba.putalpha(ap)
    # Sub-pixel edge: tiny blur on alpha only, then restore RGB.
    alpha = rgba.split()[-1].filter(ImageFilter.GaussianBlur(radius=0.35))
    rgba.putalpha(alpha)
    return rgba


def extract_project_object_v2(
    source: Image.Image,
    *,
    crop_box: dict[str, float] | None = None,
    filename: str | None = None,
    asset_id: str | None = None,
) -> tuple[Image.Image, dict[str, Any]]:
    window, crop_meta = crop_project_window(source.convert("RGB"), crop_box)
    sky = _sky_mask(window)
    arch = derive_architecture_mask(window).convert("L")
    w, h = window.size
    fg = Image.new("L", (w, h), 0)
    ap, sp, fp = arch.load(), sky.load(), fg.load()
    for y in range(h):
        for x in range(w):
            if ap[x, y] > 56 and sp[x, y] < 128:
                fp[x, y] = 255
    fg = fg.point(lambda v: 255 if v > 128 else 0)
    trimap = _trimap(fg)
    bg = _sample_bg(window, sky)
    fg_mean = _sample_fg_interior(window, fg.filter(ImageFilter.MinFilter(5)))
    rgba = _reconstruct_edges(window, trimap, bg, fg_mean)
    alpha = rgba.split()[-1]
    bbox = alpha.getbbox()
    if bbox is None:
        raise RuntimeError("ProjectObjectExtractionV2 failed to isolate project object")
    x0, y0, x1, y1 = bbox
    obj = rgba.crop((x0, y0, x1, y1))
    meta = {
        "schema": SCHEMA,
        "filename": filename or DAY003_FILENAME,
        "asset_id": asset_id or DAY003_ASSET_ID,
        "crop": crop_meta,
        "object_size": list(obj.size),
        "bbox": [x0, y0, x1, y1],
        "generated_architecture_pixels": 0,
        "method": "trimap_matting_plus_background_decontamination",
        "dilate_after_sky_punch": False,
        "ai_redraw": False,
        "background_estimate": [round(v, 1) for v in bg],
    }
    return obj, meta


def composite_on(obj: Image.Image, color: tuple[int, int, int], size: tuple[int, int] | None = None) -> Image.Image:
    canvas = Image.new("RGB", size or (1088, 1360), color)
    fitted = obj.copy()
    fitted.thumbnail((int(canvas.size[0] * 0.82), int(canvas.size[1] * 0.88)), Image.Resampling.LANCZOS)
    x = (canvas.size[0] - fitted.size[0]) // 2
    y = (canvas.size[1] - fitted.size[1]) // 2
    canvas.paste(fitted, (x, y), fitted)
    return canvas, (x, y, fitted.size[0], fitted.size[1])


def inspect_fringe(obj: Image.Image, color: tuple[int, int, int]) -> dict[str, Any]:
    """Inspect a 2px morphological ring on the composited plate — not interior limestone."""
    plate, layout = composite_on(obj, color)
    x, y, w, h = layout
    placed = obj.resize((w, h), Image.Resampling.LANCZOS)
    alpha = placed.split()[-1]
    hard = alpha.point(lambda v: 255 if v > 160 else 0)
    hard = hard.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    pad = Image.new("L", (w + 4, h + 4), 0)
    pad.paste(hard, (2, 2))
    ImageDraw.floodfill(pad, (0, 0), 40)
    ppad = pad.load()
    ring_img = Image.new("L", (w, h), 0)
    rrp = ring_img.load()
    for yy in range(h):
        for xx in range(w):
            if int(ppad[xx + 2, yy + 2]) < 200:
                continue
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                if int(ppad[xx + 2 + dx, yy + 2 + dy]) == 40:
                    rrp[xx, yy] = 255
                    break
    crop = plate.crop((x, y, x + w, y + h))
    rp, cp, op = ring_img.load(), crop.load(), placed.convert("RGB").load()
    skyish = pale = dark = edge = 0
    bg_lum = _lum(*color)
    for yy in range(h):
        for xx in range(w):
            if int(rp[xx, yy]) < 80:
                continue
            edge += 1
            r, g, b = cp[xx, yy]
            lum = _lum(r, g, b)
            sat = max(r, g, b) - min(r, g, b)
            or_r, og, ob = op[xx, yy]
            if xx < int(w * 0.48) and yy < int(h * 0.55) and ob - or_r >= 10 and ob - og >= 4 and _lum(or_r, og, ob) > 100:
                skyish += 1
            if bg_lum < 90 and lum > 205 and sat < 18:
                pale += 1
            if bg_lum > 190 and lum < 32:
                dark += 1
    ratio = lambda n: round(n / max(edge, 1), 4)
    return {
        "edge_pixels": edge,
        "skyish_ratio": ratio(skyish),
        "pale_ratio": ratio(pale),
        "dark_ratio": ratio(dark),
        "pale_fringe": ratio(pale) > 0.06,
        "dark_fringe": ratio(dark) > 0.06,
        "sky_halo": ratio(skyish) > 0.08,
        "pass": ratio(pale) <= 0.06 and ratio(dark) <= 0.06 and ratio(skyish) <= 0.08,
    }


def spire_preserved(obj: Image.Image) -> dict[str, Any]:
    alpha = obj.split()[-1]
    w, h = obj.size
    top = alpha.crop((0, 0, w, max(8, int(h * 0.18))))
    bbox = top.getbbox()
    coverage = 0.0
    if bbox is not None:
        coverage = sum(top.getdata()) / (255.0 * top.size[0] * top.size[1])
    # A destroyed finial collapses to a stub: coverage near 0 or a wide blob.
    width_ratio = 0.0
    if bbox is not None:
        width_ratio = (bbox[2] - bbox[0]) / max(w, 1)
    preserved = coverage > 0.012 and width_ratio < 0.55
    return {"coverage": round(coverage, 4), "width_ratio": round(width_ratio, 4), "preserved": preserved}
