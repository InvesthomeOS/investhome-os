"""Phase 10.1 — natural-language HEADLINE_ONLY parse.

User speaks commercially. Technical modes stay internal.
"""

from __future__ import annotations

import re
from typing import Any

from investhome_api.services.creative_director.creative_master_router_v2 import COPY_EDIT_ONLY, classify_production_intent

USER_COMMAND = (
    "ALIRKEN KAZAN başlığını ŞİMDİ YATIRIM ZAMANI olarak değiştir,\n"
    "başka hiçbir şeyi değiştirme."
)
OLD_COPY = "ALIRKEN KAZAN"
NEW_COPY = "ŞİMDİ YATIRIM ZAMANI"
REVISION_TYPE = "HEADLINE_ONLY"

_OLD = re.compile(r"ALIRKEN\s+KAZAN")
_NEW = re.compile(r"ŞİMDİ\s+YATIRIM\s+ZAMANI")
_AS = ("olarak değiştir", "olarak degistir")
_PRESERVE = ("başka hiçbir şeyi değiştirme", "baska hicbir seyi degistirme")
_FORBIDDEN = (
    "fiyat",
    "750.000",
    "675.000",
    "usd yap",
    "%35",
    "lansman",
    "görseli",
    "gorseli",
    "fotoğraf",
    "fotograf",
    "story",
    "reel",
    "video",
    "1:1",
    "9:16",
    "logo",
)


def parse_headline_only_command(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    folded = raw.casefold()
    routed = classify_production_intent(raw)
    old_hit = _OLD.search(raw)
    new_hit = _NEW.search(raw)
    preserve = any(marker in folded for marker in _PRESERVE)
    as_change = any(marker in folded for marker in _AS)
    forbidden = [m for m in _FORBIDDEN if m in folded]
    ok = (
        routed.get("intent") == COPY_EDIT_ONLY
        and routed.get("is_revision") is True
        and old_hit is not None
        and new_hit is not None
        and as_change
        and preserve
        and not forbidden
    )
    return {
        "schema": "NaturalLanguageCopyRevisionV1",
        "user_command": raw,
        "revision_type": REVISION_TYPE if ok else routed.get("intent"),
        "router_intent": routed.get("intent"),
        "old_copy": OLD_COPY if old_hit else None,
        "new_copy": NEW_COPY if new_hit else None,
        "preserve_everything_else": preserve,
        "forbidden_markers": forbidden,
        "pass": ok,
        "fail_reason": None
        if ok
        else (
            "not_headline_only"
            if routed.get("intent") != COPY_EDIT_ONLY or forbidden
            else "missing_old_or_new_copy"
            if old_hit is None or new_hit is None
            else "missing_preserve_lock"
        ),
    }
