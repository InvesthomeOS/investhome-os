from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.document import (
    ConfidentialityLevel,
    DocumentStatus,
    DocumentType,
    ProcessingStatus,
    StorageProvider,
)


class DocumentLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    entity_type: str
    entity_id: UUID
    relationship_type: str | None
    created_at: datetime


class DocumentAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    extracted_text_location: str | None
    ai_summary: str | None
    detected_document_type: str | None
    processing_error: str | None
    processed_at: datetime | None


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    original_file_name: str
    stored_file_name: str
    file_extension: str
    mime_type: str
    file_size: int
    storage_provider: StorageProvider
    checksum: str
    document_type: DocumentType
    category: str | None
    status: DocumentStatus
    confidentiality_level: ConfidentialityLevel
    version_number: int
    parent_document_id: UUID | None
    uploaded_by_user_id: UUID | None
    uploaded_by_name: str | None = None
    project_id: UUID | None
    investor_id: UUID | None
    lead_id: UUID | None
    transaction_id: UUID | None
    description: str | None
    tags: str | None
    document_date: date | None
    expiration_date: date | None
    is_latest_version: bool
    processing_status: ProcessingStatus
    version_notes: str | None
    is_previewable: bool = False
    related_record_label: str | None = None
    is_demo: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    links: list[DocumentLinkResponse] = Field(default_factory=list)


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    document_type: DocumentType | None = None
    category: str | None = Field(default=None, max_length=120)
    status: DocumentStatus | None = None
    confidentiality_level: ConfidentialityLevel | None = None
    project_id: UUID | None = None
    investor_id: UUID | None = None
    lead_id: UUID | None = None
    transaction_id: UUID | None = None
    description: str | None = None
    tags: str | None = Field(default=None, max_length=1000)
    document_date: date | None = None
    expiration_date: date | None = None


class DocumentLinkCreate(BaseModel):
    entity_type: str = Field(min_length=1, max_length=50)
    entity_id: UUID
    relationship_type: str | None = Field(default=None, max_length=80)


class DocumentVersionResponse(BaseModel):
    id: UUID
    version_number: int
    title: str
    original_file_name: str
    file_size: int
    uploaded_by_user_id: UUID | None
    uploaded_by_name: str | None = None
    version_notes: str | None
    is_latest_version: bool
    created_at: datetime


class DocumentVersionListResponse(BaseModel):
    current_version: int
    items: list[DocumentVersionResponse]


class DocumentUploadResult(BaseModel):
    success: bool
    document: DocumentResponse | None = None
    file_name: str
    error: str | None = None


class DocumentBatchUploadResponse(BaseModel):
    results: list[DocumentUploadResult]
