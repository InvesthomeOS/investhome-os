"""Art Direction Plan → OS Final Composition fidelity.

Enriches the shared Design Plan with translator decisions: rich headline runs,
three feature callouts, localized scrims, composition families, background-aware placement.
Does not change Creative Director brief logic or GPT Image clean canvas rules.
"""

from __future__ import annotations

import io
import statistics
from dataclasses import replace
from typing import Any

from PIL import Image

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
    format_headline_for_plan,
)

OS_COMPOSITION_FAMILIES = (
    "editorial_hero",
    "lifestyle_story",
    "offer_focus",
    "location_story",
    "feature_story",
    "minimal_luxury",
)

_FAMILY_LABELS = {
    "editorial_hero": "EDITORIAL HERO",
    "lifestyle_story": "LIFESTYLE STORY",
    "offer_focus": "OFFER FOCUS",
    "location_story": "LOCATION STORY",
    "feature_story": "FEATURE STORY",
    "minimal_luxury": "MINIMAL LUXURY",
}

_INTERNAL_LEAK_TOKENS = (
    "campaign_percent",
    "confidence",
    "score",
    "asset id",
    "asset_id",
    "campaign context",
    "campaign_context",
    "debug",
    "retrieved",
    "derived_safe",
    "linked_project_id",
    "folder_category",
    "gpt_generated",
    "duplication_guard",
    "provider_call",
)


def looks_like_internal_leak(text: str) -> bool:
    raw = (text or "").strip().lower()
    if not raw:
        return False
    return any(tok in raw for tok in _INTERNAL_LEAK_TOKENS)


def count_internal_leaks(*texts: str) -> int:
    return sum(1 for text in texts if looks_like_internal_leak(text))


def build_headline_runs(
    headline: str,
    *,
    emphasis_words: list[str] | None = None,
    plan: GptImageDesignPlan | None = None,
    default_color: str = NAVY,
    accent_color: str = GOLD,
) -> list[dict[str, Any]]:
    """Word-level emphasis — e.g. Eviniz=navy, Sığınak=gold."""
    formatted = format_headline_for_plan(headline, plan)
    lines = [ln.strip() for ln in formatted.split("\n") if ln.strip()] or [headline.strip()]
    emphasis = {w.strip().lower().rstrip(",.") for w in (emphasis_words or []) if w.strip()}
    headline_words = [w.strip(",.") for w in headline.replace("\n", " ").split() if w.strip(",.")]
    if headline_words and not any(w.lower() in emphasis for w in headline_words):
        emphasis = {headline_words[-1].lower()}
    runs: list[dict[str, Any]] = []
    base_size = 76
    if plan:
        headline_layer = next((row for row in plan.layers if row.id == "text-headline"), None)
        if headline_layer and headline_layer.font_size:
            base_size = int(headline_layer.font_size)
    for line_idx, line in enumerate(lines):
        if line_idx:
            runs.append({"text": "\n", "break": True})
        parts = line.replace(",", " ,").split()
        for part_idx, part in enumerate(parts):
            if part == ",":
                runs.append({"text": ",", "fontFamily": "serif", "fontSize": base_size, "fontWeight": "medium", "color": default_color})
                continue
            word = part.rstrip(",")
            trailing = "," if part.endswith(",") else ""
            key = word.lower()
            color = accent_color if key in emphasis else default_color
            weight = "semibold" if color == accent_color else "medium"
            runs.append(
                {
                    "text": word + trailing,
                    "fontFamily": "serif",
                    "fontSize": base_size,
                    "fontWeight": weight,
                    "color": color,
                }
            )
            if part_idx < len(parts) - 1 and part != ",":
                runs.append({"text": " ", "fontFamily": "serif", "fontSize": base_size, "fontWeight": "medium", "color": default_color})
    return runs


def choose_os_composition_family(
    *,
    lifestyle: bool = False,
    feature_count: int = 0,
    has_price: bool = False,
    instruction: str = "",
    art_direction_variation: str = "",
) -> str:
    hay = (instruction or "").lower()
    if lifestyle and feature_count >= 3:
        return "feature_story"
    if lifestyle:
        return "lifestyle_story"
    if has_price or any(k in hay for k in ("fiyat", "price", "lansman", "offer")):
        return "offer_focus"
    if any(k in hay for k in ("lokasyon", "location", "adres", "konum")):
        return "location_story"
    if any(k in hay for k in ("minimal", "sade", "luxury", "lüks")):
        return "minimal_luxury"
    if art_direction_variation in OS_COMPOSITION_FAMILIES:
        return art_direction_variation
    return "editorial_hero"


