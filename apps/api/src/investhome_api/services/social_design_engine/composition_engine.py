"""Visual Composition Engine — choose HOW a CreativePlan fits the canvas.

AI / CreativePlan chooses strategy. This module chooses family + regions
from image analysis, format, copy density, and project-local variety.
Deterministic. No LLM pixels. No hardcoded project coordinates.
"""

from __future__ import annotations

import hashlib
from typing import Any

from investhome_api.services.social_design_engine.composition_blueprint import (
    COMPOSITION_FAMILIES,
    BrandLockupKind,
    CompositionBlueprint,
    CompositionFamilyKind,
    CompositionGroup,
    CtaPlacementKind,
    GridSpec,
    HeadlineRegionKind,
    ImageAnalysis,
    ImageCrop,
    MetricLayoutKind,
    MetricRegionKind,
    NormRect,
    OverlayRegion,
    SplitRatioKind,
    VisualWeight,
)
from investhome_api.services.social_design_engine.creative_plan import (
    CreativePlan,
    combined_variety_signals,
    remember_project_variety,
)

# Direction → candidate families. Not 1:1 with intent.
DIRECTION_FAMILIES: dict[str, list[CompositionFamilyKind]] = {
    "LOCATION_STORY": [
        "EDITORIAL_HERO",
        "ASYMMETRIC_EDITORIAL",
        "FLOATING_DATA",
        "OVERLAY_PANEL",
    ],
    "EDITORIAL_LUXURY": [
        "EDITORIAL_HERO",
        "ASYMMETRIC_EDITORIAL",
        "STATEMENT_LAYOUT",
        "LUXURY_BRAND",
    ],
    "ARCHITECTURAL_FEATURE": [
        "ARCHITECTURAL_MINIMAL",
        "IMAGE_DOMINANT",
        "LOWER_THIRD",
    ],
    "INVESTMENT_DATA": [
        "INVESTMENT_GRID",
        "LOWER_THIRD",
        "SPLIT_LAYOUT",
        "FLOATING_DATA",
    ],
    "LIFESTYLE_PREMIUM": [
        "LIFESTYLE_EDITORIAL",
        "IMAGE_DOMINANT",
        "OVERLAY_PANEL",
        "LOWER_THIRD",
    ],
    "BRAND_STATEMENT": [
        "LUXURY_BRAND",
        "STATEMENT_LAYOUT",
        "IMAGE_DOMINANT",
    ],
    "INFORMATIONAL_EDITORIAL": [
        "OVERLAY_PANEL",
        "SPLIT_LAYOUT",
        "ASYMMETRIC_EDITORIAL",
        "EDITORIAL_HERO",
    ],
}

PRIMITIVE_FAMILY_HINT: dict[str, CompositionFamilyKind] = {
    "TOP_LEFT_EDITORIAL": "EDITORIAL_HERO",
    "BOTTOM_LEFT_EDITORIAL": "LOWER_THIRD",
    "SIDE_COLUMN": "OVERLAY_PANEL",
    "CENTER_STATEMENT": "STATEMENT_LAYOUT",
    "LOWER_THIRD": "LOWER_THIRD",
    "ASYMMETRIC_EDITORIAL": "ASYMMETRIC_EDITORIAL",
    "DATA_GRID": "INVESTMENT_GRID",
    "IMAGE_DOMINANT": "IMAGE_DOMINANT",
    "SPLIT_INFORMATION": "SPLIT_LAYOUT",
    "FLOATING_INFORMATION_GROUP": "FLOATING_DATA",
}

FORMAT_MARGINS: dict[str, tuple[float, float]] = {
    "square": (7.0, 7.0),
    "portrait": (6.0, 7.0),
    "story": (6.0, 9.0),
    "reelsCover": (6.0, 9.5),
    "landscape": (7.0, 6.0),
    "carousel": (7.0, 7.0),
}


def format_margins(format_preset: str) -> tuple[float, float]:
    return FORMAT_MARGINS.get(format_preset or "square", (7.0, 7.0))


