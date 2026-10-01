"""Phase 11.7 finish pass — same Day_003 object, same field, no new concept.

Fixes isolation halo, paper occlusion/grounding, and commercial rhythm.
Does not AI-redraw architecture. Does not regenerate the field unless
the caller requests it (this pass retains the 11.6 field).
"""

from __future__ import annotations

import io
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from investhome_api.services.creative_director.phase5_photo_foundation import apply_photographic_grade
from investhome_api.services.creative_director.phase11_6_strategy import DAY003_ASSET_ID, DAY003_FILENAME
from investhome_api.services.creative_director.project_architecture_lock import derive_architecture_mask

CROP_BOX = {"left": 0.39, "top": 0.00, "width": 0.46, "height": 0.80}
GRADE = {"warmth": 0.12, "contrast": 1.06, "brightness": 0.84, "vignette": 0.14}


def _is_sky(r: int, g: int, b: int, yn: float) -> bool:
    lum = int(0.2126 * r + 0.7152 * g + 0.0722 * b)
    sat = max(r, g, b) - min(r, g, b)
    if b >= r + 6 and b >= g + 3 and lum > 108:
        return True
    if yn < 0.70 and lum > 148 and sat < 36:
        return True
    if lum > 200 and sat < 22:
        return True
    if yn < 0.42 and b > r + 2 and lum > 96 and sat < 48:
        return True
    return False


def _kill_edge_fringe(rgba: Image.Image) -> Image.Image:
    """Drop pale/cyan halo pixels on the silhouette. Does not invent architecture."""
    w, h = rgba.size
    rp, gp2, bp, ap = rgba.split()
    rpx, gpx, bpx, apx = rp.load(), gp2.load(), bp.load(), ap.load()
    for y in range(h):
        yn = y / max(h - 1, 1)
        for x in range(w):
            aa = int(apx[x, y])
            if aa == 0:
                continue
            rr, gg, bb = int(rpx[x, y]), int(gpx[x, y]), int(bpx[x, y])
            if _is_sky(rr, gg, bb, yn):
                apx[x, y] = 0
                continue
            edge = False
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1)):
                nx, ny = x + dx, y + dy
                if nx < 0 or ny < 0 or nx >= w or ny >= h or int(apx[nx, ny]) < 12:
                    edge = True
                    break
            if not edge:
                continue
            lum = 0.2126 * rr + 0.7152 * gg + 0.0722 * bb
            sat = max(rr, gg, bb) - min(rr, gg, bb)
            if lum > 158 and sat < 44:
                apx[x, y] = 0
            elif bb >= rr + 3 and lum > 88:
                apx[x, y] = 0
            elif aa < 90:
                apx[x, y] = 0
    rgba.putalpha(ap)
    return rgba


def feather_object_feet(obj: Image.Image, fraction: float = 0.16) -> Image.Image:
    """Dissolve the hard crop into the paper instead of leaving a sticker edge."""
    out = obj.convert("RGBA")
    alpha = out.split()[-1]
    w, h = out.size
    fade_h = max(8, int(h * fraction))
    px = alpha.load()
    for y in range(h - fade_h, h):
        t = (h - 1 - y) / max(fade_h - 1, 1)
        gain = t * t
        for x in range(w):
            px[x, y] = int(px[x, y] * gain)
    out.putalpha(alpha)
    return out


