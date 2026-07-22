"""Marketing campaign performance & lead attribution 8A3.

Revision ID: 0053_mkt_attrib_8a3
Revises: 0052_mkt_assets_8a2
Create Date: 2026-07-19

Primary campaign attribution per lead (single-touch). Additive only.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0053_mkt_attrib_8a3"
down_revision: str | None = "0052_mkt_assets_8a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table: str) -> bool:
    return table in inspect(op.get_bind()).get_table_names()


def _has_index(table: str, index_name: str) -> bool:
    if not _has_table(table):
        return False
    return any(idx["name"] == index_name for idx in inspect(op.get_bind()).get_indexes(table))


def upgrade() -> None:
    if not _has_table("marketing_lead_attributions"):
        op.create_table(
            "marketing_lead_attributions",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("lead_id", sa.Uuid(), nullable=False),
            sa.Column("campaign_id", sa.Uuid(), nullable=True),
            sa.Column("company_id", sa.Uuid(), nullable=True),
            sa.Column("attribution_source", sa.String(length=20), nullable=False, server_default="other"),
            sa.Column("utm_source", sa.String(length=255), nullable=True),
            sa.Column("utm_medium", sa.String(length=255), nullable=True),
            sa.Column("utm_campaign", sa.String(length=255), nullable=True),
            sa.Column("utm_term", sa.String(length=255), nullable=True),
            sa.Column("utm_content", sa.String(length=255), nullable=True),
            sa.Column("first_touch_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("attribution_reason", sa.Text(), nullable=True),
            sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
            sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("lead_id", name="uq_marketing_lead_attributions_lead_id"),
        )
        if _has_table("leads"):
            op.create_foreign_key(
                "fk_mkt_lead_attrib_lead_id",
                "marketing_lead_attributions",
                "leads",
                ["lead_id"],
                ["id"],
                ondelete="CASCADE",
            )
        if _has_table("marketing_campaigns"):
            op.create_foreign_key(
                "fk_mkt_lead_attrib_campaign_id",
                "marketing_lead_attributions",
                "marketing_campaigns",
                ["campaign_id"],
                ["id"],
                ondelete="SET NULL",
            )
        if _has_table("companies"):
            op.create_foreign_key(
                "fk_mkt_lead_attrib_company_id",
                "marketing_lead_attributions",
                "companies",
                ["company_id"],
                ["id"],
                ondelete="SET NULL",
            )
        if _has_table("users"):
            op.create_foreign_key(
                "fk_mkt_lead_attrib_created_by",
                "marketing_lead_attributions",
                "users",
                ["created_by_user_id"],
                ["id"],
                ondelete="SET NULL",
            )
            op.create_foreign_key(
                "fk_mkt_lead_attrib_updated_by",
                "marketing_lead_attributions",
                "users",
                ["updated_by_user_id"],
                ["id"],
                ondelete="SET NULL",
            )

        for idx_name, cols in (
            ("ix_mkt_lead_attrib_lead_id", ["lead_id"]),
            ("ix_mkt_lead_attrib_campaign_id", ["campaign_id"]),
            ("ix_mkt_lead_attrib_company_id", ["company_id"]),
            ("ix_mkt_lead_attrib_created_at", ["created_at"]),
            ("ix_mkt_lead_attrib_converted_at", ["converted_at"]),
            ("ix_mkt_lead_attrib_utm_source", ["utm_source"]),
        ):
            if not _has_index("marketing_lead_attributions", idx_name):
                op.create_index(idx_name, "marketing_lead_attributions", cols)

    if not _has_table("marketing_lead_attribution_audit"):
        op.create_table(
            "marketing_lead_attribution_audit",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("attribution_id", sa.Uuid(), nullable=True),
            sa.Column("lead_id", sa.Uuid(), nullable=False),
            sa.Column("previous_campaign_id", sa.Uuid(), nullable=True),
            sa.Column("new_campaign_id", sa.Uuid(), nullable=True),
            sa.Column("changed_by_user_id", sa.Uuid(), nullable=True),
            sa.Column("change_reason", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        if _has_table("marketing_lead_attributions"):
            op.create_foreign_key(
                "fk_mkt_lead_attrib_audit_attrib_id",
                "marketing_lead_attribution_audit",
                "marketing_lead_attributions",
                ["attribution_id"],
                ["id"],
                ondelete="SET NULL",
            )
        if _has_table("leads"):
            op.create_foreign_key(
                "fk_mkt_lead_attrib_audit_lead_id",
                "marketing_lead_attribution_audit",
                "leads",
                ["lead_id"],
                ["id"],
                ondelete="CASCADE",
            )
        if _has_table("marketing_campaigns"):
            op.create_foreign_key(
                "fk_mkt_lead_attrib_audit_prev_campaign",
                "marketing_lead_attribution_audit",
                "marketing_campaigns",
                ["previous_campaign_id"],
                ["id"],
                ondelete="SET NULL",
            )
            op.create_foreign_key(
                "fk_mkt_lead_attrib_audit_new_campaign",
                "marketing_lead_attribution_audit",
                "marketing_campaigns",
                ["new_campaign_id"],
                ["id"],
                ondelete="SET NULL",
            )
        if _has_table("users"):
            op.create_foreign_key(
                "fk_mkt_lead_attrib_audit_changed_by",
                "marketing_lead_attribution_audit",
                "users",
                ["changed_by_user_id"],
                ["id"],
                ondelete="SET NULL",
            )
        if not _has_index("marketing_lead_attribution_audit", "ix_mkt_lead_attrib_audit_lead_id"):
            op.create_index(
                "ix_mkt_lead_attrib_audit_lead_id",
                "marketing_lead_attribution_audit",
                ["lead_id"],
            )


def downgrade() -> None:
    if _has_table("marketing_lead_attribution_audit"):
        op.drop_table("marketing_lead_attribution_audit")
    if _has_table("marketing_lead_attributions"):
        op.drop_table("marketing_lead_attributions")
