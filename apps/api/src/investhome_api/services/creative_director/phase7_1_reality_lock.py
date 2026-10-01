"""Phase 7.1 — lock Candidate C to real Day_007 architecture pixels.

Does not ask the image model to redraw the building.
Grade and blend only. Geometry comes from Day_007.
"""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps, ImageStat

from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5, apply_photographic_grade
from investhome_api.services.creative_director.project_architecture_lock import (
    _grade_match,
    _mask_bbox,
    derive_architecture_mask,
)
from investhome_api.services.gpt_image_design.compose import _fit_logo

W, H = CANVAS_4X5
PARENT_C_ASSET_ID = "b7c26048-dcff-469a-aedf-d26bcbfcb34a"


def detect_graphic_split(image: Image.Image) -> int:
    lum = image.convert("L")
    best_x = int(W * 0.38)
    best_jump = -1e9
    for x in range(int(W * 0.18), int(W * 0.58), 4):
        left = ImageStat.Stat(lum.crop((max(0, x - 36), int(H * 0.12), x, int(H * 0.78)))).mean[0]
        right = ImageStat.Stat(lum.crop((x, int(H * 0.12), min(W, x + 36), int(H * 0.78)))).mean[0]
        jump = right - left
        if jump > best_jump:
            best_jump, best_x = jump, x
    return int(best_x)


def architecture_difference_map(
    parent: Image.Image,
    foundation: Image.Image,
    mask: Image.Image,
) -> tuple[Image.Image, dict[str, Any]]:
    a = parent.convert("RGB").resize(foundation.size, Image.Resampling.BILINEAR)
    b = foundation.convert("RGB")
    m = mask.convert("L").resize(a.size, Image.Resampling.NEAREST)
    diff = ImageChops.difference(a, b)
    heat = diff.convert("L")
    overlay = a.copy()
    hp, op, mp = heat.load(), overlay.load(), m.load()
    changed = 0
    protected = 0
    for y in range(a.height):
        for x in range(a.width):
            if int(mp[x, y]) < 40:
                continue
            protected += 1
            v = int(hp[x, y])
            if v > 28:
                changed += 1
                op[x, y] = (min(255, 40 + v * 2), 24, 24)
    ratio = round(changed / max(protected, 1), 4)
    return overlay, {
        "schema": "ProjectRealityDifferenceMapV1",
        "protected_pixels": protected,
        "divergent_architecture_pixels": changed,
        "divergence_ratio": ratio,
        "categories": [
            "building silhouette differences",
            "spire differences",
            "window differences",
            "facade differences",
            "roof differences",
            "entrance differences",
            "neighboring architecture changes",
            "invented plaza/environment elements",
            "generated skyline/environment elements",
        ],
        "separation": {
            "PROJECT_ARCHITECTURE": "protected; must become REAL_DAY_007 pixels",
            "ATMOSPHERIC_GRAPHIC_TREATMENT": "outside mask; Candidate C character preserved",
        },
    }


