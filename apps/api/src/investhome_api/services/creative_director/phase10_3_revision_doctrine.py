"""Phase 10.3 — permanent natural-language revision doctrine.

Locked after human visual proof of price, copy, and project-photo revision.
Does not render pixels. Does not start Stage 3.
"""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.creative_master_router_v2 import (
    COPY_EDIT_ONLY,
    PRICE_EDIT_ONLY,
    VISUAL_REPLACE_ONLY,
)
from investhome_api.services.creative_director.phase7_2_doctrine import PROJECT_CREATIVE_RULE

REVISION_DOCTRINE = "NATURAL_LANGUAGE_FIRST"
STAGE_2_STATUS = "COMPLETE"
NEXT_PHASE = "STAGE 3 — CREATIVE QUALITY ENGINE"
USER_NEVER_SPECIFIES = (
    "layer IDs",
    "coordinates",
    "masks",
    "bounding boxes",
    "asset slots",
    "renderer commands",
    "technical revision types",
)

PERMANENT_RULE = (
    "X'i değiştir, başka hiçbir şeyi değiştirme. "
    "Identify the semantic target. Preserve unrelated creative. "
    "Reconstruct only the minimum necessary target territory. "
    "Adapt the requested element professionally. "
    "Never regenerate the complete artwork unless the user asks for a new design."
)

PRICE_LEARNING = (
    "Preservation is the creative outside the target, not every raster pixel "
    "inside the target. Inside the territory: quality first. "
    "Cleanly reconstruct when required. No glyph painting over old text, "
    "ghosting, dirty masks, or visible patches."
)

COPY_LEARNING = (
    "Different-length copy may require local responsive recomposition "
    "inside the semantic target territory only. "
    "Do not distort typography to keep old coordinates."
)

PHOTO_LEARNING = (
    "For VISUAL_REPLACE_ONLY, design geometry is locked. "
    "The new photo adapts to the design. The design does not rebuild "
    "around the new photo. Crop, scale, translation, and focal position "
    "may adapt professionally inside the photo territory."
)

PROJECT_REALITY_POLICY = (
    "Real approved project photography is mandatory by default. "
    "AI must not invent architecture, interiors, exteriors, or the project logo "
    "unless the user explicitly asks for AI-generated project imagery."
)

MASTER_IMMUTABILITY = (
    "Approved Premium Masters remain immutable. "
    "Revisions create CHILD revisions. Never overwrite the HUMAN_APPROVED parent Master."
)

STAGE_3_SUCCESS_GATE = (
    "A creative is successful only when the human user would actually publish it "
    "as a premium InvestHome campaign. Technical critic PASS is not sufficient."
)


def revision_doctrine() -> dict[str, Any]:
    return {
        "schema": "NaturalLanguageRevisionDoctrineV1",
        "doctrine": REVISION_DOCTRINE,
        "status": STAGE_2_STATUS,
        "product_experience": "natural language only",
        "user_never_specifies": list(USER_NEVER_SPECIFIES),
        "permanent_rule": PERMANENT_RULE,
        "steps": [
            "identify semantic target",
            "preserve all unrelated creative decisions",
            "reconstruct only the minimum necessary target territory",
            "adapt the requested element professionally",
            "never regenerate the complete artwork unless the user explicitly asks for a new design",
        ],
        "capabilities": {
            PRICE_EDIT_ONLY: {
                "status": "HUMAN_APPROVED",
                "learning": PRICE_LEARNING,
                "inside_target": "QUALITY_FIRST",
                "outside_target": "PRESERVE_CREATIVE",
            },
            COPY_EDIT_ONLY: {
                "status": "HUMAN_APPROVED",
                "learning": COPY_LEARNING,
                "local_responsive_recomposition": True,
            },
            VISUAL_REPLACE_ONLY: {
                "status": "HUMAN_APPROVED",
                "learning": PHOTO_LEARNING,
                "design_geometry": "LOCKED",
                "photo_adapts_to_design": True,
                "project_reality_rule": PROJECT_CREATIVE_RULE,
            },
        },
        "project_reality_policy": PROJECT_REALITY_POLICY,
        "approved_master_immutability": MASTER_IMMUTABILITY,
        "stage_3_success_gate": STAGE_3_SUCCESS_GATE,
        "stage_3_executed": False,
        "format_work_executed": False,
        "next_phase": NEXT_PHASE,
    }
