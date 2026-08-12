"""Copy Director — campaign copy from strategy, not from a data dump.

Runs after Marketing Strategist and before Creative Director.
Internally scores ~3 headline directions; only the selected package reaches the canvas.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from investhome_api.services.social_design_engine.creative_director import (
    GENERIC_CTA_PHRASES,
    GENERIC_HEADLINE_PHRASES,
    clip_headline,
    is_generic_cta,
    is_generic_headline,
)
from investhome_api.services.social_design_engine.marketing_strategist import (
    UNSUPPORTED_CLAIM_TERMS,
    MarketingStrategy,
    contains_raw_suppress_term,
    looks_like_raw_database_value,
    looks_like_street_address,
)
from investhome_api.services.social_design_engine.ops import (
    looks_like_rag_or_debug_copy,
    sanitize_creative_copy,
)

if TYPE_CHECKING:
    from investhome_api.services.social_design_engine.generation import (
        CampaignFact,
        ContentPackage,
        GenerationIntent,
    )

CopyEditKind = Literal[
    "none",
    "regenerate_headline",
    "adjust_tone",
    "strip_address",
    "change_objective",
]

AVOID_HEADLINES = frozenset(
    {
        *GENERIC_HEADLINE_PHRASES,
        "on columbia rd",
        "discover more",
        "explore more today",
        "premium living",
        "unique opportunity",
    }
)
AVOID_CTAS = frozenset(
    {
        *GENERIC_CTA_PHRASES,
        "discover more",
        "explore more today",
        "learn more",
        "click here",
    }
)
SPAM_LUXURY = ("premium", "luxury", "exclusive", "unique", "lüks", "luks")

QUALITY_DIMENSIONS = (
    "objective_match",
    "factual_grounding",
    "specificity",
    "brevity",
    "marketing_quality",
    "visual_usability",
    "cta_relevance",
)

REJECT_CODES = (
    "headline_is_address",
    "headline_is_project_name",
    "generic_filler",
    "support_is_raw_data",
    "irrelevant_facts",
    "too_long",
)


@dataclass
class HeadlineCandidate:
    text: str
    scores: dict[str, float] = field(default_factory=dict)
    total: float = 0.0
    notes: str = ""


@dataclass
class CopyQualityScore:
    scores: dict[str, float] = field(default_factory=dict)
    total: float = 0.0
    passed: bool = True
    reject_codes: list[str] = field(default_factory=list)


@dataclass
class CopyPackage:
    eyebrow: str
    headline: str
    supporting_copy: str
    cta: str
    language: str = "en"
    tone: str = "professional"


@dataclass
class CopyDirection:
    package: CopyPackage
    candidates: list[HeadlineCandidate] = field(default_factory=list)
    quality: CopyQualityScore = field(default_factory=CopyQualityScore)
    selected_index: int = 0


def _norm(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text or "")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    folded = folded.replace("ı", "i").replace("İ", "i")
    return folded.strip().lower()


def _word_count(text: str) -> int:
    return len([w for w in re.split(r"\s+", (text or "").strip()) if w])


def _clip(text: str, max_len: int) -> str:
    clean = sanitize_creative_copy(text, max_len=max_len)
    if not clean:
        return ""
    if len(clean) <= max_len:
        return clean
    cut = clean[: max_len - 1].rsplit(" ", 1)[0].strip()
    return cut or clean[:max_len]


def _title_case_identity(name: str) -> str:
    raw = (name or "").strip()
    if not raw:
        return ""
    if raw.isupper() and len(raw) > 3:
        return raw
    return raw.upper() if len(raw) <= 28 else raw


def _strip_unsupported_claims(text: str, *, evidence_blob: str) -> str:
    out = text or ""
    ev = _norm(evidence_blob)
    for term in UNSUPPORTED_CLAIM_TERMS:
        if term in _norm(out) and term not in ev:
            out = re.sub(re.escape(term), "", out, flags=re.I)
    out = re.sub(r"\s{2,}", " ", out).strip(" ,.;")
    return out


def _luxury_spam(text: str) -> bool:
    t = _norm(text)
    hits = sum(1 for w in SPAM_LUXURY if w in t)
    return hits >= 2


def _is_project_name_only(headline: str, project_name: str) -> bool:
    h = _norm(headline)
    n = _norm(project_name)
    if not h or not n:
        return False
    return h == n or h == f"the {n}"


def headline_is_merely_address(headline: str, excluded: list[str]) -> bool:
    if looks_like_street_address(headline):
        return True
    hn = _norm(headline)
    for fact in excluded:
        fn = _norm(fact)
        if fn and (fn == hn or fn in hn) and looks_like_street_address(fact):
            return True
        if looks_like_street_address(headline):
            return True
    return False


def _score_band(ok: bool, strong: bool = False) -> float:
    if strong:
        return 1.0
    return 0.85 if ok else 0.25


def score_headline_candidate(
    text: str,
    *,
    strategy: MarketingStrategy,
    campaign_facts: list[CampaignFact],
) -> HeadlineCandidate:
    t = clip_headline(text)
    tn = _norm(t)
    words = _word_count(t)
    scores: dict[str, float] = {}

    obj = strategy.objective
    angle = strategy.campaign_angle
    loc_ok = any(
        k in tn
        for k in (
            "washington",
            "city",
            "central",
            "neighborhood",
            "location",
            "address",
            _norm(strategy.neighborhood),
            _norm(strategy.city),
        )
        if k
    )
    inv_ok = bool(campaign_facts) and any(f.display in t for f in campaign_facts)
    arch_ok = any(k in tn for k in ("architecture", "character", "craft", "form", "facade", "façade", "material"))
    if obj == "location":
        scores["objective_relevance"] = _score_band(loc_ok, strong="central" in tn or bool(strategy.neighborhood and _norm(strategy.neighborhood) in tn))
    elif obj == "investment":
        scores["objective_relevance"] = _score_band(inv_ok or "invest" in tn, strong=inv_ok)
    elif obj == "architecture":
        scores["objective_relevance"] = _score_band(arch_ok or "character" in tn, strong=arch_ok)
    else:
        scores["objective_relevance"] = 0.7

    grounded = True
    if looks_like_street_address(t):
        grounded = False
    if contains_raw_suppress_term(t):
        grounded = False
    if any(term in tn for term in UNSUPPORTED_CLAIM_TERMS):
        ev = " ".join(strategy.supporting_evidence)
        if not any(term in _norm(ev) for term in UNSUPPORTED_CLAIM_TERMS if term in tn):
            grounded = False
    scores["factual_grounding"] = 0.95 if grounded else 0.15

    specific = not is_generic_headline(t) and tn not in AVOID_HEADLINES and not _is_project_name_only(t, strategy.project_name)
    if obj == "location" and looks_like_street_address(t):
        specific = False
    scores["specificity"] = 0.9 if specific else 0.2

    scores["clarity"] = 0.9 if 2 <= words <= 8 and "," not in t else 0.4
    scores["brevity"] = 1.0 if 2 <= words <= 6 else (0.7 if words <= 8 else 0.2)

    marketing = specific and not looks_like_street_address(t) and not _luxury_spam(t)
    if tn.startswith("on ") and looks_like_street_address(t):
        marketing = False
    scores["differentiation"] = 0.85 if marketing and not _is_project_name_only(t, strategy.project_name) else 0.3
    scores["visual_usability"] = 0.9 if words <= 6 and len(t) <= 42 else (0.6 if words <= 8 else 0.2)

    total = sum(scores.values()) / max(1, len(scores))
    notes = angle
    return HeadlineCandidate(text=t, scores=scores, total=round(total, 4), notes=notes)


def generate_headline_candidates(
    *,
    strategy: MarketingStrategy,
    intent: GenerationIntent,
    campaign_facts: list[CampaignFact],
) -> list[HeadlineCandidate]:
    """~3 directions. Scored; only the winner is selected for canvas."""
    en = intent.language != "tr"
    name = strategy.project_name or "Residences"
    city = strategy.city
    neighborhood = strategy.neighborhood
    obj = strategy.objective
    angle = strategy.campaign_angle
    raw: list[str] = []

    if obj == "location":
        if angle == "central_positioning" and city:
            raw.append(f"A Central {city} Address" if en else f"{city} merkezinde")
            raw.append(f"Centered in {city}" if en else f"{city} merkezinde")
        if neighborhood:
            raw.append(f"{neighborhood} Living" if en else f"{neighborhood} yaşamı")
            raw.append(f"At Home in {neighborhood}" if en else f"{neighborhood}'te")
        if angle == "city_lifestyle" and city:
            raw.append(f"{city} Living" if en else f"{city} yaşamı")
        if angle == "urban_connectivity" and city:
            ev = " ".join(strategy.supporting_evidence)
            if any(k in _norm(ev + " " + strategy.single_minded_message) for k in ("transit", "metro", "connect")):
                raw.append(f"Connected {city} Living" if en else f"{city} bağlantısı")
        if city and f"A Central {city} Address" not in raw:
            raw.append(f"A Central {city} Address" if en else f"{city} merkezinde")
        if not raw:
            raw.append("A City Address" if en else "Şehir adresinde")
    elif obj == "investment":
        money = next((f.display for f in campaign_facts if f.kind == "money"), None)
        pct = next((f.display for f in campaign_facts if f.kind == "percent"), None)
        if money:
            raw.append(f"From {money}" if en else f"{money} ile başlayın")
        if pct:
            raw.append(f"Target {pct}" if en else f"Hedef {pct}")
        raw.append(f"Invest in {name}" if en else f"{name} yatırımı")
        if money and pct:
            raw.append(f"{money} · {pct}" if en else f"{money} · {pct}")
    elif obj == "architecture":
        raw.extend(
            [
                f"The Character of {name}" if en else f"{name} karakteri",
                f"{name} in Form" if en else f"{name} formu",
                "Architecture, Not Inventory" if en else "Mimari önde",
            ]
        )
    elif obj in {"lifestyle", "interior"}:
        raw.extend(
            [
                f"Life at {name}" if en else f"{name} yaşamı",
                f"Living at {name}" if en else f"{name}'te yaşam",
                "A Daily Ritual" if en else "Günlük ritüel",
            ]
        )
    elif obj in {"launch", "project_introduction"}:
        raw.extend(
            [
                f"{name} Arrives" if en else f"{name} lansmanı",
                f"Introducing {name}" if en else f"{name} tanıtımı",
                f"{name}" if _word_count(name) >= 2 else f"Meet {name}",
            ]
        )
    else:
        raw.append(name if _word_count(name) >= 2 else f"Discover {name}")

    # Dedup, clip, drop address-like / generic
    seen: set[str] = set()
    candidates: list[HeadlineCandidate] = []
    for line in raw:
        clipped = clip_headline(line)
        key = _norm(clipped)
        if not key or key in seen:
            continue
        if looks_like_street_address(clipped) or key in AVOID_HEADLINES:
            continue
        if is_generic_headline(clipped):
            continue
        seen.add(key)
        candidates.append(score_headline_candidate(clipped, strategy=strategy, campaign_facts=campaign_facts))
        if len(candidates) >= 3:
            break
    if not candidates:
        fallback = clip_headline(
            f"A Central {city} Address" if obj == "location" and city else name
        )
        if looks_like_street_address(fallback) or _is_project_name_only(fallback, name):
            fallback = "A City Address" if obj == "location" else clip_headline(f"Meet {name}")
        candidates.append(score_headline_candidate(fallback, strategy=strategy, campaign_facts=campaign_facts))
    candidates.sort(key=lambda c: c.total, reverse=True)
    return candidates[:3]


def _supporting_copy(
    *,
    strategy: MarketingStrategy,
    intent: GenerationIntent,
    campaign_facts: list[CampaignFact],
    headline: str,
) -> str:
    en = intent.language != "tr"
    obj = strategy.objective
    evidence_blob = " ".join(strategy.supporting_evidence)
    if obj == "investment":
        metrics = [f.display for f in campaign_facts][:3]
        return " · ".join(metrics)
    if obj == "location":
        neighborhood = strategy.neighborhood
        city = strategy.city
        retrieved = next(
            (
                f.text
                for f in strategy.classified_facts
                if f.source == "retrieved" and not f.suppress_from_copy and not looks_like_street_address(f.text)
            ),
            "",
        )
        retrieved = _strip_unsupported_claims(retrieved, evidence_blob=evidence_blob)
        if retrieved and not contains_raw_suppress_term(retrieved) and not looks_like_raw_database_value(retrieved):
            line = retrieved.split(".")[0].strip()
            if line and _norm(line) not in _norm(headline) and not looks_like_street_address(line):
                return _clip(line, 110)
        if neighborhood and city:
            return (
                f"{neighborhood}, {city}."
                if en
                else f"{neighborhood}, {city}."
            )
        if neighborhood:
            return f"{neighborhood}." if neighborhood.endswith(".") else f"{neighborhood}."
        if city:
            return f"A refined address in {city}." if en else f"{city} içinde sakin bir adres."
        return ""
    if obj == "architecture":
        retrieved = next(
            (
                f.text
                for f in strategy.classified_facts
                if f.source == "retrieved" and not f.suppress_from_copy
            ),
            "",
        )
        if retrieved and not looks_like_street_address(retrieved):
            return _clip(retrieved.split(".")[0].strip(), 110)
        name = strategy.project_name or "the residences"
        return (
            f"A considered architectural presence at {name}."
            if en
            else f"{name} için ölçülü bir mimari duruş."
        )
    prose = next(
        (
            f.text
            for f in strategy.classified_facts
            if f.source == "retrieved" and not f.suppress_from_copy
        ),
        "",
    )
    if prose and not looks_like_street_address(prose) and not contains_raw_suppress_term(prose):
        return _clip(prose.split(".")[0].strip(), 110)
    return ""


def _cta_for(strategy: MarketingStrategy, intent: GenerationIntent) -> str:
    desired = (strategy.desired_action or "").strip()
    if desired and _norm(desired) not in AVOID_CTAS and not is_generic_cta(desired):
        return _clip(desired, 36)
    en = intent.language != "tr"
    obj = strategy.objective
    if obj == "location":
        return "Explore the Neighborhood" if en else "Mahalleyi keşfet"
    if obj == "investment":
        return "Explore the investment" if en else "Yatırımı incele"
    if obj == "architecture":
        return "View the architecture" if en else "Mimariyi incele"
    if obj in {"lifestyle", "interior"}:
        return "Tour the residences" if en else "Rezidansı gez"
    if obj in {"launch", "project_introduction"}:
        return "Join the launch" if en else "Lansmana katıl"
    return "Schedule a private tour" if en else "Özel tur planla"


def _eyebrow_for(strategy: MarketingStrategy, intent: GenerationIntent) -> str:
    """Optional identity. Location often uses the project name as eyebrow."""
    name = strategy.project_name
    if not name:
        return ""
    obj = strategy.objective
    if obj == "location":
        return _clip(_title_case_identity(name), 32)
    if obj in {"launch", "project_introduction", "architecture"}:
        return _clip(_title_case_identity(name), 32)
    return ""


def score_copy_quality(
    package: CopyPackage,
    *,
    strategy: MarketingStrategy,
    campaign_facts: list[CampaignFact],
) -> CopyQualityScore:
    scores: dict[str, float] = {k: 0.5 for k in QUALITY_DIMENSIONS}
    reject: list[str] = []
    headline = package.headline or ""
    support = package.supporting_copy or ""
    cta = package.cta or ""
    blob = f"{package.eyebrow} {headline} {support} {cta}"
    bn = _norm(blob)
    hn = _norm(headline)

    if headline_is_merely_address(headline, strategy.excluded_facts):
        reject.append("headline_is_address")
        scores["marketing_quality"] = 0.05
        scores["specificity"] = 0.1
    if _is_project_name_only(headline, strategy.project_name):
        reject.append("headline_is_project_name")
        scores["specificity"] = 0.15
    if is_generic_headline(headline) or hn in AVOID_HEADLINES or _luxury_spam(headline):
        reject.append("generic_filler")
        scores["marketing_quality"] = min(scores["marketing_quality"], 0.15)
    if looks_like_raw_database_value(support) or looks_like_street_address(support) or contains_raw_suppress_term(support):
        reject.append("support_is_raw_data")
        scores["factual_grounding"] = 0.1
    for fact in strategy.excluded_facts:
        token = (fact or "").strip()
        if token and len(token) >= 6 and token in blob and looks_like_street_address(token):
            if token in headline or token in support:
                reject.append("irrelevant_facts")
                break
        if token and contains_raw_suppress_term(token) and _norm(token) in bn:
            reject.append("irrelevant_facts")
            break
    if _word_count(headline) > 8 or len(support) > 140 or support.count("\n") > 1:
        reject.append("too_long")
        scores["brevity"] = 0.2

    obj = strategy.objective
    if obj == "location":
        loc_hit = any(
            k in bn
            for k in filter(
                None,
                (
                    _norm(strategy.city),
                    _norm(strategy.neighborhood),
                    "central",
                    "city",
                    "neighborhood",
                    "location",
                    "washington",
                ),
            )
        )
        scores["objective_match"] = 0.9 if loc_hit and "headline_is_address" not in reject else 0.2
    elif obj == "investment":
        present = all(f.display in blob for f in campaign_facts) if campaign_facts else "invest" in bn
        scores["objective_match"] = 0.95 if present else 0.2
        loc_dump = looks_like_street_address(blob) or contains_raw_suppress_term(blob)
        if loc_dump:
            reject.append("irrelevant_facts")
    elif obj == "architecture":
        leak = any(f.display in blob for f in campaign_facts) or looks_like_street_address(blob)
        scores["objective_match"] = 0.2 if leak else 0.85
        if leak:
            reject.append("irrelevant_facts")
    else:
        scores["objective_match"] = 0.75

    scores["factual_grounding"] = max(scores["factual_grounding"], 0.8) if "support_is_raw_data" not in reject else 0.1
    if "headline_is_address" not in reject and "generic_filler" not in reject:
        scores["specificity"] = max(scores["specificity"], 0.8)
        scores["marketing_quality"] = max(scores["marketing_quality"], 0.8)
    scores["brevity"] = 0.9 if 2 <= _word_count(headline) <= 8 and len(support) <= 110 else scores["brevity"]
    scores["visual_usability"] = 0.85 if _word_count(headline) <= 8 and len(headline) <= 48 else 0.4
    cta_n = _norm(cta)
    if is_generic_cta(cta) or cta_n in AVOID_CTAS:
        scores["cta_relevance"] = 0.2
        reject.append("generic_filler")
    else:
        if obj == "location" and any(k in cta_n for k in ("neighborhood", "location", "tour", "visit", "mahalle")):
            scores["cta_relevance"] = 0.95
        elif obj == "investment" and any(k in cta_n for k in ("invest", "yatırım", "yatirim", "opportunity", "details")):
            scores["cta_relevance"] = 0.95
        else:
            scores["cta_relevance"] = 0.75

    # Unique reject codes
    reject = list(dict.fromkeys(reject))
    total = sum(scores.values()) / max(1, len(scores))
    passed = not reject and total >= 0.55
    return CopyQualityScore(
        scores={k: round(v, 4) for k, v in scores.items()},
        total=round(total, 4),
        passed=passed,
        reject_codes=reject,
    )


def build_copy_package(
    *,
    strategy: MarketingStrategy,
    intent: GenerationIntent,
    campaign_facts: list[CampaignFact],
    preferred_headline: str | None = None,
) -> CopyDirection:
    candidates = generate_headline_candidates(
        strategy=strategy,
        intent=intent,
        campaign_facts=campaign_facts,
    )
    selected_index = 0
    headline = candidates[0].text if candidates else clip_headline(strategy.project_name or "Residences")
    if preferred_headline:
        pref = clip_headline(preferred_headline)
        if pref and not looks_like_street_address(pref) and not is_generic_headline(pref):
            scored = score_headline_candidate(pref, strategy=strategy, campaign_facts=campaign_facts)
            candidates = [scored] + [c for c in candidates if _norm(c.text) != _norm(pref)]
            headline = pref
            selected_index = 0
    support = _supporting_copy(
        strategy=strategy,
        intent=intent,
        campaign_facts=campaign_facts,
        headline=headline,
    )
    # Never put excluded raw facts on the canvas.
    for fact in strategy.excluded_facts:
        token = (fact or "").strip()
        if token and len(token) >= 5:
            if token in support:
                support = support.replace(token, "").strip(" ,.;")
            if token in headline:
                headline = candidates[0].text if candidates else headline
    support = _strip_unsupported_claims(support, evidence_blob=" ".join(strategy.supporting_evidence))
    support = _clip(re.sub(r"\s{2,}", " ", support).strip(" ,.;"), 110)
    if looks_like_street_address(support) or looks_like_raw_database_value(support):
        support = ""
        if strategy.objective == "location" and strategy.city:
            support = f"A refined address in {strategy.city}." if intent.language != "tr" else f"{strategy.city} içinde."
            if looks_like_street_address(support):
                support = strategy.city
    cta = _cta_for(strategy, intent)
    eyebrow = _eyebrow_for(strategy, intent)
    package = CopyPackage(
        eyebrow=_clip(eyebrow, 32),
        headline=_clip(headline, 70),
        supporting_copy=_clip(support, 110),
        cta=_clip(cta, 36),
        language=intent.language,
        tone=strategy.tone or intent.tone,
    )
    quality = score_copy_quality(package, strategy=strategy, campaign_facts=campaign_facts)
    if not quality.passed:
        package, candidates, selected_index, quality = _repair_copy(
            package,
            strategy=strategy,
            intent=intent,
            campaign_facts=campaign_facts,
            candidates=candidates,
            quality=quality,
        )
    return CopyDirection(
        package=package,
        candidates=candidates,
        quality=quality,
        selected_index=selected_index,
    )


def _repair_copy(
    package: CopyPackage,
    *,
    strategy: MarketingStrategy,
    intent: GenerationIntent,
    campaign_facts: list[CampaignFact],
    candidates: list[HeadlineCandidate],
    quality: CopyQualityScore,
) -> tuple[CopyPackage, list[HeadlineCandidate], int, CopyQualityScore]:
    headline = package.headline
    support = package.supporting_copy
    cta = package.cta
    eyebrow = package.eyebrow
    codes = set(quality.reject_codes)
    idx = 0
    if codes & {"headline_is_address", "headline_is_project_name", "generic_filler"}:
        for i, cand in enumerate(candidates):
            if not looks_like_street_address(cand.text) and not is_generic_headline(cand.text):
                if not _is_project_name_only(cand.text, strategy.project_name):
                    headline = cand.text
                    idx = i
                    break
        if looks_like_street_address(headline) or is_generic_headline(headline):
            city = strategy.city
            if strategy.objective == "location" and city:
                headline = clip_headline(f"A Central {city} Address")
            elif strategy.objective == "architecture":
                headline = clip_headline(f"The Character of {strategy.project_name or 'the Residences'}")
            else:
                headline = clip_headline(strategy.single_minded_message)
    if codes & {"support_is_raw_data", "irrelevant_facts"}:
        support = ""
        if strategy.objective == "location" and strategy.neighborhood:
            support = f"{strategy.neighborhood}."
        elif strategy.objective == "location" and strategy.city:
            support = f"A refined address in {strategy.city}."
        elif strategy.objective == "investment":
            support = " · ".join(f.display for f in campaign_facts[:3])
        for fact in strategy.excluded_facts:
            token = (fact or "").strip()
            if token and token in support:
                support = support.replace(token, "").strip(" ,.;")
        if looks_like_street_address(support):
            support = strategy.city
    if "too_long" in codes:
        headline = clip_headline(headline)
        support = _clip(support, 110)
    if "generic_filler" in codes and is_generic_cta(cta):
        cta = _cta_for(strategy, intent)
    repaired = CopyPackage(
        eyebrow=_clip(eyebrow, 32),
        headline=_clip(headline, 70),
        supporting_copy=_clip(support, 110),
        cta=_clip(cta, 36),
        language=package.language,
        tone=package.tone,
    )
    q2 = score_copy_quality(repaired, strategy=strategy, campaign_facts=campaign_facts)
    # After repair, address/generic must not survive even if other scores are soft.
    if headline_is_merely_address(repaired.headline, strategy.excluded_facts):
        city = strategy.city or "the City"
        repaired.headline = clip_headline(f"A Central {city} Address")
        q2 = score_copy_quality(repaired, strategy=strategy, campaign_facts=campaign_facts)
    return repaired, candidates, idx, q2


def copy_package_to_content_package(package: CopyPackage) -> ContentPackage:
    from investhome_api.services.social_design_engine.generation import ContentPackage

    return ContentPackage(
        headline=package.headline,
        supporting_text=package.supporting_copy,
        key_fact="",
        cta=package.cta,
        language=package.language,
        tone=package.tone,
        eyebrow=package.eyebrow,
    )


def content_package_to_copy_package(package: ContentPackage) -> CopyPackage:
    return CopyPackage(
        eyebrow=getattr(package, "eyebrow", "") or "",
        headline=package.headline,
        supporting_copy=package.supporting_text or package.key_fact,
        cta=package.cta,
        language=package.language,
        tone=package.tone,
    )


def copy_direction_to_dict(direction: CopyDirection) -> dict[str, Any]:
    return {
        "package": asdict(direction.package),
        "headline_candidates": [
            {"text": c.text, "scores": c.scores, "total": c.total, "notes": c.notes}
            for c in direction.candidates
        ],
        "copy_quality": {
            "scores": direction.quality.scores,
            "total": direction.quality.total,
            "passed": direction.quality.passed,
            "reject_codes": list(direction.quality.reject_codes),
        },
        "selected_index": direction.selected_index,
    }


def classify_copy_intelligence_edit(instruction: str) -> tuple[CopyEditKind, dict[str, str]]:
    """Copy-strategy edits — not layout, not a full new brief unless objective changes."""
    t = _norm(instruction)
    if any(
        k in t
        for k in (
            "yatırımcıya yönelik",
            "yatirimciya yonelik",
            "for investors",
            "investor-focused",
            "investor focused",
            "make it investment",
            "yatırım odaklı",
            "yatirim odakli",
        )
    ):
        return "change_objective", {"objective": "investment"}
    if any(
        k in t
        for k in (
            "adres bilgisini kaldır",
            "adres bilgisini kaldir",
            "adresi kaldır",
            "adresi kaldir",
            "remove the address",
            "remove address",
            "strip the address",
        )
    ):
        return "strip_address", {}
    if (
        any(k in t for k in ("baslig", "baslik", "headline", "title"))
        and any(k in t for k in ("daha guclu", "stronger", "guclu yap"))
    ) or any(
        k in t
        for k in (
            "make headline stronger",
            "make the headline stronger",
            "stronger headline",
        )
    ):
        return "regenerate_headline", {}
    if any(
        k in t
        for k in (
            "daha kurumsal",
            "more corporate",
            "more institutional",
            "daha resmi",
            "lokasyon mesajını daha",
            "lokasyon mesajini daha",
        )
    ):
        tone = "corporate" if any(k in t for k in ("kurumsal", "corporate", "institutional", "resmi")) else "professional"
        return "adjust_tone", {"tone": tone}
    return "none", {}


def apply_copy_intelligence_edit(
    *,
    kind: CopyEditKind,
    meta: dict[str, str],
    strategy: MarketingStrategy,
    intent: GenerationIntent,
    campaign_facts: list[CampaignFact],
    current: CopyPackage,
) -> CopyDirection:
    if kind == "strip_address":
        headline = current.headline
        support = current.supporting_copy
        eyebrow = current.eyebrow
        for blob_attr in ("headline", "support", "eyebrow"):
            pass
        if looks_like_street_address(headline) or headline_is_merely_address(headline, strategy.excluded_facts):
            rebuilt = build_copy_package(strategy=strategy, intent=intent, campaign_facts=campaign_facts)
            headline = rebuilt.package.headline
        for token in list(strategy.excluded_facts) + [current.supporting_copy]:
            piece = (token or "").strip()
            if piece and looks_like_street_address(piece):
                support = support.replace(piece, "").strip(" ,.;")
                headline = headline.replace(piece, "").strip(" ,.;")
        support = re.sub(r"\b\d{1,6}[A-Za-z]?\s+[A-Za-z].{0,40}", "", support)
        support = re.sub(r"\s{2,}", " ", support).strip(" ,.;")
        if looks_like_street_address(support):
            support = strategy.neighborhood or strategy.city or ""
        package = CopyPackage(
            eyebrow=eyebrow,
            headline=clip_headline(headline) or current.headline,
            supporting_copy=_clip(support, 110),
            cta=current.cta,
            language=current.language,
            tone=current.tone,
        )
        quality = score_copy_quality(package, strategy=strategy, campaign_facts=campaign_facts)
        return CopyDirection(package=package, candidates=[], quality=quality, selected_index=0)

    if kind == "regenerate_headline":
        direction = build_copy_package(strategy=strategy, intent=intent, campaign_facts=campaign_facts)
        # Stay in strategy: keep support/cta/eyebrow; swap to a stronger different headline.
        next_headline = direction.package.headline
        for cand in direction.candidates:
            if _norm(cand.text) != _norm(current.headline) and cand.total >= direction.candidates[0].total * 0.9:
                next_headline = cand.text
                break
        if _norm(next_headline) == _norm(current.headline) and len(direction.candidates) > 1:
            next_headline = direction.candidates[1].text
        package = CopyPackage(
            eyebrow=current.eyebrow or direction.package.eyebrow,
            headline=next_headline,
            supporting_copy=current.supporting_copy,
            cta=current.cta,
            language=current.language,
            tone=current.tone,
        )
        quality = score_copy_quality(package, strategy=strategy, campaign_facts=campaign_facts)
        return CopyDirection(
            package=package,
            candidates=direction.candidates,
            quality=quality,
            selected_index=0,
        )

    if kind == "adjust_tone":
        new_tone = meta.get("tone") or "corporate"
        strategy.tone = new_tone
        intent.tone = new_tone
        direction = build_copy_package(strategy=strategy, intent=intent, campaign_facts=campaign_facts)
        # Preserve objective/angle; allow copy to shift register.
        return direction

    return build_copy_package(strategy=strategy, intent=intent, campaign_facts=campaign_facts)


def copy_edit_ops(
    *,
    package: CopyPackage,
    post: dict[str, Any],
    linked_project_id: str,
) -> list[dict[str, Any]]:
    """Surgical copy updates on the current post — no full regenerate."""
    post_id = str(post.get("id") or "")
    pid = str(linked_project_id)
    ops: list[dict[str, Any]] = []
    elements = post.get("elements") if isinstance(post.get("elements"), list) else []

    def _el(role: str, types: tuple[str, ...]) -> dict[str, Any] | None:
        for el in elements:
            if not isinstance(el, dict):
                continue
            if el.get("type") in types and str(el.get("role") or "").lower() == role:
                return el
        if role == "cta":
            for el in elements:
                if isinstance(el, dict) and el.get("type") in {"BUTTON", "CTA"}:
                    return el
        return None

    headline_el = _el("headline", ("TEXT",))
    body_el = _el("body", ("TEXT",))
    eyebrow_el = _el("eyebrow", ("TEXT",))
    cta_el = _el("cta", ("BUTTON", "CTA"))

    if headline_el and package.headline:
        ops.append(
            {
                "op": "UPDATE_TEXT",
                "linked_project_id": pid,
                "post_id": post_id,
                "element_id": headline_el.get("id"),
                "payload": {"content": package.headline},
            }
        )
    if body_el is not None:
        if package.supporting_copy:
            ops.append(
                {
                    "op": "UPDATE_TEXT",
                    "linked_project_id": pid,
                    "post_id": post_id,
                    "element_id": body_el.get("id"),
                    "payload": {"content": package.supporting_copy},
                }
            )
        else:
            ops.append(
                {
                    "op": "DELETE_ELEMENT",
                    "linked_project_id": pid,
                    "post_id": post_id,
                    "element_id": body_el.get("id"),
                    "payload": {},
                }
            )
    if eyebrow_el is not None and package.eyebrow:
        ops.append(
            {
                "op": "UPDATE_TEXT",
                "linked_project_id": pid,
                "post_id": post_id,
                "element_id": eyebrow_el.get("id"),
                "payload": {"content": package.eyebrow},
            }
        )
    if cta_el is not None and package.cta:
        ops.append(
            {
                "op": "UPDATE_CTA",
                "linked_project_id": pid,
                "post_id": post_id,
                "element_id": cta_el.get("id"),
                "payload": {"label": package.cta},
            }
        )
    return ops
