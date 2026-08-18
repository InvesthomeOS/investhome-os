"""Alembic: creative_director_campaigns table.

Revision ID: 0069_creative_director_campaigns
Revises: 0068_cs_media_folder_drive_ids
Create Date: 2026-08-18

Additive only. Persists Creative Director Campaign Context for later builders.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0069_creative_director_campaigns"
down_revision: str | None = "0068_cs_media_folder_drive_ids"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "creative_director_campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("linked_project_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("mode", sa.String(length=32), server_default="project", nullable=False),
        sa.Column("original_brief", sa.Text(), nullable=False),
        sa.Column("context_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["linked_project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_creative_director_campaigns_linked_project_id",
        "creative_director_campaigns",
        ["linked_project_id"],
    )
    op.create_index(
        "ix_creative_director_campaigns_created_by_user_id",
        "creative_director_campaigns",
        ["created_by_user_id"],
    )
    op.create_index(
        "ix_creative_director_campaigns_status",
        "creative_director_campaigns",
        ["status"],
    )
    op.create_index(
        "ix_creative_director_campaigns_created_at",
        "creative_director_campaigns",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_creative_director_campaigns_created_at", table_name="creative_director_campaigns")
    op.drop_index("ix_creative_director_campaigns_status", table_name="creative_director_campaigns")
    op.drop_index(
        "ix_creative_director_campaigns_created_by_user_id",
        table_name="creative_director_campaigns",
    )
    op.drop_index(
        "ix_creative_director_campaigns_linked_project_id",
        table_name="creative_director_campaigns",
    )
    op.drop_table("creative_director_campaigns")
