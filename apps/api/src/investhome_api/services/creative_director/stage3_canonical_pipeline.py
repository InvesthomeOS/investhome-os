"""Canonical Stage 3 premium generation path. Archives competing premium engines."""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.creative_master_router_v2 import (
    NEW_CREATIVE_REQUEST,
    classify_production_intent,
)
from investhome_api.services.creative_director.idea_first_pipeline import PIPELINE_ID as SUPERSEDED_IDEA_FIRST_PATH
from investhome_api.services.creative_director.idea_first_pipeline import idea_first_pipeline
from investhome_api.services.creative_director.integrated_campaign_pipeline import (
    INTEGRATED_PIPELINE_ID,
    integrated_campaign_pipeline,
)

CANONICAL_PREMIUM_PATH = INTEGRATED_PIPELINE_ID
SUPERSEDED_PREMIUM_PATH = SUPERSEDED_IDEA_FIRST_PATH
EXPLICIT_QUICK_MARKERS = ("hızlı creative", "hizli creative", "ai quick", "quick creative", "hızlı reklam")

LEGACY_PREMIUM_PATHS = (
    {
        "id": "chromium_html_locked_master_compositor",
        "files": ["phase8_2_compose.py", "phase9_0_compose.py", "phase9_1_compose.py"],
        "status": "ARCHIVED_FOR_NEW_PREMIUM_GENERATION",
        "kept_for": "locked Masters 01–03 as proven system masters; not a quality ceiling",
    },
    {
        "id": "gpt_image_project_mode_generate_ad",
        "files": ["generate_ad.py", "gpt_image_design/service.py"],
        "status": "ARCHIVED_FOR_PREMIUM",
        "kept_for": "explicit non-premium / finished-ad product modes only",
    },
    {
        "id": "phase5_gpt_designer",
        "files": ["phase5_workflow.py"],
        "status": "ARCHIVED",
        "kept_for": "research history; workflow=phase5 is not premium Stage 3",
    },
    {
        "id": "golden_native_v1_designspec",
        "files": ["generate_ad.py", "design_spec.py"],
        "status": "ARCHIVED_FOR_PREMIUM",
        "kept_for": "editable finished-ad experiments, not premium campaign generation",
    },
    {
        "id": "structured_reconstruction",
        "files": ["structured_reconstruction.py", "phase5_5b_r1_structured_reconstruction.py"],
        "status": "ARCHIVED",
        "kept_for": "research",
    },
    {
        "id": "generative_master_director",
        "files": ["generative_master_director.py", "phase5_generative_master.py"],
        "status": "ARCHIVED",
        "kept_for": "research",
    },
    {
        "id": "graphic_design_compositor_v3_v5",
        "files": ["graphic_design_compositor_v3.py", "compositor_relational_v4.py"],
        "status": "ARCHIVED",
        "kept_for": "research",
    },
    {
        "id": "router_populate_approved_master_as_new_premium",
        "files": ["creative_master_router_v2.py"],
        "status": "ARCHIVED_FOR_NEW_PREMIUM_GENERATION",
        "kept_for": "reusing an approved Master when the user is not asking for a new campaign idea",
    },
)

ACTIVE_PREMIUM_PATHS_BEFORE = 8


def is_explicit_ai_quick(user_text: str | None = None, production_mode: str | None = None, workflow: str | None = None) -> bool:
    folded = (user_text or "").casefold()
    if any(marker in folded for marker in EXPLICIT_QUICK_MARKERS):
        return True
    if (production_mode or "").casefold() in {"ai_quick", "quick"}:
        return True
    if (workflow or "").casefold() in {"quick", "ai_quick_creative"}:
        return True
    return False


def is_premium_new_request(user_text: str) -> bool:
    classified = classify_production_intent(user_text)
    if classified.get("is_revision"):
        return False
    folded = (user_text or "").casefold()
    premium = classified.get("preference") == "PREMIUM_CAMPAIGN" or "premium" in folded or "lansman reklam" in folded
    return classified.get("intent") == NEW_CREATIVE_REQUEST and premium


