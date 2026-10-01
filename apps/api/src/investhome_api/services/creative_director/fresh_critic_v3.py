"""Fresh Critic V3 — blind review including commercial-message-as-idea."""

from __future__ import annotations

from typing import Any

SCHEMA = "FreshCriticV3"

QUESTIONS = (
    "PROFESSIONAL_CREATIVE_AGENCY",
    "CLEAR_VISUAL_IDEA",
    "PROJECT_SPECIFIC",
    "COMMERCIAL_MESSAGE_PART_OF_IDEA",
    "COMMERCIAL_INFORMATION_FEELS_ATTACHED",
    "CLEAR_READING_PATH",
    "PERSUASIVE",
    "MEMORABLE_AFTER_TWO_SECONDS",
    "LOOKS_LIKE_TEMPLATE",
    "WOULD_PUBLISH",
)

REQUIRED = {
    "PROFESSIONAL_CREATIVE_AGENCY": "YES",
    "CLEAR_VISUAL_IDEA": "YES",
    "PROJECT_SPECIFIC": "YES",
    "COMMERCIAL_MESSAGE_PART_OF_IDEA": "YES",
    "COMMERCIAL_INFORMATION_FEELS_ATTACHED": "NO",
    "CLEAR_READING_PATH": "YES",
    "PERSUASIVE": "YES",
    "MEMORABLE_AFTER_TWO_SECONDS": "YES",
    "LOOKS_LIKE_TEMPLATE": "NO",
    "WOULD_PUBLISH": "YES",
}

ADVERTISEMENT_QUESTION = "Does this look like an advertisement designed to persuade, or a beautiful poster with sales information added?"


def fresh_critic_v3_contract() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "shown": "artwork only — no phase number, no previous failure, no desired score, no concept explanation",
        "questions": list(QUESTIONS),
        "required": dict(REQUIRED),
        "advertisement_vs_poster": {
            "question": ADVERTISEMENT_QUESTION,
            "allowed": "DESIGNED ADVERTISEMENT",
            "fail": "POSTER + SALES INFORMATION",
        },
        "status": "READY",
    }


def score_fresh_critic_v3(answers: dict[str, str]) -> dict[str, Any]:
    payload = {key: str((answers or {}).get(key) or "").upper() for key in QUESTIONS}
    failures = [key for key, expected in REQUIRED.items() if payload.get(key) != expected]
    return {
        "schema": "FreshCriticV3Result",
        "answers": payload,
        "failures": failures,
        "pass": not failures,
        "action_if_fail": "CREATIVE_QUALITY_PROOF_FAIL",
    }


def proof_01_fresh_v3_would_fail() -> dict[str, Any]:
    return score_fresh_critic_v3(
        {
            "PROFESSIONAL_CREATIVE_AGENCY": "NO",
            "CLEAR_VISUAL_IDEA": "YES",
            "PROJECT_SPECIFIC": "YES",
            "COMMERCIAL_MESSAGE_PART_OF_IDEA": "NO",
            "COMMERCIAL_INFORMATION_FEELS_ATTACHED": "YES",
            "CLEAR_READING_PATH": "NO",
            "PERSUASIVE": "NO",
            "MEMORABLE_AFTER_TWO_SECONDS": "YES",
            "LOOKS_LIKE_TEMPLATE": "NO",
            "WOULD_PUBLISH": "NO",
        }
    )


def proof_02_fresh_v3_would_fail() -> dict[str, Any]:
    return score_fresh_critic_v3(
        {
            "PROFESSIONAL_CREATIVE_AGENCY": "NO",
            "CLEAR_VISUAL_IDEA": "YES",
            "PROJECT_SPECIFIC": "YES",
            "COMMERCIAL_MESSAGE_PART_OF_IDEA": "NO",
            "COMMERCIAL_INFORMATION_FEELS_ATTACHED": "YES",
            "CLEAR_READING_PATH": "NO",
            "PERSUASIVE": "NO",
            "MEMORABLE_AFTER_TWO_SECONDS": "YES",
            "LOOKS_LIKE_TEMPLATE": "NO",
            "WOULD_PUBLISH": "NO",
        }
    )
