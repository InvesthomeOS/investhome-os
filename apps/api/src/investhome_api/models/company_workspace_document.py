"""Company workspace document models extending the central Document Engine."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from investhome_api.db.base import Base
from investhome_api.models.document import ConfidentialityLevel, DocumentStatus, DocumentType


class CompanyDocumentCategory(str, enum.Enum):
    LEGAL = "legal"
    HR = "hr"
    FINANCE = "finance"
    COMPLIANCE = "compliance"
    OPERATIONS = "operations"
    MARKETING = "marketing"
    IT = "it"
    CONTRACT = "contract"
    POLICY = "policy"
    OTHER = "other"


class CompanyDocumentRecordStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    ARCHIVED = "archived"
    TRASH = "trash"


class ApprovalStepStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SKIPPED = "skipped"


class SignatureRequestStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    SIGNED = "signed"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class DocumentFolder(Base):
    __tablename__ = "document_folders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    parent_folder_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("document_folders.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    parent_folder: Mapped[DocumentFolder | None] = relationship(
        "DocumentFolder", remote_side="DocumentFolder.id", foreign_keys=[parent_folder_id]
    )
    documents: Mapped[list[CompanyWorkspaceDocument]] = relationship(back_populates="folder")

    __table_args__ = (
        UniqueConstraint("company_id", "parent_folder_id", "slug", name="uq_document_folders_company_parent_slug"),
        Index("ix_document_folders_company_id", "company_id"),
        Index("ix_document_folders_parent_folder_id", "parent_folder_id"),
    )


class CompanyWorkspaceDocument(Base):
    """Company-scoped document record linked to the central Document Engine."""

    __tablename__ = "company_workspace_documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[CompanyDocumentCategory] = mapped_column(
        Enum(CompanyDocumentCategory, native_enum=False, length=40),
        nullable=False,
        default=CompanyDocumentCategory.OTHER,
    )
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, native_enum=False, length=50),
        nullable=False,
        default=DocumentType.OTHER,
    )
    confidentiality_level: Mapped[ConfidentialityLevel] = mapped_column(
        Enum(ConfidentialityLevel, native_enum=False, length=30),
        nullable=False,
        default=ConfidentialityLevel.INTERNAL,
    )
    status: Mapped[CompanyDocumentRecordStatus] = mapped_column(
        Enum(CompanyDocumentRecordStatus, native_enum=False, length=30),
        nullable=False,
        default=CompanyDocumentRecordStatus.ACTIVE,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("company_departments.id", ondelete="SET NULL"), nullable=True
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    employee_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    folder_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("document_folders.id", ondelete="SET NULL"), nullable=True
    )
    related_record_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    related_record_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False)
    current_version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    tags_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    renewal_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retention_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    folder: Mapped[DocumentFolder | None] = relationship(back_populates="documents")
    versions: Mapped[list[CompanyDocumentVersion]] = relationship(
        back_populates="workspace_document", cascade="all, delete-orphan", order_by="CompanyDocumentVersion.version_number"
    )
    permissions: Mapped[list[CompanyDocumentPermission]] = relationship(
        back_populates="workspace_document", cascade="all, delete-orphan"
    )
    share_links: Mapped[list[CompanyDocumentShareLink]] = relationship(
        back_populates="workspace_document", cascade="all, delete-orphan"
    )
    favorites: Mapped[list[CompanyDocumentFavorite]] = relationship(
        back_populates="workspace_document", cascade="all, delete-orphan"
    )
    approval_workflows: Mapped[list[CompanyDocumentApprovalWorkflow]] = relationship(
        back_populates="workspace_document", cascade="all, delete-orphan"
    )
    signature_requests: Mapped[list[CompanyDocumentSignatureRequest]] = relationship(
        back_populates="workspace_document", cascade="all, delete-orphan"
    )
    legal_holds: Mapped[list[CompanyDocumentLegalHold]] = relationship(
        back_populates="workspace_document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_cw_documents_company_id", "company_id"),
        Index("ix_cw_documents_folder_id", "folder_id"),
        Index("ix_cw_documents_status", "status"),
        Index("ix_cw_documents_expiration_date", "expiration_date"),
        Index("ix_cw_documents_deleted_at", "deleted_at"),
        Index("ix_cw_documents_document_id", "document_id"),
    )


class CompanyDocumentVersion(Base):
    __tablename__ = "company_document_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workspace_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("company_workspace_documents.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    version_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    original_file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    workspace_document: Mapped[CompanyWorkspaceDocument] = relationship(back_populates="versions")

    __table_args__ = (
        UniqueConstraint("workspace_document_id", "version_number", name="uq_company_doc_versions_number"),
        Index("ix_company_doc_versions_workspace_id", "workspace_document_id"),
    )


class CompanyDocumentPermission(Base):
    __tablename__ = "company_document_permissions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workspace_document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("company_workspace_documents.id", ondelete="CASCADE"), nullable=True
    )
    folder_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("document_folders.id", ondelete="CASCADE"), nullable=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    role_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    can_view: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    can_download: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_share: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_edit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    inherit_from_folder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    workspace_document: Mapped[CompanyWorkspaceDocument | None] = relationship(back_populates="permissions")


class CompanyDocumentShareLink(Base):
    __tablename__ = "company_document_share_links"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workspace_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("company_workspace_documents.id", ondelete="CASCADE"), nullable=False
    )
    token: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_downloads: Mapped[int | None] = mapped_column(Integer, nullable=True)
    download_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    workspace_document: Mapped[CompanyWorkspaceDocument] = relationship(back_populates="share_links")

    __table_args__ = (Index("ix_company_doc_share_links_token", "token"),)


class CompanyDocumentApprovalWorkflow(Base):
    __tablename__ = "company_document_approval_workflows"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workspace_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("company_workspace_documents.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    workspace_document: Mapped[CompanyWorkspaceDocument] = relationship(back_populates="approval_workflows")
    steps: Mapped[list[CompanyDocumentApprovalStep]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan", order_by="CompanyDocumentApprovalStep.step_order"
    )


class CompanyDocumentApprovalStep(Base):
    __tablename__ = "company_document_approval_steps"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("company_document_approval_workflows.id", ondelete="CASCADE"), nullable=False
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    approver_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[ApprovalStepStatus] = mapped_column(
        Enum(ApprovalStepStatus, native_enum=False, length=20),
        nullable=False,
        default=ApprovalStepStatus.PENDING,
    )
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workflow: Mapped[CompanyDocumentApprovalWorkflow] = relationship(back_populates="steps")


class CompanyDocumentSignatureRequest(Base):
    __tablename__ = "company_document_signature_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workspace_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("company_workspace_documents.id", ondelete="CASCADE"), nullable=False
    )
    signer_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    signer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    signer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[SignatureRequestStatus] = mapped_column(
        Enum(SignatureRequestStatus, native_enum=False, length=20),
        nullable=False,
        default=SignatureRequestStatus.PENDING,
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    workspace_document: Mapped[CompanyWorkspaceDocument] = relationship(back_populates="signature_requests")


class CompanyDocumentFavorite(Base):
    __tablename__ = "company_document_favorites"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workspace_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("company_workspace_documents.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    workspace_document: Mapped[CompanyWorkspaceDocument] = relationship(back_populates="favorites")

    __table_args__ = (
        UniqueConstraint("workspace_document_id", "user_id", name="uq_company_doc_favorites_user_doc"),
    )


class CompanyDocumentLegalHold(Base):
    """Legal hold stub — records hold flag; full eDiscovery integration is Phase 2."""

    __tablename__ = "company_document_legal_holds"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workspace_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("company_workspace_documents.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    placed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    workspace_document: Mapped[CompanyWorkspaceDocument] = relationship(back_populates="legal_holds")


class CompanyDocumentRetentionPolicy(Base):
    """Retention policy stub — enforcement hook for future automated purge."""

    __tablename__ = "company_document_retention_policies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=2555)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CompanyDocumentTemplate(Base):
    """Document template stub — variable substitution not fully implemented."""

    __tablename__ = "company_document_templates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_type: Mapped[str] = mapped_column(String(50), nullable=False, default="other")
    variables_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
