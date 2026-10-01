"""CreativeRevisionControllerV1 — natural-language intent, not a designer."""

from __future__ import annotations

import re
from typing import Any

PRICE_REVISION = "PRICE_REVISION"
VISUAL_REPLACE = "VISUAL_REPLACE"
COPY_REVISION = "COPY_REVISION"
CTA_REVISION = "CTA_REVISION"
UNIT_REVISION = "UNIT_REVISION"

TEST_A_INSTRUCTION = (
    "Fiyatı 438.750 USD yap. Eski fiyat 675.000 USD üzeri çizili kalsın. "
    "Kazancınız 236.250 USD bilgisini ekle. Başka hiçbir şeyi değiştirme."
)

_PRICE_MARKERS = (
    "fiyat",
    "438.750",
    "438,750",
    "üzeri çizili",
    "uzeri cizili",
    "kazancınız",
    "kazanciniz",
    "236.250",
)
_VISUAL_MARKERS = (
    "görsel yerine",
    "gorsel yerine",
    "görseli yerine",
    "gorseli yerine",
    "dış cephe",
    "dis cephe",
    "media library",
    "başka görsel",
    "baska gorsel",
)
_CTA_MARKERS = ("keşfet", "kesfet", "cta")
_UNIT_MARKERS = ("2+1", "daire", "unit")
_COPY_MARKERS = ("başlığı", "basligi", "alırken", "alirken kazan")


def _has_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(m in text for m in markers)


def classify_revision_intent(instruction: str) -> str:
    text = (instruction or "").casefold()
    if _has_any(text, _PRICE_MARKERS):
        return PRICE_REVISION
    if _has_any(text, _VISUAL_MARKERS):
        return VISUAL_REPLACE
    if _has_any(text, _CTA_MARKERS):
        return CTA_REVISION
    if _has_any(text, _UNIT_MARKERS):
        return UNIT_REVISION
    if _has_any(text, _COPY_MARKERS):
        return COPY_REVISION
    return COPY_REVISION


def parse_price_revision(instruction: str) -> dict[str, str]:
    raw = instruction or ""
    launch = re.search(r"438[.,]750\s*USD", raw, re.IGNORECASE)
    listed = re.search(r"675[.,]000\s*USD", raw, re.IGNORECASE)
    savings = re.search(r"236[.,]250\s*USD", raw, re.IGNORECASE)
    return {
        "launch_price": (launch.group(0).replace(",", ".") if launch else "438.750 USD"),
        "list_price_struck": (listed.group(0).replace(",", ".") if listed else "675.000 USD"),
        "savings": (savings.group(0).replace(",", ".") if savings else "236.250 USD"),
        "savings_label": "KAZANCINIZ",
    }


def plan_visual_replace(instruction: str, master: dict[str, Any]) -> dict[str, Any]:
    """Architecture for Test B. Not executed in Phase 5.5."""
    return {
        "schema": "VisualReplacePlanV1",
        "intent": VISUAL_REPLACE,
        "executed": False,
        "instruction": instruction,
        "master_id": master.get("master_id"),
        "rules": {
            "same_project": True,
            "approved_assets_only": True,
            "exterior_category": True,
            "no_ai_generated_building": True,
            "no_architecture_generation": True,
            "preserve_design_identity": True,
            "preserve_semantic_content": True,
            "preserve_logo": True,
            "preserve_typography": True,
            "preserve_commercial_hierarchy": True,
            "preserve_cta": True,
            "adapt_crop_only": True,
        },
        "pipeline": [
            "replace project_photo source_asset_id",
            "photo-aware crop analysis",
            "preserve composition identity",
            "render new version",
        ],
        "forbidden": ["redesign advertisement", "generate architecture", "GPT Image designer"],
    }


def build_revision_intent(
    *,
    approved_master_id: str,
    instruction: str,
    master: dict[str, Any] | None = None,
) -> dict[str, Any]:
    intent = classify_revision_intent(instruction)
    master = master or {}
    preserved = [
        "composition",
        "photo_crop",
        "photo_grade",
        "architecture",
        "logo",
        "headline",
        "unit_type",
        "typography",
        "color_language",
        "cta",
        "design_family",
        "canvas",
    ]
    extras: dict[str, Any] = {}
    if intent == PRICE_REVISION:
        mutable = ["commercial"]
        extras["price_values"] = parse_price_revision(instruction)
        extras["preserve_explicit"] = ["2+1 DAİRE", "ALIRKEN KAZAN", "PROJEYİ KEŞFET", "%35", "LANSMAN AVANTAJI"]
        new_source = False
    elif intent == VISUAL_REPLACE:
        mutable = ["project_photo"]
        new_source = True
        extras["visual_replace"] = plan_visual_replace(instruction, master)
        extras["execute"] = False
    elif intent == CTA_REVISION:
        mutable = ["cta"]
        new_source = False
    elif intent == UNIT_REVISION:
        mutable = ["unit_type"]
        new_source = False
    else:
        mutable = ["headline"]
        new_source = False
    untouched = [g for g in ("project_photo", "logo", "headline", "unit_type", "commercial", "cta") if g not in mutable]
    return {
        "schema": "CreativeRevisionIntentV1",
        "approved_master_id": approved_master_id,
        "natural_language_instruction": instruction,
        "revision_scope": intent,
        "requested_semantic_changes": extras.get("price_values") or extras.get("visual_replace") or {},
        "explicitly_preserved_content": extras.get("preserve_explicit") or ["everything not named"],
        "implicitly_locked_content": preserved,
        "groups_requiring_reflow": mutable,
        "groups_untouched": untouched,
        "new_source_asset_required": new_source,
        "ambiguous": False,
        "user_visible": False,
    }
