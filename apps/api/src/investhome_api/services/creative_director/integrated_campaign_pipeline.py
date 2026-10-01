"""STAGE3_INTEGRATED_CAMPAIGN_PIPELINE — visual + photo + commercial + type as one system."""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.campaign_reading_path_v1 import validate_reading_path
from investhome_api.services.creative_director.idea_first_pipeline import PIPELINE_ID as SUPERSEDED_PIPELINE_ID
from investhome_api.services.creative_director.integrated_campaign_concept import validate_integrated_concept

INTEGRATED_PIPELINE_ID = "STAGE3_INTEGRATED_CAMPAIGN_PIPELINE"

STEPS = (
    "UNDERSTAND_USER_INTENT",
    "UNDERSTAND_PROJECT",
    "INSPECT_REAL_PROJECT_ASSETS",
    "DETERMINE_CAMPAIGN_HIERARCHY",
    "RETRIEVE_COMMERCIAL_AND_VISUAL_DESIGN_DNA",
    "CREATE_INTEGRATED_CAMPAIGN_CONCEPT",
    "BUILD_CAMPAIGN_SKELETON",
    "BUILD_READING_PATH",
    "VISUAL_IDEA_GATE",
    "COMMERCIAL_SYSTEM_GATE",
    "DETACHED_LOCKUP_DETECTOR",
    "THUMBNAIL_TEST",
    "ART_DIRECT_PHOTOGRAPHY_AND_TYPE_AS_ONE_SYSTEM",
    "RENDER",
    "CRITIC_V3_AND_FRESH_CRITIC_V3",
    "HUMAN_APPROVAL",
)

FORBIDDEN_STARTS = (
    "art first, information later",
    "template",
    "text boxes",
    "headline coordinates",
    "renderer primitives",
    "left-side information column",
    "populate locked master as the quality ceiling",
    "GPT Image as project architect",
    "giant %35 badge",
    "property listing layout",
)


def integrated_campaign_pipeline() -> dict[str, Any]:
    return {
        "schema": "IntegratedCampaignPipelineV1",
        "pipeline_id": INTEGRATED_PIPELINE_ID,
        "status": "CANONICAL",
        "supersedes": SUPERSEDED_PIPELINE_ID,
        "steps": list(STEPS),
        "forbidden_starts": list(FORBIDDEN_STARTS),
        "render_step_index": STEPS.index("RENDER") + 1,
        "human_approval_is_final": True,
        "executed": False,
        "phase_11_0_lessons_retained": [
            "real project photography only",
            "Grade-A design DNA as principles not layouts",
            "no-copy / visual idea gate",
            "two-second test",
            "anti-template detector",
            "project reality",
            "human approval is final",
        ],
        "doctrine": (
            "VISUAL IDEA + PROJECT PHOTOGRAPHY + COMMERCIAL MESSAGE + TYPOGRAPHY "
            "must be conceived as ONE SYSTEM. There is no separate art-first stage."
        ),
    }


def may_proceed_to_render_integrated(
    *,
    concept: dict[str, Any],
    visual_gate: dict[str, Any],
    commercial_gate: dict[str, Any],
    lockup: dict[str, Any],
    thumbnail: dict[str, Any],
    reading_path: dict[str, Any],
) -> bool:
    return bool(
        validate_integrated_concept(concept).get("pass")
        and visual_gate.get("pass")
        and commercial_gate.get("pass")
        and lockup.get("pass")
        and thumbnail.get("pass")
        and validate_reading_path(reading_path).get("pass")
    )


def integrated_pipeline_markdown() -> str:
    pipe = integrated_campaign_pipeline()
    lines = [
        "# 11 Stage 3 integrated campaign pipeline",
        "",
        f"OLD: `{pipe['supersedes']}`",
        "STATUS: SUPERSEDED",
        "",
        f"NEW: `{pipe['pipeline_id']}`",
        "STATUS: CANONICAL",
        "",
        pipe["doctrine"],
        "",
        "Locked generation order:",
        "",
    ]
    for i, step in enumerate(pipe["steps"], 1):
        lines.append(f"{i}. {step.replace('_', ' ')}")
    lines.extend(
        [
            "",
            "Do not start with art and add campaign information later.",
            "Do not reactivate legacy premium paths.",
            "AI Quick Creative remains a separate explicit product mode.",
            "This pipeline is registered in Phase 11.3. It is not executed as Proof 03 here.",
            "Executed: NO.",
        ]
    )
    return "\n".join(lines) + "\n"

