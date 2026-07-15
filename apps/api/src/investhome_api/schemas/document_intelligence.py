"""Pydantic schemas for document intelligence."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.document import ProcessingStatus


class SourceReferenceResponse(BaseModel):
    page: int | None = None
    sheet: str | None = None
    slide: int | None = None
    section: str | None = None
    reference: str | None = None


class RiskItemResponse(BaseModel):
    severity: str
    category: str
    description: str
    evidence_reference: str | None = None
    recommended_action: str | None = None
    due_date: str | None = None
    related_party: str | None = None


class DocumentAnalysisDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    document_version_id: UUID | None
    processing_status: str | None
    extraction_method: str | None
    detected_language: str | None
    detected_document_type: str | None
    classification_confidence: str | None
    classification_explanation: str | None
    classification_status: str | None
    user_document_type: str | None
    extracted_text_preview: str | None
    page_count: int | None
    word_count: int | None
    ai_summary: str | None
    ai_summary_en: str | None
    structured_data: dict[str, Any] | None = None
    extracted_entities: list[str] = Field(default_factory=list)
    extracted_dates: list[dict[str, Any]] = Field(default_factory=list)
    extracted_amounts: list[dict[str, Any]] = Field(default_factory=list)
    extracted_parties: list[str] = Field(default_factory=list)
    extracted_obligations: list[dict[str, Any]] = Field(default_factory=list)
    extracted_risks: list[RiskItemResponse] = Field(default_factory=list)
    model_provider: str | None
    model_name: str | None
    prompt_version: str | None
    processing_started_at: datetime | None
    processed_at: datetime | None
    processing_error: str | None = None
    disclaimer: str = "documents.intelligence.disclaimer"
    created_at: datetime
    updated_at: datetime


class ClassificationDecisionRequest(BaseModel):
    accept: bool


class DocumentAskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    language: str = Field(default="tr", pattern="^(tr|en)$")
    conversation_id: UUID | None = None


class DocumentAskResponse(BaseModel):
    answer: str
    found: bool
    source_references: list[SourceReferenceResponse] = Field(default_factory=list)
    conversation_id: UUID
    message_id: UUID
    model_provider: str | None = None
    model_name: str | None = None
    disclaimer: str = "documents.intelligence.disclaimer"


class DocumentConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    document_version_id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


class DocumentMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    source_references: list[SourceReferenceResponse] = Field(default_factory=list)
    created_at: datetime


class DocumentConversationDetailResponse(BaseModel):
    conversation: DocumentConversationResponse
    messages: list[DocumentMessageResponse]


def _parse_json_list(raw: str | None) -> list[Any]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _parse_json_dict(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def build_analysis_response(analysis, *, user_document_type: str | None) -> DocumentAnalysisDetailResponse:
    risks_raw = _parse_json_list(analysis.extracted_risks_json)
    risks = [RiskItemResponse(**item) for item in risks_raw if isinstance(item, dict)]
    return DocumentAnalysisDetailResponse(
        id=analysis.id,
        document_id=analysis.document_id,
        document_version_id=analysis.document_version_id,
        processing_status=analysis.processing_status,
        extraction_method=analysis.extraction_method,
        detected_language=analysis.detected_language,
        detected_document_type=analysis.detected_document_type,
        classification_confidence=analysis.classification_confidence,
        classification_explanation=analysis.classification_explanation,
        classification_status=analysis.classification_status,
        user_document_type=user_document_type,
        extracted_text_preview=analysis.extracted_text_preview,
        page_count=analysis.page_count,
        word_count=analysis.word_count,
        ai_summary=analysis.ai_summary,
        ai_summary_en=analysis.ai_summary_en,
        structured_data=_parse_json_dict(analysis.structured_data_json),
        extracted_entities=_parse_json_list(analysis.extracted_entities_json),
        extracted_dates=_parse_json_list(analysis.extracted_dates_json),
        extracted_amounts=_parse_json_list(analysis.extracted_amounts_json),
        extracted_parties=_parse_json_list(analysis.extracted_parties_json),
        extracted_obligations=_parse_json_list(analysis.extracted_obligations_json),
        extracted_risks=risks,
        model_provider=analysis.model_provider,
        model_name=analysis.model_name,
        prompt_version=analysis.prompt_version,
        processing_started_at=analysis.processing_started_at,
        processed_at=analysis.processed_at,
        processing_error=analysis.processing_error,
        created_at=analysis.created_at,
        updated_at=analysis.updated_at,
    )


class ProcessingStatusResponse(BaseModel):
    document_id: UUID
    processing_status: ProcessingStatus
    analysis_status: str | None
    processed_at: datetime | None
    processing_error: str | None = None
