"""Semantic search foundation: chunks + embeddings tables.

Revision ID: 0067_ai_semantic_search
Revises: 0066_ai_index_foundation
Create Date: 2026-08-07

Additive and reversible. No Drive mutations. Vectors stored as JSON for
SQLite/Postgres portability; VectorStore abstraction can adopt pgvector later.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0067_ai_semantic_search"
down_revision: str | None = "0066_ai_index_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_order", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["ai_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "chunk_order", name="uq_ai_chunks_document_order"),
    )
    op.create_index("ix_ai_chunks_document_id", "ai_chunks", ["document_id"])
    op.create_index("ix_ai_chunks_checksum", "ai_chunks", ["checksum"])

    op.create_table(
        "ai_embeddings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("vector", sa.JSON(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["chunk_id"], ["ai_chunks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chunk_id", "model", name="uq_ai_embeddings_chunk_model"),
    )
    op.create_index("ix_ai_embeddings_chunk_id", "ai_embeddings", ["chunk_id"])
    op.create_index("ix_ai_embeddings_model", "ai_embeddings", ["model"])
    op.create_index("ix_ai_embeddings_checksum", "ai_embeddings", ["checksum"])


def downgrade() -> None:
    op.drop_index("ix_ai_embeddings_checksum", table_name="ai_embeddings")
    op.drop_index("ix_ai_embeddings_model", table_name="ai_embeddings")
    op.drop_index("ix_ai_embeddings_chunk_id", table_name="ai_embeddings")
    op.drop_table("ai_embeddings")
    op.drop_index("ix_ai_chunks_checksum", table_name="ai_chunks")
    op.drop_index("ix_ai_chunks_document_id", table_name="ai_chunks")
    op.drop_table("ai_chunks")
