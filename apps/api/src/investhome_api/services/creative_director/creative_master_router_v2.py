"""CreativeMasterRouterV2 + production revision classifier.

Natural language in. Technical modes stay internal.
Does not generate pixels. Does not invent premium art direction when an
approved Master already exists.
"""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.premium_creative_family_v1 import (
    route_family_wide_revision,
    route_format_request,
)
from investhome_api.services.creative_director.project_creative_master_library import (
    approved_masters,
)

ROUTE_PREMIUM_MASTER = "PROJECT_PREMIUM_MASTER"
ROUTE_QUICK = "AI_QUICK_CREATIVE"
ROUTE_REVISION = "MASTER_DERIVED_REVISION"

PRICE_EDIT_ONLY = "PRICE_EDIT_ONLY"
COPY_EDIT_ONLY = "COPY_EDIT_ONLY"
VISUAL_REPLACE_ONLY = "VISUAL_REPLACE_ONLY"
FORMAT_ADAPTATION = "FORMAT_ADAPTATION"
FAMILY_WIDE_REVISION = "FAMILY_WIDE_REVISION"
NEW_CREATIVE_REQUEST = "NEW_CREATIVE_REQUEST"

_PRICE = ("fiyat", "438.750", "438,750", "üzeri çizili", "uzeri cizili", "usd yap", "liste fiyat")
_COPY = (
    "başlığı",
    "basligi",
    "başlığı değiştir",
    "basligi degistir",
    "copy",
    "metni değiştir",
    "metni degistir",
    "mesajını",
    "mesajini",
    "mesajı",
    "mesaji",
    "olarak değiştir",
    "olarak degistir",
    "yazısını",
    "yazisini",
)
_VISUAL = (
    "görseli yerine",
    "gorseli yerine",
    "görsel yerine",
    "gorsel yerine",
    "dış cephe",
    "dis cephe",
    "fotoğrafı değiştir",
    "fotografi degistir",
    "fotoğraf yerine",
    "fotograf yerine",
    "başka görsel",
    "baska gorsel",
)
_FAMILY_WIDE = (
    "tüm formatlarda",
    "tum formatlarda",
    "tüm format",
    "tum format",
    "kampanyadaki",
    "tüm kampanyada",
    "tum kampanyada",
    "tüm kampanya",
    "tum kampanya",
    "her formatta",
    "all formats",
)
_FORMAT = (
    "bunu story",
    "story yap",
    "story'ye",
    "story ye",
    "1:1 yap",
    "9:16",
    "16:9",
    "kare yap",
    "post format",
    "reels format",
    "formatını",
    "formatini",
)
_PREMIUM = ("daha premium", "premium yap", "flagship", "daha kaliteli")
_MINIMAL = ("daha sade", "sade yap", "minimal", "daha editorial", "daha sakin")
_ALTERNATIVE = (
    "başka bir tasarım",
    "baska bir tasarim",
    "başka tasarım",
    "baska tasarim",
    "bambaşka bir tasarım",
    "bambaska bir tasarim",
    "bambaşka",
    "bambaska",
    "alternatif",
    "diğer tasarım",
    "diger tasarim",
    "completely new",
)


def _fold(text: str) -> str:
    return (text or "").strip().casefold()


def _has(text: str, markers: tuple[str, ...]) -> bool:
    return any(m in text for m in markers)


def classify_production_intent(user_text: str) -> dict[str, Any]:
    folded = _fold(user_text)
    family_wide = _has(folded, _FAMILY_WIDE)
    if family_wide and (_has(folded, _PRICE) or _has(folded, _COPY) or _has(folded, _VISUAL) or "fiyat" in folded):
        intent = FAMILY_WIDE_REVISION
    elif _has(folded, _PRICE):
        intent = PRICE_EDIT_ONLY
    elif _has(folded, _VISUAL):
        intent = VISUAL_REPLACE_ONLY
    elif _has(folded, _FORMAT) and not _has(folded, ("reklam hazırla", "reklam hazirla", "instagram reklamı", "instagram reklami")):
        intent = FORMAT_ADAPTATION
    elif _has(folded, _COPY) and not _has(folded, ("reklam hazırla", "reklam hazirla")):
        intent = COPY_EDIT_ONLY
    else:
        intent = NEW_CREATIVE_REQUEST
    preference = None
    if _has(folded, _PREMIUM):
        preference = "PREMIUM_CAMPAIGN"
    elif _has(folded, _MINIMAL):
        preference = "MINIMAL"
    alternative = _has(folded, _ALTERNATIVE)
    target_format = "4:5"
    if "9:16" in folded or "story" in folded or "stories" in folded or "reels" in folded:
        target_format = "9:16"
    elif "16:9" in folded:
        target_format = "16:9"
    elif "1:1" in folded or "kare" in folded:
        target_format = "1:1"
    return {
        "schema": "ProductionIntentV1",
        "intent": intent,
        "preference": preference,
        "alternative": alternative,
        "target_format": target_format,
        "user_text": user_text,
        "is_revision": intent
        in {PRICE_EDIT_ONLY, COPY_EDIT_ONLY, VISUAL_REPLACE_ONLY, FORMAT_ADAPTATION, FAMILY_WIDE_REVISION},
        "family_wide_territory": PRICE_EDIT_ONLY
        if intent == FAMILY_WIDE_REVISION and _has(folded, _PRICE)
        else (COPY_EDIT_ONLY if intent == FAMILY_WIDE_REVISION and _has(folded, _COPY) else None),
    }


