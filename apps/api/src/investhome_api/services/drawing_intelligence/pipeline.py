"""Drawing processing pipeline."""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.document import Document, DocumentType, ProcessingStatus
from investhome_api.models.drawing_intelligence import (
    DrawingAnalysis,
    DrawingElement,
    DrawingSheet,
    DrawingUnitProposal,
)
from investhome_api.services.drawing_intelligence.activity import (
    record_drawing_processing_completed,
    record_drawing_processing_failed,
    record_drawing_processing_started,
    record_unit_proposal_created,
)
from investhome_api.services.drawing_intelligence.config import (
    DRAWING_GEOMETRY_SUBDIR,
    DRAWING_MAX_ELEMENTS,
    DRAWING_MAX_GEOMETRY_BYTES,
    DRAWING_PREVIEW_SUBDIR,
    should_process_as_drawing,
)
from investhome_api.services.drawing_intelligence.conversion import (
    convert_drawing,
    detect_discipline_from_texts,
    detect_scale_from_texts,
)
from investhome_api.services.drawing_intelligence.detection import detect_elements, detect_sheets
from investhome_api.services.drawing_intelligence.types import ParsedGeometry
from investhome_api.services.storage.factory import get_storage_provider

logger = logging.getLogger(__name__)

IN_FLIGHT_STATUSES = {
    "converting",
    "extracting_geometry",
    "detecting_elements",
    "analyzing",
    "queued",
}


def _get_or_create_analysis(db: Session, document: Document) -> DrawingAnalysis:
    if document.drawing_analysis:
        return document.drawing_analysis
    analysis = DrawingAnalysis(
        document_id=document.id,
        document_version_id=document.id,
        processing_status="uploaded",
        source_format=document.file_extension,
    )
    db.add(analysis)
    db.flush()
    document.drawing_analysis = analysis
    return analysis


def _store_preview(document_id: uuid.UUID, svg: str) -> str:
    settings = get_settings()
    root = Path(settings.document_storage_root) / DRAWING_PREVIEW_SUBDIR
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{document_id}.svg"
    path.write_text(svg, encoding="utf-8")
    return str(path)


def _store_geometry(document_id: uuid.UUID, geometry: ParsedGeometry) -> tuple[str, int]:
    settings = get_settings()
    root = Path(settings.document_storage_root) / DRAWING_GEOMETRY_SUBDIR
    root.mkdir(parents=True, exist_ok=True)
    payload = {
        "bounds": (
            {
                "min_x": geometry.bounds.min_x,
                "min_y": geometry.bounds.min_y,
                "max_x": geometry.bounds.max_x,
                "max_y": geometry.bounds.max_y,
            }
            if geometry.bounds
            else None
        ),
        "path_count": len(geometry.paths),
        "text_count": len(geometry.texts),
        "layer_count": geometry.layer_count,
        "entity_count": geometry.entity_count,
    }
    content = json.dumps(payload)
    if len(content.encode("utf-8")) > DRAWING_MAX_GEOMETRY_BYTES:
        content = content[:DRAWING_MAX_GEOMETRY_BYTES]
    path = root / f"{document_id}.json"
    path.write_text(content, encoding="utf-8")
    return str(path), len(content.encode("utf-8"))


def _document_type_value(document: Document) -> str:
    value = document.document_type
    return value.value if isinstance(value, DocumentType) else str(value)


def _set_status(db: Session, document: Document, analysis: DrawingAnalysis, status: str) -> None:
    analysis.processing_status = status
    if status == "completed":
        document.processing_status = ProcessingStatus.COMPLETED
    elif status == "failed":
        document.processing_status = ProcessingStatus.FAILED
    elif status == "not_supported":
        document.processing_status = ProcessingStatus.NOT_SUPPORTED
    else:
        document.processing_status = ProcessingStatus.PROCESSING
    db.flush()


