"""Drawing version comparison."""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.document import Document
from investhome_api.models.drawing_intelligence import DrawingAnalysis, DrawingElement, DrawingVersionComparison
from investhome_api.services.drawing_intelligence.activity import record_version_compared


def compare_drawing_versions(
    db: Session,
    *,
    parent_document_id: UUID,
    from_version_id: UUID,
    to_version_id: UUID,
    user_id: UUID,
) -> DrawingVersionComparison:
    from_doc = db.get(Document, from_version_id)
    to_doc = db.get(Document, to_version_id)
    if from_doc is None or to_doc is None:
        raise ValueError("version_not_found")
    if from_doc.parent_document_id != parent_document_id or to_doc.parent_document_id != parent_document_id:
        if from_doc.id != parent_document_id and to_doc.id != parent_document_id:
            raise ValueError("version_mismatch")

    from_analysis = db.scalar(
        select(DrawingAnalysis).where(DrawingAnalysis.document_id == from_version_id)
    )
    to_analysis = db.scalar(
        select(DrawingAnalysis).where(DrawingAnalysis.document_id == to_version_id)
    )

    from_elements = []
    to_elements = []
    if from_analysis:
        from_elements = db.scalars(
            select(DrawingElement).where(DrawingElement.analysis_id == from_analysis.id)
        ).all()
    if to_analysis:
        to_elements = db.scalars(
            select(DrawingElement).where(DrawingElement.analysis_id == to_analysis.id)
        ).all()

    from_labels = {e.label for e in from_elements if e.label}
    to_labels = {e.label for e in to_elements if e.label}
    added = sorted(to_labels - from_labels)
    removed = sorted(from_labels - to_labels)

    from_scale = (from_analysis.scale_corrected or from_analysis.scale_detected) if from_analysis else None
    to_scale = (to_analysis.scale_corrected or to_analysis.scale_detected) if to_analysis else None
    scale_changed = from_scale != to_scale

    changes = {
        "added_labels": added[:20],
        "removed_labels": removed[:20],
        "scale_changed": scale_changed,
        "from_scale": from_scale,
        "to_scale": to_scale,
        "from_element_count": len(from_elements),
        "to_element_count": len(to_elements),
    }

    summary_en = (
        f"Version comparison: {len(added)} added, {len(removed)} removed element(s)."
        + (" Scale changed." if scale_changed else "")
    )
    summary_tr = (
        f"Sürüm karşılaştırması: {len(added)} eklenen, {len(removed)} kaldırılan öğe."
        + (" Ölçek değişti." if scale_changed else "")
    )

    comparison = DrawingVersionComparison(
        parent_document_id=parent_document_id,
        from_version_id=from_version_id,
        to_version_id=to_version_id,
        summary=summary_tr,
        summary_en=summary_en,
        changes_json=json.dumps(changes),
        created_by_user_id=user_id,
    )
    db.add(comparison)
    db.flush()

    parent = db.get(Document, parent_document_id) or to_doc
    record_version_compared(db, parent, user_id, from_version_id, to_version_id, summary_en)
    return comparison
