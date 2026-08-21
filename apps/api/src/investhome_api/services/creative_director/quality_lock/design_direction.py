"""Design Direction for finished-ad provider — mood & hierarchy, not pixel layout."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class DesignDirection:
    visual_mood: str
    hierarchy: str
    typography_character: str
    composition_direction: str
    image_treatment: str
    contrast: str
    brand_presence: str
    cta_importance: str
    information_density: str
    premium_level: str
    creative_freedom: str = (
        "Full creative freedom for placement — no forced left panel, bottom band, "
        "badge grid, icon row, or card stack. Each ad may look different."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_MOOD: dict[str, str] = {
    "sales_offer": "Premium sales urgency with editorial restraint",
    "price_campaign": "Luxury offer drama — clear, high-contrast, photograph-led",
    "investment": "Confident, data-aware luxury without brochure clutter",
    "location": "Urban editorial — place-led, airy, destination feel",
    "lifestyle": "Quiet luxury sanctuary — warm interior atmosphere",
    "amenities": "Elevated living features — selective, not checklist-heavy",
    "architecture": "Material and form first — architectural photography mood",
    "project_brand": "Brand-forward, minimal copy, strong mark presence",
    "launch": "Launch energy with refined typography",
    "educational": "Clear, calm, instructional editorial",
    "event": "Invitational, time-bound, elegant",
    "general_awareness": "Memorable single-image brand impression",
}


def build_design_direction(
    *,
    campaign_intent: str,
    strategy: dict[str, Any] | None = None,
    density: str = "medium",
    language: str = "tr",
    creative_freedom_level: int | None = None,
) -> DesignDirection:
    """Provider-facing art direction cues derived from intent + CD strategy."""
    strategy = strategy or {}
    intent = str(campaign_intent or "general_awareness").strip().lower()
    mood = _MOOD.get(intent, _MOOD["general_awareness"])
    visual = str(strategy.get("visual_direction") or "").strip()
    composition = str(strategy.get("composition_direction") or "").strip()
    typography = str(strategy.get("typography_direction") or "").strip()
    tone = str(strategy.get("tone") or "premium").strip()

    hierarchy = (
        "One dominant read in the first 2 seconds; secondary lines quieter; CTA actionable; "
        "logo present once."
    )
    if intent in {"price_campaign", "sales_offer"}:
        hierarchy = (
            "Price/offer may lead if that is the campaign intent; otherwise headline leads. "
            "Never compete with three equal-weight messages."
        )
    elif intent == "location":
        hierarchy = "Location name / advantage leads; supporting place cues secondary; CTA clear."
    elif intent in {"lifestyle", "amenities"}:
        hierarchy = "Living feeling leads; features as short support only; CTA soft but clear."

    dens = density if density in {"sparse", "medium", "rich"} else "medium"
    premium = "high" if "premium" in tone.lower() or "lüks" in tone.lower() or "luxury" in tone.lower() else "elevated"

    level = 1 if creative_freedom_level is None else int(creative_freedom_level)
    if level <= 0:
        freedom = (
            f"Language={language}. LEVEL 0 STRICT architectural truth — crop/position/typography/"
            "gradient/CTA/graphics only. NEVER regenerate or invent project architecture, facade, "
            "Addition, massing, or Historic+Addition relationships."
        )
        image_treatment = (
            "Immutable architecture photograph — preserve source building pixels. "
            "Controlled grade only; do not redesign facade or site relationship."
        )
    elif level == 1:
        freedom = (
            f"Language={language}. LEVEL 1 CONTROLLED — approved interiors only. "
            "Placement freedom without forced panels; do not invent room geometry."
        )
        image_treatment = (
            "Preserve real project interior architecture/photography — enhance atmosphere, do not redesign. "
            "Subtle grade toward premium RE editorial."
        )
    else:
        freedom = (
            f"Language={language}. LEVEL 2 CREATIVE for lifestyle/place imagery — no forced left panel, "
            "bottom band, badge grid, icon row, or card stack. Never invent project architectural facts "
            "or present neighbor buildings as The Temple."
        )
        image_treatment = (
            "Preserve supplied photography. Do not invent The Temple exterior or Addition. "
            "Subtle grade toward premium RE editorial."
        )

    return DesignDirection(
        visual_mood=visual or mood,
        hierarchy=hierarchy,
        typography_character=typography
        or "Expressive display for the primary line; restrained sans for support; high contrast CTA",
        composition_direction=composition
        or (
            "Photograph-led full-bleed composition with intentional negative space for type. "
            "No mandatory side or bottom panels."
        ),
        image_treatment=image_treatment,
        contrast="High readability for primary message and CTA against the locked photograph",
        brand_presence="One verified project logo lockup — never invent or duplicate",
        cta_importance="Single clear CTA; visible and actionable, not tiny footer text",
        information_density=dens,
        premium_level=premium,
        creative_freedom=freedom,
    )
