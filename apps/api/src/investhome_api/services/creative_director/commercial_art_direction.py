"""Commercial information must be art-directed. Premium still sells."""

from __future__ import annotations

from typing import Any

HIERARCHY = (
    "CAMPAIGN_IDEA",
    "PROJECT_VALUE",
    "OFFER",
    "PRICE_UNIT",
    "CTA",
    "BRAND",
)

FORBIDDEN_COMMERCIAL_DEVICES = (
    "cards",
    "badges",
    "dashboard boxes",
    "property-listing UI",
    "KPI tiles",
    "pills around every fact",
    "floating information panel",
    "three boxes plus photograph",
)

VIEWER_QUESTIONS = (
    "WHAT IS THIS?",
    "WHY SHOULD I CARE?",
    "WHAT IS THE OFFER?",
    "WHAT DO I DO NEXT?",
)


def commercial_art_direction_rules() -> dict[str, Any]:
    return {
        "schema": "CommercialArtDirectionV1",
        "hierarchy": list(HIERARCHY),
        "viewer_learns_in_order": list(VIEWER_QUESTIONS),
        "forbidden_devices": list(FORBIDDEN_COMMERCIAL_DEVICES),
        "principle": (
            "The creative cannot become an art-school poster that forgets the offer. "
            "Price, unit, and CTA are actors in the composition, not a listing footer."
        ),
        "art_direct": [
            "price as designed numerals inside the idea",
            "offer as a spoken line or a single accent, never a medallion",
            "CTA as typographic close",
            "brand as composed signature",
        ],
        "status": "READY",
    }
