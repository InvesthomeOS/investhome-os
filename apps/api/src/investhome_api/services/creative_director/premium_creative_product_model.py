"""Premium Creative Product Model — two modes. Autonomous Premium generation disabled.

AI is a Premium Creative Operator, not an autonomous Premium Designer.
"""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.creative_master_router_v2 import (
    COPY_EDIT_ONLY,
    FAMILY_WIDE_REVISION,
    FORMAT_ADAPTATION,
    NEW_CREATIVE_REQUEST,
    PRICE_EDIT_ONLY,
    VISUAL_REPLACE_ONLY,
    classify_production_intent,
    select_approved_master,
)
from investhome_api.services.creative_director.hybrid_premium_engine_v1 import ENGINE_ID as HYBRID_V1
from investhome_api.services.creative_director.hybrid_premium_engine_v2 import ENGINE_ID as HYBRID_V2
from investhome_api.services.creative_director.idea_first_pipeline import PIPELINE_ID as IDEA_FIRST
from investhome_api.services.creative_director.integrated_campaign_pipeline import INTEGRATED_PIPELINE_ID
from investhome_api.services.creative_director.phase10_3_revision_doctrine import (
    COPY_LEARNING,
    MASTER_IMMUTABILITY,
    PERMANENT_RULE,
    PHOTO_LEARNING,
    PRICE_LEARNING,
    PROJECT_REALITY_POLICY,
    REVISION_DOCTRINE,
    STAGE_2_STATUS,
    revision_doctrine,
)
from investhome_api.services.creative_director.project_creative_master_library import (
    AI_QUICK_GATES,
    LIBRARY_SCHEMA,
    PRODUCTION_LEVELS,
)
from investhome_api.services.creative_director.premium_creative_family_v1 import (
    route_family_wide_revision,
    route_format_request,
)
from investhome_api.services.creative_director.phase13_0_final_lock import (
    NEXT_PRODUCT_WORK,
    live_creative_studio_lock,
)
from investhome_api.services.creative_director.stage3_canonical_pipeline import is_explicit_ai_quick

PRODUCT_MODEL_ID = "PREMIUM_CREATIVE_PRODUCT_MODEL_V1"
STATUS = "PREMIUM_CREATIVE_PRODUCT_MODEL_LOCKED"
AI_ROLE = "PREMIUM_CREATIVE_OPERATOR"
NEXT_STAGE = "STAGE 4 — PREMIUM FORMAT ADAPTATION"

PREMIUM_REQUEST_MARKERS = (
    "premium",
    "kampanya",
    "lansman",
    "flagship",
    "agency",
    "ajans",
)

MASTER_SOURCES = (
    "HUMAN_DESIGNER",
    "INVESTHOME_APPROVED",
    "USER_UPLOADED_APPROVED",
    "HISTORICAL_APPROVED",
    "SYSTEM_GENERATED_HUMAN_APPROVED",
)

SEMANTIC_TERRITORIES = (
    "PROJECT",
    "MASTER_ASSET",
    "CANONICAL_FORMAT",
    "LOGO",
    "PROJECT_PHOTO",
    "HEADLINE",
    "SUBHEAD",
    "OFFER",
    "PRICE",
    "UNIT",
    "CTA",
    "CLOSURE",
    "BACKGROUND_GRAPHIC",
    "IMMUTABLE_DESIGN_RELATIONSHIPS",
)

NL_OPERATIONS = (
    "PRICE_ONLY",
    "HEADLINE_ONLY",
    "COPY_ONLY",
    "PROJECT_PHOTO_REPLACE_ONLY",
    "CTA_ONLY",
    "OFFER_ONLY",
    "UNIT_ONLY",
    "LOGO_REPLACE_ONLY",
)

