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
from investhome_api.services.gpt_image_design.design_plan import (
    DesignPlanLayer,
    GptImageDesignPlan,
    build_gpt_image_design_plan,
)
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
# Serif maps to Georgia / Liberation Serif / DejaVu Serif — already on host, nearest SMB `serif`.
_SANS_REGULAR = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/calibri.ttf",
)
_SANS_BOLD = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
)
_SERIF_REGULAR = (
    "C:/Windows/Fonts/georgia.ttf",
    "C:/Windows/Fonts/times.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
)
_SERIF_BOLD = (
    "C:/Windows/Fonts/georgiab.ttf",
    "C:/Windows/Fonts/timesbd.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
)
_FONT_CANDIDATES = _SANS_REGULAR + _SANS_BOLD


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


def resolve_turkish_font(
    *,
    bold: bool = False,
    size: int = 32,
    family: str = "sans",
) -> ImageFont.ImageFont:
    """Load a Turkish-capable system font already available on host/container."""
    env_font = (os.environ.get("GPT_IMAGE_COMPOSE_FONT") or "").strip()
    ordered: list[str] = []
    if env_font:
        ordered.append(env_font)
    serif = (family or "sans").strip().lower() == "serif"
    if serif and bold:
        ordered.extend(_SERIF_BOLD)
        ordered.extend(_SERIF_REGULAR)
        ordered.extend(_SANS_BOLD)
    elif serif:
        ordered.extend(_SERIF_REGULAR)
        ordered.extend(_SANS_REGULAR)
    elif bold:
        ordered.extend(_SANS_BOLD)
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


def _hex_rgba(color: str | None, alpha: int = 255) -> tuple[int, int, int, int]:
    raw = (color or "").strip().lstrip("#")
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    if len(raw) != 6:
        return (255, 255, 255, alpha)
    try:
        return (int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16), alpha)
    except ValueError:
        return (255, 255, 255, alpha)


def _slot_text(slots: CompositionSlotPlan, content_slot: str) -> str:
    if content_slot == "headline":
        return slots.headline
    if content_slot == "subhead":
        return slots.subhead
    if content_slot in {"location", "verified", "verified_data"}:
        return slots.verified_data
    if content_slot == "cta":
        return slots.cta
    if content_slot == "slogan":
        return INVESHOME_SLOGAN if slots.include_slogan else ""
    return ""


def _is_bold(weight: str | None) -> bool:
    return (weight or "").lower() in {"bold", "semibold", "700", "600"}


def compose_final_layers(
    base_bytes: bytes,
    *,
    logos: list[ResolvedSourceImage],
    slots: CompositionSlotPlan,
    canvas_width: int | None = None,
    canvas_height: int | None = None,
    base_asset_id: UUID | None = None,
    composed_asset_id: UUID | None = None,
    plan: GptImageDesignPlan | None = None,
) -> CompositionResult:
    """Composite real logos + OS text at Design Plan coordinates. Never a default 600/500 template."""
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

    project = next((row for row in logos if row.role == "project_logo"), None)
    supporting = next((row for row in logos if row.role == "investhome_logo"), None)
    if plan is None:
        plan = build_gpt_image_design_plan(
            canvas_width=width,
            canvas_height=height,
            has_project_logo=project is not None,
            has_investhome_logo=supporting is not None,
            include_slogan=slots.include_slogan,
        )

    layers: list[dict[str, Any]] = []
    draw = ImageDraw.Draw(canvas)

    for spec in plan.layers:
        _compose_plan_layer(
            canvas,
            draw,
            spec=spec,
            slots=slots,
            project=project,
            supporting=supporting,
            layers=layers,
            used=used,
            warnings=warnings,
        )

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    png = buf.getvalue()
    logger.info(
        "gpt_image_final_composition_ok used=%s variation=%s warnings=%s composed_asset=%s",
        used,
        plan.variation,
        warnings,
        str(composed_asset_id) if composed_asset_id else None,
    )
    return CompositionResult(png_bytes=png, layers=layers, warnings=warnings, used_slots=used)


