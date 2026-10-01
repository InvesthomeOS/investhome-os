"""PremiumFormatAdapterV1 — production-master gate + deprecated reposition model.

Stage 4.0 proved this adapter can preserve semantic/layer integrity.
It cannot yet create professionally art-directed composition across a
substantial aspect-ratio change. Composition is succeeded by
PremiumFormatRecomposerV1. Keep the production-master gate.
Masters 01–03 remain research/system proofs and are never production sources.
"""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_MASTER_ID
from investhome_api.services.creative_director.phase9_0_master import TEMPLE_PREMIUM_MASTER_02_ID
from investhome_api.services.creative_director.phase9_1_master import TEMPLE_PREMIUM_MASTER_03_ID
from investhome_api.services.creative_director.premium_creative_product_model import (
    MASTER_SOURCES,
    SEMANTIC_TERRITORIES,
    premium_semantic_map_v1,
)
from investhome_api.services.creative_director.project_creative_master_library import (
    approved_brand_masters,
    approved_masters,
)

ADAPTER_ID = "PremiumFormatAdapterV1"
COMPOSITION_MODEL = "REPOSITION"
COMPOSITION_STATUS = "DEPRECATED"
REPLACED_BY = "PremiumFormatRecomposerV1"
STATUS_NO_PRODUCTION_MASTER = "NO_PRODUCTION_PREMIUM_MASTER_AVAILABLE"
STATUS_PENDING_REVIEW = "PREMIUM_FORMAT_ADAPTATION_PENDING_HUMAN_REVIEW"
STATUS_FAIL = "PREMIUM_FORMAT_ADAPTATION_FAIL"
PROOF_TARGET_FORMAT = "9:16"
CANONICAL_FORMAT = "4:5"
STORY_CANVAS = {"width": 1080, "height": 1920, "label": "9:16 STORY"}
STAGE4_PROOF_SCOPE = "INVESTHOME BRAND MASTER → STORY"
STAGE4_PROOF_SCOPE_FORBIDDEN = "THE TEMPLE PROJECT MASTER → STORY"

RESEARCH_PROOF_MASTER_IDS = frozenset(
    {
        APPROVED_MASTER_ID,
        TEMPLE_PREMIUM_MASTER_02_ID,
        TEMPLE_PREMIUM_MASTER_03_ID,
    }
)

PRODUCTION_SOURCES = frozenset(MASTER_SOURCES)

SEMANTIC_LOCK_FLEXIBILITY = {
    "PROJECT": ["IDENTITY_LOCKED", "IMMUTABLE"],
    "MASTER_ASSET": ["IDENTITY_LOCKED", "IMMUTABLE"],
    "CANONICAL_FORMAT": ["IDENTITY_LOCKED"],
    "LOGO": ["IDENTITY_LOCKED", "IMMUTABLE", "POSITION_FLEXIBLE", "SCALE_FLEXIBLE"],
    "PROJECT_PHOTO": ["IDENTITY_LOCKED", "IMMUTABLE", "CROP_FLEXIBLE", "POSITION_FLEXIBLE", "SCALE_FLEXIBLE"],
    "HEADLINE": ["IDENTITY_LOCKED", "LINEBREAK_FLEXIBLE", "SCALE_FLEXIBLE", "POSITION_FLEXIBLE"],
    "SUBHEAD": ["IDENTITY_LOCKED", "LINEBREAK_FLEXIBLE", "SCALE_FLEXIBLE", "POSITION_FLEXIBLE", "OPTIONAL_AT_TARGET"],
    "OFFER": ["IDENTITY_LOCKED", "RELATIONSHIP_LOCKED", "POSITION_FLEXIBLE", "SCALE_FLEXIBLE"],
    "PRICE": ["IDENTITY_LOCKED", "RELATIONSHIP_LOCKED", "POSITION_FLEXIBLE", "SCALE_FLEXIBLE"],
    "UNIT": ["IDENTITY_LOCKED", "RELATIONSHIP_LOCKED", "POSITION_FLEXIBLE", "SCALE_FLEXIBLE"],
    "CTA": ["IDENTITY_LOCKED", "POSITION_FLEXIBLE", "SCALE_FLEXIBLE"],
    "CLOSURE": ["IDENTITY_LOCKED", "LINEBREAK_FLEXIBLE", "POSITION_FLEXIBLE", "OPTIONAL_AT_TARGET"],
    "BACKGROUND_GRAPHIC": ["POSITION_FLEXIBLE", "SCALE_FLEXIBLE", "CROP_FLEXIBLE"],
    "IMMUTABLE_DESIGN_RELATIONSHIPS": ["RELATIONSHIP_LOCKED", "IMMUTABLE"],
}

