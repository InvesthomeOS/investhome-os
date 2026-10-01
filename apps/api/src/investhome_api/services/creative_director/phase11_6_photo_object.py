"""Isolate a real Temple photograph as a compositional object. Never regenerate architecture."""

from __future__ import annotations

import io
from typing import Any

from PIL import Image, ImageDraw, ImageFilter

from investhome_api.services.creative_director.phase5_photo_foundation import apply_photographic_grade
from investhome_api.services.creative_director.phase11_6_strategy import DAY003_ASSET_ID, DAY003_FILENAME
from investhome_api.services.creative_director.project_architecture_lock import derive_architecture_mask

# Tight window on Day_003: Temple spire + project mass. Drop the right-hand city block.
CROP_BOX = {"left": 0.38, "top": 0.00, "width": 0.48, "height": 0.72}
GRADE = {"warmth": 0.06, "contrast": 1.10, "brightness": 0.98, "vignette": 0.04}


def _png(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


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


def isolate_project_object(source: Image.Image) -> tuple[Image.Image, Image.Image, dict[str, Any]]:
    """Return RGBA object (transparent around architecture) plus RGB crop for provenance."""
    window, crop_meta = crop_project_window(source.convert("RGB"))
    graded = apply_photographic_grade(window, GRADE)
    protect = derive_architecture_mask(graded).convert("L")
    w, h = graded.size
    gp = graded.load()
    pp = protect.load()
    # Punch photographic sky: pale low-sat upper pixels are not the Temple object.
    for y in range(h):
        yn = y / max(h - 1, 1)
        for x in range(w):
            r, g, b = gp[x, y]
            mx, mn = max(r, g, b), min(r, g, b)
            sat = mx - mn
            lum = int(0.2126 * r + 0.7152 * g + 0.0722 * b)
            sky = (b >= r + 8 and b >= g + 4 and lum > 118) or (yn < 0.62 and lum > 150 and sat < 38)
            if sky:
                pp[x, y] = 0
            if yn > 0.86 and lum < 96:
                pp[x, y] = min(int(pp[x, y]), 28)
    protect = protect.point(lambda v: 255 if v > 48 else 0)
    protect = protect.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(3))
    protect = protect.filter(ImageFilter.GaussianBlur(radius=2.2))
    alpha = protect.point(lambda v: min(255, int(v * 1.05)))
    rgba = graded.convert("RGBA")
    rgba.putalpha(alpha)
    bbox = alpha.getbbox()
    if bbox is None:
        raise RuntimeError("Phase 11.6 failed to isolate a Temple object from Day_003")
    pad = 12
    x0, y0, x1, y1 = bbox
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(w, x1 + pad), min(h, y1 + pad)
    obj = rgba.crop((x0, y0, x1, y1))
    coverage = sum(alpha.getdata()) / (255.0 * w * h)
    meta = {
        "filename": DAY003_FILENAME,
        "asset_id": DAY003_ASSET_ID,
        "crop": crop_meta,
        "object_size": list(obj.size),
        "alpha_coverage_in_window": round(coverage, 4),
        "bbox": [x0, y0, x1, y1],
        "generated_architecture_pixels": 0,
        "method": "architecture_mask_plus_sky_punch_plus_feather",
        "transformations": ("crop", "grade", "mask", "isolate", "feather"),
    }
    return obj, graded, meta


def object_on_checker(obj: Image.Image, size: tuple[int, int] = (1088, 1360)) -> Image.Image:
    canvas = Image.new("RGB", size, (36, 34, 32))
    draw = ImageDraw.Draw(canvas)
    cell = 28
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            if ((x // cell) + (y // cell)) % 2 == 0:
                draw.rectangle((x, y, x + cell, y + cell), fill=(48, 46, 44))
    fitted = obj.copy()
    fitted.thumbnail((int(size[0] * 0.78), int(size[1] * 0.86)), Image.Resampling.LANCZOS)
    x = (size[0] - fitted.size[0]) // 2
    y = (size[1] - fitted.size[1]) // 2
    canvas.paste(fitted, (x, y), fitted)
    return canvas
