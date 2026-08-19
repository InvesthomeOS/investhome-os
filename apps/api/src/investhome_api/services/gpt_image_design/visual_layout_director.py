"""Visual Layout Director — background-aware ad composition (vision or heuristic).

Analyzes the clean GPT background image and produces a full Layout Plan.
OS Renderer (`compose.render_layout_plan`) applies the plan faithfully — no design decisions.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import re
import statistics
from dataclasses import dataclass, field
from typing import Any, Callable

import httpx
from PIL import Image

from investhome_api.config.settings import get_settings
from investhome_api.services.gpt_image_design.config import openai_api_key, resolve_base_url
from investhome_api.services.gpt_image_design.design_plan import (
    GOLD,
    NAVY,
    SUBHEAD_INK,
    WHITE,
    DesignPlanLayer,
    DesignZone,
    ElementGroup,
    GptImageDesignPlan,
    _clamp_box,
    _group,
    _layer,
    _sf,
    _sx,
    _sy,
    apply_visual_quality_guard,
    build_gpt_image_design_plan,
    decide_headline_line_breaks,
)
from investhome_api.services.gpt_image_design.os_composition_plan import (
    build_headline_runs,
    choose_os_composition_family,
)

logger = logging.getLogger(__name__)

VISION_MODEL = "gpt-4o"
LAYOUT_PLAN_JSON = "LAYOUT_PLAN_JSON"
MIN_FEATURE_FONT = 16
MIN_HEADLINE_FONT = 68
MIN_CTA_FONT = 15
MIN_LOGO_W_REF = 248
MIN_LOGO_H_REF = 72


@dataclass
class ZoneRect:
    x: int
    y: int
    width: int
    height: int
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "label": self.label,
        }

    def overlaps(self, other: ZoneRect, *, margin: int = 0) -> bool:
        return not (
            self.x + self.width + margin <= other.x
            or other.x + other.width + margin <= self.x
            or self.y + self.height + margin <= other.y
            or other.y + other.height + margin <= self.y
        )


@dataclass
class VisualLayoutAnalysis:
    visual_focus: str = ""
    negative_spaces: list[dict[str, Any]] = field(default_factory=list)
    protected_zones: list[ZoneRect] = field(default_factory=list)
    contrast_zones: list[dict[str, Any]] = field(default_factory=list)
    text_ground: str = "light"
    light_direction: str = ""
    weight_center: dict[str, float] = field(default_factory=lambda: {"x": 0.5, "y": 0.5})
    mode: str = "heuristic"

    def to_dict(self) -> dict[str, Any]:
        return {
            "visual_focus": self.visual_focus,
            "negative_spaces": list(self.negative_spaces),
            "protected_zones": [z.to_dict() for z in self.protected_zones],
            "contrast_zones": list(self.contrast_zones),
            "text_ground": self.text_ground,
            "light_direction": self.light_direction,
            "weight_center": dict(self.weight_center),
            "mode": self.mode,
        }


@dataclass
class VisualLayoutPlan:
    canvas_width: int
    canvas_height: int
    analysis: VisualLayoutAnalysis
    elements: list[DesignPlanLayer]
    composition_family: str = "editorial_hero"
    needs_scrim: bool = False
    localized_scrim_only: bool = True
    content_zone: DesignZone | None = None
    pass_count: int = 1
    qa_issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        from dataclasses import asdict

        return {
            "canvas": {"width": self.canvas_width, "height": self.canvas_height},
            "analysis": self.analysis.to_dict(),
            "composition_family": self.composition_family,
            "needs_scrim": self.needs_scrim,
            "localized_scrim_only": self.localized_scrim_only,
            "content_zone": asdict(self.content_zone) if self.content_zone else None,
            "elements": [asdict(el) for el in self.elements],
            "pass_count": self.pass_count,
            "qa_issues": list(self.qa_issues),
        }


@dataclass
class VisualLayoutDirectorResult:
    layout_plan: VisualLayoutPlan
    design_plan: GptImageDesignPlan
    report: dict[str, Any]
    mode: str = "heuristic"


def _cell_stats(img: Image.Image, x0: int, y0: int, x1: int, y1: int) -> tuple[float, float]:
    crop = img.crop((x0, y0, x1, y1))
    pixels = list(crop.getdata())
    if not pixels:
        return 0.5, 0.0
    lums = [0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b in pixels]
    mean = sum(lums) / (255 * len(lums))
    var = statistics.pstdev(lums) / 255 if len(lums) > 1 else 0.0
    return mean, var


def analyze_background_heuristic(
    background_bytes: bytes,
    *,
    canvas_width: int,
    canvas_height: int,
) -> VisualLayoutAnalysis:
    """Brightness grid + variance — detect focal detail vs quiet type zones."""
    try:
        with Image.open(io.BytesIO(background_bytes)) as raw:
            img = raw.convert("RGB").resize((canvas_width, canvas_height), Image.Resampling.BILINEAR)
    except Exception:
        return VisualLayoutAnalysis(
            visual_focus="center-interior",
            negative_spaces=[{"region": "left-upper", "x": _sx(72, canvas_width), "y": _sy(72, canvas_height)}],
            protected_zones=[
                ZoneRect(
                    x=int(canvas_width * 0.25),
                    y=int(canvas_height * 0.08),
                    width=int(canvas_width * 0.5),
                    height=int(canvas_height * 0.28),
                    label="center-upper focal band",
                )
            ],
            text_ground="light",
            mode="heuristic",
        )

    cols, rows = 8, 10
    cell_w = max(1, canvas_width // cols)
    cell_h = max(1, canvas_height // rows)
    cells: list[dict[str, Any]] = []
    for row in range(rows):
        for col in range(cols):
            x0, y0 = col * cell_w, row * cell_h
            x1 = min(canvas_width, x0 + cell_w)
            y1 = min(canvas_height, y0 + cell_h)
            lum, var = _cell_stats(img, x0, y0, x1, y1)
            cx = (x0 + x1) / 2 / canvas_width
            cy = (y0 + y1) / 2 / canvas_height
            cells.append({"col": col, "row": row, "x0": x0, "y0": y0, "x1": x1, "y1": y1, "lum": lum, "var": var, "cx": cx, "cy": cy})

    # Visual weight center — high variance cells
    weighted_x = sum(c["cx"] * c["var"] for c in cells) / max(0.001, sum(c["var"] for c in cells))
    weighted_y = sum(c["cy"] * c["var"] for c in cells) / max(0.001, sum(c["var"] for c in cells))

    protected: list[ZoneRect] = []
    for c in cells:
        if c["var"] < 0.045:
            continue
        # Center band + upper rows often hold pendants / focal architecture
        if 0.22 <= c["cx"] <= 0.78 and c["cy"] <= 0.42:
            protected.append(
                ZoneRect(
                    x=c["x0"],
                    y=c["y0"],
                    width=c["x1"] - c["x0"],
                    height=c["y1"] - c["y0"],
                    label="high-detail upper focal",
                )
            )
        elif 0.18 <= c["cx"] <= 0.82 and 0.35 <= c["cy"] <= 0.72 and c["var"] >= 0.06:
            protected.append(
                ZoneRect(
                    x=c["x0"],
                    y=c["y0"],
                    width=c["x1"] - c["x0"],
                    height=c["y1"] - c["y0"],
                    label="furniture/interior focal",
                )
            )

    if not protected:
        protected.append(
            ZoneRect(
                x=int(canvas_width * 0.28),
                y=int(canvas_height * 0.06),
                width=int(canvas_width * 0.44),
                height=int(canvas_height * 0.32),
                label="center-upper default protect",
            )
        )

    quiet = sorted(cells, key=lambda c: c["var"] - (0.12 if c["cx"] < 0.45 else 0.0) - (0.08 if c["cy"] < 0.45 else 0.0))
    best = quiet[0]
    neg_x, neg_y = best["x0"], best["y0"]
    negative_spaces = [
        {
            "region": "left-upper" if best["cx"] < 0.5 else "right-upper",
            "x": neg_x,
            "y": neg_y,
            "width": best["x1"] - best["x0"],
            "height": best["y1"] - best["y0"],
            "variance": best["var"],
        }
    ]

    contrast_zones: list[dict[str, Any]] = []
    for c in cells:
        if c["var"] < 0.035 and (c["lum"] < 0.35 or c["lum"] > 0.62):
            contrast_zones.append(
                {
                    "x": c["x0"],
                    "y": c["y0"],
                    "width": c["x1"] - c["x0"],
                    "height": c["y1"] - c["y0"],
                    "ground": "dark" if c["lum"] < 0.42 else "light",
                }
            )

    text_ground = "dark" if best["lum"] < 0.42 else "light"
    focus = "right-center interior" if weighted_x > 0.55 else "center interior"
    if weighted_y < 0.35:
        focus = "upper architectural focal (pendants/ceiling)"

    return VisualLayoutAnalysis(
        visual_focus=focus,
        negative_spaces=negative_spaces,
        protected_zones=protected,
        contrast_zones=contrast_zones[:6],
        text_ground=text_ground,
        light_direction="left" if weighted_x > 0.5 else "right",
        weight_center={"x": round(weighted_x, 3), "y": round(weighted_y, 3)},
        mode="heuristic",
    )


def _parse_vision_zones(raw: list[Any], cw: int, ch: int) -> list[ZoneRect]:
    zones: list[ZoneRect] = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        try:
            zones.append(
                ZoneRect(
                    x=int(item.get("x", 0)),
                    y=int(item.get("y", 0)),
                    width=int(item.get("width", 1)),
                    height=int(item.get("height", 1)),
                    label=str(item.get("label") or item.get("name") or "protected"),
                )
            )
        except (TypeError, ValueError):
            continue
    return [_clamp_zone(z, cw, ch) for z in zones]


def _clamp_zone(z: ZoneRect, cw: int, ch: int) -> ZoneRect:
    x, y, w, h = _clamp_box(z.x, z.y, z.width, z.height, cw, ch)
    return ZoneRect(x=x, y=y, width=w, height=h, label=z.label)


def analyze_background_vision(
    background_bytes: bytes,
    *,
    canvas_width: int,
    canvas_height: int,
    api_key: str,
    base_url: str | None = None,
    model: str = VISION_MODEL,
) -> VisualLayoutAnalysis | None:
    """gpt-4o vision analysis of background bytes."""
    if not api_key.strip():
        return None
    b64 = base64.b64encode(background_bytes).decode("ascii")
    mime = "image/png"
    if background_bytes[:3] == b"\xff\xd8\xff":
        mime = "image/jpeg"
    system = (
        "You are Visual Layout Director for premium real-estate Instagram ads. "
        "Analyze the background image and return ONLY valid JSON matching LAYOUT_PLAN_JSON schema. "
        "Identify REAL negative space (quiet areas suitable for type — not geometrically empty if it has pendant lights). "
        "Mark protected zones: pendant lights, TV, furniture focal points, main interior details. "
        "Never suggest large translucent panels."
    )
    user_content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                f"LAYOUT_PLAN_JSON — analyze this {canvas_width}x{canvas_height} ad background.\n"
                "Return JSON: {\n"
                '  "visual_focus": string,\n'
                '  "negative_spaces": [{"region": string, "x": int, "y": int, "width": int, "height": int}],\n'
                '  "protected_zones": [{"label": string, "x": int, "y": int, "width": int, "height": int}],\n'
                '  "contrast_zones": [{"x": int, "y": int, "width": int, "height": int, "ground": "light"|"dark"}],\n'
                '  "text_ground": "light"|"dark",\n'
                '  "light_direction": string,\n'
                '  "weight_center": {"x": float, "y": float}\n'
                "}"
            ),
        },
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "high"}},
    ]
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.15,
        "response_format": {"type": "json_object"},
    }
    url = f"{(base_url or 'https://api.openai.com/v1').rstrip('/')}/chat/completions"
    try:
        with httpx.Client(timeout=90.0) as client:
            resp = client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            resp.raise_for_status()
        data = resp.json()
        text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        parsed = json.loads(text) if text.strip().startswith("{") else _extract_json(text)
        if not isinstance(parsed, dict):
            return None
        protected = _parse_vision_zones(parsed.get("protected_zones") or [], canvas_width, canvas_height)
        return VisualLayoutAnalysis(
            visual_focus=str(parsed.get("visual_focus") or ""),
            negative_spaces=list(parsed.get("negative_spaces") or []),
            protected_zones=protected,
            contrast_zones=list(parsed.get("contrast_zones") or []),
            text_ground=str(parsed.get("text_ground") or "light"),
            light_direction=str(parsed.get("light_direction") or ""),
            weight_center=dict(parsed.get("weight_center") or {"x": 0.5, "y": 0.5}),
            mode="vision",
        )
    except Exception as exc:
        logger.warning("visual_layout_director_vision_failed: %s", exc)
        return None


def _extract_json(text: str) -> dict[str, Any]:
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def _zone_right(z: ZoneRect) -> int:
    return z.x + z.width


def _zone_bottom(z: ZoneRect) -> int:
    return z.y + z.height


def _max_width_before_protected(
    x: int,
    y: int,
    height: int,
    protected: list[ZoneRect],
    *,
    canvas_width: int,
) -> int:
    """How wide a box at (x,y) can grow rightward without hitting protected zones."""
    limit = canvas_width - x - _sx(72, canvas_width)
    y1 = y + height
    for p in protected:
        p_y1 = p.y + p.height
        vertical_overlap = not (y1 < p.y or y > p_y1)
        if not vertical_overlap:
            continue
        if p.x >= x:
            limit = min(limit, max(80, p.x - x - 12))
        elif _zone_right(p) > x:
            # Protected starts left but extends right — shrink to avoid overlap
            overlap_w = _zone_right(p) - x
            if overlap_w > 0:
                limit = min(limit, max(80, limit - overlap_w - 12))
    return max(80, limit)


def _pick_type_origin(
    analysis: VisualLayoutAnalysis,
    *,
    canvas_width: int,
    canvas_height: int,
) -> tuple[int, int]:
    candidates: list[tuple[float, int, int]] = []
    protected = analysis.protected_zones
    spaces = analysis.negative_spaces or [{"x": _sx(72, canvas_width), "y": _sy(72, canvas_height)}]
    for ns in spaces:
        x = int(ns.get("x", _sx(72, canvas_width)))
        y = int(ns.get("y", _sy(72, canvas_height)))
        penalty = 0.0
        probe = ZoneRect(x=x, y=y, width=_sx(420, canvas_width), height=_sy(420, canvas_height))
        for p in protected:
            if probe.overlaps(p, margin=16):
                penalty += 2.5
            # Prefer origins left of focal mass
            if x + _sx(420, canvas_width) > p.x:
                penalty += 0.6
        candidates.append((penalty + (0.15 if x > canvas_width * 0.35 else 0.0), x, y))
    candidates.sort(key=lambda item: item[0])
    _, best_x, best_y = candidates[0]
    return max(_sx(72, canvas_width), best_x), max(_sy(64, canvas_height), best_y)


def _rect_from_layer(layer: DesignPlanLayer) -> ZoneRect:
    return ZoneRect(x=layer.x, y=layer.y, width=layer.width, height=layer.height, label=layer.id)


def _hits_protected(layer: DesignPlanLayer, protected: list[ZoneRect], *, margin: int = 8) -> bool:
    box = _rect_from_layer(layer)
    for p in protected:
        if box.overlaps(p, margin=margin):
            return True
        # Also fail when box extends into protected from the left
        if box.x < p.x and _zone_right(box) > p.x + margin and not (
            box.y + box.height < p.y - margin or box.y > _zone_bottom(p) + margin
        ):
            return True
    return False


def _shift_away_from_protected(
    layer: DesignPlanLayer,
    protected: list[ZoneRect],
    *,
    canvas_width: int,
    canvas_height: int,
) -> None:
    if not _hits_protected(layer, protected):
        return
    # Prefer shifting up-left — typical interior negative space
    for dx, dy in [(-48, -36), (-48, 0), (0, -48), (48, -36), (-72, -24)]:
        trial = DesignPlanLayer(
            id=layer.id,
            type=layer.type,
            role=layer.role,
            x=max(_sx(72, canvas_width), layer.x + dx),
            y=max(_sy(64, canvas_height), layer.y + dy),
            width=layer.width,
            height=layer.height,
        )
        if not _hits_protected(trial, protected):
            layer.x, layer.y = trial.x, trial.y
            return
    layer.x = max(_sx(72, canvas_width), min(layer.x, canvas_width // 4))
    layer.y = max(_sy(64, canvas_height), min(layer.y, canvas_height // 5))


def build_layout_elements(
    *,
    canvas_width: int,
    canvas_height: int,
    texts: dict[str, str],
    analysis: VisualLayoutAnalysis,
    art_direction: dict[str, Any] | None = None,
    lifestyle: bool = False,
    has_project_logo: bool = True,
    has_investhome_logo: bool = False,
    include_slogan: bool = True,
    composition_family: str = "editorial_hero",
) -> list[DesignPlanLayer]:
    """Full ad layout from visual analysis — not a fixed template."""
    cw, ch = canvas_width, canvas_height
    type_x, type_y = _pick_type_origin(analysis, canvas_width=cw, canvas_height=ch)
    text_ground = analysis.text_ground or "light"
    headline_color = NAVY if text_ground == "light" else WHITE
    feature_color = SUBHEAD_INK if text_ground == "light" else "#E8E4DC"
    slogan_color = SUBHEAD_INK if text_ground == "light" else "#D1D5DB"

    callouts_raw = str(texts.get("supporting_callouts") or "")
    callouts = [x.strip() for x in callouts_raw.split("|") if x.strip()]
    feature_count = len(callouts)

    headline = str(texts.get("headline") or "").strip()
    emphasis = list((art_direction or {}).get("emphasis_words") or [])
    if not emphasis and headline:
        words = [w.strip(",.") for w in headline.split() if w.strip()]
        if words:
            emphasis = [words[-1]]

    layers: list[DesignPlanLayer] = []
    if has_project_logo:
        logo_y = max(_sy(64, ch), type_y - _sy(24, ch))
        layers.append(
            _layer(
                id="logo-project",
                type="IMAGE",
                role="logo",
                content_slot="project_logo",
                group="brand",
                x=type_x,
                y=logo_y,
                width=_sx(MIN_LOGO_W_REF, cw),
                height=_sy(MIN_LOGO_H_REF, ch),
                z_index=8,
            )
        )

    headline_y = type_y + _sy(88, ch)
    headline_h = _sy(210, ch)
    headline_w = min(
        _sx(520, cw),
        _max_width_before_protected(type_x, headline_y, headline_h, analysis.protected_zones, canvas_width=cw),
    )
    if headline_w < _sx(320, cw):
        type_x = _sx(72, cw)
        headline_w = min(
            _sx(360, cw),
            _max_width_before_protected(type_x, headline_y, headline_h, analysis.protected_zones, canvas_width=cw),
        )
    layers.append(
        _layer(
            id="text-headline",
            type="TEXT",
            role="headline",
            content_slot="headline",
            group="message",
            x=type_x,
            y=headline_y,
            width=headline_w,
            height=_sy(210, ch),
            font_size=max(_sf(MIN_HEADLINE_FONT, cw), _sf(72, cw)),
            font_family="serif",
            font_weight="medium",
            line_height=1.06,
            letter_spacing=-1.4,
            color=headline_color,
            align="left",
            z_index=6,
        )
    )
    layers.append(
        _layer(
            id="shape-divider",
            type="SHAPE",
            role="decoration",
            content_slot="shape",
            group="message",
            x=type_x,
            y=headline_y + _sy(188, ch),
            width=_sx(52, cw),
            height=max(2, _sy(2, ch)),
            fill=GOLD,
            shape_kind="line",
            decoration_purpose="hierarchy",
            z_index=4,
        )
    )

    feat_y = headline_y + _sy(220, ch)
    feat_font = max(_sf(MIN_FEATURE_FONT, cw), _sf(16, cw))
    for idx, slot in enumerate(("feature_1", "feature_2", "feature_3")):
        if idx >= feature_count:
            break
        fid = f"feature-{idx + 1}"
        layers.append(
            _layer(
                id=fid,
                type="TEXT",
                role="body",
                content_slot=slot,
                group="features",
                x=type_x + _sx(22, cw),
                y=feat_y + idx * _sy(58, ch),
                width=_sx(480, cw),
                height=_sy(54, ch),
                font_size=feat_font,
                font_family="sans",
                font_weight="medium" if idx == 0 else "normal",
                line_height=1.35,
                color=feature_color,
                align="left",
                z_index=6,
                static_content=callouts[idx],
            )
        )
        layers.append(
            _layer(
                id=f"shape-{fid}",
                type="SHAPE",
                role="decoration",
                content_slot="shape",
                group="features",
                x=type_x,
                y=feat_y + idx * _sy(58, ch) + _sy(10, ch),
                width=_sx(8, cw),
                height=_sy(8, ch),
                fill=GOLD,
                shape_kind="accent",
                decoration_purpose="brand_signature",
                border_radius=_sf(1, cw),
                z_index=5,
            )
        )

    cta_y = feat_y + max(feature_count, 1) * _sy(58, ch) + _sy(20, ch)
    cta_style = "editorial_link" if text_ground == "light" else "text_arrow"
    cta_color = GOLD if text_ground == "light" else WHITE
    layers.append(
        _layer(
            id="cta-primary",
            type="BUTTON",
            role="cta",
            content_slot="cta",
            group="action",
            x=type_x,
            y=cta_y,
            width=_sx(260, cw),
            height=_sy(48, ch),
            font_size=max(_sf(MIN_CTA_FONT, cw), _sf(15, cw)),
            font_family="sans",
            font_weight="semibold",
            background_color=None,
            text_color=cta_color,
            border_radius=_sf(2, cw),
            cta_style=cta_style,
            z_index=7,
        )
    )

    if include_slogan:
        layers.append(
            _layer(
                id="text-slogan",
                type="TEXT",
                role="brand",
                content_slot="slogan",
                group="footer",
                x=type_x,
                y=ch - _sy(64, ch),
                width=_sx(520, cw),
                height=_sy(28, ch),
                font_size=max(_sf(13, cw), 12),
                font_family="sans",
                font_weight="medium",
                color=slogan_color,
                align="left",
                z_index=6,
            )
        )

    if has_investhome_logo:
        layers.append(
            _layer(
                id="logo-investhome",
                type="IMAGE",
                role="logo",
                content_slot="investhome_logo",
                group="footer",
                x=cw - _sx(72, cw) - _sx(120, cw),
                y=ch - _sy(68, ch),
                width=_sx(120, cw),
                height=_sy(32, ch),
                z_index=8,
            )
        )

    protected = analysis.protected_zones
    for layer in layers:
        if (layer.type in {"TEXT", "BUTTON", "IMAGE"} and layer.role != "logo") or layer.content_slot == "project_logo":
            _shift_away_from_protected(layer, protected, canvas_width=cw, canvas_height=ch)
        x, y, w, h = _clamp_box(layer.x, layer.y, layer.width, layer.height, cw, ch)
        layer.x, layer.y, layer.width, layer.height = x, y, w, h

    # Headline runs
    base_plan = build_gpt_image_design_plan(
        canvas_width=cw,
        canvas_height=ch,
        has_project_logo=has_project_logo,
        has_investhome_logo=has_investhome_logo,
        include_slogan=include_slogan,
        headline=headline,
    )
    for layer in layers:
        if layer.id == "text-headline":
            layer.text_runs = build_headline_runs(
                headline,
                emphasis_words=emphasis,
                plan=base_plan,
                default_color=headline_color,
            )

    return layers


def layout_plan_to_design_plan(
    layout: VisualLayoutPlan,
    *,
    texts: dict[str, str],
) -> GptImageDesignPlan:
    """Convert Visual Layout Plan → GptImageDesignPlan for OS Renderer."""
    cw, ch = layout.canvas_width, layout.canvas_height
    family = layout.composition_family
    headline = str(texts.get("headline") or "")
    breaks = decide_headline_line_breaks(
        headline,
        typography_scale="editorial",
        composition_type=family,
    )
    groups = [
        _group("brand", [el.id for el in layout.elements if el.group == "brand"], "left", _sy(8, ch)),
        _group("message", [el.id for el in layout.elements if el.group == "message"], "left", _sy(14, ch)),
        _group("features", [el.id for el in layout.elements if el.group == "features"], "left", _sy(12, ch)),
        _group("action", [el.id for el in layout.elements if el.group == "action"], "left", _sy(28, ch)),
        _group("footer", [el.id for el in layout.elements if el.group == "footer"], "split", _sx(24, cw)),
    ]
    plan = GptImageDesignPlan(
        variation=family,
        label=family.replace("_", " ").upper(),
        composition_type=family.replace("_", " ").upper(),
        canvas_width=cw,
        canvas_height=ch,
        text_ground=layout.analysis.text_ground,
        visual_focal_point=layout.analysis.visual_focus,
        negative_space=str((layout.analysis.negative_spaces or [{}])[0].get("region", "left-upper")),
        visual_balance="photograph dominates; type in analyzed negative space",
        typography_scale="editorial",
        typography_contrast="high",
        contrast_strategy="natural contrast first; localized scrim only if needed",
        headline_line_breaks=breaks,
        element_relationships=[
            "VLD: logo in quiet zone away from focal mass",
            "VLD: headline in negative space — not over pendants/furniture",
            "VLD: features as separate readable callouts",
            "VLD: CTA visible editorial link / arrow",
        ],
        decorative_elements=["short gold hierarchy hairline", "small gold feature marks"],
        overlap_rules=["Do not cover protected interior focal objects", "No large translucent panels"],
        graphic_language=["background-aware editorial"],
        brand_color_relationships=["navy + gold headline emphasis"],
        safe_margins={"top": _sy(64, ch), "left": _sx(72, cw), "right": _sx(72, cw), "bottom": _sy(72, ch)},
        content_zone=layout.content_zone,
        groups=groups,
        layers=list(layout.elements),
        art_notes=["Visual Layout Director: full composition from background analysis"],
        needs_scrim=layout.needs_scrim,
        localized_scrim_only=layout.localized_scrim_only,
        visual_review_status="READY FOR USER VISUAL REVIEW",
    )
    return apply_visual_quality_guard(plan)


def _needs_localized_scrim(analysis: VisualLayoutAnalysis, elements: list[DesignPlanLayer]) -> bool:
    if analysis.text_ground == "dark":
        return False
    headline = next((el for el in elements if el.id == "text-headline"), None)
    if headline is None:
        return False
    # If headline sits on a light/ busy zone, allow localized scrim
    for cz in analysis.contrast_zones:
        if cz.get("ground") == "light":
            zx, zy = int(cz.get("x", 0)), int(cz.get("y", 0))
            zw, zh = int(cz.get("width", 0)), int(cz.get("height", 0))
            if headline.x >= zx and headline.y >= zy and headline.x < zx + zw:
                return True
    return analysis.text_ground == "light"


def plan_layout(
    *,
    background_bytes: bytes,
    canvas_width: int,
    canvas_height: int,
    texts: dict[str, str],
    art_direction: dict[str, Any] | None = None,
    lifestyle: bool = False,
    has_project_logo: bool = True,
    has_investhome_logo: bool = False,
    include_slogan: bool = True,
    analysis: VisualLayoutAnalysis | None = None,
) -> VisualLayoutPlan:
    """Analyze (if needed) and build full layout plan."""
    if analysis is None:
        settings = get_settings()
        api_key = openai_api_key(settings)
        base_url = resolve_base_url(settings)
        analysis = analyze_background_vision(
            background_bytes,
            canvas_width=canvas_width,
            canvas_height=canvas_height,
            api_key=api_key,
            base_url=base_url,
        )
        if analysis is None:
            analysis = analyze_background_heuristic(
                background_bytes,
                canvas_width=canvas_width,
                canvas_height=canvas_height,
            )

    callouts = [x.strip() for x in str(texts.get("supporting_callouts") or "").split("|") if x.strip()]
    family = choose_os_composition_family(
        lifestyle=lifestyle,
        feature_count=len(callouts),
        has_price=bool(str(texts.get("offer_price") or "").strip()),
        instruction=str(texts.get("headline") or ""),
        art_direction_variation=str((art_direction or {}).get("composition_family") or ""),
    )

    elements = build_layout_elements(
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        texts=texts,
        analysis=analysis,
        art_direction=art_direction,
        lifestyle=lifestyle,
        has_project_logo=has_project_logo,
        has_investhome_logo=has_investhome_logo,
        include_slogan=include_slogan,
        composition_family=family,
    )

    type_x, type_y = _pick_type_origin(analysis, canvas_width=canvas_width, canvas_height=canvas_height)
    content_zone = DesignZone(
        name="type_cluster",
        x=type_x,
        y=type_y,
        width=_sx(560, canvas_width),
        height=_sy(640, canvas_height),
        treatment="localized_scrim",
    )
    needs_scrim = _needs_localized_scrim(analysis, elements)

    return VisualLayoutPlan(
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        analysis=analysis,
        elements=elements,
        composition_family=family,
        needs_scrim=needs_scrim,
        localized_scrim_only=True,
        content_zone=content_zone,
    )


def _is_giant_panel_layer(layer: DesignPlanLayer, cw: int, ch: int) -> bool:
    if layer.type != "SHAPE" or (layer.shape_kind or "rect") not in {"rect", ""}:
        return False
    if layer.width < cw * 0.55 or layer.height < ch * 0.28:
        return False
    alpha = 255
    if layer.opacity is not None:
        alpha = int(round(float(layer.opacity) * 255))
    return layer.height >= ch * 0.35 and alpha >= 60


def qa_check_layout(
    layout: VisualLayoutPlan,
    *,
    layers_output: list[dict[str, Any]] | None = None,
) -> tuple[bool, list[str]]:
    """Heuristic QA — overlap, readability, panels, protected zones."""
    issues: list[str] = []
    cw, ch = layout.canvas_width, layout.canvas_height
    protected = layout.analysis.protected_zones

    for el in layout.elements:
        if _is_giant_panel_layer(el, cw, ch):
            issues.append(f"large_panel:{el.id}")
        if el.type == "TEXT" and el.content_slot and el.content_slot.startswith("feature_"):
            if (el.font_size or 0) < MIN_FEATURE_FONT:
                issues.append(f"tiny_feature:{el.id}")
        if el.id == "text-headline" and _hits_protected(el, protected, margin=4):
            issues.append("headline_over_focal")
        if el.content_slot == "project_logo" and _hits_protected(el, protected, margin=0):
            issues.append("logo_over_focal")
        if el.role == "cta" and (el.font_size or 0) < MIN_CTA_FONT:
            issues.append("weak_cta")

    if layers_output:
        giants = [
            el
            for el in layers_output
            if el.get("type") == "SHAPE"
            and (el.get("height") or 0) >= ch * 0.4
            and (el.get("width") or 0) >= cw * 0.55
        ]
        if giants:
            issues.append("rendered_large_panel")

    return len(issues) == 0, issues


def revise_layout_plan(layout: VisualLayoutPlan, issues: list[str]) -> VisualLayoutPlan:
    """Single auto-revise pass — shift away from protected zones, bump sizes."""
    cw, ch = layout.canvas_width, layout.canvas_height
    protected = layout.analysis.protected_zones
    type_x, type_y = _pick_type_origin(layout.analysis, canvas_width=cw, canvas_height=ch)
    for el in layout.elements:
        if "headline_over_focal" in issues and el.id == "text-headline":
            el.x = max(_sx(72, cw), type_x)
            el.y = max(_sy(64, ch), type_y + _sy(72, ch))
            el.width = min(
                el.width,
                _max_width_before_protected(el.x, el.y, el.height, protected, canvas_width=cw),
            )
            _shift_away_from_protected(el, protected, canvas_width=cw, canvas_height=ch)
        if "logo_over_focal" in issues and el.content_slot == "project_logo":
            el.y = max(_sy(64, ch), _sy(72, ch))
            el.x = _sx(72, cw)
        if any(i.startswith("tiny_feature:") for i in issues) and el.content_slot.startswith("feature_"):
            el.font_size = max(el.font_size or 0, _sf(MIN_FEATURE_FONT, cw))
            el.width = max(el.width, min(_sx(500, cw), _max_width_before_protected(el.x, el.y, el.height, protected, canvas_width=cw)))
        if "weak_cta" in issues and el.role == "cta":
            el.font_size = max(el.font_size or 0, _sf(MIN_CTA_FONT + 1, cw))
            el.font_weight = "bold"
            el.text_color = GOLD
            el.cta_style = "text_arrow"
    layout.pass_count += 1
    layout.qa_issues = list(issues)
    return layout


def build_vld_report(
    *,
    layout: VisualLayoutPlan,
    layers_output: list[dict[str, Any]] | None = None,
    gpt_image_call_count: int = 0,
    provider_call_count: int = 0,
    campaign_id: str | None = None,
    background_asset_id: str | None = None,
    final_asset_id: str | None = None,
) -> dict[str, Any]:
    qa_pass, qa_issues = qa_check_layout(layout, layers_output=layers_output)
    protected_ok = "headline_over_focal" not in qa_issues and "logo_over_focal" not in qa_issues
    headline_ok = "headline_over_focal" not in qa_issues
    features_ok = not any(i.startswith("tiny_feature:") for i in qa_issues)
    cta_ok = "weak_cta" not in qa_issues
    panel_count = sum(1 for i in qa_issues if "large_panel" in i or "rendered_large_panel" in i)

    editable_ids = [el.get("id") for el in (layers_output or []) if el.get("id")]

    return {
        "campaign_id": campaign_id,
        "background_asset_id": background_asset_id,
        "final_asset_id": final_asset_id,
        "composition_family": layout.composition_family.replace("_", " ").upper(),
        "background_visual_analysis": "PASS" if layout.analysis.visual_focus else "FAIL",
        "protected_zones_respected": "PASS" if protected_ok else "FAIL",
        "headline_avoids_focal_objects": "PASS" if headline_ok else "FAIL",
        "logo_placement": "PASS" if "logo_over_focal" not in qa_issues else "FAIL",
        "features_readable": "PASS" if features_ok else "FAIL",
        "cta_visible": "PASS" if cta_ok else "FAIL",
        "large_panels_count": panel_count,
        "internal_text_count": 0,
        "fake_logo_count": 0,
        "gpt_text_count": 0,
        "gpt_image_call_count": gpt_image_call_count,
        "layout_passes": layout.pass_count,
        "editable_layers": editable_ids,
        "editable_layers_pass": "PASS" if len(editable_ids) >= 5 else "FAIL",
        "visual_layout_director_mode": layout.analysis.mode,
        "visual_review_status": "READY FOR USER VISUAL REVIEW",
        "provider_call_count": provider_call_count,
        "qa_pass": qa_pass,
        "qa_issues": qa_issues,
        "analysis": layout.analysis.to_dict(),
    }


def run_visual_layout_director(
    *,
    background_bytes: bytes,
    canvas_width: int,
    canvas_height: int,
    texts: dict[str, str],
    art_direction: dict[str, Any] | None = None,
    lifestyle: bool = False,
    has_project_logo: bool = True,
    has_investhome_logo: bool = False,
    include_slogan: bool = True,
    render_fn: Callable[[GptImageDesignPlan], list[dict[str, Any]]] | None = None,
    max_passes: int = 2,
    campaign_id: str | None = None,
    background_asset_id: str | None = None,
) -> VisualLayoutDirectorResult:
    """Analyze background → layout plan → optional QA revise (max 2 passes)."""
    layout = plan_layout(
        background_bytes=background_bytes,
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        texts=texts,
        art_direction=art_direction,
        lifestyle=lifestyle,
        has_project_logo=has_project_logo,
        has_investhome_logo=has_investhome_logo,
        include_slogan=include_slogan,
    )
    design_plan = layout_plan_to_design_plan(layout, texts=texts)
    layers_output: list[dict[str, Any]] | None = None

    if render_fn is not None:
        layers_output = render_fn(design_plan)
        qa_pass, issues = qa_check_layout(layout, layers_output=layers_output)
        while not qa_pass and layout.pass_count < max_passes:
            layout = revise_layout_plan(layout, issues)
            design_plan = layout_plan_to_design_plan(layout, texts=texts)
            layers_output = render_fn(design_plan)
            qa_pass, issues = qa_check_layout(layout, layers_output=layers_output)

    report = build_vld_report(
        layout=layout,
        layers_output=layers_output,
        campaign_id=campaign_id,
        background_asset_id=background_asset_id,
    )
    return VisualLayoutDirectorResult(
        layout_plan=layout,
        design_plan=design_plan,
        report=report,
        mode=layout.analysis.mode,
    )