PRESERVE = (
    "creative idea",
    "visual identity",
    "project identity",
    "typographic personality",
    "commercial hierarchy",
    "image / type relationship",
    "brand character",
    "campaign message",
)

ALLOW = (
    "crop changes",
    "scale changes",
    "position changes",
    "line-break changes",
    "local typography changes",
    "negative-space redistribution",
    "visual emphasis changes",
    "semantic group movement",
)

CRITICAL_FAILURES = (
    "it looks like a new campaign",
    "it looks like a resized poster",
    "commercial hierarchy collapses",
    "project photo becomes decorative instead of structural",
    "CTA disappears",
    "typography loses personality",
    "logo becomes incorrect",
    "architecture changes",
    "unrelated new creative elements are invented",
    "render a semantic role more than once",
    "leave source-position typography inside PROJECT_PHOTO",
)


def research_proof_master_ids() -> frozenset[str]:
    return RESEARCH_PROOF_MASTER_IDS


def is_research_system_proof(master: dict[str, Any] | None) -> bool:
    if not isinstance(master, dict):
        return False
    if str(master.get("master_id") or "") in RESEARCH_PROOF_MASTER_IDS:
        return True
    if master.get("research") is True:
        return True
    if master.get("quality_benchmark") is False and master.get("role") == "research/system proofs":
        return True
    return False


def is_production_premium_master(master: dict[str, Any] | None) -> bool:
    if not isinstance(master, dict):
        return False
    if is_research_system_proof(master):
        return False
    if master.get("approval_status") != "HUMAN_APPROVED":
        return False
    if master.get("master_type") != "PREMIUM_CAMPAIGN":
        return False
    if master.get("router_eligible") is False:
        return False
    if master.get("production_quality") is True:
        return True
    source = str(master.get("source") or master.get("master_source") or "")
    return source in PRODUCTION_SOURCES


def select_production_premium_master(
    library: dict[str, Any] | None,
    *,
    project_id: str | None = None,
    scope: str | None = None,
    brand_id: str | None = None,
    canonical_format: str = CANONICAL_FORMAT,
) -> dict[str, Any] | None:
    """Return a production HUMAN_APPROVED master. Never silently select Masters 01–03.

    Brand masters are not project masters. A Temple request must not receive
    an Investhome brand master, UniLoft master, or any other project's master.
    """
    if not isinstance(library, dict):
        return None
    want_brand = (scope or "").upper() == "BRAND" or (brand_id and not project_id)
    pool = (
        approved_brand_masters(library, brand_id=brand_id or "INVESTHOME")
        if want_brand
        else approved_masters(library, project_id=project_id)
    )
    candidates = []
    for item in pool:
        if not is_production_premium_master(item):
            continue
        if want_brand and str(item.get("master_scope") or "") != "BRAND":
            continue
        if not want_brand and str(item.get("master_scope") or "PROJECT") == "BRAND":
            continue
        canonical = str(item.get("canonical_format") or CANONICAL_FORMAT)
        if canonical != canonical_format:
            continue
        candidates.append(item)
    return candidates[0] if candidates else None


def missing_master_requirement(library: dict[str, Any] | None = None) -> dict[str, Any]:
    inspected = []
    for item in (library or {}).get("masters") or []:
        inspected.append(
            {
                "master_id": item.get("master_id"),
                "name": item.get("master_name"),
                "approval_status": item.get("approval_status"),
                "router_eligible": item.get("router_eligible"),
                "research_system_proof": is_research_system_proof(item),
                "production_quality": is_production_premium_master(item),
                "source": item.get("source") or item.get("master_source"),
                "canonical_format": item.get("canonical_format"),
            }
        )
    return {
        "schema": "MissingProductionPremiumMasterRequirementV1",
        "status": STATUS_NO_PRODUCTION_MASTER,
        "why": (
            "Stage 4.0 requires one genuinely HUMAN_APPROVED production-quality Premium Master. "
            "Masters 01–03 remain research/system proofs and are not the quality benchmark. "
            "Research proofs are not automatically production masters."
        ),
        "required": {
            "approval": "HUMAN_APPROVED",
            "production_quality": True,
            "source": list(PRODUCTION_SOURCES),
            "canonical_format": CANONICAL_FORMAT,
            "semantic_map": "PremiumSemanticMapV1 extracted AFTER the approved design exists",
            "not": ["Master 01", "Master 02", "Master 03", "archived research candidates"],
        },
        "how_to_unblock": [
            "Ingest an approved finished creative via PremiumMasterIngestionV1",
            "Explicitly human-approve it as a production Premium Master",
            "Do not generate a new autonomous Premium Master",
            "Then retry STAGE 4.0",
        ],
        "research_proof_master_ids": sorted(RESEARCH_PROOF_MASTER_IDS),
        "inspected_masters": inspected,
        "library_masters_01_03_role": (library or {}).get("masters_01_03_role"),
    }


