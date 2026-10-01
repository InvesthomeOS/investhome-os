"""PremiumCreativeFamilyV1 — human-approved format masters, not autonomous format design.

A Premium campaign is a family of independently art-directed, HUMAN_APPROVED
finished creatives that share campaign identity. Missing formats are missing.
"""

from __future__ import annotations

from typing import Any
from uuid import NAMESPACE_URL, uuid5

FAMILY_SCHEMA = "PremiumCreativeFamilyV1"
FORMAT_MASTER_SCHEMA = "PremiumFormatMasterV1"
STATUS_MODEL_READY = "PREMIUM_CREATIVE_FAMILY_MODEL_READY"
STATUS_FORMAT_MISSING = "PREMIUM_FORMAT_MASTER_MISSING"
STATUS_STAGE41_FAIL = "PREMIUM_FORMAT_RECOMPOSITION_FAIL"
PREMIUM_MODEL = "HUMAN_APPROVED_CREATIVE_FAMILY"
AUTONOMOUS_PREMIUM_FORMAT_DESIGN = "DISABLED"
NEXT_PHASE = "FIRST MULTI-FORMAT PRODUCTION CREATIVE FAMILY INGESTION"
ROUTE_USE_FORMAT_MASTER = "USE_FORMAT_MASTER"
ROUTE_FORMAT_MISSING = "PREMIUM_FORMAT_MASTER_MISSING"
ROUTE_FAMILY_WIDE = "FAMILY_WIDE_REVISION"
ACTION_SURFACE_MISSING = "SURFACE_PREMIUM_FORMAT_MASTER_MISSING"
ACTION_USE_FORMAT = "OPERATE_APPROVED_FORMAT_MASTER"
ACTION_FAMILY_WIDE = "REVISE_EVERY_APPROVED_FORMAT_MASTER"
SKIP_TARGET_NOT_PRESENT = "SKIP_TARGET_NOT_PRESENT"
SKIP_FORMAT_MASTER_MISSING = "SKIP_FORMAT_MASTER_MISSING"
REVISE_INDEPENDENTLY = "REVISE_INDEPENDENTLY"
COMPLETE_SUCCESS = "COMPLETE_SUCCESS"
PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
FAIL = "FAIL"
STATUS_FAMILY_WIDE_PARTIAL = "FAMILY_WIDE_REVISION_PARTIAL_SUCCESS"
STATUS_FAMILY_WIDE_COMPLETE = "FAMILY_WIDE_REVISION_COMPLETE_SUCCESS"
STATUS_FAMILY_WIDE_FAIL = "FAMILY_WIDE_REVISION_FAIL"
ENGINE_PRODUCTION_READY = "PRODUCTION READY"

FEED_PORTRAIT = "4:5"
STORY_REEL = "9:16"
SQUARE = "1:1"
LANDSCAPE = "16:9"

SUPPORTED_FORMATS = (
    {"id": "FEED_PORTRAIT", "format": FEED_PORTRAIT, "dimensions": {"width": 1080, "height": 1350}},
    {"id": "STORY_REEL", "format": STORY_REEL, "dimensions": {"width": 1080, "height": 1920}},
    {"id": "SQUARE", "format": SQUARE, "dimensions": {"width": 1080, "height": 1080}},
    {"id": "LANDSCAPE", "format": LANDSCAPE, "dimensions": {"width": 1920, "height": 1080}},
)

FAMILY_LOCKED_PROPERTIES = (
    "CAMPAIGN_IDEA",
    "CAMPAIGN_COPY",
    "BRAND_IDENTITY",
    "PROJECT_IDENTITY",
    "APPROVED_ASSET_SET",
    "COLOR_SYSTEM",
    "TYPOGRAPHIC_PERSONALITY",
    "GRAPHIC_LANGUAGE",
    "COMMERCIAL_MESSAGE",
    "VISUAL_CHARACTER",
)

ORNEK_FAMILY_ID = str(uuid5(NAMESPACE_URL, "investhome:premium-creative-family:ornek-00013"))
BRAND_ID = "INVESTHOME"


def _production_master_id() -> str:
    from investhome_api.services.creative_director.phase12_0_ingestion import PRODUCTION_MASTER_ID

    return PRODUCTION_MASTER_ID


def format_dimensions(fmt: str) -> dict[str, int]:
    for item in SUPPORTED_FORMATS:
        if item["format"] == fmt:
            return dict(item["dimensions"])
    return {"width": 1080, "height": 1350}