def route_premium_generation(user_text: str, *, production_mode: str | None = None, workflow: str | None = None) -> dict[str, Any]:
    if is_explicit_ai_quick(user_text, production_mode, workflow):
        return {
            "schema": "Stage3GenerationRouteV1",
            "route": "AI_QUICK_CREATIVE",
            "canonical": False,
            "premium": False,
            "action": "EXPLICIT_AI_QUICK_CREATIVE",
            "executed": False,
        }
    if is_premium_new_request(user_text):
        return {
            "schema": "Stage3GenerationRouteV1",
            "route": CANONICAL_PREMIUM_PATH,
            "canonical": True,
            "premium": True,
            "action": "PREPARE_INTEGRATED_CAMPAIGN_PIPELINE",
            "executed": False,
            "reason": (
                "Premium requests use STAGE3_INTEGRATED_CAMPAIGN_PIPELINE. "
                "No silent GPT Image / template / reconstruction fallback. "
                "Idea-first is superseded."
            ),
        }
    return {
        "schema": "Stage3GenerationRouteV1",
        "route": "NOT_PREMIUM_NEW_GENERATION",
        "canonical": False,
        "action": "DEFER_TO_EXISTING_ROUTER_OR_REVISION",
        "executed": False,
    }


def maybe_refuse_legacy_premium_generation(
    ctx: dict[str, Any],
    *,
    user_text: str,
    production_mode: str | None = None,
    workflow: str | None = None,
) -> dict[str, Any] | None:
    """Refuse autonomous Premium generation. AI Quick and Stage 2 revisions remain."""
    blob = dict((ctx or {}).get("phase5") or {})
    if blob.get("premium_creative_product_model_locked"):
        from investhome_api.services.creative_director.premium_creative_product_model import (
            route_locked_creative_product,
        )
        from investhome_api.services.creative_director.phase5_workflow import TEMPLE_PROJECT_ID

        if is_explicit_ai_quick(user_text, production_mode, workflow):
            return None
        routed = route_premium_generation(user_text, production_mode=production_mode, workflow=workflow)
        if routed.get("route") != CANONICAL_PREMIUM_PATH:
            return None
        locked_route = route_locked_creative_product(
            user_text,
            production_mode=production_mode,
            workflow=workflow,
            library=blob.get("project_creative_master_library") if isinstance(blob.get("project_creative_master_library"), dict) else None,
            project_id=TEMPLE_PROJECT_ID,
        )
        return {
            "refuse": True,
            "status": "AUTONOMOUS_PREMIUM_GENERATION_DISABLED",
            "canonical_path": None,
            "locked_route": locked_route,
            "detail": (
                "Autonomous Premium Master creation is disabled. "
                "Premium Masters begin from a human-approved design. "
                "Do not fabricate premium status. "
                "Use an approved Premium Master as operator, ingest/approve a design, "
                "or use AI Quick Creative."
            ),
        }
    locked = bool(blob.get("stage3_premium_generation_locked"))
    if not locked:
        return None
    routed = route_premium_generation(user_text, production_mode=production_mode, workflow=workflow)
    if routed.get("route") != CANONICAL_PREMIUM_PATH:
        return None
    return {
        "refuse": True,
        "status": "STAGE3_CANONICAL_PATH_REQUIRED",
        "canonical_path": CANONICAL_PREMIUM_PATH,
        "detail": (
            "Premium campaign generation is locked to STAGE3_INTEGRATED_CAMPAIGN_PIPELINE. "
            "STAGE3_IDEA_FIRST_PREMIUM_PIPELINE is superseded. "
            "Legacy GPT Image, template renderer, structured reconstruction, and locked-master "
            "imitation are refused for this request."
        ),
    }


def generation_path_audit() -> dict[str, Any]:
    return {
        "schema": "GenerationPathAuditV1",
        "active_premium_generation_paths_before": ACTIVE_PREMIUM_PATHS_BEFORE,
        "canonical_premium_generation_path": CANONICAL_PREMIUM_PATH,
        "superseded_premium_path": SUPERSEDED_PREMIUM_PATH,
        "legacy_premium_paths": list(LEGACY_PREMIUM_PATHS),
        "legacy_status": "ARCHIVED",
        "ai_quick_creative": "separate explicit product mode",
        "pipeline": integrated_campaign_pipeline(),
        "superseded_pipeline": idea_first_pipeline(),
        "stage_3_executed": False,
    }
