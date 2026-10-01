"""Phase 10.2 — natural-language VISUAL_REPLACE_ONLY parse.

User speaks commercially. Technical modes stay internal.
"""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.creative_master_router_v2 import VISUAL_REPLACE_ONLY, classify_production_intent

USER_COMMAND = (
    "Sağdaki dış cephe görselini başka bir gerçek Temple dış cephe\n"
    "görseliyle değiştir, başka hiçbir şeyi değiştirme."
)
REVISION_TYPE = "VISUAL_REPLACE_ONLY"
TARGET_OBJECT = "PROJECT_EXTERIOR_REVEAL"
OLD_EXTERIOR_FILENAME = "IH_DC_TMP_001_Render_Exterior_Day_002.jpg"
OLD_EXTERIOR_ASSET_ID = "543aeb03-c4c9-46f9-9d9f-81bf53f45438"
INTERIOR_FILENAME = "IH_DC_TMP_001_Render_Living_Room_001.jpg"
INTERIOR_ASSET_ID = "c3d11c35-d8b7-485c-b216-0a4da68b751a"

_PRESERVE = ("başka hiçbir şeyi değiştirme", "baska hicbir seyi degistirme")
_EXTERIOR = ("dış cephe", "dis cephe", "sağdaki", "sagdaki")
_REAL = ("gerçek", "gercek")
_FORBIDDEN = (
    "başlığı",
    "basligi",
    "alirken",
    "fiyat",
    "usd yap",
    "story",
    "reel",
    "video",
    "1:1",
    "9:16",
    "living",
    "iç mekan",
    "ic mekan",
    "logo",
)


def parse_visual_replace_command(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    folded = raw.casefold()
    routed = classify_production_intent(raw)
    preserve = any(marker in folded for marker in _PRESERVE)
    exterior = any(marker in folded for marker in _EXTERIOR)
    real_temple = any(marker in folded for marker in _REAL) and "temple" in folded
    forbidden = [m for m in _FORBIDDEN if m in folded]
    ok = (
        routed.get("intent") == VISUAL_REPLACE_ONLY
        and routed.get("is_revision") is True
        and exterior
        and real_temple
        and preserve
        and not forbidden
    )
    return {
        "schema": "NaturalLanguageVisualReplaceV1",
        "user_command": raw,
        "revision_type": REVISION_TYPE if ok else routed.get("intent"),
        "router_intent": routed.get("intent"),
        "target_object": TARGET_OBJECT if ok else None,
        "old_asset": OLD_EXTERIOR_ASSET_ID,
        "preserve_interior": True,
        "preserve_everything_else": preserve,
        "forbidden_markers": forbidden,
        "pass": ok,
        "fail_reason": None
        if ok
        else (
            "not_visual_replace_only"
            if routed.get("intent") != VISUAL_REPLACE_ONLY or forbidden
            else "missing_exterior_or_real_temple"
            if not exterior or not real_temple
            else "missing_preserve_lock"
        ),
    }