def analyze_image(profile: Any, *, format_preset: str = "square") -> ImageAnalysis:
    """Approximate layout reading from asset metadata. No CV, no project-specific coords."""
    subject = "unknown"
    brightness = "mixed"
    busy = False
    empty = False
    tags: list[str] = []
    filename = ""
    if isinstance(profile, dict):
        subject = str(profile.get("subject") or "unknown")
        brightness = str(profile.get("brightness") or "mixed")
        busy = bool(profile.get("busy"))
        empty = bool(profile.get("empty_negative_space") or profile.get("empty"))
        tags = [str(t).lower() for t in (profile.get("tags") or [])]
        filename = str(profile.get("filename") or "")
    elif profile is not None:
        subject = str(getattr(profile, "subject", "unknown") or "unknown")
        brightness = str(getattr(profile, "brightness", "mixed") or "mixed")
        busy = bool(getattr(profile, "busy", False))
        empty = bool(getattr(profile, "empty_negative_space", False))
        tags = [str(t).lower() for t in (getattr(profile, "tags", None) or [])]
        filename = str(getattr(profile, "filename", "") or "")

    hay = " ".join(tags + [filename, subject]).lower()
    skyline = subject == "skyline" or any(k in hay for k in ("skyline", "aerial", "drone", "cityscape"))
    if any(k in hay for k in ("interior", "lobby", "kitchen", "living", "bedroom", "suite", "residence")):
        busy = True
        if subject in {"unknown", "architecture"}:
            subject = "architecture"
    if any(k in hay for k in ("sky", "open", "void", "cloud")):
        empty = True

    # Subject-class heuristics — never a named building's pixel recipe.
    if subject in {"building", "architecture"}:
        horizon_y = 30.0 if format_preset in {"story", "reelsCover"} else 28.0
        focal = NormRect(18.0, horizon_y, 64.0, 58.0)
        negative = NormRect(6.0, 5.0, 88.0, max(16.0, horizon_y - 6.0))
        cog = (50.0, 58.0)
        lines = ["vertical", "horizontal"]
        safe = [negative, NormRect(6.0, 78.0, 50.0, 16.0)]
    elif skyline:
        horizon_y = 42.0
        focal = NormRect(8.0, 38.0, 84.0, 48.0)
        negative = NormRect(6.0, 5.0, 88.0, 30.0)
        cog = (50.0, 62.0)
        lines = ["horizontal"]
        safe = [negative, NormRect(8.0, 78.0, 70.0, 16.0)]
    elif subject == "people":
        horizon_y = 48.0
        focal = NormRect(28.0, 18.0, 44.0, 58.0)
        negative = NormRect(6.0, 72.0, 88.0, 22.0)
        cog = (50.0, 42.0)
        lines = ["vertical"]
        safe = [negative, NormRect(6.0, 6.0, 40.0, 16.0)]
    elif busy:
        horizon_y = 36.0
        focal = NormRect(16.0, 16.0, 68.0, 64.0)
        negative = NormRect(6.0, 72.0, 70.0, 22.0)
        cog = (50.0, 50.0)
        lines = ["diagonal"]
        safe = [negative, NormRect(6.0, 6.0, 36.0, 14.0)]
    elif empty:
        horizon_y = 40.0
        focal = NormRect(20.0, 36.0, 60.0, 48.0)
        negative = NormRect(8.0, 8.0, 70.0, 28.0)
        cog = (52.0, 58.0)
        lines = ["horizontal"]
        safe = [negative]
    else:
        horizon_y = 34.0
        focal = NormRect(20.0, 30.0, 60.0, 50.0)
        negative = NormRect(7.0, 7.0, 72.0, 22.0)
        cog = (50.0, 52.0)
        lines = ["horizontal"]
        safe = [negative, NormRect(7.0, 78.0, 55.0, 15.0)]

    protected = NormRect(
        x=focal.x + 4.0,
        y=focal.y + 4.0,
        w=max(20.0, focal.w - 8.0),
        h=max(18.0, focal.h - 10.0),
    )
    return ImageAnalysis(
        subject=subject,
        brightness=brightness,
        busy=busy,
        empty=empty,
        skyline=skyline,
        horizon_y=horizon_y,
        major_lines=lines,
        center_of_gravity=cog,
        focal_region=focal.clamped(),
        negative_space=negative.clamped(),
        safe_zones=[z.clamped() for z in safe],
        protected_focal=protected.clamped(),
        tags=tags,
        filename=filename,
    )


def _used_family_tokens(used_signals: list[str] | None) -> set[str]:
    used: set[str] = set()
    for raw in used_signals or []:
        token = str(raw or "").strip().upper()
        if not token:
            continue
        used.add(token)
        if token.startswith("HEADLINE:"):
            used.add(token)
        if token.startswith("METRIC:"):
            used.add(token)
        if token.startswith("CTA:"):
            used.add(token)
        if token in COMPOSITION_FAMILIES:
            used.add(token)
    return used