def story_safe_zone_v1() -> dict[str, Any]:
    return {
        "schema": "StorySafeZoneV1",
        "format": PROOF_TARGET_FORMAT,
        "canvas": dict(STORY_CANVAS),
        "not": "a taller 4:5 poster",
        "top_ui_territory": {"y0": 0.0, "y1": 0.12, "protect": ["profile", "time", "close"]},
        "bottom_ui_territory": {"y0": 0.86, "y1": 1.0, "protect": ["reply", "cta chrome", "swipe"]},
        "edge_inset": 0.05,
        "content_well": {"x0": 0.06, "x1": 0.94, "y0": 0.14, "y1": 0.84},
        "critical_content_must_stay_inside_well": [
            "project identity",
            "primary message",
            "offer",
            "price",
            "unit",
            "CTA",
        ],
        "mobile": {
            "reading_distance": "thumb / arm",
            "vertical_visual_rhythm": True,
            "thumb_scale_readability": True,
            "fast_commercial_comprehension_seconds": 2,
        },
        "do_not": ["center the 4:5 composition inside 9:16", "simple resize", "letterbox poster"],
    }


def story_format_intent() -> dict[str, Any]:
    return {
        "schema": "StoryFormatIntentV1",
        "target": "9:16 STORY",
        "is_not": "a taller poster",
        "behavior": [
            "top safe zone",
            "bottom safe zone",
            "mobile reading distance",
            "vertical visual rhythm",
            "thumb-scale readability",
            "fast commercial comprehension",
        ],
        "two_second_read": ["WHAT PROJECT?", "WHAT OPPORTUNITY?", "WHAT PRODUCT / PRICE?", "WHAT ACTION?"],
        "photo": {
            "first_attempt": "adapt the SAME approved project photo",
            "allow": ["crop", "scale", "translation", "focal repositioning"],
            "substitute_only_if": "source photo fundamentally cannot support 9:16 while preserving visual role",
            "substitute_must_be": "another approved REAL project photograph",
            "no_generated_architecture": True,
        },
        "typography_allow": ["font size", "line breaks", "leading", "tracking", "local alignment", "group spacing"],
        "typography_do_not_change": ["copy", "font personality", "fundamental hierarchy"],
        "relationships": {
            "PRICE_UNIT": "clear commercial pair",
            "OFFER_PRIMARY_MESSAGE": "retain hierarchy",
            "CTA": "final action beat",
            "LOGO": "brand identification, not visual hero unless the master says so",
        },
    }


def semantic_lock_flexibility() -> dict[str, Any]:
    return {
        "schema": "FormatSemanticLockFlexibilityV1",
        "elements": [
            {"id": territory, "locks": list(SEMANTIC_LOCK_FLEXIBILITY[territory])}
            for territory in SEMANTIC_TERRITORIES
            if territory in SEMANTIC_LOCK_FLEXIBILITY
        ],
        "examples": {
            "REAL PROJECT PHOTO": ["identity locked", "architecture immutable", "crop flexible", "position flexible"],
            "LOGO": ["identity immutable", "scale limited", "position flexible"],
            "PRICE + UNIT": ["relationship locked", "position flexible", "scale flexible"],
            "HEADLINE": ["copy locked", "line break flexible", "scale flexible"],
            "CTA": ["semantic role locked", "position flexible"],
        },
        "preserve": list(PRESERVE),
        "allow": list(ALLOW),
    }


def story_format_plan(*, master: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema": "StoryFormatPlanV1",
        "adapter": ADAPTER_ID,
        "composition_model": COMPOSITION_MODEL,
        "composition_status": COMPOSITION_STATUS,
        "successor": REPLACED_BY,
        "source_format": CANONICAL_FORMAT,
        "target_format": PROOF_TARGET_FORMAT,
        "principle": "SEMANTIC FORMAT RECOMPOSITION",
        "not": "resize",
        "source_master_id": None if master is None else master.get("master_id"),
        "executed": False,
        "intent": story_format_intent(),
        "safe_zones": story_safe_zone_v1(),
        "lock_flexibility": semantic_lock_flexibility(),
        "recomposition_from": "PremiumSemanticMapV1",
        "never_from": "raw pixel coordinates",
        "doctrine": ["DESIGN FIRST", "SEMANTICS SECOND", "EDITABILITY THIRD"],
        "gpt_image_redesign": False,
        "final_pixels_from": [
            "approved master assets",
            "real project assets",
            "deterministic composition tools",
        ],
    }