def crop_project_window(source: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    sw, sh = source.size
    left = int(sw * float(CROP_BOX["left"]))
    top = int(sh * float(CROP_BOX["top"]))
    width = max(1, int(sw * float(CROP_BOX["width"])))
    height = max(1, int(sh * float(CROP_BOX["height"])))
    left = min(max(0, left), max(0, sw - width))
    top = min(max(0, top), max(0, sh - height))
    window = source.crop((left, top, left + width, top + height))
    return window, {"crop_box": dict(CROP_BOX), "source_size": [sw, sh], "window_size": list(window.size)}


def isolate_project_object_r1(source: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    """Same source photograph. Erode fringe instead of blurring a halo."""
    window, crop_meta = crop_project_window(source.convert("RGB"))
    graded = apply_photographic_grade(window, GRADE)
    protect = derive_architecture_mask(graded).convert("L")
    w, h = graded.size
    gp, pp = graded.load(), protect.load()
    for y in range(h):
        yn = y / max(h - 1, 1)
        for x in range(w):
            r, g, b = gp[x, y]
            if _is_sky(r, g, b, yn):
                pp[x, y] = 0
    binary = protect.point(lambda v: 255 if v > 56 else 0)
    # Do not dilate after sky punch — that re-closes spire lancets and grows halo.
    core = binary.filter(ImageFilter.MinFilter(3))
    alpha = core.filter(ImageFilter.GaussianBlur(radius=0.45))
    rgba = graded.convert("RGBA")
    rgba.putalpha(alpha)
    rgba = _kill_edge_fringe(rgba)
    bbox = rgba.split()[-1].getbbox()
    if bbox is None:
        raise RuntimeError("Phase 11.7 failed to isolate Day_003")
    x0, y0, x1, y1 = bbox
    x0, y0 = max(0, x0 - 1), max(0, y0 - 1)
    x1, y1 = min(w, x1 + 1), min(h, y1 + 1)
    obj = feather_object_feet(rgba.crop((x0, y0, x1, y1)))
    meta = {
        "filename": DAY003_FILENAME,
        "asset_id": DAY003_ASSET_ID,
        "crop": crop_meta,
        "object_size": list(obj.size),
        "generated_architecture_pixels": 0,
        "method": "architecture_mask_sky_punch_erode_defringe_feet_feather",
        "halo_blur_radius": 0.45,
        "dilate_after_sky_punch": False,
    }
    return obj, meta


def paper_mask(field: Image.Image) -> Image.Image:
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
    mask = mask.filter(ImageFilter.MaxFilter(11)).filter(ImageFilter.MinFilter(7))
    mask = mask.filter(ImageFilter.GaussianBlur(radius=1.2))
    return mask


def paper_overlay(field: Image.Image, mask: Image.Image) -> Image.Image:
    rgba = field.convert("RGBA")
    rgba.putalpha(mask.convert("L"))
    return rgba


def paper_bbox(mask: Image.Image) -> tuple[int, int, int, int]:
    hard = mask.point(lambda v: 255 if v > 140 else 0)
    box = hard.getbbox()
    if box is None:
        w, h = mask.size
        return int(w * 0.18), int(h * 0.62), int(w * 0.82), int(h * 0.92)
    return box


def object_layout_r1(obj: Image.Image, paper: tuple[int, int, int, int], canvas: tuple[int, int]) -> dict[str, int]:
    W, H = canvas
    px0, py0, px1, py1 = paper
    target_h = max(int(H * 0.56), min(int(H * 0.66), int((py1 - py0) * 1.15)))
    scale = target_h / max(obj.size[1], 1)
    ow = max(1, int(obj.size[0] * scale))
    oh = max(1, int(obj.size[1] * scale))
    if ow > int(W * 0.80):
        scale = (W * 0.80) / max(obj.size[0], 1)
        ow = max(1, int(obj.size[0] * scale))
        oh = max(1, int(obj.size[1] * scale))
    x = (W - ow) // 2
    # About a third of the mass sits in the vellum so paper can occlude the feet.
    y = py0 - int(oh * 0.66)
    y = max(int(H * 0.05), min(y, int(H * 0.12)))
    return {"x": x, "y": y, "w": ow, "h": oh}


def contact_on_paper(
    obj: Image.Image,
    layout: dict[str, int],
    paper: Image.Image,
    canvas: tuple[int, int],
) -> Image.Image:
    """Soft contact only where the object meets the paper. Not a full-silhouette drop shadow."""
    W, H = canvas
    placed = obj.resize((layout["w"], layout["h"]), Image.Resampling.LANCZOS)
    alpha = placed.split()[-1]
    stamp = Image.new("L", (W, H), 0)
    # Field light is upper-left: contact falls slightly down and right.
    stamp.paste(alpha, (layout["x"] + 6, layout["y"] + 12))
    stamp = stamp.filter(ImageFilter.GaussianBlur(radius=9))
    stamp = ImageChops.multiply(stamp, paper.point(lambda v: min(255, int(v * 1.1))))
    stamp = stamp.point(lambda v: int(v * 0.34))
    dark = Image.new("RGBA", (W, H), (18, 14, 10, 0))
    dark.putalpha(stamp)
    return dark


def feet_occlusion_overlay(
    field: Image.Image,
    paper: Image.Image,
    layout: dict[str, int],
) -> Image.Image:
    """Recomposite field paper only over the object's lower contact — not over the printed offer."""
    W, H = field.size
    band = Image.new("L", (W, H), 0)
    y0 = max(0, layout["y"] + int(layout["h"] * 0.58))
    ImageDraw.Draw(band).rectangle((0, y0, W, H), fill=255)
    mask = ImageChops.multiply(paper, band)
    return paper_overlay(field, mask)


def hybrid_layers(field: Image.Image, obj: Image.Image) -> dict[str, Any]:
    W, H = field.size
    pmask = paper_mask(field)
    pbbox = paper_bbox(pmask)
    layout = object_layout_r1(obj, pbbox, (W, H))
    placed = obj.resize((layout["w"], layout["h"]), Image.Resampling.LANCZOS)
    overlay = feet_occlusion_overlay(field, pmask, layout)
    contact = contact_on_paper(obj, layout, pmask, (W, H))
    plate = field.convert("RGBA")
    plate.paste(placed, (layout["x"], layout["y"]), placed)
    plate = Image.alpha_composite(plate, overlay)
    plate = Image.alpha_composite(plate, contact)
    return {
        "fused": plate.convert("RGB"),
        "placed": placed,
        "overlay": overlay,
        "contact": contact,
        "layout": layout,
        "paper_bbox": list(pbbox),
        "paper_coverage": round(sum(pmask.getdata()) / (255.0 * W * H), 4),
        "occlusion": "field_paper_recomposited_over_object_feet",
        "field_retained": True,
    }


def fuse_object_into_field(
    field: Image.Image,
    obj: Image.Image,
) -> tuple[Image.Image, dict[str, Any]]:
    layers = hybrid_layers(field, obj)
    meta = {
        "layout": layers["layout"],
        "paper_bbox": layers["paper_bbox"],
        "paper_coverage": layers["paper_coverage"],
        "occlusion": layers["occlusion"],
        "field_retained": True,
    }
    return layers["fused"], meta
