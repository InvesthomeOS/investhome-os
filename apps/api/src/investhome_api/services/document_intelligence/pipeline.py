"""Asynchronous document processing pipeline."""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.document import Document, DocumentAnalysis, ProcessingStatus
from investhome_api.models.document_intelligence import AIUsage
from investhome_api.services.document_intelligence.ai import (
    get_ai_provider,
    serialize_risks,
    serialize_structured,
)
from investhome_api.services.document_intelligence.chunking import persist_chunks
from investhome_api.services.document_intelligence.extraction import (
    extract_text,
    is_image_extension,
    is_processable,
)
from investhome_api.services.document_intelligence.ocr import get_ocr_provider
from investhome_api.services.document_intelligence.types import TextSegment
from investhome_api.services.storage.factory import get_storage_provider

logger = logging.getLogger(__name__)


def _get_or_create_analysis(db: Session, document: Document) -> DocumentAnalysis:
    if document.analysis:
        return document.analysis
    analysis = DocumentAnalysis(
        document_id=document.id,
        document_version_id=document.id,
        processing_status=ProcessingStatus.QUEUED.value,
        classification_status="pending",
    )
    db.add(analysis)
    db.flush()
    document.analysis = analysis
    return analysis


def _store_extracted_text(document_id: uuid.UUID, text: str) -> str:
    settings = get_settings()
    root = Path(settings.document_storage_root) / settings.document_extracted_text_subdir
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{document_id}.txt"
    path.write_text(text, encoding="utf-8")
    return str(path)


def _set_status(
    db: Session,
    document: Document,
    analysis: DocumentAnalysis,
    status: ProcessingStatus,
) -> None:
    document.processing_status = status
    analysis.processing_status = status.value
    db.flush()


