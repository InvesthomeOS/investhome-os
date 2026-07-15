"""Drawing-aware question answering."""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.drawing_intelligence import DrawingAnalysis, DrawingElement
from investhome_api.services.document_intelligence.types import SourceReference


def answer_drawing_question(
    db: Session,
    analysis: DrawingAnalysis,
    question: str,
    *,
    locale: str = "en",
) -> tuple[str, list[SourceReference], bool]:
    """Answer questions using drawing elements. Returns answer, sources, grounded."""
    q = question.lower().strip()
    elements = db.scalars(
        select(DrawingElement).where(DrawingElement.analysis_id == analysis.id)
    ).all()

    if "scale" in q or "ölçek" in q:
        scale = analysis.scale_corrected or analysis.scale_detected
        conf = analysis.scale_confidence or "low"
        if scale:
            answer = (
                f"Scale: {scale} (confidence: {conf})"
                if locale == "en"
                else f"Ölçek: {scale} (güven: {conf})"
            )
            if conf == "low":
                answer += " [low confidence]" if locale == "en" else " [düşük güven]"
            return answer, [SourceReference(page=1)], True
        return (
            "Scale not detected in this drawing."
            if locale == "en"
            else "Bu çizimde ölçek tespit edilemedi.",
            [],
            False,
        )

    if "room" in q or "oda" in q:
        rooms = [e for e in elements if e.element_type == "room"]
        if rooms:
            labels = ", ".join(e.label or "?" for e in rooms[:10])
            answer = (
                f"Detected rooms: {labels}"
                if locale == "en"
                else f"Tespit edilen odalar: {labels}"
            )
            return answer, [SourceReference(page=1)], True
        return (
            "No rooms detected."
            if locale == "en"
            else "Oda tespit edilmedi.",
            [],
            False,
        )

    if "wall" in q or "duvar" in q:
        walls = [e for e in elements if e.element_type == "wall"]
        low = [e for e in walls if e.confidence == "low"]
        answer = (
            f"Detected {len(walls)} wall segment(s). {len(low)} marked low-confidence."
            if locale == "en"
            else f"{len(walls)} duvar segmenti tespit edildi. {len(low)} düşük güvenilirlik."
        )
        return answer, [SourceReference(page=1)], bool(walls)

    if "area" in q or "alan" in q:
        areas = [e for e in elements if e.element_type == "area"]
        if areas:
            parts = []
            for area in areas[:5]:
                conf_note = " [low confidence]" if area.confidence == "low" else ""
                parts.append(f"{area.label}: {area.numeric_value} {area.unit}{conf_note}")
            answer = "; ".join(parts)
            return answer, [SourceReference(page=1)], True
        return (
            "No area measurements found."
            if locale == "en"
            else "Alan ölçümü bulunamadı.",
            [],
            False,
        )

    if "sheet" in q or "sayfa" in q:
        count = analysis.sheet_count or 0
        answer = (
            f"This drawing has {count} sheet(s)."
            if locale == "en"
            else f"Bu çizimde {count} sayfa var."
        )
        return answer, [SourceReference(page=1)], count > 0

    if analysis.summary:
        return (
            analysis.summary_en if locale == "en" else analysis.summary,
            [SourceReference(page=1)],
            True,
        )

    return (
        "I could not find an answer in the drawing data."
        if locale == "en"
        else "Çizim verilerinde yanıt bulunamadı.",
        [],
        False,
    )
