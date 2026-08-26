"""AI-first Master Creative revision classifier.

Classifies natural-language revision commands. Does not execute revisions.
Does not call PRICE_BLOCK_ONLY, hide plates, or pixel surgery.
"""

from __future__ import annotations

from typing import Any, Literal

RevisionIntent = Literal[
    "VISUAL_REPLACE_ONLY",
    "PRICE_EDIT_ONLY",
    "LOGO_EDIT_ONLY",
    "CREATIVE_RECOMPOSE",
]

_LOCKS: dict[str, tuple[str, ...]] = {
    "VISUAL_REPLACE_ONLY": (
        "headline",
        "prices",
        "discount",
        "logo",
        "cta",
        "typography",
        "colors",
        "spacing",
        "decorative_treatment",
        "overall_layout",
    ),
    "PRICE_EDIT_ONLY": (
        "hero_visual",
        "crop",
        "headline",
        "discount",
        "logo",
        "cta",
        "typography_outside_price",
        "overall_composition",
    ),
    "LOGO_EDIT_ONLY": (
        "hero_visual",
        "crop",
        "headline",
        "prices",
        "discount",
        "cta",
        "typography",
        "overall_layout",
    ),
    "CREATIVE_RECOMPOSE": (),
}


def _norm(text: str) -> str:
    return (
        (text or "")
        .replace("İ", "i")
        .replace("I", "ı")
        .lower()
    )


def classify_revision_command(instruction: str) -> dict[str, Any]:
    """Map a user revision sentence to a locked-revision intent.

    Fail-closed later: if the provider cannot apply the op locally, revision
    must fail rather than silently redesign the master.
    """
    raw = _norm(instruction)
    lock_rest = any(
        tok in raw
        for tok in (
            "baska hicbir seyi degistirme",
            "başka hiçbir şeyi değiştirme",
            "baska hicbir sey",
            "nothing else",
            "don't change anything else",
            "do not change anything else",
        )
    )
    visual = any(
        tok in raw
        for tok in (
            "görsel yerine",
            "gorsel yerine",
            "dış cephe",
            "dis cephe",
            "exterior",
            "interior kullan",
            "bu görsel",
            "bu gorsel",
            "fotoğrafı değiştir",
            "fotografi degistir",
            "render",
        )
    )
    price = any(
        tok in raw
        for tok in (
            "fiyat",
            "price",
            "usd",
            "liste",
            "438",
            "675",
            "üzerini çiz",
            "uzerini ciz",
            "strikethrough",
        )
    )
    logo = any(tok in raw for tok in ("logo", "logoyu"))
    recompose = any(
        tok in raw
        for tok in (
            "daha lüks",
            "daha luks",
            "dramatik",
            "yeniden tasarla",
            "recompose",
            "redesign",
            "daha premium",
        )
    )

    intent: RevisionIntent
    if visual and (lock_rest or not price):
        intent = "VISUAL_REPLACE_ONLY"
    elif price and (lock_rest or not visual):
        intent = "PRICE_EDIT_ONLY"
    elif logo and not visual and not price:
        intent = "LOGO_EDIT_ONLY"
    elif recompose:
        intent = "CREATIVE_RECOMPOSE"
    elif visual:
        intent = "VISUAL_REPLACE_ONLY"
    elif price:
        intent = "PRICE_EDIT_ONLY"
    elif logo:
        intent = "LOGO_EDIT_ONLY"
    else:
        intent = "CREATIVE_RECOMPOSE"

    mutable = {
        "VISUAL_REPLACE_ONLY": ("hero_visual",),
        "PRICE_EDIT_ONLY": ("price_content",),
        "LOGO_EDIT_ONLY": ("logo_geometry",),
        "CREATIVE_RECOMPOSE": ("creative_direction",),
    }[intent]
    return {
        "intent": intent,
        "mutable": list(mutable),
        "locked": list(_LOCKS[intent]),
        "fail_closed": True,
        "pixel_surgery_allowed": False,
        "provider_redesign_allowed": intent == "CREATIVE_RECOMPOSE",
        "executed": False,
    }