def format_master_fidelity_audit_schema() -> dict[str, Any]:
    return {
        "schema": "FormatMasterFidelityAuditV1",
        "status": "NOT_EXECUTED",
        "scores": {
            "CREATIVE IDEA PRESERVATION": None,
            "VISUAL IDENTITY PRESERVATION": None,
            "TYPOGRAPHIC CHARACTER": None,
            "COMMERCIAL HIERARCHY": None,
            "PHOTO ROLE": None,
            "BRAND CHARACTER": None,
            "READING PATH": None,
        },
        "thumbnail": {"100%": None, "50%": None, "25%": None, "15%": None},
        "critical_failures": list(CRITICAL_FAILURES),
        "child_may_look_compositionally_different": True,
        "must_unmistakably_belong_to_same_campaign": True,
        "automated_pass_does_not_approve": True,
    }


def semantic_lineage_schema(*, parent_master_id: str | None = None, child_id: str | None = None) -> dict[str, Any]:
    return {
        "schema": "PremiumFormatSemanticLineageV1",
        "status": "NOT_CREATED" if parent_master_id is None else "READY",
        "PARENT_MASTER_ID": parent_master_id,
        "FORMAT_CHILD_ID": child_id,
        "TARGET_FORMAT": PROOF_TARGET_FORMAT,
        "ADAPTATION_OPERATIONS": [],
        "semantic_map": "PremiumSemanticMapV1",
        "future_revision_example": "This Story’de fiyatı değiştir.",
        "future_revision_territory": "PRICE",
        "revision_implemented_now": False,
        "child_linked_to_premium_master": bool(parent_master_id and child_id),
    }


def adapter_contract() -> dict[str, Any]:
    return {
        "schema": ADAPTER_ID,
        "composition_model": COMPOSITION_MODEL,
        "composition_status": COMPOSITION_STATUS,
        "replaced_by": REPLACED_BY,
        "input": ["Premium Master", "PremiumSemanticMapV1", "target format"],
        "output": "Format Child",
        "proof_scope": {
            "source": CANONICAL_FORMAT,
            "target": "9:16 STORY",
            "identity": STAGE4_PROOF_SCOPE,
            "not": STAGE4_PROOF_SCOPE_FORBIDDEN,
            "only_one_target": True,
        },
        "not_in_this_stage": ["1:1", "16:9", "Reel", "video", "animation", "publishing", "live Creative Studio UI"],
        "do_not": [
            "generate a new creative concept",
            "redesign the advertisement",
            "improve the master",
            "use autonomous premium generation",
            "silently use Masters 01–03 as the production source",
        ],
        "project_reality": {
            "firewall": "ProjectRealityFirewallV1",
            "architecture_fidelity": 10,
            "generated_project_pixels": 0,
            "real_project_logo": "preserved",
        },
        "human_review": "PENDING HUMAN REVIEW until explicit human approval",
        "semantic_map": premium_semantic_map_v1(),
        "safe_zones": story_safe_zone_v1(),
        "lock_flexibility": semantic_lock_flexibility(),
    }


def adapt_premium_master_to_format(
    library: dict[str, Any] | None,
    *,
    target_format: str = PROOF_TARGET_FORMAT,
    project_id: str | None = None,
    scope: str | None = None,
    brand_id: str | None = None,
    execute: bool = False,
) -> dict[str, Any]:
    """Gate + plan. Reposition composition is deprecated; use PremiumFormatRecomposerV1."""
    if target_format != PROOF_TARGET_FORMAT:
        return {
            "schema": ADAPTER_ID,
            "status": STATUS_FAIL,
            "reason": "Stage 4.0 proof supports only 9:16 STORY",
            "executed": False,
            "format_child": None,
        }
    selected = select_production_premium_master(
        library,
        project_id=project_id,
        scope=scope,
        brand_id=brand_id,
    )
    if selected is None:
        return {
            "schema": ADAPTER_ID,
            "status": STATUS_NO_PRODUCTION_MASTER,
            "executed": False,
            "format_child": None,
            "source_master": None,
            "plan": story_format_plan(master=None),
            "semantic_map": None,
            "lineage": semantic_lineage_schema(),
            "fidelity_audit": format_master_fidelity_audit_schema(),
            "requirement": missing_master_requirement(library),
            "gpt_image_calls": 0,
        }
    return {
        "schema": ADAPTER_ID,
        "status": STATUS_PENDING_REVIEW,
        "executed": False,
        "format_child": None,
        "source_master_id": selected.get("master_id"),
        "plan": story_format_plan(master=selected),
        "composition_model": COMPOSITION_MODEL,
        "composition_status": COMPOSITION_STATUS,
        "successor": REPLACED_BY,
        "note": (
            "A production Premium Master is registered. "
            "Reposition composition is deprecated. Use PremiumFormatRecomposerV1."
            if not execute
            else "Production master present; reposition composition is deprecated. Use PremiumFormatRecomposerV1."
        ),
    }
