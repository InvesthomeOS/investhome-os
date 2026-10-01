"""Phase 10.0 — natural-language PRICE_ONLY parse.

User speaks commercially. Technical modes stay internal.
"""

from __future__ import annotations

import re
from typing import Any

from investhome_api.services.creative_director.creative_master_router_v2 import PRICE_EDIT_ONLY, classify_production_intent

USER_COMMAND = "Fiyatı 750.000 USD yap, başka hiçbir şeyi değiştirme."
OLD_PRICE = "675.000 USD"
NEW_PRICE = "750.000 USD"
REVISION_TYPE = "PRICE_ONLY"

_PRICE_TOKEN = re.compile(
    r"(?P<amount>\d{1,3}(?:[.\s]\d{3})+|\d{4,7})\s*(?P<currency>USD|usd)",
    re.IGNORECASE,
)
_PRESERVE = ("başka hiçbir şeyi değiştirme", "baska hicbir seyi degistirme")
_FORBIDDEN = (
    "başlığı",
    "basligi",
    "alirken",
    "kazan",
    "%35",
    "lansman",
    "daire",
    "keşfet",
    "kesfet",
    "logo",
    "görsel",
    "gorsel",
    "fotoğraf",
    "fotograf",
    "story",
    "1:1",
    "9:16",
)


def _norm_price(amount: str, currency: str) -> str:
    digits = re.sub(r"\D", "", amount)
    if len(digits) < 4:
        raise ValueError("price amount too small")
    grouped = f"{int(digits):,}".replace(",", ".")
    return f"{grouped} {currency.upper()}"


def parse_price_only_command(
    text: str,
    *,
    current_price: str = OLD_PRICE,
) -> dict[str, Any]:
    raw = (text or "").strip()
    folded = raw.casefold()
    routed = classify_production_intent(raw)
    hits = list(_PRICE_TOKEN.finditer(raw))
    preserve = any(marker in folded for marker in _PRESERVE)
    forbidden = [m for m in _FORBIDDEN if m in folded]
    new_value = _norm_price(hits[0].group("amount"), hits[0].group("currency")) if hits else None
    old_value = current_price
    ok = (
        routed.get("intent") == PRICE_EDIT_ONLY
        and routed.get("is_revision") is True
        and len(hits) == 1
        and new_value is not None
        and new_value != old_value
        and preserve
        and not forbidden
    )
    return {
        "schema": "NaturalLanguagePriceRevisionV1",
        "user_command": raw,
        "revision_type": REVISION_TYPE if ok else routed.get("intent"),
        "router_intent": routed.get("intent"),
        "old_value": old_value,
        "new_value": new_value,
        "preserve_everything_else": preserve,
        "forbidden_markers": forbidden,
        "pass": ok,
        "fail_reason": None
        if ok
        else (
            "not_price_only"
            if routed.get("intent") != PRICE_EDIT_ONLY or forbidden
            else "missing_new_price"
            if new_value is None
            else "price_unchanged"
            if new_value == old_value
            else "missing_preserve_lock"
        ),
    }
