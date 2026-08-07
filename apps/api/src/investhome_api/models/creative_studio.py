"""Creative Studio models — projects, documents, drafts, and append-only versions."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
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


class CreativeStudioProjectStatus(str, enum.Enum):
    ACTIVE = "active"
    DRAFT = "draft"
    ARCHIVED = "archived"


class CreativeStudioDocumentType(str, enum.Enum):
    WEBSITE = "website"
    LANDING = "landing"
    BLOG = "blog"
    EMAIL = "email"
    SOCIAL = "social"
    ADS = "ads"
    PROPOSAL = "proposal"
    PRESENTATION = "presentation"
    BROCHURE = "brochure"
    VIDEO = "video"
    IMAGE = "image"
    ARCHITECTURAL = "architectural"


class CreativeStudioDocumentStatus(str, enum.Enum):
    DRAFT = "draft"
    READY = "ready"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class CreativeStudioProject(Base):
    __tablename__ = "creative_studio_projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[CreativeStudioProjectStatus] = mapped_column(
        Enum(CreativeStudioProjectStatus, native_enum=False, length=30),
        nullable=False,
        default=CreativeStudioProjectStatus.ACTIVE,
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    linked_project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
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
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    documents: Mapped[list["CreativeStudioDocument"]] = relationship(
        "CreativeStudioDocument",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_creative_studio_projects_status", "status"),
        Index("ix_creative_studio_projects_owner_id", "owner_id"),
        Index("ix_creative_studio_projects_company_id", "company_id"),
        Index("ix_creative_studio_projects_linked_project_id", "linked_project_id"),
        Index("ix_creative_studio_projects_archived_at", "archived_at"),
    )


class CreativeStudioDocument(Base):
    __tablename__ = "creative_studio_documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("creative_studio_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_type: Mapped[CreativeStudioDocumentType] = mapped_column(
        Enum(CreativeStudioDocumentType, native_enum=False, length=40),
        nullable=False,
    )
    status: Mapped[CreativeStudioDocumentStatus] = mapped_column(
        Enum(CreativeStudioDocumentStatus, native_enum=False, length=30),
        nullable=False,
        default=CreativeStudioDocumentStatus.DRAFT,
    )
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    draft_body_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    draft_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    draft_updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Soft reference — avoid circular FK with versions table (marketing content pattern)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
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
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["CreativeStudioProject"] = relationship(
        "CreativeStudioProject",
        back_populates="documents",
    )
    versions: Mapped[list["CreativeStudioDocumentVersion"]] = relationship(
        "CreativeStudioDocumentVersion",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="CreativeStudioDocumentVersion.version_number",
    )

    __table_args__ = (
        Index("ix_creative_studio_documents_project_id", "project_id"),
        Index("ix_creative_studio_documents_document_type", "document_type"),
        Index("ix_creative_studio_documents_status", "status"),
        Index("ix_creative_studio_documents_archived_at", "archived_at"),
    )


class CreativeStudioDocumentVersion(Base):
    """Append-only version snapshots. Rows are never mutated after creation."""

    __tablename__ = "creative_studio_document_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("creative_studio_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    document: Mapped["CreativeStudioDocument"] = relationship(
        "CreativeStudioDocument",
        back_populates="versions",
    )

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "version_number",
            name="uq_creative_studio_document_versions_doc_number",
        ),
        Index("ix_creative_studio_document_versions_document_id", "document_id"),
    )
