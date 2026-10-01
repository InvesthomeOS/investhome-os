"""Prepare a 4:5 protected Temple source and an official edits mask."""

from __future__ import annotations

import io
from typing import Any

from PIL import Image, ImageFilter, ImageOps

from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.project_architecture_lock import derive_architecture_mask

W, H = CANVAS_4X5


def fit_source_4x5(source: Image.Image, *, centering: tuple[float, float]) -> Image.Image:
    return ImageOps.fit(
        source.convert("RGB"),
        (W, H),
        method=Image.Resampling.LANCZOS,
        centering=centering,
    )


def architecture_preserve_mask(fitted: Image.Image) -> Image.Image:
    """L mask: 255 = architecture (preserve), 0 = editable field."""
    raw = derive_architecture_mask(fitted).convert("L")
    # Over-preserve: dilate so windows/spire are not accidentally editable.
    protected = raw.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MaxFilter(5))
    return protected.point(lambda v: 255 if v > 110 else 0)


def encode_edits_mask(protected: Image.Image) -> bytes:
    """PNG RGBA. Opaque architecture = preserve. Transparent = edit."""
    alpha = protected.convert("L")
    rgba = Image.merge(
        "RGBA",
        (
            Image.new("L", alpha.size, 0),
            Image.new("L", alpha.size, 0),
            Image.new("L", alpha.size, 0),
            alpha,
        ),
    )
    buf = io.BytesIO()
    rgba.save(buf, format="PNG")
    return buf.getvalue()


def encode_png(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


def source_pack(fitted: Image.Image) -> dict[str, Any]:
    protected = architecture_preserve_mask(fitted)
    coverage = sum(protected.getdata()) / (255.0 * protected.size[0] * protected.size[1])
    return {
        "fitted": fitted,
        "protected": protected,
        "mask_bytes": encode_edits_mask(protected),
        "source_bytes": encode_png(fitted),
        "coverage": round(coverage, 4),
        "canvas": [W, H],
    }


def mask_preview(fitted: Image.Image, protected: Image.Image) -> Image.Image:
    rgb = fitted.convert("RGB")
    overlay = Image.new("RGB", rgb.size, (180, 40, 40))
    vis = Image.blend(rgb, overlay, 0.35)
    vis.paste(rgb, (0, 0), protected.point(lambda v: 180 if v > 128 else 0))
    return vis