def process_document(db: Session, document_id: uuid.UUID, *, force: bool = False) -> None:
    """Run full intelligence pipeline for a document version."""
    started = time.perf_counter()
    document = db.get(Document, document_id)
    if document is None:
        logger.warning("Document %s not found for processing", document_id)
        return

    analysis = _get_or_create_analysis(db, document)
    settings = get_settings()

    if (
        not force
        and analysis.processing_status == ProcessingStatus.COMPLETED.value
        and analysis.extracted_text_location
    ):
        return

    in_progress = {
        ProcessingStatus.PROCESSING.value,
        ProcessingStatus.EXTRACTING_TEXT.value,
        ProcessingStatus.RUNNING_OCR.value,
        ProcessingStatus.CLASSIFYING.value,
        ProcessingStatus.ANALYZING.value,
    }
    if not force and analysis.processing_status in in_progress:
        logger.info("Document %s already processing; skipping duplicate job", document_id)
        return

    if not is_processable(document.file_extension):
        _set_status(db, document, analysis, ProcessingStatus.NOT_SUPPORTED)
        analysis.processing_error = "unsupported_format"
        analysis.processed_at = datetime.now(UTC)
        db.commit()
        return

    analysis.processing_started_at = datetime.now(UTC)
    analysis.retry_count = (analysis.retry_count or 0) + (1 if force else 0)
    _set_status(db, document, analysis, ProcessingStatus.PROCESSING)
    db.commit()

    from investhome_api.services.document_intelligence.activity import record_processing_started

    record_processing_started(db, document)
    db.commit()

    try:
        storage = get_storage_provider()
        with storage.open(document.storage_key) as stream:
            raw = stream.read()

        _set_status(db, document, analysis, ProcessingStatus.EXTRACTING_TEXT)
        db.commit()

        extraction = extract_text(raw, document.file_extension)
        segments = list(extraction.segments)

        ocr_provider = get_ocr_provider()
        ocr_pages = 0
        needs_ocr = is_image_extension(document.file_extension) or any(
            s.needs_ocr for s in segments
        )
        if needs_ocr:
            _set_status(db, document, analysis, ProcessingStatus.RUNNING_OCR)
            db.commit()
            if is_image_extension(document.file_extension):
                from investhome_api.services.document_intelligence.types import SourceReference

                result = ocr_provider.ocr_image(raw, SourceReference(page=1))
                segments = [
                    TextSegment(
                        text=result.text,
                        source=result.source,
                        confidence=result.confidence,
                    )
                ]
                extraction.method = f"ocr:{ocr_provider.name}"
                ocr_pages = 1
            else:
                updated: list[TextSegment] = []
                for seg in segments:
                    if seg.needs_ocr and not seg.text.strip():
                        placeholder = (
                            f"[OCR required for {seg.source.label()} — "
                            f"provider: {ocr_provider.name}]"
                        )
                        updated.append(
                            TextSegment(
                                text=placeholder,
                                source=seg.source,
                                confidence=0.0,
                            )
                        )
                        ocr_pages += 1
                    else:
                        updated.append(seg)
                segments = updated
                extraction.method = f"{extraction.method}+ocr_partial"

        extraction.segments = segments
        full_text = extraction.build_full_text()
        if not full_text.strip():
            raise ValueError("no_text_extracted")

        text_path = _store_extracted_text(document.id, full_text)
        preview_len = settings.document_text_preview_chars
        analysis.extracted_text_location = text_path
        analysis.extracted_text_preview = full_text[:preview_len]
        analysis.extraction_method = extraction.method
        analysis.page_count = extraction.page_count
        analysis.word_count = len(full_text.split())

        _set_status(db, document, analysis, ProcessingStatus.CLASSIFYING)
        db.commit()

        provider = get_ai_provider(confidentiality=document.confidentiality_level.value)
        user_type = document.document_type.value if hasattr(document.document_type, "value") else str(
            document.document_type
        )
        analysis_result = provider.analyze(full_text, user_type, language="tr")

        _set_status(db, document, analysis, ProcessingStatus.ANALYZING)
        db.commit()

        structured = analysis_result.structured
        analysis.detected_language = analysis_result.language
        analysis.detected_document_type = analysis_result.classification.document_type
        analysis.classification_confidence = f"{analysis_result.classification.confidence:.2f}"
        analysis.classification_explanation = analysis_result.classification.explanation
        analysis.classification_status = "pending"
        analysis.ai_summary = analysis_result.summary_tr
        analysis.ai_summary_en = analysis_result.summary_en
        analysis.structured_data_json = serialize_structured(structured)
        analysis.extracted_entities_json = json.dumps(structured.entities, ensure_ascii=False)
        analysis.extracted_dates_json = json.dumps(structured.dates, ensure_ascii=False)
        analysis.extracted_amounts_json = json.dumps(structured.amounts, ensure_ascii=False)
        analysis.extracted_parties_json = json.dumps(structured.parties, ensure_ascii=False)
        analysis.extracted_obligations_json = json.dumps(structured.obligations, ensure_ascii=False)
        analysis.extracted_risks_json = serialize_risks(structured.risks)
        analysis.model_provider = analysis_result.provider
        analysis.model_name = analysis_result.model
        analysis.prompt_version = analysis_result.prompt_version
        analysis.processing_error = None

        persist_chunks(
            db,
            document_id=document.id,
            version_id=document.id,
            analysis_id=analysis.id,
            segments=segments,
        )

        duration_ms = int((time.perf_counter() - started) * 1000)
        db.add(
            AIUsage(
                document_id=document.id,
                analysis_id=analysis.id,
                provider=analysis_result.provider,
                model_name=analysis_result.model,
                operation="full_analysis",
                input_tokens=analysis.word_count,
                output_tokens=len(analysis.ai_summary or "") // 4,
                ocr_pages=ocr_pages or None,
                duration_ms=duration_ms,
                retry_count=analysis.retry_count,
            )
        )

        analysis.processed_at = datetime.now(UTC)
        _set_status(db, document, analysis, ProcessingStatus.COMPLETED)
        db.commit()

        from investhome_api.services.document_intelligence.activity import (
            notify_processing_completed,
            record_processing_completed,
        )

        record_processing_completed(db, document)
        notify_processing_completed(db, document, structured.risks)

    except Exception as exc:
        logger.exception("Document processing failed for %s", document_id)
        db.rollback()
        document = db.get(Document, document_id)
        if document is None:
            return
        analysis = _get_or_create_analysis(db, document)
        analysis.processing_error = str(exc)[:2000]
        analysis.processed_at = datetime.now(UTC)
        _set_status(db, document, analysis, ProcessingStatus.FAILED)
        db.commit()

        from investhome_api.services.document_intelligence.activity import (
            notify_processing_failed,
            record_processing_failed,
        )

        record_processing_failed(db, document, str(exc))
        notify_processing_failed(db, document)
