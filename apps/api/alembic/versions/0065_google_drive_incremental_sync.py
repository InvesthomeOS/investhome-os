"""Google Drive incremental sync state + global Changes API cursor.

Revision ID: 0065_google_drive_incremental_sync
Revises: 0064_google_drive_asset_scanner
Create Date: 2026-08-07

Additive and reversible. Preserves existing mappings and media assets.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0065_google_drive_incremental_sync"
down_revision: str | None = "0064_google_drive_asset_scanner"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "google_drive_sync_cursors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cursor_key", sa.String(length=64), nullable=False),
        sa.Column("start_page_token", sa.String(length=256), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cursor_key", name="uq_google_drive_sync_cursors_key"),
    )

    op.add_column(
        "project_drive_mappings",
        sa.Column(
            "last_successful_sync_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "project_drive_mappings",
        sa.Column(
            "last_sync_status",
            sa.String(length=20),
            server_default=sa.text("'IDLE'"),
            nullable=False,
        ),
    )
    op.add_column(
        "project_drive_mappings",
        sa.Column("last_sync_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "project_drive_mappings",
        sa.Column("sync_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "project_drive_mappings",
        sa.Column(
            "force_full_sync",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "project_drive_mappings",
        sa.Column("mapped_folder_id_at_sync", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "ix_project_drive_mappings_last_sync_status",
        "project_drive_mappings",
        ["last_sync_status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_project_drive_mappings_last_sync_status",
        table_name="project_drive_mappings",
    )
    op.drop_column("project_drive_mappings", "mapped_folder_id_at_sync")
    op.drop_column("project_drive_mappings", "force_full_sync")
    op.drop_column("project_drive_mappings", "sync_started_at")
    op.drop_column("project_drive_mappings", "last_sync_error")
    op.drop_column("project_drive_mappings", "last_sync_status")
    op.drop_column("project_drive_mappings", "last_successful_sync_at")
    op.drop_table("google_drive_sync_cursors")
