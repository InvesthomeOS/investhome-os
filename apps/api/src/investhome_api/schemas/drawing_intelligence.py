"""Drawing intelligence API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from investhome_api.models.drawing_intelligence import DrawingAnalysis, DrawingAnnotation, DrawingElement, DrawingSheet


class DrawingElementResponse(BaseModel):
    id: UUID
    element_type: str
    label: str | None = None
    value_text: str | None = None
    numeric_value: float | None = None
    unit: str | None = None
    confidence: str
    geometry_json: str | None = None
    metadata_json: str | None = None

    model_config = {"from_attributes": True}


class DrawingSheetResponse(BaseModel):
    id: UUID
    sheet_index: int
    sheet_name: str | None = None
    sheet_number: str | None = None
    sheet_type: str | None = None
    confidence: str | None = None

    model_config = {"from_attributes": True}


class DrawingAnnotationResponse(BaseModel):
    id: UUID
    label: str | None = None
    content: str | None = None
    geometry_json: str | None = None
    color: str | None = None
    is_resolved: bool
    created_by_user_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class DrawingUnitProposalResponse(BaseModel):
    id: UUID
    unit_label: str
    unit_type: str | None = None
    area_sqm: float | None = None
    confidence: str
    status: str
    created_unit_id: UUID | None = None

    model_config = {"from_attributes": True}


class DrawingAnalysisResponse(BaseModel):
    document_id: UUID
    document_version_id: UUID
    processing_status: str
    source_format: str | None = None
    conversion_method: str | None = None
    preview_status: str | None = None
    discipline: str | None = None
    discipline_confidence: str | None = None
    drawing_type: str | None = None
    drawing_type_confidence: str | None = None
    scale_detected: str | None = None
    scale_confidence: str | None = None
    scale_corrected: str | None = None
    sheet_count: int | None = None
    summary: str | None = None
    summary_en: str | None = None
    title_block_json: str | None = None
    schedules_json: str | None = None
    processing_error: str | None = None
    retry_count: int = 0
    processed_at: datetime | None = None
    sheets: list[DrawingSheetResponse] = Field(default_factory=list)
    elements: list[DrawingElementResponse] = Field(default_factory=list)
    annotations: list[DrawingAnnotationResponse] = Field(default_factory=list)
    unit_proposals: list[DrawingUnitProposalResponse] = Field(default_factory=list)
    low_confidence_count: int = 0


class DrawingProcessingStatusResponse(BaseModel):
    document_id: UUID
    processing_status: str
    preview_status: str | None = None
    processing_error: str | None = None
    processed_at: datetime | None = None


class DrawingScaleCorrectionRequest(BaseModel):
    scale: str = Field(min_length=1, max_length=120)


class DrawingAnnotationCreateRequest(BaseModel):
    label: str | None = Field(default=None, max_length=200)
    content: str | None = Field(default=None, max_length=2000)
    geometry_json: str | None = None
    color: str | None = Field(default="#f59e0b", max_length=20)
    sheet_id: UUID | None = None


class DrawingAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    locale: str = Field(default="en", pattern="^(en|tr)$")


class DrawingAskResponse(BaseModel):
    answer: str
    grounded: bool
    sources: list[str] = Field(default_factory=list)


class DrawingVersionCompareRequest(BaseModel):
    from_version_id: UUID
    to_version_id: UUID


class DrawingVersionCompareResponse(BaseModel):
    id: UUID
    from_version_id: UUID
    to_version_id: UUID
    summary: str | None = None
    summary_en: str | None = None
    changes_json: str | None = None
    created_at: datetime


class DrawingUnitApprovalRequest(BaseModel):
    proposal_id: UUID
    approved: bool = True


def build_drawing_analysis_response(analysis: DrawingAnalysis) -> DrawingAnalysisResponse:
    low_confidence = sum(1 for e in analysis.elements if e.confidence == "low")
    return DrawingAnalysisResponse(
        document_id=analysis.document_id,
        document_version_id=analysis.document_version_id,
        processing_status=analysis.processing_status,
        source_format=analysis.source_format,
        conversion_method=analysis.conversion_method,
        preview_status=analysis.preview_status,
        discipline=analysis.discipline,
        discipline_confidence=analysis.discipline_confidence,
        drawing_type=analysis.drawing_type,
        drawing_type_confidence=analysis.drawing_type_confidence,
        scale_detected=analysis.scale_detected,
        scale_confidence=analysis.scale_confidence,
        scale_corrected=analysis.scale_corrected,
        sheet_count=analysis.sheet_count,
        summary=analysis.summary,
        summary_en=analysis.summary_en,
        title_block_json=analysis.title_block_json,
        schedules_json=analysis.schedules_json,
        processing_error=analysis.processing_error,
        retry_count=analysis.retry_count,
        processed_at=analysis.processed_at,
        sheets=[DrawingSheetResponse.model_validate(s) for s in analysis.sheets],
        elements=[DrawingElementResponse.model_validate(e) for e in analysis.elements],
        annotations=[DrawingAnnotationResponse.model_validate(a) for a in analysis.annotations],
        unit_proposals=[DrawingUnitProposalResponse.model_validate(p) for p in analysis.unit_proposals],
        low_confidence_count=low_confidence,
    )