def family_schema() -> dict[str, Any]:
    return {
        "schema": FAMILY_SCHEMA,
        "status": STATUS_MODEL_READY,
        "premium_model": PREMIUM_MODEL,
        "autonomous_premium_format_design": AUTONOMOUS_PREMIUM_FORMAT_DESIGN,
        "locked_properties": list(FAMILY_LOCKED_PROPERTIES),
        "these_define": "SAME CAMPAIGN",
        "not": [
            "one master plus automatically designed formats",
            "autonomous PremiumFormatRecomposerV1 production",
            "resize + reposition semantic layers",
        ],
        "each_format": "independently art-directed and HUMAN_APPROVED",
        "may_differ": "composition / layout geometry",
        "must_share": list(FAMILY_LOCKED_PROPERTIES),
        "supported_formats": [dict(item) for item in SUPPORTED_FORMATS],
        "missing_format_policy": STATUS_FORMAT_MISSING,
        "do_not_fabricate_premium_format": True,
        "ai_quick_creative_separate": True,
    }


def format_master_schema() -> dict[str, Any]:
    return {
        "schema": FORMAT_MASTER_SCHEMA,
        "required_fields": [
            "FAMILY_ID",
            "FORMAT_MASTER_ID",
            "FORMAT",
            "DIMENSIONS",
            "SOURCE_ASSET_ID",
            "SOURCE_CATEGORY",
            "APPROVAL_STATUS",
            "SEMANTIC_MAP",
            "LOCK_MAP",
            "RELATIONSHIP_MAP",
            "PROJECT_SCOPE",
            "BRAND_SCOPE",
        ],
        "approval": "HUMAN_APPROVED to be router eligible",
        "rejected_stage4_stories": "NOT family members",
        "autonomous_derivation": "FORBIDDEN",
    }


def format_lock_map(*, fmt: str, approval: str) -> dict[str, Any]:
    return {
        "schema": "FormatMasterLockMapV1",
        "format": fmt,
        "campaign_identity": "LOCKED",
        "composition": "LOCKED after HUMAN_APPROVED",
        "layout_geometry": "OWNED_BY_THIS_FORMAT",
        "do_not_rebuild_from_another_format": True,
        "approval_status": approval,
    }


def format_relationship_map(*, family_id: str, fmt: str) -> dict[str, Any]:
    return {
        "schema": "FormatMasterRelationshipMapV1",
        "family_id": family_id,
        "format": fmt,
        "sibling_formats": [item["format"] for item in SUPPORTED_FORMATS if item["format"] != fmt],
        "revision_child_of": "this format master only",
        "not_derived_from": "sibling format masters",
    }


def empty_format_slot(*, family_id: str, fmt: str) -> dict[str, Any]:
    return {
        "schema": FORMAT_MASTER_SCHEMA,
        "FAMILY_ID": family_id,
        "FORMAT_MASTER_ID": None,
        "FORMAT": fmt,
        "DIMENSIONS": format_dimensions(fmt),
        "SOURCE_ASSET_ID": None,
        "SOURCE_CATEGORY": None,
        "APPROVAL_STATUS": "MISSING",
        "SEMANTIC_MAP": None,
        "LOCK_MAP": format_lock_map(fmt=fmt, approval="MISSING"),
        "RELATIONSHIP_MAP": format_relationship_map(family_id=family_id, fmt=fmt),
        "PROJECT_SCOPE": None,
        "BRAND_SCOPE": None,
        "router_eligible": False,
        "family_member": False,
    }


