"""Idea-first premium pipeline. Render is step 11, not step 1."""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.creative_strategy_v1 import STRATEGY_FIELDS, validate_creative_strategy

PIPELINE_ID = "STAGE3_IDEA_FIRST_PREMIUM_PIPELINE"

STEPS = (
    "UNDERSTAND_USER_INTENT",
    "UNDERSTAND_PROJECT",
    "INSPECT_REAL_PROJECT_ASSETS",
    "DETERMINE_CAMPAIGN_STORY",
    "RETRIEVE_RELEVANT_DESIGN_DNA",
    "CREATE_VISUAL_IDEA",
    "TEST_IDEA_WITHOUT_COPY",
    "ART_DIRECT_PHOTOGRAPHY",
    "BUILD_TYPOGRAPHIC_SYSTEM",
    "BUILD_COMMERCIAL_HIERARCHY",
    "RENDER",
    "HUMAN_STYLE_CREATIVE_CRITIQUE",
    "HUMAN_APPROVAL",
)

FORBIDDEN_STARTS = (
    "template",
    "text boxes",
    "headline coordinates",
    "renderer primitives",
    "populate locked master as the quality ceiling",
    "GPT Image as project architect",
)


def idea_first_pipeline() -> dict[str, Any]:
    return {
        "schema": "IdeaFirstPipelineV1",
        "pipeline_id": PIPELINE_ID,
        "steps": list(STEPS),
        "forbidden_starts": list(FORBIDDEN_STARTS),
        "render_step_index": STEPS.index("RENDER") + 1,
        "human_approval_is_final": True,
        "executed": False,
        "status": "SUPERSEDED",
        "superseded_by": "STAGE3_INTEGRATED_CAMPAIGN_PIPELINE",
        "reason": (
            "Idea-first still produced poster-plus-sales-information. "
            "Phase 11.0 lessons are retained; the canonical path is now integrated campaign."
        ),
    }


def no_copy_test(*, visual_mechanism: str, photography_participates: bool, feels_designed_without_copy: bool) -> dict[str, Any]:
    mechanism = bool(str(visual_mechanism or "").strip()) and str(visual_mechanism).casefold() not in {
        "a property photo with text",
        "photo plus headline",
        "none",
    }
    passed = feels_designed_without_copy and mechanism and photography_participates
    return {
        "schema": "NoCopyTestV1",
        "feels_intentionally_designed_without_copy": feels_designed_without_copy,
        "clear_visual_mechanism": mechanism,
        "photography_participates": photography_participates,
        "visual_mechanism": visual_mechanism,
        "pass": passed,
        "action_if_fail": "DO_NOT_CONTINUE_TO_TYPOGRAPHY",
    }


def two_second_test(answer: str | None) -> dict[str, Any]:
    text = str(answer or "").strip()
    failed_answers = {
        "",
        "a property photo with text",
        "photo plus headline",
        "photo + text",
        "listing",
        "brochure",
    }
    passed = bool(text) and text.casefold() not in failed_answers
    return {
        "schema": "TwoSecondTestV1",
        "question": "What does the viewer perceive in the first two seconds?",
        "answer": text or None,
        "pass": passed,
        "fail_if": "a property photo with text",
    }


def may_proceed_to_typography(no_copy: dict[str, Any], strategy: dict[str, Any] | None = None) -> bool:
    if not no_copy.get("pass"):
        return False
    if strategy is not None and not validate_creative_strategy(strategy).get("pass"):
        return False
    return True


def may_proceed_to_render(*, no_copy: dict[str, Any], two_seconds: dict[str, Any], strategy: dict[str, Any]) -> bool:
    return bool(
        no_copy.get("pass")
        and two_seconds.get("pass")
        and validate_creative_strategy(strategy).get("pass")
        and all(strategy.get(field) for field in STRATEGY_FIELDS)
    )
