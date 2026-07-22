"""Marketing campaign foundation 8A1 — additive campaign fields.

Revision ID: 0051_mkt_campaign_8a1
Revises: 0050_project_cost_tracking
Create Date: 2026-07-19

Additive only. Extends marketing_campaigns for lightweight workspace DoD:
notes, lead_source_id, target_project_id, primary_channel, company_id.
Does not rewrite existing campaign_type / status enums.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0051_mkt_campaign_8a1"
down_revision: str | None = "0050_project_cost_tracking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table: str) -> bool:
    return table in inspect(op.get_bind()).get_table_names()


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return any(col["name"] == column for col in inspect(op.get_bind()).get_columns(table))


def upgrade() -> None:
    if not _has_table("marketing_campaigns"):
        return

    if not _has_column("marketing_campaigns", "notes"):
        op.add_column("marketing_campaigns", sa.Column("notes", sa.Text(), nullable=True))

    if not _has_column("marketing_campaigns", "primary_channel"):
        op.add_column(
            "marketing_campaigns",
            sa.Column("primary_channel", sa.String(length=30), nullable=True),
        )
        op.create_index(
            "ix_marketing_campaigns_primary_channel",
            "marketing_campaigns",
            ["primary_channel"],
        )

    if not _has_column("marketing_campaigns", "lead_source_id"):
        op.add_column(
            "marketing_campaigns",
            sa.Column("lead_source_id", sa.Uuid(), nullable=True),
        )
        if _has_table("marketing_lead_sources"):
            op.create_foreign_key(
                "fk_marketing_campaigns_lead_source_id",
                "marketing_campaigns",
                "marketing_lead_sources",
                ["lead_source_id"],
                ["id"],
                ondelete="SET NULL",
            )
        op.create_index(
            "ix_marketing_campaigns_lead_source_id",
            "marketing_campaigns",
            ["lead_source_id"],
        )

    if not _has_column("marketing_campaigns", "target_project_id"):
        op.add_column(
            "marketing_campaigns",
            sa.Column("target_project_id", sa.Uuid(), nullable=True),
        )
        if _has_table("projects"):
            op.create_foreign_key(
                "fk_marketing_campaigns_target_project_id",
                "marketing_campaigns",
                "projects",
                ["target_project_id"],
                ["id"],
                ondelete="SET NULL",
            )
        op.create_index(
            "ix_marketing_campaigns_target_project_id",
            "marketing_campaigns",
            ["target_project_id"],
        )

    if not _has_column("marketing_campaigns", "company_id"):
        op.add_column(
            "marketing_campaigns",
            sa.Column("company_id", sa.Uuid(), nullable=True),
        )
        if _has_table("companies"):
            op.create_foreign_key(
                "fk_marketing_campaigns_company_id",
                "marketing_campaigns",
                "companies",
                ["company_id"],
                ["id"],
                ondelete="SET NULL",
            )
        op.create_index(
            "ix_marketing_campaigns_company_id",
            "marketing_campaigns",
            ["company_id"],
        )


def downgrade() -> None:
    if not _has_table("marketing_campaigns"):
        return

    for index_name in (
        "ix_marketing_campaigns_company_id",
        "ix_marketing_campaigns_target_project_id",
        "ix_marketing_campaigns_lead_source_id",
        "ix_marketing_campaigns_primary_channel",
    ):
        try:
            op.drop_index(index_name, table_name="marketing_campaigns")
        except Exception:
            pass

    for fk_name in (
        "fk_marketing_campaigns_company_id",
        "fk_marketing_campaigns_target_project_id",
        "fk_marketing_campaigns_lead_source_id",
    ):
        try:
            op.drop_constraint(fk_name, "marketing_campaigns", type_="foreignkey")
        except Exception:
            pass

    for column in ("company_id", "target_project_id", "lead_source_id", "primary_channel", "notes"):
        if _has_column("marketing_campaigns", column):
            op.drop_column("marketing_campaigns", column)
