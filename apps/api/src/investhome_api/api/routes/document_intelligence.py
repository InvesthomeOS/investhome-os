"""Document intelligence API routes."""

from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.document import Document, ProcessingStatus
from investhome_api.models.document_intelligence import (
    DocumentChunk,
    DocumentConversation,
    DocumentMessage,
    MessageRole,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.document_intelligence import (
    ClassificationDecisionRequest,
    DocumentAnalysisDetailResponse,
    DocumentAskRequest,
    DocumentAskResponse,
    DocumentConversationDetailResponse,
    DocumentConversationResponse,
    DocumentMessageResponse,
    ProcessingStatusResponse,
    SourceReferenceResponse,
    build_analysis_response,
)
from investhome_api.services.document_intelligence.activity import (
    record_classification_accepted,
    record_classification_rejected,
    record_question_asked,
    record_reprocessed,
)
from investhome_api.services.document_intelligence.ai import get_ai_provider
from investhome_api.services.document_intelligence.queue import enqueue_document_processing
from investhome_api.services.document_service import (
    get_document_or_404,
    user_can_ask_document,
    user_can_export_analysis,
    user_can_reprocess_document,
    user_can_view_analysis,
)

router = APIRouter(prefix="/documents", tags=["document-intelligence"])


def _user_document_type(document: Document) -> str:
    value = document.document_type
    return value.value if hasattr(value, "value") else str(value)


@router.get("/{document_id}/analysis", response_model=DocumentAnalysisDetailResponse)
def get_document_analysis(
    document_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "view_analysis")),
) -> DocumentAnalysisDetailResponse:
    document = get_document_or_404(db, document_id, user)
    if not user_can_view_analysis(user, document):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="documents.errors.analysis_forbidden")
    if document.analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="documents.errors.analysis_not_found")
    return build_analysis_response(document.analysis, user_document_type=_user_document_type(document))


@router.get("/{document_id}/processing-status", response_model=ProcessingStatusResponse)
def get_processing_status(
    document_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "view")),
) -> ProcessingStatusResponse:
    document = get_document_or_404(db, document_id, user)
    analysis_status = document.analysis.processing_status if document.analysis else None
    processing_error = None
    if document.analysis and user_can_view_analysis(user, document):
        processing_error = document.analysis.processing_error
    return ProcessingStatusResponse(
        document_id=document.id,
        processing_status=document.processing_status,
        analysis_status=analysis_status,
        processed_at=document.analysis.processed_at if document.analysis else None,
        processing_error=processing_error,
    )


@router.post("/{document_id}/reprocess", response_model=ProcessingStatusResponse)
def reprocess_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "reprocess")),
) -> ProcessingStatusResponse:
    document = get_document_or_404(db, document_id, user)
    if not user_can_reprocess_document(user, document):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="documents.errors.reprocess_forbidden")
    document.processing_status = ProcessingStatus.QUEUED
    if document.analysis:
        document.analysis.processing_status = ProcessingStatus.QUEUED.value
    db.commit()
    record_reprocessed(db, document, str(user.id))
    db.commit()
    enqueue_document_processing(document.id, force=True)
    return ProcessingStatusResponse(
        document_id=document.id,
        processing_status=document.processing_status,
        analysis_status=document.analysis.processing_status if document.analysis else None,
        processed_at=document.analysis.processed_at if document.analysis else None,
    )


@router.post("/{document_id}/classification", response_model=DocumentAnalysisDetailResponse)
def decide_classification(
    document_id: UUID,
    body: ClassificationDecisionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "view_analysis")),
) -> DocumentAnalysisDetailResponse:
    document = get_document_or_404(db, document_id, user)
    if document.analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="documents.errors.analysis_not_found")
    if body.accept:
        document.analysis.classification_status = "accepted"
        record_classification_accepted(db, document, str(user.id))
    else:
        document.analysis.classification_status = "rejected"
        record_classification_rejected(db, document, str(user.id))
    db.commit()
    db.refresh(document)
    return build_analysis_response(document.analysis, user_document_type=_user_document_type(document))