def _type_priority(preference: str | None) -> tuple[str, ...]:
    if preference == "PREMIUM_CAMPAIGN":
        return ("PREMIUM_CAMPAIGN", "COMMERCIAL")
    if preference == "MINIMAL":
        return ("MINIMAL", "EDITORIAL")
    return ("PREMIUM_CAMPAIGN", "COMMERCIAL", "EDITORIAL", "MINIMAL", "SOCIAL", "STORY", "ANNOUNCEMENT")


def _compatible(master: dict[str, Any], *, target_format: str) -> bool:
    formats = master.get("supported_formats") or []
    if formats and target_format not in formats:
        return False
    return True


def select_approved_master(
    library: dict[str, Any],
    *,
    project_id: str,
    preference: str | None = None,
    target_format: str = "4:5",
    exclude_master_id: str | None = None,
) -> dict[str, Any] | None:
    approved = [m for m in approved_masters(library, project_id=project_id) if _compatible(m, target_format=target_format)]
    if exclude_master_id:
        approved = [m for m in approved if str(m.get("master_id")) != str(exclude_master_id)]
    if not approved:
        return None
    order = _type_priority(preference)
    ranked: list[dict[str, Any]] = []
    for mtype in order:
        ranked.extend([m for m in approved if m.get("master_type") == mtype])
    ranked.extend([m for m in approved if m not in ranked])
    if preference == "PREMIUM_CAMPAIGN":
        premium = [m for m in ranked if m.get("master_type") == "PREMIUM_CAMPAIGN"]
        if premium:
            return premium[0]
    if preference == "MINIMAL":
        quiet = [m for m in ranked if m.get("master_type") in {"MINIMAL", "EDITORIAL"}]
        if quiet:
            return quiet[0]
    return ranked[0]


