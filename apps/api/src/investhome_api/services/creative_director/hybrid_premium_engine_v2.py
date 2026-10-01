"""STAGE3_HYBRID_PREMIUM_ENGINE_V2 — experimental capability upgrade.

V1 proved the hybrid architecture. Phase 11.7 showed the remaining gap is
production capability, not concept. V2 adds three capabilities:

1. ProjectObjectExtractionV2
2. SceneMaterialIntegrationV2
3. ResponsiveCommercialHierarchyV2

Not the canonical Stage 3 router. No campaign is generated from this module.
"""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.hybrid_premium_engine_v1 import (
    MATERIAL_CLASSES as V1_MATERIALS,
    NOT_IMPLEMENTED as V1_NOT_IMPLEMENTED,
    PIPELINE_STEPS as V1_PIPELINE,
)

ENGINE_ID = "STAGE3_HYBRID_PREMIUM_ENGINE_V2"
ENGINE_VERSION = "2.0"
SCHEMA = "HybridPremiumEngineV2"
PARENT_ENGINE = "STAGE3_HYBRID_PREMIUM_ENGINE_V1"

CAPABILITIES = (
    "PROJECT_OBJECT_EXTRACTION_V2",
    "SCENE_MATERIAL_INTEGRATION_V2",
    "RESPONSIVE_COMMERCIAL_HIERARCHY_V2",
)


def hybrid_engine_v2_contract() -> dict[str, Any]:
    materials = dict(V1_MATERIALS)
    materials["A_REAL_PROJECT_OBJECTS"] = {
        **dict(V1_MATERIALS["A_REAL_PROJECT_OBJECTS"]),
        "v2_allowed": (
            "edge-aware matting",
            "alpha reconstruction",
            "background-color decontamination",
            "halo suppression",
            "semi-transparent edge reconstruction",
            "non-destructive exposure / curves / white balance",
            "contact occlusion onto non-project field",
        ),
    }
    return {
        "schema": SCHEMA,
        "engine_id": ENGINE_ID,
        "version": ENGINE_VERSION,
        "parent": PARENT_ENGINE,
        "status": "EXPERIMENTAL",
        "canonical_stage3_router": "UNCHANGED",
        "pipeline": list(V1_PIPELINE),
        "capabilities": list(CAPABILITIES),
        "material_classes": materials,
        "not_implemented": list(V1_NOT_IMPLEMENTED),
        "does_not_generate": (
            "campaign creative",
            "THE_LEDGER R2",
            "Proof 04",
            "Premium Master",
            "Story",
            "Reel",
            "format adaptation",
        ),
    }
