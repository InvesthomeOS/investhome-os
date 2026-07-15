"""Architectural drawing intelligence API routes."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.drawing_intelligence import DrawingAnalysis, DrawingAnnotation, DrawingUnitProposal
from investhome_api.models.user_auth import User
from investhome_api.schemas.drawing_intelligence import (
    DrawingAnalysisResponse,
    DrawingAnnotationCreateRequest,
    DrawingAnnotationResponse,
    DrawingAskRequest,
    DrawingAskResponse,
    DrawingProcessingStatusResponse,
    DrawingScaleCorrectionRequest,
    DrawingUnitApprovalRequest,
    DrawingUnitProposalResponse,
    DrawingVersionCompareRequest,
    DrawingVersionCompareResponse,
    build_drawing_analysis_response,
)
from investhome_api.services.document_service import (
    get_document_or_404,
    user_can_view_analysis,
)
from investhome_api.services.drawing_intelligence.activity import (
    record_annotation_added,
    record_drawing_question_asked,
    record_scale_corrected,
    record_unit_approved,
)
from investhome_api.services.drawing_intelligence.config import should_process_as_drawing
from investhome_api.services.drawing_intelligence.qa import answer_drawing_question
from investhome_api.services.drawing_intelligence.queue import enqueue_drawing_processing
from investhome_api.services.drawing_intelligence.version_compare import compare_drawing_versions
from investhome_api.services.permission_service import user_has_permission

router = APIRouter(prefix="/documents", tags=["drawing-intelligence"])


def _get_drawing_analysis_or_404(db: Session, document_id: UUID) -> DrawingAnalysis:
    analysis = db.scalar(
        select(DrawingAnalysis)
        .options(
            selectinload(DrawingAnalysis.sheets),
            selectinload(DrawingAnalysis.elements),
            selectinload(DrawingAnalysis.annotations),
            selectinload(DrawingAnalysis.unit_proposals),
        )
        .where(DrawingAnalysis.document_id == document_id)
        .limit(1)
    )
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="documents.errors.drawing_analysis_not_found")
    return analysis


def _document_type_value(document) -> str:
    value = document.document_type
    return value.value if hasattr(value, "value") else str(value)


def _is_drawing_document(document) -> bool:
    return should_process_as_drawing(document.file_extension, _document_type_value(document))


@router.get("/{document_id}/drawing-analysis", response_model=DrawingAnalysisResponse)
def get_drawing_analysis(
    document_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "view_analysis")),
) -> DrawingAnalysisResponse:
    document = get_document_or_404(db, document_id, user)
    if not user_can_view_analysis(user, document):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="documents.errors.analysis_forbidden")
    if not _is_drawing_document(document):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="documents.errors.not_a_drawing")
    analysis = _get_drawing_analysis_or_404(db, document_id)
    return build_drawing_analysis_response(analysis)


@router.get("/{document_id}/drawing-processing-status", response_model=DrawingProcessingStatusResponse)
def get_drawing_processing_status(
    document_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "view")),
) -> DrawingProcessingStatusResponse:
    document = get_document_or_404(db, document_id, user)
    analysis = document.drawing_analysis
    processing_error = None
    if analysis and user_can_view_analysis(user, document):
        processing_error = analysis.processing_error
    return DrawingProcessingStatusResponse(
        document_id=document.id,
        processing_status=analysis.processing_status if analysis else "not_supported",
        preview_status=analysis.preview_status if analysis else None,
        processing_error=processing_error,
        processed_at=analysis.processed_at if analysis else None,
    )


@router.post("/{document_id}/drawing-reprocess", response_model=DrawingProcessingStatusResponse)
def reprocess_drawing(
    document_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "reprocess")),
) -> DrawingProcessingStatusResponse:
    document = get_document_or_404(db, document_id, user)
    if not _is_drawing_document(document):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="documents.errors.not_a_drawing")
    enqueue_drawing_processing(document.id, force=True)
    analysis = document.drawing_analysis
    return DrawingProcessingStatusResponse(
        document_id=document.id,
        processing_status=analysis.processing_status if analysis else "queued",
        preview_status=analysis.preview_status if analysis else None,
        processed_at=analysis.processed_at if analysis else None,
    )


@router.get("/{document_id}/drawing-preview")
def get_drawing_preview(
    document_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "download")),
) -> Response:
    document = get_document_or_404(db, document_id, user)
    analysis = document.drawing_analysis
    if analysis is None or analysis.preview_status == "unavailable" or not analysis.preview_storage_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="documents.errors.drawing_preview_unavailable")
    path = Path(analysis.preview_storage_key)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="documents.errors.drawing_preview_unavailable")
    return FileResponse(path, media_type="image/svg+xml")


@router.post("/{document_id}/drawing-scale", response_model=DrawingAnalysisResponse)
def correct_drawing_scale(
    document_id: UUID,
    body: DrawingScaleCorrectionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "update")),
) -> DrawingAnalysisResponse:
    document = get_document_or_404(db, document_id, user)
    analysis = _get_drawing_analysis_or_404(db, document_id)
    analysis.scale_corrected = body.scale
    analysis.scale_corrected_by_user_id = user.id
    analysis.scale_corrected_at = datetime.now(UTC)
    db.commit()
    record_scale_corrected(db, document, user.id, body.scale)
    db.commit()
    db.refresh(analysis)
    return build_drawing_analysis_response(analysis)


@router.post("/{document_id}/drawing-annotations", response_model=DrawingAnnotationResponse, status_code=status.HTTP_201_CREATED)
def create_drawing_annotation(
    document_id: UUID,
    body: DrawingAnnotationCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "update")),
) -> DrawingAnnotationResponse:
    document = get_document_or_404(db, document_id, user)
    analysis = _get_drawing_analysis_or_404(db, document_id)
    annotation = DrawingAnnotation(
        analysis_id=analysis.id,
        sheet_id=body.sheet_id,
        created_by_user_id=user.id,
        label=body.label,
        content=body.content,
        geometry_json=body.geometry_json,
        color=body.color,
    )
    db.add(annotation)
    db.commit()
    record_annotation_added(db, document, user.id, body.label)
    db.commit()
    db.refresh(annotation)
    return DrawingAnnotationResponse.model_validate(annotation)


@router.post("/{document_id}/drawing-ask", response_model=DrawingAskResponse)
def ask_drawing(
    document_id: UUID,
    body: DrawingAskRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "ask")),
) -> DrawingAskResponse:
    document = get_document_or_404(db, document_id, user)
    if not user_can_view_analysis(user, document):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="documents.errors.analysis_forbidden")
    analysis = _get_drawing_analysis_or_404(db, document_id)
    answer, sources, grounded = answer_drawing_question(db, analysis, body.question, locale=body.locale)
    record_drawing_question_asked(db, document, user.id, body.question)
    db.commit()
    return DrawingAskResponse(
        answer=answer,
        grounded=grounded,
        sources=[s.label() for s in sources],
    )


@router.post("/{document_id}/drawing-compare", response_model=DrawingVersionCompareResponse)
def compare_versions(
    document_id: UUID,
    body: DrawingVersionCompareRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "view_analysis")),
) -> DrawingVersionCompareResponse:
    document = get_document_or_404(db, document_id, user)
    parent_id = document.parent_document_id or document.id
    try:
        comparison = compare_drawing_versions(
            db,
            parent_document_id=parent_id,
            from_version_id=body.from_version_id,
            to_version_id=body.to_version_id,
            user_id=user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    return DrawingVersionCompareResponse.model_validate(comparison, from_attributes=True)


@router.post("/{document_id}/drawing-units/approve", response_model=DrawingUnitProposalResponse)
def approve_drawing_unit(
    document_id: UUID,
    body: DrawingUnitApprovalRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "approve")),
) -> DrawingUnitProposalResponse:
    document = get_document_or_404(db, document_id, user)
    if not user_has_permission(user, "documents", "approve"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="documents.errors.unit_approval_forbidden")
    analysis = _get_drawing_analysis_or_404(db, document_id)
    proposal = db.get(DrawingUnitProposal, body.proposal_id)
    if proposal is None or proposal.analysis_id != analysis.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="documents.errors.unit_proposal_not_found")
    proposal.status = "approved" if body.approved else "rejected"
    proposal.approved_by_user_id = user.id
    proposal.approved_at = datetime.now(UTC)
    if body.approved:
        # Unit records are only created after explicit approval — store placeholder ID
        proposal.created_unit_id = proposal.id
        record_unit_approved(db, document, user.id, proposal.unit_label)
    db.commit()
    db.refresh(proposal)
    return DrawingUnitProposalResponse.model_validate(proposal)
