"""Art Direction Plan v2 — GPT Image and OS share one campaign plan.

Not a coordinate dump. The Art Director chooses composition type, focal point,
negative space, groups, typography, and decorative language from prompt + image
role. GPT paints the campaign background to those zones. OS typesets real
editable TEXT / LOGO / CTA / SHAPE layers at the same pixels.
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

COMPOSITION_TYPES = (
    "editorial_hero",
    "location_story",
    "architecture_focus",
    "minimal_luxury",
    "investment_story",
    "lifestyle",
    "neighborhood",
    "project_intro",
    "full_bleed",
    "split_editorial",
)

COMPOSITION_LABELS = {
    "editorial_hero": "EDITORIAL HERO",
    "location_story": "LOCATION STORY",
    "architecture_focus": "ARCHITECTURE FOCUS",
    "minimal_luxury": "MINIMAL LUXURY",
    "investment_story": "INVESTMENT STORY",
    "lifestyle": "LIFESTYLE",
    "neighborhood": "NEIGHBORHOOD",
    "project_intro": "PROJECT INTRO",
    "full_bleed": "FULL BLEED",
    "split_editorial": "SPLIT EDITORIAL",
}

_LEGACY_ALIASES = {
    "editorial_luxury": "editorial_hero",
    "centered_editorial": "project_intro",
    "architectural_minimal": "architecture_focus",
    "architectural_hero": "architecture_focus",
    "split_light_panel": "split_editorial",
    "dusk_overlay": "location_story",
    "brand_campaign": "project_intro",
    "data_location": "investment_story",
}

# Logo must stay visible on a 1080 canvas — 168x44 vanished in the corner.
MIN_PROJECT_LOGO_W_REF = 248
MIN_PROJECT_LOGO_H_REF = 72
MIN_SAFE_REF = {"top": 64, "left": 72, "right": 72, "bottom": 72}
MAX_VERTICAL_RULE_H_REF = 40
DECORATION_PURPOSES = frozenset({"hierarchy", "direction", "framing", "brand_signature"})
_METADATA_PREFIXES = (
    "project name:",
    "project_name:",
    "project:",
    "asset id:",
    "asset_id:",
    "linked_project_id:",
    "folder_category:",
    "filename:",
    "tags:",
    "source:",
    "role:",
)
_DROP_METADATA_PREFIXES = (
    "project name:",
    "project_name:",
    "project:",
    "asset id:",
    "asset_id:",
    "linked_project_id:",
    "folder_category:",
    "filename:",
    "tags:",
    "source:",
    "role:",
)
_STRIP_LABEL_PREFIXES = (
    "city:",
    "country:",
    "address:",
    "label:",
    "location:",
    "adres:",
    "şehir:",
    "sehir:",
)
_CTA_STYLE_BY_COMPOSITION = {
    "editorial_hero": "editorial_link",
    "location_story": "pill",
    "architecture_focus": "outline",
    "minimal_luxury": "editorial_link",
    "investment_story": "text_arrow",
    "lifestyle": "text_arrow",
    "neighborhood": "outline",
    "project_intro": "pill",
    "full_bleed": "editorial_link",
    "split_editorial": "text_arrow",
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
class DesignZone:
    name: str
    x: int
    y: int
    width: int
    height: int
    treatment: str = ""


@dataclass
class ElementGroup:
    name: str
    members: list[str] = field(default_factory=list)
    alignment: str = "left"
    gap: int = 16


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
    group: str = ""
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
    cta_style: str | None = None
    decoration_purpose: str | None = None
    opacity: float | None = None
    text_runs: list[dict[str, Any]] | None = None
    static_content: str | None = None


@dataclass
class GptImageDesignPlan:
    variation: str
    label: str
    composition_type: str
    canvas_width: int
    canvas_height: int
    text_ground: str
    visual_focal_point: str = ""
    negative_space: str = ""
    visual_balance: str = ""
    typography_scale: str = "editorial"
    typography_contrast: str = "high"
    contrast_strategy: str = ""
    headline_line_breaks: list[str] = field(default_factory=list)
    element_relationships: list[str] = field(default_factory=list)
    decorative_elements: list[str] = field(default_factory=list)
    overlap_rules: list[str] = field(default_factory=list)
    graphic_language: list[str] = field(default_factory=list)
    brand_color_relationships: list[str] = field(default_factory=list)
    safe_margins: dict[str, int] = field(default_factory=dict)
    content_zone: DesignZone | None = None
    image_zone: DesignZone | None = None
    headline_zone: DesignZone | None = None
    brand_zone: DesignZone | None = None
    cta_zone: DesignZone | None = None
    groups: list[ElementGroup] = field(default_factory=list)
    reserved: list[ReservedRegion] = field(default_factory=list)
    layers: list[DesignPlanLayer] = field(default_factory=list)
    art_notes: list[str] = field(default_factory=list)
    needs_scrim: bool = False
    localized_scrim_only: bool = False
    visual_review_status: str = "READY FOR USER VISUAL REVIEW"
    quality_corrections: list[str] = field(default_factory=list)


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


def _zone(name: str, x: int, y: int, w: int, h: int, treatment: str = "") -> DesignZone:
    return DesignZone(name=name, x=x, y=y, width=w, height=h, treatment=treatment)


def _group(name: str, members: list[str], alignment: str, gap: int) -> ElementGroup:
    return ElementGroup(name=name, members=members, alignment=alignment, gap=gap)


def _layer(**kwargs: Any) -> DesignPlanLayer:
    return DesignPlanLayer(**kwargs)


def decide_headline_line_breaks(
    headline: str,
    *,
    typography_scale: str = "editorial",
    composition_type: str = "",
) -> list[str]:
    """Intentional breaks from space + composition — not always one line, not always two."""
    text = " ".join((headline or "").split())
    if not text:
        return []
    words = text.split()
    n = len(words)
    scale = (typography_scale or "editorial").strip().lower()
    composition = (composition_type or "").strip().lower()

    if n == 1:
        return [text]
    if scale == "minimal" and len(text) <= 24:
        return [text]
    if scale == "modern" and n <= 3 and len(text) <= 26:
        return [text]
    if composition in {"architecture_focus", "architectural_hero", "minimal_luxury", "full_bleed"} and n <= 3 and len(text) <= 22:
        return [text]

    if scale == "editorial" or composition in {"editorial_hero", "brand_campaign", "project_intro", "split_editorial"}:
        if n == 2:
            return list(words)
        if n == 3:
            last = words[-1]
            if len(last) >= 4:
                return [" ".join(words[:-1]), last]
            return [words[0], " ".join(words[1:])]
        mid = max(1, n // 2)
        return [" ".join(words[:mid]), " ".join(words[mid:])]

    if n >= 4:
        mid = max(1, (n + 1) // 2)
        return [" ".join(words[:mid]), " ".join(words[mid:])]
    return [text]


def format_headline_for_plan(headline: str, plan: GptImageDesignPlan | None) -> str:
    text = " ".join((headline or "").replace("\n", " ").split())
    if not text:
        return ""
    planned = [str(ln).strip() for ln in ((plan.headline_line_breaks if plan else None) or []) if str(ln).strip()]
    compact_plan = " ".join(planned)
    if planned and compact_plan.lower() == text.lower():
        return "\n".join(planned)
    scale = plan.typography_scale if plan else "editorial"
    composition = plan.variation if plan else ""
    breaks = decide_headline_line_breaks(text, typography_scale=scale, composition_type=composition)
    return "\n".join(breaks) if breaks else text


def choose_composition_type(
    *,
    instruction: str = "",
    composition_family: str = "",
    objective: str = "",
    campaign_angle: str = "",
) -> str:
    """Choose a composition family from prompt + campaign signals. Never a random template pick."""
    hay = f"{instruction} {composition_family} {objective} {campaign_angle}".lower()
    family = (composition_family or "").strip().upper().replace(" ", "_").replace("-", "_")
    loc = any(
        k in hay
        for k in (
            "washington",
            "lokasyon",
            "location",
            "adres",
            "konum",
            "merkezi lokasyon",
        )
    )
    premium = any(k in hay for k in ("premium", "luxury", "lüks", "luks", "editorial"))

    family_map = {
        "LUXURY_BRAND": "editorial_hero",
        "EDITORIAL_HERO": "editorial_hero",
        "EDITORIAL": "editorial_hero",
        "STATEMENT_LAYOUT": "project_intro",
        "IMAGE_DOMINANT": "architecture_focus",
        "LOWER_THIRD": "location_story",
        "LOCATION": "location_story",
        "LIFESTYLE_EDITORIAL": "lifestyle",
        "ARCHITECTURAL_MINIMAL": "architecture_focus",
        "ARCHITECTURE_FOCUS": "architecture_focus",
        "ASYMMETRIC_EDITORIAL": "split_editorial",
        "SPLIT_LAYOUT": "split_editorial",
        "SPLIT_EDITORIAL": "split_editorial",
        "OVERLAY_PANEL": "location_story",
        "INVESTMENT_GRID": "investment_story",
        "INVESTMENT": "investment_story",
        "INVESTMENT_STORY": "investment_story",
        "FLOATING_DATA": "investment_story",
        "MINIMAL_HERO": "minimal_luxury",
        "MINIMAL_LUXURY": "minimal_luxury",
        "NEIGHBORHOOD": "neighborhood",
        "PROJECT_INTRO": "project_intro",
        "BRAND_CAMPAIGN": "project_intro",
        "FULL_BLEED": "full_bleed",
    }
    if family in family_map:
        mapped = family_map[family]
        # Location briefs must not collapse into EDITORIAL HERO just because they are premium.
        if mapped == "editorial_hero" and loc:
            return "location_story"
        return mapped

    if any(k in hay for k in ("mahalle", "neighborhood", "komşu", "komsu")):
        return "neighborhood"
    if loc or any(k in hay for k in ("adres", "city center", "merkez")):
        return "location_story"
    if any(k in hay for k in ("lifestyle", "yaşam", "yasam", "interior", "ritüel", "rituel")):
        return "lifestyle"
    if any(k in hay for k in ("yatırım", "yatirim", "investment", "investor")):
        return "investment_story"
    if any(k in hay for k in ("split", "iki kolon", "iki panel")):
        return "split_editorial"
    if any(k in hay for k in ("full bleed", "full-bleed", "kenarlara", "cephe doldur")):
        return "full_bleed"
    if any(k in hay for k in ("architecture", "architectural", "facade", "cephe", "mimari")):
        return "architecture_focus"
    if any(k in hay for k in ("tanıtım", "tanitim", "intro", "lockup", "brand", "marka", "kampanya")):
        return "project_intro"
    if any(k in hay for k in ("minimal", "sade")) and not loc:
        return "minimal_luxury"
    if premium:
        return "editorial_hero"
    return "editorial_hero"


def choose_art_direction(
    *,
    instruction: str = "",
    composition_family: str = "",
    objective: str = "",
    campaign_angle: str = "",
) -> str:
    """Back-compat alias — returns a v2 composition type, never a hashed template."""
    return choose_composition_type(
        instruction=instruction,
        composition_family=composition_family,
        objective=objective,
        campaign_angle=campaign_angle,
    )


def _normalize_variation(art_direction: str | None) -> str | None:
    if not art_direction:
        return None
    key = art_direction.strip().lower().replace(" ", "_").replace("-", "_")
    key = _LEGACY_ALIASES.get(key, key)
    if key in COMPOSITION_TYPES:
        return key
    return None


# ---------------------------------------------------------------------------
# Composition families — different zones, not the same left column
# ---------------------------------------------------------------------------


def _build_editorial_hero(cw: int, ch: int) -> dict[str, Any]:
    """Large serif, left-upper type air, building right-lower. Groups, not a stack."""
    mx, my = _sx(80, cw), _sy(72, ch)
    return {
        "text_ground": "light",
        "visual_focal_point": "building-right-lower",
        "negative_space": "left-upper",
        "visual_balance": "type-left / architecture-right; heavy headline at top, location mark at base",
        "typography_scale": "editorial",
        "typography_contrast": "high",
        "contrast_strategy": "navy serif on ivory air; gold CTA and location mark",
        "element_relationships": [
            "BRAND GROUP: visible project logo upper-left — part of the design, not a corner stamp",
            "MESSAGE GROUP: headline + subhead, tight 12–16px grouping, large serif hierarchy",
            "ACTION GROUP: CTA continues the headline group as an editorial link — never the main focus",
            "PROOF/LOCATION GROUP: diamond mark + location at the base, near the architecture, not in the type stack",
            "FOOTER GROUP: slogan bottom-left, supporting mark bottom-right",
        ],
        "decorative_elements": ["short gold hierarchy hairline", "small gold location mark"],
        "overlap_rules": [
            "Do not sit type on busy windows or floors",
            "Building may crop into the right half; type stays in left-upper air",
            "CTA must not cover the facade mass",
        ],
        "graphic_language": [
            "editorial serif campaign, not a social-media template",
            "thin gold lines, ivory atmosphere, photographic architecture",
            "location as a jewel mark, not a stacked caption",
        ],
        "brand_color_relationships": [
            "navy #1B2A4A headline on ivory/cream air",
            "gold #C4A35A for editorial link, short hairline, and location mark",
            "muted navy for subhead; architecture remains photographic",
        ],
        "safe_margins": {"top": _sy(64, ch), "left": _sx(72, cw), "right": _sx(72, cw), "bottom": _sy(72, ch)},
        "content_zone": _zone("content", _sx(48, cw), _sy(48, ch), _sx(520, cw), _sy(540, ch), "ivory_air"),
        "image_zone": _zone("image", _sx(400, cw), _sy(280, ch), _sx(680, cw), _sy(980, ch), "architecture"),
        "headline_zone": _zone("headline", mx, _sy(168, ch), _sx(560, cw), _sy(200, ch), "quiet"),
        "brand_zone": _zone("brand", mx, my, _sx(260, cw), _sy(80, ch), "quiet"),
        "cta_zone": _zone("cta", mx, _sy(468, ch), _sx(240, cw), _sy(50, ch), "quiet"),
        "reserved": [
            ReservedRegion("brand_air", mx, my, _sx(200, cw), _sy(56, ch), "ivory_air"),
            ReservedRegion("headline_air", mx, _sy(160, ch), _sx(580, cw), _sy(360, ch), "ivory_air"),
            ReservedRegion("proof_air", mx, _sy(1170, ch), _sx(480, cw), _sy(140, ch), "quiet"),
        ],
        "groups": [
            _group("brand", ["logo-project"], "left", _sy(8, ch)),
            _group("message", ["text-headline", "text-subhead", "shape-divider"], "left", _sy(14, ch)),
            _group("action", ["cta-primary"], "left", _sy(36, ch)),
            _group("proof", ["shape-location-mark", "text-location"], "left", _sx(10, cw)),
            _group("footer", ["text-slogan", "logo-investhome"], "split", _sx(24, cw)),
        ],
        "layers": [
            _layer(
                id="logo-project", type="IMAGE", role="logo", content_slot="project_logo", group="brand",
                x=mx, y=my, width=_sx(248, cw), height=_sy(72, ch), z_index=8,
            ),
            _layer(
                id="text-headline", type="TEXT", role="headline", content_slot="headline", group="message",
                x=mx, y=_sy(168, ch), width=_sx(540, cw), height=_sy(188, ch),
                font_size=_sf(76, cw), font_family="serif", font_weight="medium",
                line_height=1.06, letter_spacing=-1.6, color=NAVY, align="left", z_index=5,
            ),
            _layer(
                id="text-subhead", type="TEXT", role="body", content_slot="subhead", group="message",
                x=mx, y=_sy(368, ch), width=_sx(460, cw), height=_sy(44, ch),
                font_size=_sf(18, cw), font_family="sans", font_weight="normal",
                line_height=1.35, color=SUBHEAD_INK, align="left", z_index=5,
            ),
            _layer(
                id="shape-divider", type="SHAPE", role="decoration", content_slot="shape", group="message",
                x=mx, y=_sy(424, ch), width=_sx(48, cw), height=max(2, _sy(2, ch)),
                fill=GOLD, shape_kind="line", decoration_purpose="hierarchy", z_index=4,
            ),
            _layer(
                id="cta-primary", type="BUTTON", role="cta", content_slot="cta", group="action",
                x=mx, y=_sy(468, ch), width=_sx(228, cw), height=_sy(40, ch),
                font_size=_sf(14, cw), font_family="sans", font_weight="semibold",
                background_color=None, text_color=GOLD, border_radius=_sf(2, cw),
                padding=_sx(4, cw), cta_style="editorial_link", z_index=7,
            ),
            _layer(
                id="shape-location-mark", type="SHAPE", role="decoration", content_slot="shape", group="proof",
                x=mx, y=_sy(1198, ch), width=_sx(8, cw), height=_sy(8, ch),
                fill=GOLD, shape_kind="accent", decoration_purpose="brand_signature",
                border_radius=_sf(1, cw), z_index=4,
            ),
            _layer(
                id="text-location", type="TEXT", role="eyebrow", content_slot="location", group="proof",
                x=_sx(98, cw), y=_sy(1192, ch), width=_sx(420, cw), height=_sy(22, ch),
                font_size=_sf(12, cw), font_family="sans", font_weight="medium",
                letter_spacing=2.8, color=GOLD, align="left", z_index=5,
            ),
            _layer(
                id="text-slogan", type="TEXT", role="brand", content_slot="slogan", group="footer",
                x=mx, y=_sy(1286, ch), width=_sx(500, cw), height=_sy(26, ch),
                font_size=_sf(12, cw), font_family="sans", font_weight="normal",
                color=MUTED_INK, align="left", z_index=6,
            ),
            _layer(
                id="logo-investhome", type="IMAGE", role="logo", content_slot="investhome_logo", group="footer",
                x=_sx(880, cw), y=_sy(1282, ch), width=_sx(120, cw), height=_sy(32, ch), z_index=8,
            ),
        ],
        "art_notes": [
            "Editorial luxury RE campaign: oversized serif, intentional line break, ivory negative space.",
            "Place the real building as the hero in the RIGHT-LOWER image zone. Do not redesign facade, floors, or windows.",
            "Left-upper is campaign AIR (sky, stone, cream atmosphere, architectural shadow) — not a hard white template panel and not fake typeset copy.",
            "OS will place the real logo, headline, editorial CTA, a short gold hairline, and location mark. Compose light and crop around those zones. Do not paint a vertical gold bar.",
        ],
    }


def _build_architectural_hero(cw: int, ch: int) -> dict[str, Any]:
    """Building fills the frame. Sparse type at the base — not a left panel."""
    return {
        "text_ground": "light",
        "visual_focal_point": "building-full-frame",
        "negative_space": "lower-left sparse",
        "visual_balance": "architecture dominates; type is a quiet caption",
        "typography_scale": "minimal",
        "typography_contrast": "high",
        "contrast_strategy": "small navy type on photographic air at the base",
        "element_relationships": [
            "BRAND GROUP: visible logo upper-left",
            "MESSAGE GROUP: smaller serif headline at lower-left with thin gold rule above",
            "ACTION GROUP: compact CTA beside the message, not stacked as a poster",
            "FOOTER GROUP: slogan under the message",
        ],
        "decorative_elements": ["thin gold editorial rule"],
        "overlap_rules": ["Type stays off the primary facade mass", "Do not invent a side panel"],
        "graphic_language": ["architectural photography campaign", "sparse type", "thin gold rule"],
        "brand_color_relationships": ["navy type, gold hairline, photographic building"],
        "safe_margins": {"top": _sy(56, ch), "left": _sx(72, cw), "right": _sx(72, cw), "bottom": _sy(56, ch)},
        "content_zone": _zone("content", _sx(64, cw), _sy(980, ch), _sx(620, cw), _sy(280, ch), "quiet"),
        "image_zone": _zone("image", 0, 0, cw, ch, "architecture"),
        "headline_zone": _zone("headline", _sx(72, cw), _sy(1040, ch), _sx(560, cw), _sy(90, ch), "quiet"),
        "brand_zone": _zone("brand", _sx(72, cw), _sy(64, ch), _sx(150, cw), _sy(44, ch), "quiet"),
        "cta_zone": _zone("cta", _sx(72, cw), _sy(1158, ch), _sx(200, cw), _sy(42, ch), "quiet"),
        "reserved": [
            ReservedRegion("brand_air", _sx(64, cw), _sy(56, ch), _sx(170, cw), _sy(52, ch), "quiet"),
            ReservedRegion("lower_caption", _sx(56, cw), _sy(1000, ch), _sx(640, cw), _sy(260, ch), "quiet"),
        ],
        "groups": [
            _group("brand", ["logo-project"], "left", 8),
            _group("message", ["shape-divider", "text-headline", "text-subhead"], "left", _sy(10, ch)),
            _group("action", ["cta-primary"], "left", _sy(16, ch)),
            _group("footer", ["text-slogan", "logo-investhome"], "split", 24),
        ],
        "layers": [
            _layer(
                id="logo-project", type="IMAGE", role="logo", content_slot="project_logo", group="brand",
                x=_sx(72, cw), y=_sy(64, ch), width=_sx(140, cw), height=_sy(40, ch), z_index=8,
            ),
            _layer(
                id="shape-divider", type="SHAPE", role="decoration", content_slot="shape", group="message",
                x=_sx(72, cw), y=_sy(1028, ch), width=_sx(40, cw), height=max(2, _sy(2, ch)),
                fill=GOLD, shape_kind="line", decoration_purpose="hierarchy", z_index=4,
            ),
            _layer(
                id="text-headline", type="TEXT", role="headline", content_slot="headline", group="message",
                x=_sx(72, cw), y=_sy(1042, ch), width=_sx(540, cw), height=_sy(88, ch),
                font_size=_sf(36, cw), font_family="serif", font_weight="medium",
                line_height=1.12, color=NAVY, align="left", z_index=5,
            ),
            _layer(
                id="text-subhead", type="TEXT", role="body", content_slot="subhead", group="message",
                x=_sx(72, cw), y=_sy(1132, ch), width=_sx(480, cw), height=_sy(28, ch),
                font_size=_sf(15, cw), font_family="sans", color=SUBHEAD_INK, align="left", z_index=5,
            ),
            _layer(
                id="cta-primary", type="BUTTON", role="cta", content_slot="cta", group="action",
                x=_sx(72, cw), y=_sy(1172, ch), width=_sx(196, cw), height=_sy(40, ch),
                font_size=_sf(13, cw), font_family="sans", font_weight="medium",
                background_color=NAVY, text_color=WHITE, border_radius=_sf(2, cw), z_index=7,
            ),
            _layer(
                id="text-slogan", type="TEXT", role="brand", content_slot="slogan", group="footer",
                x=_sx(72, cw), y=_sy(1288, ch), width=_sx(480, cw), height=_sy(22, ch),
                font_size=_sf(12, cw), font_family="sans", color=MUTED_INK, align="left", z_index=6,
            ),
            _layer(
                id="logo-investhome", type="IMAGE", role="logo", content_slot="investhome_logo", group="footer",
                x=_sx(890, cw), y=_sy(1284, ch), width=_sx(110, cw), height=_sy(30, ch), z_index=8,
            ),
        ],
        "art_notes": [
            "Architecture is the advertisement. Keep type sparse at the lower-left caption zone.",
            "Do not invent a left information panel. Preserve the building exactly.",
        ],
    }


def _build_location_story(cw: int, ch: int) -> dict[str, Any]:
    """Building-dominant. Type lives in a quiet lower band — not a left column."""
    return {
        "text_ground": "dark",
        "visual_focal_point": "building-center",
        "negative_space": "lower-third quiet band",
        "visual_balance": "photograph first; location mark + headline as a lower story",
        "typography_scale": "modern",
        "typography_contrast": "high",
        "contrast_strategy": "ivory/white type on a quiet darkened lower band; gold location mark",
        "element_relationships": [
            "BRAND GROUP: small logo upper-left over the photograph",
            "PROOF/LOCATION GROUP: gold mark + location lead the lower story",
            "MESSAGE GROUP: headline then subhead in the lower band",
            "ACTION GROUP: CTA after the message in the same band",
            "FOOTER GROUP: slogan + supporting mark on the band baseline",
        ],
        "decorative_elements": ["gold location mark", "thin gold rule"],
        "overlap_rules": ["Lower band may darken; do not paint fake addresses or map pins"],
        "graphic_language": ["place-led campaign", "building as geography", "gold location jewel"],
        "brand_color_relationships": ["gold mark, ivory type, navy/dusk photograph"],
        "safe_margins": {"top": _sy(64, ch), "left": _sx(80, cw), "right": _sx(80, cw), "bottom": _sy(48, ch)},
        "content_zone": _zone("content", _sx(48, cw), _sy(860, ch), _sx(984, cw), _sy(440, ch), "dusk_band"),
        "image_zone": _zone("image", 0, 0, cw, _sy(980, ch), "architecture"),
        "headline_zone": _zone("headline", _sx(80, cw), _sy(930, ch), _sx(860, cw), _sy(120, ch), "dusk_band"),
        "brand_zone": _zone("brand", _sx(80, cw), _sy(72, ch), _sx(180, cw), _sy(48, ch), "quiet"),
        "cta_zone": _zone("cta", _sx(80, cw), _sy(1128, ch), _sx(230, cw), _sy(46, ch), "dusk_band"),
        "reserved": [
            ReservedRegion("brand_air", _sx(72, cw), _sy(64, ch), _sx(200, cw), _sy(56, ch), "quiet"),
            ReservedRegion("lower_story", _sx(48, cw), _sy(860, ch), _sx(984, cw), _sy(440, ch), "dusk_band"),
        ],
        "groups": [
            _group("brand", ["logo-project"], "left", 8),
            _group("proof", ["shape-location-mark", "text-location"], "left", 10),
            _group("message", ["text-headline", "text-subhead"], "left", 12),
            _group("action", ["cta-primary"], "left", 20),
            _group("footer", ["text-slogan", "logo-investhome"], "split", 24),
        ],
        "layers": [
            _layer(
                id="logo-project", type="IMAGE", role="logo", content_slot="project_logo", group="brand",
                x=_sx(80, cw), y=_sy(72, ch), width=_sx(168, cw), height=_sy(44, ch), z_index=8,
            ),
            _layer(
                id="shape-location-mark", type="SHAPE", role="decoration", content_slot="shape", group="proof",
                x=_sx(80, cw), y=_sy(892, ch), width=_sx(8, cw), height=_sy(8, ch),
                fill=GOLD, shape_kind="accent", decoration_purpose="brand_signature",
                border_radius=_sf(1, cw), z_index=4,
            ),
            _layer(
                id="text-location", type="TEXT", role="eyebrow", content_slot="location", group="proof",
                x=_sx(98, cw), y=_sy(886, ch), width=_sx(640, cw), height=_sy(22, ch),
                font_size=_sf(13, cw), font_family="sans", font_weight="medium",
                letter_spacing=2.6, color=GOLD, align="left", z_index=5,
            ),
            _layer(
                id="text-headline", type="TEXT", role="headline", content_slot="headline", group="message",
                x=_sx(80, cw), y=_sy(922, ch), width=_sx(860, cw), height=_sy(110, ch),
                font_size=_sf(52, cw), font_family="sans", font_weight="bold",
                line_height=1.1, color=WHITE, align="left", z_index=5,
            ),
            _layer(
                id="text-subhead", type="TEXT", role="body", content_slot="subhead", group="message",
                x=_sx(80, cw), y=_sy(1040, ch), width=_sx(700, cw), height=_sy(40, ch),
                font_size=_sf(17, cw), font_family="sans", color="#E8E4DC", align="left", z_index=5,
            ),
            _layer(
                id="shape-divider", type="SHAPE", role="decoration", content_slot="shape", group="message",
                x=_sx(80, cw), y=_sy(1092, ch), width=_sx(56, cw), height=max(2, _sy(2, ch)),
                fill=GOLD, shape_kind="line", decoration_purpose="hierarchy", z_index=4,
            ),
            _layer(
                id="cta-primary", type="BUTTON", role="cta", content_slot="cta", group="action",
                x=_sx(80, cw), y=_sy(1120, ch), width=_sx(220, cw), height=_sy(44, ch),
                font_size=_sf(14, cw), font_family="sans", font_weight="semibold",
                background_color=GOLD, text_color=NAVY, border_radius=_sf(2, cw), z_index=7,
            ),
            _layer(
                id="text-slogan", type="TEXT", role="brand", content_slot="slogan", group="footer",
                x=_sx(80, cw), y=_sy(1284, ch), width=_sx(500, cw), height=_sy(24, ch),
                font_size=_sf(12, cw), font_family="sans", color="#D1D5DB", align="left", z_index=6,
            ),
            _layer(
                id="logo-investhome", type="IMAGE", role="logo", content_slot="investhome_logo", group="footer",
                x=_sx(880, cw), y=_sy(1280, ch), width=_sx(120, cw), height=_sy(32, ch), z_index=8,
            ),
        ],
        "art_notes": [
            "Location story: the building is the place. Quiet darkened lower band for OS type.",
            "Do not invent map pins, monuments, or walk times. Gold location mark is OS-composited.",
        ],
    }


def _build_minimal_luxury(cw: int, ch: int) -> dict[str, Any]:
    """Smaller type, more air. Not a filled template column."""
    return {
        "text_ground": "light",
        "visual_focal_point": "building-right",
        "negative_space": "generous left and upper air",
        "visual_balance": "few elements, large empty field, architecture as object",
        "typography_scale": "minimal",
        "typography_contrast": "high",
        "contrast_strategy": "small serif navy on open ivory",
        "element_relationships": [
            "BRAND GROUP: restrained but readable logo",
            "MESSAGE GROUP: one restrained headline, optional subhead",
            "ACTION GROUP: quiet navy CTA",
            "FOOTER GROUP: slogan only",
        ],
        "decorative_elements": ["short gold hairline"],
        "overlap_rules": ["Leave most of the canvas to the building and air"],
        "graphic_language": ["quiet luxury", "restraint", "no stacked captions"],
        "brand_color_relationships": ["navy, gold hairline, ivory air"],
        "safe_margins": {"top": _sy(80, ch), "left": _sx(88, cw), "right": _sx(88, cw), "bottom": _sy(64, ch)},
        "content_zone": _zone("content", _sx(72, cw), _sy(80, ch), _sx(480, cw), _sy(360, ch), "ivory_air"),
        "image_zone": _zone("image", _sx(360, cw), _sy(160, ch), _sx(720, cw), _sy(1100, ch), "architecture"),
        "headline_zone": _zone("headline", _sx(88, cw), _sy(160, ch), _sx(440, cw), _sy(100, ch), "quiet"),
        "brand_zone": _zone("brand", _sx(88, cw), _sy(80, ch), _sx(140, cw), _sy(40, ch), "quiet"),
        "cta_zone": _zone("cta", _sx(88, cw), _sy(320, ch), _sx(180, cw), _sy(40, ch), "quiet"),
        "reserved": [
            ReservedRegion("sparse_type", _sx(72, cw), _sy(72, ch), _sx(460, cw), _sy(340, ch), "ivory_air"),
            ReservedRegion("footer_air", _sx(80, cw), _sy(1268, ch), _sx(480, cw), _sy(40, ch), "quiet"),
        ],
        "groups": [
            _group("brand", ["logo-project"], "left", 8),
            _group("message", ["text-headline", "shape-divider", "text-subhead"], "left", 12),
            _group("action", ["cta-primary"], "left", 28),
            _group("footer", ["text-slogan", "logo-investhome"], "split", 24),
        ],
        "layers": [
            _layer(
                id="logo-project", type="IMAGE", role="logo", content_slot="project_logo", group="brand",
                x=_sx(88, cw), y=_sy(80, ch), width=_sx(132, cw), height=_sy(36, ch), z_index=8,
            ),
            _layer(
                id="text-headline", type="TEXT", role="headline", content_slot="headline", group="message",
                x=_sx(88, cw), y=_sy(156, ch), width=_sx(420, cw), height=_sy(80, ch),
                font_size=_sf(34, cw), font_family="serif", font_weight="medium",
                line_height=1.14, color=NAVY, align="left", z_index=5,
            ),
            _layer(
                id="shape-divider", type="SHAPE", role="decoration", content_slot="shape", group="message",
                x=_sx(88, cw), y=_sy(248, ch), width=_sx(36, cw), height=max(2, _sy(2, ch)),
                fill=GOLD, shape_kind="line", decoration_purpose="hierarchy", z_index=4,
            ),
            _layer(
                id="text-subhead", type="TEXT", role="body", content_slot="subhead", group="message",
                x=_sx(88, cw), y=_sy(264, ch), width=_sx(380, cw), height=_sy(36, ch),
                font_size=_sf(15, cw), font_family="sans", color=SUBHEAD_INK, align="left", z_index=5,
            ),
            _layer(
                id="cta-primary", type="BUTTON", role="cta", content_slot="cta", group="action",
                x=_sx(88, cw), y=_sy(320, ch), width=_sx(176, cw), height=_sy(38, ch),
                font_size=_sf(12, cw), font_family="sans", font_weight="medium",
                background_color=NAVY, text_color=WHITE, border_radius=_sf(2, cw), z_index=7,
            ),
            _layer(
                id="text-slogan", type="TEXT", role="brand", content_slot="slogan", group="footer",
                x=_sx(88, cw), y=_sy(1290, ch), width=_sx(460, cw), height=_sy(22, ch),
                font_size=_sf(11, cw), font_family="sans", color=MUTED_INK, align="left", z_index=6,
            ),
            _layer(
                id="logo-investhome", type="IMAGE", role="logo", content_slot="investhome_logo", group="footer",
                x=_sx(900, cw), y=_sy(1286, ch), width=_sx(100, cw), height=_sy(28, ch), z_index=8,
            ),
        ],
        "art_notes": [
            "Minimal luxury: more air than type. Building is an object in space.",
            "Do not fill the left field with stacked captions.",
        ],
    }


def _build_brand_campaign(cw: int, ch: int) -> dict[str, Any]:
    """Centered lockup — brand campaign, not a left stack."""
    return {
        "text_ground": "light",
        "visual_focal_point": "building-behind-center",
        "negative_space": "centered field around the lockup",
        "visual_balance": "axial; logo / headline / CTA stacked as a brand unit, not a sidebar",
        "typography_scale": "editorial",
        "typography_contrast": "high",
        "contrast_strategy": "navy serif centered on light air; gold rule",
        "element_relationships": [
            "BRAND GROUP: logo centered top",
            "MESSAGE GROUP: centered headline + subhead",
            "ACTION GROUP: centered CTA",
            "FOOTER GROUP: slogan centered, supporting mark below",
        ],
        "decorative_elements": ["centered gold rule"],
        "overlap_rules": ["Keep the central lockup free of busy facade detail"],
        "graphic_language": ["brand campaign", "centered editorial", "architecture as backdrop"],
        "brand_color_relationships": ["navy type, gold rule, ivory field"],
        "safe_margins": {"top": _sy(72, ch), "left": _sx(120, cw), "right": _sx(120, cw), "bottom": _sy(56, ch)},
        "content_zone": _zone("content", _sx(140, cw), _sy(80, ch), _sx(800, cw), _sy(520, ch), "ivory_air"),
        "image_zone": _zone("image", 0, _sy(560, ch), cw, _sy(790, ch), "architecture"),
        "headline_zone": _zone("headline", _sx(140, cw), _sy(200, ch), _sx(800, cw), _sy(170, ch), "quiet"),
        "brand_zone": _zone("brand", _sx(400, cw), _sy(80, ch), _sx(280, cw), _sy(56, ch), "quiet"),
        "cta_zone": _zone("cta", _sx(400, cw), _sy(500, ch), _sx(280, cw), _sy(48, ch), "quiet"),
        "reserved": [
            ReservedRegion("center_lockup", _sx(140, cw), _sy(70, ch), _sx(800, cw), _sy(520, ch), "ivory_air"),
            ReservedRegion("footer_air", _sx(240, cw), _sy(1260, ch), _sx(600, cw), _sy(50, ch), "quiet"),
        ],
        "groups": [
            _group("brand", ["logo-project"], "center", 12),
            _group("message", ["text-headline", "text-subhead", "shape-divider"], "center", 14),
            _group("action", ["cta-primary"], "center", 28),
            _group("footer", ["text-slogan", "logo-investhome"], "center", 12),
        ],
        "layers": [
            _layer(
                id="logo-project", type="IMAGE", role="logo", content_slot="project_logo", group="brand",
                x=_sx(430, cw), y=_sy(84, ch), width=_sx(220, cw), height=_sy(52, ch), z_index=8,
            ),
            _layer(
                id="text-headline", type="TEXT", role="headline", content_slot="headline", group="message",
                x=_sx(140, cw), y=_sy(200, ch), width=_sx(800, cw), height=_sy(168, ch),
                font_size=_sf(64, cw), font_family="serif", font_weight="medium",
                line_height=1.08, letter_spacing=-0.8, color=NAVY, align="center", z_index=5,
            ),
            _layer(
                id="text-subhead", type="TEXT", role="body", content_slot="subhead", group="message",
                x=_sx(200, cw), y=_sy(380, ch), width=_sx(680, cw), height=_sy(44, ch),
                font_size=_sf(18, cw), font_family="sans", color=SUBHEAD_INK, align="center", z_index=5,
            ),
            _layer(
                id="shape-divider", type="SHAPE", role="decoration", content_slot="shape", group="message",
                x=_sx(504, cw), y=_sy(436, ch), width=_sx(72, cw), height=max(2, _sy(2, ch)),
                fill=GOLD, shape_kind="line", decoration_purpose="hierarchy", z_index=4,
            ),
            _layer(
                id="cta-primary", type="BUTTON", role="cta", content_slot="cta", group="action",
                x=_sx(400, cw), y=_sy(500, ch), width=_sx(280, cw), height=_sy(46, ch),
                font_size=_sf(14, cw), font_family="sans", font_weight="semibold",
                background_color=NAVY, text_color=WHITE, border_radius=_sf(2, cw), z_index=7,
            ),
            _layer(
                id="text-slogan", type="TEXT", role="brand", content_slot="slogan", group="footer",
                x=_sx(240, cw), y=_sy(1284, ch), width=_sx(600, cw), height=_sy(24, ch),
                font_size=_sf(12, cw), font_family="sans", color=MUTED_INK, align="center", z_index=6,
            ),
            _layer(
                id="logo-investhome", type="IMAGE", role="logo", content_slot="investhome_logo", group="footer",
                x=_sx(470, cw), y=_sy(1236, ch), width=_sx(140, cw), height=_sy(32, ch), z_index=8,
            ),
        ],
        "art_notes": [
            "Brand campaign: centered lockup. Architecture may live below or as a soft backdrop.",
            "Keep the central field as calm air for OS type. Do not rasterize the wordmark.",
        ],
    }


def _build_data_location(cw: int, ch: int) -> dict[str, Any]:
    """Location as proof — marker + verified line, not a metric dump."""
    return {
        "text_ground": "light",
        "visual_focal_point": "building-right",
        "negative_space": "left field for proof + headline",
        "visual_balance": "location mark is a graphic; headline relates to it; building is the place",
        "typography_scale": "modern",
        "typography_contrast": "high",
        "contrast_strategy": "gold location graphic against navy headline",
        "element_relationships": [
            "PROOF/LOCATION GROUP leads: diamond + verified location",
            "MESSAGE GROUP follows the proof",
            "ACTION GROUP under the message",
            "BRAND GROUP small top",
            "FOOTER GROUP slogan",
        ],
        "decorative_elements": ["gold location diamond", "direction line from mark to type"],
        "overlap_rules": ["Only verified location copy; no invented distances"],
        "graphic_language": ["wayfinding jewel", "editorial proof", "architecture as place"],
        "brand_color_relationships": ["gold proof, navy headline, ivory air"],
        "safe_margins": {"top": _sy(64, ch), "left": _sx(80, cw), "right": _sx(72, cw), "bottom": _sy(48, ch)},
        "content_zone": _zone("content", _sx(56, cw), _sy(64, ch), _sx(560, cw), _sy(520, ch), "ivory_air"),
        "image_zone": _zone("image", _sx(420, cw), _sy(240, ch), _sx(660, cw), _sy(1020, ch), "architecture"),
        "headline_zone": _zone("headline", _sx(80, cw), _sy(220, ch), _sx(520, cw), _sy(160, ch), "quiet"),
        "brand_zone": _zone("brand", _sx(80, cw), _sy(68, ch), _sx(160, cw), _sy(44, ch), "quiet"),
        "cta_zone": _zone("cta", _sx(80, cw), _sy(460, ch), _sx(220, cw), _sy(46, ch), "quiet"),
        "reserved": [
            ReservedRegion("proof_type", _sx(56, cw), _sy(56, ch), _sx(560, cw), _sy(500, ch), "ivory_air"),
            ReservedRegion("footer_air", _sx(72, cw), _sy(1268, ch), _sx(500, cw), _sy(40, ch), "quiet"),
        ],
        "groups": [
            _group("brand", ["logo-project"], "left", 8),
            _group("proof", ["shape-location-mark", "text-location", "shape-divider"], "left", 8),
            _group("message", ["text-headline", "text-subhead"], "left", 12),
            _group("action", ["cta-primary"], "left", 24),
            _group("footer", ["text-slogan", "logo-investhome"], "split", 24),
        ],
        "layers": [
            _layer(
                id="logo-project", type="IMAGE", role="logo", content_slot="project_logo", group="brand",
                x=_sx(80, cw), y=_sy(68, ch), width=_sx(150, cw), height=_sy(40, ch), z_index=8,
            ),
            _layer(
                id="shape-location-mark", type="SHAPE", role="decoration", content_slot="shape", group="proof",
                x=_sx(80, cw), y=_sy(148, ch), width=_sx(10, cw), height=_sy(10, ch),
                fill=GOLD, shape_kind="accent", decoration_purpose="brand_signature",
                border_radius=_sf(1, cw), z_index=4,
            ),
            _layer(
                id="text-location", type="TEXT", role="eyebrow", content_slot="location", group="proof",
                x=_sx(100, cw), y=_sy(144, ch), width=_sx(480, cw), height=_sy(22, ch),
                font_size=_sf(13, cw), font_family="sans", font_weight="medium",
                letter_spacing=2.4, color=GOLD, align="left", z_index=5,
            ),
            _layer(
                id="shape-divider", type="SHAPE", role="decoration", content_slot="shape", group="proof",
                x=_sx(80, cw), y=_sy(176, ch), width=_sx(40, cw), height=max(2, _sy(2, ch)),
                fill=GOLD, shape_kind="line", decoration_purpose="hierarchy", z_index=4,
            ),
            _layer(
                id="text-headline", type="TEXT", role="headline", content_slot="headline", group="message",
                x=_sx(80, cw), y=_sy(200, ch), width=_sx(500, cw), height=_sy(140, ch),
                font_size=_sf(56, cw), font_family="sans", font_weight="bold",
                line_height=1.1, color=NAVY, align="left", z_index=5,
            ),
            _layer(
                id="text-subhead", type="TEXT", role="body", content_slot="subhead", group="message",
                x=_sx(80, cw), y=_sy(352, ch), width=_sx(460, cw), height=_sy(44, ch),
                font_size=_sf(16, cw), font_family="sans", color=SUBHEAD_INK, align="left", z_index=5,
            ),
            _layer(
                id="cta-primary", type="BUTTON", role="cta", content_slot="cta", group="action",
                x=_sx(80, cw), y=_sy(420, ch), width=_sx(210, cw), height=_sy(44, ch),
                font_size=_sf(14, cw), font_family="sans", font_weight="semibold",
                background_color=GOLD, text_color=NAVY, border_radius=_sf(2, cw), z_index=7,
            ),
            _layer(
                id="text-slogan", type="TEXT", role="brand", content_slot="slogan", group="footer",
                x=_sx(80, cw), y=_sy(1286, ch), width=_sx(500, cw), height=_sy(24, ch),
                font_size=_sf(12, cw), font_family="sans", color=MUTED_INK, align="left", z_index=6,
            ),
            _layer(
                id="logo-investhome", type="IMAGE", role="logo", content_slot="investhome_logo", group="footer",
                x=_sx(880, cw), y=_sy(1282, ch), width=_sx(120, cw), height=_sy(32, ch), z_index=8,
            ),
        ],
        "art_notes": [
            "Data/location: the verified place is the proof. Gold mark leads, then headline.",
            "Do not invent distances, yield, or landmarks. Building stays the real photograph.",
        ],
    }


def _build_lifestyle(cw: int, ch: int) -> dict[str, Any]:
    """Right-side type, building left/center — not a left panel."""
    rx = _sx(520, cw)
    return {
        "text_ground": "light",
        "visual_focal_point": "building-left",
        "negative_space": "right-upper type field",
        "visual_balance": "architecture left; editorial type right-aligned",
        "typography_scale": "editorial",
        "typography_contrast": "high",
        "contrast_strategy": "navy serif on right-side air against the photograph",
        "element_relationships": [
            "BRAND GROUP: small logo upper-right",
            "MESSAGE GROUP: right-aligned headline + subhead",
            "ACTION GROUP: CTA under the right type",
            "FOOTER GROUP: slogan right, supporting mark left-bottom",
        ],
        "decorative_elements": ["short gold rule aligned to the type"],
        "overlap_rules": ["Type stays on the right air; building occupies the left two-thirds"],
        "graphic_language": ["lifestyle editorial", "right rag", "photographic living"],
        "brand_color_relationships": ["navy type, gold rule, ivory right field"],
        "safe_margins": {"top": _sy(72, ch), "left": _sx(56, cw), "right": _sx(72, cw), "bottom": _sy(48, ch)},
        "content_zone": _zone("content", _sx(500, cw), _sy(64, ch), _sx(520, cw), _sy(520, ch), "ivory_air"),
        "image_zone": _zone("image", 0, 0, _sx(640, cw), ch, "architecture"),
        "headline_zone": _zone("headline", rx, _sy(180, ch), _sx(480, cw), _sy(200, ch), "quiet"),
        "brand_zone": _zone("brand", _sx(760, cw), _sy(72, ch), _sx(240, cw), _sy(48, ch), "quiet"),
        "cta_zone": _zone("cta", _sx(720, cw), _sy(480, ch), _sx(220, cw), _sy(46, ch), "quiet"),
        "reserved": [
            ReservedRegion("right_type", _sx(500, cw), _sy(56, ch), _sx(520, cw), _sy(520, ch), "ivory_air"),
            ReservedRegion("footer_air", _sx(500, cw), _sy(1268, ch), _sx(500, cw), _sy(40, ch), "quiet"),
        ],
        "groups": [
            _group("brand", ["logo-project"], "right", 8),
            _group("message", ["text-headline", "text-subhead", "shape-divider"], "right", 12),
            _group("action", ["cta-primary"], "right", 28),
            _group("footer", ["text-slogan", "logo-investhome"], "split", 24),
        ],
        "layers": [
            _layer(
                id="logo-project", type="IMAGE", role="logo", content_slot="project_logo", group="brand",
                x=_sx(780, cw), y=_sy(72, ch), width=_sx(180, cw), height=_sy(44, ch), z_index=8,
            ),
            _layer(
                id="text-headline", type="TEXT", role="headline", content_slot="headline", group="message",
                x=rx, y=_sy(176, ch), width=_sx(480, cw), height=_sy(188, ch),
                font_size=_sf(64, cw), font_family="serif", font_weight="medium",
                line_height=1.08, letter_spacing=-1.2, color=NAVY, align="right", z_index=5,
            ),
            _layer(
                id="text-subhead", type="TEXT", role="body", content_slot="subhead", group="message",
                x=rx, y=_sy(376, ch), width=_sx(480, cw), height=_sy(44, ch),
                font_size=_sf(17, cw), font_family="sans", color=SUBHEAD_INK, align="right", z_index=5,
            ),
            _layer(
                id="shape-divider", type="SHAPE", role="decoration", content_slot="shape", group="message",
                x=_sx(944, cw), y=_sy(432, ch), width=_sx(56, cw), height=max(2, _sy(2, ch)),
                fill=GOLD, shape_kind="line", decoration_purpose="hierarchy", z_index=4,
            ),
            _layer(
                id="cta-primary", type="BUTTON", role="cta", content_slot="cta", group="action",
                x=_sx(780, cw), y=_sy(468, ch), width=_sx(220, cw), height=_sy(44, ch),
                font_size=_sf(14, cw), font_family="sans", font_weight="semibold",
                background_color=GOLD, text_color=NAVY, border_radius=_sf(2, cw), z_index=7,
            ),
            _layer(
                id="text-slogan", type="TEXT", role="brand", content_slot="slogan", group="footer",
                x=rx, y=_sy(1286, ch), width=_sx(480, cw), height=_sy(24, ch),
                font_size=_sf(12, cw), font_family="sans", color=MUTED_INK, align="right", z_index=6,
            ),
            _layer(
                id="logo-investhome", type="IMAGE", role="logo", content_slot="investhome_logo", group="footer",
                x=_sx(72, cw), y=_sy(1282, ch), width=_sx(120, cw), height=_sy(32, ch), z_index=8,
            ),
        ],
        "art_notes": [
            "Lifestyle: building occupies the left; type is a right-hand editorial column.",
            "Do not default to a left information panel. Preserve the architecture.",
        ],
    }


def _build_neighborhood(cw: int, ch: int) -> dict[str, Any]:
    """Place-led: location chip + headline in the upper field. Building fills the rest — not a left panel."""
    return {
        "text_ground": "light",
        "visual_focal_point": "building-lower",
        "negative_space": "upper campaign air",
        "visual_balance": "place name leads; architecture occupies the lower two-thirds",
        "typography_scale": "modern",
        "typography_contrast": "high",
        "contrast_strategy": "navy headline on upper air; gold location chip",
        "element_relationships": [
            "PROOF/LOCATION GROUP leads at the top",
            "MESSAGE GROUP follows immediately — headline as place story",
            "BRAND GROUP: logo upper-right, independent of the place lockup",
            "ACTION GROUP: outline CTA under the message",
            "FOOTER GROUP: slogan on the baseline",
        ],
        "decorative_elements": ["gold location mark"],
        "overlap_rules": ["Keep the upper air calm; do not invent neighborhood distances"],
        "graphic_language": ["neighborhood editorial", "place before type stack", "architecture as the street"],
        "brand_color_relationships": ["gold location, navy headline, photographic building"],
        "safe_margins": {"top": _sy(64, ch), "left": _sx(72, cw), "right": _sx(72, cw), "bottom": _sy(72, ch)},
        "content_zone": _zone("content", _sx(56, cw), _sy(56, ch), _sx(720, cw), _sy(360, ch), "ivory_air"),
        "image_zone": _zone("image", 0, _sy(280, ch), cw, _sy(1070, ch), "architecture"),
        "headline_zone": _zone("headline", _sx(72, cw), _sy(148, ch), _sx(700, cw), _sy(120, ch), "quiet"),
        "brand_zone": _zone("brand", _sx(760, cw), _sy(64, ch), _sx(248, cw), _sy(72, ch), "quiet"),
        "cta_zone": _zone("cta", _sx(72, cw), _sy(300, ch), _sx(220, cw), _sy(42, ch), "quiet"),
        "reserved": [
            ReservedRegion("upper_place", _sx(48, cw), _sy(48, ch), _sx(740, cw), _sy(340, ch), "ivory_air"),
            ReservedRegion("footer_air", _sx(64, cw), _sy(1248, ch), _sx(500, cw), _sy(50, ch), "quiet"),
        ],
        "groups": [
            _group("brand", ["logo-project"], "right", 8),
            _group("proof", ["shape-location-mark", "text-location"], "left", 10),
            _group("message", ["text-headline", "text-subhead"], "left", 12),
            _group("action", ["cta-primary"], "left", 20),
            _group("footer", ["text-slogan", "logo-investhome"], "split", 24),
        ],
        "layers": [
            _layer(
                id="logo-project", type="IMAGE", role="logo", content_slot="project_logo", group="brand",
                x=_sx(780, cw), y=_sy(64, ch), width=_sx(248, cw), height=_sy(72, ch), z_index=8,
            ),
            _layer(
                id="shape-location-mark", type="SHAPE", role="decoration", content_slot="shape", group="proof",
                x=_sx(72, cw), y=_sy(88, ch), width=_sx(8, cw), height=_sy(8, ch),
                fill=GOLD, shape_kind="accent", decoration_purpose="brand_signature",
                border_radius=_sf(1, cw), z_index=4,
            ),
            _layer(
                id="text-location", type="TEXT", role="eyebrow", content_slot="location", group="proof",
                x=_sx(90, cw), y=_sy(82, ch), width=_sx(520, cw), height=_sy(22, ch),
                font_size=_sf(13, cw), font_family="sans", font_weight="medium",
                letter_spacing=2.4, color=GOLD, align="left", z_index=5,
            ),
            _layer(
                id="text-headline", type="TEXT", role="headline", content_slot="headline", group="message",
                x=_sx(72, cw), y=_sy(128, ch), width=_sx(700, cw), height=_sy(110, ch),
                font_size=_sf(48, cw), font_family="serif", font_weight="medium",
                line_height=1.1, color=NAVY, align="left", z_index=5,
            ),
            _layer(
                id="text-subhead", type="TEXT", role="body", content_slot="subhead", group="message",
                x=_sx(72, cw), y=_sy(248, ch), width=_sx(560, cw), height=_sy(36, ch),
                font_size=_sf(16, cw), font_family="sans", color=SUBHEAD_INK, align="left", z_index=5,
            ),
            _layer(
                id="cta-primary", type="BUTTON", role="cta", content_slot="cta", group="action",
                x=_sx(72, cw), y=_sy(300, ch), width=_sx(210, cw), height=_sy(40, ch),
                font_size=_sf(13, cw), font_family="sans", font_weight="medium",
                background_color=None, text_color=NAVY, border_radius=_sy(20, ch),
                cta_style="outline", z_index=7,
            ),
            _layer(
                id="text-slogan", type="TEXT", role="brand", content_slot="slogan", group="footer",
                x=_sx(72, cw), y=_sy(1260, ch), width=_sx(500, cw), height=_sy(24, ch),
                font_size=_sf(12, cw), font_family="sans", color=MUTED_INK, align="left", z_index=6,
            ),
            _layer(
                id="logo-investhome", type="IMAGE", role="logo", content_slot="investhome_logo", group="footer",
                x=_sx(880, cw), y=_sy(1256, ch), width=_sx(120, cw), height=_sy(32, ch), z_index=8,
            ),
        ],
        "art_notes": [
            "Neighborhood: the place name leads. Architecture fills below. Not a left information panel.",
            "Do not invent landmarks or walk times. Location copy is OS-typeset from verified facts only.",
        ],
    }


def _build_full_bleed(cw: int, ch: int) -> dict[str, Any]:
    """Architecture edge-to-edge. Sparse type lower-right — opposite of a left caption."""
    rx = _sx(520, cw)
    return {
        "text_ground": "dark",
        "visual_focal_point": "building-full-frame",
        "negative_space": "lower-right quiet pocket",
        "visual_balance": "photograph owns the frame; type is a quiet lower-right signature",
        "typography_scale": "minimal",
        "typography_contrast": "high",
        "contrast_strategy": "ivory type on a quiet darkened lower-right pocket; gold editorial link",
        "element_relationships": [
            "BRAND GROUP: logo upper-right over the photograph",
            "MESSAGE GROUP: smaller headline lower-right",
            "ACTION GROUP: editorial link under the headline",
            "FOOTER GROUP: slogan lower-right baseline",
        ],
        "decorative_elements": [],
        "overlap_rules": ["Do not invent a panel. Type stays off the primary facade mass."],
        "graphic_language": ["full-bleed photography", "sparse signature type", "no extra decoration"],
        "brand_color_relationships": ["ivory type, gold link, photographic building"],
        "safe_margins": {"top": _sy(64, ch), "left": _sx(72, cw), "right": _sx(72, cw), "bottom": _sy(72, ch)},
        "content_zone": _zone("content", rx, _sy(980, ch), _sx(500, cw), _sy(280, ch), "dusk_band"),
        "image_zone": _zone("image", 0, 0, cw, ch, "architecture"),
        "headline_zone": _zone("headline", rx, _sy(1020, ch), _sx(480, cw), _sy(90, ch), "dusk_band"),
        "brand_zone": _zone("brand", _sx(760, cw), _sy(64, ch), _sx(248, cw), _sy(72, ch), "quiet"),
        "cta_zone": _zone("cta", rx, _sy(1130, ch), _sx(220, cw), _sy(40, ch), "dusk_band"),
        "reserved": [
            ReservedRegion("brand_air", _sx(750, cw), _sy(56, ch), _sx(260, cw), _sy(80, ch), "quiet"),
            ReservedRegion("lower_right", rx, _sy(980, ch), _sx(500, cw), _sy(280, ch), "dusk_band"),
        ],
        "groups": [
            _group("brand", ["logo-project"], "right", 8),
            _group("message", ["text-headline", "text-subhead"], "right", 10),
            _group("action", ["cta-primary"], "right", 16),
            _group("footer", ["text-slogan", "logo-investhome"], "right", 12),
        ],
        "layers": [
            _layer(
                id="logo-project", type="IMAGE", role="logo", content_slot="project_logo", group="brand",
                x=_sx(780, cw), y=_sy(64, ch), width=_sx(248, cw), height=_sy(72, ch), z_index=8,
            ),
            _layer(
                id="text-headline", type="TEXT", role="headline", content_slot="headline", group="message",
                x=rx, y=_sy(1020, ch), width=_sx(480, cw), height=_sy(88, ch),
                font_size=_sf(32, cw), font_family="serif", font_weight="medium",
                line_height=1.12, color=WHITE, align="right", z_index=5,
            ),
            _layer(
                id="text-subhead", type="TEXT", role="body", content_slot="subhead", group="message",
                x=rx, y=_sy(1112, ch), width=_sx(480, cw), height=_sy(28, ch),
                font_size=_sf(15, cw), font_family="sans", color="#E8E4DC", align="right", z_index=5,
            ),
            _layer(
                id="cta-primary", type="BUTTON", role="cta", content_slot="cta", group="action",
                x=_sx(780, cw), y=_sy(1152, ch), width=_sx(220, cw), height=_sy(36, ch),
                font_size=_sf(13, cw), font_family="sans", font_weight="medium",
                background_color=None, text_color=GOLD, cta_style="editorial_link", z_index=7,
            ),
            _layer(
                id="text-slogan", type="TEXT", role="brand", content_slot="slogan", group="footer",
                x=rx, y=_sy(1256, ch), width=_sx(480, cw), height=_sy(24, ch),
                font_size=_sf(12, cw), font_family="sans", color=IVORY, align="right", z_index=6,
            ),
            _layer(
                id="logo-investhome", type="IMAGE", role="logo", content_slot="investhome_logo", group="footer",
                x=_sx(72, cw), y=_sy(1256, ch), width=_sx(120, cw), height=_sy(32, ch), z_index=8,
            ),
        ],
        "art_notes": [
            "Full bleed: the building is the ad. Keep type as a lower-right signature, not a stacked poster.",
            "Preserve architecture exactly. Darken only a quiet pocket for OS type if needed.",
        ],
    }


def looks_like_metadata_leak(text: str) -> bool:
    """Internal field names must never appear in the creative."""
    raw = (text or "").strip().lower()
    if not raw:
        return False
    return any(raw.startswith(prefix) or f" {prefix}" in raw for prefix in _METADATA_PREFIXES)


def sanitize_creative_text(text: str) -> str:
    """Strip internal field names. Never show 'project name: The Temple'."""
    raw = (text or "").strip()
    if not raw:
        return ""
    lower = raw.lower()
    for prefix in _DROP_METADATA_PREFIXES:
        if lower.startswith(prefix):
            return ""
    for prefix in _STRIP_LABEL_PREFIXES:
        if lower.startswith(prefix):
            return raw.split(":", 1)[1].strip()
    if looks_like_metadata_leak(raw):
        return ""
    return raw


def _hex_luma(color: str | None) -> float:
    raw = (color or "").strip().lstrip("#")
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    if len(raw) != 6:
        return 1.0
    try:
        r, g, b = int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
    except ValueError:
        return 1.0
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0


def _apply_cta_style(layer: DesignPlanLayer, style: str) -> None:
    layer.cta_style = style
    if style == "pill":
        layer.border_radius = max(layer.height // 2, 16)
        layer.background_color = layer.background_color or GOLD
        layer.text_color = layer.text_color or NAVY
    elif style == "outline":
        layer.border_radius = max(layer.height // 2, 16)
        layer.background_color = None
        layer.text_color = layer.text_color or NAVY
    elif style in {"editorial_link", "text_arrow", "minimal"}:
        layer.background_color = None
        layer.border_radius = 0
        if not layer.text_color:
            layer.text_color = GOLD if style == "editorial_link" else NAVY


def apply_visual_quality_guard(plan: GptImageDesignPlan) -> GptImageDesignPlan:
    """Auto-correct Design Plan quality. Final visual approval is the user's — never a PASS stamp."""
    corrections: list[str] = []
    cw, ch = plan.canvas_width, plan.canvas_height
    min_logo_w = _sx(MIN_PROJECT_LOGO_W_REF, cw)
    min_logo_h = _sy(MIN_PROJECT_LOGO_H_REF, ch)
    max_vert = _sy(MAX_VERTICAL_RULE_H_REF, ch)
    margins = dict(plan.safe_margins or {})
    left = max(int(margins.get("left") or 0), _sx(MIN_SAFE_REF["left"], cw))
    right = max(int(margins.get("right") or 0), _sx(MIN_SAFE_REF["right"], cw))
    top = max(int(margins.get("top") or 0), _sy(MIN_SAFE_REF["top"], ch))
    bottom = max(int(margins.get("bottom") or 0), _sy(MIN_SAFE_REF["bottom"], ch))
    plan.safe_margins = {"top": top, "left": left, "right": right, "bottom": bottom}

    kept: list[DesignPlanLayer] = []
    for layer in plan.layers:
        if layer.content_slot == "project_logo":
            if layer.width < min_logo_w or layer.height < min_logo_h:
                layer.width = max(layer.width, min_logo_w)
                layer.height = max(layer.height, min_logo_h)
                corrections.append("logo_min_presence")
        if layer.type == "SHAPE":
            purpose = (layer.decoration_purpose or "").strip().lower()
            tall_rule = layer.height > layer.width * 4 and layer.height > max_vert
            if tall_rule and purpose != "framing":
                corrections.append("removed_meaningless_vertical_rule")
                continue
            if layer.role == "decoration" and purpose not in DECORATION_PURPOSES:
                if layer.shape_kind == "accent":
                    layer.decoration_purpose = "brand_signature"
                elif layer.width >= layer.height:
                    layer.decoration_purpose = "hierarchy"
                else:
                    corrections.append("removed_purposeless_decoration")
                    continue
        dark = (plan.text_ground or "").lower() == "dark"
        if layer.type == "BUTTON" or layer.role == "cta":
            style = layer.cta_style or _CTA_STYLE_BY_COMPOSITION.get(plan.variation, "editorial_link")
            if not layer.cta_style:
                corrections.append(f"cta_style:{style}")
            _apply_cta_style(layer, style)
            if dark and style in {"outline", "editorial_link", "text_arrow", "minimal"}:
                if _hex_luma(layer.text_color) < 0.45:
                    layer.text_color = GOLD if style == "editorial_link" else IVORY
                    corrections.append("cta_contrast")
        if layer.type == "TEXT":
            luma = _hex_luma(layer.color)
            if dark and luma < 0.45:
                layer.color = WHITE if layer.role == "headline" else IVORY
                corrections.append("contrast_text_color")
            if not dark and luma > 0.82:
                layer.color = NAVY
                corrections.append("contrast_text_color")
            if layer.content_slot == "slogan" and dark and luma < 0.55:
                layer.color = IVORY
                corrections.append("slogan_contrast")
        x, y, w, h = layer.x, layer.y, layer.width, layer.height
        if layer.type in {"TEXT", "IMAGE", "BUTTON"}:
            if x < left:
                x = left
                corrections.append("safe_area_left")
            if y < top:
                y = top
                corrections.append("safe_area_top")
            if x + w > cw - right:
                x = max(left, cw - right - w)
                corrections.append("safe_area_right")
            if y + h > ch - bottom:
                y = max(top, ch - bottom - h)
                corrections.append("safe_area_bottom")
            layer.x, layer.y = x, y
        kept.append(layer)

    member_ids = {layer.id for layer in kept}
    plan.layers = kept
    plan.groups = [
        ElementGroup(
            name=g.name,
            members=[m for m in g.members if m in member_ids],
            alignment=g.alignment,
            gap=g.gap,
        )
        for g in plan.groups
    ]
    plan.decorative_elements = [
        item
        for item in plan.decorative_elements
        if "vertical gold" not in item.lower()
    ]
    dark_ground = (plan.text_ground or "").lower() == "dark"
    slogan = next((row for row in plan.layers if row.content_slot == "slogan"), None)
    if dark_ground and slogan and _hex_luma(slogan.color) < 0.6:
        plan.needs_scrim = True
        corrections.append("scrim_for_contrast")
    elif dark_ground:
        plan.needs_scrim = True
    plan.quality_corrections = list(dict.fromkeys(corrections))
    plan.visual_review_status = "READY FOR USER VISUAL REVIEW"
    return plan


