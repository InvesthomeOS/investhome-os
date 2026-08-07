"""AI Index foundation — canonical text knowledge documents for Drive-backed assets."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


class AiDocumentStatus(str, enum.Enum):
    PENDING = "pending"
    READY = "ready"
    SKIPPED = "skipped"
    FAILED = "failed"
    INACTIVE = "inactive"


class AiDocumentType(str, enum.Enum):
    README = "readme"
    METADATA = "metadata"
    TXT = "txt"
    MD = "md"
    JSON = "json"
    DOCX = "docx"
    PDF = "pdf"
    LEGAL_META = "legal_meta"
    UNSUPPORTED = "unsupported"


class AiDocument(Base):
    """Canonical AI knowledge document (text only — never stores binary)."""

    __tablename__ = "ai_documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("creative_studio_media_assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    drive_file_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    document_type: Mapped[str] = mapped_column(String(40), nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords: Mapped[list | None] = mapped_column(JSON, nullable=True)
    builders: Mapped[list | None] = mapped_column(JSON, nullable=True)
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    index_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AiDocumentStatus.PENDING.value,
    )
    skip_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
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

    __table_args__ = (
        Index("ix_ai_documents_project_id", "project_id"),
        Index("ix_ai_documents_asset_id", "asset_id"),
        Index("ix_ai_documents_drive_file_id", "drive_file_id"),
        Index("ix_ai_documents_index_status", "index_status"),
        Index("ix_ai_documents_is_active", "is_active"),
        Index("ix_ai_documents_category", "category"),
        Index(
            "uq_ai_documents_asset_id",
            "asset_id",
            unique=True,
            postgresql_where=text("asset_id IS NOT NULL"),
            sqlite_where=text("asset_id IS NOT NULL"),
        ),
        Index(
            "uq_ai_documents_project_drive_file",
            "project_id",
            "drive_file_id",
            unique=True,
            postgresql_where=text("drive_file_id IS NOT NULL"),
            sqlite_where=text("drive_file_id IS NOT NULL"),
        ),
    )
