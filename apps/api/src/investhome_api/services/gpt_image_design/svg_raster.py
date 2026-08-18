"""Minimal SVG → PNG rasterization for real brand logos. Never AI-redrawn."""

from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)


def svg_bytes_to_png(svg_bytes: bytes, *, max_side: int = 1024) -> bytes | None:
    """Rasterize a real SVG logo for composition. Never redraw via AI."""
    if not svg_bytes:
        return None
    try:
        import cairosvg  # type: ignore[import-untyped]
    except Exception:
        cairosvg = None
    if cairosvg is not None:
        try:
            return cairosvg.svg2png(
                bytestring=svg_bytes,
                output_width=max_side,
                output_height=max_side,
            )
        except Exception as exc:
            logger.info("gpt_image_svg_cairosvg_failed err=%s", type(exc).__name__)

    try:
        from reportlab.graphics import renderPM
        from svglib.svglib import svg2rlg
    except Exception:
        logger.info("gpt_image_svg_deps_missing")
        return None
    try:
        drawing = svg2rlg(io.BytesIO(svg_bytes))
        if drawing is None:
            return None
        w = float(getattr(drawing, "width", 0) or 0) or float(max_side)
        h = float(getattr(drawing, "height", 0) or 0) or float(max_side)
        scale = min(max_side / max(w, 1.0), max_side / max(h, 1.0), 1.0)
        if scale != 1.0:
            drawing.width = w * scale
            drawing.height = h * scale
            drawing.scale(scale, scale)
        return renderPM.drawToString(drawing, fmt="PNG")
    except Exception as exc:
        logger.info("gpt_image_svg_svglib_failed err=%s", type(exc).__name__)
        return None