RESEARCH_PATHS = (
    {
        "id": "OLD_PREMIUM_COMPILER",
        "files": ["phase11_4_compose.py"],
        "quality_ceiling": 6,
        "status": "RESEARCH_ARCHIVED",
    },
    {
        "id": IDEA_FIRST,
        "files": ["idea_first_pipeline.py"],
        "quality_ceiling": None,
        "status": "RESEARCH_ARCHIVED",
    },
    {
        "id": INTEGRATED_PIPELINE_ID,
        "files": ["integrated_campaign_pipeline.py"],
        "quality_ceiling": None,
        "status": "RESEARCH_ARCHIVED",
    },
    {
        "id": HYBRID_V1,
        "files": ["hybrid_premium_engine_v1.py"],
        "quality_ceiling": 8,
        "status": "RESEARCH_ARCHIVED",
    },
    {
        "id": HYBRID_V2,
        "files": ["hybrid_premium_engine_v2.py"],
        "quality_ceiling": 8,
        "status": "RESEARCH_ARCHIVED",
    },
    {
        "id": "AI_NATIVE_PREMIUM_EXPERIMENT",
        "files": ["phase11_10_master.py"],
        "quality_ceiling": "PROJECT_REALITY_FAIL",
        "status": "RESEARCH_ARCHIVED",
    },
    {
        "id": "REFERENCE_GUIDED_PREMIUM_EXPERIMENT",
        "files": ["phase11_11_master.py"],
        "quality_ceiling": "QUALITY_FAIL",
        "status": "RESEARCH_ARCHIVED",
    },
    {
        "id": "PREMIUM_FORMAT_ADAPTER_REPOSITION",
        "files": ["premium_format_adapter_v1.py"],
        "status": "RESEARCH_ARCHIVED",
    },
    {
        "id": "PREMIUM_FORMAT_RECOMPOSER_AUTONOMOUS",
        "files": ["premium_format_recomposer_v1.py"],
        "quality_ceiling": "DESIGN_QUALITY_FAIL",
        "status": "NON_PRODUCTION",
        "human_decision": "REJECTED",
        "production_route": False,
    },
    {
        "id": "PREMIUM_STORY_RECOMPOSER_EXPERIMENT",
        "files": ["premium_story_recomposer_v1.py", "stage4_1_recompose.py"],
        "quality_ceiling": "DESIGN_QUALITY_FAIL",
        "status": "NON_PRODUCTION",
        "human_decision": "REJECTED",
        "production_route": False,
    },
)


def research_conclusion() -> dict[str, Any]:
    return {
        "schema": "PremiumCreativeResearchConclusionV1",
        "decision": "STOP autonomous premium creative quality experimentation",
        "cannot_satisfy_simultaneously": [
            "PUBLISHABILITY / AGENCY-LEVEL QUALITY",
            "PROJECT REALITY / ARCHITECTURE FIDELITY",
            "RELIABLE AUTOMATED PRODUCTION",
        ],
        "evidence": {
            "OLD_PROGRAMMATIC_COMPILER": 6,
            "HYBRID_V1": 7,
            "HYBRID_V1_FINISH": 8,
            "HYBRID_V2": 8,
            "AI_NATIVE": "PROJECT_REALITY_FAIL",
            "REFERENCE_GUIDED": "QUALITY_FAIL",
        },
        "do_not_create": [
            "Hybrid V3",
            "another reference reconstruction",
            "another AI-native experiment",
            "another Temple creative proof",
            "another renderer architecture",
            "13.1 proof",
            "13.2 proof",
            "new format engines",
            "new Premium generation experiments",
        ],
        "ai_role_shift": {
            "from": "AUTONOMOUS PREMIUM DESIGNER",
            "to": AI_ROLE,
        },
        "masters_01_03": "RESEARCH_SYSTEM_PROOF_NOT_QUALITY_BENCHMARK",
        "delete_research": False,
    }


def ai_quick_creative_contract() -> dict[str, Any]:
    return {
        "schema": "AiQuickCreativeContractV1",
        "mode": "A",
        "name": "AI QUICK CREATIVE",
        "status": "ACTIVE",
        "premium": False,
        "purpose": ["fast", "automatic", "convenient", "good-enough everyday creative"],
        "may_generate_automatically": True,
        "must_not_be_represented_as": [
            "Premium Master",
            "agency-level campaign",
            "human-approved creative",
        ],
        "required_gates": list(AI_QUICK_GATES),
        "production_levels": list(PRODUCTION_LEVELS),
        "default_when": "project has no suitable HUMAN_APPROVED Premium Master",
        "never_silently_label_premium": True,
    }


