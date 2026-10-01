"""STAGE3_HYBRID_PREMIUM_ENGINE_V1 — minimum hybrid premium production method.

Architecture D (Phase 11.5): real project photo objects + AI non-project
creative field + advanced SVG/vector typography.

This module is a quality proof of the production method. It is not yet the
canonical Stage 3 router. Stage 2 revision, format adaptation, and master
routing are intentionally absent.
"""

from __future__ import annotations

from typing import Any

ENGINE_ID = "STAGE3_HYBRID_PREMIUM_ENGINE_V1"
ENGINE_VERSION = "1.0"
SCHEMA = "HybridPremiumEngineV1"

PIPELINE_STEPS = (
    "CAMPAIGN_STRATEGY",
    "REAL_PROJECT_PHOTO_OBJECT_SELECTION",
    "NON_PROJECT_CREATIVE_FIELD_GENERATION",
    "ADVANCED_PHOTO_FIELD_COMPOSITION",
    "ADVANCED_SVG_VECTOR_TYPOGRAPHY",
    "COMMERCIAL_ART_DIRECTION",
    "FINAL_HIGH_RESOLUTION_RENDER",
    "HUMAN_VISUAL_REVIEW",
)

MATERIAL_CLASSES = {
    "A_REAL_PROJECT_OBJECTS": {
        "allowed": (
            "crop",
            "scale",
            "position",
            "mask",
            "isolate",
            "clip",
            "color_grade",
            "non_destructive_tonal_adjustment",
        ),
        "forbidden": (
            "AI repainting of architecture",
            "AI architectural extension",
            "AI window invention",
            "AI façade modification",
            "AI interior modification",
        ),
    },
    "B_GENERATED_CREATIVE_FIELD": {
        "allowed": (
            "paper",
            "material field",
            "abstract geometry",
            "light",
            "atmosphere",
            "texture",
            "graphic surfaces",
            "editorial field",
            "shadow",
            "color environment",
            "non-project visual devices",
        ),
        "forbidden": (
            "buildings",
            "Temple architecture",
            "fake project imagery",
            "fake project logo",
            "fake factual text",
        ),
    },
    "C_VECTOR_TYPOGRAPHIC_SYSTEM": {
        "allowed": (
            "SVG text",
            "clipping",
            "masks",
            "overlap",
            "rotation",
            "controlled transparency",
            "layering",
            "graphic geometry",
        ),
        "forbidden": (
            "independent absolutely positioned fact boxes as the composition method",
            "Pillow flattened photographic plate as the page",
            "website CTA button",
            "%35 badge",
            "price card",
            "footer fact row",
            "left/right information stack",
        ),
    },
}

NOT_IMPLEMENTED = (
    "Stage 2 revision support for the new engine",
    "format adaptation",
    "Story",
    "Reel",
    "video",
    "master routing",
    "production publishing",
    "full Creative Studio integration",
)


def hybrid_engine_contract() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "engine_id": ENGINE_ID,
        "version": ENGINE_VERSION,
        "pipeline": list(PIPELINE_STEPS),
        "material_classes": MATERIAL_CLASSES,
        "old_compiler_forbidden_for_final": (
            "Pillow flattened photo + primitive masks/washes + absolutely positioned HTML/CSS facts + Chromium screenshot"
        ),
        "final_renderer": "Chromium screenshot of an SVG scene graph (field image + masked photo object + SVG text)",
        "canonical_stage3_router": "UNCHANGED — this engine is a quality proof only",
        "not_implemented": list(NOT_IMPLEMENTED),
        "status": "MINIMUM_VIABLE_QUALITY_PROOF",
    }
