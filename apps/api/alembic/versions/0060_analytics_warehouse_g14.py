"""G14 analytics warehouse schema + core tables.

Revision ID: 0060_analytics_warehouse_g14
Revises: 0059_merge_p10_p11
Create Date: 2026-07-20

Non-destructive: creates isolated `analytics` schema only. Does not modify
or delete operational/transactional data.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text
from sqlalchemy.dialects import postgresql

revision: str = "0060_analytics_warehouse_g14"
down_revision: str | None = "0059_merge_p10_p11"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "analytics"


def _schema_exists() -> bool:
    bind = op.get_bind()
    row = bind.execute(
        text("SELECT 1 FROM information_schema.schemata WHERE schema_name = :s"),
        {"s": SCHEMA},
    ).scalar()
    return row is not None


def _has_table(table: str) -> bool:
    bind = op.get_bind()
    insp = inspect(bind)
    return table in insp.get_table_names(schema=SCHEMA)


def upgrade() -> None:
    op.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))

    if not _has_table("wh_ingestion_runs"):
        op.create_table(
            "wh_ingestion_runs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("domain", sa.String(64), nullable=False),
            sa.Column("job_name", sa.String(128), nullable=False),
            sa.Column("mode", sa.String(32), nullable=False, server_default="incremental"),
            sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
            sa.Column("watermark_from", sa.DateTime(timezone=True), nullable=True),
            sa.Column("watermark_to", sa.DateTime(timezone=True), nullable=True),
            sa.Column("rows_read", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("rows_written", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("rows_rejected", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("reject_reasons_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("meta_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            schema=SCHEMA,
        )
        op.create_index(
            "ix_wh_ingestion_runs_domain_status",
            "wh_ingestion_runs",
            ["domain", "status"],
            schema=SCHEMA,
        )
        op.create_index(
            "ix_wh_ingestion_runs_started",
            "wh_ingestion_runs",
            ["started_at"],
            schema=SCHEMA,
        )

    if not _has_table("wh_fx_rates"):
        op.create_table(
            "wh_fx_rates",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("rate_date", sa.Date(), nullable=False),
            sa.Column("from_currency", sa.String(3), nullable=False),
            sa.Column("to_currency", sa.String(3), nullable=False),
            sa.Column("rate", sa.Numeric(18, 8), nullable=False),
            sa.Column("source", sa.String(64), nullable=False, server_default="manual"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("rate_date", "from_currency", "to_currency", name="uq_wh_fx_rates_day_pair"),
            schema=SCHEMA,
        )

    if not _has_table("wh_dim_date"):
        op.create_table(
            "wh_dim_date",
            sa.Column("date_key", sa.Integer(), primary_key=True),
            sa.Column("full_date", sa.Date(), nullable=False, unique=True),
            sa.Column("year", sa.Integer(), nullable=False),
            sa.Column("quarter", sa.Integer(), nullable=False),
            sa.Column("month", sa.Integer(), nullable=False),
            sa.Column("week", sa.Integer(), nullable=False),
            sa.Column("day_of_week", sa.Integer(), nullable=False),
            sa.Column("is_month_end", sa.Boolean(), nullable=False, server_default="false"),
            schema=SCHEMA,
        )

    if not _has_table("wh_dim_currency"):
        op.create_table(
            "wh_dim_currency",
            sa.Column("currency_code", sa.String(3), primary_key=True),
            sa.Column("name", sa.String(64), nullable=False),
            sa.Column("is_reporting", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("decimals", sa.Integer(), nullable=False, server_default="2"),
            schema=SCHEMA,
        )

    if not _has_table("wh_dim_project"):
        op.create_table(
            "wh_dim_project",
            sa.Column("project_sk", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("source_project_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("status", sa.String(64), nullable=True),
            sa.Column("project_type", sa.String(64), nullable=True),
            sa.Column("currency", sa.String(3), nullable=True),
            sa.Column("classification", sa.String(32), nullable=False, server_default="internal"),
            sa.Column("effective_from", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_current", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("ingestion_run_id", postgresql.UUID(as_uuid=True), nullable=True),
            schema=SCHEMA,
        )
        op.create_index("ix_wh_dim_project_source", "wh_dim_project", ["source_project_id"], schema=SCHEMA)

    if not _has_table("wh_dim_investor"):
        op.create_table(
            "wh_dim_investor",
            sa.Column("investor_sk", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("source_investor_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
            sa.Column("display_name", sa.String(255), nullable=False),
            sa.Column("status", sa.String(64), nullable=True),
            sa.Column("country", sa.String(64), nullable=True),
            sa.Column("classification", sa.String(32), nullable=False, server_default="confidential"),
            sa.Column("effective_from", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_current", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("ingestion_run_id", postgresql.UUID(as_uuid=True), nullable=True),
            schema=SCHEMA,
        )
        op.create_index("ix_wh_dim_investor_source", "wh_dim_investor", ["source_investor_id"], schema=SCHEMA)

    if not _has_table("wh_dim_campaign"):
        op.create_table(
            "wh_dim_campaign",
            sa.Column("campaign_sk", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("source_campaign_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("status", sa.String(64), nullable=True),
            sa.Column("channel", sa.String(64), nullable=True),
            sa.Column("classification", sa.String(32), nullable=False, server_default="internal"),
            sa.Column("is_current", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("ingestion_run_id", postgresql.UUID(as_uuid=True), nullable=True),
            schema=SCHEMA,
        )

    if not _has_table("wh_status_history"):
        op.create_table(
            "wh_status_history",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("entity_type", sa.String(64), nullable=False),
            sa.Column("source_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("from_status", sa.String(64), nullable=True),
            sa.Column("to_status", sa.String(64), nullable=False),
            sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("changed_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("ingestion_run_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("meta_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            schema=SCHEMA,
        )
        op.create_index(
            "ix_wh_status_history_entity",
            "wh_status_history",
            ["entity_type", "source_entity_id"],
            schema=SCHEMA,
        )

    if not _has_table("wh_fact_cash_movement"):
        op.create_table(
            "wh_fact_cash_movement",
            sa.Column("cash_sk", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("source_transaction_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("date_key", sa.Integer(), nullable=False),
            sa.Column("project_sk", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("txn_type", sa.String(64), nullable=False),
            sa.Column("amount_original", sa.Numeric(18, 2), nullable=False),
            sa.Column("currency_original", sa.String(3), nullable=False),
            sa.Column("amount_usd", sa.Numeric(18, 2), nullable=True),
            sa.Column("amount_try", sa.Numeric(18, 2), nullable=True),
            sa.Column("fx_rate_usd", sa.Numeric(18, 8), nullable=True),
            sa.Column("fx_rate_try", sa.Numeric(18, 8), nullable=True),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("ingestion_run_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.UniqueConstraint("source_transaction_id", name="uq_wh_fact_cash_source_txn"),
            schema=SCHEMA,
        )
        op.create_index("ix_wh_fact_cash_date", "wh_fact_cash_movement", ["date_key"], schema=SCHEMA)

    if not _has_table("wh_fact_pipeline"):
        op.create_table(
            "wh_fact_pipeline",
            sa.Column("pipeline_sk", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("source_opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("snapshot_date", sa.Date(), nullable=False),
            sa.Column("date_key", sa.Integer(), nullable=False),
            sa.Column("project_sk", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("investor_sk", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("stage", sa.String(64), nullable=False),
            sa.Column("is_open", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("expected_revenue_original", sa.Numeric(18, 2), nullable=True),
            sa.Column("currency_original", sa.String(3), nullable=True),
            sa.Column("expected_revenue_usd", sa.Numeric(18, 2), nullable=True),
            sa.Column("expected_revenue_try", sa.Numeric(18, 2), nullable=True),
            sa.Column("probability", sa.Numeric(5, 2), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("ingestion_run_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.UniqueConstraint("source_opportunity_id", "snapshot_date", name="uq_wh_fact_pipeline_snap"),
            schema=SCHEMA,
        )
        op.create_index("ix_wh_fact_pipeline_date", "wh_fact_pipeline", ["snapshot_date"], schema=SCHEMA)

    if not _has_table("wh_fact_investor_activity"):
        op.create_table(
            "wh_fact_investor_activity",
            sa.Column("activity_sk", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("source_investor_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("investor_sk", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("snapshot_date", sa.Date(), nullable=False),
            sa.Column("status", sa.String(64), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("commitment_original", sa.Numeric(18, 2), nullable=True),
            sa.Column("currency_original", sa.String(3), nullable=True),
            sa.Column("commitment_usd", sa.Numeric(18, 2), nullable=True),
            sa.Column("commitment_try", sa.Numeric(18, 2), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("ingestion_run_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.UniqueConstraint("source_investor_id", "snapshot_date", name="uq_wh_fact_inv_act_snap"),
            schema=SCHEMA,
        )

    if not _has_table("wh_fact_marketing_spend"):
        op.create_table(
            "wh_fact_marketing_spend",
            sa.Column("spend_sk", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("source_row_id", sa.String(128), nullable=False),
            sa.Column("campaign_sk", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("date_key", sa.Integer(), nullable=False),
            sa.Column("spend_original", sa.Numeric(18, 2), nullable=False),
            sa.Column("currency_original", sa.String(3), nullable=False),
            sa.Column("spend_usd", sa.Numeric(18, 2), nullable=True),
            sa.Column("spend_try", sa.Numeric(18, 2), nullable=True),
            sa.Column("attributed_value_original", sa.Numeric(18, 2), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("ingestion_run_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.UniqueConstraint("source_row_id", name="uq_wh_fact_mkt_spend_source"),
            schema=SCHEMA,
        )

    if not _has_table("wh_mart_executive_daily"):
        op.create_table(
            "wh_mart_executive_daily",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("snapshot_date", sa.Date(), nullable=False),
            sa.Column("reporting_currency", sa.String(3), nullable=False),
            sa.Column("cash_balance", sa.Numeric(18, 2), nullable=True),
            sa.Column("pipeline_open", sa.Numeric(18, 2), nullable=True),
            sa.Column("active_investors", sa.Integer(), nullable=True),
            sa.Column("marketing_spend", sa.Numeric(18, 2), nullable=True),
            sa.Column("project_count", sa.Integer(), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("ingestion_run_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.UniqueConstraint("snapshot_date", "reporting_currency", name="uq_wh_mart_exec_day_ccy"),
            schema=SCHEMA,
        )

    if not _has_table("wh_metric_catalog"):
        op.create_table(
            "wh_metric_catalog",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("metric_key", sa.String(80), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("domain", sa.String(40), nullable=False),
            sa.Column("formula", sa.Text(), nullable=False),
            sa.Column("source", sa.Text(), nullable=False),
            sa.Column("grain", sa.String(128), nullable=False),
            sa.Column("certification_status", sa.String(32), nullable=False, server_default="draft"),
            sa.Column("certified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("certified_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("classification", sa.String(32), nullable=False, server_default="internal"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("meta_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("metric_key", name="uq_wh_metric_catalog_key"),
            schema=SCHEMA,
        )

    if not _has_table("wh_dq_check_results"):
        op.create_table(
            "wh_dq_check_results",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("check_key", sa.String(80), nullable=False),
            sa.Column("domain", sa.String(64), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("expected_value", sa.String(128), nullable=True),
            sa.Column("actual_value", sa.String(128), nullable=True),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("ingestion_run_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            schema=SCHEMA,
        )
        op.create_index("ix_wh_dq_check_run", "wh_dq_check_results", ["ingestion_run_id"], schema=SCHEMA)

    if not _has_table("wh_lineage_edges"):
        op.create_table(
            "wh_lineage_edges",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("source_object", sa.String(255), nullable=False),
            sa.Column("target_object", sa.String(255), nullable=False),
            sa.Column("relation", sa.String(64), nullable=False),
            sa.Column("domain", sa.String(64), nullable=True),
            sa.Column("meta_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("source_object", "target_object", "relation", name="uq_wh_lineage_edge"),
            schema=SCHEMA,
        )

    if not _has_table("wh_scheduled_reports"):
        op.create_table(
            "wh_scheduled_reports",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("dataset_key", sa.String(80), nullable=False),
            sa.Column("metric_keys_json", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default="[]"),
            sa.Column("cron_expr", sa.String(64), nullable=False, server_default="0 8 * * 1"),
            sa.Column("format", sa.String(16), nullable=False, server_default="csv"),
            sa.Column("recipients_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            schema=SCHEMA,
        )

    if not _has_table("wh_export_audit"):
        op.create_table(
            "wh_export_audit",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("dataset_key", sa.String(80), nullable=False),
            sa.Column("format", sa.String(16), nullable=False),
            sa.Column("metric_keys_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("row_count", sa.Integer(), nullable=True),
            sa.Column("permission_checked", sa.String(64), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            schema=SCHEMA,
        )
        op.create_index("ix_wh_export_audit_user", "wh_export_audit", ["user_id"], schema=SCHEMA)

    if not _has_table("wh_governed_datasets"):
        op.create_table(
            "wh_governed_datasets",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("dataset_key", sa.String(80), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("mart_table", sa.String(128), nullable=False),
            sa.Column("allowed_columns_json", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default="[]"),
            sa.Column("classification", sa.String(32), nullable=False, server_default="internal"),
            sa.Column("requires_permission", sa.String(64), nullable=False, server_default="analytics:view"),
            sa.Column("certified_metrics_only", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
            sa.UniqueConstraint("dataset_key", name="uq_wh_governed_dataset_key"),
            schema=SCHEMA,
        )

    # Seed currencies + identity FX (no fabricated market rates)
    op.execute(
        text(
            f"""
            INSERT INTO {SCHEMA}.wh_dim_currency (currency_code, name, is_reporting, decimals)
            VALUES
              ('USD', 'US Dollar', true, 2),
              ('TRY', 'Turkish Lira', true, 2),
              ('EUR', 'Euro', false, 2),
              ('GBP', 'British Pound', false, 2),
              ('AED', 'UAE Dirham', false, 2)
            ON CONFLICT (currency_code) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    # Non-destructive by default in ops; downgrade drops analytics objects only.
    for table in (
        "wh_governed_datasets",
        "wh_export_audit",
        "wh_scheduled_reports",
        "wh_lineage_edges",
        "wh_dq_check_results",
        "wh_metric_catalog",
        "wh_mart_executive_daily",
        "wh_fact_marketing_spend",
        "wh_fact_investor_activity",
        "wh_fact_pipeline",
        "wh_fact_cash_movement",
        "wh_status_history",
        "wh_dim_campaign",
        "wh_dim_investor",
        "wh_dim_project",
        "wh_dim_currency",
        "wh_dim_date",
        "wh_fx_rates",
        "wh_ingestion_runs",
    ):
        if _has_table(table):
            op.drop_table(table, schema=SCHEMA)
    if _schema_exists():
        op.execute(text(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE"))