def premium_master_contract() -> dict[str, Any]:
    return {
        "schema": "PremiumMasterContractV1",
        "mode": "B",
        "name": "PREMIUM MASTER",
        "status": "LOCKED",
        "purpose": ["high-quality", "brand-critical", "campaign-critical", "launch-quality"],
        "begins_from": "HUMAN-APPROVED DESIGN",
        "sources_may_include": [
            "approved Investhome creative",
            "approved designer creative",
            "approved uploaded design",
            "approved externally produced campaign",
            "approved historical Investhome design",
        ],
        "system_does_not_invent_initial_master": True,
        "ai_role": AI_ROLE,
        "operator_jobs": [
            "understanding approved design",
            "understanding semantic territories",
            "using correct project assets",
            "performing natural-language revisions",
            "preserving unrelated design",
            "adapting approved creative to formats",
            "creating campaign derivatives",
            "creating Story / Reel / video derivatives",
            "maintaining project reality",
            "maintaining brand consistency",
        ],
        "human_approval_required": True,
        "router_eligible_only_if": "HUMAN_APPROVED",
        "ingested_master_until_human_approval": False,
        "source_categories": list(MASTER_SOURCES),
        "system_generated_becomes_premium_only_after": "explicit human approval",
        "masters_01_03": {
            "preserve": True,
            "delete": False,
            "role": "research/system proofs",
            "quality_benchmark": False,
            "automatic_treatment_as_desired_quality": False,
        },
    }


def premium_master_ingestion_v1() -> dict[str, Any]:
    return {
        "schema": "PremiumMasterIngestionV1",
        "status": "READY",
        "executed": False,
        "input": ["approved finished creative", "project identity"],
        "registers": list(SEMANTIC_TERRITORIES),
        "doctrine": ["DESIGN FIRST", "SEMANTICS SECOND", "EDITABILITY THIRD"],
        "never_force_design_from_map": True,
        "output": {
            "MASTER_ID": "uuid",
            "PROJECT_ID": "uuid",
            "SOURCE": MASTER_SOURCES,
            "APPROVAL": "HUMAN_APPROVED",
            "CANONICAL_ASSET": "asset_id",
            "CANONICAL_FORMAT": "4:5 unless ingested otherwise",
            "SEMANTIC_MAP": "PremiumSemanticMapV1",
            "REVISION_HISTORY": [],
            "FORMAT_CHILDREN": [],
            "CAMPAIGN_CHILDREN": [],
            "STATUS": "HUMAN_APPROVED",
        },
    }


def premium_semantic_map_v1() -> dict[str, Any]:
    return {
        "schema": "PremiumSemanticMapV1",
        "status": "READY",
        "extracted": "AFTER the design exists",
        "never_originate_design_from_map": True,
        "territories": [
            {"id": "PROJECT", "role": "identity of the project the master belongs to"},
            {"id": "MASTER_ASSET", "role": "canonical finished creative raster/vector"},
            {"id": "CANONICAL_FORMAT", "role": "native frame of the approved design"},
            {"id": "LOGO", "role": "real project logo territory"},
            {"id": "PROJECT_PHOTO", "role": "approved real project photography territories"},
            {"id": "HEADLINE", "role": "primary verbal territory"},
            {"id": "SUBHEAD", "role": "supporting verbal territory"},
            {"id": "OFFER", "role": "commercial offer / % territory"},
            {"id": "PRICE", "role": "price territory"},
            {"id": "UNIT", "role": "unit / product territory"},
            {"id": "CTA", "role": "action territory"},
            {"id": "CLOSURE", "role": "editorial close / tagline territory"},
            {"id": "BACKGROUND_GRAPHIC", "role": "non-project graphic / field territories"},
            {"id": "IMMUTABLE_DESIGN_RELATIONSHIPS", "role": "locked relationships the operator must preserve"},
        ],
        "library_schema": LIBRARY_SCHEMA,
    }