def _compose_plan_layer(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    *,
    spec: DesignPlanLayer,
    slots: CompositionSlotPlan,
    project: ResolvedSourceImage | None,
    supporting: ResolvedSourceImage | None,
    layers: list[dict[str, Any]],
    used: list[str],
    warnings: list[str],
) -> None:
    slot = spec.content_slot
    if spec.type == "IMAGE" and slot in {"project_logo", "investhome_logo"}:
        source = project if slot == "project_logo" else supporting
        if source is None:
            return
        logo_im = logo_to_rgba(source.image_bytes, source.filename, source.content_type)
        if logo_im is None:
            warnings.append(f"{slot}_unreadable:{source.filename}")
            return
        fitted = _fit_logo(logo_im, spec.width, spec.height)
        pos = (spec.x, spec.y)
        canvas.alpha_composite(fitted, pos)
        layers.append(
            {
                "id": spec.id,
                "type": "IMAGE",
                "role": "logo",
                "assetId": str(source.asset_id),
                "x": pos[0],
                "y": pos[1],
                "width": fitted.width,
                "height": fitted.height,
                "zIndex": spec.z_index,
            }
        )
        used.append(slot)
        return

    if spec.type == "SHAPE":
        fill = _hex_rgba(spec.fill or "#C4A35A")
        draw.rectangle((spec.x, spec.y, spec.x + spec.width, spec.y + spec.height), fill=fill)
        layers.append(
            {
                "id": spec.id,
                "type": "SHAPE",
                "role": spec.role or "decoration",
                "fill": spec.fill or "#C4A35A",
                "shapeKind": spec.shape_kind or "rect",
                "x": spec.x,
                "y": spec.y,
                "width": spec.width,
                "height": spec.height,
                "zIndex": spec.z_index,
            }
        )
        used.append(spec.id)
        return

    if spec.type == "BUTTON":
        label = _slot_text(slots, slot) or slots.cta
        if not label:
            return
        font = resolve_turkish_font(
            bold=_is_bold(spec.font_weight) if spec.font_weight else True,
            size=int(spec.font_size or 14),
            family=spec.font_family or "sans",
        )
        bg = _hex_rgba(spec.background_color or "#C4A35A")
        fg = _hex_rgba(spec.text_color or "#1B2A4A")
        radius = max(0, int(spec.border_radius or 4))
        draw.rounded_rectangle(
            (spec.x, spec.y, spec.x + spec.width, spec.y + spec.height),
            radius=radius,
            fill=bg,
        )
        bbox = font.getbbox(label)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = spec.x + max(0, (spec.width - tw) // 2)
        ty = spec.y + max(0, (spec.height - th) // 2) - 1
        draw.text((tx, ty), label, font=font, fill=fg)
        layers.append(
            {
                "id": spec.id,
                "type": "BUTTON",
                "label": label,
                "backgroundColor": spec.background_color or "#C4A35A",
                "textColor": spec.text_color or "#1B2A4A",
                "ctaStyle": "gold" if (spec.background_color or "").upper() == "#C4A35A" else None,
                "fontSize": int(spec.font_size or 14),
                "fontWeight": spec.font_weight or "semibold",
                "fontFamily": spec.font_family or "sans",
                "borderRadius": radius,
                "x": spec.x,
                "y": spec.y,
                "width": spec.width,
                "height": spec.height,
                "zIndex": spec.z_index,
            }
        )
        used.append("cta")
        return

    if spec.type == "TEXT":
        text = _slot_text(slots, slot)
        if not text:
            return
        font = resolve_turkish_font(
            bold=_is_bold(spec.font_weight),
            size=int(spec.font_size or 24),
            family=spec.font_family or "sans",
        )
        fill = _hex_rgba(spec.color or "#FFFFFF")
        _, block_h = _draw_text_block(
            draw,
            text=text,
            font=font,
            x=spec.x,
            y=spec.y,
            max_width=spec.width,
            fill=fill,
            align=spec.align or "left",
            line_gap=float(spec.line_height or 1.2),
        )
        layer: dict[str, Any] = {
            "id": spec.id,
            "type": "TEXT",
            "role": spec.role or "custom",
            "content": text,
            "fontSize": int(spec.font_size or getattr(font, "size", 24) or 24),
            "fontWeight": spec.font_weight or "normal",
            "fontFamily": spec.font_family or "sans",
            "align": spec.align or "left",
            "color": spec.color or "#ffffff",
            "x": spec.x,
            "y": spec.y,
            "width": spec.width,
            "height": max(block_h, spec.height, 20),
            "zIndex": spec.z_index,
        }
        if spec.line_height is not None:
            layer["lineHeight"] = spec.line_height
        if spec.letter_spacing is not None:
            layer["letterSpacing"] = spec.letter_spacing
        layers.append(layer)
        used.append("headline" if spec.role == "headline" else slot or spec.id)
        return


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
