"""BI saved reports and alert thresholds — Product Polish P9.

Revision ID: 0057_bi_saved_reports
Revises: 0056_docs_ws_11a2
Create Date: 2026-07-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0057_bi_saved_reports"
down_revision: str | None = "0056_docs_ws_11a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table: str) -> bool:
    return table in inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not _has_table("bi_saved_reports"):
        op.create_table(
            "bi_saved_reports",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("domain", sa.String(40), nullable=False, server_default="executive"),
            sa.Column("chart_type", sa.String(40), nullable=False, server_default="kpi"),
            sa.Column("metric_keys_json", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default="[]"),
            sa.Column("filters_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("layout_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("is_shared", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_bi_saved_reports_owner", "bi_saved_reports", ["owner_user_id"])
        op.create_index("ix_bi_saved_reports_domain", "bi_saved_reports", ["domain"])

    if not _has_table("bi_alert_thresholds"):
        op.create_table(
            "bi_alert_thresholds",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("metric_key", sa.String(80), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("operator", sa.String(20), nullable=False),
            sa.Column("threshold_value", sa.String(64), nullable=False),
            sa.Column("severity", sa.String(20), nullable=False, server_default="warning"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("filters_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("metric_key", "name", name="uq_bi_alert_thresholds_metric_name"),
        )
        op.create_index("ix_bi_alert_thresholds_metric", "bi_alert_thresholds", ["metric_key"])


def downgrade() -> None:
    if _has_table("bi_alert_thresholds"):
        op.drop_index("ix_bi_alert_thresholds_metric", table_name="bi_alert_thresholds")
        op.drop_table("bi_alert_thresholds")
    if _has_table("bi_saved_reports"):
        op.drop_index("ix_bi_saved_reports_domain", table_name="bi_saved_reports")
        op.drop_index("ix_bi_saved_reports_owner", table_name="bi_saved_reports")
        op.drop_table("bi_saved_reports")
