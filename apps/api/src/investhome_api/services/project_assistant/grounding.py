"""Grounding / confidence helpers — never answer without verified evidence."""

from __future__ import annotations

from dataclasses import dataclass

from investhome_api.services.ai_search.hybrid_search import SearchHit
from investhome_api.services.project_assistant.llm_provider import INSUFFICIENT_EVIDENCE_MESSAGE

# Minimum hybrid score to treat retrieval as usable evidence
DEFAULT_MIN_SCORE = 0.12
# Soft floor for "low but present" confidence band
DEFAULT_WEAK_SCORE = 0.22


@dataclass(frozen=True)
class GroundingDecision:
    sufficient: bool
    confidence: float
    message: str | None
    top_score: float


def evaluate_grounding(
    hits: list[SearchHit],
    *,
    min_score: float = DEFAULT_MIN_SCORE,
) -> GroundingDecision:
    """
    Decide whether retrieved chunks are enough to answer.

    Insufficient → fixed message; caller must not invent.
    """
    if not hits:
        return GroundingDecision(
            sufficient=False,
            confidence=0.0,
            message=INSUFFICIENT_EVIDENCE_MESSAGE,
            top_score=0.0,
        )
    top = float(hits[0].score or 0.0)
    if top < min_score:
        return GroundingDecision(
            sufficient=False,
            confidence=round(max(0.0, top), 4),
            message=INSUFFICIENT_EVIDENCE_MESSAGE,
            top_score=top,
        )

    # Map score → confidence in [0.35, 0.95]
    if top >= 0.55:
        confidence = min(0.95, 0.7 + (top - 0.55) * 0.5)
    elif top >= DEFAULT_WEAK_SCORE:
        confidence = 0.45 + (top - DEFAULT_WEAK_SCORE) * 0.8
    else:
        confidence = 0.35 + (top - min_score) * 1.0
    return GroundingDecision(
        sufficient=True,
        confidence=round(min(0.95, max(0.35, confidence)), 4),
        message=None,
        top_score=top,
    )
