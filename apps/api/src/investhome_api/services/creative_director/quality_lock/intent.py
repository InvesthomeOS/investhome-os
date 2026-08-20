"""Campaign Intent classification for Creative Director Quality Lock.

Taxonomy is CD-facing (sales_offer, price_campaign, …). Distinct from the older
social_design_engine campaign_intent kinds used by Claim Guard / fact governance.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from investhome_api.services.social_design_engine.generation import AssetPreference

CDCampaignIntentKind = Literal[
    "sales_offer",
    "price_campaign",
    "investment",
    "location",
    "lifestyle",
    "amenities",
    "architecture",
    "project_brand",
    "launch",
    "educational",
    "event",
    "general_awareness",
]

CD_CAMPAIGN_INTENTS: tuple[CDCampaignIntentKind, ...] = (
    "sales_offer",
    "price_campaign",
    "investment",
    "location",
    "lifestyle",
    "amenities",
    "architecture",
    "project_brand",
    "launch",
    "educational",
    "event",
    "general_awareness",
)

INTENT_TO_ASSET: dict[CDCampaignIntentKind, AssetPreference] = {
    "sales_offer": "premium_hero",
    "price_campaign": "premium_hero",
    "investment": "premium_hero",
    "location": "neighborhood",
    "lifestyle": "interior",
    "amenities": "interior",
    "architecture": "exterior",
    "project_brand": "premium_hero",
    "launch": "premium_hero",
    "educational": "any",
    "event": "premium_hero",
    "general_awareness": "premium_hero",
}

# Map CD intents → legacy social_design_engine kinds (Claim Guard / retrieval).
CD_TO_LEGACY_INTENT: dict[CDCampaignIntentKind, str] = {
    "sales_offer": "launch",
    "price_campaign": "launch",
    "investment": "investment",
    "location": "location",
    "lifestyle": "lifestyle",
    "amenities": "amenities",
    "architecture": "architecture",
    "project_brand": "project_awareness",
    "launch": "launch",
    "educational": "generic_project_promotion",
    "event": "launch",
    "general_awareness": "generic_project_promotion",
}


def _norm(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text or "")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    folded = folded.replace("ı", "i").replace("İ", "i")
    return folded.strip().lower()


@dataclass
class CampaignQualityIntent:
    campaign_intent: CDCampaignIntentKind
    legacy_campaign_intent: str
    confidence: float
    language: str
    asset_preference: AssetPreference
    primary_message_focus: str
    signals: list[str] = field(default_factory=list)
    density: str = "medium"  # sparse | medium | rich

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def intent_to_asset_preference(intent: CDCampaignIntentKind | str) -> AssetPreference:
    key = str(intent or "general_awareness").strip().lower()
    if key in INTENT_TO_ASSET:
        return INTENT_TO_ASSET[key]  # type: ignore[index]
    return "premium_hero"


def is_price_led_intent(intent: str | None) -> bool:
    return str(intent or "").strip().lower() in {
        "sales_offer",
        "price_campaign",
        "launch",
    }


def is_visual_lifestyle_intent(intent: str | None) -> bool:
    return str(intent or "").strip().lower() in {
        "lifestyle",
        "amenities",
    }


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
    if re.search(r"[çğıöşü]", instruction or ""):
        return "tr"
    return "en"


def classify_cd_campaign_intent(
    instruction: str,
    *,
    language: str | None = None,
    project_name: str | None = None,
    project_knowledge: str | None = None,
    has_price_pair: bool = False,
) -> CampaignQualityIntent:
    """Classify CD campaign intent from brief + optional project knowledge."""
    raw = instruction or ""
    knowledge = project_knowledge or ""
    t = _norm(f"{raw}\n{knowledge}")
    lang = _detect_language(raw, language)
    signals: list[str] = []
    scores: dict[CDCampaignIntentKind, float] = {k: 0.0 for k in CD_CAMPAIGN_INTENTS}

    def bump(kind: CDCampaignIntentKind, weight: float, signal: str) -> None:
        scores[kind] = scores.get(kind, 0.0) + weight
        if signal not in signals:
            signals.append(signal)

    # --- Price / sales ---
    if has_price_pair or bool(
        re.search(r"\$\s*\d[\d,]*(?:\.\d+)?\s*(?:→|->|to|dan|den)?\s*\$\s*\d", t)
        or re.search(r"\d[\d.,]*\s*(?:→|->)\s*\d", t)
    ):
        bump("price_campaign", 5.0, "price_pair")
        bump("sales_offer", 3.5, "price_pair_sales")
    if any(
        k in t
        for k in (
            "lansman fiyat",
            "launch price",
            "indirim",
            "discount",
            "fiyat avantaj",
            "price advantage",
            "sales offer",
            "satis teklif",
            "satış teklif",
            "kampanya fiyat",
        )
    ):
        bump("price_campaign", 4.5, "price_campaign_language")
        bump("sales_offer", 3.0, "sales_language")
    if any(k in t for k in ("unit 204", "daire", "unit ", "lansman", "launch")):
        bump("launch", 2.5, "unit_or_launch")
        bump("sales_offer", 1.5, "unit_sales")

    # --- Investment ---
    if any(
        k in t
        for k in (
            "yatirim",
            "yatırım",
            "investor",
            "investment",
            "roi",
            "irr",
            "getiri",
            "yield",
        )
    ):
        bump("investment", 4.5, "investment_language")

    # --- Location ---
    if any(
        k in t
        for k in (
            "lokasyon",
            "location",
            "konum",
            "adams morgan",
            "neighborhood",
            "mahalle",
            "merkezi",
            "central",
            "lokasyon avantaj",
            "konum avantaj",
            "streetscape",
        )
    ):
        bump("location", 5.0, "location_language")

    # --- Lifestyle / amenities / architecture ---
    if any(
        k in t
        for k in (
            "yasam",
            "yaşam",
            "lifestyle",
            "ic mekan",
            "iç mekan",
            "interior living",
            "sakin",
            "sanctuary",
            "siginak",
            "sığınak",
        )
    ):
        bump("lifestyle", 4.0, "lifestyle_language")
    if any(
        k in t
        for k in (
            "ozellik",
            "özellik",
            "amenit",
            "spa",
            "pool",
            "rooftop",
            "lobby",
            "katalog",
            "catalog",
            "feature",
            "olanak",
        )
    ):
        bump("amenities", 4.5, "amenities_or_features")
        bump("lifestyle", 2.0, "features_as_lifestyle")
    if any(
        k in t
        for k in (
            "mimari",
            "architecture",
            "facade",
            "façade",
            "cephe",
            "architectural",
        )
    ):
        bump("architecture", 4.5, "architecture_language")

    # --- Brand / launch / educational / event / awareness ---
    if any(k in t for k in ("marka", "brand", "logo", "project brand", "kimlik")):
        bump("project_brand", 3.5, "brand_language")
    if any(k in t for k in ("lansman", "launch", "opening", "introducing", "tanitim", "tanıtım")):
        bump("launch", 3.5, "launch_language")
    if any(k in t for k in ("egitim", "eğitim", "educational", "nasil", "nasıl", "guide", "rehber")):
        bump("educational", 4.0, "educational_language")
    if any(k in t for k in ("etkinlik", "event", "open house", "acilis", "açılış", "davet")):
        bump("event", 4.0, "event_language")
    if any(
        k in t
        for k in (
            "farkindalik",
            "farkındalık",
            "awareness",
            "genel",
            "overview",
            "promote",
            "tanit",
        )
    ):
        bump("general_awareness", 2.0, "awareness_language")

    if max(scores.values()) < 1.0:
        if project_name and _norm(project_name) in t:
            bump("general_awareness", 1.0, "project_named_only")
        else:
            bump("general_awareness", 0.5, "fallback_general")

    # Price pair without strong location/lifestyle should win as price_campaign.
    if scores["price_campaign"] >= 4.0 and scores["location"] < 4.0 and scores["lifestyle"] < 3.5:
        scores["price_campaign"] += 1.5

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    campaign_intent = ranked[0][0]
    top_score = ranked[0][1]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    confidence = min(0.98, 0.45 + top_score / 8.0 + (0.1 if top_score - second >= 1.5 else 0.0))

    focus_map: dict[CDCampaignIntentKind, str] = {
        "sales_offer": "sales offer / commercial hook",
        "price_campaign": "price advantage / launch offer",
        "investment": "investment opportunity",
        "location": "location advantage",
        "lifestyle": "lifestyle / living experience",
        "amenities": "project features / amenities",
        "architecture": "architectural character",
        "project_brand": "project brand presence",
        "launch": "launch opportunity",
        "educational": "educational clarity",
        "event": "event invitation",
        "general_awareness": "project awareness",
    }

    if campaign_intent in {"educational", "general_awareness", "project_brand"}:
        density = "sparse"
    elif campaign_intent in {"price_campaign", "sales_offer", "amenities"}:
        density = "medium"
    else:
        density = "medium"

    return CampaignQualityIntent(
        campaign_intent=campaign_intent,
        legacy_campaign_intent=CD_TO_LEGACY_INTENT[campaign_intent],
        confidence=round(confidence, 3),
        language=lang,
        asset_preference=INTENT_TO_ASSET[campaign_intent],
        primary_message_focus=focus_map[campaign_intent],
        signals=signals,
        density=density,
    )