def process_drawing(db: Session, document_id: uuid.UUID, *, force: bool = False) -> None:
    """Run drawing intelligence pipeline. Original CAD files are never modified."""
    started = time.perf_counter()
    document = db.get(Document, document_id)
    if document is None:
        logger.warning("Document %s not found for drawing processing", document_id)
        return

    if not document.is_latest_version and not force:
        logger.info("Skipping drawing processing for non-current version %s", document_id)
        return

    ext = document.file_extension.lower().lstrip(".")
    doc_type = _document_type_value(document)
    if not should_process_as_drawing(ext, doc_type):
        return

    analysis = _get_or_create_analysis(db, document)
    if not force and analysis.processing_status in IN_FLIGHT_STATUSES:
        logger.info("Drawing %s already processing (%s)", document_id, analysis.processing_status)
        return
    if not force and analysis.processing_status == "completed":
        return

    analysis.document_version_id = document.id
    analysis.retry_count = (analysis.retry_count or 0) + (1 if force else 0)
    analysis.processing_started_at = datetime.now(UTC)
    analysis.processing_error = None
    _set_status(db, document, analysis, "queued")
    db.commit()
    record_drawing_processing_started(db, document)
    db.commit()

    try:
        storage = get_storage_provider()
        source_path = Path(storage.get_local_path(document.storage_key))

        _set_status(db, document, analysis, "converting")
        db.commit()
        result = convert_drawing(source_path, ext)
        analysis.conversion_method = result.method
        analysis.preview_status = "unavailable" if result.preview_unavailable else "ready"

        if not result.success and ext == "dwg":
            analysis.processing_error = result.error
            analysis.preview_status = "unavailable"
            _set_status(db, document, analysis, "preview_unavailable")
            analysis.processed_at = datetime.now(UTC)
            db.commit()
            record_drawing_processing_completed(db, document)
            db.commit()
            return

        if not result.success:
            raise RuntimeError(result.error or "conversion_failed")

        geometry = result.geometry
        texts = geometry.texts if geometry else []

        _set_status(db, document, analysis, "extracting_geometry")
        db.commit()
        if geometry and result.preview_svg:
            analysis.preview_storage_key = _store_preview(document.id, result.preview_svg)
        if geometry:
            key, size = _store_geometry(document.id, geometry)
            analysis.geometry_storage_key = key
            analysis.geometry_size_bytes = size

        scale, scale_conf = detect_scale_from_texts(texts)
        discipline, discipline_conf = detect_discipline_from_texts(texts, doc_type)
        analysis.scale_detected = scale
        analysis.scale_confidence = scale_conf
        analysis.discipline = discipline
        analysis.discipline_confidence = discipline_conf
        analysis.drawing_type = "floor_plan" if "FLOOR" in " ".join(t[0] for t in texts).upper() else "unknown"
        analysis.drawing_type_confidence = "high" if analysis.drawing_type == "floor_plan" else "low"

        _set_status(db, document, analysis, "detecting_elements")
        db.commit()

        for sheet in analysis.sheets:
            db.delete(sheet)
        for element in analysis.elements:
            db.delete(element)
        for proposal in analysis.unit_proposals:
            db.delete(proposal)
        db.flush()

        sheets = detect_sheets(geometry, texts) if geometry else []
        sheet_models: list[DrawingSheet] = []
        for sheet in sheets:
            model = DrawingSheet(
                analysis_id=analysis.id,
                sheet_index=sheet.sheet_index,
                sheet_name=sheet.sheet_name,
                sheet_number=sheet.sheet_number,
                sheet_type=sheet.sheet_type,
                confidence=sheet.confidence,
                width=sheet.width,
                height=sheet.height,
            )
            db.add(model)
            sheet_models.append(model)
        db.flush()
        analysis.sheet_count = len(sheet_models)

        elements = detect_elements(geometry, texts) if geometry else []
        title_blocks: list[dict] = []
        schedules: list[dict] = []
        for detected in elements[:DRAWING_MAX_ELEMENTS]:
            sheet_id = sheet_models[0].id if sheet_models else None
            db.add(
                DrawingElement(
                    analysis_id=analysis.id,
                    sheet_id=sheet_id,
                    element_type=detected.element_type,
                    label=detected.label,
                    value_text=detected.value_text,
                    numeric_value=detected.numeric_value,
                    unit=detected.unit,
                    confidence=detected.confidence,
                    geometry_json=json.dumps(detected.geometry) if detected.geometry else None,
                    metadata_json=json.dumps(detected.metadata) if detected.metadata else None,
                )
            )
            if detected.element_type == "title_block":
                title_blocks.append({"label": detected.label, "confidence": detected.confidence})
            if detected.element_type == "schedule":
                schedules.append({"label": detected.label, "confidence": detected.confidence})
            if detected.element_type == "unit":
                db.add(
                    DrawingUnitProposal(
                        analysis_id=analysis.id,
                        unit_label=detected.label or "Unit",
                        confidence=detected.confidence,
                        status="proposed",
                    )
                )
                record_unit_proposal_created(db, document, detected.label or "Unit")

        analysis.title_block_json = json.dumps(title_blocks) if title_blocks else None
        analysis.schedules_json = json.dumps(schedules) if schedules else None

        _set_status(db, document, analysis, "analyzing")
        db.commit()

        room_count = sum(1 for e in elements if e.element_type == "room")
        wall_count = sum(1 for e in elements if e.element_type == "wall")
        low_conf = sum(1 for e in elements if e.confidence == "low")
        analysis.summary = (
            f"Mimari çizim analizi tamamlandı. {len(sheet_models)} sayfa, "
            f"{room_count} oda, {wall_count} duvar tespit edildi. "
            f"{low_conf} düşük güvenilirlikli ölçüm işaretlendi."
        )
        analysis.summary_en = (
            f"Drawing analysis complete. {len(sheet_models)} sheet(s), "
            f"{room_count} room(s), {wall_count} wall(s) detected. "
            f"{low_conf} low-confidence measurement(s) flagged."
        )

        _set_status(db, document, analysis, "completed")
        analysis.processed_at = datetime.now(UTC)
        analysis.processing_error = None
        db.commit()
        record_drawing_processing_completed(db, document)
        db.commit()
        logger.info(
            "Drawing %s processed in %.2fs",
            document_id,
            time.perf_counter() - started,
        )
    except Exception as exc:
        logger.exception("Drawing processing failed for %s", document_id)
        analysis.processing_error = str(exc)
        _set_status(db, document, analysis, "failed")
        analysis.processed_at = datetime.now(UTC)
        db.commit()
        record_drawing_processing_failed(db, document, str(exc))
        db.commit()
