"""Schemas for Business Intelligence aggregation API (P9)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


ChartType = Literal["line", "bar", "area", "donut", "funnel", "kpi", "table"]
AttributionLabel = Literal["first", "last", "multi", "unattributed"]
MetricState = Literal["ready", "empty", "unavailable", "permission"]


class BiFilters(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    comparison: Literal["previous_period", "none"] = "previous_period"
    workspace: str | None = None
    project_id: UUID | None = None
    assigned_to: str | None = None
    lead_source: str | None = None
    investor_id: UUID | None = None
    campaign_id: UUID | None = None
    currency: str | None = None
    status: str | None = None
    preset: str | None = None


class MetricComparisonOut(BaseModel):
    previous: float | int | str | None = None
    change_pct: float | None = None
    change_available: bool = False
    reason: str | None = None


class BiMetricValue(BaseModel):
    key: str
    name: str
    value: float | int | str | None = None
    state: MetricState = "unavailable"
    unit: str | None = None
    currency: str | None = None
    reason: str | None = None
    definition: str | None = None
    source: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    comparison: MetricComparisonOut | None = None
    freshness_at: datetime | None = None
    freshness_seconds: int | None = None
    drilldown_path: str | None = None
    attribution: AttributionLabel | None = None


class MetricDefinitionOut(BaseModel):
    key: str
    name: str
    description: str
    formula: str
    source: str
    domain: str
    unit: str
    currency_aware: bool
    permission: str
    supports_comparison: bool
    freshness_seconds: int
    drilldown_path: str
    filters: list[str]
    certification_status: str = "draft"
    grain: str = "see formula"
    reporting_timezone: str = "UTC"


class BiOverviewResponse(BaseModel):
    generated_at: datetime
    filters: BiFilters
    metrics: list[BiMetricValue]
    attention_count: int = 0
    missing_sources: list[str] = Field(default_factory=list)


class BiDomainSeriesPoint(BaseModel):
    label: str
    value: float | int | None = None
    state: MetricState = "ready"


class BiDomainSection(BaseModel):
    key: str
    title: str
    metrics: list[BiMetricValue] = Field(default_factory=list)
    series: list[BiDomainSeriesPoint] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    attribution_breakdown: dict[str, int] | None = None
    notes: list[str] = Field(default_factory=list)


class BiDomainResponse(BaseModel):
    domain: str
    generated_at: datetime
    filters: BiFilters
    sections: list[BiDomainSection]
    missing_sources: list[str] = Field(default_factory=list)


class DataQualityFinding(BaseModel):
    key: str
    severity: Literal["info", "warning", "critical"]
    title: str
    description: str
    source: str
    metric_keys: list[str] = Field(default_factory=list)


class DataQualityResponse(BaseModel):
    generated_at: datetime
    findings: list[DataQualityFinding]
    freshness: dict[str, datetime | None] = Field(default_factory=dict)


class BiSavedReportCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    domain: str = "executive"
    chart_type: ChartType = "kpi"
    metric_keys: list[str] = Field(min_length=1)
    filters: dict[str, Any] | None = None
    layout: dict[str, Any] | None = None
    is_shared: bool = False


class BiSavedReportUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    domain: str | None = None
    chart_type: ChartType | None = None
    metric_keys: list[str] | None = None
    filters: dict[str, Any] | None = None
    layout: dict[str, Any] | None = None
    is_shared: bool | None = None


class BiSavedReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_user_id: UUID
    name: str
    description: str | None
    domain: str
    chart_type: str
    metric_keys: list[str]
    filters: dict[str, Any] | None = None
    layout: dict[str, Any] | None = None
    is_shared: bool
    created_at: datetime
    updated_at: datetime


class BiAlertThresholdCreate(BaseModel):
    metric_key: str
    name: str = Field(min_length=1, max_length=255)
    operator: Literal["gt", "gte", "lt", "lte", "eq"]
    threshold_value: str
    severity: Literal["information", "warning", "critical"] = "warning"
    enabled: bool = True
    filters: dict[str, Any] | None = None


class BiAlertThresholdOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    metric_key: str
    name: str
    operator: str
    threshold_value: str
    severity: str
    enabled: bool
    filters: dict[str, Any] | None = None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


class BiExportRequest(BaseModel):
    format: Literal["csv", "xlsx", "pdf", "print"] = "csv"
    domain: str = "executive"
    metric_keys: list[str] = Field(default_factory=list)
    filters: BiFilters | None = None
