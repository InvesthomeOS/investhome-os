"""Document intelligence: expanded analysis, chunks, conversations, AI usage.

Revision ID: 0011_document_intelligence
Revises: 0010_create_documents
Create Date: 2026-07-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_document_intelligence"
down_revision: str | None = "0010_create_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("document_analyses", sa.Column("document_version_id", sa.Uuid(), nullable=True))
    op.add_column("document_analyses", sa.Column("processing_status", sa.String(length=30), nullable=True))
    op.add_column("document_analyses", sa.Column("extraction_method", sa.String(length=50), nullable=True))
    op.add_column("document_analyses", sa.Column("detected_language", sa.String(length=20), nullable=True))
    op.add_column("document_analyses", sa.Column("classification_confidence", sa.String(length=20), nullable=True))
    op.add_column("document_analyses", sa.Column("classification_explanation", sa.Text(), nullable=True))
    op.add_column("document_analyses", sa.Column("classification_status", sa.String(length=20), nullable=True))
    op.add_column("document_analyses", sa.Column("extracted_text_preview", sa.Text(), nullable=True))
    op.add_column("document_analyses", sa.Column("page_count", sa.Integer(), nullable=True))
    op.add_column("document_analyses", sa.Column("word_count", sa.Integer(), nullable=True))
    op.add_column("document_analyses", sa.Column("ai_summary_en", sa.Text(), nullable=True))
    op.add_column("document_analyses", sa.Column("structured_data_json", sa.Text(), nullable=True))
    op.add_column("document_analyses", sa.Column("extracted_entities_json", sa.Text(), nullable=True))
    op.add_column("document_analyses", sa.Column("extracted_dates_json", sa.Text(), nullable=True))
    op.add_column("document_analyses", sa.Column("extracted_amounts_json", sa.Text(), nullable=True))
    op.add_column("document_analyses", sa.Column("extracted_parties_json", sa.Text(), nullable=True))
    op.add_column("document_analyses", sa.Column("extracted_obligations_json", sa.Text(), nullable=True))
    op.add_column("document_analyses", sa.Column("extracted_risks_json", sa.Text(), nullable=True))
    op.add_column("document_analyses", sa.Column("model_provider", sa.String(length=50), nullable=True))
    op.add_column("document_analyses", sa.Column("model_name", sa.String(length=80), nullable=True))
    op.add_column("document_analyses", sa.Column("prompt_version", sa.String(length=40), nullable=True))
    op.add_column("document_analyses", sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("document_analyses", sa.Column("retry_count", sa.Integer(), server_default=sa.text("0"), nullable=False))

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_reference", sa.String(length=500), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("embedding_provider", sa.String(length=50), nullable=True),
        sa.Column("embedding_model", sa.String(length=80), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["analysis_id"], ["document_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_version_id", "document_chunks", ["document_version_id"])

    op.create_table(
        "document_conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_conversations_document_id", "document_conversations", ["document_id"])
    op.create_index("ix_document_conversations_user_id", "document_conversations", ["user_id"])

    op.create_table(
        "document_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_references_json", sa.Text(), nullable=True),
        sa.Column("model_provider", sa.String(length=50), nullable=True),
        sa.Column("model_name", sa.String(length=80), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["document_conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_messages_conversation_id", "document_messages", ["conversation_id"])

    op.create_table(
        "ai_usage",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("analysis_id", sa.Uuid(), nullable=True),
        sa.Column("conversation_id", sa.Uuid(), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=80), nullable=True),
        sa.Column("operation", sa.String(length=50), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("ocr_pages", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("estimated_cost_usd", sa.String(length=20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_usage_document_id", "ai_usage", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_usage_document_id", table_name="ai_usage")
    op.drop_table("ai_usage")
    op.drop_index("ix_document_messages_conversation_id", table_name="document_messages")
    op.drop_table("document_messages")
    op.drop_index("ix_document_conversations_user_id", table_name="document_conversations")
    op.drop_index("ix_document_conversations_document_id", table_name="document_conversations")
    op.drop_table("document_conversations")
    op.drop_index("ix_document_chunks_version_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")
    for col in (
        "retry_count",
        "processing_started_at",
        "prompt_version",
        "model_name",
        "model_provider",
        "extracted_risks_json",
        "extracted_obligations_json",
        "extracted_parties_json",
        "extracted_amounts_json",
        "extracted_dates_json",
        "extracted_entities_json",
        "structured_data_json",
        "ai_summary_en",
        "word_count",
        "page_count",
        "extracted_text_preview",
        "classification_status",
        "classification_explanation",
        "classification_confidence",
        "detected_language",
        "extraction_method",
        "processing_status",
        "document_version_id",
    ):
        op.drop_column("document_analyses", col)
