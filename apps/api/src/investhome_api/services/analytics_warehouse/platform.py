"""Data platform admin — overview, DQ, lineage, recon, catalog."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.analytics_warehouse import (
    WhDimInvestor,
    WhDimProject,
    WhDqCheckResult,
    WhExportAudit,
    WhFactCashMovement,
    WhFactInvestorActivity,
    WhFactPipeline,
    WhGovernedDataset,
    WhIngestionRun,
    WhLineageEdge,
    WhMartExecutiveDaily,
    WhMetricCatalogEntry,
)
from investhome_api.models.finance import AccountStatus, FinancialAccount, FinanceTransaction
from investhome_api.models.investor import Investor
from investhome_api.models.project import Project
from investhome_api.services.analytics_warehouse.seed_catalog import CERTIFIED_KEYS


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def list_ingestion_runs(db: Session, *, limit: int = 50) -> list[WhIngestionRun]:
    return list(
        db.scalars(
            select(WhIngestionRun).order_by(WhIngestionRun.created_at.desc()).limit(limit)
        ).all()
    )


def list_metric_catalog(
    db: Session, *, certification: str | None = None
) -> list[WhMetricCatalogEntry]:
    q = select(WhMetricCatalogEntry).order_by(WhMetricCatalogEntry.domain, WhMetricCatalogEntry.metric_key)
    if certification:
        q = q.where(WhMetricCatalogEntry.certification_status == certification)
    return list(db.scalars(q).all())


def list_lineage(db: Session) -> list[WhLineageEdge]:
    return list(db.scalars(select(WhLineageEdge).order_by(WhLineageEdge.source_object)).all())


def list_governed_datasets(db: Session) -> list[WhGovernedDataset]:
    return list(
        db.scalars(select(WhGovernedDataset).where(WhGovernedDataset.enabled.is_(True))).all()
    )


def get_platform_overview(db: Session) -> dict[str, Any]:
    last_run = db.scalar(
        select(WhIngestionRun).order_by(WhIngestionRun.created_at.desc()).limit(1)
    )
    succeeded = db.scalar(
        select(func.count()).select_from(WhIngestionRun).where(WhIngestionRun.status == "succeeded")
    ) or 0
    failed = db.scalar(
        select(func.count()).select_from(WhIngestionRun).where(WhIngestionRun.status == "failed")
    ) or 0
    certified = db.scalar(
        select(func.count())
        .select_from(WhMetricCatalogEntry)
        .where(WhMetricCatalogEntry.certification_status == "certified")
    ) or 0
    draft = db.scalar(
        select(func.count())
        .select_from(WhMetricCatalogEntry)
        .where(WhMetricCatalogEntry.certification_status == "draft")
    ) or 0
    fact_cash = db.scalar(select(func.count()).select_from(WhFactCashMovement)) or 0
    fact_pipe = db.scalar(select(func.count()).select_from(WhFactPipeline)) or 0
    dims_proj = db.scalar(select(func.count()).select_from(WhDimProject)) or 0
    dims_inv = db.scalar(select(func.count()).select_from(WhDimInvestor)) or 0
    lineage = db.scalar(select(func.count()).select_from(WhLineageEdge)) or 0
    exports = db.scalar(select(func.count()).select_from(WhExportAudit)) or 0

    return {
        "schema": "analytics",
        "isolation": "postgres_schema",
        "oltp_queries_replaced": False,
        "reporting_timezones": ["UTC", "Europe/Istanbul"],
        "supported_currencies": ["USD", "TRY", "EUR", "GBP", "AED"],
        "reporting_currencies": ["USD", "TRY"],
        "last_run": {
            "id": str(last_run.id) if last_run else None,
            "status": last_run.status if last_run else None,
            "mode": last_run.mode if last_run else None,
            "started_at": last_run.started_at.isoformat() if last_run and last_run.started_at else None,
            "finished_at": last_run.finished_at.isoformat() if last_run and last_run.finished_at else None,
            "rows_written": last_run.rows_written if last_run else 0,
            "rows_rejected": last_run.rows_rejected if last_run else 0,
            "error_message": last_run.error_message if last_run else None,
        },
        "ingestion_counts": {"succeeded": succeeded, "failed": failed},
        "metric_catalog": {"certified": certified, "draft": draft},
        "row_counts": {
            "wh_fact_cash_movement": fact_cash,
            "wh_fact_pipeline": fact_pipe,
            "wh_dim_project": dims_proj,
            "wh_dim_investor": dims_inv,
            "wh_lineage_edges": lineage,
            "wh_export_audit": exports,
        },
        "cost_estimate_monthly_usd": {
            "postgres_extra_storage_gb": 2,
            "worker_cpu_minutes": 120,
            "estimated_infra_usd": 15,
            "notes": "Same Postgres cluster; no Snowflake. Cost is incremental storage + ARQ cron.",
        },
    }


def run_dq_suite(db: Session, *, ingestion_run_id: UUID | None = None) -> list[WhDqCheckResult]:
    results: list[WhDqCheckResult] = []
    today = date.today()

    def add(check_key: str, domain: str, status: str, message: str, expected: str | None = None, actual: str | None = None) -> None:
        row = WhDqCheckResult(
            check_key=check_key,
            domain=domain,
            status=status,
            expected_value=expected,
            actual_value=actual,
            message=message,
            ingestion_run_id=ingestion_run_id,
            checked_at=_utcnow(),
        )
        db.add(row)
        results.append(row)

    # Unique source keys on cash facts
    cash_total = db.scalar(select(func.count()).select_from(WhFactCashMovement)) or 0
    cash_distinct = db.scalar(
        select(func.count(func.distinct(WhFactCashMovement.source_transaction_id)))
    ) or 0
    add(
        "cash_no_duplicate_source",
        "finance",
        "pass" if cash_total == cash_distinct else "fail",
        "Cash fact source_transaction_id must be unique",
        expected=str(cash_total),
        actual=str(cash_distinct),
    )

    # Pipeline snapshot uniqueness for today
    pipe_total = db.scalar(
        select(func.count()).select_from(WhFactPipeline).where(WhFactPipeline.snapshot_date == today)
    ) or 0
    pipe_distinct = db.scalar(
        select(func.count(func.distinct(WhFactPipeline.source_opportunity_id))).where(
            WhFactPipeline.snapshot_date == today
        )
    ) or 0
    add(
        "pipeline_no_duplicate_snapshot",
        "sales",
        "pass" if pipe_total == pipe_distinct else "fail",
        "Pipeline snapshot unique per opportunity per day",
        expected=str(pipe_total),
        actual=str(pipe_distinct),
    )

    # Original currency preserved (non-null)
    missing_ccy = db.scalar(
        select(func.count())
        .select_from(WhFactCashMovement)
        .where(
            (WhFactCashMovement.currency_original.is_(None))
            | (WhFactCashMovement.currency_original == "")
        )
    ) or 0
    add(
        "cash_original_currency_present",
        "finance",
        "pass" if missing_ccy == 0 else "fail",
        "Original currency must never be blank",
        expected="0",
        actual=str(missing_ccy),
    )

    # Dim projects vs OLTP count (warn if warehouse empty while OLTP has rows)
    oltp_projects = db.scalar(select(func.count()).select_from(Project)) or 0
    wh_projects = db.scalar(select(func.count()).select_from(WhDimProject)) or 0
    status = "pass"
    if oltp_projects > 0 and wh_projects == 0:
        status = "fail"
    elif oltp_projects != wh_projects:
        status = "warn"
    add(
        "projects_dim_coverage",
        "projects",
        status,
        "Project dimension coverage vs OLTP",
        expected=str(oltp_projects),
        actual=str(wh_projects),
    )

    db.flush()
    return results


def list_dq_results(db: Session, *, limit: int = 100) -> list[WhDqCheckResult]:
    return list(
        db.scalars(
            select(WhDqCheckResult).order_by(WhDqCheckResult.checked_at.desc()).limit(limit)
        ).all()
    )


def reconcile_certified_subset(db: Session) -> dict[str, Any]:
    """Reconcile certified warehouse aggregates against OLTP for the certified subset."""
    today = date.today()
    checks: list[dict[str, Any]] = []

    # Cash: sum of available_balance (OLTP) vs mart cash_balance USD when identity FX
    oltp_cash = Decimal("0")
    for acct in db.scalars(
        select(FinancialAccount).where(FinancialAccount.status == AccountStatus.ACTIVE)
    ).all():
        bal = getattr(acct, "available_balance", None) or getattr(acct, "current_balance", None) or 0
        ccy = (acct.currency or "USD").upper()
        if ccy == "USD":
            oltp_cash += Decimal(str(bal))

    mart = db.scalar(
        select(WhMartExecutiveDaily).where(
            WhMartExecutiveDaily.snapshot_date == today,
            WhMartExecutiveDaily.reporting_currency == "USD",
        )
    )
    mart_cash = Decimal(str(mart.cash_balance)) if mart and mart.cash_balance is not None else None
    cash_ok = mart_cash is not None and abs(mart_cash - oltp_cash) <= Decimal("0.01")
    checks.append(
        {
            "metric_key": "cash",
            "domain": "finance",
            "oltp_value": float(oltp_cash),
            "warehouse_value": float(mart_cash) if mart_cash is not None else None,
            "status": "pass" if cash_ok else ("blocked" if mart is None else "fail"),
            "note": "USD accounts only for identity FX recon; cross-ccy needs dated market FX",
        }
    )

    # Active investors — Python filter for enum portability
    active_statuses = {
        "active",
        "portfolio",
        "invested",
        "rental",
        "construction",
        "closing",
        "wire_received",
        "contract",
        "payment_pending",
    }
    oltp_active = 0
    for inv in db.scalars(select(Investor).where(Investor.archived_at.is_(None))).all():
        st = getattr(inv.status, "value", inv.status)
        if str(st).lower() in active_statuses:
            oltp_active += 1

    wh_active = db.scalar(
        select(func.count())
        .select_from(WhFactInvestorActivity)
        .where(
            WhFactInvestorActivity.snapshot_date == today,
            WhFactInvestorActivity.is_active.is_(True),
        )
    ) or 0
    checks.append(
        {
            "metric_key": "active_investors",
            "domain": "investors",
            "oltp_value": int(oltp_active),
            "warehouse_value": int(wh_active),
            "status": "pass" if int(oltp_active) == int(wh_active) else ("blocked" if wh_active == 0 and oltp_active > 0 else "fail"),
            "note": "Status-based active definition aligned with ingestion",
        }
    )

    # Projects dim count
    oltp_proj = db.scalar(select(func.count()).select_from(Project)) or 0
    wh_proj = db.scalar(select(func.count()).select_from(WhDimProject)) or 0
    checks.append(
        {
            "metric_key": "project_exposure",
            "domain": "projects",
            "oltp_value": int(oltp_proj),
            "warehouse_value": int(wh_proj),
            "status": "pass" if oltp_proj == wh_proj else ("blocked" if wh_proj == 0 else "warn"),
            "note": "Dimension coverage recon (exposure amount PARTIAL — funding gap formula domain-owned)",
        }
    )

    # Pipeline open count vs open facts
    try:
        from investhome_api.models.sales import SalesOpportunity

        oltp_open = 0
        closed = {"won", "lost", "dormant", "cancelled", "closed_won", "closed_lost"}
        for opp in db.scalars(select(SalesOpportunity).where(SalesOpportunity.archived_at.is_(None))).all():
            stage = str(getattr(opp.stage, "value", opp.stage)).lower()
            if stage not in closed:
                oltp_open += 1
        wh_open = db.scalar(
            select(func.count())
            .select_from(WhFactPipeline)
            .where(WhFactPipeline.snapshot_date == today, WhFactPipeline.is_open.is_(True))
        ) or 0
        checks.append(
            {
                "metric_key": "pipeline",
                "domain": "sales",
                "oltp_value": oltp_open,
                "warehouse_value": int(wh_open),
                "status": "pass" if oltp_open == wh_open else ("blocked" if wh_open == 0 and oltp_open > 0 else "fail"),
                "note": "Open opportunity count recon",
            }
        )
    except Exception as exc:  # noqa: BLE001
        checks.append(
            {
                "metric_key": "pipeline",
                "domain": "sales",
                "oltp_value": None,
                "warehouse_value": None,
                "status": "blocked",
                "note": f"sales model unavailable: {exc}",
            }
        )

    # Marketing: campaign count coverage (spend amounts may be budget proxies — PARTIAL)
    try:
        from investhome_api.models.marketing import MarketingCampaign

        oltp_mkt = db.scalar(
            select(func.count()).select_from(MarketingCampaign).where(MarketingCampaign.archived_at.is_(None))
        ) or 0
        from investhome_api.models.analytics_warehouse import WhDimCampaign

        wh_mkt = db.scalar(select(func.count()).select_from(WhDimCampaign)) or 0
        checks.append(
            {
                "metric_key": "marketing_spend",
                "domain": "marketing",
                "oltp_value": int(oltp_mkt),
                "warehouse_value": int(wh_mkt),
                "status": "pass" if oltp_mkt == wh_mkt else ("warn" if wh_mkt > 0 else "blocked"),
                "note": "Campaign dim coverage; spend uses budget_amount when actual spend absent (PARTIAL)",
            }
        )
    except Exception as exc:  # noqa: BLE001
        checks.append(
            {
                "metric_key": "marketing_spend",
                "domain": "marketing",
                "oltp_value": None,
                "warehouse_value": None,
                "status": "blocked",
                "note": str(exc),
            }
        )

    # Transaction count vs cash facts (full refresh expectation)
    oltp_txn = db.scalar(select(func.count()).select_from(FinanceTransaction)) or 0
    wh_txn = db.scalar(select(func.count()).select_from(WhFactCashMovement)) or 0
    checks.append(
        {
            "metric_key": "cash_movements",
            "domain": "finance",
            "oltp_value": int(oltp_txn),
            "warehouse_value": int(wh_txn),
            "status": "pass" if oltp_txn == wh_txn else ("blocked" if wh_txn == 0 else "warn"),
            "note": "Fact row count vs OLTP transactions",
        }
    )

    passed = sum(1 for c in checks if c["status"] == "pass")
    failed = sum(1 for c in checks if c["status"] == "fail")
    blocked = sum(1 for c in checks if c["status"] == "blocked")
    warn = sum(1 for c in checks if c["status"] == "warn")

    return {
        "certified_keys": sorted(CERTIFIED_KEYS),
        "checked_at": _utcnow().isoformat(),
        "summary": {"pass": passed, "fail": failed, "warn": warn, "blocked": blocked},
        "checks": checks,
        "overall": "pass" if failed == 0 and blocked == 0 else ("revision_required" if failed or blocked else "pass"),
    }


def log_export_audit(
    db: Session,
    *,
    user_id: UUID,
    dataset_key: str,
    fmt: str,
    metric_keys: list[str] | None,
    row_count: int | None,
    permission_checked: str,
) -> WhExportAudit:
    row = WhExportAudit(
        user_id=user_id,
        dataset_key=dataset_key,
        format=fmt,
        metric_keys_json=metric_keys,
        row_count=row_count,
        permission_checked=permission_checked,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def explore_dataset(
    db: Session,
    *,
    dataset_key: str,
    limit: int = 100,
) -> dict[str, Any]:
    """Governed explorer — only whitelisted datasets/columns; no arbitrary SQL."""
    ds = db.scalar(
        select(WhGovernedDataset).where(
            WhGovernedDataset.dataset_key == dataset_key,
            WhGovernedDataset.enabled.is_(True),
        )
    )
    if not ds:
        return {"error": "dataset_not_found_or_disabled", "rows": []}

    cols = list(ds.allowed_columns_json or [])
    if dataset_key == "executive_daily":
        rows = db.scalars(
            select(WhMartExecutiveDaily).order_by(WhMartExecutiveDaily.snapshot_date.desc()).limit(limit)
        ).all()
        data = [
            {
                "snapshot_date": r.snapshot_date.isoformat(),
                "reporting_currency": r.reporting_currency,
                "cash_balance": float(r.cash_balance) if r.cash_balance is not None else None,
                "pipeline_open": float(r.pipeline_open) if r.pipeline_open is not None else None,
                "active_investors": r.active_investors,
                "marketing_spend": float(r.marketing_spend) if r.marketing_spend is not None else None,
                "project_count": r.project_count,
            }
            for r in rows
        ]
    elif dataset_key == "cash_movements":
        rows = db.scalars(
            select(WhFactCashMovement).order_by(WhFactCashMovement.date_key.desc()).limit(limit)
        ).all()
        data = [
            {
                "date_key": r.date_key,
                "txn_type": r.txn_type,
                "amount_original": float(r.amount_original),
                "currency_original": r.currency_original,
                "amount_usd": float(r.amount_usd) if r.amount_usd is not None else None,
                "amount_try": float(r.amount_try) if r.amount_try is not None else None,
                "status": r.status,
            }
            for r in rows
        ]
    elif dataset_key == "pipeline_snapshot":
        rows = db.scalars(
            select(WhFactPipeline).order_by(WhFactPipeline.snapshot_date.desc()).limit(limit)
        ).all()
        data = [
            {
                "snapshot_date": r.snapshot_date.isoformat(),
                "stage": r.stage,
                "is_open": r.is_open,
                "expected_revenue_original": float(r.expected_revenue_original)
                if r.expected_revenue_original is not None
                else None,
                "currency_original": r.currency_original,
                "expected_revenue_usd": float(r.expected_revenue_usd)
                if r.expected_revenue_usd is not None
                else None,
                "expected_revenue_try": float(r.expected_revenue_try)
                if r.expected_revenue_try is not None
                else None,
            }
            for r in rows
        ]
    else:
        return {"error": "dataset_handler_missing", "rows": [], "allowed_columns": cols}

    # Filter to allowed columns only
    filtered = [{k: row.get(k) for k in cols if k in row} for row in data]
    return {
        "dataset_key": dataset_key,
        "mart_table": ds.mart_table,
        "classification": ds.classification,
        "allowed_columns": cols,
        "row_count": len(filtered),
        "rows": filtered,
    }
