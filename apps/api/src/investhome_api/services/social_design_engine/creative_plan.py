"""Creative Direction + CreativePlan — strategies, not templates.

Intent does not map 1:1 onto a layout. Direction is chosen from intent +
project facts + asset analysis + copy length + format + variety signal.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from investhome_api.services.social_design_engine.creative_intent import CreativeIntentKind

# Process-local diversity ring for NEW posts in the current project.
# Sibling draft fields can drop on round-trip; this is not a source of facts/copy/metrics.
_PROJECT_VARIETY: dict[str, list[str]] = defaultdict(list)
_PROJECT_VARIETY_CAP = 40

CreativeDirectionKind = Literal[
    "EDITORIAL_LUXURY",
    "INVESTMENT_DATA",
    "LOCATION_STORY",
    "ARCHITECTURAL_FEATURE",
    "LIFESTYLE_PREMIUM",
    "BRAND_STATEMENT",
    "INFORMATIONAL_EDITORIAL",
]

CompositionPrimitive = Literal[
    "TOP_LEFT_EDITORIAL",
    "BOTTOM_LEFT_EDITORIAL",
    "SIDE_COLUMN",
    "CENTER_STATEMENT",
    "LOWER_THIRD",
    "ASYMMETRIC_EDITORIAL",
    "DATA_GRID",
    "IMAGE_DOMINANT",
    "SPLIT_INFORMATION",
    "FLOATING_INFORMATION_GROUP",
]

CopyDensityKind = Literal["MINIMAL", "LOW", "MEDIUM", "DATA_RICH"]
ContrastStrategyKind = Literal[
    "NONE",
    "SUBTLE_GRADIENT",
    "DARK_GRADIENT",
    "LIGHT_GRADIENT",
    "SOFT_OVERLAY",
    "LOCAL_TEXT_BACKDROP",
]
CtaStrategyKind = Literal["NONE", "TEXT_LINK_STYLE", "PILL_BUTTON", "MINIMAL_BUTTON"]
MetricStrategyKind = Literal["NONE", "STRUCTURED_GROUP"]
BrandTreatmentKind = Literal["NONE", "IDENTITY_LINE", "CORNER_MARK"]
VisualPriorityKind = Literal[
    "place",
    "figures",
    "building",
    "atmosphere",
    "identity",
    "announcement",
    "explanation",
]
HierarchyRole = Literal["PRIMARY", "SECONDARY", "TERTIARY", "CTA", "BRAND"]

# Compatibility families used by existing layout grammar.
FamilyKind = Literal["MINIMAL_HERO", "EDITORIAL", "INVESTMENT", "LOCATION"]

DIRECTION_LIBRARY: dict[CreativeDirectionKind, dict[str, Any]] = {
    "EDITORIAL_LUXURY": {
        "visual_priority": "place",
        "default_density": "LOW",
        "default_composition": "TOP_LEFT_EDITORIAL",
        "family": "EDITORIAL",
        "cta": "TEXT_LINK_STYLE",
        "concept": "Quiet luxury editorial: photography leads, type is considered, not filled.",
    },
    "INVESTMENT_DATA": {
        "visual_priority": "figures",
        "default_density": "DATA_RICH",
        "default_composition": "DATA_GRID",
        "family": "INVESTMENT",
        "cta": "PILL_BUTTON",
        "concept": "Investment case: eligible figures are the hero; architecture remains visible.",
    },
    "LOCATION_STORY": {
        "visual_priority": "place",
        "default_density": "MEDIUM",
        "default_composition": "TOP_LEFT_EDITORIAL",
        "family": "LOCATION",
        "cta": "TEXT_LINK_STYLE",
        "concept": "Place-led story: the project belongs to the city, not a spec sheet.",
    },
    "ARCHITECTURAL_FEATURE": {
        "visual_priority": "building",
        "default_density": "MINIMAL",
        "default_composition": "IMAGE_DOMINANT",
        "family": "MINIMAL_HERO",
        "cta": "NONE",
        "concept": "Building remains the hero. Restrained type in negative space.",
    },
    "LIFESTYLE_PREMIUM": {
        "visual_priority": "atmosphere",
        "default_density": "LOW",
        "default_composition": "IMAGE_DOMINANT",
        "family": "MINIMAL_HERO",
        "cta": "MINIMAL_BUTTON",
        "concept": "Aspirational atmosphere without inventing amenities.",
    },
    "BRAND_STATEMENT": {
        "visual_priority": "identity",
        "default_density": "LOW",
        "default_composition": "CENTER_STATEMENT",
        "family": "EDITORIAL",
        "cta": "NONE",
        "concept": "Identity lockup: the project name and one line of presence.",
    },
    "INFORMATIONAL_EDITORIAL": {
        "visual_priority": "explanation",
        "default_density": "MEDIUM",
        "default_composition": "SIDE_COLUMN",
        "family": "EDITORIAL",
        "cta": "TEXT_LINK_STYLE",
        "concept": "Clear editorial information. Density with breathing room.",
    },
}

PRIMITIVE_TO_FAMILY: dict[CompositionPrimitive, FamilyKind] = {
    "TOP_LEFT_EDITORIAL": "LOCATION",
    "BOTTOM_LEFT_EDITORIAL": "MINIMAL_HERO",
    "SIDE_COLUMN": "EDITORIAL",
    "CENTER_STATEMENT": "EDITORIAL",
    "LOWER_THIRD": "INVESTMENT",
    "ASYMMETRIC_EDITORIAL": "EDITORIAL",
    "DATA_GRID": "INVESTMENT",
    "IMAGE_DOMINANT": "MINIMAL_HERO",
    "SPLIT_INFORMATION": "EDITORIAL",
    "FLOATING_INFORMATION_GROUP": "LOCATION",
}

DENSITY_TO_LEGACY: dict[CopyDensityKind, str] = {
    "MINIMAL": "sparse",
    "LOW": "sparse",
    "MEDIUM": "moderate",
    "DATA_RICH": "dense",
}

CONTRAST_TO_OVERLAY: dict[ContrastStrategyKind, str] = {
    "NONE": "none",
    "SUBTLE_GRADIENT": "subtle",
    "DARK_GRADIENT": "localized",
    "LIGHT_GRADIENT": "light",
    "SOFT_OVERLAY": "soft",
    "LOCAL_TEXT_BACKDROP": "backdrop",
}


@dataclass
class HierarchyPlan:
    primary: str = "headline"
    secondary: str = "body"
    tertiary: str = "eyebrow"
    cta: str = "cta"
    brand: str = "eyebrow"


@dataclass
class TextRegionPlan:
    zone: str = "top"
    align: str = "left"
    width_ratio: float = 0.72
    avoid_focal: bool = True


@dataclass
class CreativePlan:
    intent: CreativeIntentKind
    audience: str
    objective: str
    creative_direction: CreativeDirectionKind
    visual_priority: VisualPriorityKind
    hierarchy: HierarchyPlan = field(default_factory=HierarchyPlan)
    copy_density: CopyDensityKind = "LOW"
    composition: CompositionPrimitive = "TOP_LEFT_EDITORIAL"
    text_regions: TextRegionPlan = field(default_factory=TextRegionPlan)
    image_strategy: str = "photography_is_hero"
    contrast_strategy: ContrastStrategyKind = "SUBTLE_GRADIENT"
    overlay_strategy: str = "subtle-top"
    overlay_region: str = "top"
    metric_strategy: MetricStrategyKind = "NONE"
    cta_strategy: CtaStrategyKind = "TEXT_LINK_STYLE"
    brand_treatment: BrandTreatmentKind = "IDENTITY_LINE"
    family: FamilyKind = "LOCATION"
    include_eyebrow: bool = False
    include_support: bool = True
    include_cta: bool = True
    include_metrics: bool = False
    include_brand: bool = True
    alignment: str = "left"
    safe_text_zone: str = "top"
    concept: str = ""
    decisions: list[str] = field(default_factory=list)
    variety_avoided: list[str] = field(default_factory=list)


def _asset_subject(profile: Any) -> str:
    if profile is None:
        return "unknown"
    if isinstance(profile, dict):
        return str(profile.get("subject") or "unknown")
    return str(getattr(profile, "subject", "unknown") or "unknown")


def _asset_zone(profile: Any) -> str:
    if profile is None:
        return "top"
    if isinstance(profile, dict):
        return str(profile.get("safe_text_zone") or profile.get("negative_space") or "top")
    return str(getattr(profile, "safe_text_zone", None) or getattr(profile, "negative_space", "top") or "top")


def _asset_brightness(profile: Any) -> str:
    if profile is None:
        return "mixed"
    if isinstance(profile, dict):
        return str(profile.get("brightness") or "mixed")
    return str(getattr(profile, "brightness", "mixed") or "mixed")


def _asset_busy(profile: Any) -> bool:
    if profile is None:
        return False
    tags = []
    if isinstance(profile, dict):
        tags = [str(t).lower() for t in (profile.get("tags") or [])]
        hay = " ".join(tags + [str(profile.get("filename") or "")]).lower()
        if profile.get("busy"):
            return True
    else:
        tags = [str(t).lower() for t in (getattr(profile, "tags", None) or [])]
        hay = " ".join(tags + [str(getattr(profile, "filename", "") or "")]).lower()
        if getattr(profile, "busy", False):
            return True
    return any(k in hay for k in ("busy", "crowd", "clutter", "detail", "interior", "kitchen", "lobby"))


def _asset_empty(profile: Any) -> bool:
    if profile is None:
        return False
    if isinstance(profile, dict):
        hay = " ".join([str(profile.get("filename") or "")] + [str(t) for t in (profile.get("tags") or [])]).lower()
        if profile.get("empty_negative_space"):
            return True
    else:
        hay = " ".join([str(getattr(profile, "filename", "") or "")] + [str(t) for t in (getattr(profile, "tags", None) or [])]).lower()
        if getattr(profile, "empty_negative_space", False):
            return True
    return any(k in hay for k in ("sky", "aerial", "drone", "skyline", "empty", "open"))


def sibling_composition_signals(posts: list[dict[str, Any]] | None) -> list[str]:
    """Diversity signal only — never a source of campaign facts, copy, or metrics."""
    used: list[str] = []
    for post in posts or []:
        if not isinstance(post, dict):
            continue
        primitive = post.get("compositionPrimitive") or post.get("composition_primitive")
        meta = post.get("generationMeta") if isinstance(post.get("generationMeta"), dict) else {}
        plan = meta.get("creative_plan") if isinstance(meta, dict) else None
        camel_plan = post.get("creativePlan") if isinstance(post.get("creativePlan"), dict) else None
        for candidate in (plan, camel_plan):
            if not isinstance(candidate, dict):
                continue
            primitive = primitive or candidate.get("composition")
            direction = candidate.get("creative_direction")
            if direction and str(direction) not in used:
                used.append(str(direction))
        if primitive and str(primitive) not in used:
            used.append(str(primitive))
        family = post.get("compositionStrategy") or post.get("composition_strategy")
        if family and str(family) not in used:
            used.append(str(family))
        signal = post.get("diversitySignal") or post.get("diversity_signal")
        if isinstance(signal, str) and ":" in signal:
            for part in signal.split(":"):
                token = part.strip()
                if token and token not in used:
                    used.append(token)
        if isinstance(meta, dict):
            plan_dict = meta.get("design_plan")
            if isinstance(plan_dict, dict):
                prim = plan_dict.get("composition_primitive") or plan_dict.get("compositionPrimitive")
                if prim and str(prim) not in used:
                    used.append(str(prim))
            bp = meta.get("composition_blueprint") if isinstance(meta.get("composition_blueprint"), dict) else None
            if isinstance(bp, dict):
                fam = bp.get("composition_family")
                if fam and str(fam) not in used:
                    used.append(str(fam))
                for key, prefix in (
                    ("headline_region_kind", "headline"),
                    ("metric_region_kind", "metric"),
                    ("cta_placement", "cta"),
                ):
                    value = bp.get(key)
                    token = f"{prefix}:{value}" if value else ""
                    if token and token not in used:
                        used.append(token)
        raw_bp = post.get("compositionBlueprint") or post.get("composition_blueprint")
        if isinstance(raw_bp, dict):
            fam = raw_bp.get("composition_family")
            if fam and str(fam) not in used:
                used.append(str(fam))
    return used


def project_variety_signals(project_id: Any) -> list[str]:
    key = str(project_id or "").strip()
    if not key:
        return []
    return list(_PROJECT_VARIETY.get(key) or [])


def remember_project_variety(project_id: Any, *tokens: str) -> None:
    key = str(project_id or "").strip()
    if not key:
        return
    buf = _PROJECT_VARIETY[key]
    for token in tokens:
        value = str(token or "").strip()
        if value:
            buf.append(value)
    _PROJECT_VARIETY[key] = buf[-_PROJECT_VARIETY_CAP:]


def combined_variety_signals(
    sibling_posts: list[dict[str, Any]] | None,
    project_id: Any = None,
) -> list[str]:
    used = sibling_composition_signals(sibling_posts)
    for token in project_variety_signals(project_id):
        if token not in used:
            used.append(token)
    return used


def choose_creative_direction(
    *,
    intent: CreativeIntentKind,
    profile: Any = None,
    has_eligible_metrics: bool = False,
    copy_length: int = 0,
    format_preset: str = "square",
    campaign_goal: str | None = None,
    tone: str = "premium",
    used_signals: list[str] | None = None,
    instruction: str = "",
) -> tuple[CreativeDirectionKind, list[str]]:
    """Not 1:1 with intent. Two LOCATION posts may diverge."""
    decisions: list[str] = []
    used = {str(s).upper() for s in (used_signals or [])}
    subject = _asset_subject(profile)
    instr = (instruction or "").lower()
    goal = (campaign_goal or "").lower()
    candidates: list[tuple[CreativeDirectionKind, float]] = []

    def add(kind: CreativeDirectionKind, score: float, why: str) -> None:
        candidates.append((kind, score))
        decisions.append(f"{kind}:{why}:{score:.1f}")

    if intent == "LOCATION":
        add("LOCATION_STORY", 4.0, "place_led")
        add("EDITORIAL_LUXURY", 3.2, "premium_place")
        if subject in {"skyline", "unknown"} or _asset_empty(profile):
            add("LOCATION_STORY", 1.6, "skyline_or_open")
        if subject in {"building", "architecture"} and tone in {"premium", "luxury"}:
            add("EDITORIAL_LUXURY", 1.8, "building_luxury")
        if "editorial" in instr or "quiet luxury" in instr or "lüks" in instr or "luks" in instr:
            add("EDITORIAL_LUXURY", 1.5, "editorial_ask")
        if format_preset in {"story", "reelsCover"}:
            add("EDITORIAL_LUXURY", 0.6, "vertical_editorial")
    elif intent == "INVESTMENT":
        if has_eligible_metrics:
            add("INVESTMENT_DATA", 5.5, "eligible_metrics")
            add("INFORMATIONAL_EDITORIAL", 1.2, "alt_without_grid")
        else:
            add("INFORMATIONAL_EDITORIAL", 4.2, "no_eligible_metrics")
            add("BRAND_STATEMENT", 2.4, "identity_fallback")
            decisions.append("metrics_absent_no_invention")
    elif intent == "ARCHITECTURE":
        add("ARCHITECTURAL_FEATURE", 5.0, "building_hero")
        if subject in {"detail"} or copy_length > 80:
            add("EDITORIAL_LUXURY", 2.0, "detail_or_longer_copy")
        else:
            add("EDITORIAL_LUXURY", 0.8, "alt_editorial")
    elif intent == "LIFESTYLE":
        add("LIFESTYLE_PREMIUM", 4.8, "atmosphere")
        add("EDITORIAL_LUXURY", 2.2, "quiet_lifestyle")
        if subject == "people":
            add("LIFESTYLE_PREMIUM", 1.2, "people_subject")
    elif intent == "BRAND":
        add("BRAND_STATEMENT", 4.6, "identity")
        add("EDITORIAL_LUXURY", 2.6, "premium_identity")
        if subject in {"building", "architecture"}:
            add("ARCHITECTURAL_FEATURE", 1.4, "building_as_brand")
    elif intent == "ANNOUNCEMENT":
        add("BRAND_STATEMENT", 4.0, "arrival")
        add("INFORMATIONAL_EDITORIAL", 2.8, "launch_info")
        if "launch" in goal or "lansman" in instr:
            add("BRAND_STATEMENT", 1.0, "launch_goal")
    elif intent == "EDUCATIONAL":
        add("INFORMATIONAL_EDITORIAL", 5.0, "explain")
        if has_eligible_metrics:
            add("INVESTMENT_DATA", 2.2, "eligible_figures_as_evidence")
        add("LOCATION_STORY", 1.0, "place_as_context")
    else:
        add("BRAND_STATEMENT", 1.0, "fallback")

    # Variety: penalize repeating the exact direction used on a sibling NEW post.
    scored: dict[CreativeDirectionKind, float] = {}
    for kind, score in candidates:
        scored[kind] = scored.get(kind, 0.0) + score
        if kind in used:
            scored[kind] -= 2.4
            decisions.append(f"variety_penalty:{kind}")
    ranked = sorted(scored.items(), key=lambda kv: kv[1], reverse=True)
    chosen = ranked[0][0]
    return chosen, decisions


def choose_composition_primitive(
    *,
    direction: CreativeDirectionKind,
    intent: CreativeIntentKind,
    profile: Any = None,
    format_preset: str = "square",
    copy_density: CopyDensityKind = "LOW",
    has_metrics: bool = False,
    used_signals: list[str] | None = None,
    instruction: str = "",
) -> tuple[CompositionPrimitive, list[str]]:
    used = {str(s).upper() for s in (used_signals or [])}
    zone = _asset_zone(profile)
    subject = _asset_subject(profile)
    busy = _asset_busy(profile)
    empty = _asset_empty(profile)
    vertical = format_preset in {"story", "reelsCover", "portrait"}
    landscape = format_preset == "landscape"
    notes: list[str] = []
    options: list[CompositionPrimitive] = []

    if direction == "INVESTMENT_DATA" and has_metrics:
        options = ["DATA_GRID", "LOWER_THIRD", "SPLIT_INFORMATION"]
        if subject in {"building", "architecture", "skyline"}:
            options = ["LOWER_THIRD", "DATA_GRID", "SPLIT_INFORMATION"]
            notes.append("building_hero_metrics_in_lower_third")
        if vertical:
            options = ["LOWER_THIRD", "SPLIT_INFORMATION", "DATA_GRID"]
    elif direction == "ARCHITECTURAL_FEATURE":
        options = ["IMAGE_DOMINANT", "BOTTOM_LEFT_EDITORIAL", "FLOATING_INFORMATION_GROUP"]
        if subject in {"building", "architecture"}:
            options = ["BOTTOM_LEFT_EDITORIAL", "IMAGE_DOMINANT", "FLOATING_INFORMATION_GROUP"]
            notes.append("keep_type_off_building_focal")
        if zone == "bottom":
            options = ["BOTTOM_LEFT_EDITORIAL", "LOWER_THIRD", "IMAGE_DOMINANT"]
        if busy:
            notes.append("busy_asset_keep_type_off_focal")
            options = ["IMAGE_DOMINANT", "FLOATING_INFORMATION_GROUP", "BOTTOM_LEFT_EDITORIAL"]
    elif direction == "LIFESTYLE_PREMIUM":
        options = ["IMAGE_DOMINANT", "LOWER_THIRD", "FLOATING_INFORMATION_GROUP"]
        if subject == "people":
            options = ["LOWER_THIRD", "IMAGE_DOMINANT", "FLOATING_INFORMATION_GROUP"]
    elif direction == "BRAND_STATEMENT":
        options = ["CENTER_STATEMENT", "TOP_LEFT_EDITORIAL", "IMAGE_DOMINANT"]
        if vertical:
            options = ["CENTER_STATEMENT", "SIDE_COLUMN", "IMAGE_DOMINANT"]
    elif direction == "INFORMATIONAL_EDITORIAL":
        options = ["SIDE_COLUMN", "ASYMMETRIC_EDITORIAL", "SPLIT_INFORMATION"]
        if landscape:
            options = ["SPLIT_INFORMATION", "SIDE_COLUMN", "ASYMMETRIC_EDITORIAL"]
        if vertical:
            options = ["SIDE_COLUMN", "SPLIT_INFORMATION", "LOWER_THIRD"]
    elif direction == "LOCATION_STORY":
        if zone == "bottom":
            options = ["BOTTOM_LEFT_EDITORIAL", "LOWER_THIRD", "FLOATING_INFORMATION_GROUP"]
        elif empty:
            options = ["FLOATING_INFORMATION_GROUP", "TOP_LEFT_EDITORIAL", "IMAGE_DOMINANT"]
        elif busy:
            options = ["TOP_LEFT_EDITORIAL", "SIDE_COLUMN", "IMAGE_DOMINANT"]
        else:
            options = ["TOP_LEFT_EDITORIAL", "ASYMMETRIC_EDITORIAL", "FLOATING_INFORMATION_GROUP"]
        if vertical:
            options = ["SIDE_COLUMN", "TOP_LEFT_EDITORIAL", "IMAGE_DOMINANT"]
    else:  # EDITORIAL_LUXURY
        options = ["TOP_LEFT_EDITORIAL", "ASYMMETRIC_EDITORIAL", "SIDE_COLUMN", "CENTER_STATEMENT"]
        if vertical:
            options = ["SIDE_COLUMN", "TOP_LEFT_EDITORIAL", "IMAGE_DOMINANT"]
        if copy_density == "MINIMAL":
            options = ["IMAGE_DOMINANT", "CENTER_STATEMENT", "TOP_LEFT_EDITORIAL"]
        if subject in {"building", "architecture"} and not busy:
            options = ["TOP_LEFT_EDITORIAL", "IMAGE_DOMINANT", "ASYMMETRIC_EDITORIAL"]

    # Don't park type on the likely architectural focal band.
    if subject in {"building", "architecture"} and zone == "top":
        options = [o for o in options if o != "CENTER_STATEMENT"] + (
            ["CENTER_STATEMENT"] if "CENTER_STATEMENT" in options else []
        )
        notes.append("avoid_center_on_building_focal")

    unused = [option for option in options if option not in used]
    pool = unused if unused else (options[1:] if len(options) > 1 else options)
    if not pool:
        picked = "TOP_LEFT_EDITORIAL"
        notes.append("variety_exhausted_reuse")
    elif len(pool) == 1:
        picked = pool[0]
        notes.append(f"composition:{picked}")
    else:
        digest = hashlib.sha1((instruction or "").encode("utf-8")).hexdigest()
        idx = int(digest[:8], 16)
        instr = (instruction or "").lower()
        if any(k in instr for k in ("ikinci", "second ", "another ", "bir diğer", "bir diger")):
            idx += 1
            notes.append("variety_followup_request")
        idx = (idx + sum(1 for s in used if s in options or s == direction)) % len(pool)
        picked = pool[idx]
        notes.append(f"composition:{picked}:request_variety")
    return picked, notes


def choose_copy_density(
    *,
    intent: CreativeIntentKind,
    direction: CreativeDirectionKind,
    has_metrics: bool,
    format_preset: str = "square",
) -> CopyDensityKind:
    if direction == "ARCHITECTURAL_FEATURE" or intent == "ARCHITECTURE":
        return "MINIMAL"
    if direction == "INVESTMENT_DATA" and has_metrics:
        return "DATA_RICH"
    if intent in {"LIFESTYLE", "BRAND"} or direction in {"LIFESTYLE_PREMIUM", "BRAND_STATEMENT", "EDITORIAL_LUXURY"}:
        return "LOW"
    if intent == "EDUCATIONAL" or direction == "INFORMATIONAL_EDITORIAL":
        return "MEDIUM"
    if intent == "LOCATION":
        return "MEDIUM" if direction == "LOCATION_STORY" else "LOW"
    if intent == "ANNOUNCEMENT":
        return "LOW"
    if format_preset in {"story", "reelsCover"}:
        return "LOW"
    return "LOW"


def choose_contrast(
    *,
    profile: Any,
    composition: CompositionPrimitive,
    density: CopyDensityKind,
) -> tuple[ContrastStrategyKind, str]:
    brightness = _asset_brightness(profile)
    busy = _asset_busy(profile)
    empty = _asset_empty(profile)
    zone = _asset_zone(profile)
    if composition in {"DATA_GRID", "LOWER_THIRD"}:
        return ("DARK_GRADIENT" if brightness == "light" else "SOFT_OVERLAY"), "bottom"
    if composition == "SPLIT_INFORMATION":
        return "SOFT_OVERLAY", "left"
    if density == "MINIMAL" and empty and brightness in {"dark", "mixed"}:
        return "NONE", zone
    if busy:
        return "LOCAL_TEXT_BACKDROP", zone if zone in {"top", "bottom", "left", "right"} else "top"
    if composition in {"CENTER_STATEMENT", "IMAGE_DOMINANT"}:
        if brightness == "light":
            return "DARK_GRADIENT", zone
        if brightness == "dark":
            return "LIGHT_GRADIENT", zone
        return "SUBTLE_GRADIENT", zone
    if brightness == "dark":
        return "LIGHT_GRADIENT", zone
    if brightness == "light":
        return "DARK_GRADIENT", zone
    if composition in {"SIDE_COLUMN", "TOP_LEFT_EDITORIAL", "ASYMMETRIC_EDITORIAL"}:
        return "SUBTLE_GRADIENT", "left" if composition == "SIDE_COLUMN" else "top"
    return "SUBTLE_GRADIENT", zone


def choose_cta_strategy(
    *,
    intent: CreativeIntentKind,
    direction: CreativeDirectionKind,
    density: CopyDensityKind,
    instruction: str = "",
) -> CtaStrategyKind:
    asked = (instruction or "").lower()
    explicit = any(
        k in asked
        for k in ("cta", "buton", "button", "explore", "keşfet", "kesfet", "randevu", "tour", "schedule")
    )
    if density == "MINIMAL" and intent == "ARCHITECTURE" and not explicit:
        return "NONE"
    if intent == "INVESTMENT" or direction == "INVESTMENT_DATA":
        return "PILL_BUTTON"
    if direction == "BRAND_STATEMENT" and not explicit:
        return "NONE"
    if intent == "ANNOUNCEMENT":
        return "PILL_BUTTON" if explicit else "MINIMAL_BUTTON"
    if intent == "LIFESTYLE" or direction == "LIFESTYLE_PREMIUM":
        return "MINIMAL_BUTTON"
    if intent in {"LOCATION", "EDUCATIONAL"} or direction in {"LOCATION_STORY", "EDITORIAL_LUXURY", "INFORMATIONAL_EDITORIAL"}:
        return "TEXT_LINK_STYLE"
    if explicit:
        return "PILL_BUTTON"
    return "TEXT_LINK_STYLE"


def overlay_token(contrast: ContrastStrategyKind, region: str) -> str:
    base = CONTRAST_TO_OVERLAY.get(contrast, "localized")
    zone = region if region in {"top", "bottom", "left", "right"} else "top"
    if base == "none":
        return "none"
    if base == "localized":
        return f"localized-{zone}"
    return f"{base}-{zone}"


def build_creative_plan(
    *,
    intent: CreativeIntentKind,
    audience: str,
    objective: str,
    profile: Any = None,
    has_eligible_metrics: bool = False,
    copy_length: int = 0,
    format_preset: str = "square",
    campaign_goal: str | None = None,
    tone: str = "premium",
    used_signals: list[str] | None = None,
    instruction: str = "",
    project_name: str = "",
) -> CreativePlan:
    used = list(used_signals or [])
    direction, dir_notes = choose_creative_direction(
        intent=intent,
        profile=profile,
        has_eligible_metrics=has_eligible_metrics,
        copy_length=copy_length,
        format_preset=format_preset,
        campaign_goal=campaign_goal,
        tone=tone,
        used_signals=used,
        instruction=instruction,
    )
    metrics_ok = bool(has_eligible_metrics and direction == "INVESTMENT_DATA")
    density = choose_copy_density(
        intent=intent,
        direction=direction,
        has_metrics=metrics_ok,
        format_preset=format_preset,
    )
    composition, comp_notes = choose_composition_primitive(
        direction=direction,
        intent=intent,
        profile=profile,
        format_preset=format_preset,
        copy_density=density,
        has_metrics=metrics_ok,
        used_signals=used,
        instruction=instruction,
    )
    contrast, region = choose_contrast(profile=profile, composition=composition, density=density)
    # Keep type off the architectural focal point: prefer top/left/bottom safe zones.
    subject = _asset_subject(profile)
    if subject in {"building", "architecture"} and region not in {"top", "bottom", "left"}:
        region = _asset_zone(profile) if _asset_zone(profile) in {"top", "bottom", "left"} else "top"
    cta = choose_cta_strategy(
        intent=intent, direction=direction, density=density, instruction=instruction
    )
    spec = DIRECTION_LIBRARY[direction]
    family: FamilyKind = PRIMITIVE_TO_FAMILY.get(composition, spec["family"])
    if intent == "LOCATION" or direction == "LOCATION_STORY":
        family = "LOCATION"
    elif direction == "INVESTMENT_DATA":
        family = "INVESTMENT"
    elif direction == "ARCHITECTURAL_FEATURE" or intent == "ARCHITECTURE":
        family = "MINIMAL_HERO"

    include_metrics = metrics_ok
    include_support = density in {"MEDIUM", "DATA_RICH"} or (
        density == "LOW" and direction in {"LOCATION_STORY", "INFORMATIONAL_EDITORIAL", "EDITORIAL_LUXURY"}
    )
    if density == "MINIMAL":
        include_support = False
    if include_metrics:
        include_support = False
    include_cta = cta != "NONE"
    include_eyebrow = density in {"MEDIUM", "DATA_RICH"} or direction in {
        "EDITORIAL_LUXURY",
        "INVESTMENT_DATA",
        "BRAND_STATEMENT",
        "LOCATION_STORY",
    }
    if density == "MINIMAL":
        include_eyebrow = False
    brand: BrandTreatmentKind = "NONE"
    if project_name and direction in {"BRAND_STATEMENT", "INVESTMENT_DATA", "EDITORIAL_LUXURY", "LOCATION_STORY"}:
        brand = "IDENTITY_LINE"
        include_eyebrow = True if direction != "ARCHITECTURAL_FEATURE" else include_eyebrow
    elif project_name and density != "MINIMAL":
        brand = "CORNER_MARK"

    align = "center" if composition == "CENTER_STATEMENT" else "left"
    if composition == "SPLIT_INFORMATION":
        align = "left"
    zone = region
    if composition in {"BOTTOM_LEFT_EDITORIAL", "LOWER_THIRD"}:
        zone = "bottom"
    elif composition in {"SIDE_COLUMN", "ASYMMETRIC_EDITORIAL"}:
        zone = "left" if composition == "SIDE_COLUMN" else "top"
    elif composition == "IMAGE_DOMINANT":
        zone = _asset_zone(profile) if _asset_zone(profile) in {"top", "bottom"} else "top"

    width_ratio = 0.58 if composition in {"SIDE_COLUMN", "ASYMMETRIC_EDITORIAL"} else 0.72
    if composition == "CENTER_STATEMENT":
        width_ratio = 0.78
        align = "center"
    if composition == "IMAGE_DOMINANT":
        width_ratio = 0.70
    if composition == "DATA_GRID":
        width_ratio = 0.86

    visual: VisualPriorityKind = spec["visual_priority"]
    if intent == "LOCATION":
        visual = "place"
    elif intent == "ARCHITECTURE":
        visual = "building"
    elif intent == "INVESTMENT":
        visual = "figures" if include_metrics else "identity"
    elif intent == "LIFESTYLE":
        visual = "atmosphere"
    elif intent == "BRAND":
        visual = "identity"
    elif intent == "ANNOUNCEMENT":
        visual = "announcement"

    image_strategy = {
        "building": "Keep the facade readable. Type lives in negative space, never on the focal mass.",
        "place": "Exterior or skyline carries belonging. Do not cover the building with a type stack.",
        "figures": "Lower content band for eligible metrics; architecture stays visible above.",
        "atmosphere": "Image-led living. Sparse type. Do not invent amenities.",
        "identity": "Photography supports the name. One primary line.",
        "announcement": "Arrival statement. Photography as stage, not a data wall.",
        "explanation": "Editorial column; image remains a field, not a collage.",
    }.get(visual, "Photography is the hero.")

    avoided = [s for s in used if s]
    decisions = dir_notes + comp_notes + [
        f"density:{density}",
        f"contrast:{contrast}",
        f"cta:{cta}",
        f"metrics:{'structured' if include_metrics else 'none'}",
        f"brand:{brand}",
    ]

    return CreativePlan(
        intent=intent,
        audience=audience,
        objective=objective,
        creative_direction=direction,
        visual_priority=visual,
        hierarchy=HierarchyPlan(),
        copy_density=density,
        composition=composition,
        text_regions=TextRegionPlan(zone=zone, align=align, width_ratio=width_ratio, avoid_focal=True),
        image_strategy=image_strategy,
        contrast_strategy=contrast,
        overlay_strategy=overlay_token(contrast, zone),
        overlay_region=zone,
        metric_strategy="STRUCTURED_GROUP" if include_metrics else "NONE",
        cta_strategy=cta,
        brand_treatment=brand,
        family=family,
        include_eyebrow=include_eyebrow and brand != "NONE",
        include_support=include_support,
        include_cta=include_cta,
        include_metrics=include_metrics,
        include_brand=brand != "NONE",
        alignment=align,
        safe_text_zone=zone if zone in {"top", "bottom", "left", "right"} else "top",
        concept=str(spec["concept"]),
        decisions=decisions,
        variety_avoided=avoided,
    )


def creative_plan_to_dict(plan: CreativePlan) -> dict[str, Any]:
    payload = asdict(plan)
    return payload


def creative_plan_from_dict(raw: Any) -> CreativePlan | None:
    if not isinstance(raw, dict) or not raw.get("creative_direction"):
        return None
    hierarchy_raw = raw.get("hierarchy") if isinstance(raw.get("hierarchy"), dict) else {}
    regions_raw = raw.get("text_regions") if isinstance(raw.get("text_regions"), dict) else {}
    try:
        return CreativePlan(
            intent=raw.get("intent") or "BRAND",
            audience=str(raw.get("audience") or "general"),
            objective=str(raw.get("objective") or "general"),
            creative_direction=raw["creative_direction"],
            visual_priority=raw.get("visual_priority") or "identity",
            hierarchy=HierarchyPlan(
                primary=str(hierarchy_raw.get("primary") or "headline"),
                secondary=str(hierarchy_raw.get("secondary") or "body"),
                tertiary=str(hierarchy_raw.get("tertiary") or "eyebrow"),
                cta=str(hierarchy_raw.get("cta") or "cta"),
                brand=str(hierarchy_raw.get("brand") or "eyebrow"),
            ),
            copy_density=raw.get("copy_density") or "LOW",
            composition=raw.get("composition") or "TOP_LEFT_EDITORIAL",
            text_regions=TextRegionPlan(
                zone=str(regions_raw.get("zone") or "top"),
                align=str(regions_raw.get("align") or "left"),
                width_ratio=float(regions_raw.get("width_ratio") or 0.72),
                avoid_focal=bool(regions_raw.get("avoid_focal", True)),
            ),
            image_strategy=str(raw.get("image_strategy") or ""),
            contrast_strategy=raw.get("contrast_strategy") or "SUBTLE_GRADIENT",
            overlay_strategy=str(raw.get("overlay_strategy") or "subtle-top"),
            overlay_region=str(raw.get("overlay_region") or "top"),
            metric_strategy=raw.get("metric_strategy") or "NONE",
            cta_strategy=raw.get("cta_strategy") or "TEXT_LINK_STYLE",
            brand_treatment=raw.get("brand_treatment") or "IDENTITY_LINE",
            family=raw.get("family") or "LOCATION",
            include_eyebrow=bool(raw.get("include_eyebrow")),
            include_support=bool(raw.get("include_support")),
            include_cta=bool(raw.get("include_cta")),
            include_metrics=bool(raw.get("include_metrics")),
            include_brand=bool(raw.get("include_brand", True)),
            alignment=str(raw.get("alignment") or "left"),
            safe_text_zone=str(raw.get("safe_text_zone") or "top"),
            concept=str(raw.get("concept") or ""),
            decisions=list(raw.get("decisions") or []),
            variety_avoided=list(raw.get("variety_avoided") or []),
        )
    except (TypeError, ValueError, KeyError):
        return None


def compact_debug(plan: CreativePlan, quality: dict[str, Any] | None = None) -> dict[str, Any]:
    """Dev/debug observability — not for production chrome."""
    return {
        "intent": plan.intent,
        "direction": plan.creative_direction,
        "composition": plan.composition,
        "density": plan.copy_density,
        "contrast": plan.contrast_strategy,
        "cta": plan.cta_strategy,
        "quality": None if not quality else quality.get("total"),
    }
