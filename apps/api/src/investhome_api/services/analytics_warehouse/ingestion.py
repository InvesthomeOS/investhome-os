"""Warehouse ingestion framework — incremental + full refresh with run tracking."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.core.logging_config import get_logger
from investhome_api.models.analytics_warehouse import (
    IngestionMode,
    IngestionStatus,
    WhDimCampaign,
    WhDimDate,
    WhDimInvestor,
    WhDimProject,
    WhFactCashMovement,
    WhFactInvestorActivity,
    WhFactMarketingSpend,
    WhFactPipeline,
    WhIngestionRun,
    WhLineageEdge,
    WhMartExecutiveDaily,
    WhStatusHistory,
)
from investhome_api.models.finance import (
    AccountStatus,
    FinancialAccount,
    FinanceTransaction,
    TransactionStatus,
)
from investhome_api.models.investor import Investor
from investhome_api.models.project import Project
from investhome_api.services.analytics_warehouse.currency import (
    convert_reporting,
    date_key,
    ensure_identity_fx,
)
from investhome_api.services.analytics_warehouse.seed_catalog import sync_metric_catalog_and_lineage

logger = get_logger("investhome.analytics.warehouse")

JOB_NAME_INCREMENTAL = "warehouse_ingestion_incremental"
JOB_NAME_FULL_REFRESH = "warehouse_ingestion_full_refresh"

CLOSED_STAGES = frozenset({"won", "lost", "dormant", "cancelled", "closed_won", "closed_lost"})


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_dim_dates(db: Session, start: date, end: date) -> int:
    written = 0
    cur = start
    while cur <= end:
        key = date_key(cur)
        existing = db.get(WhDimDate, key)
        if not existing:
            db.add(
                WhDimDate(
                    date_key=key,
                    full_date=cur,
                    year=cur.year,
                    quarter=(cur.month - 1) // 3 + 1,
                    month=cur.month,
                    week=int(cur.strftime("%U")),
                    day_of_week=cur.isoweekday(),
                    is_month_end=(cur + timedelta(days=1)).month != cur.month,
                )
            )
            written += 1
        cur += timedelta(days=1)
    if written:
        db.flush()
    return written


def _upsert_lineage(db: Session, source: str, target: str, relation: str, domain: str) -> None:
    existing = db.scalar(
        select(WhLineageEdge).where(
            WhLineageEdge.source_object == source,
            WhLineageEdge.target_object == target,
            WhLineageEdge.relation == relation,
        )
    )
    if existing:
        existing.updated_at = _utcnow()
        return
    db.add(
        WhLineageEdge(
            source_object=source,
            target_object=target,
            relation=relation,
            domain=domain,
        )
    )


def _load_projects(db: Session, run_id: UUID) -> tuple[int, int, list[str]]:
    rows = list(db.scalars(select(Project)).all())
    written = 0
    rejected = 0
    reasons: list[str] = []
    for p in rows:
        pname = getattr(p, "project_name", None) or getattr(p, "name", None)
        if not p.id or not (pname or "").strip():
            rejected += 1
            reasons.append(f"project_missing_name:{p.id}")
            continue
        dim = db.scalar(select(WhDimProject).where(WhDimProject.source_project_id == p.id))
        status_raw = getattr(p, "project_status", None) or getattr(p, "status", None)
        status_val = getattr(status_raw, "value", status_raw) if status_raw is not None else None
        ptype = getattr(p.project_type, "value", p.project_type) if getattr(p, "project_type", None) else None
        if dim:
            if dim.status and status_val and dim.status != str(status_val):
                db.add(
                    WhStatusHistory(
                        entity_type="project",
                        source_entity_id=p.id,
                        from_status=dim.status,
                        to_status=str(status_val),
                        changed_at=_utcnow(),
                        ingestion_run_id=run_id,
                    )
                )
            dim.name = str(pname)
            dim.status = str(status_val) if status_val else dim.status
            dim.project_type = str(ptype) if ptype else dim.project_type
            dim.currency = getattr(p, "currency", None) or dim.currency
            dim.loaded_at = _utcnow()
            dim.ingestion_run_id = run_id
        else:
            db.add(
                WhDimProject(
                    source_project_id=p.id,
                    name=str(pname),
                    status=str(status_val) if status_val else None,
                    project_type=str(ptype) if ptype else None,
                    currency=getattr(p, "currency", None),
                    ingestion_run_id=run_id,
                )
            )
        written += 1
    db.flush()
    _upsert_lineage(db, "public.projects", "analytics.wh_dim_project", "extracts", "projects")
    return len(rows), written, reasons


def _investor_display_name(inv: Investor) -> str:
    for attr in ("full_name", "name", "display_name", "company_name"):
        val = getattr(inv, attr, None)
        if val and str(val).strip():
            return str(val).strip()
    return f"Investor {inv.id}"


def _load_investors(db: Session, run_id: UUID) -> tuple[int, int, list[str]]:
    rows = list(db.scalars(select(Investor).where(Investor.archived_at.is_(None))).all())
    written = 0
    rejected = 0
    reasons: list[str] = []
    today = date.today()
    for inv in rows:
        name = _investor_display_name(inv)
        status_val = getattr(inv.status, "value", inv.status) if inv.status is not None else None
        dim = db.scalar(select(WhDimInvestor).where(WhDimInvestor.source_investor_id == inv.id))
        if dim:
            if dim.status and status_val and dim.status != str(status_val):
                db.add(
                    WhStatusHistory(
                        entity_type="investor",
                        source_entity_id=inv.id,
                        from_status=dim.status,
                        to_status=str(status_val),
                        changed_at=_utcnow(),
                        ingestion_run_id=run_id,
                    )
                )
            dim.display_name = name
            dim.status = str(status_val) if status_val else dim.status
            dim.country = getattr(inv, "country", None) or dim.country
            dim.loaded_at = _utcnow()
            dim.ingestion_run_id = run_id
            investor_sk = dim.investor_sk
        else:
            dim = WhDimInvestor(
                source_investor_id=inv.id,
                display_name=name,
                status=str(status_val) if status_val else None,
                country=getattr(inv, "country", None),
                ingestion_run_id=run_id,
            )
            db.add(dim)
            db.flush()
            investor_sk = dim.investor_sk
        is_active = str(status_val or "").lower() in {
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
        existing_fact = db.scalar(
            select(WhFactInvestorActivity).where(
                WhFactInvestorActivity.source_investor_id == inv.id,
                WhFactInvestorActivity.snapshot_date == today,
            )
        )
        if existing_fact:
            existing_fact.is_active = is_active
            existing_fact.status = str(status_val) if status_val else None
            existing_fact.investor_sk = investor_sk
            existing_fact.ingestion_run_id = run_id
            existing_fact.loaded_at = _utcnow()
        else:
            db.add(
                WhFactInvestorActivity(
                    source_investor_id=inv.id,
                    investor_sk=investor_sk,
                    snapshot_date=today,
                    status=str(status_val) if status_val else None,
                    is_active=is_active,
                    ingestion_run_id=run_id,
                )
            )
        written += 1
    db.flush()
    _upsert_lineage(db, "public.investors", "analytics.wh_dim_investor", "extracts", "investors")
    _upsert_lineage(db, "analytics.wh_dim_investor", "analytics.wh_fact_investor_activity", "feeds", "investors")
    return len(rows), written, reasons if rejected else []


def _load_cash(db: Session, run_id: UUID, watermark_from: datetime | None, full: bool) -> tuple[int, int, list[str]]:
    q = select(FinanceTransaction)
    if not full and watermark_from is not None:
        q = q.where(FinanceTransaction.updated_at >= watermark_from)  # type: ignore[attr-defined]
    try:
        rows = list(db.scalars(q).all())
    except Exception:
        # Some envs may lack updated_at — fall back to all (documented)
        rows = list(db.scalars(select(FinanceTransaction)).all())
    written = 0
    rejected = 0
    reasons: list[str] = []
    for txn in rows:
        amount = getattr(txn, "amount", None)
        if amount is None:
            rejected += 1
            reasons.append(f"cash_missing_amount:{txn.id}")
            continue
        ccy = (getattr(txn, "currency", None) or "USD").upper()
        occurred = getattr(txn, "transaction_date", None) or getattr(txn, "created_at", None) or _utcnow()
        if isinstance(occurred, datetime):
            d = occurred.date()
            occurred_at = occurred if occurred.tzinfo else occurred.replace(tzinfo=timezone.utc)
        else:
            d = occurred if isinstance(occurred, date) else date.today()
            occurred_at = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
        ensure_identity_fx(db, d)
        amount_dec = Decimal(str(amount))
        amount_usd, amount_try, fx_usd, fx_try = convert_reporting(
            db, amount=amount_dec, currency=ccy, as_of=d
        )
        status_val = getattr(txn.status, "value", txn.status) if txn.status is not None else "unknown"
        txn_type = getattr(txn.transaction_type, "value", txn.transaction_type) if hasattr(txn, "transaction_type") else "other"
        project_id = getattr(txn, "project_id", None)
        project_sk = None
        if project_id:
            dim = db.scalar(select(WhDimProject).where(WhDimProject.source_project_id == project_id))
            project_sk = dim.project_sk if dim else None
        existing = db.scalar(
            select(WhFactCashMovement).where(WhFactCashMovement.source_transaction_id == txn.id)
        )
        if existing:
            # Upsert — no duplicate increments
            existing.amount_original = amount_dec
            existing.currency_original = ccy
            existing.amount_usd = amount_usd
            existing.amount_try = amount_try
            existing.fx_rate_usd = fx_usd
            existing.fx_rate_try = fx_try
            existing.status = str(status_val)
            existing.txn_type = str(txn_type)
            existing.date_key = date_key(d)
            existing.occurred_at = occurred_at
            existing.project_sk = project_sk
            existing.account_id = getattr(txn, "account_id", None)
            existing.ingestion_run_id = run_id
            existing.loaded_at = _utcnow()
        else:
            db.add(
                WhFactCashMovement(
                    source_transaction_id=txn.id,
                    date_key=date_key(d),
                    project_sk=project_sk,
                    account_id=getattr(txn, "account_id", None),
                    txn_type=str(txn_type),
                    amount_original=amount_dec,
                    currency_original=ccy,
                    amount_usd=amount_usd,
                    amount_try=amount_try,
                    fx_rate_usd=fx_usd,
                    fx_rate_try=fx_try,
                    status=str(status_val),
                    occurred_at=occurred_at,
                    ingestion_run_id=run_id,
                )
            )
        written += 1
    db.flush()
    _upsert_lineage(db, "public.finance_transactions", "analytics.wh_fact_cash_movement", "extracts", "finance")
    return len(rows), written, reasons


def _load_pipeline(db: Session, run_id: UUID) -> tuple[int, int, list[str]]:
    try:
        from investhome_api.models.sales import SalesOpportunity
    except Exception:
        return 0, 0, ["sales_opportunities_model_unavailable"]

    rows = list(db.scalars(select(SalesOpportunity).where(SalesOpportunity.archived_at.is_(None))).all())
    today = date.today()
    dk = date_key(today)
    written = 0
    rejected = 0
    reasons: list[str] = []
    for opp in rows:
        stage = str(getattr(opp.stage, "value", opp.stage) if opp.stage is not None else "unknown")
        is_open = stage.lower() not in CLOSED_STAGES
        revenue = getattr(opp, "expected_revenue", None)
        ccy = (getattr(opp, "currency", None) or "USD").upper()
        amount_usd = amount_try = None
        if revenue is not None:
            ensure_identity_fx(db, today)
            amount_usd, amount_try, _, _ = convert_reporting(
                db, amount=Decimal(str(revenue)), currency=ccy, as_of=today
            )
        project_id = getattr(opp, "project_id", None)
        project_sk = None
        if project_id:
            dim = db.scalar(select(WhDimProject).where(WhDimProject.source_project_id == project_id))
            project_sk = dim.project_sk if dim else None
        existing = db.scalar(
            select(WhFactPipeline).where(
                WhFactPipeline.source_opportunity_id == opp.id,
                WhFactPipeline.snapshot_date == today,
            )
        )
        if existing:
            existing.stage = stage
            existing.is_open = is_open
            existing.expected_revenue_original = Decimal(str(revenue)) if revenue is not None else None
            existing.currency_original = ccy
            existing.expected_revenue_usd = amount_usd
            existing.expected_revenue_try = amount_try
            existing.project_sk = project_sk
            existing.probability = Decimal(str(opp.probability)) if getattr(opp, "probability", None) is not None else None
            existing.ingestion_run_id = run_id
            existing.loaded_at = _utcnow()
        else:
            db.add(
                WhFactPipeline(
                    source_opportunity_id=opp.id,
                    snapshot_date=today,
                    date_key=dk,
                    project_sk=project_sk,
                    stage=stage,
                    is_open=is_open,
                    expected_revenue_original=Decimal(str(revenue)) if revenue is not None else None,
                    currency_original=ccy,
                    expected_revenue_usd=amount_usd,
                    expected_revenue_try=amount_try,
                    probability=Decimal(str(opp.probability)) if getattr(opp, "probability", None) is not None else None,
                    ingestion_run_id=run_id,
                )
            )
        written += 1
    db.flush()
    _upsert_lineage(db, "public.sales_opportunities", "analytics.wh_fact_pipeline", "extracts", "sales")
    return len(rows), written, reasons if rejected else []


def _load_marketing(db: Session, run_id: UUID) -> tuple[int, int, list[str]]:
    """Best-effort campaign dim + spend facts when marketing tables exist."""
    written = 0
    rejected = 0
    reasons: list[str] = []
    read = 0
    today = date.today()
    dk = date_key(today)
    try:
        from investhome_api.models.marketing import MarketingCampaign
    except Exception:
        return 0, 0, ["marketing_campaign_model_unavailable"]

    rows = list(db.scalars(select(MarketingCampaign)).all())
    read = len(rows)
    for camp in rows:
        name = getattr(camp, "name", None) or getattr(camp, "title", None) or f"Campaign {camp.id}"
        status_val = getattr(camp.status, "value", camp.status) if getattr(camp, "status", None) is not None else None
        channel = None
        primary = getattr(camp, "primary_channel", None)
        if primary is not None:
            channel = getattr(primary, "value", primary)
        dim = db.scalar(select(WhDimCampaign).where(WhDimCampaign.source_campaign_id == camp.id))
        if dim:
            dim.name = str(name)
            dim.status = str(status_val) if status_val else dim.status
            dim.channel = str(channel) if channel else dim.channel
            dim.loaded_at = _utcnow()
            dim.ingestion_run_id = run_id
            campaign_sk = dim.campaign_sk
        else:
            dim = WhDimCampaign(
                source_campaign_id=camp.id,
                name=str(name),
                status=str(status_val) if status_val else None,
                channel=str(channel) if channel else None,
                ingestion_run_id=run_id,
            )
            db.add(dim)
            db.flush()
            campaign_sk = dim.campaign_sk
        spend = (
            getattr(camp, "budget_spent", None)
            or getattr(camp, "spent_amount", None)
            or getattr(camp, "actual_spend", None)
            or getattr(camp, "budget_amount", None)
        )
        if spend is None:
            # Still count dim write; spend fact optional
            written += 1
            continue
        ccy = (getattr(camp, "budget_currency", None) or getattr(camp, "currency", None) or "USD").upper()
        ensure_identity_fx(db, today)
        amount_dec = Decimal(str(spend))
        amount_usd, amount_try, _, _ = convert_reporting(db, amount=amount_dec, currency=ccy, as_of=today)
        source_row_id = f"campaign_budget:{camp.id}"
        existing = db.scalar(
            select(WhFactMarketingSpend).where(WhFactMarketingSpend.source_row_id == source_row_id)
        )
        if existing:
            existing.spend_original = amount_dec
            existing.currency_original = ccy
            existing.spend_usd = amount_usd
            existing.spend_try = amount_try
            existing.campaign_sk = campaign_sk
            existing.date_key = dk
            existing.ingestion_run_id = run_id
            existing.loaded_at = _utcnow()
        else:
            db.add(
                WhFactMarketingSpend(
                    source_row_id=source_row_id,
                    campaign_sk=campaign_sk,
                    date_key=dk,
                    spend_original=amount_dec,
                    currency_original=ccy,
                    spend_usd=amount_usd,
                    spend_try=amount_try,
                    ingestion_run_id=run_id,
                )
            )
        written += 1
    db.flush()
    _upsert_lineage(db, "public.marketing_campaigns", "analytics.wh_dim_campaign", "extracts", "marketing")
    _upsert_lineage(db, "analytics.wh_dim_campaign", "analytics.wh_fact_marketing_spend", "feeds", "marketing")
    return read, written, reasons if rejected else []


def _build_executive_mart(db: Session, run_id: UUID) -> int:
    today = date.today()
    written = 0
    # Cash from active accounts (OLTP truth for balance) — reporting identity when ccy matches
    accounts = list(
        db.scalars(select(FinancialAccount).where(FinancialAccount.status == AccountStatus.ACTIVE)).all()
    )
    cash_by_ccy: dict[str, Decimal] = {"USD": Decimal("0"), "TRY": Decimal("0")}
    for acct in accounts:
        bal = Decimal(str(getattr(acct, "available_balance", None) or getattr(acct, "balance", None) or 0))
        ccy = (getattr(acct, "currency", None) or "USD").upper()
        ensure_identity_fx(db, today)
        usd, try_amt, _, _ = convert_reporting(db, amount=bal, currency=ccy, as_of=today)
        if usd is not None:
            cash_by_ccy["USD"] += usd
        if try_amt is not None:
            cash_by_ccy["TRY"] += try_amt
        if ccy == "USD":
            cash_by_ccy["USD"] = cash_by_ccy.get("USD", Decimal("0"))  # already via convert if identity
        if ccy == "TRY" and try_amt is None:
            cash_by_ccy["TRY"] += bal

    pipeline_usd = db.scalar(
        select(func.coalesce(func.sum(WhFactPipeline.expected_revenue_usd), 0)).where(
            WhFactPipeline.snapshot_date == today,
            WhFactPipeline.is_open.is_(True),
        )
    )
    pipeline_try = db.scalar(
        select(func.coalesce(func.sum(WhFactPipeline.expected_revenue_try), 0)).where(
            WhFactPipeline.snapshot_date == today,
            WhFactPipeline.is_open.is_(True),
        )
    )
    active_investors = db.scalar(
        select(func.count()).select_from(WhFactInvestorActivity).where(
            WhFactInvestorActivity.snapshot_date == today,
            WhFactInvestorActivity.is_active.is_(True),
        )
    ) or 0
    mkt_usd = db.scalar(
        select(func.coalesce(func.sum(WhFactMarketingSpend.spend_usd), 0)).where(
            WhFactMarketingSpend.date_key == date_key(today)
        )
    )
    mkt_try = db.scalar(
        select(func.coalesce(func.sum(WhFactMarketingSpend.spend_try), 0)).where(
            WhFactMarketingSpend.date_key == date_key(today)
        )
    )
    project_count = db.scalar(select(func.count()).select_from(WhDimProject).where(WhDimProject.is_current.is_(True))) or 0

    for ccy, cash, pipe, mkt in (
        ("USD", cash_by_ccy["USD"], pipeline_usd, mkt_usd),
        ("TRY", cash_by_ccy["TRY"], pipeline_try, mkt_try),
    ):
        existing = db.scalar(
            select(WhMartExecutiveDaily).where(
                WhMartExecutiveDaily.snapshot_date == today,
                WhMartExecutiveDaily.reporting_currency == ccy,
            )
        )
        if existing:
            existing.cash_balance = Decimal(str(cash or 0))
            existing.pipeline_open = Decimal(str(pipe or 0))
            existing.active_investors = int(active_investors)
            existing.marketing_spend = Decimal(str(mkt or 0))
            existing.project_count = int(project_count)
            existing.ingestion_run_id = run_id
            existing.loaded_at = _utcnow()
        else:
            db.add(
                WhMartExecutiveDaily(
                    snapshot_date=today,
                    reporting_currency=ccy,
                    cash_balance=Decimal(str(cash or 0)),
                    pipeline_open=Decimal(str(pipe or 0)),
                    active_investors=int(active_investors),
                    marketing_spend=Decimal(str(mkt or 0)),
                    project_count=int(project_count),
                    ingestion_run_id=run_id,
                )
            )
        written += 1
    db.flush()
    _upsert_lineage(db, "analytics.wh_fact_cash_movement", "analytics.wh_mart_executive_daily", "transforms", "executive")
    _upsert_lineage(db, "analytics.wh_fact_pipeline", "analytics.wh_mart_executive_daily", "transforms", "executive")
    return written


def run_warehouse_ingestion(
    db: Session,
    *,
    mode: str = IngestionMode.INCREMENTAL.value,
    created_by: UUID | None = None,
    domains: list[str] | None = None,
) -> WhIngestionRun:
    """Run multi-domain warehouse load. Rejects are recorded — never silently skipped."""
    full = mode == IngestionMode.FULL_REFRESH.value
    job_name = JOB_NAME_FULL_REFRESH if full else JOB_NAME_INCREMENTAL
    run = WhIngestionRun(
        domain="warehouse",
        job_name=job_name,
        mode=mode,
        status=IngestionStatus.PENDING.value,
        created_by=created_by,
        meta_json={"domains": domains or ["all"]},
    )
    db.add(run)
    db.flush()

    run.status = IngestionStatus.RUNNING.value
    run.started_at = _utcnow()
    # Watermark: last successful run
    last = db.scalar(
        select(WhIngestionRun)
        .where(
            WhIngestionRun.status == IngestionStatus.SUCCEEDED.value,
            WhIngestionRun.id != run.id,
        )
        .order_by(WhIngestionRun.finished_at.desc())
        .limit(1)
    )
    watermark_from = last.finished_at if last and not full else None
    run.watermark_from = watermark_from
    run.watermark_to = _utcnow()
    db.flush()

    total_read = 0
    total_written = 0
    total_rejected = 0
    all_reasons: list[str] = []
    errors: list[str] = []

    today = date.today()
    try:
        total_written += _ensure_dim_dates(db, today - timedelta(days=400), today + timedelta(days=30))
        ensure_identity_fx(db, today)
        sync_metric_catalog_and_lineage(db)

        steps = [
            ("projects", lambda: _load_projects(db, run.id)),
            ("investors", lambda: _load_investors(db, run.id)),
            ("finance", lambda: _load_cash(db, run.id, watermark_from, full)),
            ("sales", lambda: _load_pipeline(db, run.id)),
            ("marketing", lambda: _load_marketing(db, run.id)),
        ]
        selected = set(domains) if domains else None
        for name, fn in steps:
            if selected and name not in selected and "all" not in selected:
                continue
            try:
                r, w, reasons = fn()
                total_read += r
                total_written += w
                total_rejected += len(reasons)
                all_reasons.extend(reasons[:50])
            except Exception as exc:  # noqa: BLE001 — per-domain isolation
                logger.exception("warehouse_ingestion_domain_failed", extra={"domain": name})
                errors.append(f"{name}:{exc}")
                total_rejected += 1
                all_reasons.append(f"{name}_failed:{exc}")

        try:
            total_written += _build_executive_mart(db, run.id)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"mart:{exc}")
            all_reasons.append(f"mart_failed:{exc}")

        run.rows_read = total_read
        run.rows_written = total_written
        run.rows_rejected = total_rejected
        run.reject_reasons_json = all_reasons[:100] or None
        run.finished_at = _utcnow()

        if errors and total_written == 0:
            run.status = IngestionStatus.FAILED.value
            run.error_message = "; ".join(errors)[:2000]
        elif errors or total_rejected:
            run.status = IngestionStatus.PARTIAL.value
            run.error_message = "; ".join(errors)[:2000] if errors else None
        else:
            run.status = IngestionStatus.SUCCEEDED.value

        db.commit()
        db.refresh(run)
        return run
    except Exception as exc:  # noqa: BLE001
        logger.exception("warehouse_ingestion_failed")
        run.status = IngestionStatus.FAILED.value
        run.error_message = str(exc)[:2000]
        run.rows_read = total_read
        run.rows_written = total_written
        run.rows_rejected = total_rejected
        run.reject_reasons_json = all_reasons[:100] or None
        run.finished_at = _utcnow()
        db.commit()
        db.refresh(run)
        return run


async def warehouse_ingestion_incremental_job(ctx: dict[str, Any]) -> dict[str, Any]:
    """ARQ cron entrypoint — incremental warehouse refresh."""
    from investhome_api.db.session import SessionLocal

    db = SessionLocal()
    try:
        run = run_warehouse_ingestion(db, mode=IngestionMode.INCREMENTAL.value)
        return {
            "run_id": str(run.id),
            "status": run.status,
            "rows_written": run.rows_written,
            "rows_rejected": run.rows_rejected,
        }
    finally:
        db.close()


async def warehouse_ingestion_full_refresh_job(ctx: dict[str, Any]) -> dict[str, Any]:
    from investhome_api.db.session import SessionLocal

    db = SessionLocal()
    try:
        run = run_warehouse_ingestion(db, mode=IngestionMode.FULL_REFRESH.value)
        return {
            "run_id": str(run.id),
            "status": run.status,
            "rows_written": run.rows_written,
            "rows_rejected": run.rows_rejected,
        }
    finally:
        db.close()
