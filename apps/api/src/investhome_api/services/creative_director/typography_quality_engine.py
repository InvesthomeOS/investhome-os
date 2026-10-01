"""Typographic quality as a first-class creative system."""

from __future__ import annotations

from typing import Any

HARD_REJECTS = (
    "default centered text",
    "generic luxury serif everywhere",
    "random letter spacing",
    "tiny commercial copy",
    "headline simply placed in empty corner",
    "web-button CTA",
    "fact-card typography",
)

RULES = {
    "headline_authority": (
        "The headline must have optical presence equal to a primary actor, not a caption. "
        "Scale is earned by the idea, not by filling leftover sky."
    ),
    "optical_sizing": (
        "Display sizes must look cut for the canvas. Do not scale a UI font up. "
        "Hairlines that vanish at 4:5 are a fail."
    ),
    "line_breaks": (
        "Break for spoken rhythm and meaning, never for a leftover box width. "
        "A three-word chant may stack; a sentence may not be arbitrarily sliced."
    ),
    "leading": "Leading is atmosphere. Tight chant vs open editorial are different ideas. Do not use app default leading.",
    "tracking": "Tracking is intentional. Random wide tracking on a serif is a reject.",
    "contrast": "Type must win against its actual ground. If the photo is busy, move the ground, not the tracking.",
    "serif_sans_pairing": (
        "Serif and sans may pair when one is display and one is information. "
        "Generic luxury serif on every line is banned."
    ),
    "commercial_number_typography": (
        "Price and unit are designed numerals, not captions. "
        "They may be quieter than the idea, never illegible, never a dashboard tile."
    ),
    "microcopy": "Location, legal, and support lines are composed whispers, not UI labels.",
    "cta_restraint": "CTA is a typographic close, not a website button, pill, or filled rectangle.",
    "text_photo_interaction": (
        "Type either occupies real photographic quiet, a designed field that is part of the idea, "
        "or collides with architecture on purpose. Parking type in a leftover corner fails."
    ),
    "responsive_local_recomposition": (
        "If copy length changes, recompose inside the semantic territory. "
        "Do not distort glyphs to keep old coordinates. Stage 2 COPY_EDIT_ONLY remains locked."
    ),
}


def typography_quality_rules() -> dict[str, Any]:
    return {
        "schema": "TypographicQualityEngineV1",
        "rules": dict(RULES),
        "hard_rejects": list(HARD_REJECTS),
        "status": "READY",
    }


def reject_typography(flags: dict[str, bool] | None = None) -> dict[str, Any]:
    hits = [name for name, on in (flags or {}).items() if on]
    return {
        "schema": "TypographicRejectV1",
        "rejected": bool(hits),
        "hits": hits,
        "hard_rejects": list(HARD_REJECTS),
    }