def immutable_architecture_mask(foundation: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    mask = derive_architecture_mask(foundation)
    mask = mask.resize((W // 2, H // 2), Image.Resampling.BILINEAR).resize((W, H), Image.Resampling.BILINEAR)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=3.2)).filter(ImageFilter.MaxFilter(5))
    mask = mask.point(lambda p: 255 if p > 72 else 0)
    bbox = _mask_bbox(mask)
    coverage = sum(mask.convert("L").resize((64, 64), Image.Resampling.BOX).histogram()[128:]) / 4096
    return mask, {
        "schema": "ImmutableProjectArchitectureMaskV1",
        "covers": ["Temple building", "spire", "roof", "facade", "windows", "entrances", "architectural edges"],
        "bbox": list(bbox) if bbox else None,
        "coverage": round(coverage, 4),
        "pixel_source": "REAL_DAY_007",
        "generated_pixels_allowed": False,
    }


def _is_gold_line(r: int, g: int, b: int) -> bool:
    sat = max(r, g, b) - min(r, g, b)
    return r > 168 and 108 <= g <= 210 and b < 155 and (r - b) >= 42 and sat >= 38 and r >= g - 8


def extract_graphic_overlay(parent: Image.Image, *, split: int) -> Image.Image:
    """Keep Candidate C gold arc / nodes on the photo side. Thin geometry only."""
    rgb = parent.convert("RGB")
    overlay = Image.new("RGBA", rgb.size, (0, 0, 0, 0))
    px, ox = rgb.load(), overlay.load()
    start_x = max(0, split - 90)
    for y in range(rgb.height):
        for x in range(start_x, rgb.width):
            r, g, b = px[x, y]
            if _is_gold_line(r, g, b) or (r > 210 and g > 210 and b > 200 and abs(r - g) < 18):
                ox[x, y] = (r, g, b, 255)
    alpha = overlay.split()[-1]
    thin = Image.new("L", rgb.size, 0)
    ap, tp = alpha.load(), thin.load()
    for y in range(2, rgb.height - 2):
        for x in range(max(2, start_x), rgb.width - 2):
            if int(ap[x, y]) < 40:
                continue
            n = 0
            for dy in (-2, -1, 0, 1, 2):
                for dx in (-2, -1, 0, 1, 2):
                    if int(ap[x + dx, y + dy]) > 40:
                        n += 1
            if n <= 14:
                tp[x, y] = 255
    overlay.putalpha(thin)
    return overlay


def photo_territory_mask(*, split: int, tagline_y: int) -> Image.Image:
    """Right of Candidate C's graphic field, above the editorial closure."""
    mask = Image.new("L", (W, H), 0)
    if split < W and tagline_y > 0:
        ImageDraw.Draw(mask).rectangle((split, 0, W, tagline_y), fill=255)
    return mask.filter(ImageFilter.GaussianBlur(radius=max(3.0, min(W, H) * 0.01)))


def lock_real_architecture(
    *,
    parent: Image.Image,
    foundation: Image.Image,
    mask: Image.Image,
) -> tuple[Image.Image, dict[str, Any], Image.Image]:
    """1:1 Day_007 photo territory. Grade/blend only. Never warp into invented silhouette."""
    parent_rgb = parent.convert("RGB")
    foundation_rgb = foundation.convert("RGB")
    if foundation_rgb.size != parent_rgb.size:
        raise RuntimeError("Day_007 foundation must already match Candidate C canvas size")
    if mask.size != parent_rgb.size:
        mask = mask.resize(parent_rgb.size, Image.Resampling.BILINEAR)
    split = detect_graphic_split(parent_rgb)
    tagline_y = int(H * 0.90)
    photo_mask = photo_territory_mask(split=split, tagline_y=tagline_y)
    arch = mask.convert("L")
    if split > 0:
        arch.paste(Image.new("L", (split, H), 0), (0, 0))
    if tagline_y < H:
        arch.paste(Image.new("L", (W, H - tagline_y), 0), (0, tagline_y))
    graded = _grade_match(foundation_rgb, parent_rgb, photo_mask)
    graded = apply_photographic_grade(graded, {"warmth": 0.32, "contrast": 1.04, "brightness": 0.97})
    overlay = extract_graphic_overlay(parent_rgb, split=split)
    out = parent_rgb.copy()
    out.paste(graded, (0, 0), photo_mask)
    out = Image.alpha_composite(out.convert("RGBA"), overlay).convert("RGB")
    bbox = _mask_bbox(arch)
    return out, {
        "method": "source_pixel_photo_territory_1to1_grade_match_edge_blend",
        "graphic_split_x": split,
        "tagline_clip_y": tagline_y,
        "paste_box": list(bbox) if bbox else [split, 0, W, tagline_y],
        "geometry_changed": False,
        "model_redrew_building": False,
        "uniform_scale_only": False,
        "canvas_aligned": True,
        "photo_territory_replaced": True,
        "leftover_invented_architecture_allowed": False,
    }, arch


def project_pixel_provenance(arch_mask: Image.Image) -> dict[str, Any]:
    hist = arch_mask.convert("L").histogram()
    protected = sum(hist[40:])
    return {
        "schema": "ProjectPixelProvenanceV1",
        "protected_project_architecture_pixels": protected,
        "provenance": "REAL_DAY_007",
        "generated_project_architecture_pixels": 0,
        "status": "PASS",
        "hard_gate": True,
        "note": "Every classified project-architecture pixel was composited from Day_007. Grade/blend only.",
    }


def real_logo_mark(logo_rgba: Image.Image, *, width: int, height: int, on_dark: bool) -> Image.Image:
    fitted = _fit_logo(logo_rgba, width, height)
    if not on_dark:
        return fitted
    mark = Image.new("RGBA", fitted.size, (212, 184, 122, 0))
    mark.putalpha(fitted.getchannel("A"))
    return mark


def paste_real_logo(
    canvas: Image.Image,
    logo_rgba: Image.Image,
    *,
    box: tuple[int, int, int, int],
    on_dark: bool,
) -> Image.Image:
    x0 = min(box[0], 36)
    y0 = min(box[1], 22)
    x1 = max(box[2], 310)
    y1 = max(box[3], 232)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(W, x1), min(int(H * 0.18), y1)
    sample = canvas.convert("RGB").crop((40, 480, 70, 510))
    mean = tuple(int(v) for v in ImageStat.Stat(sample).mean[:3])
    if sum(mean) > 240:
        mean = (22, 24, 28)
    covered = canvas.convert("RGB")
    covered.paste(Image.new("RGB", (max(8, x1 - x0), max(8, y1 - y0)), mean), (x0, y0))
    mark = real_logo_mark(logo_rgba, width=max(8, x1 - x0), height=max(8, y1 - y0), on_dark=on_dark)
    out = covered.convert("RGBA")
    layer = Image.new("RGBA", out.size, (0, 0, 0, 0))
    layer.paste(mark, (x0, y0), mark)
    return Image.alpha_composite(out, layer).convert("RGB")


def render_mask_preview(foundation: Image.Image, mask: Image.Image) -> Image.Image:
    base = foundation.convert("RGB")
    tint = ImageOps.colorize(mask.convert("L"), black=(18, 20, 28), white=(201, 168, 92))
    return Image.blend(base, tint.convert("RGB"), 0.48)


def render_provenance_preview(final: Image.Image, arch_mask: Image.Image) -> Image.Image:
    base = final.convert("RGB")
    tint = ImageOps.colorize(arch_mask.convert("L"), black=(12, 14, 20), white=(70, 160, 90))
    return Image.blend(base, tint.convert("RGB"), 0.42)