_BUILDERS = {
    "editorial_hero": _build_editorial_hero,
    "location_story": _build_location_story,
    "architecture_focus": _build_architectural_hero,
    "architectural_hero": _build_architectural_hero,
    "minimal_luxury": _build_minimal_luxury,
    "investment_story": _build_data_location,
    "data_location": _build_data_location,
    "lifestyle": _build_lifestyle,
    "neighborhood": _build_neighborhood,
    "project_intro": _build_brand_campaign,
    "brand_campaign": _build_brand_campaign,
    "full_bleed": _build_full_bleed,
    "split_editorial": _build_lifestyle,
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
    headline: str = "",
) -> GptImageDesignPlan:
    cw = max(8, int(canvas_width or REF_W))
    ch = max(8, int(canvas_height or REF_H))
    variation = _normalize_variation(art_direction) or choose_composition_type(
        instruction=instruction,
        composition_family=composition_family,
        objective=objective,
        campaign_angle=campaign_angle,
    )
    builder = _BUILDERS.get(variation, _build_editorial_hero)
    recipe = builder(cw, ch)
    layers = list(recipe["layers"])
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

    typography_scale = str(recipe.get("typography_scale") or "editorial")
    breaks = decide_headline_line_breaks(
        headline,
        typography_scale=typography_scale,
        composition_type=variation,
    )
    groups = list(recipe.get("groups") or [])
    if not has_project_logo:
        groups = [
            ElementGroup(
                name=g.name,
                members=[m for m in g.members if m != "logo-project"],
                alignment=g.alignment,
                gap=g.gap,
            )
            for g in groups
        ]
    if not has_investhome_logo:
        groups = [
            ElementGroup(
                name=g.name,
                members=[m for m in g.members if m != "logo-investhome"],
                alignment=g.alignment,
                gap=g.gap,
            )
            for g in groups
        ]
    if not include_slogan:
        groups = [
            ElementGroup(
                name=g.name,
                members=[m for m in g.members if m != "text-slogan"],
                alignment=g.alignment,
                gap=g.gap,
            )
            for g in groups
        ]

    plan = GptImageDesignPlan(
        variation=variation,
        label=COMPOSITION_LABELS.get(variation, variation),
        composition_type=COMPOSITION_LABELS.get(variation, variation),
        canvas_width=cw,
        canvas_height=ch,
        text_ground=str(recipe.get("text_ground") or "light"),
        visual_focal_point=str(recipe.get("visual_focal_point") or ""),
        negative_space=str(recipe.get("negative_space") or ""),
        visual_balance=str(recipe.get("visual_balance") or ""),
        typography_scale=typography_scale,
        typography_contrast=str(recipe.get("typography_contrast") or "high"),
        contrast_strategy=str(recipe.get("contrast_strategy") or ""),
        headline_line_breaks=breaks,
        element_relationships=list(recipe.get("element_relationships") or []),
        decorative_elements=list(recipe.get("decorative_elements") or []),
        overlap_rules=list(recipe.get("overlap_rules") or []),
        graphic_language=list(recipe.get("graphic_language") or []),
        brand_color_relationships=list(recipe.get("brand_color_relationships") or []),
        safe_margins=dict(recipe.get("safe_margins") or {}),
        content_zone=recipe.get("content_zone"),
        image_zone=recipe.get("image_zone"),
        headline_zone=recipe.get("headline_zone"),
        brand_zone=recipe.get("brand_zone"),
        cta_zone=recipe.get("cta_zone"),
        groups=groups,
        reserved=list(recipe.get("reserved") or []),
        layers=kept,
        art_notes=list(recipe.get("art_notes") or []),
    )
    return apply_visual_quality_guard(plan)


