"""AI-first Master Creative revision classifier.

Classifies natural-language revision commands. Does not execute revisions.
Does not call PRICE_BLOCK_ONLY, hide plates, or pixel surgery.
"""

from __future__ import annotations

import re
from typing import Any, Literal

RevisionIntent = Literal[
    "VISUAL_REPLACE_ONLY",
    "PRICE_EDIT_ONLY",
    "LOGO_EDIT_ONLY",
    "CREATIVE_RECOMPOSE",
]

# Multi-word phrases match as substrings. Single tokens use Turkish word boundaries
# so "sadece" never counts as "sade".
_TR_WORD = r"a-z0-9çğıöşüâîû"

VISUAL_REPLACE_PHRASES = (
    "görseli değiştir",
    "gorseli degistir",
    "görselini değiştir",
    "gorselini degistir",
    "görseli yerine",
    "gorseli yerine",
    "görselin yerine",
    "gorselin yerine",
    "bu görsel yerine",
    "bu gorsel yerine",
    "bu görselin yerine",
    "bu gorselin yerine",
    "başka görsel kullan",
    "baska gorsel kullan",
    "başka fotoğraf kullan",
    "baska fotograf kullan",
    "dış cephe görselini kullan",
    "dis cephe gorselini kullan",
    "dış cepheyi kullan",
    "dis cepheyi kullan",
    "drive'daki dış cepheyi kullan",
    "drive daki dış cepheyi kullan",
    "ana proje görselini değiştir",
    "ana proje gorselini degistir",
    "dış cephe",
    "dis cephe",
    "fotoğrafı değiştir",
    "fotografi degistir",
    "başka görsel",
    "baska gorsel",
)

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


def has_tr_word(text: str, token: str) -> bool:
    """True when token is a whole Turkish word, not a substring of a longer word."""
    raw = _norm(text)
    tok = _norm(token).strip()
    if not raw or not tok:
        return False
    if " " in tok:
        return tok in raw
    return re.search(rf"(?<![{_TR_WORD}]){re.escape(tok)}(?![{_TR_WORD}])", raw) is not None


def is_visual_replace_command(instruction: str) -> bool:
    raw = _norm(instruction)
    return any(phrase in raw for phrase in VISUAL_REPLACE_PHRASES)


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
            "kesinlikle değiştirme",
            "kesinlikle degistirme",
            "geri kalan",
            "birebir aynı",
            "birebir ayni",
            "aynı kalsın",
            "ayni kalsin",
            "nothing else",
            "don't change anything else",
            "do not change anything else",
        )
    )
    visual = is_visual_replace_command(instruction) or any(
        tok in raw
        for tok in (
            "exterior",
            "interior kullan",
            "bu görsel",
            "bu gorsel",
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