def choose_composition_family(
    *,
    plan: CreativePlan,
    analysis: ImageAnalysis,
    format_preset: str = "square",
    used_signals: list[str] | None = None,
    instruction: str = "",
    metric_count: int = 0,
) -> tuple[CompositionFamilyKind, list[str]]:
    notes: list[str] = []
    direction = str(plan.creative_direction or "")
    candidates = list(DIRECTION_FAMILIES.get(direction, ["EDITORIAL_HERO"]))
    hint = PRIMITIVE_FAMILY_HINT.get(str(plan.composition or ""))
    if hint and hint in candidates:
        candidates = [hint] + [c for c in candidates if c != hint]
        notes.append(f"primitive_hint:{hint}")

    # Image constraints — architecture must not park a statement over the building.
    building_mass = analysis.subject in {"building", "architecture"} or analysis.skyline
    if building_mass:
        banned = {"STATEMENT_LAYOUT"}
        if plan.visual_priority == "building" or plan.intent == "ARCHITECTURE":
            banned.update({"EDITORIAL_HERO"})
        filtered = [c for c in candidates if c not in banned]
        if filtered:
            candidates = filtered
            notes.append("avoid_type_on_building_mass")
        if "ARCHITECTURAL_MINIMAL" not in candidates and plan.intent == "ARCHITECTURE":
            candidates = ["ARCHITECTURAL_MINIMAL"] + candidates
    if analysis.subject == "people":
        preferred = [c for c in candidates if c in {"LOWER_THIRD", "LIFESTYLE_EDITORIAL", "IMAGE_DOMINANT"}]
        if preferred:
            candidates = preferred + [c for c in candidates if c not in preferred]
            notes.append("keep_type_off_faces")
    if analysis.busy:
        preferred = [c for c in candidates if c in {"OVERLAY_PANEL", "LOWER_THIRD", "SPLIT_LAYOUT"}]
        if preferred:
            candidates = preferred + [c for c in candidates if c not in preferred]
            notes.append("busy_asset_panel_or_band")
    if analysis.empty or analysis.skyline:
        preferred = [c for c in candidates if c in {"EDITORIAL_HERO", "FLOATING_DATA", "ASYMMETRIC_EDITORIAL"}]
        if preferred:
            candidates = preferred + [c for c in candidates if c not in preferred]
            notes.append("open_negative_space")
    if plan.include_metrics and metric_count >= 3:
        preferred = [c for c in candidates if c in {"INVESTMENT_GRID", "SPLIT_LAYOUT", "LOWER_THIRD"}]
        if preferred:
            candidates = preferred + [c for c in candidates if c not in preferred]
            notes.append("data_rich_not_always_horizontal")
    if plan.copy_density == "MINIMAL":
        preferred = [c for c in candidates if c in {"ARCHITECTURAL_MINIMAL", "IMAGE_DOMINANT", "LUXURY_BRAND"}]
        if preferred:
            candidates = preferred + [c for c in candidates if c not in preferred]
    if format_preset in {"story", "reelsCover"}:
        preferred = [c for c in candidates if c in {"LOWER_THIRD", "OVERLAY_PANEL", "IMAGE_DOMINANT", "SPLIT_LAYOUT"}]
        if preferred:
            candidates = preferred + [c for c in candidates if c not in preferred]
            notes.append("vertical_reflow_family")
    if format_preset == "landscape":
        preferred = [c for c in candidates if c in {"SPLIT_LAYOUT", "OVERLAY_PANEL", "ASYMMETRIC_EDITORIAL"}]
        if preferred:
            candidates = preferred + [c for c in candidates if c not in preferred]

    used = _used_family_tokens(used_signals)
    unused = [c for c in candidates if c not in used]
    pool = unused if unused else (candidates[1:] if len(candidates) > 1 else candidates)
    if not pool:
        picked: CompositionFamilyKind = candidates[0] if candidates else "EDITORIAL_HERO"
        notes.append("variety_exhausted_reuse")
        return picked, notes

    digest = hashlib.sha1((instruction or plan.concept or direction).encode("utf-8")).hexdigest()
    idx = int(digest[:8], 16) + sum(1 for s in used if s in COMPOSITION_FAMILIES)
    instr = (instruction or "").lower()
    if any(k in instr for k in ("ikinci", "second ", "another ", "bir diğer", "bir diger")):
        idx += 1
        notes.append("variety_followup")
    picked = pool[idx % len(pool)]
    notes.append(f"family:{picked}")
    return picked, notes


def choose_metric_composition(
    *,
    family: CompositionFamilyKind,
    metric_count: int,
    format_preset: str,
) -> tuple[MetricLayoutKind, MetricRegionKind]:
    """3 metrics on a square are not always a horizontal row."""
    n = max(0, metric_count)
    if n <= 0:
        return "HORIZONTAL_ROW", "none"
    if family == "SPLIT_LAYOUT":
        return ("VERTICAL_STACK" if n >= 2 else "SIDE_PANEL"), "side_panel"
    if family == "FLOATING_DATA":
        if n >= 3:
            return "HORIZONTAL_ROW", "lower_band"
        return "FLOATING_GROUP", "floating_group"
    if family == "LOWER_THIRD":
        if n >= 3 and format_preset == "square":
            return "2X2_GRID", "lower_band"
        return "HORIZONTAL_ROW" if n <= 2 else "2X2_GRID", "lower_band"
    if family == "INVESTMENT_GRID":
        if format_preset in {"story", "reelsCover"}:
            return "VERTICAL_STACK", "side_panel"
        if n == 1:
            return "FLOATING_GROUP", "floating_group"
        if n == 2:
            return "HORIZONTAL_ROW", "grid_block"
        # 3 figures: designed 2×2 / stack, never default three-across on square.
        if format_preset == "square":
            return "2X2_GRID", "grid_block"
        if format_preset == "portrait":
            return "VERTICAL_STACK", "grid_block"
        return "2X2_GRID", "lower_band"
    if n >= 3:
        return "2X2_GRID", "lower_band"
    if n == 2:
        return "HORIZONTAL_ROW", "under_headline"
    return "FLOATING_GROUP", "floating_group"


def _grid_for(format_preset: str) -> GridSpec:
    mx, my = format_margins(format_preset)
    gutter = 1.0 if format_preset in {"story", "reelsCover"} else 1.2
    return GridSpec(columns=12, rows=12, gutter=gutter, margin_x=mx, margin_y=my)


def _cell(grid: GridSpec, col: int, row: int, col_span: int, row_span: int) -> NormRect:
    """Map 12-col / 12-row cells into normalized space inside safe margins."""
    inner_w = 100.0 - 2 * grid.margin_x
    inner_h = 100.0 - 2 * grid.margin_y
    col_w = (inner_w - grid.gutter * (grid.columns - 1)) / grid.columns
    row_h = (inner_h - grid.gutter * (grid.rows - 1)) / grid.rows
    x = grid.margin_x + col * (col_w + grid.gutter)
    y = grid.margin_y + row * (row_h + grid.gutter)
    w = col_span * col_w + max(0, col_span - 1) * grid.gutter
    h = row_span * row_h + max(0, row_span - 1) * grid.gutter
    return NormRect(x=x, y=y, w=w, h=h).clamped()


