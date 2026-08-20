"""Message Strategy — ONE AD = ONE PRIMARY MESSAGE, density by intent."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from investhome_api.services.creative_director.quality_lock.intent import (
    CDCampaignIntentKind,
    is_price_led_intent,
)
from investhome_api.services.creative_director.quality_lock.simplicity import (
    simplicity_caps_for_intent,
)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _s(value: Any) -> str:
    return str(value or "").strip()


@dataclass
class MessageStrategy:
    big_idea: str
    primary_message: str
    sales_attention_hook: str
    hero_headline: str
    supporting_messages: list[str] = field(default_factory=list)
    cta: str = ""
    emotional_angle: str = ""
    commercial_priority: list[str] = field(default_factory=list)
    information_hierarchy: list[str] = field(default_factory=list)
    one_ad_one_message: bool = True
    density: str = "medium"
    campaign_intent: str = "general_awareness"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_EMOTIONAL_BY_INTENT: dict[str, str] = {
    "sales_offer": "urgency with premium restraint — opportunity without desperation",
    "price_campaign": "confident advantage — clear value, calm luxury",
    "investment": "assured opportunity — clarity and trust",
    "location": "belonging to place — urban pulse with elevated calm",
    "lifestyle": "sanctuary living — quiet luxury, daily ease",
    "amenities": "elevated daily rituals — features as lifestyle, not a checklist",
    "architecture": "craft and character — material honesty, timeless form",
    "project_brand": "brand gravity — quiet confidence",
    "launch": "first-mover excitement — refined, not loud",
    "educational": "clarity and guidance — helpful without sales pressure",
    "event": "invitation and anticipation",
    "general_awareness": "memorable presence — one strong impression",
}


def _commercial_priority_for_intent(
    intent: str,
    *,
    strategy: dict[str, Any],
    pricing: dict[str, Any],
) -> list[str]:
    presentation = _as_dict(pricing.get("price_presentation"))
    has_price = bool(presentation.get("list") and presentation.get("offer"))
    if is_price_led_intent(intent) and has_price:
        return [
            "price hook / launch offer",
            "primary sales message",
            "product / unit opportunity",
            "call to action",
            "brand presence",
        ]
    if intent == "location":
        return [
            "location advantage",
            "primary sales message",
            "neighborhood proof",
            "call to action",
            "brand presence",
        ]
    if intent in {"lifestyle", "amenities"}:
        return [
            "lifestyle / living experience",
            "primary sales message",
            "feature callouts",
            "call to action",
            "brand presence",
        ]
    if intent == "architecture":
        return [
            "architectural character",
            "primary sales message",
            "call to action",
            "brand presence",
        ]
    if intent == "investment":
        return [
            "investment opportunity",
            "primary sales message",
            "verified proof only",
            "call to action",
            "brand presence",
        ]
    # Default / brand / awareness
    first = _s(strategy.get("first_2_seconds")) or "primary sales message"
    return [
        first if len(first) < 80 else "primary sales message",
        "creative idea / brand story",
        "call to action",
        "brand presence",
    ]


def build_message_strategy(
    *,
    campaign_intent: CDCampaignIntentKind | str,
    strategy: dict[str, Any],
    campaign_copy: dict[str, Any] | None = None,
    pricing: dict[str, Any] | None = None,
    texts: dict[str, str] | None = None,
    art_direction: dict[str, Any] | None = None,
) -> MessageStrategy:
    """Assemble CD message strategy before production. Caps supporting by intent."""
    copy = campaign_copy or {}
    price = pricing or {}
    tx = texts or {}
    art = art_direction or {}
    intent = str(campaign_intent or "general_awareness").strip().lower()
    caps = simplicity_caps_for_intent(intent)

    big_idea = _s(copy.get("big_idea") or strategy.get("big_idea") or strategy.get("concept") or tx.get("headline"))
    hero = _s(
        tx.get("headline")
        or tx.get("hero")
        or copy.get("hero_message")
        or strategy.get("hero_message")
        or big_idea
    )
    hook = _s(
        tx.get("sales_hook")
        or copy.get("sales_hook")
        or strategy.get("sales_hook")
        or tx.get("eyebrow")
    )
    primary = _s(strategy.get("first_2_seconds") or hero or big_idea or hook)
    cta = _s(tx.get("cta") or copy.get("cta") or strategy.get("cta") or "Detayları İncele")

    support_src = _as_list(copy.get("supporting_messages") or strategy.get("supporting_messages"))
    if tx.get("supporting_callouts"):
        support_src = [x.strip() for x in str(tx["supporting_callouts"]).split("|") if x.strip()] or support_src
    elif tx.get("supporting"):
        # Prefer pipe-split if present; else single supporting line.
        raw_sup = str(tx["supporting"])
        if "|" in raw_sup:
            support_src = [x.strip() for x in raw_sup.split("|") if x.strip()]
        elif raw_sup.strip():
            support_src = [raw_sup.strip()]

    supporting: list[str] = []
    for item in support_src:
        s = _s(item)
        if s and s not in supporting:
            supporting.append(s)
        if len(supporting) >= caps.max_supporting:
            break

    emotional = _s(strategy.get("emotional_angle")) or _EMOTIONAL_BY_INTENT.get(
        intent, _EMOTIONAL_BY_INTENT["general_awareness"]
    )

    commercial = _as_list(art.get("commercial_priority"))
    if not commercial:
        commercial = _commercial_priority_for_intent(intent, strategy=strategy, pricing=price)

    hierarchy = [
        f"1 — PRIMARY: {primary}",
        f"2 — HOOK: {hook}" if hook else "2 — HOOK: (none)",
        f"3 — SUPPORT: {' | '.join(supporting) if supporting else '(none)'}",
        f"4 — CTA: {cta}",
        "5 — BRAND: one real project logo",
    ]

    density = caps.density_label
    return MessageStrategy(
        big_idea=big_idea,
        primary_message=primary,
        sales_attention_hook=hook,
        hero_headline=hero,
        supporting_messages=supporting,
        cta=cta,
        emotional_angle=emotional,
        commercial_priority=[str(x) for x in commercial if str(x).strip()],
        information_hierarchy=hierarchy,
        one_ad_one_message=True,
        density=density,
        campaign_intent=intent,
    )
