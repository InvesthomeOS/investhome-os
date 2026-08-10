"""Persist Google Drive folder hierarchy on media_folders.

Revision ID: 0068_cs_media_folder_drive_ids
Revises: 0067_ai_semantic_search
Create Date: 2026-08-10

Additive only. Links Drive folder ids onto creative_studio_media_folders so
scanner sync can upsert real hierarchy and assets.folder_id can point at it.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0068_cs_media_folder_drive_ids"
down_revision: str | None = "0067_ai_semantic_search"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "creative_studio_media_folders",
        sa.Column("external_folder_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "creative_studio_media_folders",
        sa.Column("external_parent_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "creative_studio_media_folders",
        sa.Column("linked_project_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_cs_media_folders_linked_project_id",
        "creative_studio_media_folders",
        "projects",
        ["linked_project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_cs_media_folders_external_folder_id",
        "creative_studio_media_folders",
        ["external_folder_id"],
        unique=True,
    )
    op.create_index(
        "ix_cs_media_folders_external_parent_id",
        "creative_studio_media_folders",
        ["external_parent_id"],
    )
    op.create_index(
        "ix_cs_media_folders_linked_project_id",
        "creative_studio_media_folders",
        ["linked_project_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_cs_media_folders_linked_project_id", table_name="creative_studio_media_folders")
    op.drop_index("ix_cs_media_folders_external_parent_id", table_name="creative_studio_media_folders")
    op.drop_index("ix_cs_media_folders_external_folder_id", table_name="creative_studio_media_folders")
    op.drop_constraint(
        "fk_cs_media_folders_linked_project_id",
        "creative_studio_media_folders",
        type_="foreignkey",
    )
    op.drop_column("creative_studio_media_folders", "linked_project_id")
    op.drop_column("creative_studio_media_folders", "external_parent_id")
    op.drop_column("creative_studio_media_folders", "external_folder_id")