def _avoid_focal(region: NormRect, protected: NormRect, fallback: NormRect) -> NormRect:
    if not region.intersects(protected, gap=1.0):
        return region
    return fallback


def _overlay_for(
    family: CompositionFamilyKind,
    analysis: ImageAnalysis,
    content: NormRect,
    contrast: str,
) -> tuple[str, list[OverlayRegion]]:
    zone = "top"
    if content.y >= 55:
        zone = "bottom"
    elif content.x <= 12 and content.w <= 48:
        zone = "left"
    strength = "subtle"
    if contrast in {"DARK_GRADIENT", "SOFT_OVERLAY", "LOCAL_TEXT_BACKDROP"}:
        strength = "localized"
    elif contrast == "NONE":
        return "none", []
    elif contrast == "LIGHT_GRADIENT":
        strength = "light"
    if family in {"OVERLAY_PANEL", "SPLIT_LAYOUT"}:
        if content.y >= 55:
            token = "soft-bottom" if strength != "light" else "light-bottom"
            region = NormRect(0, max(48.0, content.y - 10), 100, 100 - max(48.0, content.y - 10))
            return token, [OverlayRegion(kind=token, region=region, strength="localized")]
        token = f"{'soft' if strength != 'light' else 'light'}-left"
        region = NormRect(0, 0, min(52.0, content.x + content.w + 8), 100)
        return token, [OverlayRegion(kind=token, region=region, strength="localized")]
    if family in {"LOWER_THIRD", "INVESTMENT_GRID", "LIFESTYLE_EDITORIAL"} and zone == "bottom":
        token = f"{strength}-bottom" if strength in {"subtle", "light"} else "localized-bottom"
        if strength == "localized":
            token = "soft-bottom"
        region = NormRect(0, max(48.0, content.y - 8), 100, 100 - max(48.0, content.y - 8))
        return token, [OverlayRegion(kind=token, region=region, strength=strength)]
    if family in {"ARCHITECTURAL_MINIMAL", "IMAGE_DOMINANT"} and analysis.empty:
        token = "none" if analysis.brightness in {"dark", "mixed"} else "subtle-top"
        if token == "none":
            return "none", []
        return token, [OverlayRegion(kind=token, region=NormRect(0, 0, 100, 24), strength="subtle")]
    token = f"{strength}-{zone}" if strength in {"subtle", "light"} else f"localized-{zone}"
    if strength == "localized" and zone == "top":
        token = "localized-top"
    h = 32.0 if zone == "top" else (100.0 - content.y + 6 if zone == "bottom" else 100.0)
    y = 0.0 if zone != "bottom" else max(0.0, content.y - 6)
    w = 100.0 if zone != "left" else min(52.0, content.w + content.x + 8)
    x = 0.0
    return token, [OverlayRegion(kind=token, region=NormRect(x, y, w, h), strength=strength)]


