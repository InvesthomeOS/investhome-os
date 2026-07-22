"""Knowledge Hub models — extend Documents Workspace, never duplicate Document storage."""

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
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from investhome_api.db.base import Base


class KnowledgeCollectionType(str, enum.Enum):
    MANUAL = "manual"
    SMART = "smart"


class KnowledgeReviewReason(str, enum.Enum):
    LOW_CONFIDENCE = "low_confidence"
    MISSING_METADATA = "missing_metadata"
    UNLINKED = "unlinked"
    DUPLICATE_CANDIDATE = "duplicate_candidate"
    FAILED_PROCESSING = "failed_processing"
    EXPIRING = "expiring"
    CLASSIFICATION_PENDING = "classification_pending"


class KnowledgeReviewStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class KnowledgeRetentionAction(str, enum.Enum):
    NOTIFY = "notify"
    ARCHIVE = "archive"
    REVIEW = "review"


class KnowledgeCategory(Base):
    __tablename__ = "knowledge_categories"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    name_en: Mapped[str] = mapped_column(String(200), nullable=False)
    name_tr: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (Index("ix_knowledge_categories_active", "is_active"),)


class KnowledgeCollection(Base):
    __tablename__ = "knowledge_collections"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    collection_type: Mapped[str] = mapped_column(String(30), nullable=False, default="manual")
    smart_rules_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    is_shared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    document_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["KnowledgeCollectionItem"]] = relationship(
        "KnowledgeCollectionItem",
        back_populates="collection",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_knowledge_collections_type", "collection_type"),
        Index("ix_knowledge_collections_owner", "owner_user_id"),
    )


class KnowledgeCollectionItem(Base):
    __tablename__ = "knowledge_collection_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    collection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("knowledge_collections.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    added_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="manual")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    collection: Mapped["KnowledgeCollection"] = relationship(
        "KnowledgeCollection", back_populates="items"
    )

    __table_args__ = (
        UniqueConstraint("collection_id", "document_id", name="uq_knowledge_collection_document"),
        Index("ix_knowledge_collection_items_collection", "collection_id"),
        Index("ix_knowledge_collection_items_document", "document_id"),
    )


class KnowledgeReviewItem(Base):
    __tablename__ = "knowledge_review_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[str | None] = mapped_column(String(20), nullable=True)
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_knowledge_review_status", "status"),
        Index("ix_knowledge_review_reason", "reason"),
        Index("ix_knowledge_review_document", "document_id"),
    )


class KnowledgeRetentionPolicy(Base):
    __tablename__ = "knowledge_retention_policies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    retention_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action_on_expiry: Mapped[str] = mapped_column(String(40), nullable=False, default="notify")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    legal_hold_capable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class KnowledgeSetting(Base):
    __tablename__ = "knowledge_settings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    value_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
