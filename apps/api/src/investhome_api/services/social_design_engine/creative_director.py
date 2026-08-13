"""Creative Director — editorial decisions between retrieval and composition.

Deterministic, structured planning data only (never chain-of-thought).
Marketing objective controls which facts may appear on the canvas.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from investhome_api.schemas.creative_studio_generation import CreativeStudioGenerationContext
from investhome_api.schemas.social_design_engine import SocialDesignMediaCandidate
from investhome_api.services.social_design_engine.ops import looks_like_rag_or_debug_copy
from investhome_api.services.social_design_engine.marketing_strategist import (
    MarketingStrategy,
    looks_like_street_address,
)
from investhome_api.services.social_design_engine.creative_intent import (
    CreativeIntentKind,
    classify_creative_intent,
)
from investhome_api.services.social_design_engine.creative_plan import (
    CreativePlan,
    build_creative_plan,
    combined_variety_signals,
    creative_plan_to_dict,
    remember_project_variety,
)

if TYPE_CHECKING:
    from investhome_api.services.social_design_engine.generation import (
        CampaignFact,
        GenerationIntent,
        MarketingObjective,
    )

CompositionFamily = Literal["MINIMAL_HERO", "EDITORIAL", "INVESTMENT", "LOCATION"]
TextDensity = Literal["sparse", "moderate", "dense"]
ContrastMode = Literal[
    "localized_gradient",
    "controlled_overlay",
    "alternate_region",
    "text_color",
]
AlignAxis = Literal["left", "center", "right"]
SafeZone = Literal["top", "bottom", "left", "right"]
AssetSubject = Literal["building", "skyline", "architecture", "people", "detail", "unknown"]

GENERIC_HEADLINE_PHRASES = frozenset(
    {
        "premium living",
        "unique opportunity",
        "discover more",
        "explore more today",
        "luxury living",
        "live premium",
        "exclusive living",
        "redefined living",
    }
)
GENERIC_CTA_PHRASES = frozenset(
    {
        "explore more today",
        "discover more",
        "learn more",
        "click here",
        "explore more",
        "find out more",
        "see more",
    }
)

LOCATION_ALLOW_KEYS = frozenset({"city", "country", "project_name"})
LOCATION_ALLOW_TERMS = (
    "location",
    "neighborhood",
    "neighbourhood",
    "address",
    "washington",
    "columbia",
    "heights",
    "metro",
    "transit",
    "walk",
    "connectivity",
    "avenue",
    "park",
    "central",
    "district",
    "corridor",
    "lifestyle",
    "d.c",
    "dc ",
)
LOCATION_DENY_TERMS = (
    "under construction",
    "construction schedule",
    "mixed-use",
    "mixed use",
    "total_units",
    "total units",
    "unit count",
    "financing",
    "mortgage",
    "project_status",
    "project_type",
    "floor plan",
    "floorplan",
    "sqm",
    "sq ft",
    "completion date",
    "delivery date",
    "technical",
    "parking spaces",
    "residential construction",
    "construction status",
    "units=",
)

INVESTMENT_ALLOW_TERMS = (
    "investment",
    "investor",
    "roi",
    "yield",
    "return",
    "getiri",
    "yatırım",
    "yatirim",
    "minimum",
    "target",
)
INVESTMENT_DENY_TERMS = (
    "under construction",
    "construction schedule",
    "mixed-use",
    "mixed use",
    "total_units",
    "floor plan",
    "amenities spa",
    "project_status",
    "project_type",
)

LIFESTYLE_ALLOW_TERMS = (
    "lifestyle",
    "amenity",
    "amenities",
    "spa",
    "pool",
    "architecture",
    "design",
    "experience",
    "residences",
    "lobby",
    "rooftop",
    "interior",
)
LIFESTYLE_DENY_TERMS = (
    "under construction",
    "total_units",
    "financing",
    "mixed-use",
    "mixed use",
    "project_status",
    "roi",
    "mortgage",
)

LAUNCH_ALLOW_TERMS = (
    "launch",
    "lansman",
    "opening",
    "identity",
    "signature",
    "architecture",
    "residences",
)
LAUNCH_DENY_TERMS = (
    "under construction",
    "total_units",
    "financing",
    "mixed-use",
    "floor plan",
    "project_status",
)

ARCHITECTURE_ALLOW_TERMS = (
    "architecture",
    "architectural",
    "facade",
    "façade",
    "material",
    "craft",
    "character",
    "design language",
    "form",
    "presence",
)
ARCHITECTURE_DENY_TERMS = (
    "under construction",
    "total_units",
    "financing",
    "mixed-use",
    "roi",
    "mortgage",
    "address",
    "project_status",
)


@dataclass
class FactCandidate:
    text: str
    source: str  # verified_fact | retrieved | identity | campaign
    key: str | None = None
    provenance: str = ""


@dataclass
class SelectedFact:
    text: str
    source: str
    reason: str
    provenance: str = ""


@dataclass
class SuppressedFact:
    text: str
    source: str
    reason: str
    provenance: str = ""


@dataclass
class AssetVisualProfile:
    subject: AssetSubject = "unknown"
    negative_space: SafeZone = "top"
    brightness: str = "mixed"
    contrast: str = "medium"
    safe_text_zone: SafeZone = "top"
    image_led: bool = True
    tags: list[str] = field(default_factory=list)
    filename: str = ""
    busy: bool = False
    empty_negative_space: bool = False
    focal: str = "unknown"


@dataclass
class CreativeConcept:
    objective: MarketingObjective
    concept: str
    visual_strategy: str
    primary_message: str
    supporting_message: str
    cta: str
    information_to_exclude: list[str]
    composition_strategy: CompositionFamily
    tone: str
    text_density: TextDensity
    eyebrow: str = ""
    include_eyebrow: bool = False
    include_support: bool = True
    include_cta: bool = True
    alignment: AlignAxis = "left"
    contrast_strategy: str = "localized_gradient"
    overlay_region: str = "top"
    safe_text_zone: str = "top"
    selected_facts: list[SelectedFact] = field(default_factory=list)
    suppressed_facts: list[SuppressedFact] = field(default_factory=list)
    asset_profile: dict[str, Any] = field(default_factory=dict)
    metric_group_layout: str = "horizontal"
    structured_metrics: list[dict[str, Any]] = field(default_factory=list)
    project_identity_line: str = ""
    creative_intent: CreativeIntentKind = "BRAND"
    creative_direction: str = "BRAND_STATEMENT"
    composition_primitive: str = "TOP_LEFT_EDITORIAL"
    copy_density_kind: str = "LOW"
    cta_strategy: str = "PILL_BUTTON"
    contrast_kind: str = "SUBTLE_GRADIENT"
    brand_treatment: str = "IDENTITY_LINE"
    visual_priority: str = "identity"
    creative_plan: dict[str, Any] = field(default_factory=dict)
    composition_blueprint: dict[str, Any] = field(default_factory=dict)
    composition_family: str = ""


def _norm(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text or "")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return folded.strip().lower()


def _word_count(text: str) -> int:
    return len([w for w in re.split(r"\s+", (text or "").strip()) if w])


def clip_headline(text: str, *, max_words: int = 8, min_words: int = 2) -> str:
    words = [w for w in re.split(r"\s+", (text or "").strip()) if w]
    if len(words) > max_words:
        words = words[:max_words]
    clipped = " ".join(words).strip(" ,.—–-")
    return clipped


def is_generic_headline(text: str) -> bool:
    t = _norm(text)
    if t in GENERIC_HEADLINE_PHRASES:
        return True
    if t.startswith("discover ") or t.startswith("explore "):
        return True
    return False


def is_generic_cta(text: str) -> bool:
    return _norm(text) in GENERIC_CTA_PHRASES


def infer_asset_visual_profile(
    candidate: SocialDesignMediaCandidate | None,
) -> AssetVisualProfile:
    if candidate is None:
        return AssetVisualProfile(image_led=False)
    hay = " ".join(
        [
            candidate.filename or "",
            " ".join(candidate.tags or []),
            candidate.folder_category or "",
        ]
    ).lower()
    tags = [str(t).lower() for t in (candidate.tags or [])]
    subject: AssetSubject = "unknown"
    if any(k in hay for k in ("aerial", "drone", "skyline", "cityscape")):
        subject = "skyline"
    elif any(k in hay for k in ("people", "lifestyle", "resident", "portrait")):
        subject = "people"
    elif any(k in hay for k in ("detail", "material", "close", "texture")):
        subject = "detail"
    elif any(k in hay for k in ("interior", "lobby", "living", "kitchen")):
        subject = "architecture"
    elif any(k in hay for k in ("exterior", "facade", "façade", "building", "render", "hero")):
        subject = "building"

    brightness = "dark" if any(k in hay for k in ("twilight", "night", "dusk", "evening")) else "mixed"
    if any(k in hay for k in ("day", "bright", "sunny")):
        brightness = "light"

    if subject in {"building", "skyline", "architecture"}:
        negative: SafeZone = "top"
        safe: SafeZone = "top"
    elif subject == "people":
        negative = "bottom"
        safe = "bottom"
    else:
        negative = "top"
        safe = "top"

    busy = any(k in hay for k in ("busy", "crowd", "clutter", "detail", "interior", "kitchen", "lobby", "street"))
    empty = any(k in hay for k in ("sky", "aerial", "drone", "skyline", "open", "void", "cloud"))
    focal = "building" if subject in {"building", "architecture"} else subject
    if empty and subject in {"skyline", "unknown"}:
        safe = "top"
        negative = "top"
    elif busy and subject in {"building", "architecture"}:
        safe = "top"
        negative = "top"

    return AssetVisualProfile(
        subject=subject,
        negative_space=negative,
        brightness=brightness,
        contrast="high" if brightness == "dark" else "medium",
        safe_text_zone=safe,
        image_led=True,
        tags=tags,
        filename=candidate.filename or "",
        busy=busy,
        empty_negative_space=empty,
        focal=focal,
    )


def _parse_identity_facts(raw: list[str]) -> list[FactCandidate]:
    out: list[FactCandidate] = []
    for item in raw:
        text = (item or "").strip()
        if not text:
            continue
        key = None
        display = text
        if "=" in text and re.match(
            r"^(project_name|project_code|city|country|address|total_units|project_type|project_status)\s*=",
            text,
            re.I,
        ):
            key, _, val = text.partition("=")
            key = key.strip().lower()
            val = val.strip()
            if not val:
                continue
            display = val
        elif looks_like_rag_or_debug_copy(text):
            continue
        if looks_like_rag_or_debug_copy(display) and key is None:
            continue
        out.append(
            FactCandidate(
                text=display,
                source="verified_fact",
                key=key,
                provenance=text,
            )
        )
    return out


def _parse_retrieved_facts(retrieved: list[Any]) -> list[FactCandidate]:
    out: list[FactCandidate] = []
    for row in retrieved:
        if not isinstance(row, dict):
            continue
        name = str(row.get("document_name") or "").lower()
        if "metadata.json" in name or name.endswith(".json"):
            continue
        text = str(row.get("text") or row.get("excerpt") or "").strip()
        if not text or looks_like_rag_or_debug_copy(text):
            continue
        sentence = text.split(".")[0].strip()
        if len(sentence) < 12:
            continue
        out.append(
            FactCandidate(
                text=sentence[:220],
                source="retrieved",
                provenance=name or "retrieved",
            )
        )
    return out


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    t = _norm(text)
    return any(term in t for term in terms)


def _objective_filters(
    objective: MarketingObjective,
) -> tuple[frozenset[str], tuple[str, ...], tuple[str, ...]]:
    if objective == "location":
        return LOCATION_ALLOW_KEYS, LOCATION_ALLOW_TERMS, LOCATION_DENY_TERMS
    if objective == "investment":
        return frozenset({"project_name", "city"}), INVESTMENT_ALLOW_TERMS, INVESTMENT_DENY_TERMS
    if objective == "lifestyle" or objective == "interior":
        return frozenset({"project_name"}), LIFESTYLE_ALLOW_TERMS, LIFESTYLE_DENY_TERMS
    if objective == "architecture":
        return frozenset({"project_name"}), ARCHITECTURE_ALLOW_TERMS, ARCHITECTURE_DENY_TERMS
    if objective in {"launch", "project_introduction", "general"}:
        return frozenset({"project_name", "city"}), LAUNCH_ALLOW_TERMS, LAUNCH_DENY_TERMS
    return frozenset({"project_name"}), tuple(), LOCATION_DENY_TERMS


def select_facts_for_objective(
    *,
    objective: MarketingObjective,
    context: CreativeStudioGenerationContext,
    campaign_facts: list[CampaignFact],
    instruction: str = "",
    allowed_financial_tokens: list[str] | None = None,
) -> tuple[list[SelectedFact], list[SuppressedFact]]:
    """Objective-first fact gate. More RAG does not mean more canvas text."""
    allow_keys, allow_terms, deny_terms = _objective_filters(objective)
    asked = _norm(instruction)
    user_asked_construction = any(
        k in asked for k in ("construction", "inşaat", "insaat", "status", "units", "unit count")
    )

    selected: list[SelectedFact] = []
    suppressed: list[SuppressedFact] = []
    seen: set[str] = set()

    def _take(fact: FactCandidate, reason: str) -> None:
        token = _norm(fact.text)
        if not token or token in seen:
            return
        seen.add(token)
        selected.append(
            SelectedFact(
                text=fact.text,
                source=fact.source,
                reason=reason,
                provenance=fact.provenance,
            )
        )

    def _drop(fact: FactCandidate, reason: str) -> None:
        suppressed.append(
            SuppressedFact(
                text=fact.text,
                source=fact.source,
                reason=reason,
                provenance=fact.provenance,
            )
        )

    identity = _parse_identity_facts(list(context.verified_facts or []))
    ident = context.project_identity
    have_keys = {f.key for f in identity if f.key}
    for key, val in (
        ("project_name", ident.project_name),
        ("city", ident.city),
        ("country", ident.country),
    ):
        if val and key not in have_keys:
            identity.append(
                FactCandidate(
                    text=val,
                    source="identity",
                    key=key,
                    provenance=f"{key}={val}",
                )
            )
    retrieved = _parse_retrieved_facts(list(context.retrieved_content or []))
    from investhome_api.services.social_design_engine.fact_governance import (
        text_contains_ineligible_financial,
        text_has_financial_claim,
    )

    allowed_fin = list(allowed_financial_tokens or [])
    if not allowed_fin:
        allowed_fin = [cf.display for cf in campaign_facts]

    for fact in identity:
        key = fact.key or ""
        blob = f"{key} {fact.text} {fact.provenance}"
        denied = _contains_any(blob, deny_terms) and not user_asked_construction
        if key in {"total_units", "project_status", "project_type", "project_code"}:
            if objective == "location" or (denied and objective != "investment"):
                _drop(fact, f"irrelevant_for_{objective}")
                continue
        if key == "address" or looks_like_street_address(fact.text):
            _drop(fact, "address_is_evidence_not_the_ad")
            continue
        if denied:
            _drop(fact, f"excluded_for_{objective}")
            continue
        if key in allow_keys:
            _take(fact, f"identity_{key}")
            continue
        if objective == "investment" and key in {"project_name", "city"}:
            _take(fact, "investment_identity")
            continue
        _drop(fact, f"not_needed_for_{objective}")

    for fact in retrieved:
        blob = fact.text
        if text_has_financial_claim(blob) and text_contains_ineligible_financial(
            blob, allowed_tokens=allowed_fin
        ):
            _drop(fact, "ineligible_financial_claim")
            continue
        if _contains_any(blob, deny_terms) and not user_asked_construction:
            _drop(fact, f"excluded_for_{objective}")
            continue
        if allow_terms and not _contains_any(blob, allow_terms):
            _drop(fact, f"off_objective_{objective}")
            continue
        if len(selected) >= 4:
            _drop(fact, "density_cap")
            continue
        _take(fact, "objective_relevant")

    for cf in campaign_facts:
        if objective == "investment" or cf.display.lower() in asked:
            _take(
                FactCandidate(text=cf.display, source="campaign", provenance="user_supplied"),
                "user_supplied_campaign",
            )
        else:
            _drop(
                FactCandidate(text=cf.display, source="campaign", provenance="user_supplied"),
                "campaign_not_for_objective",
            )

    return selected, suppressed


def choose_composition_strategy(
    *,
    objective: MarketingObjective,
    profile: AssetVisualProfile,
    campaign_facts: list[CampaignFact],
    campaign_angle: str | None = None,
) -> CompositionFamily:
    angle = (campaign_angle or "").strip().lower()
    if objective == "investment" or (campaign_facts and objective == "investment"):
        return "INVESTMENT"
    if objective == "location":
        if angle in {"city_lifestyle"} and profile.image_led:
            return "LOCATION"
        return "LOCATION"
    if objective == "architecture":
        return "MINIMAL_HERO" if profile.image_led else "EDITORIAL"
    if objective in {"lifestyle", "interior"} and profile.image_led:
        return "MINIMAL_HERO"
    if objective in {"launch", "project_introduction", "general", "floor_plan"}:
        return "EDITORIAL" if not profile.image_led else "MINIMAL_HERO"
    if profile.image_led and objective != "investment":
        return "MINIMAL_HERO"
    return "EDITORIAL"


def _street_from_address(address: str) -> str:
    """Short verified street line — never invent a neighborhood name."""
    text = (address or "").strip()
    if not text:
        return ""
    text = text.split(",")[0].strip()
    text = re.sub(r"^\d+[A-Za-z]?\s+", "", text)
    text = re.sub(r"\s+\b(NW|NE|SW|SE)\b\s*$", "", text, flags=re.I).strip(" ,")
    return text


def _address_fact(selected: list[SelectedFact]) -> str:
    for fact in selected:
        if fact.reason == "identity_address":
            return fact.text
    return ""


def _place_name(context: CreativeStudioGenerationContext, selected: list[SelectedFact]) -> str:
    """City or neighborhood — never a street line. Address is evidence, not the place name."""
    city = context.project_identity.city or ""
    for fact in selected:
        if fact.reason == "identity_city":
            return fact.text
    return city


def _objective_cta(intent: GenerationIntent, *, en: bool) -> str:
    obj = intent.marketing_objective
    if intent.cta_hint and not is_generic_cta(intent.cta_hint):
        return intent.cta_hint
    if obj == "investment":
        from investhome_api.services.social_design_engine.localization import choose_investment_cta

        return choose_investment_cta("en" if en else "tr")
    if obj == "location":
        return "Explore the Neighborhood" if en else "Mahalleyi keşfet"
    if obj == "architecture":
        return "View the architecture" if en else "Mimariyi incele"
    if obj in {"lifestyle", "interior"}:
        return "Tour the residences" if en else "Rezidansı gez"
    if obj == "launch":
        return "Join the launch" if en else "Lansmana katıl"
    return "Schedule a private tour" if en else "Özel tur planla"


def _objective_headline(
    *,
    intent: GenerationIntent,
    context: CreativeStudioGenerationContext,
    selected: list[SelectedFact],
    campaign_facts: list[CampaignFact],
) -> str:
    en = intent.language != "tr"
    name = context.project_identity.project_name or "Project"
    place = _place_name(context, selected)
    obj = intent.marketing_objective

    if obj == "location":
        city = context.project_identity.city or ""
        if city:
            return f"A Central {city} Address" if en else f"{city} merkezinde"
        if place and place.lower() not in name.lower() and not looks_like_street_address(place):
            return f"A Central {place} Address" if en else f"{place} merkezinde"
        return f"{name} in the City" if en else f"{name} şehir merkezinde"
    if obj == "architecture":
        return f"The Character of {name}" if en else f"{name} karakteri"
    if obj == "investment":
        if campaign_facts:
            return f"Invest in {name}" if en else f"{name} yatırımı"
        return f"Invest in {name}" if en else f"{name} yatırımı"
    if obj in {"lifestyle", "interior"}:
        return f"Life at {name}" if en else f"{name} yaşamı"
    if obj == "launch":
        return f"{name} Arrives" if en else f"{name} lansmanı"
    return name


def _objective_support(
    *,
    intent: GenerationIntent,
    context: CreativeStudioGenerationContext,
    selected: list[SelectedFact],
    campaign_facts: list[CampaignFact],
) -> str:
    en = intent.language != "tr"
    obj = intent.marketing_objective
    prose = next(
        (f.text for f in selected if f.source == "retrieved" and len(f.text) >= 20),
        "",
    )
    if obj == "investment":
        return ""
    if obj == "location":
        if prose and not _contains_any(prose, LOCATION_DENY_TERMS) and not looks_like_street_address(prose):
            return prose[:110]
        city = context.project_identity.city or ""
        if city:
            return (
                f"A refined address in {city}."
                if en
                else f"{city} içinde sakin bir adres."
            )
        return ""
    if obj == "architecture":
        if prose and not looks_like_street_address(prose):
            return prose[:110]
        return ""
    if prose and not _contains_any(prose, LOCATION_DENY_TERMS):
        return prose[:110]
    return ""


def _objective_eyebrow(
    *,
    intent: GenerationIntent,
    context: CreativeStudioGenerationContext,
    family: CompositionFamily,
) -> str:
    if family != "EDITORIAL":
        return ""
    city = context.project_identity.city or ""
    name = context.project_identity.project_name or ""
    if intent.marketing_objective == "location" and city:
        return city
    return name


def _concept_line(objective: MarketingObjective, family: CompositionFamily, place: str, name: str) -> str:
    if objective == "location":
        return f"Place-led hero: {name} belongs to {place or 'the city'}, not a spec sheet."
    if objective == "investment":
        return f"Investment case for {name}: campaign figures lead, photography supports."
    if objective == "architecture":
        return f"Architecture-led hero for {name}: character over inventory."
    if objective in {"lifestyle", "interior"}:
        return f"Image-led lifestyle for {name}: experience over inventory."
    return f"Editorial identity for {name}."


def _visual_strategy(family: CompositionFamily, profile: AssetVisualProfile) -> str:
    zone = profile.safe_text_zone
    subject = profile.subject
    if family == "MINIMAL_HERO":
        return f"Photography is the hero. Keep type in the {zone} safe zone; do not cover the {subject}."
    if family == "LOCATION":
        return f"Exterior/neighborhood as hero. Type in {zone} negative space; building stays readable."
    if family == "INVESTMENT":
        return "Lower content band for figures; keep architecture visible above the type group."
    return "Left editorial column with generous photo field."


def _density_for(family: CompositionFamily, include_support: bool, include_eyebrow: bool) -> TextDensity:
    blocks = 1 + int(include_support) + int(include_eyebrow) + 1  # headline + cta
    if family == "MINIMAL_HERO" or blocks <= 2:
        return "sparse"
    if blocks <= 4:
        return "moderate"
    return "dense"


def _alignment_for(family: CompositionFamily) -> AlignAxis:
    if family in {"EDITORIAL", "INVESTMENT", "LOCATION", "MINIMAL_HERO"}:
        return "left"
    return "center"


def _contrast_for(family: CompositionFamily, profile: AssetVisualProfile) -> tuple[ContrastMode, SafeZone]:
    zone = profile.safe_text_zone
    if family == "INVESTMENT":
        return "localized_gradient", "bottom"
    if family == "EDITORIAL":
        return "localized_gradient", "left"
    if family in {"LOCATION", "MINIMAL_HERO"}:
        return "localized_gradient", zone
    return "controlled_overlay", zone


def direct_creative(
    *,
    instruction: str,
    intent: GenerationIntent,
    context: CreativeStudioGenerationContext,
    campaign_facts: list[CampaignFact],
    asset: SocialDesignMediaCandidate | None = None,
    strategy: MarketingStrategy | None = None,
    copy_package: Any | None = None,
    structured_metrics: list[Any] | None = None,
    campaign_intelligence: Any | None = None,
    campaign_intent_result: Any | None = None,
    sibling_posts: list[dict[str, Any]] | None = None,
) -> CreativeConcept:
    """Produce structured creative decisions. No chain-of-thought.

    When marketing_strategy + final copy are supplied, composition follows the
    campaign angle and copy is not rewritten from raw facts.
    """
    profile = infer_asset_visual_profile(asset)
    objective = strategy.objective if strategy is not None else intent.marketing_objective
    allowed_fin = [cf.display for cf in campaign_facts]
    blocked_fin: list[str] = []
    if campaign_intelligence is not None:
        for vf in list(getattr(campaign_intelligence, "marketing_safe_facts", []) or []):
            if getattr(vf, "is_financial", False) and getattr(vf, "display_value", None):
                token = str(vf.display_value)
                if token not in allowed_fin:
                    allowed_fin.append(token)
        qa = getattr(campaign_intelligence, "qa_trace", None) or {}
        blocked_fin = [str(t) for t in (qa.get("blocked_financial_tokens") or []) if t]
        for row in list(getattr(campaign_intelligence, "claim_eligibility_trace", []) or []):
            if isinstance(row, dict) and row.get("is_financial") and not row.get("eligible"):
                token = str(row.get("fact") or "")
                if token and token not in blocked_fin:
                    blocked_fin.append(token)
    selected, suppressed = select_facts_for_objective(
        objective=objective,  # type: ignore[arg-type]
        context=context,
        campaign_facts=campaign_facts,
        instruction=instruction,
        allowed_financial_tokens=allowed_fin,
    )
    if strategy is not None:
        # Never reintroduce strategist-suppressed raw facts onto the canvas.
        extra_drop = {_norm(t) for t in strategy.excluded_facts if t}
        kept: list[SelectedFact] = []
        for fact in selected:
            if _norm(fact.text) in extra_drop or looks_like_street_address(fact.text):
                suppressed.append(
                    SuppressedFact(
                        text=fact.text,
                        source=fact.source,
                        reason="strategy_excluded",
                        provenance=fact.provenance,
                    )
                )
            else:
                kept.append(fact)
        selected = kept
    creative_intent = classify_creative_intent(
        instruction,
        campaign=campaign_intent_result,
        project_name=context.project_identity.project_name,
    )
    eligible_metrics = bool(structured_metrics) or (
        bool(campaign_facts) and objective == "investment"
    )
    copy_len = 0
    if copy_package is not None:
        copy_len = len(
            str(getattr(copy_package, "headline", "") or "")
            + str(getattr(copy_package, "supporting_copy", "") or "")
        )
    plan_model: CreativePlan = build_creative_plan(
        intent=creative_intent.creative_intent,
        audience=creative_intent.audience or intent.audience or "general",
        objective=str(objective),
        profile=profile,
        has_eligible_metrics=eligible_metrics,
        copy_length=copy_len,
        format_preset=intent.format_preset or "square",
        campaign_goal=getattr(strategy, "campaign_angle", None) if strategy else None,
        tone=(strategy.tone if strategy is not None else None) or intent.tone or "premium",
        used_signals=combined_variety_signals(
            sibling_posts,
            getattr(context.project_identity, "project_id", None),
        ),
        instruction=instruction,
        project_name=context.project_identity.project_name or "",
    )
    remember_project_variety(
        getattr(context.project_identity, "project_id", None),
        plan_model.creative_direction,
        plan_model.composition,
        plan_model.family,
    )
    family = plan_model.family
    en = intent.language != "tr"
    name = context.project_identity.project_name or "Project"
    place = (strategy.neighborhood or strategy.city or _place_name(context, selected)) if strategy else _place_name(context, selected)

    include_eyebrow = plan_model.include_eyebrow
    include_support = plan_model.include_support
    include_cta = plan_model.include_cta

    if copy_package is not None:
        headline = clip_headline(getattr(copy_package, "headline", "") or "")
        support = str(getattr(copy_package, "supporting_copy", None) or getattr(copy_package, "supporting_text", "") or "")
        cta = str(getattr(copy_package, "cta", "") or "")
        eyebrow = str(getattr(copy_package, "eyebrow", "") or "")
        if not plan_model.include_support:
            support = ""
        if not plan_model.include_cta:
            cta = ""
        if not plan_model.include_eyebrow:
            eyebrow = ""
        include_eyebrow = bool(eyebrow) and plan_model.include_eyebrow
        include_support = bool(support) and plan_model.include_support
        include_cta = bool(cta) and plan_model.include_cta
    else:
        headline = clip_headline(_objective_headline(
            intent=intent,
            context=context,
            selected=selected,
            campaign_facts=campaign_facts,
        ))
        support = _objective_support(
            intent=intent,
            context=context,
            selected=selected,
            campaign_facts=campaign_facts,
        )
        if not include_support:
            support = ""
        cta = _objective_cta(intent, en=en) if include_cta else ""
        eyebrow = _objective_eyebrow(intent=intent, context=context, family=family) if include_eyebrow else ""
        if not include_support:
            support = ""

    from investhome_api.services.social_design_engine.fact_governance import (
        strip_ineligible_financial_claims,
        text_contains_ineligible_financial,
    )
    from investhome_api.services.social_design_engine.localization import (
        looks_like_concatenated_metrics,
        project_identity_lines,
    )
    from investhome_api.services.social_design_engine.metrics import (
        campaign_facts_to_structured_metrics,
        choose_metric_group_layout,
        structured_metrics_from_dicts,
        structured_metrics_to_dicts,
    )

    headline = strip_ineligible_financial_claims(
        headline, allowed_tokens=allowed_fin, blocked_tokens=blocked_fin
    )
    support = strip_ineligible_financial_claims(
        support, allowed_tokens=allowed_fin, blocked_tokens=blocked_fin
    )
    eyebrow = strip_ineligible_financial_claims(
        eyebrow, allowed_tokens=allowed_fin, blocked_tokens=blocked_fin
    )

    metrics_list = []
    if plan_model.include_metrics:
        if structured_metrics:
            if structured_metrics and hasattr(structured_metrics[0], "display_value"):
                metrics_list = list(structured_metrics)
            else:
                metrics_list = structured_metrics_from_dicts(list(structured_metrics))
        elif campaign_facts and objective == "investment":
            # Current-campaign user inputs only — never recover blocked facts from RAG.
            metrics_list = campaign_facts_to_structured_metrics(
                campaign_facts,
                language=intent.language,
                instruction=instruction,
            )
    # Never invent placeholders because a composition has a metric region.
    if looks_like_concatenated_metrics(support):
        support = ""
        include_support = False
    if metrics_list and objective == "investment":
        include_support = False
        support = ""
        ident, ident_place = project_identity_lines(
            project_name=name,
            city=context.project_identity.city or (strategy.city if strategy else "") or "",
            country=context.project_identity.country or "",
            locale=intent.language,
        )
        if ident and not eyebrow:
            eyebrow = ident if not ident_place else f"{ident}\n{ident_place}"
            include_eyebrow = True
        identity_line = ident
    else:
        identity_line = ""
    metric_layout = choose_metric_group_layout(
        metrics=metrics_list,
        format_preset=intent.format_preset,
        canvas_w=1080,
        available_width=840,
        requested="horizontal" if family == "INVESTMENT" and len(metrics_list) <= 3 else None,
    )

    # Hard gate: never let a street line become the primary message.
    if looks_like_street_address(headline):
        city = (strategy.city if strategy else None) or context.project_identity.city or ""
        headline = clip_headline(f"A Central {city} Address" if city else name)
    if looks_like_street_address(support):
        support = (strategy.neighborhood if strategy else "") or (strategy.city if strategy else "") or ""
        if not support:
            support = context.project_identity.city or ""
    for token in list(strategy.excluded_facts if strategy else []) + blocked_fin:
        piece = (token or "").strip()
        if piece and len(piece) >= 3:
            if piece in support:
                support = support.replace(piece, "").strip(" ,.;")
            if piece in headline and (
                looks_like_street_address(piece)
                or text_contains_ineligible_financial(piece, allowed_tokens=allowed_fin, blocked_tokens=blocked_fin)
            ):
                city = (strategy.city if strategy else None) or context.project_identity.city or ""
                headline = clip_headline(f"A Central {city} Address" if city else name)

    exclude = sorted(
        {
            s.reason.replace("excluded_for_", "").replace("irrelevant_for_", "")
            for s in suppressed
        }
        | {
            "construction status",
            "unit counts",
            "technical specifications",
            "financing terms",
            "full street address",
        }
        if objective == "location"
        else {s.reason for s in suppressed}
    )
    if objective == "location":
        exclude = [
            "construction status",
            "unit counts",
            "technical specifications",
            "financing terms",
            "mixed-use inventory",
            "project_status",
            "total_units",
            "full street address",
        ]
    if strategy is not None:
        for item in strategy.excluded_facts:
            if item and item not in exclude:
                exclude.append(item)
    for token in blocked_fin:
        if token and token not in exclude:
            exclude.append(token)

    contrast = plan_model.overlay_strategy
    overlay_region = plan_model.overlay_region  # type: ignore[assignment]
    alignment = plan_model.alignment  # type: ignore[assignment]
    density = plan_model.copy_density.lower() if plan_model.copy_density != "DATA_RICH" else "dense"
    if density == "minimal":
        density = "sparse"
    elif density == "low":
        density = "sparse"
    elif density == "medium":
        density = "moderate"

    from investhome_api.services.social_design_engine.composition_blueprint import (
        composition_blueprint_to_dict,
    )
    from investhome_api.services.social_design_engine.composition_engine import (
        build_composition_blueprint,
        sibling_blueprint_signals,
    )

    blueprint = build_composition_blueprint(
        plan=plan_model,
        profile=profile,
        format_preset=intent.format_preset or "square",
        used_signals=sibling_blueprint_signals(sibling_posts)
        + combined_variety_signals(
            sibling_posts,
            getattr(context.project_identity, "project_id", None),
        ),
        instruction=instruction,
        metric_count=len(metrics_list),
        include_support=bool(support) and include_support,
        include_metrics=bool(metrics_list) and plan_model.include_metrics,
        include_cta=bool(cta) and include_cta,
        include_brand=plan_model.include_brand,
        project_id=getattr(context.project_identity, "project_id", None),
    )
    blueprint_payload = composition_blueprint_to_dict(blueprint)
    if blueprint.overlay_token:
        contrast = blueprint.overlay_token
        overlay_region = blueprint.headline_region_kind.split("_")[0] if "_" in blueprint.headline_region_kind else overlay_region
    alignment = blueprint.alignment  # type: ignore[assignment]

    return CreativeConcept(
        objective=objective,  # type: ignore[arg-type]
        concept=plan_model.concept or _concept_line(objective, family, place, name),  # type: ignore[arg-type]
        visual_strategy=plan_model.image_strategy or _visual_strategy(family, profile),
        primary_message=headline,
        supporting_message=support,
        cta=cta,
        information_to_exclude=exclude,
        composition_strategy=family,
        tone=(strategy.tone if strategy is not None else None) or intent.tone or "premium",
        text_density=density,  # type: ignore[arg-type]
        eyebrow=eyebrow,
        include_eyebrow=bool(eyebrow) and include_eyebrow,
        include_support=bool(support) and include_support,
        include_cta=bool(cta) and include_cta,
        alignment=alignment,
        contrast_strategy=contrast,  # type: ignore[arg-type]
        overlay_region=overlay_region,
        safe_text_zone=plan_model.safe_text_zone,  # type: ignore[arg-type]
        selected_facts=selected,
        suppressed_facts=suppressed,
        asset_profile=asdict(profile),
        metric_group_layout=metric_layout,
        structured_metrics=structured_metrics_to_dicts(metrics_list),
        project_identity_line=identity_line,
        creative_intent=plan_model.intent,
        creative_direction=plan_model.creative_direction,
        composition_primitive=plan_model.composition,
        copy_density_kind=plan_model.copy_density,
        cta_strategy=plan_model.cta_strategy,
        contrast_kind=plan_model.contrast_strategy,
        brand_treatment=plan_model.brand_treatment,
        visual_priority=plan_model.visual_priority,
        creative_plan=creative_plan_to_dict(plan_model),
        composition_blueprint=blueprint_payload,
        composition_family=str(blueprint_payload.get("composition_family") or ""),
    )


def creative_concept_to_dict(concept: CreativeConcept) -> dict[str, Any]:
    return {
        "objective": concept.objective,
        "concept": concept.concept,
        "visual_strategy": concept.visual_strategy,
        "primary_message": concept.primary_message,
        "supporting_message": concept.supporting_message,
        "cta": concept.cta,
        "information_to_exclude": list(concept.information_to_exclude),
        "composition_strategy": concept.composition_strategy,
        "tone": concept.tone,
        "text_density": concept.text_density,
        "eyebrow": concept.eyebrow,
        "include_eyebrow": concept.include_eyebrow,
        "include_support": concept.include_support,
        "include_cta": concept.include_cta,
        "alignment": concept.alignment,
        "contrast_strategy": concept.contrast_strategy,
        "overlay_region": concept.overlay_region,
        "safe_text_zone": concept.safe_text_zone,
        "selected_facts": [asdict(f) for f in concept.selected_facts],
        "suppressed_facts": [asdict(f) for f in concept.suppressed_facts],
        "asset_profile": concept.asset_profile,
        "metric_group_layout": concept.metric_group_layout,
        "structured_metrics": list(concept.structured_metrics),
        "project_identity_line": concept.project_identity_line,
        "creative_intent": concept.creative_intent,
        "creative_direction": concept.creative_direction,
        "composition_primitive": concept.composition_primitive,
        "copy_density_kind": concept.copy_density_kind,
        "cta_strategy": concept.cta_strategy,
        "contrast_kind": concept.contrast_kind,
        "brand_treatment": concept.brand_treatment,
        "visual_priority": concept.visual_priority,
        "creative_plan": concept.creative_plan,
        "composition_blueprint": concept.composition_blueprint,
        "composition_family": concept.composition_family,
    }


def selected_fact_texts(concept: CreativeConcept) -> list[str]:
    return [f.text for f in concept.selected_facts if f.text]