def _family_regions(
    *,
    family: CompositionFamilyKind,
    grid: GridSpec,
    analysis: ImageAnalysis,
    include_support: bool,
    include_metrics: bool,
    include_cta: bool,
    include_brand: bool,
    format_preset: str,
    metric_count: int,
) -> dict[str, Any]:
    mx, my = grid.margin_x, grid.margin_y
    protected = analysis.protected_focal
    vertical = format_preset in {"story", "reelsCover"}
    portrait = format_preset == "portrait"
    split: SplitRatioKind | None = None
    metric: NormRect | None = None
    support: NormRect | None = None
    brand: NormRect | None = None
    cta: NormRect | None = None
    headline_kind: HeadlineRegionKind = "top_left"
    cta_place: CtaPlacementKind = "under_headline" if include_cta else "none"
    brand_kind: BrandLockupKind = "compact" if include_brand else "none"
    metric_layout, metric_kind = choose_metric_composition(
        family=family, metric_count=metric_count if include_metrics else 0, format_preset=format_preset
    )
    if not include_metrics:
        metric_kind = "none"
        metric_layout = None

    if family == "EDITORIAL_HERO":
        building_mass = analysis.subject in {"building", "architecture"} or analysis.skyline
        span = 5 if building_mass and not vertical else (8 if not vertical else 10)
        headline = _cell(grid, 0, 0, span, 2 if building_mass else (3 if include_support else 2))
        headline = _avoid_focal(headline, protected, _cell(grid, 0, 0, min(span, 6), 2))
        support = _cell(grid, 0, 3, min(span, 7), 2) if include_support else None
        brand = _cell(grid, 0, 0, 4, 1) if include_brand else None
        if include_brand:
            headline = _cell(grid, 0, 1, span, 2)
        cta = _cell(grid, 0, 4 if building_mass else (5 if include_support else 4), 4, 1) if include_cta else None
        cta_place = "under_headline"
        brand_kind = "horizontal" if include_brand else "none"
        headline_kind = "top_left"
        content = headline
        weight = VisualWeight(dominant="image", supporting="headline", tertiary="cta" if include_cta else None)
    elif family == "ARCHITECTURAL_MINIMAL":
        # Type lives in sky / negative space — never a large stack on the facade.
        sky_h = max(12.0, min(18.0, analysis.horizon_y - my - 2.0))
        headline = NormRect(mx, my, 52.0 if not vertical else 68.0, sky_h)
        headline = _avoid_focal(headline, protected, NormRect(mx, my, 46.0, 11.0))
        support = None
        brand = NormRect(mx, my + headline.h + 1.2, 28.0, 5.0) if include_brand else None
        cta = None
        cta_place = "none"
        brand_kind = "compact"
        headline_kind = "top_left"
        content = headline
        weight = VisualWeight(dominant="image", supporting="headline", tertiary="brand" if include_brand else None)
    elif family == "INVESTMENT_GRID":
        headline = _cell(grid, 0, 0, 9, 2)
        if analysis.subject in {"building", "architecture", "skyline"} or analysis.skyline:
            # Sky headline + bottom data band — never a figure row across the facade.
            headline = _cell(grid, 0, 0, 7, 2)
            headline_kind = "top_left"
            metric = _cell(grid, 0, 9, 12 if metric_layout != "VERTICAL_STACK" else 5, 3)
            metric_kind = "lower_band"
            cta = _cell(grid, 8, 11, 4, 1) if include_cta else None
            cta_place = "lower_third"
            brand = _cell(grid, 0, 0, 5, 1) if include_brand else None
            if include_brand:
                headline = _cell(grid, 0, 1, 7, 2)
        else:
            headline_kind = "top_left"
            metric = _cell(grid, 0, 3, 10, 4)
            metric_kind = "grid_block"
            cta = _cell(grid, 0, 8, 4, 1) if include_cta else None
            cta_place = "under_headline"
            brand = _cell(grid, 0, 0, 5, 1) if include_brand else None
            headline = _cell(grid, 0, 1, 9, 2)
        support = None
        brand_kind = "stacked" if include_brand else "none"
        content = metric
        weight = VisualWeight(dominant="metrics", supporting="headline", tertiary="cta" if include_cta else None)
    elif family == "LUXURY_BRAND":
        # True luxury lockup — never a large centered stack on the building mass.
        building_mass = analysis.subject in {"building", "architecture"} or analysis.skyline
        if building_mass:
            brand = _cell(grid, 0, 0, 5, 1) if include_brand else None
            headline = _cell(grid, 0, 1 if include_brand else 0, 7, 2)
            headline_kind = "top_left"
            support = None
            cta = None
            cta_place = "none"
        else:
            headline = _cell(grid, 1, 4, 10, 3)
            headline_kind = "center"
            support = _cell(grid, 2, 7, 8, 1) if include_support else None
            brand = _cell(grid, 3, 3, 6, 1) if include_brand else _cell(grid, 3, 3, 6, 1)
            cta = _cell(grid, 4, 9, 4, 1) if include_cta else None
            cta_place = "under_headline" if include_cta else "none"
        brand_kind = "stacked"
        content = headline
        weight = VisualWeight(dominant="headline", supporting="brand", tertiary="cta" if include_cta else None)
    elif family == "LIFESTYLE_EDITORIAL":
        interior = analysis.busy or analysis.subject in {"people", "architecture"}
        if interior:
            headline = _cell(grid, 0, 8, 9, 2)
            headline_kind = "bottom_left"
            support = _cell(grid, 0, 10, 7, 1) if include_support else None
            cta = _cell(grid, 0, 11, 4, 1) if include_cta else None
            cta_place = "lower_third"
            brand = _cell(grid, 8, 0, 4, 1) if include_brand else None
        else:
            headline = _cell(grid, 0, 1, 8, 2)
            headline_kind = "top_left"
            support = _cell(grid, 0, 3, 6, 2) if include_support else None
            cta = _cell(grid, 0, 6, 4, 1) if include_cta else None
            cta_place = "under_headline"
            brand = _cell(grid, 0, 0, 4, 1) if include_brand else None
        brand_kind = "compact"
        content = headline
        weight = VisualWeight(dominant="image", supporting="headline", tertiary="support" if include_support else None)
    elif family == "SPLIT_LAYOUT":
        # Only 30/70, 40/60, 50/50 — pick by copy/metrics density, not decoration.
        if include_metrics and metric_count >= 3:
            split = "40/60"
            col_span = 5
        elif include_support or include_metrics:
            split = "30/70"
            col_span = 4
        else:
            split = "50/50"
            col_span = 6
        if vertical:
            split = "40/60"
            headline = _cell(grid, 0, 0, 12, 2)
            metric = _cell(grid, 0, 3, 12, 4) if include_metrics else None
            support = _cell(grid, 0, 2, 10, 1) if include_support else None
            cta = _cell(grid, 0, 8, 5, 1) if include_cta else None
            brand = _cell(grid, 0, 0, 5, 1) if include_brand else None
            headline_kind = "top"
            metric_kind = "lower_band" if include_metrics else "none"
            cta_place = "panel"
        else:
            headline = _cell(grid, 0, 1, col_span, 3)
            metric = _cell(grid, 0, 5, col_span, 4) if include_metrics else None
            support = _cell(grid, 0, 4, col_span, 2) if include_support and not include_metrics else None
            cta = _cell(grid, 0, 10, min(4, col_span), 1) if include_cta else None
            brand = _cell(grid, 0, 0, min(4, col_span), 1) if include_brand else None
            headline_kind = "left"
            metric_kind = "side_panel" if include_metrics else "none"
            cta_place = "panel"
        brand_kind = "stacked"
        content = headline
        weight = VisualWeight(
            dominant="metrics" if include_metrics else "headline",
            supporting="image",
            tertiary="cta" if include_cta else None,
        )
    elif family == "OVERLAY_PANEL":
        # If the mass sits on the left, do not park an editorial column on the architecture.
        left_weighted = analysis.center_of_gravity[0] < 42 or analysis.focal_region.x < 18
        if left_weighted and not vertical:
            headline = _cell(grid, 0, 8, 9, 2)
            support = _cell(grid, 0, 10, 7, 1) if include_support else None
            metric = _cell(grid, 0, 10, 10, 2) if include_metrics else None
            cta = _cell(grid, 0, 11, 4, 1) if include_cta else None
            brand = _cell(grid, 0, 7, 4, 1) if include_brand else None
            headline_kind = "lower_third"
            content = NormRect(mx, 62.0, 100 - 2 * mx, 100 - 62.0 - my)
        else:
            panel_span = 5 if not vertical else 12
            headline = _cell(grid, 0, 2 if include_brand else 1, panel_span, 3)
            support = _cell(grid, 0, 5, panel_span, 2) if include_support else None
            metric = _cell(grid, 0, 7, panel_span, 3) if include_metrics else None
            cta = _cell(grid, 0, 10, 4, 1) if include_cta else None
            brand = _cell(grid, 0, 0, 4, 1) if include_brand else None
            headline_kind = "left"
            content = NormRect(grid.margin_x, grid.margin_y, 42.0 if not vertical else 88.0, 86.0)
        cta_place = "panel"
        brand_kind = "horizontal"
        weight = VisualWeight(dominant="headline", supporting="image", tertiary="support" if include_support else None)
    elif family == "STATEMENT_LAYOUT":
        headline = _cell(grid, 1, 3, 10, 4)
        headline_kind = "center"
        support = _cell(grid, 2, 8, 8, 1) if include_support else None
        brand = _cell(grid, 3, 2, 6, 1) if include_brand else None
        cta = _cell(grid, 4, 10, 4, 1) if include_cta else None
        cta_place = "under_headline" if include_cta else "none"
        brand_kind = "stacked"
        content = headline
        weight = VisualWeight(dominant="headline", supporting="image", tertiary="brand" if include_brand else None)
    elif family == "ASYMMETRIC_EDITORIAL":
        building_mass = analysis.subject in {"building", "architecture"} or analysis.skyline
        headline = _cell(grid, 0 if building_mass else 1, 1, 6 if building_mass else 8, 2 if building_mass else 3)
        headline = _avoid_focal(headline, protected, _cell(grid, 0, 0, 6, 2))
        # Offset tension, but never park supporting copy on the protected mass.
        if building_mass:
            support = _cell(grid, 0, 3, 5, 2) if include_support else None
            cta = _cell(grid, 0, 9, 4, 1) if include_cta else None
        else:
            support = _cell(grid, 3, 5, 6, 2) if include_support else None
            cta = _cell(grid, 1, 8, 4, 1) if include_cta else None
        brand = _cell(grid, 8, 0, 4, 1) if include_brand else None
        headline_kind = "asymmetric_offset"
        cta_place = "under_headline"
        brand_kind = "compact"
        content = headline
        weight = VisualWeight(dominant="headline", supporting="image", tertiary="cta" if include_cta else None)
    elif family == "LOWER_THIRD":
        headline = _cell(grid, 0, 8, 9, 2)
        headline = _avoid_focal(headline, protected, _cell(grid, 0, 8, 8, 2))
        support = _cell(grid, 0, 10, 7, 1) if include_support else None
        metric = _cell(grid, 0, 10, 10, 2) if include_metrics else None
        cta = _cell(grid, 8, 11, 4, 1) if include_cta else None
        brand = _cell(grid, 0, 7, 4, 1) if include_brand else None
        headline_kind = "lower_third"
        cta_place = "lower_third"
        brand_kind = "horizontal"
        content = NormRect(mx, 62.0, 100 - 2 * mx, 100 - 62.0 - my)
        weight = VisualWeight(
            dominant="image",
            supporting="metrics" if include_metrics else "headline",
            tertiary="cta" if include_cta else None,
        )
    elif family == "FLOATING_DATA":
        # Tight cluster in negative space — image remains the field.
        cluster = analysis.negative_space
        if cluster.intersects(protected, gap=2.0) or cluster.h < 12:
            cluster = NormRect(mx, my, 56.0, 22.0)
        headline = NormRect(cluster.x, cluster.y, min(70.0, max(48.0, cluster.w)), 12.0)
        headline = _avoid_focal(headline, protected, NormRect(mx, my, 62.0, 12.0))
        metric = None
        if include_metrics:
            metric_h = 16.0 if metric_count >= 3 else 14.0
            proposed = NormRect(
                cluster.x,
                headline.y + headline.h + 1.6,
                min(52.0, cluster.w) if metric_count < 3 else 86.0,
                metric_h,
            )
            hits_mass = proposed.intersects(protected, gap=1.0) or proposed.y + proposed.h > max(
                28.0, analysis.horizon_y - 2.0
            )
            if metric_count >= 3 or hits_mass:
                lower = next((z for z in analysis.safe_zones if z.y >= 68), NormRect(mx, 78.0, 86.0, 16.0))
                metric = NormRect(mx, lower.y, min(86.0, max(lower.w, 78.0)), max(14.0, lower.h))
                metric_layout = "HORIZONTAL_ROW"
                metric_kind = "lower_band"
            else:
                metric = proposed
                metric_kind = "floating_group"
        support = (
            NormRect(cluster.x, headline.y + headline.h + 1.4, min(48.0, cluster.w), 8.0)
            if include_support and not include_metrics
            else None
        )
        if include_cta and metric is not None and metric_kind == "lower_band":
            cta = NormRect(mx, max(headline.y + headline.h + 1.4, metric.y - 8.0), 32.0, 6.0)
            cta_place = "under_headline"
        elif include_cta:
            cta = NormRect(
                cluster.x,
                (metric or support or headline).y + (metric or support or headline).h + 1.4,
                28.0,
                6.0,
            )
            cta_place = "under_headline"
        else:
            cta = None
            cta_place = "none"
        brand = NormRect(100 - mx - 22.0, my, 22.0, 5.0) if include_brand else None
        headline_kind = "top_left" if cluster.y < 40 else "bottom_left"
        brand_kind = "compact"
        if not include_metrics:
            metric_kind = "none"
        content = cluster
        weight = VisualWeight(
            dominant="image",
            supporting="metrics" if include_metrics else "headline",
            tertiary="cta" if include_cta else None,
        )
    else:  # IMAGE_DOMINANT
        if analysis.subject == "people" or analysis.busy:
            headline = _cell(grid, 0, 9, 7, 2)
            headline_kind = "bottom_left"
        else:
            headline = _cell(grid, 0, 0, 7, 2)
            headline = _avoid_focal(headline, protected, _cell(grid, 0, 0, 6, 2))
            headline_kind = "top_left"
        support = None
        metric = None
        cta = _cell(grid, 0, 11, 3, 1) if include_cta else None
        brand = _cell(grid, 9, 0, 3, 1) if include_brand else None
        cta_place = "opposite_brand" if include_cta and include_brand else ("bottom" if include_cta else "none")
        brand_kind = "compact"
        content = headline
        weight = VisualWeight(dominant="image", supporting="headline", tertiary="brand" if include_brand else None)

    # Portrait/story reflow of groups — not mere scale.
    if portrait and family in {"EDITORIAL_HERO", "ASYMMETRIC_EDITORIAL"}:
        headline = _cell(grid, 0, 0, 10, 3)
        if include_support:
            support = _cell(grid, 0, 3, 8, 2)
        if include_cta:
            cta = _cell(grid, 0, 6, 4, 1)
            cta_place = "under_headline"
    if vertical and family in {"INVESTMENT_GRID", "SPLIT_LAYOUT"} and include_metrics:
        metric = _cell(grid, 0, 4, 12, 5)
        metric_layout = "VERTICAL_STACK"
        metric_kind = "side_panel"

    locals_map = locals()
    metric_rect = locals_map.get("metric")
    return {
        "headline": headline,
        "support": support,
        "metric": metric_rect,
        "brand": brand,
        "cta": cta,
        "content": content,
        "headline_kind": headline_kind,
        "metric_kind": metric_kind,
        "metric_layout": metric_layout,
        "cta_place": cta_place,
        "brand_kind": brand_kind,
        "split": split,
        "weight": weight,
    }


