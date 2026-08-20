"""Campaign intent classification for Project-Aware Campaign Intelligence.

Understands what the user wants the ad to do — not only keyword hits.
Maps to existing MarketingObjective for downstream strategist/copy/CD.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from investhome_api.services.social_design_engine.generation import (
    AssetPreference,
    MarketingObjective,
    extract_campaign_facts,
)

CampaignIntentKind = Literal[
    "investment",
    "location",
    "lifestyle",
    "project_awareness",
    "construction_progress",
    "launch",
    "availability",
    "rental_income",
    "value_proposition",
    "amenities",
    "neighborhood",
    "architecture",
    "generic_project_promotion",
]

# Explicit financial fact asks that must not be invented when absent.
EXPLICIT_FINANCIAL_FACT_KEYS: frozenset[str] = frozenset(
    {
        "irr",
        "roi",
        "target_return",
        "yield",
        "rental_income",
        "min_investment",
        "appreciation",
        "profit",
        "financing",
        "duration",
    }
)

INTENT_TO_OBJECTIVE: dict[CampaignIntentKind, MarketingObjective] = {
    "investment": "investment",
    "rental_income": "investment",
    "value_proposition": "investment",
    "location": "location",
    "neighborhood": "location",
    "lifestyle": "lifestyle",
    "amenities": "lifestyle",
    "architecture": "architecture",
    "launch": "launch",
    "availability": "launch",
    "project_awareness": "project_introduction",
    "generic_project_promotion": "project_introduction",
    "construction_progress": "general",
}

INTENT_TO_ASSET: dict[CampaignIntentKind, AssetPreference] = {
    "investment": "premium_hero",
    "rental_income": "premium_hero",
    "value_proposition": "premium_hero",
    "location": "aerial",
    "neighborhood": "neighborhood",
    "lifestyle": "interior",
    "amenities": "interior",
    "architecture": "exterior",
    "launch": "premium_hero",
    "availability": "premium_hero",
    "project_awareness": "premium_hero",
    "generic_project_promotion": "premium_hero",
    "construction_progress": "exterior",
}


@dataclass
class ExplicitFactRequest:
    """User explicitly asked to feature a fact that may be missing."""

    key: str
    label: str
    required: bool = True
    raw_span: str = ""


@dataclass
class CampaignIntentResult:
    campaign_intent: CampaignIntentKind
    marketing_objective: MarketingObjective
    confidence: float
    audience: str
    tone: str
    language: str
    platform: str
    format_preset: str
    asset_preference: AssetPreference
    key_message: str
    cta_hint: str | None
    signals: list[str] = field(default_factory=list)
    explicit_fact_requests: list[ExplicitFactRequest] = field(default_factory=list)
    user_supplied_financial: list[str] = field(default_factory=list)


def _norm(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text or "")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    folded = folded.replace("ı", "i").replace("İ", "i")
    return folded.strip().lower()


def _detect_language(instruction: str, language: str | None) -> str:
    t = _norm(instruction)
    lang = (language or "").strip().lower()
    if any(k in t for k in ("ingilizce", "in english", "english", "write in english")):
        return "en"
    if any(k in t for k in ("turkce", "türkçe", "in turkish", "turkish")):
        return "tr"
    if lang.startswith("tr"):
        return "tr"
    if lang.startswith("en"):
        return "en"
    if re.search(r"[a-z]{4,}", t) and not re.search(r"[çğıöşü]", instruction or ""):
        return "en"
    return "tr" if re.search(r"[çğıöşü]", instruction or "") else "en"


# Verb family "öne çıkar / çıkarmak / çıkaran" must NEVER count as Profit (kâr).
_CIKAR_FAMILY_RE = re.compile(
    r"\b(?:one|öne)?\s*(?:plana\s+)?cikar\w*",
    re.I,
)
_PROFIT_FALSE_FRIENDS_RE = re.compile(
    r"\bkarakter\w*|\bkare\b|\bkart\w*",
    re.I,
)
# Standalone profit / kâr only — not substring of çıkar/karakter.
_PROFIT_MEANING_RE = re.compile(
    r"(?<![a-z])(?:profit|projected\s+profit)(?![a-z])"
    r"|(?<![a-z])net\s+kar\w*"
    r"|(?<![a-z])kar\s+(?:marj|pay|oran)\w*"
    r"|(?<![a-z])kar(?![a-z])",
    re.I,
)


def _mentions_profit_claim(normalized: str) -> bool:
    """True only for meaning-based Profit/kâr — not 'öne çıkar' / 'karakter'."""
    cleaned = _CIKAR_FAMILY_RE.sub(" ", normalized or "")
    cleaned = _PROFIT_FALSE_FRIENDS_RE.sub(" ", cleaned)
    return bool(_PROFIT_MEANING_RE.search(cleaned))


def detect_explicit_financial_requests(instruction: str) -> list[ExplicitFactRequest]:
    """Detect when the user requires a specific financial figure in the creative."""
    raw = instruction or ""
    t = _norm(raw)
    found: list[ExplicitFactRequest] = []

    patterns: list[tuple[str, str, tuple[str, ...]]] = [
        (
            "irr",
            "IRR",
            (
                r"\birr\b",
                r"irr\s*oran",
                r"irr'?yi",
                r"irr'?n[ıi]",
                r"highlight\s+(?:the\s+)?irr",
                r"öne\s+çıkar.{0,24}irr",
                r"irr.{0,24}öne\s+çıkar",
                r"irr.{0,24}one\s+cikar",
                r"one\s+cikar.{0,24}irr",
            ),
        ),
        (
            "roi",
            "ROI",
            (
                r"\broi\b",
                r"roi\s*oran",
                r"highlight\s+(?:the\s+)?roi",
                r"roi.{0,24}öne\s+çıkar",
                r"roi.{0,24}one\s+cikar",
                r"one\s+cikar.{0,24}roi",
            ),
        ),
        (
            "target_return",
            "Target return",
            (
                r"hedef\s+getiri",
                r"target\s+return",
                r"getiri\s*oran",
                r"return\s*rate",
            ),
        ),
        (
            "yield",
            "Yield",
            (r"\byield\b", r"net\s+yield", r"kira\s+getiri"),
        ),
        (
            "rental_income",
            "Rental income",
            (r"rental\s+income", r"kira\s+gelir", r"kira\s+getiri"),
        ),
        (
            "min_investment",
            "Minimum investment",
            (r"minimum\s+yat[ıi]r[ıi]m", r"min(?:imum)?\s+investment", r"entry\s+ticket"),
        ),
        (
            "appreciation",
            "Appreciation",
            (r"\bappreciation\b", r"değer\s+art[ıi][sş]", r"deger\s+artis"),
        ),
        (
            "financing",
            "Financing",
            (r"\bfinancing\b", r"finansman", r"\bmortgage\b"),
        ),
        (
            "duration",
            "Investment duration",
            (r"yat[ıi]r[ıi]m\s+s[uü]resi", r"investment\s+(?:term|duration|horizon)"),
        ),
    ]

    emphasize = any(
        k in t
        for k in (
            "one cikar",
            "öne çıkar",
            "one çıkar",
            "highlight",
            "feature",
            "goster",
            "göster",
            "vurgula",
            "include",
            "ekle",
            "kullan",
        )
    )

    for key, label, pats in patterns:
        matched = False
        span = ""
        for pat in pats:
            m = re.search(pat, t, re.I)
            if m:
                matched = True
                span = m.group(0)
                break
        if not matched:
            continue
        # IRR/ROI alone in a short imperative still counts as explicit.
        required = emphasize or key in {"irr", "roi"} or any(
            k in t for k in ("oran", "rate", "rakam", "metric", "metrik", "%")
        )
        if key in {"irr", "roi"} and (
            emphasize
            or re.search(rf"{key}.{{0,40}}(one|öne|highlight|feature|goster|göster|vurgula)", t)
            or re.search(rf"(one|öne|highlight|feature|goster|göster|vurgula).{{0,40}}{key}", t)
        ):
            required = True
        if not required and key not in {"irr", "roi"}:
            continue
        found.append(ExplicitFactRequest(key=key, label=label, required=required, raw_span=span))

    # Profit / kâr — meaning-based only (never from "öne çıkar" / "çıkarmak").
    if _mentions_profit_claim(t):
        required = emphasize or any(k in t for k in ("oran", "rate", "rakam", "metric", "metrik", "%", "net"))
        if required:
            found.append(
                ExplicitFactRequest(key="profit", label="Profit", required=True, raw_span="profit")
            )

    # Dedup by key
    seen: set[str] = set()
    out: list[ExplicitFactRequest] = []
    for item in found:
        if item.key in seen:
            continue
        seen.add(item.key)
        out.append(item)
    return out


def classify_campaign_intent(
    instruction: str,
    *,
    language: str | None = None,
    project_name: str | None = None,
) -> CampaignIntentResult:
    """Classify campaign intent from a natural brief (TR/EN)."""
    raw = instruction or ""
    t = _norm(raw)
    lang = _detect_language(raw, language)
    signals: list[str] = []
    scores: dict[CampaignIntentKind, float] = {k: 0.0 for k in INTENT_TO_OBJECTIVE}

    def bump(kind: CampaignIntentKind, weight: float, signal: str) -> None:
        scores[kind] = scores.get(kind, 0.0) + weight
        if signal not in signals:
            signals.append(signal)

    # --- Investment / financial ---
    if any(
        k in t
        for k in (
            "yatirimci",
            "yatırımcı",
            "yatirim",
            "yatırım",
            "investor",
            "investment",
            "invest ",
            "invest in",
        )
    ):
        bump("investment", 4.0, "investor_language")
    if any(k in t for k in ("roi", "irr", "getiri", "return", "yield", "hedef getiri")):
        bump("investment", 3.5, "return_language")
    if any(k in t for k in ("minimum yatirim", "minimum yatırım", "min investment", "entry")):
        bump("investment", 2.5, "entry_ticket")
    if any(k in t for k in ("kira gelir", "rental income", "rental yield", "kira getiri")):
        bump("rental_income", 4.5, "rental_income")
        bump("investment", 1.5, "rental_as_investment")
    if any(k in t for k in ("value prop", "değer öner", "deger oner", "value proposition")):
        bump("value_proposition", 3.5, "value_proposition")

    # --- Location / neighborhood ---
    if any(
        k in t
        for k in (
            "lokasyon",
            "location",
            "konum",
            "merkezi",
            "central",
            "adres avantaj",
            "lokasyon avantaj",
        )
    ):
        bump("location", 4.0, "location_language")
    if any(k in t for k in ("washington", "dc", "d.c")):
        bump("location", 1.5, "city_named")
    if any(k in t for k in ("neighborhood", "mahalle", "district", "corridor")):
        bump("neighborhood", 4.0, "neighborhood_language")
        bump("location", 1.5, "neighborhood_as_location")

    # --- Architecture / amenities / lifestyle ---
    if any(
        k in t
        for k in (
            "mimari",
            "architecture",
            "architectural",
            "facade",
            "façade",
            "malzeme",
            "materiality",
            "design language",
        )
    ):
        bump("architecture", 4.5, "architecture_language")
    if any(k in t for k in ("amenit", "spa", "pool", "rooftop", "lobby", "olanak")):
        bump("amenities", 4.0, "amenities_language")
    if any(k in t for k in ("yasam", "yaşam", "lifestyle", "daily living", "city living")):
        bump("lifestyle", 3.5, "lifestyle_language")

    # --- Launch / availability / awareness / construction ---
    if any(k in t for k in ("lansman", "launch", "opening", "introducing", "tanitim", "tanıtım")):
        bump("launch", 4.0, "launch_language")
    if any(k in t for k in ("availability", "available", "musait", "müsait", "units left", "kalan daire")):
        bump("availability", 3.5, "availability_language")
    if any(k in t for k in ("construction", "insaat", "inşaat", "progress", "ilerleme", "şantiye")):
        bump("construction_progress", 4.0, "construction_language")
    if any(k in t for k in ("project awareness", "proje farkindalik", "proje farkındalık", "brand awareness")):
        bump("project_awareness", 3.5, "awareness_language")
    if any(k in t for k in ("tanit", "promote", "promotion", "genel", "overview", "introduce", "project overview", "proje ozeti", "proje özeti")):
        bump("generic_project_promotion", 1.5, "generic_promotion")
    if any(k in t for k in ("project overview", "proje ozeti", "proje özeti", "overview of the project")):
        bump("project_awareness", 3.5, "project_overview")

    # Soft defaults when only project + premium post is asked
    if max(scores.values()) < 1.0:
        if project_name and _norm(project_name) in t:
            bump("generic_project_promotion", 1.0, "project_named_only")
        else:
            bump("generic_project_promotion", 0.5, "fallback_generic")

    # Prefer more specific intents when tied
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    campaign_intent = ranked[0][0]
    top_score = ranked[0][1]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    confidence = min(0.98, 0.45 + top_score / 8.0 + (0.1 if top_score - second >= 1.5 else 0.0))

    objective = INTENT_TO_OBJECTIVE[campaign_intent]
    asset = INTENT_TO_ASSET[campaign_intent]

    platform = "instagram"
    if "linkedin" in t:
        platform = "linkedin"
    elif "facebook" in t:
        platform = "facebook"
    elif re.search(r"\bx\b|twitter", t):
        platform = "x"

    format_preset = "square"
    if any(k in t for k in ("story", "hikaye", "hikayesi")):
        format_preset = "story"
    elif any(k in t for k in ("portrait", "dikey", "4:5", "4/5")):
        format_preset = "portrait"
    elif any(k in t for k in ("landscape", "yatay")):
        format_preset = "landscape"
    elif any(k in t for k in ("reel", "reels")):
        format_preset = "reelsCover"
    elif any(k in t for k in ("kare", "square", "1:1", "1/1")):
        format_preset = "square"

    tone = "premium" if any(k in t for k in ("premium", "luks", "lüks", "luxury", "quiet luxury")) else "professional"
    audience = "investors" if objective == "investment" else "general"

    key_message = ""
    if campaign_intent == "location":
        key_message = "central location"
    elif campaign_intent in {"investment", "value_proposition"}:
        key_message = "investment opportunity"
    elif campaign_intent == "rental_income":
        key_message = "rental income potential"
    elif campaign_intent == "architecture":
        key_message = "architectural character"
    elif campaign_intent == "neighborhood":
        key_message = "neighborhood advantage"
    elif project_name:
        key_message = project_name

    cta_hint: str | None = None
    if objective == "investment":
        from investhome_api.services.social_design_engine.localization import choose_investment_cta

        cta_hint = choose_investment_cta(lang)
    elif objective == "location":
        cta_hint = "Explore the Neighborhood" if lang == "en" else "Mahalleyi keşfet"
    elif any(k in t for k in ("tur", "tour", "randevu")):
        cta_hint = "Schedule a private tour" if lang == "en" else "Özel tur planla"

    facts = extract_campaign_facts(raw)
    explicit = detect_explicit_financial_requests(raw)

    return CampaignIntentResult(
        campaign_intent=campaign_intent,
        marketing_objective=objective,
        confidence=round(confidence, 3),
        audience=audience,
        tone=tone,
        language=lang,
        platform=platform,
        format_preset=format_preset,
        asset_preference=asset,
        key_message=key_message,
        cta_hint=cta_hint,
        signals=signals,
        explicit_fact_requests=explicit,
        user_supplied_financial=[f.display for f in facts],
    )


LOCATION_RETRIEVAL_TERMS = (
    "location",
    "neighborhood",
    "district",
    "city",
    "central",
    "metro",
    "corridor",
)


def retrieval_query_for_campaign(
    instruction: str,
    *,
    campaign_intent: CampaignIntentKind,
    city: str | None = None,
    state: str | None = None,
    country: str | None = None,
    project_name: str | None = None,
) -> str:
    """Expand the RAG query with verified place terms so location briefs still retrieve.

    The user prompt may say only 'lokasyon avantajı' without naming the city.
    Never add prices, yields, or other financial figures.
    """
    parts = [(instruction or "").strip()]
    if campaign_intent in {"location", "neighborhood"}:
        parts.extend(LOCATION_RETRIEVAL_TERMS)
        for val in (project_name, city, state, country):
            token = (val or "").strip()
            if token and token not in parts:
                parts.append(token)
    return " ".join(p for p in parts if p)


def campaign_intent_to_dict(result: CampaignIntentResult) -> dict[str, Any]:
    payload = asdict(result)
    return payload


def apply_campaign_intent_to_generation_intent(result: CampaignIntentResult, gen_intent: Any) -> Any:
    """Overlay campaign intelligence onto the existing GenerationIntent."""
    gen_intent.marketing_objective = result.marketing_objective
    gen_intent.audience = result.audience
    gen_intent.tone = result.tone
    gen_intent.language = result.language
    gen_intent.platform = result.platform
    gen_intent.format_preset = result.format_preset
    gen_intent.asset_preference = result.asset_preference
    gen_intent.key_message = result.key_message
    gen_intent.cta_hint = result.cta_hint
    gen_intent.requested_financial_figures = list(
        dict.fromkeys(list(gen_intent.requested_financial_figures or []) + result.user_supplied_financial)
    )
    return gen_intent
