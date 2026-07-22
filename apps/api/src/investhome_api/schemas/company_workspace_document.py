"""Pydantic schemas for company workspace documents."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.company_workspace_document import (
    ApprovalStepStatus,
    CompanyDocumentCategory,
    CompanyDocumentRecordStatus,
    SignatureRequestStatus,
)
from investhome_api.models.document import ConfidentialityLevel, DocumentType


class DocumentFolderCreate(BaseModel):
    company_id: UUID
    parent_folder_id: UUID | None = None
    name: str = Field(max_length=255)
    description: str | None = None


class DocumentFolderUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    parent_folder_id: UUID | None = None
    description: str | None = None


class DocumentFolderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    parent_folder_id: UUID | None
    name: str
    slug: str
    description: str | None
    is_system: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime
    document_count: int = 0
    children: list[DocumentFolderResponse] = Field(default_factory=list)


class DocumentFolderTreeResponse(BaseModel):
    items: list[DocumentFolderResponse]
    total: int


class CompanyDocumentVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    version_number: int
    version_notes: str | None
    checksum: str
    file_size: int
    original_file_name: str
    uploaded_by_user_id: UUID | None
    uploaded_by_name: str | None = None
    is_current: bool
    created_at: datetime
    document_id: UUID


class CompanyDocumentPermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None
    role_code: str | None
    can_view: bool
    can_download: bool
    can_share: bool
    can_edit: bool
    inherit_from_folder: bool


class CompanyDocumentShareLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    token: str
    expires_at: datetime
    max_downloads: int | None
    download_count: int
    revoked_at: datetime | None
    created_at: datetime
    secure_url: str | None = None


class CompanyDocumentShareLinkCreate(BaseModel):
    expires_in_hours: int = Field(default=72, ge=1, le=720)
    password: str | None = Field(default=None, max_length=128)
    max_downloads: int | None = Field(default=None, ge=1)


class CompanyDocumentApprovalStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    step_order: int
    approver_user_id: UUID | None
    status: ApprovalStepStatus
    comments: str | None
    decided_at: datetime | None


class CompanyDocumentApprovalWorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    requested_by_user_id: UUID | None
    completed_at: datetime | None
    created_at: datetime
    steps: list[CompanyDocumentApprovalStepResponse] = Field(default_factory=list)


class CompanyDocumentSignatureRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    signer_user_id: UUID | None
    signer_email: str | None
    signer_name: str | None
    status: SignatureRequestStatus
    message: str | None
    signed_at: datetime | None
    created_at: datetime


class CompanyDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_number: str
    title: str
    description: str | None
    category: CompanyDocumentCategory
    document_type: DocumentType
    confidentiality_level: ConfidentialityLevel
    status: CompanyDocumentRecordStatus
    company_id: UUID
    branch_id: UUID | None
    department_id: UUID | None
    team_id: UUID | None
    employee_user_id: UUID | None
    folder_id: UUID | None
    related_record_type: str | None
    related_record_id: UUID | None
    owner_user_id: UUID | None
    document_id: UUID
    current_version_number: int
    tags: list[str] = Field(default_factory=list)
    effective_date: date | None
    expiration_date: date | None
    renewal_date: date | None
    is_favorited: bool = False
    created_by_user_id: UUID | None
    created_by_name: str | None = None
    owner_name: str | None = None
    folder_name: str | None = None
    company_name: str | None = None
    file_name: str | None = None
    file_size: int | None = None
    file_extension: str | None = None
    mime_type: str | None = None
    checksum: str | None = None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None
    deleted_at: datetime | None
    retention_expires_at: datetime | None
    has_legal_hold: bool = False
    versions: list[CompanyDocumentVersionResponse] = Field(default_factory=list)
    permissions: list[CompanyDocumentPermissionResponse] = Field(default_factory=list)
    share_links: list[CompanyDocumentShareLinkResponse] = Field(default_factory=list)
    approval_workflows: list[CompanyDocumentApprovalWorkflowResponse] = Field(default_factory=list)
    signature_requests: list[CompanyDocumentSignatureRequestResponse] = Field(default_factory=list)


class CompanyDocumentListResponse(BaseModel):
    items: list[CompanyDocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class CompanyDocumentCreate(BaseModel):
    company_id: UUID
    title: str = Field(max_length=500)
    description: str | None = None
    category: CompanyDocumentCategory = CompanyDocumentCategory.OTHER
    document_type: DocumentType = DocumentType.OTHER
    confidentiality_level: ConfidentialityLevel = ConfidentialityLevel.INTERNAL
    branch_id: UUID | None = None
    department_id: UUID | None = None
    team_id: UUID | None = None
    employee_user_id: UUID | None = None
    folder_id: UUID | None = None
    related_record_type: str | None = None
    related_record_id: UUID | None = None
    owner_user_id: UUID | None = None
    tags: list[str] = Field(default_factory=list)
    effective_date: date | None = None
    expiration_date: date | None = None
    renewal_date: date | None = None


class CompanyDocumentUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    description: str | None = None
    category: CompanyDocumentCategory | None = None
    document_type: DocumentType | None = None
    confidentiality_level: ConfidentialityLevel | None = None
    branch_id: UUID | None = None
    department_id: UUID | None = None
    team_id: UUID | None = None
    employee_user_id: UUID | None = None
    folder_id: UUID | None = None
    related_record_type: str | None = None
    related_record_id: UUID | None = None
    owner_user_id: UUID | None = None
    tags: list[str] | None = None
    effective_date: date | None = None
    expiration_date: date | None = None
    renewal_date: date | None = None


class CompanyDocumentBulkActionRequest(BaseModel):
    document_ids: list[UUID] = Field(min_length=1)
    action: str = Field(pattern="^(archive|restore|trash|delete|favorite|unfavorite)$")


class CompanyDocumentStorageSummary(BaseModel):
    total_documents: int
    total_bytes: int
    by_category: dict[str, int]
    expiring_soon: int
    in_trash: int
    archived: int


class CompanyDocumentExportResponse(BaseModel):
    exported_at: datetime
    count: int
    items: list[CompanyDocumentResponse]


class MalwareScanResult(BaseModel):
    status: str
    scanned_at: datetime
    message: str


class TemplateGenerateRequest(BaseModel):
    template_id: UUID
    variables: dict[str, str] = Field(default_factory=dict)


class TemplateGenerateResponse(BaseModel):
    status: str
    message: str
    document_id: UUID | None = None


class LegalHoldCreate(BaseModel):
    reason: str = Field(min_length=1)


class LegalHoldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reason: str
    is_active: bool
    placed_by_user_id: UUID | None
    released_at: datetime | None
    created_at: datetime


class ApprovalRequest(BaseModel):
    approver_user_ids: list[UUID] = Field(min_length=1)


class ApprovalDecisionRequest(BaseModel):
    comments: str | None = None


class SignatureRequestCreate(BaseModel):
    signer_user_id: UUID | None = None
    signer_email: str | None = None
    signer_name: str | None = None
    message: str | None = None