def premium_revision_contract() -> dict[str, Any]:
    doctrine = revision_doctrine()
    return {
        "schema": "PremiumRevisionContractV1",
        "status": "READY / PRESERVED",
        "stage_2": STAGE_2_STATUS,
        "doctrine": REVISION_DOCTRINE,
        "permanent_rule": PERMANENT_RULE,
        "approved_master_immutability": MASTER_IMMUTABILITY,
        "text_revision": {
            "rule": "reconstruct only the clean semantic target territory",
            "do_not": "destructively paint over old glyphs",
            "allow": "local responsive recomposition inside the target territory",
            "learning": {"PRICE": PRICE_LEARNING, "COPY": COPY_LEARNING},
        },
        "photo_replacement": {
            "design_geometry": "LOCKED",
            "new_photo": "real project photo adapts to the approved design",
            "unrelated_territories": "unchanged",
            "learning": PHOTO_LEARNING,
        },
        "operations": {
            "PRICE_ONLY": {
                "status": "READY / PRESERVED",
                "maps_to": PRICE_EDIT_ONLY,
                "example": "Fiyatı 750.000 USD yap, başka hiçbir şeyi değiştirme.",
            },
            "HEADLINE_ONLY": {
                "status": "READY / PRESERVED",
                "maps_to": COPY_EDIT_ONLY,
                "territory": "HEADLINE",
                "example": "Başlığı ŞİMDİ YATIRIM ZAMANI yap, başka hiçbir şeyi değiştirme.",
            },
            "COPY_ONLY": {"status": "READY / PRESERVED", "maps_to": COPY_EDIT_ONLY},
            "PROJECT_PHOTO_REPLACE_ONLY": {
                "status": "READY / PRESERVED",
                "maps_to": VISUAL_REPLACE_ONLY,
                "example": "Sağdaki dış cepheyi başka gerçek Temple dış cephesiyle değiştir.",
            },
            "CTA_ONLY": {"status": "READY / PRESERVED", "maps_to": COPY_EDIT_ONLY, "territory": "CTA"},
            "OFFER_ONLY": {"status": "READY / PRESERVED", "maps_to": COPY_EDIT_ONLY, "territory": "OFFER"},
            "UNIT_ONLY": {"status": "READY / PRESERVED", "maps_to": COPY_EDIT_ONLY, "territory": "UNIT"},
            "LOGO_REPLACE_ONLY": {
                "status": "READY / PRESERVED",
                "when": "explicitly requested",
                "real_project_logo_mandatory": True,
            },
        },
        "format_adaptation": {
            "status": "DISABLED",
            "maps_to": FORMAT_ADAPTATION,
            "autonomous_design": False,
            "engine": "PremiumCreativeFamilyV1",
            "on_missing": "PREMIUM_FORMAT_MASTER_MISSING",
            "archived": [
                "PremiumFormatAdapterV1",
                "PremiumFormatRecomposerV1",
                "PremiumStoryRecomposerV1",
            ],
            "stage_4_1": "PREMIUM_FORMAT_RECOMPOSITION_FAIL",
            "production_route": False,
        },
        "family_wide_revision": {
            "status": "PRODUCTION READY",
            "maps_to": FAMILY_WIDE_REVISION,
            "uses": "Stage 2 Revision Router per format master",
            "never_invent_missing_semantic": True,
            "legitimate_skip_is_not_fail": True,
            "result_model": ["COMPLETE_SUCCESS", "PARTIAL_SUCCESS", "FAIL"],
            "executed": True,
        },
        "stage_2_capabilities": doctrine["capabilities"],
    }


def project_reality_contract() -> dict[str, Any]:
    return {
        "schema": "ProjectRealityContractV1",
        "status": "LOCKED",
        "policy": PROJECT_REALITY_POLICY,
        "for_project_creatives": {
            "approved_real_project_photography": "mandatory by default",
            "ai_must_not_invent": ["architecture", "interiors", "exteriors", "project logo"],
            "exception": "user explicitly requests generated project imagery",
        },
        "reusable": ["ProjectRealityFirewallV1", "ProjectObjectExtractionV2"],
    }


