"""Overlay real ML/Drive logo files onto a GPT Image result. Never invent marks."""

from __future__ import annotations

import io
import logging

from PIL import Image

from investhome_api.services.gpt_image_design.source import ResolvedSourceImage

logger = logging.getLogger(__name__)


def _fit_logo(logo: Image.Image, box_w: int, box_h: int) -> Image.Image:
    src = logo.convert("RGBA")
    src.thumbnail((max(1, box_w), max(1, box_h)), Image.Resampling.LANCZOS)
    return src


def overlay_brand_lockups(
    base_bytes: bytes,
    logos: list[ResolvedSourceImage],
) -> bytes:
    """Composite real project + Investhome logos onto the generated ad.

    GPT Image edits receive only the architecture photo. Lockups are applied here
    so the model cannot redraw or substitute wordmarks.
    """
    if not logos:
        return base_bytes
    try:
        with Image.open(io.BytesIO(base_bytes)) as raw:
            canvas = raw.convert("RGBA")
    except Exception:
        logger.info("gpt_image_logo_overlay_skip reason=base_unreadable")
        return base_bytes

    width, height = canvas.size
    margin_x = max(16, int(round(width * 0.045)))
    margin_y = max(16, int(round(height * 0.04)))
    project_box = (max(120, int(round(width * 0.22))), max(36, int(round(height * 0.055))))
    ih_box = (max(88, int(round(width * 0.12))), max(28, int(round(height * 0.032))))

    project = next((row for row in logos if row.role == "project_logo"), None)
    supporting = next((row for row in logos if row.role == "investhome_logo"), None)
    if project is None and logos:
        project = logos[0]
    if supporting is None and len(logos) > 1:
        supporting = next((row for row in logos[1:] if row.asset_id != project.asset_id), None)

    composed = False
    if project is not None:
        try:
            with Image.open(io.BytesIO(project.image_bytes)) as logo_im:
                fitted = _fit_logo(logo_im, *project_box)
            canvas.alpha_composite(fitted, (margin_x, margin_y))
            composed = True
        except Exception:
            logger.info(
                "gpt_image_logo_overlay_skip role=project_logo asset_id=%s",
                project.asset_id,
            )

    if supporting is not None:
        try:
            with Image.open(io.BytesIO(supporting.image_bytes)) as logo_im:
                fitted = _fit_logo(logo_im, *ih_box)
            x = width - margin_x - fitted.width
            y = margin_y
            canvas.alpha_composite(fitted, (max(0, x), y))
            composed = True
        except Exception:
            logger.info(
                "gpt_image_logo_overlay_skip role=investhome_logo asset_id=%s",
                supporting.asset_id,
            )

    if not composed:
        return base_bytes

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    logger.info(
        "gpt_image_logo_overlay_ok project_logo=%s investhome_logo=%s",
        str(project.asset_id) if project is not None else None,
        str(supporting.asset_id) if supporting is not None else None,
    )
    return buf.getvalue()