def ornek_00013_feed_master(*, family_id: str) -> dict[str, Any]:
    from investhome_api.services.creative_director.phase12_0_ingestion import (
        PRODUCTION_MASTER_ID,
        SELECTED_ASSET_ID,
        SELECTED_FILENAME,
        ornek_00013_semantic_map,
    )
    from investhome_api.services.creative_director.phase12_1_approve_lock import brand_master_scope

    scope = brand_master_scope()
    semantic = ornek_00013_semantic_map()
    return {
        "schema": FORMAT_MASTER_SCHEMA,
        "FAMILY_ID": family_id,
        "FORMAT_MASTER_ID": PRODUCTION_MASTER_ID,
        "FORMAT": FEED_PORTRAIT,
        "DIMENSIONS": format_dimensions(FEED_PORTRAIT),
        "SOURCE_ASSET_ID": SELECTED_ASSET_ID,
        "SOURCE_FILENAME": SELECTED_FILENAME,
        "SOURCE_CATEGORY": "INVESTHOME_APPROVED",
        "APPROVAL_STATUS": "HUMAN_APPROVED",
        "SEMANTIC_MAP": semantic,
        "LOCK_MAP": format_lock_map(fmt=FEED_PORTRAIT, approval="HUMAN_APPROVED"),
        "RELATIONSHIP_MAP": format_relationship_map(family_id=family_id, fmt=FEED_PORTRAIT),
        "PROJECT_SCOPE": None,
        "BRAND_SCOPE": BRAND_ID,
        "master_scope": scope["MASTER_SCOPE"],
        "cross_project_reuse": False,
        "router_eligible": True,
        "family_member": True,
        "is_premium_master": True,
    }


def ornek_00013_family() -> dict[str, Any]:
    from investhome_api.services.creative_director.phase12_0_ingestion import SELECTED_ASSET_ID

    family_id = ORNEK_FAMILY_ID
    feed = ornek_00013_feed_master(family_id=family_id)
    inventory = {
        FEED_PORTRAIT: feed,
        STORY_REEL: empty_format_slot(family_id=family_id, fmt=STORY_REEL),
        SQUARE: empty_format_slot(family_id=family_id, fmt=SQUARE),
        LANDSCAPE: empty_format_slot(family_id=family_id, fmt=LANDSCAPE),
    }
    return {
        "schema": FAMILY_SCHEMA,
        "FAMILY_ID": family_id,
        "family_type": "INVESTHOME BRAND",
        "brand_id": BRAND_ID,
        "project_id": None,
        "cross_project_reuse": False,
        "campaign_name": "ORNEK_00013 — DÜZENLİ. GÜVENLİ. PRESTİJLİ.",
        "identity": {
            "CAMPAIGN_IDEA": "Washington D.C. investment as orderly, secure, prestigious",
            "CAMPAIGN_COPY": {
                "headline": "DÜZENLİ. / GÜVENLİ. / PRESTİJLİ.",
                "body": (
                    "Planlı şehir dokusu, yüksek yaşam standartları ve güçlü kira piyasası... "
                    "Tüm bunlar Washington DC’yi sadece popüler değil, istikrarlı bir yatırım lokasyonu yapıyor."
                ),
                "highlight": "istikrarlı bir yatırım lokasyonu yapıyor.",
                "tagline": "YATIRIMA AÇILAN KAPI",
            },
            "BRAND_IDENTITY": "Investhome",
            "PROJECT_IDENTITY": None,
            "APPROVED_ASSET_SET": [SELECTED_ASSET_ID],
            "COLOR_SYSTEM": {"navy": [40, 47, 56], "gold": [201, 168, 92], "ivory": [236, 230, 218]},
            "TYPOGRAPHIC_PERSONALITY": "stacked all-caps chant + quiet body + gold land",
            "GRAPHIC_LANGUAGE": "monochrome colonnade as structural mass on a navy page",
            "COMMERCIAL_MESSAGE": "Washington D.C. as a stable investment location — no invented price/unit/CTA",
            "VISUAL_CHARACTER": "premium editorial, asymmetric two-mass 4:5",
        },
        "formats": inventory,
        "inventory": {
            FEED_PORTRAIT: "HUMAN_APPROVED",
            STORY_REEL: "MISSING",
            SQUARE: "MISSING",
            LANDSCAPE: "MISSING",
        },
        "rejected_not_members": [
            "Stage 4.0 RETRY",
            "R1",
            "R2",
            "CLEAN",
            "R3",
            "Stage 4.1 Story",
        ],
    }