def build_composition_blueprint(
    *,
    plan: CreativePlan,
    profile: Any = None,
    format_preset: str = "square",
    used_signals: list[str] | None = None,
    instruction: str = "",
    metric_count: int = 0,
    include_support: bool | None = None,
    include_metrics: bool | None = None,
    include_cta: bool | None = None,
    include_brand: bool | None = None,
    project_id: Any = None,
) -> CompositionBlueprint:
    analysis = analyze_image(profile, format_preset=format_preset)
    family, family_notes = choose_composition_family(
        plan=plan,
        analysis=analysis,
        format_preset=format_preset,
        used_signals=used_signals,
        instruction=instruction,
        metric_count=metric_count,
    )
    grid = _grid_for(format_preset)
    support = plan.include_support if include_support is None else include_support
    metrics = plan.include_metrics if include_metrics is None else include_metrics
    cta = plan.include_cta if include_cta is None else include_cta
    brand = plan.include_brand if include_brand is None else include_brand
    if family in {"ARCHITECTURAL_MINIMAL", "IMAGE_DOMINANT"}:
        support = False
    if family == "LUXURY_BRAND" and not include_support:
        support = False
    if family == "ARCHITECTURAL_MINIMAL" and plan.cta_strategy == "NONE":
        cta = False
    if not metrics:
        metric_count = 0

    regions = _family_regions(
        family=family,
        grid=grid,
        analysis=analysis,
        include_support=bool(support),
        include_metrics=bool(metrics) and metric_count > 0,
        include_cta=bool(cta),
        include_brand=bool(brand),
        format_preset=format_preset,
        metric_count=metric_count,
    )
    overlay_token, overlays = _overlay_for(
        family, analysis, regions["content"], str(plan.contrast_strategy or "")
    )
    metric_rect = regions.get("metric")
    if (
        family in {"FLOATING_DATA", "INVESTMENT_GRID"}
        and isinstance(metric_rect, NormRect)
        and metric_rect.y >= 55
    ):
        overlay_token = "soft-bottom"
        overlays = [
            OverlayRegion(
                kind="soft-bottom",
                region=NormRect(0, max(52.0, metric_rect.y - 10), 100, 100 - max(52.0, metric_rect.y - 10)),
                strength="localized",
            )
        ]
    if family == "LUXURY_BRAND" and regions["headline"].y < 28:
        overlay_token = "localized-top"
        overlays = [OverlayRegion(kind="localized-top", region=NormRect(0, 0, 100, 28), strength="localized")]
    align = "center" if family in {"STATEMENT_LAYOUT", "LUXURY_BRAND"} else "left"
    if family == "ASYMMETRIC_EDITORIAL":
        align = "left"
    if family == "LUXURY_BRAND" and regions["headline_kind"] in {"top", "top_left", "lower_third"}:
        if analysis.subject in {"building", "architecture"} or analysis.skyline:
            align = "left"

    groups: list[CompositionGroup] = []
    if regions["brand"] is not None and brand:
        groups.append(
            CompositionGroup(
                kind="BRAND_LOCKUP",
                region=regions["brand"],
                alignment=align,
                spacing_inside=0.8,
                members=["eyebrow", "brand"],
                weight="tertiary",
            )
        )
    groups.append(
        CompositionGroup(
            kind="HEADLINE",
            region=regions["headline"],
            alignment=align,
            spacing_inside=1.2,
            members=["headline"],
            weight="dominant" if regions["weight"].dominant == "headline" else "supporting",
        )
    )
    if regions["support"] is not None and support:
        groups.append(
            CompositionGroup(
                kind="SUPPORTING_COPY",
                region=regions["support"],
                alignment=align,
                spacing_inside=1.0,
                members=["body"],
                weight="tertiary",
            )
        )
    if regions["metric"] is not None and metrics and metric_count > 0:
        groups.append(
            CompositionGroup(
                kind="METRIC",
                region=regions["metric"],
                alignment="left",
                spacing_inside=1.6,
                members=["metric_group"],
                weight="dominant" if regions["weight"].dominant == "metrics" else "supporting",
            )
        )
    if regions["cta"] is not None and cta:
        groups.append(
            CompositionGroup(
                kind="CTA",
                region=regions["cta"],
                alignment=align,
                spacing_inside=0.6,
                members=["cta"],
                weight="tertiary",
            )
        )

    bp = CompositionBlueprint(
        composition_family=family,
        focal_region=analysis.focal_region,
        content_zone=regions["content"],
        negative_space=analysis.negative_space,
        image_crop=ImageCrop(focal_bias="top" if analysis.subject in {"building", "architecture"} else "center"),
        headline_region=regions["headline"],
        support_region=regions["support"],
        metric_region=regions["metric"],
        brand_region=regions["brand"],
        cta_region=regions["cta"],
        alignment=align,
        grid=grid,
        overlay_regions=overlays,
        visual_weight=regions["weight"],
        safe_zones=list(analysis.safe_zones),
        groups=groups,
        headline_region_kind=regions["headline_kind"],
        metric_region_kind=regions["metric_kind"],
        cta_placement=regions["cta_place"],
        brand_lockup=regions["brand_kind"],
        metric_layout=regions["metric_layout"],
        split_ratio=regions["split"],
        overlay_token=overlay_token,
        format_preset=format_preset,
        decisions=family_notes + [
            f"headline:{regions['headline_kind']}",
            f"metric:{regions['metric_kind']}",
            f"cta:{regions['cta_place']}",
            f"overlay:{overlay_token}",
        ],
    )
    bp.diversity_key = ":".join(bp.diversity_tokens())
    remember_project_variety(
        project_id,
        bp.composition_family,
        f"headline:{bp.headline_region_kind}",
        f"metric:{bp.metric_region_kind}",
        f"cta:{bp.cta_placement}",
    )
    return bp


