"""Central semantic metric registry for Business Intelligence (P9).

Every BI metric must be defined here before it can appear in dashboards,
report builder, exports, or alert thresholds. Unrestricted SQL is not allowed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

MetricDomain = Literal[
    "executive",
    "sales",
    "marketing",
    "investor",
    "finance",
    "project",
    "website",
    "operational",
]
MetricUnit = Literal["count", "currency", "percent", "ratio", "days", "score", "text"]
ComparisonMode = Literal["period_over_period", "none"]
CertificationStatus = Literal["draft", "certified", "deprecated"]

# G14 certified subset — frozen definitions; do not silently redefine.
CERTIFIED_METRIC_KEYS: frozenset[str] = frozenset(
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


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    key: str
    name: str
    description: str
    formula: str
    source: str
    domain: MetricDomain
    unit: MetricUnit
    currency_aware: bool
    permission: tuple[str, str]
    supports_comparison: bool
    freshness_seconds: int
    drilldown_path: str
    filters: tuple[str, ...]
    certification_status: CertificationStatus = "draft"
    grain: str = "see formula"
    reporting_timezone: str = "UTC"


METRIC_REGISTRY: dict[str, MetricDefinition] = {
    "revenue": MetricDefinition(
        key="revenue",
        name="Revenue",
        description="Recognized income in the selected period from finance transactions.",
        formula="SUM(finance_transactions.amount WHERE type IN income AND status=posted AND date in range)",
        source="finance.transactions + executive.financial_overview",
        domain="finance",
        unit="currency",
        currency_aware=True,
        permission=("finance", "view"),
        supports_comparison=True,
        freshness_seconds=300,
        drilldown_path="/dashboard/finance?tab=transactions",
        filters=("date_from", "date_to", "currency", "project_id"),
    ),
    "cash": MetricDefinition(
        key="cash",
        name="Available Cash",
        description="Sum of available balances across active financial accounts.",
        formula="SUM(financial_accounts.available_balance WHERE status=active)",
        source="finance.stats / executive.summary.available_cash",
        domain="finance",
        unit="currency",
        currency_aware=True,
        permission=("finance", "view"),
        supports_comparison=True,
        freshness_seconds=300,
        drilldown_path="/dashboard/finance?tab=accounts",
        filters=("currency",),
    ),
    "receivables": MetricDefinition(
        key="receivables",
        name="Receivables",
        description="Open payment obligations owed to the company.",
        formula="SUM(payment_obligations.amount WHERE status IN open/overdue AND direction=inbound)",
        source="finance.payment_obligations",
        domain="finance",
        unit="currency",
        currency_aware=True,
        permission=("finance", "view"),
        supports_comparison=True,
        freshness_seconds=300,
        drilldown_path="/dashboard/finance?tab=obligations",
        filters=("date_from", "date_to", "currency", "project_id", "status"),
    ),
    "pipeline": MetricDefinition(
        key="pipeline",
        name="Sales Pipeline",
        description="Open opportunity expected revenue.",
        formula="SUM(sales_opportunities.expected_revenue WHERE stage NOT IN closed)",
        source="sales.opportunities.dashboard/metrics",
        domain="sales",
        unit="currency",
        currency_aware=True,
        permission=("sales", "view"),
        supports_comparison=True,
        freshness_seconds=180,
        drilldown_path="/dashboard/sales",
        filters=("date_from", "date_to", "assigned_to", "project_id", "status"),
    ),
    "closed_sales": MetricDefinition(
        key="closed_sales",
        name="Closed Sales",
        description="Won opportunities in the selected period.",
        formula="COUNT(sales_opportunities WHERE stage=won AND close_date in range)",
        source="sales.opportunities.dashboard/metrics",
        domain="sales",
        unit="count",
        currency_aware=False,
        permission=("sales", "view"),
        supports_comparison=True,
        freshness_seconds=180,
        drilldown_path="/dashboard/sales?stage=won",
        filters=("date_from", "date_to", "assigned_to", "project_id"),
    ),
    "active_investors": MetricDefinition(
        key="active_investors",
        name="Active Investors",
        description="Investors with active status.",
        formula="COUNT(investors WHERE status=active AND archived_at IS NULL)",
        source="executive.investor_overview / investors",
        domain="investor",
        unit="count",
        currency_aware=False,
        permission=("investors", "view"),
        supports_comparison=True,
        freshness_seconds=600,
        drilldown_path="/dashboard/investors?status=active",
        filters=("status",),
    ),
    "marketing_spend": MetricDefinition(
        key="marketing_spend",
        name="Marketing Spend",
        description="Attributed campaign spend in the selected period.",
        formula="SUM(campaign_spend WHERE date in range)",
        source="marketing.performance.overview",
        domain="marketing",
        unit="currency",
        currency_aware=True,
        permission=("marketing", "view_dashboard"),
        supports_comparison=True,
        freshness_seconds=600,
        drilldown_path="/workspaces/marketing/dashboard/performance",
        filters=("date_from", "date_to", "campaign_id", "currency"),
    ),
    "marketing_roi": MetricDefinition(
        key="marketing_roi",
        name="Marketing ROI",
        description="Estimated ROI when spend and attributed conversion value are both available.",
        formula="(attributed_value - spend) / spend WHEN both available; else unavailable",
        source="marketing.performance.overview",
        domain="marketing",
        unit="ratio",
        currency_aware=False,
        permission=("marketing", "view_dashboard"),
        supports_comparison=True,
        freshness_seconds=600,
        drilldown_path="/workspaces/marketing/dashboard/performance",
        filters=("date_from", "date_to", "campaign_id"),
    ),
    "project_exposure": MetricDefinition(
        key="project_exposure",
        name="Project Exposure",
        description="Aggregate remaining budget / funding gap across active projects.",
        formula="SUM(funding_gap OR budget_remaining) for active projects",
        source="executive.project_portfolio / project budgets",
        domain="project",
        unit="currency",
        currency_aware=True,
        permission=("projects", "view"),
        supports_comparison=True,
        freshness_seconds=600,
        drilldown_path="/dashboard/projects",
        filters=("project_id", "currency", "status"),
    ),
    "open_risks": MetricDefinition(
        key="open_risks",
        name="Open Risks",
        description="Critical and warning attention items requiring action.",
        formula="COUNT(executive.attention WHERE severity IN critical,warning)",
        source="executive.attention",
        domain="operational",
        unit="count",
        currency_aware=False,
        permission=("executive", "view"),
        supports_comparison=False,
        freshness_seconds=120,
        drilldown_path="/dashboard/executive",
        filters=("project_id", "status"),
    ),
    "overdue_actions": MetricDefinition(
        key="overdue_actions",
        name="Overdue Actions",
        description="Overdue payment obligations and past-due follow-ups.",
        formula="COUNT(overdue obligations) + COUNT(opportunities with past next_action_date)",
        source="finance.obligations + sales.dashboard/metrics.no_follow_up",
        domain="operational",
        unit="count",
        currency_aware=False,
        permission=("executive", "view"),
        supports_comparison=True,
        freshness_seconds=180,
        drilldown_path="/dashboard/activity",
        filters=("date_from", "date_to", "assigned_to", "project_id"),
    ),
    "automation_health": MetricDefinition(
        key="automation_health",
        name="Automation Health",
        description="Overall automation center health score/status.",
        formula="automation.overview.health.status",
        source="automation.overview",
        domain="operational",
        unit="score",
        currency_aware=False,
        permission=("automation", "view"),
        supports_comparison=False,
        freshness_seconds=120,
        drilldown_path="/dashboard/settings",
        filters=(),
    ),
    "website_sessions": MetricDefinition(
        key="website_sessions",
        name="Website Sessions",
        description="Public site sessions. Requires website analytics connector.",
        formula="COUNT(sessions) from website analytics provider",
        source="website.analytics (not connected)",
        domain="website",
        unit="count",
        currency_aware=False,
        permission=("analytics", "view"),
        supports_comparison=True,
        freshness_seconds=3600,
        drilldown_path="/dashboard/analytics/website",
        filters=("date_from", "date_to"),
    ),
    "website_conversions": MetricDefinition(
        key="website_conversions",
        name="Website Conversions",
        description="Form/landing conversions attributed to the public site.",
        formula="COUNT(marketing form submissions + landing conversions) when tracked",
        source="marketing.conversions / landing pages",
        domain="website",
        unit="count",
        currency_aware=False,
        permission=("marketing", "view_conversions"),
        supports_comparison=True,
        freshness_seconds=600,
        drilldown_path="/workspaces/marketing/forms",
        filters=("date_from", "date_to", "campaign_id", "lead_source"),
    ),
    "lead_volume": MetricDefinition(
        key="lead_volume",
        name="Lead Volume",
        description="New leads created in the selected period.",
        formula="COUNT(leads WHERE created_at in range)",
        source="executive.leads_pipeline / leads",
        domain="sales",
        unit="count",
        currency_aware=False,
        permission=("leads", "view"),
        supports_comparison=True,
        freshness_seconds=180,
        drilldown_path="/dashboard/leads",
        filters=("date_from", "date_to", "lead_source", "assigned_to", "status"),
    ),
    "attribution_coverage": MetricDefinition(
        key="attribution_coverage",
        name="Attribution Coverage",
        description="Share of leads with first/last/multi-touch attribution vs unattributed.",
        formula="attributed_leads / total_leads; labels only — no invented certainty",
        source="marketing.performance.attributions",
        domain="marketing",
        unit="percent",
        currency_aware=False,
        permission=("marketing", "view_attribution"),
        supports_comparison=False,
        freshness_seconds=600,
        drilldown_path="/workspaces/marketing/attribution",
        filters=("date_from", "date_to", "campaign_id", "lead_source"),
    ),
    "knowledge_documents": MetricDefinition(
        key="knowledge_documents",
        name="Knowledge Documents",
        description="Active latest-version documents in the Knowledge Hub library.",
        formula="COUNT(documents WHERE is_latest_version AND archived_at IS NULL)",
        source="knowledge.overview.total_documents",
        domain="operational",
        unit="count",
        currency_aware=False,
        permission=("knowledge", "view"),
        supports_comparison=True,
        freshness_seconds=300,
        drilldown_path="/dashboard/knowledge/documents",
        filters=("date_from", "date_to", "folder", "category_code"),
    ),
    "knowledge_awaiting_review": MetricDefinition(
        key="knowledge_awaiting_review",
        name="Knowledge Awaiting Review",
        description="Open Knowledge Hub review queue items.",
        formula="COUNT(knowledge_review_items WHERE status IN open/in_progress)",
        source="knowledge.overview.awaiting_review",
        domain="operational",
        unit="count",
        currency_aware=False,
        permission=("knowledge", "review"),
        supports_comparison=False,
        freshness_seconds=180,
        drilldown_path="/dashboard/knowledge/review",
        filters=("reason", "priority"),
    ),
    "knowledge_expiring": MetricDefinition(
        key="knowledge_expiring",
        name="Knowledge Expiring Soon",
        description="Documents with expiration within the configured alert window.",
        formula="COUNT(documents WHERE expiration_date within alert window)",
        source="knowledge.overview.expiring_soon",
        domain="operational",
        unit="count",
        currency_aware=False,
        permission=("knowledge", "view"),
        supports_comparison=False,
        freshness_seconds=600,
        drilldown_path="/dashboard/knowledge/retention",
        filters=("days"),
    ),
}


def _with_certification(m: MetricDefinition) -> MetricDefinition:
    if m.key in CERTIFIED_METRIC_KEYS and m.certification_status != "certified":
        return MetricDefinition(
            key=m.key,
            name=m.name,
            description=m.description,
            formula=m.formula,
            source=m.source,
            domain=m.domain,
            unit=m.unit,
            currency_aware=m.currency_aware,
            permission=m.permission,
            supports_comparison=m.supports_comparison,
            freshness_seconds=m.freshness_seconds,
            drilldown_path=m.drilldown_path,
            filters=m.filters,
            certification_status="certified",
            grain=m.grain,
            reporting_timezone=m.reporting_timezone,
        )
    return m


def list_metrics(*, domain: str | None = None) -> list[MetricDefinition]:
    items = [_with_certification(m) for m in METRIC_REGISTRY.values()]
    if domain:
        items = [m for m in items if m.domain == domain]
    return sorted(items, key=lambda m: (m.domain, m.key))


def get_metric(key: str) -> MetricDefinition | None:
    m = METRIC_REGISTRY.get(key)
    return _with_certification(m) if m else None