def _zone_to_dict(zone: DesignZone | None) -> dict[str, Any] | None:
    if zone is None:
        return None
    return asdict(zone)


def design_plan_to_dict(plan: GptImageDesignPlan) -> dict[str, Any]:
    return {
        "variation": plan.variation,
        "label": plan.label,
        "composition_type": plan.composition_type,
        "canvas_width": plan.canvas_width,
        "canvas_height": plan.canvas_height,
        "text_ground": plan.text_ground,
        "visual_focal_point": plan.visual_focal_point,
        "negative_space": plan.negative_space,
        "visual_balance": plan.visual_balance,
        "typography_scale": plan.typography_scale,
        "typography_contrast": plan.typography_contrast,
        "contrast_strategy": plan.contrast_strategy,
        "headline_line_breaks": list(plan.headline_line_breaks),
        "element_relationships": list(plan.element_relationships),
        "decorative_elements": list(plan.decorative_elements),
        "overlap_rules": list(plan.overlap_rules),
        "graphic_language": list(plan.graphic_language),
        "brand_color_relationships": list(plan.brand_color_relationships),
        "safe_margins": dict(plan.safe_margins),
        "content_zone": _zone_to_dict(plan.content_zone),
        "image_zone": _zone_to_dict(plan.image_zone),
        "headline_zone": _zone_to_dict(plan.headline_zone),
        "brand_zone": _zone_to_dict(plan.brand_zone),
        "cta_zone": _zone_to_dict(plan.cta_zone),
        "groups": [asdict(row) for row in plan.groups],
        "reserved": [asdict(row) for row in plan.reserved],
        "layers": [asdict(row) for row in plan.layers],
        "art_notes": list(plan.art_notes),
        "needs_scrim": bool(plan.needs_scrim),
        "localized_scrim_only": bool(plan.localized_scrim_only),
        "visual_review_status": plan.visual_review_status,
        "quality_corrections": list(plan.quality_corrections),
    }


