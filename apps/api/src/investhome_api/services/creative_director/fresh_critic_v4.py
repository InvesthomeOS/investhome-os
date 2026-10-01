"""Fresh Critic V4 — artwork only, Hybrid V2 publish questions."""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.fresh_critic_v3 import QUESTIONS as V3_QUESTIONS
from investhome_api.services.creative_director.fresh_critic_v3 import REQUIRED as V3_REQUIRED

SCHEMA = "FreshCriticV4"

QUESTIONS = (
    "PROFESSIONAL_CREATIVE_AGENCY",
    "CLEAR_VISUAL_IDEA",
    "TEMPLE_SPECIFIC",
    "PHOTO_GRAPHIC_INTEGRATION_SOPHISTICATED",
    "TYPOGRAPHY_PROFESSIONALLY_ART_DIRECTED",
    "COMMERCIAL_MESSAGE_PART_OF_IDEA",
    "COMMERCIAL_INFORMATION_FEELS_ATTACHED",
    "CLEAR_COMMERCIAL_HIERARCHY",
    "PERSUASIVE",
    "MEMORABLE",
    "TEMPLATE",
    "WOULD_PUBLISH",
)

REQUIRED = {
    "PROFESSIONAL_CREATIVE_AGENCY": "YES",
    "CLEAR_VISUAL_IDEA": "YES",
    "TEMPLE_SPECIFIC": "YES",
    "PHOTO_GRAPHIC_INTEGRATION_SOPHISTICATED": "YES",
    "TYPOGRAPHY_PROFESSIONALLY_ART_DIRECTED": "YES",
    "COMMERCIAL_MESSAGE_PART_OF_IDEA": "YES",
    "COMMERCIAL_INFORMATION_FEELS_ATTACHED": "NO",
    "CLEAR_COMMERCIAL_HIERARCHY": "YES",
    "PERSUASIVE": "YES",
    "MEMORABLE": "YES",
    "TEMPLATE": "NO",
    "WOULD_PUBLISH": "YES",
}


def fresh_critic_v4_contract() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "shown": "artwork only — no phase number, no previous failure, no desired score, no concept explanation",
        "questions": list(QUESTIONS),
        "required": dict(REQUIRED),
        "v3_questions_preserved": list(V3_QUESTIONS),
        "v3_required_preserved": dict(V3_REQUIRED),
        "status": "READY",
    }


def score_fresh_critic_v4(answers: dict[str, str]) -> dict[str, Any]:
    payload = {key: str((answers or {}).get(key) or "").upper() for key in QUESTIONS}
    failures = [key for key, expected in REQUIRED.items() if payload.get(key) != expected]
    return {
        "schema": "FreshCriticV4Result",
        "answers": payload,
        "failures": failures,
        "pass": not failures,
        "action_if_fail": "HYBRID_V2_CREATIVE_FAIL",
        "shown": "final artwork only",
    }
