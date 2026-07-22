"""Business Intelligence aggregation — reuses existing domain services (P9)."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from investhome_api.config.analytics_metric_registry import (
    METRIC_REGISTRY,
    get_metric,
    list_metrics,
)
from investhome_api.models.analytics_bi import BiAlertThreshold, BiSavedReport
from investhome_api.models.finance import (
    ObligationStatus,
    PaymentObligation,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.analytics_bi import (
    BiAlertThresholdCreate,
    BiAlertThresholdOut,
    BiDomainResponse,
    BiDomainSection,
    BiDomainSeriesPoint,
    BiFilters,
    BiMetricValue,
    BiOverviewResponse,
    BiSavedReportCreate,
    BiSavedReportOut,
    BiSavedReportUpdate,
    DataQualityFinding,
    DataQualityResponse,
    MetricComparisonOut,
    MetricDefinitionOut,
)
from investhome_api.schemas.marketing_performance import PerformanceFilters
from investhome_api.schemas.executive import ExecutiveFilters
from investhome_api.services.executive_service import (
    build_attention_items,
    build_executive_summary,
    build_financial_overview,
    build_investor_overview,
    build_leads_pipeline,
    build_project_portfolio,
)
from investhome_api.services.finance_service import compute_finance_stats
from investhome_api.services.permission_service import user_has_permission
from investhome_api.services.sales.opportunity_service import (
    build_dashboard_metrics as build_sales_dashboard_metrics,
)
from investhome_api.services.sales.opportunity_service import (
    build_executive_summary as build_sales_executive_summary,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _period_delta(filters: BiFilters) -> timedelta:
    if filters.date_from and filters.date_to:
        days = max((filters.date_to - filters.date_from).days + 1, 1)
        return timedelta(days=days)
    return timedelta(days=30)


def _to_exec_filters(filters: BiFilters) -> ExecutiveFilters:
    today = date.today()
    date_from = filters.date_from or (today - timedelta(days=29))
    date_to = filters.date_to or today
    return ExecutiveFilters(
        date_from=date_from,
        date_to=date_to,
        project_id=filters.project_id,
        assigned_to=filters.assigned_to,
        currency=filters.currency.upper() if filters.currency else None,
    )


def _decimal_to_number(value: Decimal | int | float | str | None) -> float | int | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    if isinstance(value, str):
        try:
            d = Decimal(value)
            if d == d.to_integral_value():
                return int(d)
            return float(d)
        except Exception:
            return None
    return value


def _pct_change(current: float | int | None, previous: float | int | None) -> MetricComparisonOut:
    if current is None or previous is None:
        return MetricComparisonOut(
            previous=previous,
            change_pct=None,
            change_available=False,
            reason="comparison_unavailable",
        )
    if previous == 0:
        return MetricComparisonOut(
            previous=previous,
            change_pct=None,
            change_available=False,
            reason="previous_period_zero",
        )
    change = ((float(current) - float(previous)) / abs(float(previous))) * 100.0
    return MetricComparisonOut(
        previous=previous,
        change_pct=round(change, 2),
        change_available=True,
    )


def _metric_base(key: str, filters: BiFilters) -> BiMetricValue:
    definition = get_metric(key)
    if not definition:
        return BiMetricValue(key=key, name=key, state="unavailable", reason="unknown_metric")
    return BiMetricValue(
        key=definition.key,
        name=definition.name,
        state="unavailable",
        unit=definition.unit,
        definition=definition.description,
        source=definition.source,
        date_from=filters.date_from,
        date_to=filters.date_to,
        freshness_seconds=definition.freshness_seconds,
        drilldown_path=definition.drilldown_path,
        freshness_at=_utcnow(),
    )


def _denied(key: str, filters: BiFilters) -> BiMetricValue:
    m = _metric_base(key, filters)
    m.state = "permission"
    m.reason = "permission_denied"
    return m


def _can(user: User, resource: str, action: str) -> bool:
    return user_has_permission(user, resource, action)


def registry_payload(*, domain: str | None = None) -> list[MetricDefinitionOut]:
    return [
        MetricDefinitionOut(
            key=m.key,
            name=m.name,
            description=m.description,
            formula=m.formula,
            source=m.source,
            domain=m.domain,
            unit=m.unit,
            currency_aware=m.currency_aware,
            permission=f"{m.permission[0]}:{m.permission[1]}",
            supports_comparison=m.supports_comparison,
            freshness_seconds=m.freshness_seconds,
            drilldown_path=m.drilldown_path,
            filters=list(m.filters),
            certification_status=m.certification_status,
            grain=m.grain,
            reporting_timezone=m.reporting_timezone,
        )
        for m in list_metrics(domain=domain)
    ]


def _card_lookup(cards: list[Any]) -> dict[str, Any]:
    return {c.key: c for c in cards}


def build_overview(db: Session, user: User, filters: BiFilters) -> BiOverviewResponse:
    exec_filters = _to_exec_filters(filters)
    filters = filters.model_copy(
        update={"date_from": exec_filters.date_from, "date_to": exec_filters.date_to}
    )
    missing: list[str] = []
    metrics: list[BiMetricValue] = []
    now = _utcnow()

    summary = None
    attention = None
    finance_stats = None
    sales_metrics = None
    investor = None
    projects = None
    automation = None

    if _can(user, "executive", "view"):
        try:
            summary = build_executive_summary(db, exec_filters, user)
        except Exception:
            summary = None
            missing.append("executive.summary")
            try:
                db.rollback()
            except Exception:
                pass
        try:
            attention = build_attention_items(db, exec_filters)
        except Exception:
            attention = None
            missing.append("executive.attention")
            try:
                db.rollback()
            except Exception:
                pass
    else:
        missing.append("executive.summary")

    if _can(user, "finance", "view"):
        try:
            finance_stats = compute_finance_stats(db)
        except Exception:
            finance_stats = None
            missing.append("finance.stats")
            try:
                db.rollback()
            except Exception:
                pass
    else:
        missing.append("finance.stats")

    if _can(user, "sales", "view") or _can(user, "leads", "view"):
        try:
            sales_metrics = build_sales_dashboard_metrics(db)
        except Exception:
            sales_metrics = None
            missing.append("sales.dashboard/metrics")
            try:
                db.rollback()
            except Exception:
                pass
    else:
        missing.append("sales.dashboard/metrics")

    if _can(user, "investors", "view"):
        try:
            investor = build_investor_overview(db, exec_filters)
        except Exception:
            investor = None
            missing.append("executive.investor_overview")
            try:
                db.rollback()
            except Exception:
                pass
    else:
        missing.append("executive.investor_overview")

    if _can(user, "projects", "view"):
        try:
            projects = build_project_portfolio(db, exec_filters)
        except Exception:
            projects = None
            missing.append("executive.project_portfolio")
            try:
                db.rollback()
            except Exception:
                pass
    else:
        missing.append("executive.project_portfolio")

    if _can(user, "automation", "view"):
        try:
            from investhome_api.services import automation_center_service as auto_svc

            automation = auto_svc.get_overview(db)
        except Exception:
            missing.append("automation.overview")
    else:
        missing.append("automation.overview")

    cards = _card_lookup(summary.cards) if summary else {}

    # Revenue
    rev = _metric_base("revenue", filters)
    if not _can(user, "finance", "view"):
        rev = _denied("revenue", filters)
    else:
        fin = None
        if _can(user, "executive", "view"):
            try:
                fin = build_financial_overview(db, exec_filters)
            except Exception:
                missing.append("executive.financial_overview")
                try:
                    db.rollback()
                except Exception:
                    pass
        if fin and fin.income_in_period:
            if filters.currency and filters.currency.upper() in fin.income_in_period:
                rev.value = _decimal_to_number(fin.income_in_period[filters.currency.upper()])
                rev.currency = filters.currency.upper()
            else:
                parts = [f"{cur} {amt}" for cur, amt in fin.income_in_period.items()]
                rev.value = ", ".join(parts)
                rev.currency = None
            rev.state = "ready"
            rev.comparison = MetricComparisonOut(
                change_available=False,
                reason="previous_period_income_not_materialized",
            )
        else:
            rev.state = "unavailable"
            rev.reason = "period_revenue_unavailable"
            missing.append("executive.financial_overview.income_in_period")
            rev.comparison = MetricComparisonOut(change_available=False, reason="comparison_unavailable")
    metrics.append(rev)

    # Cash
    cash = _metric_base("cash", filters)
    if not _can(user, "finance", "view"):
        cash = _denied("cash", filters)
    else:
        card = cards.get("available_cash")
        if card and card.currency_totals:
            # Multi-currency — expose as text totals, no fake single %
            parts = [f"{cur} {amt}" for cur, amt in card.currency_totals.items()]
            cash.value = ", ".join(parts) if parts else None
            cash.state = "ready" if parts else "empty"
            cash.unit = "currency"
            if card.currency_comparison and card.currency_comparison.change_available:
                cash.comparison = MetricComparisonOut(change_available=True)
            else:
                cash.comparison = MetricComparisonOut(
                    change_available=False,
                    reason="multi_currency_or_missing_previous",
                )
        elif card and card.value is not None:
            cash.value = _decimal_to_number(card.value) if not isinstance(card.value, str) else card.value
            cash.state = "ready"
            cash.comparison = MetricComparisonOut(change_available=False, reason="comparison_unavailable")
        elif finance_stats and isinstance(finance_stats.get("available_cash"), dict):
            totals = finance_stats["available_cash"]
            if totals:
                parts = [f"{cur} {amt}" for cur, amt in totals.items()]
                cash.value = ", ".join(parts)
                cash.state = "ready"
                cash.comparison = MetricComparisonOut(
                    change_available=False,
                    reason="multi_currency_or_missing_previous",
                )
            else:
                cash.state = "empty"
                cash.reason = "no_active_accounts"
        else:
            cash.state = "empty"
            cash.reason = "no_active_accounts"
    metrics.append(cash)

    # Receivables
    recv = _metric_base("receivables", filters)
    if not _can(user, "finance", "view"):
        recv = _denied("receivables", filters)
    else:
        open_statuses = [
            ObligationStatus.UPCOMING,
            ObligationStatus.DUE,
            ObligationStatus.OVERDUE,
        ]
        total = db.scalar(
            select(func.coalesce(func.sum(PaymentObligation.amount), 0)).where(
                PaymentObligation.archived_at.is_(None),
                PaymentObligation.status.in_(open_statuses),
            )
        )
        recv.value = _decimal_to_number(total)
        recv.state = "ready"
        recv.currency = filters.currency
        recv.comparison = MetricComparisonOut(
            change_available=False,
            reason="receivables_history_not_materialized",
        )
    metrics.append(recv)

    # Pipeline
    pipe = _metric_base("pipeline", filters)
    if not (_can(user, "sales", "view") or _can(user, "leads", "view")):
        pipe = _denied("pipeline", filters)
    elif sales_metrics is None:
        pipe.state = "unavailable"
        pipe.reason = "sales_metrics_unavailable"
    else:
        pipe.value = sales_metrics.get("pipeline_value")
        pipe.state = "ready" if pipe.value is not None else "empty"
        pipe.currency = filters.currency
        pipe.comparison = MetricComparisonOut(
            change_available=False,
            reason="pipeline_previous_period_not_materialized",
        )
    metrics.append(pipe)

    # Closed sales
    closed = _metric_base("closed_sales", filters)
    if not (_can(user, "sales", "view") or _can(user, "leads", "view")):
        closed = _denied("closed_sales", filters)
    elif sales_metrics is None:
        closed.state = "unavailable"
        closed.reason = "sales_metrics_unavailable"
    else:
        closed.value = sales_metrics.get("won_count")
        closed.state = "ready"
        closed.comparison = MetricComparisonOut(
            change_available=False,
            reason="won_count_not_period_filtered",
        )
    metrics.append(closed)

    # Active investors
    inv = _metric_base("active_investors", filters)
    if not _can(user, "investors", "view"):
        inv = _denied("active_investors", filters)
    else:
        card = cards.get("active_investors")
        if card and card.value is not None:
            inv.value = int(card.value) if str(card.value).isdigit() else card.value
            inv.state = "ready"
        elif investor is not None:
            inv.value = sum(s.count for s in investor.by_status if s.status == "active")
            inv.state = "ready"
        else:
            inv.state = "empty"
        inv.comparison = MetricComparisonOut(change_available=False, reason="investor_snapshot_only")
    metrics.append(inv)

    # Marketing spend / ROI — only when marketing services available
    m_spend = _metric_base("marketing_spend", filters)
    m_roi = _metric_base("marketing_roi", filters)
    if not (_can(user, "marketing", "view_dashboard") or _can(user, "marketing", "view")):
        m_spend = _denied("marketing_spend", filters)
        m_roi = _denied("marketing_roi", filters)
    else:
        try:
            from investhome_api.services.marketing.campaign_performance_service import (
                get_performance_overview,
            )

            overview = get_performance_overview(
                db,
                filters=PerformanceFilters(
                    date_from=datetime.combine(exec_filters.date_from, datetime.min.time(), tzinfo=timezone.utc),
                    date_to=datetime.combine(exec_filters.date_to, datetime.max.time(), tzinfo=timezone.utc),
                    campaign_id=filters.campaign_id,
                    project_id=filters.project_id,
                ),
            )
            spend_metric = overview.total_spend
            if spend_metric.state != "ready" or spend_metric.value is None:
                m_spend.state = "unavailable" if spend_metric.state != "ready" else "empty"
                m_spend.reason = spend_metric.reason or "spend_not_connected_or_empty"
                missing.append("marketing.performance.spend")
            else:
                m_spend.value = _decimal_to_number(spend_metric.value)
                m_spend.state = "ready"
                m_spend.currency = overview.currency
                m_spend.comparison = MetricComparisonOut(
                    change_available=False,
                    reason="marketing_spend_comparison_not_materialized",
                )
            # ROI is not on overview aggregate — keep honest unavailable
            m_roi.state = "unavailable"
            m_roi.reason = "roi_requires_campaign_level_revenue_and_spend"
            missing.append("marketing.performance.roi_aggregate")
            m_roi.comparison = MetricComparisonOut(
                change_available=False,
                reason="comparison_unavailable",
            )
        except Exception:
            m_spend.state = "unavailable"
            m_spend.reason = "marketing_performance_unavailable"
            m_roi.state = "unavailable"
            m_roi.reason = "marketing_performance_unavailable"
            missing.append("marketing.performance.overview")
    metrics.extend([m_spend, m_roi])

    # Project exposure
    exp = _metric_base("project_exposure", filters)
    if not _can(user, "projects", "view"):
        exp = _denied("project_exposure", filters)
    elif projects is None:
        exp.state = "unavailable"
        exp.reason = "project_portfolio_unavailable"
    else:
        gaps = [
            _decimal_to_number(p.funding_gap) or 0
            for p in projects.projects
            if p.funding_gap is not None
        ]
        if gaps:
            exp.value = sum(gaps)
            exp.state = "ready"
        else:
            exp.state = "unavailable"
            exp.reason = "funding_gap_not_available"
            missing.append("projects.funding_gap")
        exp.comparison = MetricComparisonOut(change_available=False, reason="exposure_snapshot_only")
    metrics.append(exp)

    # Open risks
    risks = _metric_base("open_risks", filters)
    if not _can(user, "executive", "view"):
        risks = _denied("open_risks", filters)
    elif attention is None:
        risks.state = "unavailable"
        risks.reason = "attention_feed_unavailable"
    else:
        risks.value = sum(1 for i in attention.items if i.severity in ("critical", "warning"))
        risks.state = "ready"
        risks.comparison = MetricComparisonOut(change_available=False, reason="point_in_time")
    metrics.append(risks)

    # Overdue actions
    overdue = _metric_base("overdue_actions", filters)
    if not _can(user, "executive", "view"):
        overdue = _denied("overdue_actions", filters)
    else:
        overdue_obs = db.scalar(
            select(func.count()).select_from(PaymentObligation).where(
                PaymentObligation.archived_at.is_(None),
                PaymentObligation.status == ObligationStatus.OVERDUE,
            )
        ) or 0
        no_follow = (sales_metrics or {}).get("no_follow_up") if sales_metrics else None
        if no_follow is None and not (_can(user, "sales", "view") or _can(user, "leads", "view")):
            overdue.value = overdue_obs
            overdue.state = "ready"
            overdue.reason = "sales_followups_excluded_no_permission"
        else:
            overdue.value = int(overdue_obs) + int(no_follow or 0)
            overdue.state = "ready"
        overdue.comparison = MetricComparisonOut(change_available=False, reason="point_in_time")
    metrics.append(overdue)

    # Automation health
    auto = _metric_base("automation_health", filters)
    if not _can(user, "automation", "view"):
        auto = _denied("automation_health", filters)
    elif automation is None:
        auto.state = "unavailable"
        auto.reason = "automation_center_unavailable"
    else:
        health = automation.get("health") if isinstance(automation, dict) else None
        status = None
        if isinstance(health, dict):
            status = health.get("availability") or health.get("status") or health.get("overall_status")
        elif health is not None:
            status = (
                getattr(health, "availability", None)
                or getattr(health, "status", None)
                or getattr(health, "overall_status", None)
            )
        auto.value = status
        auto.state = "ready" if status is not None else "empty"
        auto.comparison = MetricComparisonOut(change_available=False, reason="status_not_numeric")
    metrics.append(auto)

    for m in metrics:
        m.freshness_at = now
        m.date_from = filters.date_from
        m.date_to = filters.date_to

    attention_count = len(attention.items) if attention else 0
    return BiOverviewResponse(
        generated_at=now,
        filters=filters,
        metrics=metrics,
        attention_count=attention_count,
        missing_sources=sorted(set(missing)),
    )


def build_domain(db: Session, user: User, domain: str, filters: BiFilters) -> BiDomainResponse:
    exec_filters = _to_exec_filters(filters)
    filters = filters.model_copy(
        update={"date_from": exec_filters.date_from, "date_to": exec_filters.date_to}
    )
    now = _utcnow()
    missing: list[str] = []
    sections: list[BiDomainSection] = []

    if domain == "executive":
        overview = build_overview(db, user, filters)
        sections.append(
            BiDomainSection(
                key="kpis",
                title="Executive KPIs",
                metrics=overview.metrics,
            )
        )
        missing = overview.missing_sources

    elif domain == "sales":
        metrics: list[BiMetricValue] = []
        series: list[BiDomainSeriesPoint] = []
        if _can(user, "sales", "view") or _can(user, "leads", "view"):
            sales = build_sales_dashboard_metrics(db)
            for key, source_key in (
                ("pipeline", "pipeline_value"),
                ("closed_sales", "won_count"),
                ("lead_volume", None),
            ):
                m = _metric_base(key, filters)
                if key == "lead_volume":
                    if _can(user, "leads", "view") or _can(user, "executive", "view"):
                        try:
                            pipeline = build_leads_pipeline(db, exec_filters)
                            m.value = pipeline.summary.total
                            m.state = "ready"
                        except Exception:
                            m.state = "unavailable"
                            m.reason = "leads_pipeline_unavailable"
                            missing.append("executive.leads_pipeline")
                            try:
                                db.rollback()
                            except Exception:
                                pass
                    else:
                        m = _denied(key, filters)
                else:
                    m.value = sales.get(source_key)
                    m.state = "ready"
                    m.comparison = MetricComparisonOut(
                        change_available=False,
                        reason="sales_period_comparison_not_materialized",
                    )
                metrics.append(m)
            try:
                exec_sales = build_sales_executive_summary(db)
                for label, val in (
                    ("Pipeline", exec_sales.get("pipeline_value")),
                    ("Weighted", exec_sales.get("weighted_pipeline_value")),
                    ("High risk", exec_sales.get("high_risk_count")),
                    ("No follow-up", exec_sales.get("no_follow_up_count")),
                ):
                    numeric = _decimal_to_number(val) if not isinstance(val, str) else None
                    series.append(
                        BiDomainSeriesPoint(
                            label=label,
                            value=numeric,
                            state="ready" if val is not None else "empty",
                        )
                    )
            except Exception:
                missing.append("sales.executive-summary")
            if _can(user, "leads", "view") or _can(user, "executive", "view"):
                try:
                    pipeline = build_leads_pipeline(db, exec_filters)
                    for stage in pipeline.stages:
                        series.append(
                            BiDomainSeriesPoint(label=stage.status, value=stage.count, state="ready")
                        )
                except Exception:
                    missing.append("executive.leads_pipeline")
                    try:
                        db.rollback()
                    except Exception:
                        pass
        else:
            missing.append("sales")
            metrics = [_denied("pipeline", filters), _denied("closed_sales", filters)]
        sections.append(BiDomainSection(key="sales", title="Sales", metrics=metrics, series=series))

    elif domain == "marketing":
        metrics = []
        attribution: dict[str, int] | None = None
        notes = [
            "Attribution labels are first / last / multi / unattributed only — no invented certainty.",
        ]
        if _can(user, "marketing", "view_dashboard") or _can(user, "marketing", "view"):
            try:
                from investhome_api.services.marketing.campaign_performance_service import (
                    get_performance_overview,
                )

                overview = get_performance_overview(
                    db,
                    filters=PerformanceFilters(
                        date_from=datetime.combine(
                            exec_filters.date_from, datetime.min.time(), tzinfo=timezone.utc
                        ),
                        date_to=datetime.combine(
                            exec_filters.date_to, datetime.max.time(), tzinfo=timezone.utc
                        ),
                        campaign_id=filters.campaign_id,
                        project_id=filters.project_id,
                    ),
                )
                spend = _metric_base("marketing_spend", filters)
                if overview.total_spend.state == "ready" and overview.total_spend.value is not None:
                    spend.value = _decimal_to_number(overview.total_spend.value)
                    spend.state = "ready"
                    spend.currency = overview.currency
                else:
                    spend.state = "unavailable"
                    spend.reason = overview.total_spend.reason or "spend_not_connected"
                spend.comparison = MetricComparisonOut(
                    change_available=False, reason="comparison_unavailable"
                )
                metrics.append(spend)

                roi = _metric_base("marketing_roi", filters)
                roi.state = "unavailable"
                roi.reason = "roi_requires_campaign_level_revenue_and_spend"
                roi.comparison = MetricComparisonOut(
                    change_available=False, reason="comparison_unavailable"
                )
                metrics.append(roi)

                cov = _metric_base("attribution_coverage", filters)
                total_leads = (
                    overview.total_leads.value
                    if overview.total_leads.state == "ready"
                    else None
                )
                if total_leads is None:
                    cov.state = "unavailable"
                    cov.reason = "lead_volume_unavailable"
                else:
                    # Without first/last/multi rollup, coverage cannot be claimed
                    cov.state = "unavailable"
                    cov.reason = "attribution_model_breakdown_not_materialized"
                    missing.append("marketing.attribution.model_breakdown")
                cov.comparison = MetricComparisonOut(
                    change_available=False, reason="comparison_unavailable"
                )
                metrics.append(cov)
            except Exception:
                metrics = [
                    _metric_base("marketing_spend", filters),
                    _metric_base("marketing_roi", filters),
                ]
                for m in metrics:
                    m.state = "unavailable"
                    m.reason = "marketing_performance_unavailable"
                missing.append("marketing.performance.overview")
            attribution = None
            notes.append("Attribution model breakdown (first/last/multi/unattributed) not yet aggregated.")
            missing.append("marketing.performance.attribution_breakdown")
        else:
            metrics = [
                _denied("marketing_spend", filters),
                _denied("marketing_roi", filters),
            ]
        sections.append(
            BiDomainSection(
                key="marketing",
                title="Marketing",
                metrics=metrics,
                attribution_breakdown=attribution,
                notes=notes,
            )
        )

    elif domain == "investor":
        metrics = []
        rows: list[dict[str, Any]] = []
        if _can(user, "investors", "view"):
            try:
                overview = build_investor_overview(db, exec_filters)
                m = _metric_base("active_investors", filters)
                m.value = sum(s.count for s in overview.by_status if s.status == "active")
                m.state = "ready"
                m.comparison = MetricComparisonOut(change_available=False, reason="snapshot_only")
                metrics.append(m)
                for s in overview.by_status:
                    rows.append({"status": s.status, "count": s.count})
                for s in overview.by_investment_model:
                    rows.append({"model": s.model, "count": s.count})
            except Exception:
                m = _metric_base("active_investors", filters)
                m.state = "unavailable"
                m.reason = "investor_overview_unavailable"
                metrics.append(m)
                missing.append("executive.investor_overview")
                try:
                    db.rollback()
                except Exception:
                    pass
        else:
            metrics = [_denied("active_investors", filters)]
        sections.append(
            BiDomainSection(key="investor", title="Investor", metrics=metrics, rows=rows)
        )

    elif domain == "finance":
        metrics = []
        series = []
        if _can(user, "finance", "view"):
            fin = (
                build_financial_overview(db, exec_filters)
                if _can(user, "executive", "view")
                else None
            )
            overview = build_overview(db, user, filters)
            metrics = [m for m in overview.metrics if m.key in ("revenue", "cash", "receivables")]
            if fin and fin.cash_flow_trend:
                for point in fin.cash_flow_trend:
                    net_vals = list(point.net.values())
                    series.append(
                        BiDomainSeriesPoint(
                            label=str(point.period_start),
                            value=_decimal_to_number(sum(net_vals, Decimal("0"))) if net_vals else None,
                            state="ready" if net_vals else "empty",
                        )
                    )
            else:
                missing.append("finance.cash_flow_series")
        else:
            metrics = [
                _denied("revenue", filters),
                _denied("cash", filters),
                _denied("receivables", filters),
            ]
        sections.append(
            BiDomainSection(key="finance", title="Finance", metrics=metrics, series=series)
        )

    elif domain == "project":
        metrics = []
        rows = []
        if _can(user, "projects", "view"):
            try:
                portfolio = build_project_portfolio(db, exec_filters)
                m = _metric_base("project_exposure", filters)
                gaps = [
                    _decimal_to_number(p.funding_gap) or 0
                    for p in portfolio.projects
                    if p.funding_gap is not None
                ]
                if gaps:
                    m.value = sum(gaps)
                    m.state = "ready"
                else:
                    m.state = "unavailable"
                    m.reason = "funding_gap_not_available"
                    missing.append("projects.funding_gap")
                m.comparison = MetricComparisonOut(change_available=False, reason="snapshot_only")
                metrics.append(m)
                for row in portfolio.projects:
                    rows.append(
                        {
                            "project_id": str(row.project_id),
                            "project_name": row.project_name,
                            "status": row.status,
                            "health_status": row.health_status,
                            "funding_gap": str(row.funding_gap) if row.funding_gap is not None else None,
                            "drilldown": f"/dashboard/projects/{row.project_id}",
                        }
                    )
            except Exception:
                m = _metric_base("project_exposure", filters)
                m.state = "unavailable"
                m.reason = "project_portfolio_unavailable"
                metrics.append(m)
                missing.append("executive.project_portfolio")
                try:
                    db.rollback()
                except Exception:
                    pass
        else:
            metrics = [_denied("project_exposure", filters)]
        sections.append(
            BiDomainSection(key="project", title="Projects", metrics=metrics, rows=rows)
        )

    elif domain == "website":
        notes = [
            "Website analytics connector is not configured.",
            "Landing/form conversions reuse marketing conversion APIs when permitted.",
        ]
        metrics = []
        for key in ("website_sessions", "website_conversions"):
            m = _metric_base(key, filters)
            definition = get_metric(key)
            assert definition
            if not _can(user, definition.permission[0], definition.permission[1]):
                m = _denied(key, filters)
            elif key == "website_sessions":
                m.state = "unavailable"
                m.reason = "website_analytics_not_connected"
                missing.append("website.analytics")
            else:
                try:
                    from investhome_api.services.marketing import conversion_service as conv_svc

                    if hasattr(conv_svc, "count_conversions"):
                        m.value = conv_svc.count_conversions(  # type: ignore[attr-defined]
                            db,
                            date_from=exec_filters.date_from,
                            date_to=exec_filters.date_to,
                        )
                        m.state = "ready"
                    else:
                        m.state = "unavailable"
                        m.reason = "conversion_count_api_missing"
                        missing.append("marketing.conversions.count")
                except Exception:
                    m.state = "unavailable"
                    m.reason = "marketing_conversions_unavailable"
                    missing.append("marketing.conversions")
            m.comparison = MetricComparisonOut(
                change_available=False,
                reason="comparison_unavailable",
            )
            metrics.append(m)
        sections.append(
            BiDomainSection(key="website", title="Website", metrics=metrics, notes=notes)
        )

    elif domain == "operational":
        overview = build_overview(db, user, filters)
        metrics = [
            m
            for m in overview.metrics
            if m.key in ("open_risks", "overdue_actions", "automation_health")
        ]
        sections.append(
            BiDomainSection(key="operational", title="Operational", metrics=metrics)
        )
        missing = overview.missing_sources

    else:
        sections.append(
            BiDomainSection(
                key=domain,
                title=domain.title(),
                notes=[f"Unknown domain '{domain}'."],
            )
        )

    return BiDomainResponse(
        domain=domain,
        generated_at=now,
        filters=filters,
        sections=sections,
        missing_sources=sorted(set(missing)),
    )


def build_data_quality(db: Session, user: User) -> DataQualityResponse:
    findings: list[DataQualityFinding] = []
    freshness: dict[str, datetime | None] = {}
    now = _utcnow()

    overview = build_overview(db, user, BiFilters())
    for source in overview.missing_sources:
        findings.append(
            DataQualityFinding(
                key=f"missing:{source}",
                severity="warning",
                title=f"Source unavailable: {source}",
                description="Metric dependent on this source will show Unavailable until connected.",
                source=source,
            )
        )

    for m in overview.metrics:
        freshness[m.key] = m.freshness_at
        if m.state == "unavailable":
            findings.append(
                DataQualityFinding(
                    key=f"metric:{m.key}",
                    severity="warning",
                    title=f"{m.name} unavailable",
                    description=m.reason or "Source or comparison missing.",
                    source=m.source or "unknown",
                    metric_keys=[m.key],
                )
            )
        elif m.comparison and not m.comparison.change_available and m.state == "ready":
            findings.append(
                DataQualityFinding(
                    key=f"comparison:{m.key}",
                    severity="info",
                    title=f"{m.name} comparison unavailable",
                    description=m.comparison.reason or "Previous period not materialized.",
                    source=m.source or "unknown",
                    metric_keys=[m.key],
                )
            )

    if not any(f.key.startswith("missing:website") for f in findings):
        findings.append(
            DataQualityFinding(
                key="missing:website.analytics",
                severity="info",
                title="Website analytics not connected",
                description="Sessions/bounce/traffic sources require a website analytics connector.",
                source="website.analytics",
                metric_keys=["website_sessions"],
            )
        )

    freshness["_overview"] = now
    return DataQualityResponse(generated_at=now, findings=findings, freshness=freshness)


def _report_out(row: BiSavedReport) -> BiSavedReportOut:
    return BiSavedReportOut(
        id=row.id,
        owner_user_id=row.owner_user_id,
        name=row.name,
        description=row.description,
        domain=row.domain,
        chart_type=row.chart_type,
        metric_keys=list(row.metric_keys_json or []),
        filters=row.filters_json,
        layout=row.layout_json,
        is_shared=row.is_shared,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def list_saved_reports(db: Session, user: User) -> list[BiSavedReportOut]:
    rows = db.scalars(
        select(BiSavedReport)
        .where(
            or_(
                BiSavedReport.owner_user_id == user.id,
                BiSavedReport.is_shared.is_(True),
            )
        )
        .order_by(BiSavedReport.updated_at.desc())
    ).all()
    return [_report_out(r) for r in rows]


def create_saved_report(db: Session, user: User, payload: BiSavedReportCreate) -> BiSavedReportOut:
    unknown = [k for k in payload.metric_keys if k not in METRIC_REGISTRY]
    if unknown:
        raise ValueError(f"Unknown metric keys: {', '.join(unknown)}")
    row = BiSavedReport(
        owner_user_id=user.id,
        name=payload.name.strip(),
        description=payload.description,
        domain=payload.domain,
        chart_type=payload.chart_type,
        metric_keys_json=payload.metric_keys,
        filters_json=payload.filters,
        layout_json=payload.layout,
        is_shared=payload.is_shared,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _report_out(row)


def update_saved_report(
    db: Session, user: User, report_id: UUID, payload: BiSavedReportUpdate
) -> BiSavedReportOut:
    row = db.get(BiSavedReport, report_id)
    if row is None:
        raise LookupError("report_not_found")
    if row.owner_user_id != user.id and not _can(user, "analytics", "manage"):
        raise PermissionError("not_owner")
    data = payload.model_dump(exclude_unset=True)
    if "metric_keys" in data and data["metric_keys"] is not None:
        unknown = [k for k in data["metric_keys"] if k not in METRIC_REGISTRY]
        if unknown:
            raise ValueError(f"Unknown metric keys: {', '.join(unknown)}")
        row.metric_keys_json = data.pop("metric_keys")
    if "filters" in data:
        row.filters_json = data.pop("filters")
    if "layout" in data:
        row.layout_json = data.pop("layout")
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return _report_out(row)


def delete_saved_report(db: Session, user: User, report_id: UUID) -> None:
    row = db.get(BiSavedReport, report_id)
    if row is None:
        raise LookupError("report_not_found")
    if row.owner_user_id != user.id and not _can(user, "analytics", "manage"):
        raise PermissionError("not_owner")
    db.delete(row)
    db.commit()


def list_alert_thresholds(db: Session) -> list[BiAlertThresholdOut]:
    rows = db.scalars(select(BiAlertThreshold).order_by(BiAlertThreshold.metric_key)).all()
    return [
        BiAlertThresholdOut(
            id=r.id,
            metric_key=r.metric_key,
            name=r.name,
            operator=r.operator,
            threshold_value=r.threshold_value,
            severity=r.severity,
            enabled=r.enabled,
            filters=r.filters_json,
            created_by=r.created_by,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]


def create_alert_threshold(
    db: Session, user: User, payload: BiAlertThresholdCreate
) -> BiAlertThresholdOut:
    if payload.metric_key not in METRIC_REGISTRY:
        raise ValueError("unknown_metric")
    row = BiAlertThreshold(
        metric_key=payload.metric_key,
        name=payload.name.strip(),
        operator=payload.operator,
        threshold_value=payload.threshold_value,
        severity=payload.severity,
        enabled=payload.enabled,
        filters_json=payload.filters,
        created_by=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return BiAlertThresholdOut(
        id=row.id,
        metric_key=row.metric_key,
        name=row.name,
        operator=row.operator,
        threshold_value=row.threshold_value,
        severity=row.severity,
        enabled=row.enabled,
        filters=row.filters_json,
        created_by=row.created_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def export_metrics_csv(db: Session, user: User, filters: BiFilters, metric_keys: list[str]) -> str:
    overview = build_overview(db, user, filters)
    selected = (
        [m for m in overview.metrics if m.key in metric_keys] if metric_keys else overview.metrics
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "key",
            "name",
            "value",
            "state",
            "unit",
            "currency",
            "date_from",
            "date_to",
            "comparison_available",
            "change_pct",
            "source",
            "definition",
            "reason",
            "freshness_at",
            "exported_at",
            "exported_by",
        ]
    )
    exported_at = _utcnow().isoformat()
    for m in selected:
        writer.writerow(
            [
                m.key,
                m.name,
                m.value,
                m.state,
                m.unit,
                m.currency,
                m.date_from,
                m.date_to,
                m.comparison.change_available if m.comparison else False,
                m.comparison.change_pct if m.comparison else None,
                m.source,
                m.definition,
                m.reason,
                m.freshness_at.isoformat() if m.freshness_at else None,
                exported_at,
                user.email,
            ]
        )
    return buf.getvalue()
