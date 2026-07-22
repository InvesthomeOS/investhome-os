"""Marketing AI Assistant outputs — Sprint 8A4.

Revision ID: 0054_mkt_ai_8a4
Revises: 0053_mkt_attrib_8a3
Create Date: 2026-07-19

Lightweight persistence for draft-only AI Marketing Assistant outputs.
Additive only.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0054_mkt_ai_8a4"
down_revision: str | None = "0053_mkt_attrib_8a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table: str) -> bool:
    return table in inspect(op.get_bind()).get_table_names()


def _has_index(table: str, index_name: str) -> bool:
    if not _has_table(table):
        return False
    return any(idx["name"] == index_name for idx in inspect(op.get_bind()).get_indexes(table))


def upgrade() -> None:
    if not _has_table("marketing_ai_outputs"):
        op.create_table(
            "marketing_ai_outputs",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("organization_id", sa.Uuid(), nullable=True),
            sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
            sa.Column("output_type", sa.String(length=60), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
            sa.Column("project_id", sa.Uuid(), nullable=True),
            sa.Column("campaign_id", sa.Uuid(), nullable=True),
            sa.Column("asset_id", sa.Uuid(), nullable=True),
            sa.Column("language", sa.String(length=10), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=True),
            sa.Column("input_summary", sa.Text(), nullable=True),
            sa.Column("generated_content", sa.Text(), nullable=False),
            sa.Column("structured_output", sa.JSON(), nullable=True),
            sa.Column("data_sources", sa.JSON(), nullable=True),
            sa.Column("data_warnings", sa.JSON(), nullable=True),
            sa.Column("assumptions", sa.JSON(), nullable=True),
            sa.Column("safety_flags", sa.JSON(), nullable=True),
            sa.Column("model_provider", sa.String(length=50), nullable=True),
            sa.Column("model_name", sa.String(length=80), nullable=True),
            sa.Column("prompt_key", sa.String(length=80), nullable=True),
            sa.Column("prompt_version", sa.String(length=40), nullable=True),
            sa.Column("token_usage", sa.JSON(), nullable=True),
            sa.Column("client_request_id", sa.String(length=80), nullable=True),
            sa.Column("context_snapshot", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["organization_id"], ["companies.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["campaign_id"], ["marketing_campaigns.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["asset_id"], ["marketing_assets.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )

    if _has_table("marketing_ai_outputs"):
        if not _has_index("marketing_ai_outputs", "ix_mkt_ai_outputs_org_created"):
            op.create_index(
                "ix_mkt_ai_outputs_org_created",
                "marketing_ai_outputs",
                ["organization_id", "created_at"],
            )
        if not _has_index("marketing_ai_outputs", "ix_mkt_ai_outputs_user_created"):
            op.create_index(
                "ix_mkt_ai_outputs_user_created",
                "marketing_ai_outputs",
                ["created_by_user_id", "created_at"],
            )
        if not _has_index("marketing_ai_outputs", "ix_mkt_ai_outputs_type_status"):
            op.create_index(
                "ix_mkt_ai_outputs_type_status",
                "marketing_ai_outputs",
                ["output_type", "status"],
            )
        if not _has_index("marketing_ai_outputs", "ix_mkt_ai_outputs_client_req"):
            op.create_index(
                "ix_mkt_ai_outputs_client_req",
                "marketing_ai_outputs",
                ["created_by_user_id", "client_request_id"],
            )


def downgrade() -> None:
    if _has_table("marketing_ai_outputs"):
        for name in (
            "ix_mkt_ai_outputs_client_req",
            "ix_mkt_ai_outputs_type_status",
            "ix_mkt_ai_outputs_user_created",
            "ix_mkt_ai_outputs_org_created",
        ):
            if _has_index("marketing_ai_outputs", name):
                op.drop_index(name, table_name="marketing_ai_outputs")
        op.drop_table("marketing_ai_outputs")
