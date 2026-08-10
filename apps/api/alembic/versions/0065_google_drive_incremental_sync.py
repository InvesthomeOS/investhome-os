"""Google Drive incremental sync state + global Changes API cursor.

Revision ID: 0065_google_drive_incremental_sync
Revises: 0064_google_drive_asset_scanner
Create Date: 2026-08-07

Additive and reversible. Preserves existing mappings and media assets.

Also widens alembic_version.version_num before Alembic stamps this
revision id (34 chars) into the default VARCHAR(32) column.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0065_google_drive_incremental_sync"
down_revision: str | None = "0064_google_drive_asset_scanner"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Alembic stamps version_num AFTER upgrade() returns. This revision id is
# longer than the default VARCHAR(32), so widen first (idempotent).
_ALEMBIC_VERSION_NUM_LENGTH = 255


def _widen_alembic_version_num() -> None:
    """Widen alembic_version.version_num so long revision ids can be stamped.

    Uses information_schema so it works when the table lives in a non-public
    schema (e.g. search_path "$user", public).
    """
    bind = op.get_bind()
    row = bind.execute(
        sa.text(
            """
            SELECT table_schema, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'alembic_version'
              AND column_name = 'version_num'
            ORDER BY CASE WHEN table_schema = current_schema() THEN 0 ELSE 1 END
            LIMIT 1
            """
        )
    ).first()
    if row is None:
        return
    table_schema, current_length = row[0], row[1]
    if current_length is not None and int(current_length) >= _ALEMBIC_VERSION_NUM_LENGTH:
        return
    # Quote schema/table identifiers; length is an internal constant.
    bind.execute(
        sa.text(
            f'ALTER TABLE "{table_schema}"."alembic_version" '
            f"ALTER COLUMN version_num TYPE VARCHAR({_ALEMBIC_VERSION_NUM_LENGTH})"
        )
    )


def upgrade() -> None:
    _widen_alembic_version_num()

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