def analyze_background_placement(
    background_bytes: bytes | None,
    *,
    canvas_width: int,
    canvas_height: int,
    preferred: str = "left-upper",
) -> tuple[str, int, int]:
    """Simple brightness/variance heuristic — keep type off busy focal bands."""
    if not background_bytes:
        return "light", _sx(80, canvas_width), _sy(160, canvas_height)
    try:
        with Image.open(io.BytesIO(background_bytes)) as raw:
            img = raw.convert("RGB").resize((canvas_width, canvas_height), Image.Resampling.BILINEAR)
    except Exception:
        return "light", _sx(80, canvas_width), _sy(160, canvas_height)

    w, h = img.size
    cols, rows = 4, 5
    cell_w, cell_h = max(1, w // cols), max(1, h // rows)
    scores: list[tuple[float, float, int, int]] = []
    for row in range(rows):
        for col in range(cols):
            x0, y0 = col * cell_w, row * cell_h
            crop = img.crop((x0, y0, min(w, x0 + cell_w), min(h, y0 + cell_h)))
            pixels = list(crop.getdata())
            if not pixels:
                continue
            lum = sum(0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b in pixels) / (255 * len(pixels))
            variance = statistics.pstdev([0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b in pixels])
            bias = 0.0
            if preferred.startswith("left") and col <= 1:
                bias += 0.08
            if "upper" in preferred and row <= 1:
                bias += 0.08
            if "lower" in preferred and row >= 3:
                bias += 0.08
            scores.append((variance - bias, lum, x0, y0))
    scores.sort(key=lambda item: item[0])
    _, lum, x0, y0 = scores[0]
    ground = "dark" if lum < 0.42 else "light"
    return ground, max(_sx(72, w), x0), max(_sy(64, h), y0)


def _feature_story_recipe(cw: int, ch: int, *, type_x: int, type_y: int, text_ground: str) -> dict[str, Any]:
    """Interior lifestyle — headline + 3 feature callouts, no giant bottom panel."""
    mx = type_x
    my = type_y
    headline_color = NAVY if text_ground == "light" else WHITE
    feature_color = SUBHEAD_INK if text_ground == "light" else "#E8E4DC"
    return {
        "text_ground": text_ground,
        "visual_focal_point": "interior-center",
        "negative_space": "left-upper air beside living area",
        "visual_balance": "photograph dominates; editorial type in left-upper cluster",
        "typography_scale": "editorial",
        "typography_contrast": "high",
        "contrast_strategy": "navy/gold headline emphasis; localized scrim behind type cluster only",
        "element_relationships": [
            "BRAND GROUP: Temple logo upper-left — readable, never a corner stamp",
            "MESSAGE GROUP: serif headline with word emphasis — two lines when needed",
            "FEATURE GROUP: three separate callouts with marks — not one long sentence",
            "ACTION GROUP: CTA continues headline cluster — editorial link or outline",
            "FOOTER GROUP: slogan baseline",
        ],
        "decorative_elements": ["short gold hierarchy hairline", "small gold feature marks"],
        "overlap_rules": [
            "Do not cover sofa/TV focal mass with type",
            "No semi-transparent panel covering bottom half",
            "Localized scrim behind type cluster only",
        ],
        "graphic_language": ["premium interior editorial", "feature callouts", "photographic living room"],
        "brand_color_relationships": ["navy + gold headline emphasis", "muted sans feature lines"],
        "safe_margins": {"top": _sy(64, ch), "left": _sx(72, cw), "right": _sx(72, cw), "bottom": _sy(72, ch)},
        "content_zone": _zone("type_cluster", mx, my, _sx(560, cw), _sy(620, ch), "localized_scrim"),
        "image_zone": _zone("image", 0, 0, cw, ch, "interior"),
        "headline_zone": _zone("headline", mx, my + _sy(96, ch), _sx(540, cw), _sy(200, ch), "quiet"),
        "brand_zone": _zone("brand", mx, _sy(72, ch), _sx(260, cw), _sy(80, ch), "quiet"),
        "cta_zone": _zone("cta", mx, my + _sy(520, ch), _sx(240, cw), _sy(48, ch), "quiet"),
        "groups": [
            _group("brand", ["logo-project"], "left", _sy(8, ch)),
            _group("message", ["text-headline", "shape-divider"], "left", _sy(14, ch)),
            _group("features", ["feature-1", "feature-2", "feature-3"], "left", _sy(12, ch)),
            _group("action", ["cta-primary"], "left", _sy(28, ch)),
            _group("footer", ["text-slogan", "logo-investhome"], "split", _sx(24, cw)),
        ],
        "layers": [
            _layer(
                id="logo-project", type="IMAGE", role="logo", content_slot="project_logo", group="brand",
                x=mx, y=_sy(72, ch), width=_sx(248, cw), height=_sy(72, ch), z_index=8,
            ),
            _layer(
                id="text-headline", type="TEXT", role="headline", content_slot="headline", group="message",
                x=mx, y=my + _sy(96, ch), width=_sx(540, cw), height=_sy(196, ch),
                font_size=_sf(72, cw), font_family="serif", font_weight="medium",
                line_height=1.06, letter_spacing=-1.4, color=headline_color, align="left", z_index=6,
            ),
            _layer(
                id="shape-divider", type="SHAPE", role="decoration", content_slot="shape", group="message",
                x=mx, y=my + _sy(300, ch), width=_sx(48, cw), height=max(2, _sy(2, ch)),
                fill=GOLD, shape_kind="line", decoration_purpose="hierarchy", z_index=4,
            ),
            _layer(
                id="feature-1", type="TEXT", role="body", content_slot="feature_1", group="features",
                x=mx + _sx(20, cw), y=my + _sy(328, ch), width=_sx(500, cw), height=_sy(52, ch),
                font_size=_sf(15, cw), font_family="sans", font_weight="medium",
                line_height=1.35, color=feature_color, align="left", z_index=6,
            ),
            _layer(
                id="shape-feature-1", type="SHAPE", role="decoration", content_slot="shape", group="features",
                x=mx, y=my + _sy(340, ch), width=_sx(8, cw), height=_sy(8, ch),
                fill=GOLD, shape_kind="accent", decoration_purpose="brand_signature",
                border_radius=_sf(1, cw), z_index=5,
            ),
            _layer(
                id="feature-2", type="TEXT", role="body", content_slot="feature_2", group="features",
                x=mx + _sx(20, cw), y=my + _sy(396, ch), width=_sx(500, cw), height=_sy(52, ch),
                font_size=_sf(15, cw), font_family="sans", font_weight="normal",
                line_height=1.35, color=feature_color, align="left", z_index=6,
            ),
            _layer(
                id="shape-feature-2", type="SHAPE", role="decoration", content_slot="shape", group="features",
                x=mx, y=my + _sy(408, ch), width=_sx(8, cw), height=_sy(8, ch),
                fill=GOLD, shape_kind="accent", decoration_purpose="brand_signature",
                border_radius=_sf(1, cw), z_index=5,
            ),
            _layer(
                id="feature-3", type="TEXT", role="body", content_slot="feature_3", group="features",
                x=mx + _sx(20, cw), y=my + _sy(464, ch), width=_sx(500, cw), height=_sy(52, ch),
                font_size=_sf(15, cw), font_family="sans", font_weight="normal",
                line_height=1.35, color=feature_color, align="left", z_index=6,
            ),
            _layer(
                id="shape-feature-3", type="SHAPE", role="decoration", content_slot="shape", group="features",
                x=mx, y=my + _sy(476, ch), width=_sx(8, cw), height=_sy(8, ch),
                fill=GOLD, shape_kind="accent", decoration_purpose="brand_signature",
                border_radius=_sf(1, cw), z_index=5,
            ),
            _layer(
                id="cta-primary", type="BUTTON", role="cta", content_slot="cta", group="action",
                x=mx, y=my + _sy(536, ch), width=_sx(228, cw), height=_sy(42, ch),
                font_size=_sf(14, cw), font_family="sans", font_weight="semibold",
                background_color=None, text_color=GOLD if text_ground == "light" else WHITE,
                border_radius=_sf(2, cw), cta_style="editorial_link", z_index=7,
            ),
            _layer(
                id="text-slogan", type="TEXT", role="brand", content_slot="slogan", group="footer",
                x=mx, y=_sy(1286, ch), width=_sx(500, cw), height=_sy(26, ch),
                font_size=_sf(12, cw), font_family="sans", font_weight="normal",
                color=SUBHEAD_INK if text_ground == "light" else "#D1D5DB",
                align="left", z_index=6,
            ),
            _layer(
                id="logo-investhome", type="IMAGE", role="logo", content_slot="investhome_logo", group="footer",
                x=_sx(880, cw), y=_sy(1282, ch), width=_sx(120, cw), height=_sy(32, ch), z_index=8,
            ),
        ],
        "art_notes": [
            "Feature story: three separate lifestyle callouts — not one long supporting sentence.",
            "Localized contrast behind the left type cluster only. Interior stays visible.",
        ],
        "needs_scrim": True,
        "localized_scrim_only": True,
    }


def _zone(name: str, x: int, y: int, w: int, h: int, treatment: str = "") -> DesignZone:
    return DesignZone(name=name, x=x, y=y, width=w, height=h, treatment=treatment)


def enrich_os_composition_plan(
    plan: GptImageDesignPlan,
    *,
    texts: dict[str, str],
    art_direction: dict[str, Any] | None = None,
    background_bytes: bytes | None = None,
    lifestyle: bool = False,
    has_project_logo: bool = True,
    has_investhome_logo: bool = False,
    include_slogan: bool = True,
) -> GptImageDesignPlan:
    """Apply translator typography + feature fidelity onto the OS composition plan."""
    cw, ch = plan.canvas_width, plan.canvas_height
    callouts_raw = str(texts.get("supporting_callouts") or "")
    callouts = [x.strip() for x in callouts_raw.split("|") if x.strip()]
    if not callouts and lifestyle:
        callouts = [x.strip() for x in str(texts.get("supporting") or "").split("·") if x.strip()]
    feature_count = len(callouts)

    family = choose_os_composition_family(
        lifestyle=lifestyle,
        feature_count=feature_count,
        has_price=bool(str(texts.get("offer_price") or "").strip()),
        instruction=str(texts.get("headline") or ""),
        art_direction_variation=plan.variation,
    )

    text_ground, type_x, type_y = analyze_background_placement(
        background_bytes,
        canvas_width=cw,
        canvas_height=ch,
        preferred=plan.negative_space or "left-upper",
    )

    if lifestyle and feature_count >= 3 and family == "feature_story":
        recipe = _feature_story_recipe(cw, ch, type_x=type_x, type_y=type_y, text_ground=text_ground)
        layers = list(recipe["layers"])
    else:
        recipe = {}
        layers = list(plan.layers)

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
        if layer.content_slot == "subhead" and lifestyle and feature_count >= 3:
            continue
        kept.append(layer)

    headline = str(texts.get("headline") or "").strip()
    emphasis = []
    if isinstance(art_direction, dict):
        emphasis = list(art_direction.get("emphasis_words") or [])
    if not emphasis and headline:
        words = [w.strip(",.") for w in headline.split() if w.strip()]
        if len(words) >= 2:
            emphasis = [words[-1]]

    breaks = decide_headline_line_breaks(
        headline,
        typography_scale=str(recipe.get("typography_scale") or plan.typography_scale),
        composition_type=family,
    )

    enriched = replace(
        plan,
        variation=family,
        label=_FAMILY_LABELS.get(family, family.upper()),
        composition_type=_FAMILY_LABELS.get(family, family.upper()),
        text_ground=str(recipe.get("text_ground") or plan.text_ground or text_ground),
        visual_focal_point=str(recipe.get("visual_focal_point") or plan.visual_focal_point),
        negative_space=str(recipe.get("negative_space") or plan.negative_space),
        headline_line_breaks=breaks,
        layers=kept,
        groups=list(recipe.get("groups") or plan.groups),
        content_zone=recipe.get("content_zone") or plan.content_zone,
        needs_scrim=bool(recipe.get("needs_scrim", plan.needs_scrim)),
        art_notes=list(recipe.get("art_notes") or plan.art_notes),
    )

    for layer in enriched.layers:
        if layer.id == "text-headline":
            layer.text_runs = build_headline_runs(
                headline,
                emphasis_words=emphasis,
                plan=enriched,
            )
        if layer.content_slot == "feature_1" and len(callouts) > 0:
            layer.static_content = callouts[0]
        if layer.content_slot == "feature_2" and len(callouts) > 1:
            layer.static_content = callouts[1]
        if layer.content_slot == "feature_3" and len(callouts) > 2:
            layer.static_content = callouts[2]

    if recipe.get("localized_scrim_only"):
        enriched = replace(enriched, needs_scrim=True, localized_scrim_only=True)

    return apply_visual_quality_guard(enriched)


def build_os_composition_plan(
    *,
    canvas_width: int,
    canvas_height: int,
    texts: dict[str, str],
    art_direction: dict[str, Any] | None = None,
    background_bytes: bytes | None = None,
    lifestyle: bool = False,
    has_project_logo: bool = True,
    has_investhome_logo: bool = False,
    include_slogan: bool = True,
    instruction: str = "",
) -> GptImageDesignPlan:
    base = build_gpt_image_design_plan(
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        instruction=instruction,
        has_project_logo=has_project_logo,
        has_investhome_logo=has_investhome_logo,
        include_slogan=include_slogan,
        headline=str(texts.get("headline") or ""),
    )
    return enrich_os_composition_plan(
        base,
        texts=texts,
        art_direction=art_direction,
        background_bytes=background_bytes,
        lifestyle=lifestyle,
        has_project_logo=has_project_logo,
        has_investhome_logo=has_investhome_logo,
        include_slogan=include_slogan,
    )
