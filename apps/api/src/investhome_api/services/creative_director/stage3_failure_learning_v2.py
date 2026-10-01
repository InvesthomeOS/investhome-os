"""Stage3FailureLearningV2 — Proof 01 and Proof 02 as one systemic diagnosis.

Do not broaden. The engine can invent visual ideas. It cannot yet turn them
into complete commercial campaign systems.
"""

from __future__ import annotations

from typing import Any

SCHEMA = "Stage3FailureLearningV2"

STAGE3_FAILURE_LEARNING_V2: dict[str, Any] = {
    "schema": SCHEMA,
    "proof_01": {
        "status": "CREATIVE_REJECTED",
        "preserved": True,
        "visual_idea": 8,
        "art_direction": 7,
        "photo_integration": 7,
        "commercial_hierarchy": 7,
        "publishability": 6,
        "fresh": {
            "CLEAR_IDEA": "YES",
            "MEMORABLE": "YES",
            "COMMERCIAL_MESSAGE_DESIGNED": "NO",
            "WOULD_PUBLISH": "NO",
        },
        "failure_mode": "clever visual device; commercial facts as a left inscription stack",
    },
    "proof_02": {
        "status": "CREATIVE_REJECTED",
        "preserved": True,
        "visual_idea": 8,
        "art_direction": 7,
        "photo_integration": 8,
        "commercial_hierarchy": 7,
        "publishability": 6,
        "fresh": {
            "CLEAR_IDEA": "YES",
            "TEMPLE_SPECIFIC": "YES",
            "MEMORABLE": "YES",
            "COMMERCIAL_MESSAGE_DESIGNED": "NO",
            "WOULD_PUBLISH": "NO",
        },
        "failure_mode": "project-specific photograph; commercial facts as a left information column on a washed façade",
    },
    "repeated_failure": "DETACHED_COMMERCIAL_LOCKUP — CREATIVE VISUAL + LEFT-SIDE INFORMATION COLUMN",
    "systemic_failure_identified": True,
    "systemic_conclusion": (
        "THE ENGINE CAN GENERATE DISTINCT VISUAL IDEAS. "
        "THE ENGINE CANNOT YET CONSISTENTLY TURN THOSE IDEAS INTO COMPLETE COMMERCIAL CAMPAIGN SYSTEMS."
    ),
    "incorrect_diagnosis": "the visual ideas were not good enough",
    "root_cause": (
        "The Stage 3 pipeline still conceives art first and places campaign information afterwards, "
        "so the commercial message is content inserted into the art instead of part of the art direction."
    ),
    "correction": "Replace idea-first with an integrated campaign concept pipeline. Do not revise Proof 01 or Proof 02.",
    "do_not": [
        "GENERATE PROOF 03 in this phase",
        "CREATE AN R1 OF PROOF 01",
        "CREATE AN R1 OF PROOF 02",
        "reinterpret either fail as success",
        "lower quality gates",
        "solve integration with badges, stickers, banners, or listing UI",
    ],
}


def stage3_failure_learning_v2() -> dict[str, Any]:
    return dict(STAGE3_FAILURE_LEARNING_V2)
