"""Marketing Strategist — facts are evidence, not automatically the advertisement.

Runs after generation intent + RAG context and before Copy Director.
Produces structured application decisions only (never chain-of-thought).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from investhome_api.schemas.creative_studio_generation import CreativeStudioGenerationContext
from investhome_api.services.social_design_engine.ops import looks_like_rag_or_debug_copy

if TYPE_CHECKING:
    from investhome_api.services.social_design_engine.generation import (
        CampaignFact,
        GenerationIntent,
        MarketingObjective,
    )

FactKind = Literal["FACT", "PROOF", "BENEFIT", "MARKETING_WORTHY"]
CampaignAngle = Literal[
    "urban_connectivity",
    "neighborhood_access",
    "proximity",
    "central_positioning",
    "city_lifestyle",
    "destination_convenience",
    "opportunity",
    "income",
    "value",
    "investor_access",
    "participation",
    "daily_living",
    "amenities_experience",
    "identity_introduction",
    "architectural_character",
    "material_craft",
    "general",
]

STREET_TYPE_RE = re.compile(
    r"\b(rd|road|ave|avenue|st|street|blvd|boulevard|dr|drive|ln|lane|way|pl|place|"
    r"ct|court|pkwy|parkway|ter|terrace|cir|circle)\b",
    re.I,
)
STREET_NUMBER_RE = re.compile(
    r"\b\d{1,6}[A-Za-z]?\s+\S.+\b(rd|road|ave|avenue|st|street|blvd|boulevard|dr|drive)\b",
    re.I,
)
ON_STREET_RE = re.compile(
    r"^on\s+.+\b(rd|road|ave|avenue|st|street|blvd|boulevard|dr|drive)\b",
    re.I,
)
DIRECTIONAL_RE = re.compile(r"\b(nw|ne|sw|se)\b", re.I)

RAW_SUPPRESS_TERMS = (
    "under construction",
    "construction status",
    "construction schedule",
    "residential construction",
    "gsf",
    "gross square",
    "sqm",
    "sq ft",
    "zoning",
    "metadata.json",
    "project_status",
    "project_type",
    "project_code",
    "financing",
    "mortgage",
    "mixed-use",
    "mixed use",
    "total_units",
    "total units",
    "unit count",
    "parking spaces",
    "completion date",
    "delivery date",
    "index_status",
    "document_name",
    "chunk_id",
)

UNSUPPORTED_CLAIM_TERMS = (
    "steps from",
    "minutes from",
    "heart of dc",
    "heart of washington",
    "walkable",
    "connected to everything",
    "in the heart of",
)

GENERIC_FILLER = (
    "premium living",
    "unique opportunity",
    "discover more",
    "explore more today",
    "luxury living",
    "exclusive living",
)

LOCATION_ANGLES: tuple[CampaignAngle, ...] = (
    "urban_connectivity",
    "neighborhood_access",
    "proximity",
    "central_positioning",
    "city_lifestyle",
    "destination_convenience",
)
INVESTMENT_ANGLES: tuple[CampaignAngle, ...] = (
    "opportunity",
    "income",
    "value",
    "investor_access",
    "participation",
)


@dataclass
class ClassifiedFact:
    text: str
    kind: FactKind
    source: str
    reason: str
    suppress_from_copy: bool = False
    provenance: str = ""
    key: str | None = None


@dataclass
class MarketingStrategy:
    objective: str
    audience: str
    campaign_angle: CampaignAngle
    single_minded_message: str
    supporting_evidence: list[str] = field(default_factory=list)
    excluded_facts: list[str] = field(default_factory=list)
    desired_action: str = ""
    tone: str = "professional"
    classified_facts: list[ClassifiedFact] = field(default_factory=list)
    neighborhood: str = ""
    city: str = ""
    project_name: str = ""


def _norm(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text or "")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return folded.strip().lower()


def looks_like_street_address(text: str) -> bool:
    """True when copy is a street/address line rather than a campaign idea."""
    raw = (text or "").strip()
    if not raw:
        return False
    t = _norm(raw)
    if STREET_NUMBER_RE.search(raw):
        return True
    if ON_STREET_RE.search(t):
        return True
    words = [w for w in re.split(r"\s+", raw) if w]
    if STREET_TYPE_RE.search(raw) and DIRECTIONAL_RE.search(raw) and len(words) <= 6:
        return True
    if STREET_TYPE_RE.search(raw) and len(words) <= 4 and not any(
        k in t for k in ("living", "address", "location", "neighborhood", "city")
    ):
        return True
    return False


def looks_like_raw_database_value(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if looks_like_rag_or_debug_copy(t):
        return True
    if re.match(
        r"^(project_name|project_code|city|country|address|total_units|project_type|project_status)\s*=",
        t,
        re.I,
    ):
        return True
    if re.fullmatch(r"\d+\s*units?", t, re.I):
        return True
    return False


def contains_raw_suppress_term(text: str) -> bool:
    t = _norm(text)
    return any(term in t for term in RAW_SUPPRESS_TERMS)


def claim_is_supported(claim: str, evidence_blob: str) -> bool:
    needle = _norm(claim)
    hay = _norm(evidence_blob)
    if not needle:
        return False
    return needle in hay


def extract_neighborhood(retrieved: list[Any], *, city: str = "", project_name: str = "") -> str:
    """Pull a neighborhood name from RAG only — never invent one."""
    city_n = _norm(city)
    name_n = _norm(project_name)
    patterns = (
        re.compile(r"\bin\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?)\s*,", re.M),
        re.compile(r"\bin\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?)\s+(?:neighborhood|district|corridor)\b"),
        re.compile(r"\b([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?)\s+neighborhood\b"),
        re.compile(r"\bneighborhood of\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?)\b"),
        re.compile(r"\bsits in\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?)\b"),
        re.compile(r"\blocated in\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?)\b"),
    )
    skip = {
        "washington",
        "united",
        "states",
        "the temple",
        "temple residences",
        "instagram",
        "project",
        "residences",
    }
    if city_n:
        skip.add(city_n)
    if name_n:
        skip.add(name_n)
    for row in retrieved:
        if not isinstance(row, dict):
            continue
        name = str(row.get("document_name") or "").lower()
        if "metadata.json" in name or name.endswith(".json"):
            continue
        text = str(row.get("text") or row.get("excerpt") or "").strip()
        if not text or looks_like_rag_or_debug_copy(text):
            continue
        for pat in patterns:
            m = pat.search(text)
            if not m:
                continue
            cand = m.group(1).strip(" ,.")
            cn = _norm(cand)
            if not cand or cn in skip or looks_like_street_address(cand):
                continue
            if STREET_TYPE_RE.search(cand):
                continue
            if len(cand.split()) > 3:
                continue
            return cand
    return ""


def _parse_identity_rows(raw: list[str]) -> list[tuple[str | None, str, str]]:
    out: list[tuple[str | None, str, str]] = []
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
            display = val.strip()
            if not display:
                continue
        out.append((key, display, text))
    return out


def classify_facts(
    *,
    objective: str,
    context: CreativeStudioGenerationContext,
    campaign_facts: list[CampaignFact],
    instruction: str = "",
) -> list[ClassifiedFact]:
    """Classify each datum as FACT / PROOF / BENEFIT / MARKETING-WORTHY.

    Address is a FACT (proof of place), never automatically a marketing-worthy message.
    """
    asked = _norm(instruction)
    user_asked_units = any(k in asked for k in ("unit", "residence count", "kaç daire", "kac daire"))
    user_asked_construction = any(k in asked for k in ("construction", "inşaat", "insaat", "status"))
    classified: list[ClassifiedFact] = []
    seen: set[str] = set()

    def _add(item: ClassifiedFact) -> None:
        token = _norm(item.text)
        if not token or token in seen:
            return
        seen.add(token)
        classified.append(item)

    ident = context.project_identity
    identity_rows = _parse_identity_rows(list(context.verified_facts or []))
    have_keys = {k for k, _, _ in identity_rows if k}
    for key, val in (
        ("project_name", ident.project_name),
        ("city", ident.city),
        ("country", ident.country),
    ):
        if val and key not in have_keys:
            identity_rows.append((key, val, f"{key}={val}"))

    for key, display, provenance in identity_rows:
        blob = f"{key or ''} {display} {provenance}"
        if looks_like_rag_or_debug_copy(display):
            _add(
                ClassifiedFact(
                    text=display,
                    kind="FACT",
                    source="verified_fact",
                    reason="debug_metadata",
                    suppress_from_copy=True,
                    provenance=provenance,
                    key=key,
                )
            )
            continue
        if key in {"project_status", "project_type", "project_code"} or contains_raw_suppress_term(blob):
            if key == "project_status" and user_asked_construction:
                _add(
                    ClassifiedFact(
                        text=display,
                        kind="FACT",
                        source="verified_fact",
                        reason="user_asked_status",
                        suppress_from_copy=False,
                        provenance=provenance,
                        key=key,
                    )
                )
            else:
                _add(
                    ClassifiedFact(
                        text=display,
                        kind="FACT",
                        source="verified_fact",
                        reason="raw_internal_metadata",
                        suppress_from_copy=True,
                        provenance=provenance,
                        key=key,
                    )
                )
            continue
        if key == "address" or looks_like_street_address(display):
            _add(
                ClassifiedFact(
                    text=display,
                    kind="FACT",
                    source="verified_fact",
                    reason="address_is_evidence_not_the_ad",
                    suppress_from_copy=True,
                    provenance=provenance,
                    key=key or "address",
                )
            )
            continue
        if key == "total_units":
            try:
                n = int(re.sub(r"[^\d]", "", display) or "0")
            except ValueError:
                n = 0
            limited_ok = (
                0 < n <= 80
                and objective in {"lifestyle", "launch", "project_introduction", "architecture"}
                and not user_asked_units
            )
            _add(
                ClassifiedFact(
                    text=display,
                    kind="PROOF" if limited_ok else "FACT",
                    source="verified_fact",
                    reason="limited_collection_proof" if limited_ok else "unit_count_internal",
                    suppress_from_copy=not (limited_ok or user_asked_units),
                    provenance=provenance,
                    key=key,
                )
            )
            if limited_ok:
                _add(
                    ClassifiedFact(
                        text="A limited collection",
                        kind="BENEFIT",
                        source="derived",
                        reason="unit_count_benefit_restrained",
                        suppress_from_copy=False,
                        provenance=provenance,
                        key="limited_collection",
                    )
                )
            continue
        if key == "city":
            _add(
                ClassifiedFact(
                    text=display,
                    kind="PROOF" if objective == "location" else "FACT",
                    source="identity",
                    reason="city_place_proof" if objective == "location" else "identity_city",
                    suppress_from_copy=False,
                    provenance=provenance,
                    key=key,
                )
            )
            continue
        if key == "project_name":
            _add(
                ClassifiedFact(
                    text=display,
                    kind="FACT",
                    source="identity",
                    reason="identity_name",
                    suppress_from_copy=False,
                    provenance=provenance,
                    key=key,
                )
            )
            continue
        _add(
            ClassifiedFact(
                text=display,
                kind="FACT",
                source="verified_fact",
                reason="identity_other",
                suppress_from_copy=objective == "location",
                provenance=provenance,
                key=key,
            )
        )

    for row in list(context.retrieved_content or []):
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
        if contains_raw_suppress_term(sentence) and not user_asked_construction:
            _add(
                ClassifiedFact(
                    text=sentence[:220],
                    kind="FACT",
                    source="retrieved",
                    reason="raw_operational_data",
                    suppress_from_copy=True,
                    provenance=name,
                )
            )
            continue
        if looks_like_street_address(sentence):
            _add(
                ClassifiedFact(
                    text=sentence[:220],
                    kind="FACT",
                    source="retrieved",
                    reason="address_is_evidence_not_the_ad",
                    suppress_from_copy=True,
                    provenance=name,
                )
            )
            continue
        loc_terms = (
            "location",
            "neighborhood",
            "neighbourhood",
            "district",
            "corridor",
            "city",
            "washington",
            "central",
        )
        inv_terms = ("investment", "investor", "roi", "yield", "return", "getiri", "yatırım")
        arch_terms = (
            "architecture",
            "architectural",
            "facade",
            "façade",
            "material",
            "craft",
            "character",
            "design language",
        )
        life_terms = ("lifestyle", "amenity", "amenities", "spa", "pool", "lobby", "rooftop")
        sn = _norm(sentence)
        relevant = True
        kind: FactKind = "PROOF"
        reason = "retrieved_proof"
        if objective == "location":
            relevant = any(k in sn for k in loc_terms) or bool(extract_neighborhood([row], city=ident.city or ""))
            reason = "neighborhood_or_place_proof"
        elif objective == "investment":
            relevant = any(k in sn for k in inv_terms)
            reason = "investment_proof"
        elif objective in {"architecture"}:
            relevant = any(k in sn for k in arch_terms)
            reason = "architecture_proof"
        elif objective in {"lifestyle", "interior"}:
            relevant = any(k in sn for k in life_terms)
            reason = "lifestyle_proof"
        if not relevant:
            _add(
                ClassifiedFact(
                    text=sentence[:220],
                    kind="FACT",
                    source="retrieved",
                    reason=f"off_objective_{objective}",
                    suppress_from_copy=True,
                    provenance=name,
                )
            )
            continue
        _add(
            ClassifiedFact(
                text=sentence[:220],
                kind=kind,
                source="retrieved",
                reason=reason,
                suppress_from_copy=False,
                provenance=name,
            )
        )

    for cf in campaign_facts:
        _add(
            ClassifiedFact(
                text=cf.display,
                kind="MARKETING_WORTHY" if objective == "investment" else "FACT",
                source="campaign",
                reason="user_supplied_campaign",
                suppress_from_copy=objective != "investment",
                provenance="user_supplied",
                key=cf.label,
            )
        )

    return classified


def choose_campaign_angle(
    *,
    objective: str,
    instruction: str,
    classified: list[ClassifiedFact],
    neighborhood: str,
    city: str,
) -> CampaignAngle:
    t = _norm(instruction)
    evidence = " ".join(f.text for f in classified if not f.suppress_from_copy)
    ev = _norm(evidence)

    if objective == "location":
        if any(k in t for k in ("merkezi", "central", "merkez")):
            return "central_positioning"
        if neighborhood and any(k in t for k in ("neighborhood", "mahalle", "district")):
            return "neighborhood_access"
        if any(k in t or k in ev for k in ("metro", "transit", "connectivity", "connected")):
            return "urban_connectivity"
        if any(k in t for k in ("yakın", "yakin", "proximity", "near")):
            return "proximity"
        if any(k in t for k in ("lifestyle", "yaşam", "yasam", "city living")):
            return "city_lifestyle"
        if neighborhood:
            return "neighborhood_access"
        if city:
            return "central_positioning" if any(k in t for k in ("lokasyon", "location", "konum")) else "city_lifestyle"
        return "central_positioning"
    if objective == "investment":
        if any(k in t for k in ("getiri", "yield", "return", "roi", "%")):
            return "income"
        if any(k in t for k in ("minimum", "from $", "entry", "katılım", "katilim")):
            return "investor_access"
        if any(k in t for k in ("süre", "sure", "duration", "ay", "month")):
            return "participation"
        if any(k in t for k in ("value", "değer", "deger")):
            return "value"
        return "opportunity"
    if objective in {"lifestyle", "interior"}:
        if any(k in t or k in ev for k in ("amenit", "spa", "pool", "rooftop")):
            return "amenities_experience"
        return "daily_living"
    if objective in {"architecture"}:
        if any(k in t or k in ev for k in ("material", "malzeme", "craft", "facade", "façade")):
            return "material_craft"
        return "architectural_character"
    if objective in {"launch", "project_introduction"}:
        return "identity_introduction"
    return "general"


def _single_minded_message(
    *,
    objective: str,
    angle: CampaignAngle,
    project_name: str,
    city: str,
    neighborhood: str,
    campaign_facts: list[CampaignFact],
    language: str,
    campaign_intelligence: Any | None = None,
) -> str:
    """ONE idea this ad should communicate — not a RAG summary, not a street."""
    en = language != "tr"
    name = project_name or "the residences"
    if objective == "location":
        place = neighborhood or city
        if angle == "central_positioning":
            if city:
                return (
                    f"A central {city} location — place, not a street number."
                    if en
                    else f"{city} merkezinde bir konum."
                )
            return "A central city location." if en else "Şehir merkezinde bir konum."
        if angle == "neighborhood_access" and neighborhood:
            return (
                f"{name} belongs to {neighborhood}."
                if en
                else f"{name} {neighborhood} mahallesinde."
            )
        if angle == "urban_connectivity":
            return (
                f"Connected urban living in {place or 'the city'}."
                if en
                else f"{place or 'şehir'} ile kurulu bir yaşam."
            )
        if angle == "city_lifestyle":
            return f"City living at {name}." if en else f"{name} şehir yaşamı."
        if angle == "destination_convenience":
            return f"{place or name} as a destination." if en else f"{place or name} bir durak."
        if angle == "proximity" and place:
            return f"Close to {place}." if en else f"{place} yakınında."
        return f"A {place or 'city'} location." if en else f"{place or 'şehir'} lokasyonu."
    if objective == "investment":
        if campaign_facts:
            return (
                "This campaign’s investment case, in the figures given."
                if en
                else "Bu kampanyanın yatırım tezi, verilen rakamlarla."
            )
        # Investment awareness without inventing returns — grounded in place/identity.
        place = city or neighborhood
        if place:
            return (
                f"A considered investment position in {place}."
                if en
                else f"{place} içinde ölçülü bir yatırım konumu."
            )
        return (
            f"A considered investment position at {name}."
            if en
            else f"{name} için ölçülü bir yatırım konumu."
        )
    if objective in {"lifestyle", "interior"}:
        return f"Daily life at {name}." if en else f"{name} günlük yaşamı."
    if objective == "architecture":
        return f"The architectural character of {name}." if en else f"{name} mimari karakteri."
    if objective in {"launch", "project_introduction"}:
        return f"Introduce {name}." if en else f"{name} tanıtımı."
    _ = campaign_intelligence
    return name


def _desired_action(objective: str, *, language: str, cta_hint: str | None) -> str:
    if cta_hint:
        return cta_hint
    en = language != "tr"
    if objective == "location":
        return "Explore the neighborhood" if en else "Mahalleyi keşfet"
    if objective == "investment":
        return "Explore the investment" if en else "Yatırımı incele"
    if objective == "architecture":
        return "View the architecture" if en else "Mimariyi incele"
    if objective in {"lifestyle", "interior"}:
        return "Tour the residences" if en else "Rezidansı gez"
    if objective in {"launch", "project_introduction"}:
        return "Join the launch" if en else "Lansmana katıl"
    return "Schedule a private tour" if en else "Özel tur planla"


def build_marketing_strategy(
    *,
    instruction: str,
    intent: GenerationIntent,
    context: CreativeStudioGenerationContext,
    campaign_facts: list[CampaignFact],
    campaign_intelligence: Any | None = None,
) -> MarketingStrategy:
    """Answer: what ONE idea should this ad communicate?"""
    objective = intent.marketing_objective
    classified = classify_facts(
        objective=objective,
        context=context,
        campaign_facts=campaign_facts,
        instruction=instruction,
    )
    city = (context.project_identity.city or "").strip()
    name = (context.project_identity.project_name or "").strip()
    neighborhood = extract_neighborhood(
        list(context.retrieved_content or []),
        city=city,
        project_name=name,
    )
    # Prefer neighborhood/city from Project Knowledge when available.
    if campaign_intelligence is not None:
        knowledge = getattr(campaign_intelligence, "project_knowledge", None)
        if knowledge is not None:
            nb = (getattr(knowledge, "neighborhood", None) or {}) if knowledge else {}
            if isinstance(nb, dict) and nb.get("name") and not neighborhood:
                neighborhood = str(nb["name"])
            loc = (getattr(knowledge, "location", None) or {}) if knowledge else {}
            if isinstance(loc, dict) and loc.get("city") and not city:
                city = str(loc["city"])
            ident = (getattr(knowledge, "project_identity", None) or {}) if knowledge else {}
            if isinstance(ident, dict) and ident.get("project_name") and not name:
                name = str(ident["project_name"])
    angle = choose_campaign_angle(
        objective=objective,
        instruction=instruction,
        classified=classified,
        neighborhood=neighborhood,
        city=city,
    )
    supporting = [
        f.text
        for f in classified
        if not f.suppress_from_copy and f.kind in {"PROOF", "BENEFIT", "MARKETING_WORTHY"}
    ]
    if objective == "location" and neighborhood and neighborhood not in supporting:
        supporting.insert(0, neighborhood)
    if objective == "location" and city and city not in supporting:
        supporting.insert(0, city)
    if objective == "investment":
        # Prefer verified/selected campaign facts from intelligence; fall back to user inputs.
        intel_evidence: list[str] = []
        if campaign_intelligence is not None:
            from investhome_api.services.social_design_engine.verified_facts import (
                selected_facts_as_strategy_evidence,
            )

            intel_evidence = selected_facts_as_strategy_evidence(
                list(getattr(campaign_intelligence, "verified_campaign_facts", []) or [])
            )
        if campaign_facts:
            supporting = [cf.display for cf in campaign_facts][:3]
        elif intel_evidence:
            # Non-metric investment: value prop / identity / place — never invent returns.
            supporting = [
                e
                for e in intel_evidence
                if not looks_like_street_address(e) and not contains_raw_suppress_term(e)
            ][:4]
        else:
            supporting = [x for x in supporting if not looks_like_street_address(x)][:3]
    excluded = [
        f.text
        for f in classified
        if f.suppress_from_copy and f.text
    ]
    # Always exclude raw address / construction / filenames from the ad.
    for f in classified:
        if f.key == "address" or looks_like_street_address(f.text):
            if f.text not in excluded:
                excluded.append(f.text)
    # Exclude off-intent financial figures when intelligence selected none for location etc.
    if campaign_intelligence is not None and objective == "location":
        for vf in list(getattr(campaign_intelligence, "verified_campaign_facts", []) or []):
            if getattr(vf, "is_financial", False) and getattr(vf, "display_value", None):
                token = str(vf.display_value)
                if token not in excluded:
                    excluded.append(token)
    return MarketingStrategy(
        objective=objective,
        audience=intent.audience or ("investors" if objective == "investment" else "general"),
        campaign_angle=angle,
        single_minded_message=_single_minded_message(
            objective=objective,
            angle=angle,
            project_name=name,
            city=city,
            neighborhood=neighborhood,
            campaign_facts=campaign_facts,
            language=intent.language,
            campaign_intelligence=campaign_intelligence,
        ),
        supporting_evidence=supporting[:6],
        excluded_facts=excluded[:24],
        desired_action=_desired_action(objective, language=intent.language, cta_hint=intent.cta_hint),
        tone=intent.tone or "professional",
        classified_facts=classified,
        neighborhood=neighborhood,
        city=city,
        project_name=name,
    )


def strategy_to_dict(strategy: MarketingStrategy) -> dict[str, Any]:
    return {
        "objective": strategy.objective,
        "audience": strategy.audience,
        "campaign_angle": strategy.campaign_angle,
        "single_minded_message": strategy.single_minded_message,
        "supporting_evidence": list(strategy.supporting_evidence),
        "excluded_facts": list(strategy.excluded_facts),
        "desired_action": strategy.desired_action,
        "tone": strategy.tone,
        "classified_facts": [asdict(f) for f in strategy.classified_facts],
        "neighborhood": strategy.neighborhood,
        "city": strategy.city,
        "project_name": strategy.project_name,
    }


def strategy_from_dict(raw: dict[str, Any] | None) -> MarketingStrategy | None:
    if not isinstance(raw, dict) or not raw.get("objective"):
        return None
    facts: list[ClassifiedFact] = []
    for row in raw.get("classified_facts") or []:
        if not isinstance(row, dict) or not row.get("text"):
            continue
        facts.append(
            ClassifiedFact(
                text=str(row.get("text") or ""),
                kind=row.get("kind") or "FACT",  # type: ignore[arg-type]
                source=str(row.get("source") or ""),
                reason=str(row.get("reason") or ""),
                suppress_from_copy=bool(row.get("suppress_from_copy")),
                provenance=str(row.get("provenance") or ""),
                key=str(row["key"]) if row.get("key") else None,
            )
        )
    angle = str(raw.get("campaign_angle") or "general")
    return MarketingStrategy(
        objective=str(raw.get("objective") or "general"),
        audience=str(raw.get("audience") or "general"),
        campaign_angle=angle if angle else "general",  # type: ignore[arg-type]
        single_minded_message=str(raw.get("single_minded_message") or ""),
        supporting_evidence=[str(x) for x in (raw.get("supporting_evidence") or []) if x],
        excluded_facts=[str(x) for x in (raw.get("excluded_facts") or []) if x],
        desired_action=str(raw.get("desired_action") or ""),
        tone=str(raw.get("tone") or "professional"),
        classified_facts=facts,
        neighborhood=str(raw.get("neighborhood") or ""),
        city=str(raw.get("city") or ""),
        project_name=str(raw.get("project_name") or ""),
    )
