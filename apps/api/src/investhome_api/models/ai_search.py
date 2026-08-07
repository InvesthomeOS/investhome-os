"""Semantic search foundation — chunks + embeddings over AI Documents.

Vectors are stored as JSON float arrays for SQLite/Postgres portability.
A VectorStore abstraction can later swap in pgvector / Qdrant / Pinecone.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


class AiChunk(Base):
    """Text chunk derived from an AiDocument (never stores binary / Drive bytes)."""

    __tablename__ = "ai_chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ai_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_order: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
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
        UniqueConstraint("document_id", "chunk_order", name="uq_ai_chunks_document_order"),
        Index("ix_ai_chunks_document_id", "document_id"),
        Index("ix_ai_chunks_checksum", "checksum"),
    )


class AiEmbedding(Base):
    """Embedding for one chunk + model. Unchanged chunks are skipped by checksum."""

    __tablename__ = "ai_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ai_chunks.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    # Portable vector payload (JSON list[float]) — never expose via search API
    vector: Mapped[list] = mapped_column(JSON, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("chunk_id", "model", name="uq_ai_embeddings_chunk_model"),
        Index("ix_ai_embeddings_chunk_id", "chunk_id"),
        Index("ix_ai_embeddings_model", "model"),
        Index("ix_ai_embeddings_checksum", "checksum"),
    )
