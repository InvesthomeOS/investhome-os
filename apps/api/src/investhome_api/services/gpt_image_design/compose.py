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
    format_headline_for_plan,
    sanitize_creative_text,
)
from investhome_api.services.gpt_image_design.os_composition_plan import (
    count_internal_leaks,
    looks_like_internal_leak,
)
from investhome_api.services.gpt_image_design.source import ResolvedSourceImage
from investhome_api.services.gpt_image_design.svg_raster import svg_bytes_to_png

# Re-export for tests / callers
__all__ = [
    "CompositionResult",
    "CompositionSlotPlan",
    "DuplicationGuardResult",
    "build_slot_plan",
    "compose_final_layers",
    "logo_to_rgba",
    "overlay_brand_lockups",
    "resolve_turkish_font",
    "run_duplication_guard",
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
    feature_1: str = ""
    feature_2: str = ""
    feature_3: str = ""
    include_slogan: bool = True


@dataclass
class CompositionResult:
    png_bytes: bytes
    layers: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    used_slots: list[str] = field(default_factory=list)
    duplication_guard: dict[str, Any] = field(default_factory=dict)


@dataclass
class DuplicationGuardResult:
    status: str
    violations: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    deduped_slots: CompositionSlotPlan | None = None


def _norm_semantic(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def run_duplication_guard(
    slots: CompositionSlotPlan,
    *,
    logos: list[ResolvedSourceImage],
    plan: GptImageDesignPlan | None = None,
) -> DuplicationGuardResult:
    """Ensure OS composition adds each semantic element once — no duplicate headline/CTA/logo."""
    violations: list[str] = []
    headline = _norm_semantic(slots.headline)
    subhead = _norm_semantic(slots.subhead)
    cta = _norm_semantic(slots.cta)
    verified = _norm_semantic(slots.verified_data)

    deduped = CompositionSlotPlan(
        headline=slots.headline,
        subhead=slots.subhead,
        verified_data=slots.verified_data,
        cta=slots.cta,
        include_slogan=slots.include_slogan,
    )

    if headline and subhead and headline == subhead:
        deduped.subhead = ""
        violations.append("headline_equals_subhead")
    elif headline and subhead and headline in subhead:
        deduped.subhead = slots.subhead.replace(slots.headline, "").strip(" ·-|,")
        violations.append("headline_in_subhead")

    if headline and cta and headline == cta:
        violations.append("headline_equals_cta")
    if subhead and cta and subhead == cta:
        deduped.subhead = ""
        violations.append("subhead_equals_cta")
    if verified and verified in {headline, subhead, cta}:
        deduped.verified_data = ""
        violations.append("verified_duplicates_visible_copy")

    project_logos = [row for row in logos if row.role == "project_logo"]
    logo_count = len(project_logos)
    if logo_count != 1:
        violations.append(f"project_logo_count_{logo_count}")

    headline_layers = 0
    cta_layers = 0
    logo_layers = 0
    if plan is not None:
        for spec in plan.layers:
            if spec.type == "TEXT" and (spec.role == "headline" or spec.content_slot == "headline"):
                headline_layers += 1
            if spec.type == "BUTTON" or spec.content_slot == "cta":
                cta_layers += 1
            if spec.type == "IMAGE" and spec.content_slot in {"project_logo", "investhome_logo"}:
                logo_layers += 1
        if headline_layers > 1:
            violations.append(f"headline_layer_count_{headline_layers}")
        if cta_layers > 1:
            violations.append(f"cta_layer_count_{cta_layers}")

    counts = {
        "project_logo_assets": logo_count,
        "headline_layers": max(headline_layers, 1 if headline else 0),
        "cta_layers": max(cta_layers, 1 if cta else 0),
        "primary_headline": 1 if headline else 0,
        "primary_cta": 1 if cta else 0,
    }
    return DuplicationGuardResult(
        status="pass" if not violations else "fail",
        violations=violations,
        counts=counts,
        deduped_slots=deduped,
    )


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
    """Scale the real logo to fill the plan box (contain). thumbnail() only shrank — logos vanished."""
    src = logo.convert("RGBA")
    bbox = src.getbbox()
    if bbox:
        src = src.crop(bbox)
    src_w, src_h = max(1, src.width), max(1, src.height)
    target_w, target_h = max(1, box_w), max(1, box_h)
    scale = min(target_w / src_w, target_h / src_h)
    nw = max(1, int(round(src_w * scale)))
    nh = max(1, int(round(src_h * scale)))
    return src.resize((nw, nh), Image.Resampling.LANCZOS)


def _wrap_text(text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    """Honor intentional newlines first; wrap remaining long lines to the box."""
    raw = text or ""
    if not raw.strip():
        return []
    paragraphs = raw.split("\n") if "\n" in raw else [raw]
    lines: list[str] = []
    for paragraph in paragraphs:
        words = paragraph.split()
        if not words:
            continue
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
    feature_callouts: list[str] | None = None,
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
    callouts = [str(x).strip() for x in (feature_callouts or []) if str(x).strip()]
    if not callouts:
        raw = str(copy.get("supporting_callouts") or "")
        callouts = [x.strip() for x in raw.split("|") if x.strip()]
    return CompositionSlotPlan(
        headline=headline,
        subhead=subhead,
        verified_data=verified,
        cta=cta,
        feature_1=callouts[0] if len(callouts) > 0 else "",
        feature_2=callouts[1] if len(callouts) > 1 else "",
        feature_3=callouts[2] if len(callouts) > 2 else "",
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
        return sanitize_creative_text(slots.headline)
    if content_slot == "subhead":
        return sanitize_creative_text(slots.subhead)
    if content_slot in {"location", "verified", "verified_data"}:
        return sanitize_creative_text(slots.verified_data)
    if content_slot == "cta":
        return sanitize_creative_text(slots.cta)
    if content_slot == "feature_1":
        return sanitize_creative_text(slots.feature_1)
    if content_slot == "feature_2":
        return sanitize_creative_text(slots.feature_2)
    if content_slot == "feature_3":
        return sanitize_creative_text(slots.feature_3)
    if content_slot == "slogan":
        return INVESHOME_SLOGAN if slots.include_slogan else ""
    return ""


def _is_bold(weight: str | None) -> bool:
    return (weight or "").lower() in {"bold", "semibold", "700", "600"}


def _is_giant_panel(spec: DesignPlanLayer, canvas_w: int, canvas_h: int) -> bool:
    """Reject large semi-transparent rectangles covering the bottom half."""
    if spec.type != "SHAPE" or (spec.shape_kind or "rect") not in {"rect", ""}:
        return False
    if spec.width < canvas_w * 0.55:
        return False
    if spec.height < canvas_h * 0.28:
        return False
    if spec.y < canvas_h * 0.35:
        return False
    alpha = 255
    if spec.opacity is not None:
        alpha = int(round(float(spec.opacity) * 255))
    fill = spec.fill or ""
    if fill.lower() in {"#1b2a4a", "#1b2a4a"} and alpha >= 80:
        return True
    return spec.height >= canvas_h * 0.4 and alpha >= 60


def _apply_plan_scrim(canvas: Image.Image, plan: GptImageDesignPlan) -> None:
    """Localized gradient/scrim behind type cluster — not a giant bottom panel."""
    if not plan.needs_scrim:
        return
    zone = plan.content_zone
    if zone is None:
        return
    localized = bool(getattr(plan, "localized_scrim_only", False))
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    painter = ImageDraw.Draw(overlay)
    x0, y0 = max(0, zone.x), max(0, zone.y)
    x1 = min(canvas.size[0], zone.x + zone.width)
    y1 = min(canvas.size[1], zone.y + zone.height)
    if localized:
        y1 = min(y1, y0 + max(int(zone.height * 0.92), int(canvas.size[1] * 0.48)))
        max_alpha = 95
    else:
        max_alpha = 150
    height = max(1, y1 - y0)
    for row in range(y0, y1):
        t = (row - y0) / height
        alpha = int(round(max_alpha * (t ** 1.35)))
        if alpha <= 0:
            continue
        painter.line([(x0, row), (x1, row)], fill=(27, 42, 74, alpha))
    canvas.alpha_composite(overlay)


def _draw_text_runs(
    draw: ImageDraw.ImageDraw,
    *,
    runs: list[dict[str, Any]],
    x: int,
    y: int,
    max_width: int,
    align: str = "left",
    line_gap: float = 1.06,
    shadow: bool = False,
) -> tuple[int, int, str]:
    """Draw rich headline runs; returns (width, height, flattened_content)."""
    if not runs:
        return 0, 0, ""
    cursor_x = x
    cursor_y = y
    line_start_x = x
    max_w = 0
    line_h = 0
    flat_parts: list[str] = []
    for run in runs:
        text = str(run.get("text") or "")
        if run.get("break"):
            cursor_x = line_start_x
            cursor_y += max(line_h, 8)
            if text == "\n":
                flat_parts.append("\n")
            continue
        if not text:
            continue
        if looks_like_internal_leak(text):
            continue
        size = int(run.get("fontSize") or 24)
        family = str(run.get("fontFamily") or "serif")
        weight = str(run.get("fontWeight") or "medium")
        font = resolve_turkish_font(
            bold=_is_bold(weight),
            size=size,
            family=family,
        )
        fill = _hex_rgba(str(run.get("color") or "#1B2A4A"))
        sample = font.getbbox("Ay")
        line_h = max(line_h, int(round((sample[3] - sample[1]) * line_gap)))
        bbox = font.getbbox(text)
        tw = bbox[2] - bbox[0]
        if cursor_x + tw > x + max_width and cursor_x > line_start_x:
            cursor_x = line_start_x
            cursor_y += line_h
            line_h = int(round((sample[3] - sample[1]) * line_gap))
        if shadow:
            draw.text((cursor_x + 1, cursor_y + 1), text, font=font, fill=(0, 0, 0, 90))
        draw.text((cursor_x, cursor_y), text, font=font, fill=fill)
        cursor_x += tw
        max_w = max(max_w, cursor_x - x)
        flat_parts.append(text)
    block_h = max(line_h, cursor_y + line_h - y)
    return max_w, block_h, "".join(flat_parts)


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

    dup_guard = run_duplication_guard(slots, logos=logos, plan=plan)
    if dup_guard.deduped_slots is not None:
        slots = dup_guard.deduped_slots

    layers: list[dict[str, Any]] = []
    draw = ImageDraw.Draw(canvas)
    _apply_plan_scrim(canvas, plan)

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
            plan=plan,
        )

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    png = buf.getvalue()

    if base_asset_id is not None:
        layers.insert(
            0,
            {
                "id": "background-gpt-image",
                "type": "IMAGE",
                "role": "background",
                "assetId": str(base_asset_id),
                "x": 0,
                "y": 0,
                "width": width,
                "height": height,
                "zIndex": 0,
            },
        )

    logger.info(
        "gpt_image_final_composition_ok used=%s variation=%s warnings=%s composed_asset=%s dup_guard=%s",
        used,
        plan.variation,
        warnings,
        str(composed_asset_id) if composed_asset_id else None,
        dup_guard.status,
    )
    return CompositionResult(
        png_bytes=png,
        layers=layers,
        warnings=warnings,
        used_slots=used,
        duplication_guard={
            "status": dup_guard.status,
            "violations": list(dup_guard.violations),
            "counts": dict(dup_guard.counts),
            "gpt_generated_text_count": 0,
            "gpt_generated_logo_count": 0,
        },
    )


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
    plan: GptImageDesignPlan | None = None,
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
        if spec.id == "shape-location-mark" and not _slot_text(slots, "location"):
            return
        if _is_giant_panel(spec, canvas.size[0], canvas.size[1]):
            warnings.append(f"skipped_giant_panel:{spec.id}")
            return
        fill = _hex_rgba(spec.fill or "#C4A35A")
        if spec.opacity is not None:
            fill = (fill[0], fill[1], fill[2], max(0, min(255, int(round(float(spec.opacity) * 255)))))
        radius = max(0, int(spec.border_radius or 0))
        box = (spec.x, spec.y, spec.x + spec.width, spec.y + spec.height)
        if fill[3] < 255:
            overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            if radius > 0:
                overlay_draw.rounded_rectangle(box, radius=radius, fill=fill)
            else:
                overlay_draw.rectangle(box, fill=fill)
            canvas.alpha_composite(overlay)
            draw = ImageDraw.Draw(canvas)
        elif radius > 0:
            draw.rounded_rectangle(box, radius=radius, fill=fill)
        else:
            draw.rectangle(box, fill=fill)
        shape_layer: dict[str, Any] = {
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
        if radius:
            shape_layer["borderRadius"] = radius
        layers.append(shape_layer)
        used.append(spec.id)
        return

    if spec.type == "BUTTON":
        label = _slot_text(slots, slot) or slots.cta
        if not label:
            return
        style = (spec.cta_style or "").strip().lower()
        if style == "text_arrow" and "→" not in label:
            label = f"{label}  →"
        font = resolve_turkish_font(
            bold=_is_bold(spec.font_weight) if spec.font_weight else True,
            size=int(spec.font_size or 14),
            family=spec.font_family or "sans",
        )
        fg = _hex_rgba(spec.text_color or "#1B2A4A")
        radius = max(0, int(spec.border_radius or 0))
        box = (spec.x, spec.y, spec.x + spec.width, spec.y + spec.height)
        if style in {"editorial_link", "text_arrow", "minimal"}:
            pass
        elif style == "outline":
            draw.rounded_rectangle(box, radius=max(radius, spec.height // 2), outline=fg, width=2)
        else:
            bg = _hex_rgba(spec.background_color or "#C4A35A")
            draw.rounded_rectangle(box, radius=radius or 4, fill=bg)
        bbox = font.getbbox(label)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = spec.x + max(0, (spec.width - tw) // 2)
        ty = spec.y + max(0, (spec.height - th) // 2) - 1
        if style in {"editorial_link", "text_arrow", "minimal"} and (spec.align or "left") == "left":
            tx = spec.x
        draw.text((tx, ty), label, font=font, fill=fg)
        if style == "editorial_link":
            underline_y = ty + th + 3
            draw.line((tx, underline_y, tx + tw, underline_y), fill=fg, width=1)
        frontend_style = {
            "pill": "PILL_BUTTON",
            "outline": "MINIMAL_BUTTON",
            "editorial_link": "TEXT_LINK_STYLE",
            "text_arrow": "TEXT_LINK_STYLE",
            "minimal": "MINIMAL_BUTTON",
        }.get(style) or spec.cta_style
        link_like = style in {"editorial_link", "text_arrow", "minimal", "outline"}
        layers.append(
            {
                "id": spec.id,
                "type": "BUTTON",
                "label": label,
                "backgroundColor": spec.background_color or ("transparent" if link_like else "#C4A35A"),
                "textColor": spec.text_color or "#1B2A4A",
                "ctaStyle": frontend_style,
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
        text = spec.static_content or _slot_text(slots, slot)
        if not text:
            return
        if looks_like_internal_leak(text):
            warnings.append(f"blocked_internal_leak:{spec.id}")
            return
        if spec.role == "headline":
            text = format_headline_for_plan(text, plan)
        runs = list(spec.text_runs or [])
        if spec.role == "headline" and runs:
            use_shadow = bool(getattr(plan, "localized_scrim_only", False)) if plan else False
            _, block_h, flat = _draw_text_runs(
                draw,
                runs=runs,
                x=spec.x,
                y=spec.y,
                max_width=spec.width,
                align=spec.align or "left",
                line_gap=float(spec.line_height or 1.06),
                shadow=use_shadow,
            )
            layer = {
                "id": spec.id,
                "type": "TEXT",
                "role": spec.role or "custom",
                "content": flat or text,
                "runs": runs,
                "fontSize": int(spec.font_size or 72),
                "fontWeight": spec.font_weight or "medium",
                "fontFamily": spec.font_family or "serif",
                "align": spec.align or "left",
                "color": spec.color or "#1B2A4A",
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
            used.append("headline")
            return
        font = resolve_turkish_font(
            bold=_is_bold(spec.font_weight),
            size=int(spec.font_size or 24),
            family=spec.font_family or "sans",
        )
        fill = _hex_rgba(spec.color or "#FFFFFF")
        use_shadow = spec.content_slot.startswith("feature_") and bool(
            getattr(plan, "localized_scrim_only", False) if plan else False
        )
        if use_shadow:
            shadow_font = font
            for i, line in enumerate(_wrap_text(text, font, spec.width)):
                sample = font.getbbox("Ay")
                line_h = max(1, int(round((sample[3] - sample[1]) * float(spec.line_height or 1.2))))
                lx = spec.x
                ly = spec.y + i * line_h
                draw.text((lx + 1, ly + 1), line, font=shadow_font, fill=(0, 0, 0, 80))
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
        if spec.content_slot.startswith("feature_"):
            used.append(spec.id)
        else:
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