def sibling_blueprint_signals(posts: list[dict[str, Any]] | None) -> list[str]:
    """Diversity only — never a source of copy, facts, or metrics."""
    used: list[str] = []
    for post in posts or []:
        if not isinstance(post, dict):
            continue
        meta = post.get("generationMeta") if isinstance(post.get("generationMeta"), dict) else {}
        raw = post.get("compositionBlueprint") or post.get("composition_blueprint")
        if raw is None and isinstance(meta, dict):
            raw = meta.get("composition_blueprint")
        if isinstance(raw, dict):
            family = str(raw.get("composition_family") or "")
            if family and family not in used:
                used.append(family)
            for key, prefix in (
                ("headline_region_kind", "headline"),
                ("metric_region_kind", "metric"),
                ("cta_placement", "cta"),
            ):
                value = str(raw.get(key) or "")
                token = f"{prefix}:{value}" if value else ""
                if token and token not in used:
                    used.append(token)
        signal = post.get("diversitySignal") or post.get("diversity_signal")
        if isinstance(signal, str):
            for part in signal.split(":"):
                token = part.strip()
                if token and token not in used:
                    used.append(token)
    used.extend(combined_variety_signals(posts))
    # Deduplicate preserving order
    seen: set[str] = set()
    out: list[str] = []
    for token in used:
        if token not in seen:
            seen.add(token)
            out.append(token)
    return out