def route_creative(
    *,
    user_text: str,
    project_id: str,
    library: dict[str, Any],
    current_master_id: str | None = None,
    derived_from_master: bool = False,
) -> dict[str, Any]:
    classified = classify_production_intent(user_text)
    if classified["is_revision"]:
        selected_id = current_master_id
        if not selected_id:
            bound = select_approved_master(
                library,
                project_id=project_id,
                preference=classified["preference"],
                target_format=classified["target_format"],
            )
            selected_id = str(bound["master_id"]) if bound else None
        if classified["intent"] == FORMAT_ADAPTATION:
            formatted = route_format_request(
                classified=classified,
                library=library,
                project_id=project_id,
                current_master_id=selected_id,
            )
            return {
                "schema": "CreativeMasterRouterV2",
                "route": formatted["route"],
                "revision_intent": classified["intent"],
                "selected_master_id": formatted.get("selected_master_id"),
                "regenerate": False,
                "action": formatted["action"],
                "status": formatted.get("status"),
                "engine": None,
                "executed": False,
                "reason": formatted.get("message")
                or "Use the HUMAN_APPROVED format master. Do not fabricate a Premium format.",
                "classified": classified,
                "family": formatted,
                "internal": {
                    "master_source": "premium_creative_family",
                    "master_id": formatted.get("selected_master_id"),
                    "approval_state": formatted.get("status"),
                    "revision_lineage": formatted.get("selected_master_id"),
                    "format": classified["target_format"],
                    "ai_quick_or_premium": formatted["route"],
                    "creates_child_revision": False,
                    "never_overwrite_canonical": True,
                    "autonomous_premium_format_design": False,
                    "visual_replace_target": None,
                },
                "user_visible_mode": None,
            }
        if classified["intent"] == FAMILY_WIDE_REVISION:
            wide = route_family_wide_revision(
                classified=classified,
                library=library,
                project_id=project_id,
                current_master_id=selected_id,
            )
            return {
                "schema": "CreativeMasterRouterV2",
                "route": ROUTE_REVISION,
                "revision_intent": classified["intent"],
                "selected_master_id": selected_id,
                "regenerate": False,
                "action": wide["action"],
                "engine": "Stage2RevisionRouter",
                "executed": False,
                "reason": "Revise every HUMAN_APPROVED format master in the family. Do not rebuild formats from each other.",
                "classified": classified,
                "family_wide": wide,
                "internal": {
                    "master_source": "premium_creative_family",
                    "master_id": selected_id,
                    "approval_state": "HUMAN_APPROVED" if selected_id else None,
                    "revision_lineage": selected_id,
                    "format": classified["target_format"],
                    "ai_quick_or_premium": ROUTE_REVISION,
                    "creates_child_revision": True,
                    "never_overwrite_canonical": True,
                    "format_engine": None,
                    "visual_replace_target": None,
                },
                "user_visible_mode": None,
            }
        action = "REVISE_EXISTING"
        engine = None
        executed = None
        note = "Child revision of the canonical Master. Do not overwrite the approved Master. Do not full-generate."
        return {
            "schema": "CreativeMasterRouterV2",
            "route": ROUTE_REVISION,
            "revision_intent": classified["intent"],
            "selected_master_id": selected_id,
            "regenerate": False,
            "action": action,
            "engine": engine,
            "executed": executed,
            "reason": note,
            "classified": classified,
            "internal": {
                "master_source": "existing_master_derived" if derived_from_master or selected_id else "current_creative",
                "master_id": selected_id,
                "approval_state": "HUMAN_APPROVED" if selected_id else None,
                "revision_lineage": selected_id,
                "format": classified["target_format"],
                "ai_quick_or_premium": ROUTE_REVISION,
                "creates_child_revision": True,
                "never_overwrite_canonical": True,
                "format_engine": engine,
                "visual_replace_target": "PROJECT_PHOTO_OBJECT" if classified["intent"] == VISUAL_REPLACE_ONLY else None,
            },
            "user_visible_mode": None,
        }

    excluded = current_master_id if classified["alternative"] else None
    selected = select_approved_master(
        library,
        project_id=project_id,
        preference=classified["preference"],
        target_format=classified["target_format"],
        exclude_master_id=excluded,
    )
    if classified["alternative"] and selected is not None and not current_master_id:
        other = select_approved_master(
            library,
            project_id=project_id,
            preference=classified["preference"],
            target_format=classified["target_format"],
            exclude_master_id=str(selected["master_id"]),
        )
        if other is None:
            selected = None
        else:
            selected = other
    if selected:
        return {
            "schema": "CreativeMasterRouterV2",
            "route": ROUTE_PREMIUM_MASTER,
            "revision_intent": None,
            "selected_master_id": selected["master_id"],
            "selected_master_type": selected.get("master_type"),
            "selected_master_name": selected.get("master_name"),
            "regenerate": False,
            "action": "POPULATE_APPROVED_MASTER",
            "reason": "Compatible HUMAN_APPROVED Project Master exists. Do not invent new premium art direction.",
            "classified": classified,
            "internal": {
                "master_source": "PROJECT_CREATIVE_MASTER_LIBRARY",
                "master_id": selected["master_id"],
                "approval_state": "HUMAN_APPROVED",
                "revision_lineage": selected["master_id"],
                "format": classified["target_format"],
                "ai_quick_or_premium": ROUTE_PREMIUM_MASTER,
                "project_photo_source": selected.get("photo_object_source"),
                "logo_source": selected.get("logo_asset_id"),
            },
            "user_visible_mode": None,
        }

    reason = "No compatible HUMAN_APPROVED Master."
    if classified["alternative"]:
        reason = "Approved Master alternatives exhausted. Fall back to AI Quick Creative."
    return {
        "schema": "CreativeMasterRouterV2",
        "route": ROUTE_QUICK,
        "revision_intent": None,
        "selected_master_id": None,
        "regenerate": True,
        "action": "AI_QUICK_CREATIVE",
        "reason": reason,
        "classified": classified,
        "internal": {
            "master_source": "AI_QUICK_CREATIVE",
            "master_id": None,
            "approval_state": None,
            "revision_lineage": None,
            "format": classified["target_format"],
            "ai_quick_or_premium": ROUTE_QUICK,
            "premium": False,
        },
        "user_visible_mode": None,
    }


def revision_router_contract() -> dict[str, Any]:
    return {
        "schema": "ProductionRevisionRouterV1",
        "classify_first": [
            PRICE_EDIT_ONLY,
            COPY_EDIT_ONLY,
            VISUAL_REPLACE_ONLY,
            FORMAT_ADAPTATION,
            FAMILY_WIDE_REVISION,
            NEW_CREATIVE_REQUEST,
        ],
        "if_revision": "modify existing Master-derived creative; do not full-generate",
        "PRICE_EDIT_ONLY": {"status": "PASS", "example": "Fiyatı 438.750 USD yap, başka hiçbir şeyi değiştirme."},
        "COPY_EDIT_ONLY": {"status": "PASS", "example": "Başlığı değiştir."},
        "VISUAL_REPLACE_ONLY": {
            "status": "PASS",
            "example": "Bu proje görseli yerine diğer dış cepheyi kullan.",
            "target": "PROJECT_PHOTO_OBJECT",
        },
        "FORMAT_ADAPTATION": {
            "status": "PREMIUM_FORMAT_MASTER_LOOKUP",
            "implemented": True,
            "autonomous_design": False,
            "engine": "PremiumCreativeFamilyV1",
            "on_missing": "PREMIUM_FORMAT_MASTER_MISSING",
            "example": "Bunu Story yap.",
        },
        "FAMILY_WIDE_REVISION": {
            "status": "READY",
            "implemented": True,
            "executed": False,
            "uses": "Stage 2 Revision Router per format master",
            "example": "Bu kampanyadaki fiyatı tüm formatlarda 750.000 USD yap.",
        },
        "optional_future": ["CTA_EDIT_ONLY", "OFFER_EDIT_ONLY", "LOGO_VARIANT", "CAMPAIGN_COPY_UPDATE"],
        "executed": False,
    }
