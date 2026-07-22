"""Schemas for G14 analytics warehouse / data platform API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IngestionRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    domain: str
    job_name: str
    mode: str
    status: str
    watermark_from: datetime | None = None
    watermark_to: datetime | None = None
    rows_read: int = 0
    rows_written: int = 0
    rows_rejected: int = 0
    reject_reasons_json: list[Any] | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None


class IngestionTriggerRequest(BaseModel):
    mode: Literal["incremental", "full_refresh"] = "incremental"
    domains: list[str] | None = None


class MetricCatalogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    metric_key: str
    name: str
    domain: str
    formula: str
    source: str
    grain: str
    certification_status: str
    certified_at: datetime | None = None
    classification: str
    version: int = 1


class LineageEdgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_object: str
    target_object: str
    relation: str
    domain: str | None = None
    meta_json: dict[str, Any] | None = None


class DqCheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    check_key: str
    domain: str
    status: str
    expected_value: str | None = None
    actual_value: str | None = None
    message: str
    checked_at: datetime | None = None


class GovernedDatasetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_key: str
    name: str
    description: str | None = None
    mart_table: str
    allowed_columns_json: list[Any] = Field(default_factory=list)
    classification: str
    requires_permission: str
    certified_metrics_only: bool = True


class PlatformOverviewOut(BaseModel):
    schema_name: str
    isolation: str
    oltp_queries_replaced: bool
    reporting_timezones: list[str]
    supported_currencies: list[str]
    reporting_currencies: list[str]
    last_run: dict[str, Any]
    ingestion_counts: dict[str, int]
    metric_catalog: dict[str, int]
    row_counts: dict[str, int]
    cost_estimate_monthly_usd: dict[str, Any]


class ReconResponse(BaseModel):
    certified_keys: list[str]
    checked_at: str
    summary: dict[str, int]
    checks: list[dict[str, Any]]
    overall: str


class ExploreResponse(BaseModel):
    dataset_key: str | None = None
    mart_table: str | None = None
    classification: str | None = None
    allowed_columns: list[str] = Field(default_factory=list)
    row_count: int = 0
    rows: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class ScheduledReportCreate(BaseModel):
    name: str
    dataset_key: str
    metric_keys: list[str] = Field(default_factory=list)
    cron_expr: str = "0 8 * * 1"
    format: Literal["csv"] = "csv"
    recipients: list[str] | None = None
    enabled: bool = True


class ScheduledReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    dataset_key: str
    metric_keys_json: list[Any] = Field(default_factory=list)
    cron_expr: str
    format: str
    recipients_json: list[Any] | None = None
    enabled: bool
    last_run_at: datetime | None = None
    created_at: datetime | None = None
