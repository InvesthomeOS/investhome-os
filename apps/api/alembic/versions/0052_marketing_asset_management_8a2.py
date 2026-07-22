"""Marketing asset management 8A2 — additive library fields.

Revision ID: 0052_mkt_assets_8a2
Revises: 0051_mkt_campaign_8a1
Create Date: 2026-07-19

Additive only. Extends marketing_assets for folders, campaign/project links,
notes, thumbnail document ref, and AI-prep metadata. Does not rewrite enums.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision: str = "0052_mkt_assets_8a2"
down_revision: str | None = "0051_mkt_campaign_8a1"
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
    if not _has_table("marketing_assets"):
        return

    if not _has_column("marketing_assets", "folder"):
        op.add_column("marketing_assets", sa.Column("folder", sa.String(length=40), nullable=True))
        op.create_index("ix_marketing_assets_folder", "marketing_assets", ["folder"])

    if not _has_column("marketing_assets", "project_id"):
        op.add_column("marketing_assets", sa.Column("project_id", sa.Uuid(), nullable=True))
        if _has_table("projects"):
            op.create_foreign_key(
                "fk_marketing_assets_project_id",
                "marketing_assets",
                "projects",
                ["project_id"],
                ["id"],
                ondelete="SET NULL",
            )
        if not _has_index("marketing_assets", "ix_marketing_assets_project_id"):
            op.create_index("ix_marketing_assets_project_id", "marketing_assets", ["project_id"])

    if not _has_column("marketing_assets", "campaign_id"):
        op.add_column("marketing_assets", sa.Column("campaign_id", sa.Uuid(), nullable=True))
        if _has_table("marketing_campaigns"):
            op.create_foreign_key(
                "fk_marketing_assets_campaign_id",
                "marketing_assets",
                "marketing_campaigns",
                ["campaign_id"],
                ["id"],
                ondelete="SET NULL",
            )
        if not _has_index("marketing_assets", "ix_marketing_assets_campaign_id"):
            op.create_index("ix_marketing_assets_campaign_id", "marketing_assets", ["campaign_id"])

    if not _has_column("marketing_assets", "notes"):
        op.add_column("marketing_assets", sa.Column("notes", sa.Text(), nullable=True))

    if not _has_column("marketing_assets", "thumbnail_document_id"):
        op.add_column("marketing_assets", sa.Column("thumbnail_document_id", sa.Uuid(), nullable=True))
        if _has_table("documents"):
            op.create_foreign_key(
                "fk_marketing_assets_thumbnail_document_id",
                "marketing_assets",
                "documents",
                ["thumbnail_document_id"],
                ["id"],
                ondelete="SET NULL",
            )

    if not _has_column("marketing_assets", "ai_prep_json"):
        op.add_column("marketing_assets", sa.Column("ai_prep_json", sa.JSON(), nullable=True))

    # Soft-map legacy active → ready without rewriting the column type/enum.
    op.execute(text("UPDATE marketing_assets SET status = 'ready' WHERE status = 'active'"))


def downgrade() -> None:
    if not _has_table("marketing_assets"):
        return

    op.execute(text("UPDATE marketing_assets SET status = 'active' WHERE status = 'ready'"))

    for fk_name in (
        "fk_marketing_assets_thumbnail_document_id",
        "fk_marketing_assets_campaign_id",
        "fk_marketing_assets_project_id",
    ):
        try:
            op.drop_constraint(fk_name, "marketing_assets", type_="foreignkey")
        except Exception:
            pass

    for index_name in (
        "ix_marketing_assets_campaign_id",
        "ix_marketing_assets_project_id",
        "ix_marketing_assets_folder",
    ):
        try:
            op.drop_index(index_name, table_name="marketing_assets")
        except Exception:
            pass

    for column in (
        "ai_prep_json",
        "thumbnail_document_id",
        "notes",
        "campaign_id",
        "project_id",
        "folder",
    ):
        if _has_column("marketing_assets", column):
            op.drop_column("marketing_assets", column)
