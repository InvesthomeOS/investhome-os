"""Shared Design Plan — geometry + styles for GPT Image AND OS Final Composition.

Generated before the image call. GPT is told to leave these reserved regions empty
(no fake text/logos). OS places real TEXT / LOGO / CTA / SHAPE layers at the same pixels.
Art-direction labels vary; this is not a single default template (no x=600 y=500 56px white sans).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# Reference canvas for Instagram 4:5 recipes. Scaled to the actual canvas.
REF_W = 1080
REF_H = 1350

NAVY = "#1B2A4A"
GOLD = "#C4A35A"
IVORY = "#F4EFE6"
WHITE = "#FFFFFF"
SUBHEAD_INK = "#3D4A63"
MUTED_INK = "#6B7280"
LOCATION_GOLD = "#C4A35A"

ART_DIRECTIONS = (
    "editorial_luxury",
    "centered_editorial",
    "location_story",
    "architectural_minimal",
    "split_light_panel",
    "dusk_overlay",
)

ART_DIRECTION_LABELS = {
    "editorial_luxury": "Editorial Luxury",
    "centered_editorial": "Centered Editorial",
    "location_story": "Location Story",
    "architectural_minimal": "Architectural Minimal",
    "split_light_panel": "Split Light Panel",
    "dusk_overlay": "Dusk Overlay",
}


@dataclass
class ReservedRegion:
    name: str
    x: int
    y: int
    width: int
    height: int
    treatment: str = "empty"


@dataclass
class DesignPlanLayer:
    id: str
    type: str
    role: str
    x: int
    y: int
    width: int
    height: int
    z_index: int = 5
    content_slot: str = ""
    font_size: int | None = None
    font_family: str | None = None
    font_weight: str | None = None
    line_height: float | None = None
    letter_spacing: float | None = None
    color: str | None = None
    align: str | None = None
    background_color: str | None = None
    text_color: str | None = None
    border_radius: int | None = None
    fill: str | None = None
    shape_kind: str | None = None
    padding: int | None = None


@dataclass
class GptImageDesignPlan:
    variation: str
    label: str
    canvas_width: int
    canvas_height: int
    text_ground: str
    reserved: list[ReservedRegion] = field(default_factory=list)
    layers: list[DesignPlanLayer] = field(default_factory=list)
    art_notes: list[str] = field(default_factory=list)


def _sx(n: float, w: int) -> int:
    return max(0, int(round(n * w / REF_W)))


def _sy(n: float, h: int) -> int:
    return max(0, int(round(n * h / REF_H)))


def _sf(n: float, w: int) -> int:
    return max(10, int(round(n * w / REF_W)))


def _clamp_box(x: int, y: int, width: int, height: int, cw: int, ch: int) -> tuple[int, int, int, int]:
    w = max(1, min(width, cw))
    h = max(1, min(height, ch))
    x = max(0, min(x, max(0, cw - w)))
    y = max(0, min(y, max(0, ch - h)))
    return x, y, w, h


def choose_art_direction(
    *,
    instruction: str = "",
    composition_family: str = "",
    objective: str = "",
    campaign_angle: str = "",
) -> str:
    """Pick an internal art-direction label. Not four hardcoded template slots."""
    hay = f"{instruction} {composition_family} {objective} {campaign_angle}".lower()
    family = (composition_family or "").strip().upper()

    # Acceptance-quality Temple location/premium posts → editorial luxury (serif navy, gold).
    if any(k in hay for k in ("washington", "lokasyon", "location")) and any(
        k in hay for k in ("premium", "luxury", "lüks", "luks")
    ):
        return "editorial_luxury"

    family_map = {
        "LUXURY_BRAND": "editorial_luxury",
        "EDITORIAL_HERO": "editorial_luxury",
        "STATEMENT_LAYOUT": "centered_editorial",
        "IMAGE_DOMINANT": "centered_editorial",
        "LOWER_THIRD": "location_story",
        "LIFESTYLE_EDITORIAL": "location_story",
        "ARCHITECTURAL_MINIMAL": "architectural_minimal",
        "ASYMMETRIC_EDITORIAL": "split_light_panel",
        "SPLIT_LAYOUT": "split_light_panel",
        "OVERLAY_PANEL": "dusk_overlay",
    }
    if family in family_map:
        return family_map[family]

    if any(k in hay for k in ("minimal", "architecture", "facade", "cephe")):
        return "architectural_minimal"
    if any(k in hay for k in ("center", "merkez", "brand", "marka")):
        return "centered_editorial"
    if any(k in hay for k in ("washington", "lokasyon", "location", "adres")):
        seed = sum(ord(c) for c in (instruction or "loc")) % 2
        return ("editorial_luxury", "location_story")[seed]
    if any(k in hay for k in ("night", "gece", "dusk")):
        return "dusk_overlay"

    options = ART_DIRECTIONS
    idx = sum(ord(c) for c in (instruction or "plan")) % len(options)
    return options[idx]


def _layer(**kwargs: Any) -> DesignPlanLayer:
    return DesignPlanLayer(**kwargs)


def _build_layers_editorial_luxury(cw: int, ch: int) -> tuple[list[ReservedRegion], list[DesignPlanLayer], str]:
    """Left editorial: serif navy ~70px at ~x=90 y=180, gold accent, premium whitespace."""
    reserved = [
        ReservedRegion("project_logo", _sx(90, cw), _sy(72, ch), _sx(220, cw), _sy(72, ch), "empty"),
        ReservedRegion(
            "type_column",
            _sx(64, cw),
            _sy(150, ch),
            _sx(780, cw),
            _sy(460, ch),
            "light_empty",
        ),
        ReservedRegion("slogan", _sx(90, cw), _sy(1264, ch), _sx(520, cw), _sy(40, ch), "empty"),
        ReservedRegion("investhome_logo", _sx(820, cw), _sy(1260, ch), _sx(170, cw), _sy(48, ch), "empty"),
    ]
    layers = [
        _layer(
            id="logo-project",
            type="IMAGE",
            role="logo",
            content_slot="project_logo",
            x=_sx(90, cw),
            y=_sy(80, ch),
            width=_sx(200, cw),
            height=_sy(56, ch),
            z_index=8,
        ),
        _layer(
            id="text-headline",
            type="TEXT",
            role="headline",
            content_slot="headline",
            x=_sx(90, cw),
            y=_sy(180, ch),
            width=_sx(780, cw),
            height=_sy(168, ch),
            font_size=_sf(70, cw),
            font_family="serif",
            font_weight="bold",
            line_height=1.08,
            letter_spacing=-1.2,
            color=NAVY,
            align="left",
            z_index=5,
        ),
        _layer(
            id="text-subhead",
            type="TEXT",
            role="body",
            content_slot="subhead",
            x=_sx(90, cw),
            y=_sy(358, ch),
            width=_sx(680, cw),
            height=_sy(56, ch),
            font_size=_sf(22, cw),
            font_family="sans",
            font_weight="normal",
            line_height=1.35,
            color=SUBHEAD_INK,
            align="left",
            z_index=5,
        ),
        _layer(
            id="shape-accent",
            type="SHAPE",
            role="decoration",
            content_slot="shape",
            x=_sx(90, cw),
            y=_sy(428, ch),
            width=_sx(72, cw),
            height=max(2, _sy(3, ch)),
            fill=GOLD,
            shape_kind="line",
            z_index=4,
        ),
        _layer(
            id="text-location",
            type="TEXT",
            role="eyebrow",
            content_slot="location",
            x=_sx(90, cw),
            y=_sy(444, ch),
            width=_sx(560, cw),
            height=_sy(32, ch),
            font_size=_sf(15, cw),
            font_family="sans",
            font_weight="medium",
            letter_spacing=2.2,
            color=LOCATION_GOLD,
            align="left",
            z_index=5,
        ),
        _layer(
            id="cta-primary",
            type="BUTTON",
            role="cta",
            content_slot="cta",
            x=_sx(90, cw),
            y=_sy(500, ch),
            width=_sx(240, cw),
            height=_sy(48, ch),
            font_size=_sf(15, cw),
            font_family="sans",
            font_weight="semibold",
            background_color=GOLD,
            text_color=NAVY,
            border_radius=_sf(4, cw),
            padding=_sx(16, cw),
            z_index=7,
        ),
        _layer(
            id="text-slogan",
            type="TEXT",
            role="brand",
            content_slot="slogan",
            x=_sx(90, cw),
            y=_sy(1278, ch),
            width=_sx(520, cw),
            height=_sy(28, ch),
            font_size=_sf(13, cw),
            font_family="sans",
            font_weight="normal",
            color=MUTED_INK,
            align="left",
            z_index=6,
        ),
        _layer(
            id="logo-investhome",
            type="IMAGE",
            role="logo",
            content_slot="investhome_logo",
            x=_sx(860, cw),
            y=_sy(1272, ch),
            width=_sx(130, cw),
            height=_sy(36, ch),
            z_index=8,
        ),
    ]
    return reserved, layers, "light"


def _build_layers_centered_editorial(cw: int, ch: int) -> tuple[list[ReservedRegion], list[DesignPlanLayer], str]:
    reserved = [
        ReservedRegion("project_logo", _sx(390, cw), _sy(70, ch), _sx(300, cw), _sy(70, ch), "empty"),
        ReservedRegion("type_block", _sx(120, cw), _sy(170, ch), _sx(840, cw), _sy(420, ch), "light_empty"),
        ReservedRegion("cta", _sx(390, cw), _sy(560, ch), _sx(300, cw), _sy(52, ch), "empty"),
        ReservedRegion("slogan", _sx(240, cw), _sy(1268, ch), _sx(600, cw), _sy(36, ch), "empty"),
    ]
    layers = [
        _layer(
            id="logo-project",
            type="IMAGE",
            role="logo",
            content_slot="project_logo",
            x=_sx(430, cw),
            y=_sy(78, ch),
            width=_sx(220, cw),
            height=_sy(56, ch),
            z_index=8,
        ),
        _layer(
            id="text-headline",
            type="TEXT",
            role="headline",
            content_slot="headline",
            x=_sx(140, cw),
            y=_sy(200, ch),
            width=_sx(800, cw),
            height=_sy(160, ch),
            font_size=_sf(62, cw),
            font_family="serif",
            font_weight="bold",
            line_height=1.1,
            letter_spacing=-0.6,
            color=NAVY,
            align="center",
            z_index=5,
        ),
        _layer(
            id="text-subhead",
            type="TEXT",
            role="body",
            content_slot="subhead",
            x=_sx(180, cw),
            y=_sy(372, ch),
            width=_sx(720, cw),
            height=_sy(52, ch),
            font_size=_sf(20, cw),
            font_family="sans",
            font_weight="normal",
            color=SUBHEAD_INK,
            align="center",
            z_index=5,
        ),
        _layer(
            id="shape-accent",
            type="SHAPE",
            role="decoration",
            content_slot="shape",
            x=_sx(504, cw),
            y=_sy(436, ch),
            width=_sx(72, cw),
            height=max(2, _sy(3, ch)),
            fill=GOLD,
            shape_kind="line",
            z_index=4,
        ),
        _layer(
            id="text-location",
            type="TEXT",
            role="eyebrow",
            content_slot="location",
            x=_sx(200, cw),
            y=_sy(452, ch),
            width=_sx(680, cw),
            height=_sy(32, ch),
            font_size=_sf(14, cw),
            font_family="sans",
            font_weight="medium",
            letter_spacing=2.4,
            color=GOLD,
            align="center",
            z_index=5,
        ),
        _layer(
            id="cta-primary",
            type="BUTTON",
            role="cta",
            content_slot="cta",
            x=_sx(400, cw),
            y=_sy(512, ch),
            width=_sx(280, cw),
            height=_sy(48, ch),
            font_size=_sf(15, cw),
            font_family="sans",
            font_weight="semibold",
            background_color=NAVY,
            text_color=WHITE,
            border_radius=_sf(4, cw),
            z_index=7,
        ),
        _layer(
            id="text-slogan",
            type="TEXT",
            role="brand",
            content_slot="slogan",
            x=_sx(240, cw),
            y=_sy(1278, ch),
            width=_sx(600, cw),
            height=_sy(28, ch),
            font_size=_sf(13, cw),
            font_family="sans",
            color=MUTED_INK,
            align="center",
            z_index=6,
        ),
        _layer(
            id="logo-investhome",
            type="IMAGE",
            role="logo",
            content_slot="investhome_logo",
            x=_sx(470, cw),
            y=_sy(1228, ch),
            width=_sx(140, cw),
            height=_sy(36, ch),
            z_index=8,
        ),
    ]
    return reserved, layers, "light"


def _build_layers_location_story(cw: int, ch: int) -> tuple[list[ReservedRegion], list[DesignPlanLayer], str]:
    reserved = [
        ReservedRegion("project_logo", _sx(88, cw), _sy(72, ch), _sx(220, cw), _sy(68, ch), "empty"),
        ReservedRegion("lower_type", _sx(64, cw), _sy(820, ch), _sx(920, cw), _sy(380, ch), "dark_quiet"),
        ReservedRegion("investhome_logo", _sx(820, cw), _sy(1264, ch), _sx(170, cw), _sy(48, ch), "empty"),
    ]
    layers = [
        _layer(
            id="logo-project",
            type="IMAGE",
            role="logo",
            content_slot="project_logo",
            x=_sx(90, cw),
            y=_sy(80, ch),
            width=_sx(190, cw),
            height=_sy(52, ch),
            z_index=8,
        ),
        _layer(
            id="text-location",
            type="TEXT",
            role="eyebrow",
            content_slot="location",
            x=_sx(90, cw),
            y=_sy(860, ch),
            width=_sx(720, cw),
            height=_sy(28, ch),
            font_size=_sf(14, cw),
            font_family="sans",
            font_weight="medium",
            letter_spacing=2.6,
            color=GOLD,
            align="left",
            z_index=5,
        ),
        _layer(
            id="text-headline",
            type="TEXT",
            role="headline",
            content_slot="headline",
            x=_sx(90, cw),
            y=_sy(896, ch),
            width=_sx(860, cw),
            height=_sy(130, ch),
            font_size=_sf(48, cw),
            font_family="serif",
            font_weight="bold",
            line_height=1.12,
            color=WHITE,
            align="left",
            z_index=5,
        ),
        _layer(
            id="text-subhead",
            type="TEXT",
            role="body",
            content_slot="subhead",
            x=_sx(90, cw),
            y=_sy(1036, ch),
            width=_sx(720, cw),
            height=_sy(48, ch),
            font_size=_sf(18, cw),
            font_family="sans",
            color="#E8E4DC",
            align="left",
            z_index=5,
        ),
        _layer(
            id="cta-primary",
            type="BUTTON",
            role="cta",
            content_slot="cta",
            x=_sx(90, cw),
            y=_sy(1100, ch),
            width=_sx(230, cw),
            height=_sy(46, ch),
            font_size=_sf(14, cw),
            font_family="sans",
            font_weight="semibold",
            background_color=GOLD,
            text_color=NAVY,
            border_radius=_sf(4, cw),
            z_index=7,
        ),
        _layer(
            id="text-slogan",
            type="TEXT",
            role="brand",
            content_slot="slogan",
            x=_sx(90, cw),
            y=_sy(1278, ch),
            width=_sx(520, cw),
            height=_sy(28, ch),
            font_size=_sf(13, cw),
            font_family="sans",
            color="#D1D5DB",
            align="left",
            z_index=6,
        ),
        _layer(
            id="logo-investhome",
            type="IMAGE",
            role="logo",
            content_slot="investhome_logo",
            x=_sx(860, cw),
            y=_sy(1272, ch),
            width=_sx(130, cw),
            height=_sy(36, ch),
            z_index=8,
        ),
    ]
    return reserved, layers, "dark"


def _build_layers_architectural_minimal(cw: int, ch: int) -> tuple[list[ReservedRegion], list[DesignPlanLayer], str]:
    reserved = [
        ReservedRegion("project_logo", _sx(88, cw), _sy(70, ch), _sx(180, cw), _sy(56, ch), "empty"),
        ReservedRegion("type_sparse", _sx(70, cw), _sy(130, ch), _sx(620, cw), _sy(280, ch), "light_empty"),
        ReservedRegion("slogan", _sx(88, cw), _sy(1270, ch), _sx(500, cw), _sy(36, ch), "empty"),
    ]
    layers = [
        _layer(
            id="logo-project",
            type="IMAGE",
            role="logo",
            content_slot="project_logo",
            x=_sx(90, cw),
            y=_sy(76, ch),
            width=_sx(160, cw),
            height=_sy(44, ch),
            z_index=8,
        ),
        _layer(
            id="text-headline",
            type="TEXT",
            role="headline",
            content_slot="headline",
            x=_sx(90, cw),
            y=_sy(150, ch),
            width=_sx(580, cw),
            height=_sy(120, ch),
            font_size=_sf(42, cw),
            font_family="serif",
            font_weight="bold",
            line_height=1.12,
            color=NAVY,
            align="left",
            z_index=5,
        ),
        _layer(
            id="shape-line",
            type="SHAPE",
            role="decoration",
            content_slot="shape",
            x=_sx(90, cw),
            y=_sy(286, ch),
            width=_sx(48, cw),
            height=max(2, _sy(2, ch)),
            fill=GOLD,
            shape_kind="line",
            z_index=4,
        ),
        _layer(
            id="text-subhead",
            type="TEXT",
            role="body",
            content_slot="subhead",
            x=_sx(90, cw),
            y=_sy(304, ch),
            width=_sx(520, cw),
            height=_sy(44, ch),
            font_size=_sf(16, cw),
            font_family="sans",
            color=SUBHEAD_INK,
            align="left",
            z_index=5,
        ),
        _layer(
            id="cta-primary",
            type="BUTTON",
            role="cta",
            content_slot="cta",
            x=_sx(90, cw),
            y=_sy(368, ch),
            width=_sx(200, cw),
            height=_sy(42, ch),
            font_size=_sf(13, cw),
            font_family="sans",
            font_weight="medium",
            background_color=NAVY,
            text_color=WHITE,
            border_radius=_sf(2, cw),
            z_index=7,
        ),
        _layer(
            id="text-slogan",
            type="TEXT",
            role="brand",
            content_slot="slogan",
            x=_sx(90, cw),
            y=_sy(1280, ch),
            width=_sx(480, cw),
            height=_sy(24, ch),
            font_size=_sf(12, cw),
            font_family="sans",
            color=MUTED_INK,
            align="left",
            z_index=6,
        ),
        _layer(
            id="logo-investhome",
            type="IMAGE",
            role="logo",
            content_slot="investhome_logo",
            x=_sx(870, cw),
            y=_sy(1274, ch),
            width=_sx(120, cw),
            height=_sy(32, ch),
            z_index=8,
        ),
    ]
    return reserved, layers, "light"


def _build_layers_split_light_panel(cw: int, ch: int) -> tuple[list[ReservedRegion], list[DesignPlanLayer], str]:
    reserved = [
        ReservedRegion("left_panel", _sx(0, cw), _sy(0, ch), _sx(460, cw), _sy(1350, ch), "light_empty"),
        ReservedRegion("investhome_logo", _sx(40, cw), _sy(1264, ch), _sx(160, cw), _sy(44, ch), "empty"),
    ]
    layers = [
        _layer(
            id="logo-project",
            type="IMAGE",
            role="logo",
            content_slot="project_logo",
            x=_sx(48, cw),
            y=_sy(80, ch),
            width=_sx(180, cw),
            height=_sy(52, ch),
            z_index=8,
        ),
        _layer(
            id="text-headline",
            type="TEXT",
            role="headline",
            content_slot="headline",
            x=_sx(48, cw),
            y=_sy(220, ch),
            width=_sx(380, cw),
            height=_sy(240, ch),
            font_size=_sf(44, cw),
            font_family="serif",
            font_weight="bold",
            line_height=1.14,
            color=NAVY,
            align="left",
            z_index=5,
        ),
        _layer(
            id="text-subhead",
            type="TEXT",
            role="body",
            content_slot="subhead",
            x=_sx(48, cw),
            y=_sy(480, ch),
            width=_sx(360, cw),
            height=_sy(80, ch),
            font_size=_sf(16, cw),
            font_family="sans",
            color=SUBHEAD_INK,
            align="left",
            z_index=5,
        ),
        _layer(
            id="shape-accent",
            type="SHAPE",
            role="decoration",
            content_slot="shape",
            x=_sx(48, cw),
            y=_sy(580, ch),
            width=_sx(56, cw),
            height=max(2, _sy(3, ch)),
            fill=GOLD,
            shape_kind="line",
            z_index=4,
        ),
        _layer(
            id="text-location",
            type="TEXT",
            role="eyebrow",
            content_slot="location",
            x=_sx(48, cw),
            y=_sy(598, ch),
            width=_sx(340, cw),
            height=_sy(28, ch),
            font_size=_sf(13, cw),
            font_family="sans",
            letter_spacing=1.8,
            color=GOLD,
            align="left",
            z_index=5,
        ),
        _layer(
            id="cta-primary",
            type="BUTTON",
            role="cta",
            content_slot="cta",
            x=_sx(48, cw),
            y=_sy(660, ch),
            width=_sx(210, cw),
            height=_sy(46, ch),
            font_size=_sf(14, cw),
            font_family="sans",
            font_weight="semibold",
            background_color=GOLD,
            text_color=NAVY,
            border_radius=_sf(4, cw),
            z_index=7,
        ),
        _layer(
            id="text-slogan",
            type="TEXT",
            role="brand",
            content_slot="slogan",
            x=_sx(48, cw),
            y=_sy(1278, ch),
            width=_sx(360, cw),
            height=_sy(28, ch),
            font_size=_sf(12, cw),
            font_family="sans",
            color=MUTED_INK,
            align="left",
            z_index=6,
        ),
        _layer(
            id="logo-investhome",
            type="IMAGE",
            role="logo",
            content_slot="investhome_logo",
            x=_sx(300, cw),
            y=_sy(1272, ch),
            width=_sx(120, cw),
            height=_sy(32, ch),
            z_index=8,
        ),
    ]
    return reserved, layers, "light"


def _build_layers_dusk_overlay(cw: int, ch: int) -> tuple[list[ReservedRegion], list[DesignPlanLayer], str]:
    reserved = [
        ReservedRegion("project_logo", _sx(88, cw), _sy(72, ch), _sx(200, cw), _sy(64, ch), "empty"),
        ReservedRegion("lower_third", _sx(0, cw), _sy(780, ch), _sx(1080, cw), _sy(570, ch), "dark_quiet"),
    ]
    layers = [
        _layer(
            id="logo-project",
            type="IMAGE",
            role="logo",
            content_slot="project_logo",
            x=_sx(90, cw),
            y=_sy(80, ch),
            width=_sx(180, cw),
            height=_sy(50, ch),
            z_index=8,
        ),
        _layer(
            id="text-headline",
            type="TEXT",
            role="headline",
            content_slot="headline",
            x=_sx(90, cw),
            y=_sy(860, ch),
            width=_sx(900, cw),
            height=_sy(140, ch),
            font_size=_sf(56, cw),
            font_family="serif",
            font_weight="bold",
            line_height=1.1,
            color=WHITE,
            align="left",
            z_index=5,
        ),
        _layer(
            id="text-subhead",
            type="TEXT",
            role="body",
            content_slot="subhead",
            x=_sx(90, cw),
            y=_sy(1010, ch),
            width=_sx(760, cw),
            height=_sy(48, ch),
            font_size=_sf(18, cw),
            font_family="sans",
            color="#E5E7EB",
            align="left",
            z_index=5,
        ),
        _layer(
            id="cta-primary",
            type="BUTTON",
            role="cta",
            content_slot="cta",
            x=_sx(90, cw),
            y=_sy(1080, ch),
            width=_sx(240, cw),
            height=_sy(48, ch),
            font_size=_sf(14, cw),
            font_family="sans",
            font_weight="semibold",
            background_color=GOLD,
            text_color=NAVY,
            border_radius=_sf(4, cw),
            z_index=7,
        ),
        _layer(
            id="text-slogan",
            type="TEXT",
            role="brand",
            content_slot="slogan",
            x=_sx(90, cw),
            y=_sy(1278, ch),
            width=_sx(500, cw),
            height=_sy(28, ch),
            font_size=_sf(13, cw),
            font_family="sans",
            color="#D1D5DB",
            align="left",
            z_index=6,
        ),
        _layer(
            id="logo-investhome",
            type="IMAGE",
            role="logo",
            content_slot="investhome_logo",
            x=_sx(860, cw),
            y=_sy(1272, ch),
            width=_sx(130, cw),
            height=_sy(36, ch),
            z_index=8,
        ),
    ]
    return reserved, layers, "dark"


_BUILDERS = {
    "editorial_luxury": _build_layers_editorial_luxury,
    "centered_editorial": _build_layers_centered_editorial,
    "location_story": _build_layers_location_story,
    "architectural_minimal": _build_layers_architectural_minimal,
    "split_light_panel": _build_layers_split_light_panel,
    "dusk_overlay": _build_layers_dusk_overlay,
}


def build_gpt_image_design_plan(
    *,
    canvas_width: int,
    canvas_height: int,
    art_direction: str | None = None,
    instruction: str = "",
    composition_family: str = "",
    objective: str = "",
    campaign_angle: str = "",
    has_project_logo: bool = True,
    has_investhome_logo: bool = False,
    include_slogan: bool = True,
) -> GptImageDesignPlan:
    cw = max(8, int(canvas_width or REF_W))
    ch = max(8, int(canvas_height or REF_H))
    variation = art_direction if art_direction in _BUILDERS else choose_art_direction(
        instruction=instruction,
        composition_family=composition_family,
        objective=objective,
        campaign_angle=campaign_angle,
    )
    builder = _BUILDERS.get(variation, _build_layers_editorial_luxury)
    reserved, layers, text_ground = builder(cw, ch)

    kept: list[DesignPlanLayer] = []
    for layer in layers:
        x, y, w, h = _clamp_box(layer.x, layer.y, layer.width, layer.height, cw, ch)
        layer.x, layer.y, layer.width, layer.height = x, y, w, h
        if layer.content_slot == "project_logo" and not has_project_logo:
            continue
        if layer.content_slot == "investhome_logo" and not has_investhome_logo:
            continue
        if layer.content_slot == "slogan" and not include_slogan:
            continue
        kept.append(layer)

    notes = {
        "editorial_luxury": [
            "Editorial serif headline, premium left whitespace, gold accent rule, luxury real-estate.",
            "Keep the left type column as calm cream/ivory negative space — no facade, no fake type.",
            "Place the real building in the complementary area (right/center/lower). Do not redesign it.",
        ],
        "centered_editorial": [
            "Centered editorial with brand lockup, location mark, gold/navy/white.",
            "Keep the central type block as light empty space. Building may frame above/below/sides.",
        ],
        "location_story": [
            "Building-dominant. Quiet darkened lower band for OS type. Gold location mark.",
            "Do not pack the lower third with fake addresses or map pins.",
        ],
        "architectural_minimal": [
            "Sparse type, generous air, thin gold rule. Building remains the photograph.",
        ],
        "split_light_panel": [
            "Left light panel is reserved for OS type. Building occupies the right side only.",
        ],
        "dusk_overlay": [
            "Quiet darkened lower third for OS type. Do not rasterize copy into the dusk band.",
        ],
    }

    return GptImageDesignPlan(
        variation=variation,
        label=ART_DIRECTION_LABELS.get(variation, variation),
        canvas_width=cw,
        canvas_height=ch,
        text_ground=text_ground,
        reserved=reserved,
        layers=kept,
        art_notes=list(notes.get(variation, [])),
    )


def design_plan_to_dict(plan: GptImageDesignPlan) -> dict[str, Any]:
    return {
        "variation": plan.variation,
        "label": plan.label,
        "canvas_width": plan.canvas_width,
        "canvas_height": plan.canvas_height,
        "text_ground": plan.text_ground,
        "reserved": [asdict(row) for row in plan.reserved],
        "layers": [asdict(row) for row in plan.layers],
        "art_notes": list(plan.art_notes),
    }


def format_design_plan_for_prompt(plan: dict[str, Any] | GptImageDesignPlan | None) -> list[str]:
    """Exact reserved-region instructions shared with GPT Image."""
    if plan is None:
        return []
    if isinstance(plan, GptImageDesignPlan):
        payload = design_plan_to_dict(plan)
    else:
        payload = plan
    variation = str(payload.get("label") or payload.get("variation") or "Editorial")
    cw = payload.get("canvas_width") or REF_W
    ch = payload.get("canvas_height") or REF_H
    lines = [
        f"SHARED DESIGN PLAN (single source of truth — OS typesets at these exact pixels, {cw}x{ch}):",
        f"Art direction: {variation}.",
        "Leave these reserved rectangles EMPTY of text, numbers, logos, wordmarks, and CTAs:",
    ]
    for row in payload.get("reserved") or []:
        if not isinstance(row, dict):
            continue
        name = row.get("name") or "region"
        treatment = row.get("treatment") or "empty"
        hint = "calm cream/ivory negative space, no facade"
        if treatment == "dark_quiet":
            hint = "quiet darkened band, no fake type"
        elif treatment == "empty":
            hint = "keep empty"
        lines.append(
            f"- {name}: x={row.get('x')} y={row.get('y')} w={row.get('width')} h={row.get('height')} ({hint})"
        )
    for note in payload.get("art_notes") or []:
        lines.append(f"- {note}")
    lines.append(
        "Compose the real building into the complementary (non-reserved) area. "
        "Do not paint fake headlines, slogans, addresses, or logos — OS will place real layers."
    )
    return lines