def routing_model() -> dict[str, Any]:
    return {
        "schema": "CreativeStudioRoutingModelV1",
        "ai_quick_creative": "ACTIVE",
        "autonomous_premium_generation": "DISABLED",
        "premium_master_source": "HUMAN_APPROVED CREATIVE FAMILY",
        "when_no_human_approved_premium_master": {
            "default_automatic": "AI QUICK CREATIVE",
            "label": "never silently Premium",
            "if_user_asks_premium_kampanya_lansman": (
                "surface that no approved Premium Master is available "
                "and allow creation/import/approval workflow"
            ),
        },
        "when_suitable_approved_premium_master_exists": {
            "Temple için post hazırla.": "select suitable approved Temple master",
            "Bunu Story yap.": (
                "Look up the Premium Creative Family. If 9:16 is HUMAN_APPROVED, use that format master. "
                "If missing, return PREMIUM_FORMAT_MASTER_MISSING. Do not fabricate a Premium Story."
            ),
            "Fiyatı değiştir.": "targeted Stage 2 revision of the current format master",
            "Bu kampanyadaki fiyatı tüm formatlarda 750.000 USD yap.": "FAMILY_WIDE_REVISION",
            "Başka dış cephe kullan.": "real-project visual replacement within current master",
        },
        "new_creative_intent": NEW_CREATIVE_REQUEST,
        "premium_request_markers": list(PREMIUM_REQUEST_MARKERS),
        "do_not_fabricate_premium_status": True,
    }


def research_archive_map() -> dict[str, Any]:
    return {
        "schema": "ResearchArchiveMapV1",
        "status": "ARCHIVED",
        "delete_code": False,
        "delete_artifacts": False,
        "active_autonomous_premium_route": None,
        "paths": list(RESEARCH_PATHS),
        "note": "Reusable utilities may be harvested later. These paths must not produce Premium Masters autonomously.",
    }


def reusable_capabilities() -> dict[str, Any]:
    return {
        "schema": "ReusableCapabilitiesV1",
        "status": "PRESERVED",
        "keep": [
            "ProjectObjectExtractionV2",
            "ProjectRealityFirewallV1",
            "ResponsiveCommercialHierarchyV2",
            "Premium Master Library",
            "Stage 2 Revision Router",
            "target territory reconstruction",
            "real project photo replacement",
            "Design Reference Library",
            "SemanticLayerExclusivityV1",
            "PremiumCreativeFamilyV1",
        ],
        "may_support": ["Stage 5 Story/Reel/video derivatives"],
    }


def next_stage_roadmap() -> dict[str, Any]:
    return {
        "schema": "PremiumProductRoadmapV1",
        "next": NEXT_PRODUCT_WORK,
        "live_creative_studio": live_creative_studio_lock(),
        "stage_4_0": {
            "status": "CLOSED",
            "visual_proof": "REJECTED",
            "production_route": False,
        },
        "stage_4_1": {
            "status": "PREMIUM_FORMAT_RECOMPOSITION_FAIL",
            "technical_integrity": "PASS",
            "design_quality": "FAIL",
            "human_decision": "REJECTED",
            "production_route": False,
        },
        "then": [
            NEXT_PRODUCT_WORK,
            "PUBLISHING / EXPORT",
        ],
        "not_executed_now": ["new Premium format generation", "publishing platform"],
        "require_additional_proof_before_product_work": False,
        "new_creative_generated": False,
    }


def product_model() -> dict[str, Any]:
    return {
        "schema": PRODUCT_MODEL_ID,
        "status": STATUS,
        "ai_role": AI_ROLE,
        "modes": {"A": ai_quick_creative_contract(), "B": premium_master_contract()},
        "ingestion": premium_master_ingestion_v1(),
        "semantic_map": premium_semantic_map_v1(),
        "revision": premium_revision_contract(),
        "project_reality": project_reality_contract(),
        "routing": routing_model(),
        "archive": research_archive_map(),
        "reusable": reusable_capabilities(),
        "roadmap": next_stage_roadmap(),
        "research_conclusion": research_conclusion(),
        "live_creative_studio": live_creative_studio_lock(),
    }


