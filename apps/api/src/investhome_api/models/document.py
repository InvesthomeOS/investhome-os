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
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from investhome_api.db.base import Base


class DocumentType(str, enum.Enum):
    CONTRACT = "contract"
    OPERATING_AGREEMENT = "operating_agreement"
    SUBSCRIPTION_AGREEMENT = "subscription_agreement"
    OFFERING_DOCUMENT = "offering_document"
    INVESTOR_DOCUMENT = "investor_document"
    PROJECT_DOCUMENT = "project_document"
    CONSTRUCTION_DRAWING = "construction_drawing"
    ARCHITECTURAL_DRAWING = "architectural_drawing"
    PERMIT = "permit"
    INSPECTION = "inspection"
    TITLE_DOCUMENT = "title_document"
    CLOSING_DOCUMENT = "closing_document"
    LOAN_DOCUMENT = "loan_document"
    INSURANCE = "insurance"
    APPRAISAL = "appraisal"
    LEASE = "lease"
    INVOICE = "invoice"
    RECEIPT = "receipt"
    BANK_STATEMENT = "bank_statement"
    FINANCIAL_REPORT = "financial_report"
    PRESENTATION = "presentation"
    MARKETING_MATERIAL = "marketing_material"
    PHOTO = "photo"
    SPREADSHEET = "spreadsheet"
    CORRESPONDENCE = "correspondence"
    LEGAL_DOCUMENT = "legal_document"
    TAX_DOCUMENT = "tax_document"
    OTHER = "other"


class DocumentStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class ConfidentialityLevel(str, enum.Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    HIGHLY_CONFIDENTIAL = "highly_confidential"


class ProcessingStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    NOT_SUPPORTED = "not_supported"


class StorageProvider(str, enum.Enum):
    LOCAL = "local"
    S3 = "s3"
    GCS = "gcs"
    AZURE = "azure"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    original_file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(20), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_provider: Mapped[StorageProvider] = mapped_column(
        Enum(StorageProvider, native_enum=False, length=20),
        nullable=False,
        default=StorageProvider.LOCAL,
    )
    storage_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, native_enum=False, length=50),
        nullable=False,
        default=DocumentType.OTHER,
    )
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, native_enum=False, length=30),
        nullable=False,
        default=DocumentStatus.ACTIVE,
    )
    confidentiality_level: Mapped[ConfidentialityLevel] = mapped_column(
        Enum(ConfidentialityLevel, native_enum=False, length=30),
        nullable=False,
        default=ConfidentialityLevel.INTERNAL,
    )
    version_number: Mapped[int] = mapped_column(nullable=False, default=1)
    parent_document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    investor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    document_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_latest_version: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, native_enum=False, length=30),
        nullable=False,
        default=ProcessingStatus.UPLOADED,
    )
    version_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    parent_document: Mapped["Document | None"] = relationship(
        "Document",
        remote_side="Document.id",
        foreign_keys=[parent_document_id],
    )
    links: Mapped[list["DocumentLink"]] = relationship(
        "DocumentLink",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    analysis: Mapped["DocumentAnalysis | None"] = relationship(
        "DocumentAnalysis",
        back_populates="document",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_documents_status", "status"),
        Index("ix_documents_document_type", "document_type"),
        Index("ix_documents_confidentiality_level", "confidentiality_level"),
        Index("ix_documents_project_id", "project_id"),
        Index("ix_documents_investor_id", "investor_id"),
        Index("ix_documents_lead_id", "lead_id"),
        Index("ix_documents_transaction_id", "transaction_id"),
        Index("ix_documents_uploaded_by_user_id", "uploaded_by_user_id"),
        Index("ix_documents_is_latest_version", "is_latest_version"),
        Index("ix_documents_archived_at", "archived_at"),
        Index("ix_documents_checksum", "checksum"),
        Index("ix_documents_created_at", "created_at"),
        Index("ix_documents_parent_document_id", "parent_document_id"),
    )


class DocumentLink(Base):
    __tablename__ = "document_links"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    relationship_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    document: Mapped["Document"] = relationship("Document", back_populates="links")

    __table_args__ = (
        Index("ix_document_links_document_id", "document_id"),
        Index("ix_document_links_entity", "entity_type", "entity_id"),
    )


class DocumentAnalysis(Base):
    """AI readiness fields — processing not implemented in Phase 1."""

    __tablename__ = "document_analyses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    extracted_text_location: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_document_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    document: Mapped["Document"] = relationship("Document", back_populates="analysis")
