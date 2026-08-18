"""OS Final Composition Layer over GPT Image — real logos + exact text. Never invent marks."""

from __future__ import annotations

import io
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

from PIL import Image, ImageDraw, ImageFont

from investhome_api.services.gpt_image_design.brief import INVESHOME_SLOGAN
from investhome_api.services.gpt_image_design.source import ResolvedSourceImage
from investhome_api.services.gpt_image_design.svg_raster import svg_bytes_to_png

# Re-export for tests / callers
__all__ = [
    "CompositionResult",
    "CompositionSlotPlan",
    "build_slot_plan",
    "compose_final_layers",
    "logo_to_rgba",
    "overlay_brand_lockups",
    "resolve_turkish_font",
    "svg_bytes_to_png",
]

logger = logging.getLogger(__name__)

# Prefer OS/container fonts that cover Turkish (çÇğĞıİöÖşŞüÜ). Not a new brand typeface.
_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/calibri.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
)


@dataclass
class CompositionSlotPlan:
    """Art-director-selected slots only — empty strings are omitted."""

    headline: str = ""
    subhead: str = ""
    verified_data: str = ""
    cta: str = ""
    include_slogan: bool = True


@dataclass
class CompositionResult:
    png_bytes: bytes
    layers: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    used_slots: list[str] = field(default_factory=list)


def logo_to_rgba(payload: bytes, filename: str, content_type: str) -> Image.Image | None:
    """Open a real logo file (SVG or raster) as RGBA for alpha_composite."""
    ctype = (content_type or "").split(";")[0].strip().lower()
    lower = (filename or "").lower()
    raw = payload
    if ctype == "image/svg+xml" or lower.endswith(".svg"):
        converted = svg_bytes_to_png(payload)
        if converted is None:
            return None
        raw = converted
    try:
        with Image.open(io.BytesIO(raw)) as im:
            return im.convert("RGBA")
    except Exception:
        return None


def resolve_turkish_font(*, bold: bool = False, size: int = 32) -> ImageFont.ImageFont:
    """Load a Turkish-capable system font already available on host/container."""
    env_font = (os.environ.get("GPT_IMAGE_COMPOSE_FONT") or "").strip()
    ordered: list[str] = []
    if env_font:
        ordered.append(env_font)
    # Prefer bold candidates when requested.
    if bold:
        ordered.extend(
            [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "C:/Windows/Fonts/arialbd.ttf",
                "C:/Windows/Fonts/segoeuib.ttf",
                "C:/Windows/Fonts/calibrib.ttf",
            ]
        )
    ordered.extend(_FONT_CANDIDATES)
    seen: set[str] = set()
    for path in ordered:
        if not path or path in seen:
            continue
        seen.add(path)
        if not Path(path).is_file():
            continue
        try:
            return ImageFont.truetype(path, size=max(8, int(size)))
        except Exception:
            continue
    return ImageFont.load_default()


def _fit_logo(logo: Image.Image, box_w: int, box_h: int) -> Image.Image:
    src = logo.convert("RGBA")
    src.thumbnail((max(1, box_w), max(1, box_h)), Image.Resampling.LANCZOS)
    return src


