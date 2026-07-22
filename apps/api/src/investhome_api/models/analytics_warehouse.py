"""G14 analytics warehouse models — isolated Postgres schema `analytics`.

OLTP tables remain transactional truth. BI reads marts/metrics here only for
certified reporting paths. No BI write path into public transactional tables.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from investhome_api.db.base import Base

ANALYTICS_SCHEMA = "analytics"


class IngestionStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"


class IngestionMode(str, enum.Enum):
    INCREMENTAL = "incremental"
    FULL_REFRESH = "full_refresh"


class MetricCertStatus(str, enum.Enum):
    DRAFT = "draft"
    CERTIFIED = "certified"
    DEPRECATED = "deprecated"


class DataClassification(str, enum.Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class WhIngestionRun(Base):
    """Observable ingestion job tracking — Pending → Running → Succeeded|Partial|Failed."""

    __tablename__ = "wh_ingestion_runs"
    __table_args__ = (
        Index("ix_wh_ingestion_runs_domain_status", "domain", "status"),
        Index("ix_wh_ingestion_runs_started", "started_at"),
        {"schema": ANALYTICS_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    domain: Mapped[str] = mapped_column(String(64), nullable=False)
    job_name: Mapped[str] = mapped_column(String(128), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False, server_default="incremental")
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")
    watermark_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    watermark_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rows_read: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    rows_written: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    rows_rejected: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    reject_reasons_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    meta_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class WhFxRate(Base):
    """Dated FX rates. Original amounts are never overwritten by conversion."""

    __tablename__ = "wh_fx_rates"
    __table_args__ = (
        UniqueConstraint("rate_date", "from_currency", "to_currency", name="uq_wh_fx_rates_day_pair"),
        {"schema": ANALYTICS_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    rate_date: Mapped[date] = mapped_column(Date, nullable=False)
    from_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    to_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False, server_default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WhDimDate(Base):
    __tablename__ = "wh_dim_date"
    __table_args__ = ({"schema": ANALYTICS_SCHEMA},)

    date_key: Mapped[int] = mapped_column(Integer, primary_key=True)  # YYYYMMDD
    full_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    quarter: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    week: Mapped[int] = mapped_column(Integer, nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    is_month_end: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")


class WhDimCurrency(Base):
    __tablename__ = "wh_dim_currency"
    __table_args__ = ({"schema": ANALYTICS_SCHEMA},)

    currency_code: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    is_reporting: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    decimals: Mapped[int] = mapped_column(Integer, nullable=False, server_default="2")


class WhDimProject(Base):
    """Conformed project dimension — SCD1 for MVP; status history via events table."""

    __tablename__ = "wh_dim_project"
    __table_args__ = (
        Index("ix_wh_dim_project_source", "source_project_id"),
        {"schema": ANALYTICS_SCHEMA},
    )

    project_sk: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    source_project_id: Mapped[uuid.UUID] = mapped_column(Uuid(), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    project_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    classification: Mapped[str] = mapped_column(String(32), nullable=False, server_default="internal")
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)


class WhDimInvestor(Base):
    __tablename__ = "wh_dim_investor"
    __table_args__ = (
        Index("ix_wh_dim_investor_source", "source_investor_id"),
        {"schema": ANALYTICS_SCHEMA},
    )

    investor_sk: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    source_investor_id: Mapped[uuid.UUID] = mapped_column(Uuid(), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    classification: Mapped[str] = mapped_column(String(32), nullable=False, server_default="confidential")
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)


class WhDimCampaign(Base):
    __tablename__ = "wh_dim_campaign"
    __table_args__ = ({"schema": ANALYTICS_SCHEMA},)

    campaign_sk: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    source_campaign_id: Mapped[uuid.UUID] = mapped_column(Uuid(), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    channel: Mapped[str | None] = mapped_column(String(64), nullable=True)
    classification: Mapped[str] = mapped_column(String(32), nullable=False, server_default="internal")
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)


class WhStatusHistory(Base):
    """Generic stage/status change history (event-style SCD)."""

    __tablename__ = "wh_status_history"
    __table_args__ = (
        Index("ix_wh_status_history_entity", "entity_type", "source_entity_id"),
        {"schema": ANALYTICS_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_entity_id: Mapped[uuid.UUID] = mapped_column(Uuid(), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    to_status: Mapped[str] = mapped_column(String(64), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    meta_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class WhFactCashMovement(Base):
    """Grain: one posted finance transaction (cash movement)."""

    __tablename__ = "wh_fact_cash_movement"
    __table_args__ = (
        UniqueConstraint("source_transaction_id", name="uq_wh_fact_cash_source_txn"),
        Index("ix_wh_fact_cash_date", "date_key"),
        {"schema": ANALYTICS_SCHEMA},
    )

    cash_sk: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    source_transaction_id: Mapped[uuid.UUID] = mapped_column(Uuid(), nullable=False)
    date_key: Mapped[int] = mapped_column(Integer, nullable=False)
    project_sk: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    account_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    txn_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # Original — never overwritten
    amount_original: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency_original: Mapped[str] = mapped_column(String(3), nullable=False)
    # Reporting conversions (nullable if FX missing)
    amount_usd: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    amount_try: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    fx_rate_usd: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    fx_rate_try: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)


class WhFactPipeline(Base):
    """Grain: one sales opportunity snapshot per ingestion (current open/closed state)."""

    __tablename__ = "wh_fact_pipeline"
    __table_args__ = (
        UniqueConstraint("source_opportunity_id", "snapshot_date", name="uq_wh_fact_pipeline_snap"),
        Index("ix_wh_fact_pipeline_date", "snapshot_date"),
        {"schema": ANALYTICS_SCHEMA},
    )

    pipeline_sk: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    source_opportunity_id: Mapped[uuid.UUID] = mapped_column(Uuid(), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    date_key: Mapped[int] = mapped_column(Integer, nullable=False)
    project_sk: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    investor_sk: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    is_open: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    expected_revenue_original: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency_original: Mapped[str | None] = mapped_column(String(3), nullable=True)
    expected_revenue_usd: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    expected_revenue_try: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    probability: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)


class WhFactInvestorActivity(Base):
    """Grain: one investor × day activity/commitment snapshot."""

    __tablename__ = "wh_fact_investor_activity"
    __table_args__ = (
        UniqueConstraint("source_investor_id", "snapshot_date", name="uq_wh_fact_inv_act_snap"),
        {"schema": ANALYTICS_SCHEMA},
    )

    activity_sk: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    source_investor_id: Mapped[uuid.UUID] = mapped_column(Uuid(), nullable=False)
    investor_sk: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    commitment_original: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency_original: Mapped[str | None] = mapped_column(String(3), nullable=True)
    commitment_usd: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    commitment_try: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)


class WhFactMarketingSpend(Base):
    """Grain: campaign spend row (or daily aggregate when source is daily)."""

    __tablename__ = "wh_fact_marketing_spend"
    __table_args__ = (
        UniqueConstraint(
            "source_row_id",
            name="uq_wh_fact_mkt_spend_source",
        ),
        {"schema": ANALYTICS_SCHEMA},
    )

    spend_sk: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    source_row_id: Mapped[str] = mapped_column(String(128), nullable=False)
    campaign_sk: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    date_key: Mapped[int] = mapped_column(Integer, nullable=False)
    spend_original: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency_original: Mapped[str] = mapped_column(String(3), nullable=False)
    spend_usd: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    spend_try: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    attributed_value_original: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)


class WhMartExecutiveDaily(Base):
    """Business mart — executive KPIs by day (certified subset)."""

    __tablename__ = "wh_mart_executive_daily"
    __table_args__ = (
        UniqueConstraint("snapshot_date", "reporting_currency", name="uq_wh_mart_exec_day_ccy"),
        {"schema": ANALYTICS_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    reporting_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    cash_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    pipeline_open: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    active_investors: Mapped[int | None] = mapped_column(Integer, nullable=True)
    marketing_spend: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    project_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)


class WhMetricCatalogEntry(Base):
    """Persisted catalog mirror of registry with certification audit trail."""

    __tablename__ = "wh_metric_catalog"
    __table_args__ = (
        UniqueConstraint("metric_key", name="uq_wh_metric_catalog_key"),
        {"schema": ANALYTICS_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    metric_key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(40), nullable=False)
    formula: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    grain: Mapped[str] = mapped_column(String(128), nullable=False)
    certification_status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="draft")
    certified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    certified_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    classification: Mapped[str] = mapped_column(String(32), nullable=False, server_default="internal")
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    meta_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class WhDqCheckResult(Base):
    __tablename__ = "wh_dq_check_results"
    __table_args__ = (
        Index("ix_wh_dq_check_run", "ingestion_run_id"),
        {"schema": ANALYTICS_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    check_key: Mapped[str] = mapped_column(String(80), nullable=False)
    domain: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # pass|warn|fail
    expected_value: Mapped[str | None] = mapped_column(String(128), nullable=True)
    actual_value: Mapped[str | None] = mapped_column(String(128), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WhLineageEdge(Base):
    __tablename__ = "wh_lineage_edges"
    __table_args__ = (
        UniqueConstraint(
            "source_object",
            "target_object",
            "relation",
            name="uq_wh_lineage_edge",
        ),
        {"schema": ANALYTICS_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    source_object: Mapped[str] = mapped_column(String(255), nullable=False)
    target_object: Mapped[str] = mapped_column(String(255), nullable=False)
    relation: Mapped[str] = mapped_column(String(64), nullable=False)  # extracts|transforms|feeds
    domain: Mapped[str | None] = mapped_column(String(64), nullable=True)
    meta_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WhScheduledReport(Base):
    __tablename__ = "wh_scheduled_reports"
    __table_args__ = ({"schema": ANALYTICS_SCHEMA},)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dataset_key: Mapped[str] = mapped_column(String(80), nullable=False)
    metric_keys_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    cron_expr: Mapped[str] = mapped_column(String(64), nullable=False, server_default="0 8 * * 1")
    format: Mapped[str] = mapped_column(String(16), nullable=False, server_default="csv")
    recipients_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WhExportAudit(Base):
    """Permission-logged exports — who exported what, when."""

    __tablename__ = "wh_export_audit"
    __table_args__ = (
        Index("ix_wh_export_audit_user", "user_id"),
        {"schema": ANALYTICS_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(), nullable=False)
    dataset_key: Mapped[str] = mapped_column(String(80), nullable=False)
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    metric_keys_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    permission_checked: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WhGovernedDataset(Base):
    """Explorer / report builder may only query these datasets."""

    __tablename__ = "wh_governed_datasets"
    __table_args__ = (
        UniqueConstraint("dataset_key", name="uq_wh_governed_dataset_key"),
        {"schema": ANALYTICS_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    dataset_key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    mart_table: Mapped[str] = mapped_column(String(128), nullable=False)
    allowed_columns_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    classification: Mapped[str] = mapped_column(String(32), nullable=False, server_default="internal")
    requires_permission: Mapped[str] = mapped_column(String(64), nullable=False, server_default="analytics:view")
    certified_metrics_only: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
