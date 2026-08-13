"""Creative Intent — how the post should communicate, not only campaign keywords.

Extends campaign_intent.py rather than replacing it. Campaign intent still
governs fact selection / Financial Claim Guard; Creative Intent decides the
communication job before composition.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from investhome_api.services.social_design_engine.campaign_intent import (
    CampaignIntentKind,
    CampaignIntentResult,
)

CreativeIntentKind = Literal[
    "LOCATION",
    "INVESTMENT",
    "ARCHITECTURE",
    "LIFESTYLE",
    "BRAND",
    "ANNOUNCEMENT",
    "EDUCATIONAL",
]

CAMPAIGN_TO_CREATIVE: dict[CampaignIntentKind, CreativeIntentKind] = {
    "investment": "INVESTMENT",
    "rental_income": "INVESTMENT",
    "value_proposition": "INVESTMENT",
    "location": "LOCATION",
    "neighborhood": "LOCATION",
    "architecture": "ARCHITECTURE",
    "lifestyle": "LIFESTYLE",
    "amenities": "LIFESTYLE",
    "launch": "ANNOUNCEMENT",
    "availability": "ANNOUNCEMENT",
    "project_awareness": "BRAND",
    "generic_project_promotion": "BRAND",
    "construction_progress": "EDUCATIONAL",
}

AUDIENCE_FOR_INTENT: dict[CreativeIntentKind, str] = {
    "LOCATION": "residents_and_relocators",
    "INVESTMENT": "investors",
    "ARCHITECTURE": "design_conscious_buyers",
    "LIFESTYLE": "aspirational_residents",
    "BRAND": "general_awareness",
    "ANNOUNCEMENT": "launch_audience",
    "EDUCATIONAL": "informed_considerers",
}


@dataclass
class CreativeIntentResult:
    creative_intent: CreativeIntentKind
    campaign_intent: CampaignIntentKind
    confidence: float
    audience: str
    signals: list[str] = field(default_factory=list)
    semantic: bool = True


def _norm(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text or "")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    folded = folded.replace("ı", "i").replace("İ", "i")
    return folded.strip().lower()


def classify_creative_intent(
    instruction: str,
    *,
    campaign: CampaignIntentResult | None = None,
    project_name: str | None = None,
) -> CreativeIntentResult:
    """Semantic communication intent. Campaign taxonomy is a prior, not a 1:1 map."""
    raw = instruction or ""
    t = _norm(raw)
    signals: list[str] = []
    scores: dict[CreativeIntentKind, float] = {
        "LOCATION": 0.0,
        "INVESTMENT": 0.0,
        "ARCHITECTURE": 0.0,
        "LIFESTYLE": 0.0,
        "BRAND": 0.0,
        "ANNOUNCEMENT": 0.0,
        "EDUCATIONAL": 0.0,
    }

    def bump(kind: CreativeIntentKind, weight: float, signal: str) -> None:
        scores[kind] = scores.get(kind, 0.0) + weight
        if signal not in signals:
            signals.append(signal)

    if campaign is not None:
        mapped = CAMPAIGN_TO_CREATIVE.get(campaign.campaign_intent, "BRAND")
        bump(mapped, 3.2 + min(1.6, campaign.confidence), f"campaign:{campaign.campaign_intent}")

    # LOCATION — place, belonging, centrality (not just the word "location")
    if any(
        k in t
        for k in (
            "lokasyon",
            "location",
            "konum",
            "merkezi",
            "central",
            "neighborhood",
            "mahalle",
            "adres avantaj",
            "belongs to",
            "in the city",
            "city living",
            "sehir hayati",
            "şehir hayatı",
        )
    ):
        bump("LOCATION", 2.4, "place_language")
    if any(k in t for k in ("washington", "columbia heights", "district")):
        bump("LOCATION", 1.2, "named_place")

    # INVESTMENT — capital allocation, not lifestyle luxury
    if any(
        k in t
        for k in (
            "yatirimci",
            "yatırımcı",
            "investor",
            "investment",
            "yatirim",
            "yatırım",
            "roi",
            "irr",
            "getiri",
            "yield",
            "minimum yatirim",
            "minimum yatırım",
        )
    ):
        bump("INVESTMENT", 2.8, "capital_language")

    # ARCHITECTURE — form, facade, craft (not inventory)
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
            "form of",
            "karakter",
            "silhouette",
            "craft",
        )
    ):
        bump("ARCHITECTURE", 2.8, "form_language")

    # LIFESTYLE — lived experience without inventing amenities
    if any(
        k in t
        for k in (
            "yasam tarzi",
            "yaşam tarzı",
            "lifestyle",
            "daily living",
            "how it feels",
            "atmosphere",
            "atmosphere",
            "residences life",
            "hayat",
        )
    ):
        bump("LIFESTYLE", 2.4, "lived_experience")
    if any(k in t for k in ("amenit", "spa", "pool", "rooftop", "lobby")):
        bump("LIFESTYLE", 1.4, "amenity_mention")

    # BRAND — identity, signature, presence
    if any(
        k in t
        for k in (
            "marka",
            "brand",
            "identity",
            "imza",
            "signature",
            "awareness",
            "farkindalik",
            "farkındalık",
            "introduce the project",
            "projeyi tanit",
            "projeyi tanıt",
        )
    ):
        bump("BRAND", 2.6, "identity_language")

    # ANNOUNCEMENT — launch, now, arrival
    if any(
        k in t
        for k in (
            "lansman",
            "launch",
            "opening",
            "introducing",
            "arrives",
            "now open",
            "duyuru",
            "announce",
        )
    ):
        bump("ANNOUNCEMENT", 2.6, "launch_language")

    # EDUCATIONAL — explain, why, how (not a spec dump)
    if any(
        k in t
        for k in (
            "neden",
            "why invest",
            "why this",
            "how ",
            "explain",
            "ogren",
            "öğren",
            "rehber",
            "guide",
            "what makes",
            "anlat",
            "bilgilendir",
        )
    ):
        bump("EDUCATIONAL", 2.5, "explain_language")

    if max(scores.values()) < 0.8:
        if project_name and _norm(project_name) in t:
            bump("BRAND", 0.9, "project_named_only")
        else:
            bump("BRAND", 0.4, "fallback_brand")

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    intent = ranked[0][0]
    top = ranked[0][1]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    confidence = min(0.98, 0.42 + top / 9.0 + (0.12 if top - second >= 1.4 else 0.0))

    campaign_kind: CampaignIntentKind = (
        campaign.campaign_intent if campaign is not None else "generic_project_promotion"
    )
    audience = AUDIENCE_FOR_INTENT[intent]
    if campaign is not None and campaign.audience:
        audience = campaign.audience if intent == "INVESTMENT" else audience

    return CreativeIntentResult(
        creative_intent=intent,
        campaign_intent=campaign_kind,
        confidence=round(confidence, 3),
        audience=audience,
        signals=signals,
        semantic=True,
    )


def creative_intent_to_dict(result: CreativeIntentResult) -> dict[str, Any]:
    return asdict(result)


def is_explicit_redesign(instruction: str) -> bool:
    """EDIT stays localized unless the user explicitly asks to redesign the post."""
    t = _norm(instruction)
    phrases = (
        "bu postu tamamen yeniden tasarla",
        "postu tamamen yeniden tasarla",
        "tamamen yeniden tasarla",
        "from scratch",
        "redesign this post",
        "completely redesign",
        "yeniden tasarla",
        "full redesign",
        "start over",
        "bastan tasar",
        "baştan tasar",
    )
    if any(p in t for p in phrases):
        # "yeniden tasarla" alone is redesign; "başlığı yeniden yaz" is copy, not layout.
        if re.search(r"(baslik|başlık|headline|cta|buton|metin).{0,16}(yeniden yaz|rewrite)", t):
            return False
        return True
    return False
