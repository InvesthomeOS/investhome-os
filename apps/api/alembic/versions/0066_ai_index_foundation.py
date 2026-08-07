"""AI Index foundation tables for Drive-backed project knowledge.

Revision ID: 0066_ai_index_foundation
Revises: 0065_google_drive_incremental_sync
Create Date: 2026-08-07

Additive and reversible. Preserves existing Drive sync and media assets.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0066_ai_index_foundation"
down_revision: str | None = "0065_google_drive_incremental_sync"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=True),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("drive_file_id", sa.String(length=128), nullable=True),
        sa.Column("document_type", sa.String(length=40), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("keywords", sa.JSON(), nullable=True),
        sa.Column("builders", sa.JSON(), nullable=True),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checksum", sa.String(length=64), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "index_status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("skip_reason", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["creative_studio_media_assets.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_documents_project_id", "ai_documents", ["project_id"])
    op.create_index("ix_ai_documents_asset_id", "ai_documents", ["asset_id"])
    op.create_index("ix_ai_documents_drive_file_id", "ai_documents", ["drive_file_id"])
    op.create_index("ix_ai_documents_index_status", "ai_documents", ["index_status"])
    op.create_index("ix_ai_documents_is_active", "ai_documents", ["is_active"])
    op.create_index("ix_ai_documents_category", "ai_documents", ["category"])
    op.create_index(
        "uq_ai_documents_asset_id",
        "ai_documents",
        ["asset_id"],
        unique=True,
        postgresql_where=sa.text("asset_id IS NOT NULL"),
        sqlite_where=sa.text("asset_id IS NOT NULL"),
    )
    op.create_index(
        "uq_ai_documents_project_drive_file",
        "ai_documents",
        ["project_id", "drive_file_id"],
        unique=True,
        postgresql_where=sa.text("drive_file_id IS NOT NULL"),
        sqlite_where=sa.text("drive_file_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_ai_documents_project_drive_file", table_name="ai_documents")
    op.drop_index("uq_ai_documents_asset_id", table_name="ai_documents")
    op.drop_index("ix_ai_documents_category", table_name="ai_documents")
    op.drop_index("ix_ai_documents_is_active", table_name="ai_documents")
    op.drop_index("ix_ai_documents_index_status", table_name="ai_documents")
    op.drop_index("ix_ai_documents_drive_file_id", table_name="ai_documents")
    op.drop_index("ix_ai_documents_asset_id", table_name="ai_documents")
    op.drop_index("ix_ai_documents_project_id", table_name="ai_documents")
    op.drop_table("ai_documents")
