"""Creative Studio Media Library tables.

Revision ID: 0063_cs_media_library
Revises: 0062_creative_studio_foundation
Create Date: 2026-08-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0063_cs_media_library"
down_revision: str | None = "0062_creative_studio_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "creative_studio_media_folders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("company_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["creative_studio_media_folders.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cs_media_folders_parent_id", "creative_studio_media_folders", ["parent_id"])
    op.create_index("ix_cs_media_folders_company_id", "creative_studio_media_folders", ["company_id"])
    op.create_index("ix_cs_media_folders_archived_at", "creative_studio_media_folders", ["archived_at"])

    op.create_table(
        "creative_studio_media_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("storage_provider", sa.String(length=20), server_default="local", nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("thumbnail_storage_key", sa.String(length=512), nullable=True),
        sa.Column("folder_id", sa.Uuid(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("company_id", sa.Uuid(), nullable=True),
        sa.Column("linked_project_id", sa.Uuid(), nullable=True),
        sa.Column("uploaded_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["folder_id"],
            ["creative_studio_media_folders.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["linked_project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cs_media_assets_folder_id", "creative_studio_media_assets", ["folder_id"])
    op.create_index("ix_cs_media_assets_company_id", "creative_studio_media_assets", ["company_id"])
    op.create_index(
        "ix_cs_media_assets_linked_project_id",
        "creative_studio_media_assets",
        ["linked_project_id"],
    )
    op.create_index(
        "ix_cs_media_assets_uploaded_by_user_id",
        "creative_studio_media_assets",
        ["uploaded_by_user_id"],
    )
    op.create_index("ix_cs_media_assets_archived_at", "creative_studio_media_assets", ["archived_at"])
    op.create_index("ix_cs_media_assets_filename", "creative_studio_media_assets", ["filename"])
    op.create_index("ix_cs_media_assets_storage_key", "creative_studio_media_assets", ["storage_key"])


def downgrade() -> None:
    op.drop_index("ix_cs_media_assets_storage_key", table_name="creative_studio_media_assets")
    op.drop_index("ix_cs_media_assets_filename", table_name="creative_studio_media_assets")
    op.drop_index("ix_cs_media_assets_archived_at", table_name="creative_studio_media_assets")
    op.drop_index("ix_cs_media_assets_uploaded_by_user_id", table_name="creative_studio_media_assets")
    op.drop_index("ix_cs_media_assets_linked_project_id", table_name="creative_studio_media_assets")
    op.drop_index("ix_cs_media_assets_company_id", table_name="creative_studio_media_assets")
    op.drop_index("ix_cs_media_assets_folder_id", table_name="creative_studio_media_assets")
    op.drop_table("creative_studio_media_assets")

    op.drop_index("ix_cs_media_folders_archived_at", table_name="creative_studio_media_folders")
    op.drop_index("ix_cs_media_folders_company_id", table_name="creative_studio_media_folders")
    op.drop_index("ix_cs_media_folders_parent_id", table_name="creative_studio_media_folders")
    op.drop_table("creative_studio_media_folders")