def wants_premium_label(user_text: str) -> bool:
    folded = (user_text or "").casefold()
    return any(marker in folded for marker in PREMIUM_REQUEST_MARKERS)


def route_locked_creative_product(
    user_text: str,
    *,
    production_mode: str | None = None,
    workflow: str | None = None,
    library: dict[str, Any] | None = None,
    project_id: str | None = None,
    current_master_id: str | None = None,
) -> dict[str, Any]:
    """Live Creative Studio routing after the product-model lock."""
    if is_explicit_ai_quick(user_text, production_mode, workflow):
        return {
            "schema": "LockedCreativeProductRouteV1",
            "route": "AI_QUICK_CREATIVE",
            "premium": False,
            "autonomous_premium": False,
            "action": "EXPLICIT_AI_QUICK_CREATIVE",
            "label": "AI Quick Creative",
        }
    classified = classify_production_intent(user_text)
    if classified.get("intent") == FORMAT_ADAPTATION:
        formatted = route_format_request(
            classified=classified,
            library=library,
            project_id=project_id,
            current_master_id=current_master_id,
        )
        return {
            "schema": "LockedCreativeProductRouteV1",
            "route": formatted["route"],
            "premium": formatted["route"] != "PREMIUM_FORMAT_MASTER_MISSING",
            "autonomous_premium": False,
            "action": formatted["action"],
            "status": formatted.get("status"),
            "revision_intent": FORMAT_ADAPTATION,
            "selected_master_id": formatted.get("selected_master_id"),
            "executed": False,
            "allow": formatted.get("allow"),
            "message": formatted.get("message"),
        }
    if classified.get("intent") == FAMILY_WIDE_REVISION:
        wide = route_family_wide_revision(
            classified=classified,
            library=library,
            project_id=project_id,
            current_master_id=current_master_id,
        )
        return {
            "schema": "LockedCreativeProductRouteV1",
            "route": "FAMILY_WIDE_REVISION",
            "premium": True,
            "autonomous_premium": False,
            "action": wide["action"],
            "revision_intent": FAMILY_WIDE_REVISION,
            "family_wide": wide,
            "executed": False,
        }
    if classified.get("is_revision"):
        return {
            "schema": "LockedCreativeProductRouteV1",
            "route": "MASTER_DERIVED_REVISION",
            "premium": True,
            "autonomous_premium": False,
            "action": "REVISE_EXISTING_APPROVED_MASTER",
            "revision_intent": classified.get("intent"),
            "selected_master_id": current_master_id,
        }
    selected = None
    if library and project_id:
        selected = select_approved_master(
            library,
            project_id=project_id,
            preference=classified.get("preference"),
            target_format=str(classified.get("target_format") or "4:5"),
        )
    if selected:
        return {
            "schema": "LockedCreativeProductRouteV1",
            "route": "PROJECT_PREMIUM_MASTER",
            "premium": True,
            "autonomous_premium": False,
            "action": "OPERATE_APPROVED_MASTER",
            "selected_master_id": selected.get("master_id"),
            "label": "Premium Master",
        }
    if wants_premium_label(user_text):
        return {
            "schema": "LockedCreativeProductRouteV1",
            "route": "NO_APPROVED_PREMIUM_MASTER",
            "premium": False,
            "autonomous_premium": False,
            "action": "SURFACE_NO_APPROVED_PREMIUM_MASTER",
            "allow": ["AI_QUICK_CREATIVE", "PREMIUM_MASTER_INGESTION"],
            "do_not_fabricate_premium_status": True,
            "message": (
                "No approved Premium Master is available. "
                "Create, import, or approve a human-approved design. "
                "Do not silently label AI Quick Creative as Premium."
            ),
        }
    return {
        "schema": "LockedCreativeProductRouteV1",
        "route": "AI_QUICK_CREATIVE",
        "premium": False,
        "autonomous_premium": False,
        "action": "DEFAULT_AI_QUICK_CREATIVE",
        "label": "AI Quick Creative",
    }
