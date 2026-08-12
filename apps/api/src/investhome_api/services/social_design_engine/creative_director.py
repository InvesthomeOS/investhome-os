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

LOCATION_ALLOW_KEYS = frozenset({"city", "country", "address", "project_name"})
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
    "street",
    "park",
    "central",
    "heart of",
    "steps from",
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
    contrast_strategy: ContrastMode = "localized_gradient"
    overlay_region: SafeZone = "top"
    safe_text_zone: SafeZone = "top"
    selected_facts: list[SelectedFact] = field(default_factory=list)
    suppressed_facts: list[SuppressedFact] = field(default_factory=list)
    asset_profile: dict[str, Any] = field(default_factory=dict)


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

    return AssetVisualProfile(
        subject=subject,
        negative_space=negative,
        brightness=brightness,
        contrast="high" if brightness == "dark" else "medium",
        safe_text_zone=safe,
        image_led=True,
        tags=tags,
        filename=candidate.filename or "",
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
    if objective in {"launch", "general"}:
        return frozenset({"project_name", "city"}), LAUNCH_ALLOW_TERMS, LAUNCH_DENY_TERMS
    return frozenset({"project_name"}), tuple(), LOCATION_DENY_TERMS


def select_facts_for_objective(
    *,
    objective: MarketingObjective,
    context: CreativeStudioGenerationContext,
    campaign_facts: list[CampaignFact],
    instruction: str = "",
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

    for fact in identity:
        key = fact.key or ""
        blob = f"{key} {fact.text} {fact.provenance}"
        denied = _contains_any(blob, deny_terms) and not user_asked_construction
        if key in {"total_units", "project_status", "project_type", "project_code"}:
            if objective == "location" or (denied and objective != "investment"):
                _drop(fact, f"irrelevant_for_{objective}")
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
) -> CompositionFamily:
    if objective == "investment" or campaign_facts:
        if objective == "investment":
            return "INVESTMENT"
    if objective == "location":
        return "LOCATION"
    if objective in {"lifestyle", "interior"} and profile.image_led:
        return "MINIMAL_HERO"
    if objective in {"launch", "general", "floor_plan"}:
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
    city = context.project_identity.city or ""
    street = _street_from_address(_address_fact(selected))
    if street:
        return street
    for fact in selected:
        if fact.reason == "identity_city":
            return fact.text
    return city


def _objective_cta(intent: GenerationIntent, *, en: bool) -> str:
    obj = intent.marketing_objective
    if intent.cta_hint and not is_generic_cta(intent.cta_hint):
        return intent.cta_hint
    if obj == "investment":
        return "Explore the investment" if en else "Yatırım fırsatını incele"
    if obj == "location":
        return "Schedule a private tour" if en else "Özel tur planla"
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
        if place and city and place.lower() != city.lower():
            return f"On {place}" if en else f"{place} üzerinde"
        if city:
            return f"A Central {city} Address" if en else f"{city} merkezinde"
        if place and place.lower() not in name.lower():
            return f"A Central {place} Address" if en else f"{place} merkezinde"
        return f"{name} in the City" if en else f"{name} şehir merkezinde"
    if obj == "investment":
        if campaign_facts:
            money = next((f.display for f in campaign_facts if f.kind == "money"), None)
            if money:
                return f"From {money}" if en else f"{money} ile başlayın"
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
        numbers = " · ".join(f.display for f in campaign_facts)
        if numbers:
            return numbers
        return prose[:90] if prose else ""
    if obj == "location":
        if prose and not _contains_any(prose, LOCATION_DENY_TERMS):
            return prose[:110]
        addr = _address_fact(selected)
        city = context.project_identity.city or ""
        if addr:
            if city and city.lower() not in addr.lower():
                return f"{addr}, {city}."
            return addr if addr.endswith(".") else f"{addr}."
        if city:
            return (
                f"Connected living in {city}."
                if en
                else f"{city} ile kurulu bir yaşam."
            )
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
) -> CreativeConcept:
    """Produce structured creative decisions. No chain-of-thought."""
    profile = infer_asset_visual_profile(asset)
    selected, suppressed = select_facts_for_objective(
        objective=intent.marketing_objective,
        context=context,
        campaign_facts=campaign_facts,
        instruction=instruction,
    )
    family = choose_composition_strategy(
        objective=intent.marketing_objective,
        profile=profile,
        campaign_facts=campaign_facts,
    )
    en = intent.language != "tr"
    name = context.project_identity.project_name or "Project"
    place = _place_name(context, selected)

    include_eyebrow = family == "EDITORIAL"
    include_support = family != "MINIMAL_HERO"
    if family == "MINIMAL_HERO" and intent.marketing_objective == "investment":
        include_support = True
    if family == "LOCATION":
        include_support = True
        include_eyebrow = False

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
    cta = _objective_cta(intent, en=en)
    eyebrow = _objective_eyebrow(intent=intent, context=context, family=family) if include_eyebrow else ""

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
        }
        if intent.marketing_objective == "location"
        else {s.reason for s in suppressed}
    )
    if intent.marketing_objective == "location":
        exclude = [
            "construction status",
            "unit counts",
            "technical specifications",
            "financing terms",
            "mixed-use inventory",
            "project_status",
            "total_units",
        ]

    contrast, overlay_region = _contrast_for(family, profile)
    alignment = _alignment_for(family)
    density = _density_for(family, include_support, include_eyebrow)

    return CreativeConcept(
        objective=intent.marketing_objective,
        concept=_concept_line(intent.marketing_objective, family, place, name),
        visual_strategy=_visual_strategy(family, profile),
        primary_message=headline,
        supporting_message=support,
        cta=cta,
        information_to_exclude=exclude,
        composition_strategy=family,
        tone=intent.tone or "premium",
        text_density=density,
        eyebrow=eyebrow,
        include_eyebrow=bool(eyebrow),
        include_support=bool(support) and include_support,
        include_cta=True,
        alignment=alignment,
        contrast_strategy=contrast,
        overlay_region=overlay_region,
        safe_text_zone=profile.safe_text_zone,
        selected_facts=selected,
        suppressed_facts=suppressed,
        asset_profile=asdict(profile),
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
    }


def selected_fact_texts(concept: CreativeConcept) -> list[str]:
    return [f.text for f in concept.selected_facts if f.text]
