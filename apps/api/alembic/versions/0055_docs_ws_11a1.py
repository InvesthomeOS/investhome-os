"""Documents Workspace Foundation — Sprint 11A1.

Revision ID: 0055_docs_ws_11a1
Revises: 0054_mkt_ai_8a4
Create Date: 2026-07-19

Additive workspace fields on documents: folder, visibility, file_kind,
owner, company, notes. Does not rewrite existing document engine tables.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0055_docs_ws_11a1"
down_revision: str | None = "0054_mkt_ai_8a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table: str) -> bool:
    return table in inspect(op.get_bind()).get_table_names()


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return any(col["name"] == column for col in inspect(op.get_bind()).get_columns(table))


def _has_index(table: str, index_name: str) -> bool:
    if not _has_table(table):
        return False
    return any(idx["name"] == index_name for idx in inspect(op.get_bind()).get_indexes(table))


def upgrade() -> None:
    if not _has_table("documents"):
        return

    if not _has_column("documents", "folder"):
        op.add_column(
            "documents",
            sa.Column("folder", sa.String(length=40), nullable=False, server_default="general"),
        )
    if not _has_column("documents", "visibility"):
        op.add_column(
            "documents",
            sa.Column("visibility", sa.String(length=30), nullable=False, server_default="organization"),
        )
    if not _has_column("documents", "file_kind"):
        op.add_column(
            "documents",
            sa.Column("file_kind", sa.String(length=30), nullable=False, server_default="other"),
        )
    if not _has_column("documents", "owner_user_id"):
        op.add_column("documents", sa.Column("owner_user_id", sa.Uuid(), nullable=True))
    if not _has_column("documents", "company_id"):
        op.add_column("documents", sa.Column("company_id", sa.Uuid(), nullable=True))
    if not _has_column("documents", "notes"):
        op.add_column("documents", sa.Column("notes", sa.Text(), nullable=True))

    # Backfill owner from uploader where missing
    op.execute(
        sa.text(
            "UPDATE documents SET owner_user_id = uploaded_by_user_id "
            "WHERE owner_user_id IS NULL AND uploaded_by_user_id IS NOT NULL"
        )
    )

    if not _has_index("documents", "ix_documents_folder"):
        op.create_index("ix_documents_folder", "documents", ["folder"])
    if not _has_index("documents", "ix_documents_visibility"):
        op.create_index("ix_documents_visibility", "documents", ["visibility"])
    if not _has_index("documents", "ix_documents_file_kind"):
        op.create_index("ix_documents_file_kind", "documents", ["file_kind"])
    if not _has_index("documents", "ix_documents_owner_user_id"):
        op.create_index("ix_documents_owner_user_id", "documents", ["owner_user_id"])
    if not _has_index("documents", "ix_documents_company_id"):
        op.create_index("ix_documents_company_id", "documents", ["company_id"])


def downgrade() -> None:
    if not _has_table("documents"):
        return

    for index_name in (
        "ix_documents_company_id",
        "ix_documents_owner_user_id",
        "ix_documents_file_kind",
        "ix_documents_visibility",
        "ix_documents_folder",
    ):
        if _has_index("documents", index_name):
            op.drop_index(index_name, table_name="documents")

    for column in ("notes", "company_id", "owner_user_id", "file_kind", "visibility", "folder"):
        if _has_column("documents", column):
            op.drop_column("documents", column)
