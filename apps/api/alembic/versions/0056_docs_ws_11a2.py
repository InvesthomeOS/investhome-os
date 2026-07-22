"""Documents Workspace Completion — Sprint 11A2.

Revision ID: 0056_docs_ws_11a2
Revises: 0055_docs_ws_11a1
Create Date: 2026-07-19

Additive access counters for honest Most Viewed / download metrics.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0056_docs_ws_11a2"
down_revision: str | None = "0055_docs_ws_11a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table: str) -> bool:
    return table in inspect(op.get_bind()).get_table_names()


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return any(col["name"] == column for col in inspect(op.get_bind()).get_columns(table))


def upgrade() -> None:
    if not _has_table("documents"):
        return

    if not _has_column("documents", "download_count"):
        op.add_column(
            "documents",
            sa.Column("download_count", sa.Integer(), nullable=False, server_default="0"),
        )
    if not _has_column("documents", "preview_count"):
        op.add_column(
            "documents",
            sa.Column("preview_count", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    if not _has_table("documents"):
        return
    for column in ("preview_count", "download_count"):
        if _has_column("documents", column):
            op.drop_column("documents", column)