@router.post("/{document_id}/ask", response_model=DocumentAskResponse)
def ask_document(
    document_id: UUID,
    body: DocumentAskRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "ask")),
) -> DocumentAskResponse:
    document = get_document_or_404(db, document_id, user)
    if not user_can_ask_document(user, document):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="documents.errors.ask_forbidden")
    if document.analysis is None or document.analysis.processing_status != ProcessingStatus.COMPLETED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="documents.errors.analysis_not_ready")

    conversation: DocumentConversation | None = None
    if body.conversation_id:
        conversation = db.scalar(
            select(DocumentConversation).where(
                DocumentConversation.id == body.conversation_id,
                DocumentConversation.user_id == user.id,
                DocumentConversation.document_id == document.id,
            )
        )
    if conversation is None:
        conversation = DocumentConversation(
            document_id=document.id,
            document_version_id=document.id,
            user_id=user.id,
            title=body.question[:120],
        )
        db.add(conversation)
        db.flush()

    chunks = db.scalars(
        select(DocumentChunk)
        .where(DocumentChunk.document_version_id == document.id)
        .order_by(DocumentChunk.chunk_index)
    ).all()
    chunk_pairs = [(c.source_reference or "document", c.content) for c in chunks]
    provider = get_ai_provider(confidentiality=document.confidentiality_level.value)
    qa = provider.answer_question(body.question, chunk_pairs, body.language)

    user_message = DocumentMessage(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=body.question,
    )
    refs = qa.source_references
    assistant_message = DocumentMessage(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content=qa.answer,
        source_references_json=json.dumps(refs, ensure_ascii=False),
        model_provider=qa.provider,
        model_name=qa.model,
    )
    db.add(user_message)
    db.add(assistant_message)
    record_question_asked(db, document, str(user.id))
    db.commit()
    db.refresh(assistant_message)

    source_refs = [
        SourceReferenceResponse(reference=str(item.get("reference")))
        for item in refs
        if isinstance(item, dict)
    ]
    return DocumentAskResponse(
        answer=qa.answer,
        found=qa.found,
        source_references=source_refs,
        conversation_id=conversation.id,
        message_id=assistant_message.id,
        model_provider=qa.provider,
        model_name=qa.model,
    )


@router.get("/{document_id}/conversations", response_model=list[DocumentConversationResponse])
def list_conversations(
    document_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "ask")),
) -> list[DocumentConversationResponse]:
    document = get_document_or_404(db, document_id, user)
    if not user_can_ask_document(user, document):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="documents.errors.ask_forbidden")
    rows = db.scalars(
        select(DocumentConversation)
        .where(
            DocumentConversation.document_id == document.id,
            DocumentConversation.user_id == user.id,
            DocumentConversation.archived_at.is_(None),
        )
        .order_by(DocumentConversation.updated_at.desc())
    ).all()
    return [DocumentConversationResponse.model_validate(row) for row in rows]


@router.get(
    "/{document_id}/conversations/{conversation_id}",
    response_model=DocumentConversationDetailResponse,
)
def get_conversation(
    document_id: UUID,
    conversation_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "ask")),
) -> DocumentConversationDetailResponse:
    document = get_document_or_404(db, document_id, user)
    conversation = db.scalar(
        select(DocumentConversation).where(
            DocumentConversation.id == conversation_id,
            DocumentConversation.document_id == document.id,
            DocumentConversation.user_id == user.id,
        )
    )
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="documents.errors.conversation_not_found")
    messages = [
        DocumentMessageResponse(
            id=m.id,
            role=m.role.value if hasattr(m.role, "value") else str(m.role),
            content=m.content,
            source_references=_parse_refs(m.source_references_json),
            created_at=m.created_at,
        )
        for m in conversation.messages
    ]
    return DocumentConversationDetailResponse(
        conversation=DocumentConversationResponse.model_validate(conversation),
        messages=messages,
    )


@router.delete("/{document_id}/conversations", status_code=status.HTTP_204_NO_CONTENT)
def clear_conversations(
    document_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "ask")),
) -> None:
    document = get_document_or_404(db, document_id, user)
    conversations = db.scalars(
        select(DocumentConversation).where(
            DocumentConversation.document_id == document.id,
            DocumentConversation.user_id == user.id,
        )
    ).all()
    for conversation in conversations:
        db.delete(conversation)
    db.commit()


@router.get("/{document_id}/analysis/export")
def export_analysis(
    document_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "export_analysis")),
) -> dict:
    document = get_document_or_404(db, document_id, user)
    if not user_can_export_analysis(user, document):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="documents.errors.export_forbidden")
    if document.analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="documents.errors.analysis_not_found")
    payload = build_analysis_response(document.analysis, user_document_type=_user_document_type(document))
    return payload.model_dump()


def _parse_refs(raw: str | None) -> list[SourceReferenceResponse]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    refs: list[SourceReferenceResponse] = []
    for item in data if isinstance(data, list) else []:
        if isinstance(item, dict):
            refs.append(SourceReferenceResponse(**{k: v for k, v in item.items() if k in SourceReferenceResponse.model_fields}))
    return refs