def families_in(library: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(library, dict):
        return []
    found = library.get("premium_creative_families") or []
    return [item for item in found if isinstance(item, dict)]


def family_containing_master(
    library: dict[str, Any] | None,
    master_id: str | None,
) -> dict[str, Any] | None:
    if not master_id:
        return None
    wanted = str(master_id)
    for family in families_in(library):
        for slot in (family.get("formats") or {}).values():
            if isinstance(slot, dict) and str(slot.get("FORMAT_MASTER_ID") or "") == wanted:
                return family
    if wanted == _production_master_id():
        return ornek_00013_family()
    return None


def _project_match_keys(family: dict[str, Any]) -> set[str]:
    keys = {
        str(family.get("project_id") or ""),
        str(family.get("project_code") or ""),
        str(family.get("PROJECT_SCOPE") or family.get("project_scope") or ""),
    }
    return {key for key in keys if key}


def resolve_family(
    library: dict[str, Any] | None,
    *,
    project_id: str | None = None,
    brand_id: str | None = None,
    family_id: str | None = None,
) -> dict[str, Any] | None:
    """Brand families are not project families. Cross-project reuse is blocked."""
    pool = families_in(library)
    if family_id:
        for item in pool:
            if str(item.get("FAMILY_ID")) == str(family_id):
                return item
        return None
    if brand_id:
        pool = [item for item in pool if str(item.get("brand_id") or "") == str(brand_id)]
        pool = [item for item in pool if item.get("project_id") in {None, ""}]
        return pool[0] if pool else None
    if project_id:
        wanted = str(project_id)
        matched = []
        for item in pool:
            keys = _project_match_keys(item)
            if wanted in keys or wanted.upper() in {key.upper() for key in keys}:
                if str(item.get("brand_id") or "") == "" or item.get("project_id"):
                    matched.append(item)
        return matched[0] if matched else None
    return pool[0] if pool else None


def lookup_format_master(
    family: dict[str, Any] | None,
    fmt: str,
) -> dict[str, Any]:
    if not isinstance(family, dict):
        return {
            "status": STATUS_FORMAT_MISSING,
            "format": fmt,
            "master": None,
            "family_member": False,
        }
    slot = (family.get("formats") or {}).get(fmt) or empty_format_slot(
        family_id=str(family.get("FAMILY_ID") or ""),
        fmt=fmt,
    )
    approved = (
        str(slot.get("APPROVAL_STATUS")) == "HUMAN_APPROVED"
        and slot.get("router_eligible") is True
        and slot.get("family_member") is True
        and slot.get("FORMAT_MASTER_ID")
    )
    if not approved:
        return {
            "status": STATUS_FORMAT_MISSING,
            "format": fmt,
            "master": None,
            "family_id": family.get("FAMILY_ID"),
            "family_member": False,
            "message": (
                f"This Premium campaign does not yet have an approved {fmt} master. "
                "Do not fabricate a Premium format. AI Quick Creative remains available separately."
            ),
        }
    return {
        "status": "HUMAN_APPROVED",
        "format": fmt,
        "master": slot,
        "family_id": family.get("FAMILY_ID"),
        "family_member": True,
        "format_master_id": slot.get("FORMAT_MASTER_ID"),
        "source_asset_id": slot.get("SOURCE_ASSET_ID"),
    }


def rejected_stage4_stories_in_family(family: dict[str, Any] | None) -> bool:
    if not isinstance(family, dict):
        return False
    for slot in (family.get("formats") or {}).values():
        if not isinstance(slot, dict):
            continue
        if str(slot.get("revision") or "") in {"RETRY", "R1", "R2", "CLEAN", "R3", "STAGE4.1"}:
            return True
        if slot.get("stage4_rejected") is True and slot.get("family_member") is True:
            return True
    return False


def route_format_request(
    *,
    classified: dict[str, Any],
    library: dict[str, Any] | None,
    project_id: str | None = None,
    brand_id: str | None = None,
    current_master_id: str | None = None,
    family_id: str | None = None,
) -> dict[str, Any]:
    fmt = str(classified.get("target_format") or STORY_REEL)
    family = resolve_family(library, family_id=family_id) if family_id else None
    if family is None:
        family = resolve_family(library, project_id=project_id, brand_id=brand_id)
    if family is None:
        family = family_containing_master(library, current_master_id)
    looked = lookup_format_master(family, fmt)
    if looked["status"] == "HUMAN_APPROVED":
        master = looked["master"]
        return {
            "schema": FAMILY_SCHEMA,
            "route": ROUTE_USE_FORMAT_MASTER,
            "action": ACTION_USE_FORMAT,
            "status": "HUMAN_APPROVED",
            "regenerate": False,
            "autonomous_premium_format_design": False,
            "family_id": looked.get("family_id"),
            "format": fmt,
            "selected_master_id": master.get("FORMAT_MASTER_ID"),
            "source_asset_id": master.get("SOURCE_ASSET_ID"),
            "source_filename": master.get("SOURCE_FILENAME"),
        }
    return {
        "schema": FAMILY_SCHEMA,
        "route": ROUTE_FORMAT_MISSING,
        "action": ACTION_SURFACE_MISSING,
        "status": STATUS_FORMAT_MISSING,
        "regenerate": False,
        "autonomous_premium_format_design": False,
        "family_id": None if family is None else family.get("FAMILY_ID"),
        "format": fmt,
        "selected_master_id": None,
        "allow": ["AI_QUICK_CREATIVE", "PREMIUM_FORMAT_MASTER_INGESTION"],
        "do_not": [
            "PremiumFormatRecomposerV1 autonomous production",
            "PremiumFormatAdapterV1 reposition",
            "fabricate a Premium Story from 4:5",
        ],
        "message": looked.get("message")
        or (
            f"No Premium Creative Family has an approved {fmt} master. "
            "Do not fabricate a Premium format."
        ),
    }


def family_wide_target_territory(classified: dict[str, Any] | None) -> str | None:
    raw = str((classified or {}).get("family_wide_territory") or (classified or {}).get("intent") or "")
    folded = raw.upper()
    if "PRICE" in folded:
        return "PRICE"
    if "COPY" in folded or "HEADLINE" in folded:
        return "HEADLINE"
    if "VISUAL" in folded or "PHOTO" in folded:
        return "PROJECT_PHOTO"
    return None


def format_semantic_present(slot: dict[str, Any] | None, territory_id: str | None) -> bool:
    if not territory_id or not isinstance(slot, dict):
        return False
    territories = ((slot.get("SEMANTIC_MAP") or {}).get("territories") or [])
    row = next((item for item in territories if str(item.get("id") or item.get("territory_id")) == territory_id), None)
    return bool(row and row.get("present"))


def _fold_copy(text: str) -> str:
    table = str.maketrans({"İ": "i", "I": "i", "ı": "i", "Ş": "s", "ş": "s"})
    return (text or "").translate(table).casefold()


def format_copy_phrase_present(slot: dict[str, Any] | None, phrase: str | None) -> bool:
    """True when the exact campaign phrase already exists in this format's copy."""
    if not phrase or not isinstance(slot, dict):
        return False
    needle = _fold_copy(phrase)
    if not needle:
        return False
    for row in ((slot.get("SEMANTIC_MAP") or {}).get("territories") or []):
        if not row.get("present"):
            continue
        hay = _fold_copy(str(row.get("copy") or ""))
        if needle in hay:
            return True
    return False


def plan_family_wide_member(
    family: dict[str, Any] | None,
    fmt: str,
    *,
    territory_id: str | None,
    target_phrase: str | None = None,
) -> dict[str, Any]:
    looked = lookup_format_master(family, fmt)
    if looked.get("status") != "HUMAN_APPROVED":
        return {
            "format": fmt,
            "format_master_id": None,
            "action": SKIP_FORMAT_MASTER_MISSING,
            "reason": SKIP_FORMAT_MASTER_MISSING,
            "applicable": False,
            "preserve_composition": True,
            "invent_missing_semantic": False,
        }
    slot = looked.get("master") or {}
    present = format_copy_phrase_present(slot, target_phrase) if target_phrase else (
        format_semantic_present(slot, territory_id) if territory_id else True
    )
    if (target_phrase or territory_id) and not present:
        return {
            "format": fmt,
            "format_master_id": looked.get("format_master_id"),
            "action": SKIP_TARGET_NOT_PRESENT,
            "reason": SKIP_TARGET_NOT_PRESENT,
            "applicable": False,
            "preserve_composition": True,
            "invent_missing_semantic": False,
        }
    return {
        "format": fmt,
        "format_master_id": looked.get("format_master_id"),
        "action": REVISE_INDEPENDENTLY,
        "reason": "TARGET_PRESENT",
        "applicable": True,
        "preserve_composition": True,
        "invent_missing_semantic": False,
    }


def score_family_wide_revision(members: list[dict[str, Any]]) -> str:
    """Legitimate SKIP never becomes FAIL. FAIL only if an applicable target could not be revised."""
    failed = [item for item in members if str(item.get("outcome") or item.get("action")) == FAIL]
    if failed:
        return FAIL
    revised = [
        item
        for item in members
        if str(item.get("outcome") or item.get("action")) in {"REVISED", REVISE_INDEPENDENTLY, "CREATE_REVISION_CHILD"}
        and str(item.get("outcome")) != FAIL
    ]
    skipped = [
        item
        for item in members
        if str(item.get("outcome") or item.get("reason") or item.get("action"))
        in {SKIP_TARGET_NOT_PRESENT, SKIP_FORMAT_MASTER_MISSING}
    ]
    applicable_failed = [
        item
        for item in members
        if item.get("applicable") is True and str(item.get("outcome") or "") in {FAIL, "FAIL"}
    ]
    if applicable_failed:
        return FAIL
    completed = [item for item in members if str(item.get("outcome")) == "REVISED"]
    if completed and not skipped:
        return COMPLETE_SUCCESS
    if completed and skipped:
        return PARTIAL_SUCCESS
    if skipped and not completed:
        return PARTIAL_SUCCESS
    if revised and not skipped:
        return COMPLETE_SUCCESS
    if revised and skipped:
        return PARTIAL_SUCCESS
    return FAIL


def family_wide_user_confirmation(*, territory: str, revised_count: int, language: str = "tr") -> str:
    _ = language
    folded = str(territory or "").upper()
    if territory == "PRICE" or "PRICE" in folded:
        return f"Fiyat, kampanyada fiyat bilgisi bulunan {revised_count} tasarımda güncellendi."
    if territory == "HEADLINE" or "COPY" in folded:
        return f"Metin, kampanyada bu alanın bulunduğu {revised_count} tasarımda güncellendi."
    return f"Kampanyada hedefi bulunan {revised_count} tasarım güncellendi."


def family_wide_revision_contract() -> dict[str, Any]:
    return {
        "schema": "FamilyWideRevisionV1",
        "status": ENGINE_PRODUCTION_READY,
        "intent": ROUTE_FAMILY_WIDE,
        "example": "Bu kampanyadaki fiyatı tüm formatlarda 750.000 USD yap.",
        "result_model": {
            COMPLETE_SUCCESS: "All applicable active format masters revised successfully.",
            PARTIAL_SUCCESS: "Some family members revised successfully; others legitimately skipped.",
            FAIL: "An applicable target existed but the requested revision could not be completed correctly.",
        },
        "member_rule": {
            "TARGET_PRESENT": REVISE_INDEPENDENTLY,
            "TARGET_NOT_PRESENT": SKIP_TARGET_NOT_PRESENT,
            "FORMAT_MASTER_MISSING": SKIP_FORMAT_MASTER_MISSING,
        },
        "never_invent_missing_semantic": True,
        "legitimate_skip_is_not_fail": True,
        "steps": [
            "resolve Creative Family",
            "find every HUMAN_APPROVED format master",
            "identify the target territory in each format independently",
            "revise independently when the target semantic is present",
            "SKIP_TARGET_NOT_PRESENT when the format does not contain the target",
            "SKIP_FORMAT_MASTER_MISSING when the format master is absent",
            "never invent the missing semantic merely to satisfy a family-wide command",
            "preserve each format's own composition",
            "do NOT rebuild formats from another format",
        ],
        "uses": "Stage 2 Revision Router per format master",
        "preserve": [
            "target territory reconstruction",
            "local responsive copy recomposition",
            "real approved photo replacement",
            "master immutability",
            "project reality firewall",
        ],
        "user_facing": "Do not expose technical routing language unless needed.",
        "pixel_execution": False,
    }


def route_family_wide_revision(
    *,
    classified: dict[str, Any],
    library: dict[str, Any] | None,
    project_id: str | None = None,
    brand_id: str | None = None,
    current_master_id: str | None = None,
    family_id: str | None = None,
    target_phrase: str | None = None,
) -> dict[str, Any]:
    family = resolve_family(library, family_id=family_id) if family_id else None
    if family is None:
        family = resolve_family(library, project_id=project_id, brand_id=brand_id)
    if family is None:
        family = family_containing_master(library, current_master_id)
    if family is None and brand_id == BRAND_ID:
        family = ornek_00013_family()
    territory_id = family_wide_target_territory(classified)
    members = [
        plan_family_wide_member(family, fmt, territory_id=territory_id, target_phrase=target_phrase)
        for fmt in (FEED_PORTRAIT, STORY_REEL, SQUARE, LANDSCAPE)
    ]
    targets = [
        {
            "format": item["format"],
            "format_master_id": item.get("format_master_id"),
            "action": "CREATE_REVISION_CHILD",
            "preserve_composition": True,
        }
        for item in members
        if item["action"] == REVISE_INDEPENDENTLY
    ]
    skipped = [
        {
            "format": item["format"],
            "format_master_id": item.get("format_master_id"),
            "action": item["action"],
            "reason": item["reason"],
            "preserve_composition": True,
        }
        for item in members
        if item["action"] != REVISE_INDEPENDENTLY
    ]
    return {
        "schema": "FamilyWideRevisionRouteV1",
        "route": ROUTE_FAMILY_WIDE,
        "action": ACTION_FAMILY_WIDE,
        "regenerate": False,
        "family_id": None if family is None else family.get("FAMILY_ID"),
        "territory": classified.get("family_wide_territory") or classified.get("intent"),
        "territory_id": territory_id,
        "target_phrase": target_phrase,
        "members": members,
        "targets": targets,
        "skipped": skipped,
        "missing_formats": [
            item["format"] for item in members if item["action"] == SKIP_FORMAT_MASTER_MISSING
        ],
        "do_not_rebuild_from_another_format": True,
        "never_invent_missing_semantic": True,
        "uses_stage_2": True,
        "executed": False,
        "result_preview": score_family_wide_revision(
            [{**item, "outcome": item["action"]} for item in members]
        ),
    }


def archived_format_research() -> dict[str, Any]:
    return {
        "schema": "ArchivedPremiumFormatResearchV1",
        "status": "RESEARCH_ARCHIVED",
        "models": [
            {
                "id": "PremiumFormatAdapterV1",
                "role": "reposition model",
                "status": "ARCHIVED",
                "autonomous_production": False,
            },
            {
                "id": "PremiumFormatRecomposerV1",
                "role": "autonomous recomposition model",
                "status": "ARCHIVED",
                "autonomous_production": False,
                "stage_4_1": STATUS_STAGE41_FAIL,
                "technical_integrity": "PASS",
                "design_quality": "FAIL",
                "human_decision": "REJECTED",
            },
        ],
        "stories": [
            {"revision": "RETRY", "status": "REJECTED"},
            {"revision": "R1", "status": "REJECTED"},
            {"revision": "R2", "status": "REJECTED"},
            {"revision": "CLEAN", "status": "REJECTED"},
            {"revision": "R3", "status": "REJECTED"},
            {"revision": "STAGE4.1", "status": "REJECTED", "close_status": STATUS_STAGE41_FAIL},
        ],
        "router_eligible": False,
        "creative_family_members": False,
        "preserve_utilities": [
            "ONE PHOTO OBJECT",
            "SEMANTIC LAYER DEDUPLICATION",
            "SOURCE TYPE CLEANUP",
            "SAFE ZONE LOGIC",
            "FORMAT METADATA",
            "SEMANTIC MAP",
            "LOCK MAP",
        ],
    }


def project_reality_for_families() -> dict[str, Any]:
    return {
        "schema": "CreativeFamilyProjectRealityV1",
        "PROJECT_scoped": {
            "images": "real approved project images only",
            "logo": "real project logo only",
            "invented_architecture": False,
            "cross_project_substitution": False,
        },
        "BRAND_scoped": {
            "assets": "only approved brand/campaign assets associated with that family",
            "cross_project_reuse": False,
        },
    }


def live_product_routing_matrix() -> dict[str, Any]:
    return {
        "schema": "PremiumCreativeFamilyRoutingMatrixV1",
        "A": {"when": "User requests normal creative", "then": "AI QUICK CREATIVE"},
        "B": {"when": "User requests Premium creative", "then": "search Premium Creative Family"},
        "C": {"when": "Approved requested format exists", "then": "use that FORMAT MASTER"},
        "D": {"when": "Requested Premium format missing", "then": STATUS_FORMAT_MISSING},
        "E": {"when": "User requests revision", "then": "Stage 2 Revision Router"},
        "F": {"when": "User requests revision across campaign", "then": ROUTE_FAMILY_WIDE},
        "autonomous_premium_format_design": AUTONOMOUS_PREMIUM_FORMAT_DESIGN,
        "ai_quick_creative": "PRESERVED",
        "stage_2_revision": "PRESERVED",
    }


def preserved_capabilities() -> dict[str, Any]:
    return {
        "schema": "PreservedCapabilitiesV1",
        "stage_2_revision": "PRESERVED",
        "ai_quick_creative": "PRESERVED",
        "project_reality": "LOCKED",
        "design_reference_library": "PRESERVED",
        "production_cover": "UNCHANGED",
        "approved_master_asset_bytes": "UNCHANGED",
        "revision_router": [
            "target territory reconstruction",
            "local responsive copy recomposition",
            "real approved photo replacement",
            "master immutability",
            "project reality firewall",
        ],
        "reusable_format_utilities": [
            "ONE PHOTO OBJECT",
            "SEMANTIC LAYER DEDUPLICATION",
            "SOURCE TYPE CLEANUP",
            "SAFE ZONE LOGIC",
            "FORMAT METADATA",
            "SEMANTIC MAP",
            "LOCK MAP",
        ],
        "not_production_paths": [
            "PremiumFormatAdapterV1 autonomous production",
            "PremiumFormatRecomposerV1 autonomous production",
        ],
    }


def required_regression_tests() -> dict[str, Any]:
    from investhome_api.services.creative_director.creative_master_router_v2 import (
        COPY_EDIT_ONLY,
        PRICE_EDIT_ONLY,
        VISUAL_REPLACE_ONLY,
        classify_production_intent,
        revision_router_contract,
    )
    from investhome_api.services.creative_director.phase5_workflow import TEMPLE_PROJECT_ID
    from investhome_api.services.creative_director.premium_creative_product_model import (
        ai_quick_creative_contract,
        route_locked_creative_product,
    )
    from investhome_api.services.creative_director.project_creative_master_library import empty_library
    from investhome_api.services.creative_director.phase12_0_ingestion import PRODUCTION_MASTER_ID

    family = ornek_00013_family()
    library = empty_library(project_id=TEMPLE_PROJECT_ID, project_name="The Temple")
    library["premium_creative_families"] = [family]
    looked_45 = lookup_format_master(family, FEED_PORTRAIT)
    looked_916 = lookup_format_master(family, STORY_REEL)
    looked_11 = lookup_format_master(family, SQUARE)
    looked_169 = lookup_format_master(family, LANDSCAPE)
    story_route = route_format_request(
        classified=classify_production_intent("Bunu Story yap."),
        library=library,
        brand_id=BRAND_ID,
        current_master_id=PRODUCTION_MASTER_ID,
    )
    cross = resolve_family(library, project_id=TEMPLE_PROJECT_ID)
    contract = revision_router_contract()
    quick = ai_quick_creative_contract()
    quick_route = route_locked_creative_product("Temple için hızlı creative yap", workflow="ai_quick_creative")
    price = classify_production_intent("Fiyatı 750.000 USD yap.")
    return {
        "schema": "Phase122RegressionTestsV1",
        "ornek_00013_family_lookup": "PASS" if resolve_family(library, brand_id=BRAND_ID, family_id=ORNEK_FAMILY_ID) else "FAIL",
        "feed_4x5": "HUMAN_APPROVED master found" if looked_45["status"] == "HUMAN_APPROVED" else "FAIL",
        "feed_4x5_master_id": looked_45.get("format_master_id"),
        "feed_4x5_source_asset_id": looked_45.get("source_asset_id"),
        "story_9x16": looked_916["status"],
        "square_1x1": looked_11["status"],
        "landscape_16x9": looked_169["status"],
        "story_live_route": story_route["status"],
        "rejected_stage4_stories_returned": "NO" if not rejected_stage4_stories_in_family(family) else "YES",
        "cross_project_reuse": "BLOCKED" if cross is None else "FAIL",
        "stage_2_revision_router_preserved": (
            "PASS"
            if contract["PRICE_EDIT_ONLY"]["status"] == "PASS"
            and contract["COPY_EDIT_ONLY"]["status"] == "PASS"
            and contract["VISUAL_REPLACE_ONLY"]["status"] == "PASS"
            and price["intent"] == PRICE_EDIT_ONLY
            else "FAIL"
        ),
        "ai_quick_creative_preserved": (
            "PASS"
            if quick["status"] == "ACTIVE" and quick_route["route"] == "AI_QUICK_CREATIVE"
            else "FAIL"
        ),
        "copy_intent": COPY_EDIT_ONLY,
        "visual_intent": VISUAL_REPLACE_ONLY,
        "autonomous_premium_format_design": AUTONOMOUS_PREMIUM_FORMAT_DESIGN,
    }
