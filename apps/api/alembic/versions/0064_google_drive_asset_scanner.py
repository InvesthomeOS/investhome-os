"""Google Drive project mapping + media asset Drive fields.

Revision ID: 0064_google_drive_asset_scanner
Revises: 0063_cs_media_library
Create Date: 2026-08-07

Additive and reversible. Preserves existing media asset rows and UUIDs.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0064_google_drive_asset_scanner"
down_revision: str | None = "0063_cs_media_library"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_drive_mappings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("drive_folder_id", sa.String(length=128), nullable=False),
        sa.Column("drive_sync_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_drive_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", name="uq_project_drive_mappings_project_id"),
    )
    op.create_index(
        "ix_project_drive_mappings_drive_folder_id",
        "project_drive_mappings",
        ["drive_folder_id"],
    )
    # Unique among active (non-archived) mappings — partial unique index.
    op.create_index(
        "uq_project_drive_mappings_active_folder",
        "project_drive_mappings",
        ["drive_folder_id"],
        unique=True,
        postgresql_where=sa.text("archived_at IS NULL"),
        sqlite_where=sa.text("archived_at IS NULL"),
    )

    op.add_column(
        "creative_studio_media_assets",
        sa.Column("source_type", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "creative_studio_media_assets",
        sa.Column("external_file_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "creative_studio_media_assets",
        sa.Column("external_parent_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "creative_studio_media_assets",
        sa.Column("external_modified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "creative_studio_media_assets",
        sa.Column("external_checksum", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "creative_studio_media_assets",
        sa.Column("sync_status", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "creative_studio_media_assets",
        sa.Column("folder_category", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "creative_studio_media_assets",
        sa.Column("possible_duplicate", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "creative_studio_media_assets",
        sa.Column("web_view_link", sa.String(length=1024), nullable=True),
    )
    op.add_column(
        "creative_studio_media_assets",
        sa.Column("external_thumbnail_link", sa.String(length=1024), nullable=True),
    )
    op.add_column(
        "creative_studio_media_assets",
        sa.Column("drive_meta_json", sa.JSON(), nullable=True),
    )

    op.create_index(
        "ix_cs_media_assets_source_type",
        "creative_studio_media_assets",
        ["source_type"],
    )
    op.create_index(
        "ix_cs_media_assets_external_file_id",
        "creative_studio_media_assets",
        ["external_file_id"],
    )
    op.create_index(
        "ix_cs_media_assets_sync_status",
        "creative_studio_media_assets",
        ["sync_status"],
    )
    op.create_index(
        "uq_cs_media_assets_drive_file",
        "creative_studio_media_assets",
        ["external_file_id"],
        unique=True,
        postgresql_where=sa.text("external_file_id IS NOT NULL AND source_type = 'google_drive'"),
        sqlite_where=sa.text("external_file_id IS NOT NULL AND source_type = 'google_drive'"),
    )


def downgrade() -> None:
    op.drop_index("uq_cs_media_assets_drive_file", table_name="creative_studio_media_assets")
    op.drop_index("ix_cs_media_assets_sync_status", table_name="creative_studio_media_assets")
    op.drop_index("ix_cs_media_assets_external_file_id", table_name="creative_studio_media_assets")
    op.drop_index("ix_cs_media_assets_source_type", table_name="creative_studio_media_assets")

    op.drop_column("creative_studio_media_assets", "drive_meta_json")
    op.drop_column("creative_studio_media_assets", "external_thumbnail_link")
    op.drop_column("creative_studio_media_assets", "web_view_link")
    op.drop_column("creative_studio_media_assets", "possible_duplicate")
    op.drop_column("creative_studio_media_assets", "folder_category")
    op.drop_column("creative_studio_media_assets", "sync_status")
    op.drop_column("creative_studio_media_assets", "external_checksum")
    op.drop_column("creative_studio_media_assets", "external_modified_at")
    op.drop_column("creative_studio_media_assets", "external_parent_id")
    op.drop_column("creative_studio_media_assets", "external_file_id")
    op.drop_column("creative_studio_media_assets", "source_type")

    op.drop_index("uq_project_drive_mappings_active_folder", table_name="project_drive_mappings")
    op.drop_index("ix_project_drive_mappings_drive_folder_id", table_name="project_drive_mappings")
    op.drop_table("project_drive_mappings")