def _wrap_text(text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = (text or "").split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        bbox = font.getbbox(trial)
        if (bbox[2] - bbox[0]) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _draw_text_block(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    font: ImageFont.ImageFont,
    x: int,
    y: int,
    max_width: int,
    fill: tuple[int, int, int, int] = (255, 255, 255, 255),
    align: str = "left",
    line_gap: float = 1.2,
) -> tuple[int, int]:
    """Draw wrapped text; returns (width, height) of the block."""
    lines = _wrap_text(text, font, max_width)
    if not lines:
        return 0, 0
    sample = font.getbbox("Ay")
    line_h = max(1, int(round((sample[3] - sample[1]) * line_gap)))
    max_w = 0
    for i, line in enumerate(lines):
        bbox = font.getbbox(line)
        lw = bbox[2] - bbox[0]
        max_w = max(max_w, lw)
        if align == "center":
            lx = x + max(0, (max_width - lw) // 2)
        elif align == "right":
            lx = x + max(0, max_width - lw)
        else:
            lx = x
        draw.text((lx, y + i * line_h), line, font=font, fill=fill)
    return max_w, line_h * len(lines)


def build_slot_plan(
    *,
    visible_copy: dict[str, Any] | None,
    verified_lines: list[str] | None = None,
    include_slogan: bool = True,
) -> CompositionSlotPlan:
    copy = visible_copy or {}
    headline = str(copy.get("headline") or "").strip()
    subhead = str(copy.get("supporting") or copy.get("subhead") or "").strip()
    if not subhead:
        subhead = str(copy.get("eyebrow") or "").strip()
    cta = str(copy.get("cta") or "").strip()
    verified = ""
    for line in verified_lines or []:
        text = (line or "").strip()
        if text:
            verified = text
            break
    return CompositionSlotPlan(
        headline=headline,
        subhead=subhead,
        verified_data=verified,
        cta=cta,
        include_slogan=include_slogan,
    )


def compose_final_layers(
    base_bytes: bytes,
    *,
    logos: list[ResolvedSourceImage],
    slots: CompositionSlotPlan,
    canvas_width: int | None = None,
    canvas_height: int | None = None,
    base_asset_id: UUID | None = None,
    composed_asset_id: UUID | None = None,
) -> CompositionResult:
    """Composite real logos + OS text onto the GPT Image visual. Returns PNG + SMB layers."""
    warnings: list[str] = []
    used: list[str] = []
    try:
        with Image.open(io.BytesIO(base_bytes)) as raw:
            canvas = raw.convert("RGBA")
    except Exception:
        warnings.append("composition_base_unreadable")
        return CompositionResult(png_bytes=base_bytes, warnings=warnings)

    width, height = canvas.size
    if canvas_width and canvas_width > 0:
        width = canvas_width
    if canvas_height and canvas_height > 0:
        height = canvas_height
    if canvas.size != (width, height):
        canvas = canvas.resize((width, height), Image.Resampling.LANCZOS)

    margin_x = max(24, int(round(width * 0.055)))
    margin_y = max(24, int(round(height * 0.045)))
    project_box = (max(140, int(round(width * 0.24))), max(40, int(round(height * 0.06))))
    ih_box = (max(96, int(round(width * 0.14))), max(32, int(round(height * 0.036))))
    text_width = max(120, width - margin_x * 2)

    project = next((row for row in logos if row.role == "project_logo"), None)
    supporting = next((row for row in logos if row.role == "investhome_logo"), None)

    layers: list[dict[str, Any]] = []
    # Cover/background is the GPT visual (set via composition_base_asset_id on the response).
    # Layers are editable logos + text only — same contract as Native Art Director.

    draw = ImageDraw.Draw(canvas)

    if project is not None:
        logo_im = logo_to_rgba(project.image_bytes, project.filename, project.content_type)
        if logo_im is None:
            warnings.append(f"project_logo_unreadable:{project.filename}")
        else:
            fitted = _fit_logo(logo_im, *project_box)
            pos = (margin_x, margin_y)
            canvas.alpha_composite(fitted, pos)
            layers.append(
                {
                    "id": "logo-project",
                    "type": "IMAGE",
                    "role": "logo",
                    "assetId": str(project.asset_id),
                    "x": pos[0],
                    "y": pos[1],
                    "width": fitted.width,
                    "height": fitted.height,
                    "zIndex": 8,
                }
            )
            used.append("project_logo")

    # Text stack: HEADLINE → SUBHEAD → OPTIONAL VERIFIED → CTA → slogan / IH logo
    cursor_y = int(round(height * 0.58))
    if slots.headline:
        font = resolve_turkish_font(bold=True, size=max(28, int(round(width * 0.048))))
        _, block_h = _draw_text_block(
            draw,
            text=slots.headline,
            font=font,
            x=margin_x,
            y=cursor_y,
            max_width=text_width,
            align="left",
        )
        layers.append(
            {
                "id": "text-headline",
                "type": "TEXT",
                "role": "headline",
                "content": slots.headline,
                "fontSize": int(getattr(font, "size", 36) or 36),
                "fontWeight": "bold",
                "align": "left",
                "color": "#ffffff",
                "x": margin_x,
                "y": cursor_y,
                "width": text_width,
                "height": max(block_h, 40),
                "zIndex": 5,
            }
        )
        cursor_y += block_h + max(10, int(round(height * 0.012)))
        used.append("headline")

    if slots.subhead:
        font = resolve_turkish_font(bold=False, size=max(16, int(round(width * 0.024))))
        _, block_h = _draw_text_block(
            draw,
            text=slots.subhead,
            font=font,
            x=margin_x,
            y=cursor_y,
            max_width=text_width,
            fill=(235, 235, 235, 255),
            align="left",
        )
        layers.append(
            {
                "id": "text-subhead",
                "type": "TEXT",
                "role": "body",
                "content": slots.subhead,
                "fontSize": int(getattr(font, "size", 20) or 20),
                "fontWeight": "normal",
                "align": "left",
                "color": "#ebebeb",
                "x": margin_x,
                "y": cursor_y,
                "width": text_width,
                "height": max(block_h, 28),
                "zIndex": 5,
            }
        )
        cursor_y += block_h + max(8, int(round(height * 0.01)))
        used.append("subhead")

    if slots.verified_data:
        font = resolve_turkish_font(bold=False, size=max(14, int(round(width * 0.02))))
        _, block_h = _draw_text_block(
            draw,
            text=slots.verified_data,
            font=font,
            x=margin_x,
            y=cursor_y,
            max_width=text_width,
            fill=(220, 220, 220, 255),
            align="left",
        )
        layers.append(
            {
                "id": "text-verified",
                "type": "TEXT",
                "role": "eyebrow",
                "content": slots.verified_data,
                "fontSize": int(getattr(font, "size", 16) or 16),
                "fontWeight": "normal",
                "align": "left",
                "color": "#dcdcdc",
                "x": margin_x,
                "y": cursor_y,
                "width": text_width,
                "height": max(block_h, 24),
                "zIndex": 5,
            }
        )
        cursor_y += block_h + max(10, int(round(height * 0.012)))
        used.append("verified_data")

    if slots.cta:
        font = resolve_turkish_font(bold=True, size=max(14, int(round(width * 0.018))))
        pad_x = max(18, int(round(width * 0.02)))
        pad_y = max(10, int(round(height * 0.01)))
        bbox = font.getbbox(slots.cta)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        btn_w = tw + pad_x * 2
        btn_h = th + pad_y * 2
        btn_x = margin_x
        btn_y = min(cursor_y, height - margin_y - btn_h)
        draw.rounded_rectangle(
            (btn_x, btn_y, btn_x + btn_w, btn_y + btn_h),
            radius=max(6, btn_h // 3),
            fill=(255, 255, 255, 235),
        )
        draw.text(
            (btn_x + pad_x, btn_y + pad_y - 1),
            slots.cta,
            font=font,
            fill=(17, 24, 39, 255),
        )
        layers.append(
            {
                "id": "cta-primary",
                "type": "BUTTON",
                "label": slots.cta,
                "backgroundColor": "#ffffff",
                "textColor": "#111827",
                "x": btn_x,
                "y": btn_y,
                "width": btn_w,
                "height": btn_h,
                "zIndex": 7,
            }
        )
        used.append("cta")

    # Endorsement: real slogan typeset by OS (exact spelling) + IH logo if present.
    endorse_y = max(margin_y, height - margin_y - max(36, int(round(height * 0.04))))
    if slots.include_slogan:
        slogan_font = resolve_turkish_font(bold=False, size=max(12, int(round(width * 0.016))))
        slogan = INVESHOME_SLOGAN
        sb = slogan_font.getbbox(slogan)
        sw = sb[2] - sb[0]
        sx = margin_x
        if supporting is not None:
            # Leave room for IH logo on the right.
            sx = margin_x
        draw.text((sx, endorse_y), slogan, font=slogan_font, fill=(230, 230, 230, 255))
        layers.append(
            {
                "id": "text-slogan",
                "type": "TEXT",
                "role": "brand",
                "content": slogan,
                "fontSize": int(getattr(slogan_font, "size", 14) or 14),
                "fontWeight": "normal",
                "align": "left",
                "color": "#e6e6e6",
                "x": sx,
                "y": endorse_y,
                "width": max(sw, int(round(width * 0.55))),
                "height": max(20, sb[3] - sb[1] + 4),
                "zIndex": 6,
            }
        )
        used.append("slogan")

    if supporting is not None:
        logo_im = logo_to_rgba(supporting.image_bytes, supporting.filename, supporting.content_type)
        if logo_im is None:
            warnings.append(f"investhome_logo_unreadable:{supporting.filename}")
        else:
            fitted = _fit_logo(logo_im, *ih_box)
            x = width - margin_x - fitted.width
            y = endorse_y - max(0, (fitted.height - 20) // 2)
            y = max(margin_y, min(y, height - margin_y - fitted.height))
            canvas.alpha_composite(fitted, (max(0, x), y))
            layers.append(
                {
                    "id": "logo-investhome",
                    "type": "IMAGE",
                    "role": "logo",
                    "assetId": str(supporting.asset_id),
                    "x": max(0, x),
                    "y": y,
                    "width": fitted.width,
                    "height": fitted.height,
                    "zIndex": 8,
                }
            )
            used.append("investhome_logo")

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    png = buf.getvalue()
    logger.info(
        "gpt_image_final_composition_ok used=%s warnings=%s composed_asset=%s",
        used,
        warnings,
        str(composed_asset_id) if composed_asset_id else None,
    )
    return CompositionResult(png_bytes=png, layers=layers, warnings=warnings, used_slots=used)


# Back-compat alias used by older unit tests / callers.
def overlay_brand_lockups(
    base_bytes: bytes,
    logos: list[ResolvedSourceImage],
) -> bytes:
    result = compose_final_layers(
        base_bytes,
        logos=logos,
        slots=CompositionSlotPlan(include_slogan=False),
    )
    return result.png_bytes