def _fmt_zone(label: str, zone: dict[str, Any] | DesignZone | None) -> str | None:
    if zone is None:
        return None
    if isinstance(zone, DesignZone):
        zone = asdict(zone)
    if not isinstance(zone, dict):
        return None
    return (
        f"- {label}: {zone.get('treatment') or zone.get('name')} "
        f"(x={zone.get('x')} y={zone.get('y')} w={zone.get('width')} h={zone.get('height')})"
    )


def format_design_plan_for_prompt(plan: dict[str, Any] | GptImageDesignPlan | None) -> list[str]:
    """Share the Art Direction Plan with GPT Image — composition, not 'leave a blank box'."""
    if plan is None:
        return []
    payload = design_plan_to_dict(plan) if isinstance(plan, GptImageDesignPlan) else plan
    composition = str(payload.get("composition_type") or payload.get("label") or "EDITORIAL HERO")
    cw = payload.get("canvas_width") or REF_W
    ch = payload.get("canvas_height") or REF_H
    lines = [
        "ART DIRECTION PLAN (shared by GPT Image and InvestHome OS — one design, two stages):",
        f"Composition type: {composition} on a {cw}x{ch} canvas.",
        f"Visual focal point: {payload.get('visual_focal_point') or 'the real building'}.",
        f"Negative space: {payload.get('negative_space') or 'compose calm campaign air for type'}.",
        f"Visual balance: {payload.get('visual_balance') or 'architecture and type in relationship'}.",
        f"Typography scale (OS): {payload.get('typography_scale') or 'editorial'} with "
        f"{payload.get('typography_contrast') or 'high'} contrast.",
        f"Contrast strategy: {payload.get('contrast_strategy') or 'navy/gold/ivory'}.",
        "ZONES (compose atmosphere here — sky, stone, cream air, dusk, architectural shadow. "
        "Not a hard white template panel. Not fake headlines, logos, CTAs, or addresses):",
    ]
    for key, label in (
        ("image_zone", "Image / architecture zone"),
        ("content_zone", "Content / campaign-air zone"),
        ("headline_zone", "Headline zone"),
        ("brand_zone", "Brand / logo zone"),
        ("cta_zone", "CTA zone"),
    ):
        formatted = _fmt_zone(label, payload.get(key))
        if formatted:
            lines.append(formatted)
    breaks = payload.get("headline_line_breaks") or []
    if breaks:
        lines.append("Headline will be OS-typeset with these line breaks (do NOT paint them): " + " / ".join(str(b) for b in breaks))
    if payload.get("graphic_language"):
        lines.append("Graphic language: " + "; ".join(str(item) for item in payload["graphic_language"]))
    if payload.get("brand_color_relationships"):
        lines.append("Brand color relationships: " + "; ".join(str(item) for item in payload["brand_color_relationships"]))
    if payload.get("decorative_elements"):
        lines.append(
            "Decorative language (OS will composite real SHAPE layers — you may echo atmosphere, "
            "not fake copy): " + ", ".join(str(item) for item in payload["decorative_elements"])
        )
    if payload.get("element_relationships"):
        lines.append("Element relationships OS will typeset:")
        for rel in payload["element_relationships"]:
            lines.append(f"- {rel}")
    if payload.get("overlap_rules"):
        lines.append("Overlap / crop rules:")
        for rule in payload["overlap_rules"]:
            lines.append(f"- {rule}")
    for note in payload.get("art_notes") or []:
        lines.append(f"- {note}")
    lines.extend(
        [
            "You are the campaign photographer and art director for the BACKGROUND.",
            "Compose crop, light, atmosphere, and empty air so the real building and the OS type share one luxury RE campaign.",
            "Do NOT rasterize real copy, logos, slogans, addresses, prices, or CTAs. InvestHome OS places those as editable layers on this same plan.",
        ]
    )
    return lines
