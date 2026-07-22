"""Sync metric catalog + governed datasets + lineage seeds for G14."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.config.analytics_metric_registry import METRIC_REGISTRY, list_metrics
from investhome_api.models.analytics_warehouse import (
    MetricCertStatus,
    WhGovernedDataset,
    WhLineageEdge,
    WhMetricCatalogEntry,
)

# Certified subset for G14 MVP — frozen definitions; no silent redefinition.
CERTIFIED_KEYS = frozenset(
    {
        "cash",
        "pipeline",
        "closed_sales",
        "active_investors",
        "marketing_spend",
        "project_exposure",
        "lead_volume",
        "receivables",
    }
)

METRIC_GRAIN = {
    "cash": "financial_account (current available_balance sum)",
    "pipeline": "sales_opportunity open snapshot / day",
    "closed_sales": "sales_opportunity won / period",
    "active_investors": "investor current status snapshot / day",
    "marketing_spend": "campaign budget/spend row",
    "project_exposure": "active project funding gap aggregate",
    "lead_volume": "lead created / period",
    "receivables": "open inbound payment_obligation",
    "revenue": "posted income finance_transaction / period",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def sync_metric_catalog_and_lineage(db: Session) -> int:
    written = 0
    for metric in list_metrics():
        status = (
            MetricCertStatus.CERTIFIED.value
            if metric.key in CERTIFIED_KEYS
            else MetricCertStatus.DRAFT.value
        )
        grain = METRIC_GRAIN.get(metric.key, "see formula")
        existing = db.scalar(
            select(WhMetricCatalogEntry).where(WhMetricCatalogEntry.metric_key == metric.key)
        )
        if existing:
            # Do not silently change certified formula/source
            if existing.certification_status != MetricCertStatus.CERTIFIED.value:
                existing.name = metric.name
                existing.formula = metric.formula
                existing.source = metric.source
                existing.domain = metric.domain
                existing.grain = grain
            existing.certification_status = status
            if status == MetricCertStatus.CERTIFIED.value and existing.certified_at is None:
                existing.certified_at = _utcnow()
            existing.updated_at = _utcnow()
        else:
            db.add(
                WhMetricCatalogEntry(
                    metric_key=metric.key,
                    name=metric.name,
                    domain=metric.domain,
                    formula=metric.formula,
                    source=metric.source,
                    grain=grain,
                    certification_status=status,
                    certified_at=_utcnow() if status == MetricCertStatus.CERTIFIED.value else None,
                    classification="confidential" if metric.domain in {"investor", "finance"} else "internal",
                )
            )
        written += 1

    # Governed datasets for explorer / report builder
    datasets = [
        {
            "dataset_key": "executive_daily",
            "name": "Executive daily mart",
            "description": "Certified executive KPIs by day (USD/TRY reporting).",
            "mart_table": "analytics.wh_mart_executive_daily",
            "allowed_columns_json": [
                "snapshot_date",
                "reporting_currency",
                "cash_balance",
                "pipeline_open",
                "active_investors",
                "marketing_spend",
                "project_count",
            ],
            "classification": "internal",
            "requires_permission": "analytics:view",
        },
        {
            "dataset_key": "cash_movements",
            "name": "Cash movements fact",
            "description": "Finance transactions materialized with original + reporting currencies.",
            "mart_table": "analytics.wh_fact_cash_movement",
            "allowed_columns_json": [
                "date_key",
                "txn_type",
                "amount_original",
                "currency_original",
                "amount_usd",
                "amount_try",
                "status",
            ],
            "classification": "confidential",
            "requires_permission": "finance:view",
        },
        {
            "dataset_key": "pipeline_snapshot",
            "name": "Sales pipeline snapshot",
            "description": "Daily opportunity pipeline snapshots.",
            "mart_table": "analytics.wh_fact_pipeline",
            "allowed_columns_json": [
                "snapshot_date",
                "stage",
                "is_open",
                "expected_revenue_original",
                "currency_original",
                "expected_revenue_usd",
                "expected_revenue_try",
            ],
            "classification": "internal",
            "requires_permission": "sales:view",
        },
    ]
    for ds in datasets:
        existing = db.scalar(
            select(WhGovernedDataset).where(WhGovernedDataset.dataset_key == ds["dataset_key"])
        )
        if existing:
            existing.name = ds["name"]
            existing.description = ds["description"]
            existing.mart_table = ds["mart_table"]
            existing.allowed_columns_json = ds["allowed_columns_json"]
            existing.classification = ds["classification"]
            existing.requires_permission = ds["requires_permission"]
        else:
            db.add(WhGovernedDataset(**ds, certified_metrics_only=True, enabled=True))
        written += 1

    # Registry → warehouse lineage for certified metrics
    for key in CERTIFIED_KEYS:
        m = METRIC_REGISTRY.get(key)
        if not m:
            continue
        src = f"registry.{key}"
        tgt = "analytics.wh_metric_catalog"
        edge = db.scalar(
            select(WhLineageEdge).where(
                WhLineageEdge.source_object == src,
                WhLineageEdge.target_object == tgt,
                WhLineageEdge.relation == "defines",
            )
        )
        if not edge:
            db.add(
                WhLineageEdge(
                    source_object=src,
                    target_object=tgt,
                    relation="defines",
                    domain=m.domain,
                    meta_json={"certification": "certified"},
                )
            )
            written += 1

    db.flush()
    return written
