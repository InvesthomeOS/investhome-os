"""Ops work items, automation stubs, BI reports, AI insights — no live AI calls."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.db.demo.markers import DEMO_METADATA, INTEGRATED_DEMO_SOURCE
from investhome_api.db.session import SessionLocal
from investhome_api.models.analytics_bi import BiSavedReport
from investhome_api.models.marketing_ai import (
    AIConfidenceLevel,
    AIInsightCategory,
    AIInsightSeverity,
    MarketingAIInsight,
)
from investhome_api.models.user_auth import User

BI_REPORTS = [
    ("Executive KPI Snapshot", "executive", "kpi", ["pipeline_value", "active_projects"]),
    ("Sales Funnel Overview", "sales", "funnel", ["leads_new", "opportunities_open"]),
    ("Project Portfolio Health", "projects", "table", ["budget_variance", "schedule_risk"]),
    ("Marketing Lead Volume", "marketing", "trend", ["leads_by_source", "cpl"]),
    ("Investor Capital Status", "investors", "kpi", ["equity_raised", "commitments"]),
    ("Inventory Availability", "inventory", "table", ["units_available", "units_reserved"]),
    ("Finance Cash Position", "finance", "kpi", ["cash_balance", "obligations_due"]),
    ("CRM Engagement Score", "crm", "trend", ["activities_week", "follow_ups_overdue"]),
    ("Construction Progress", "projects", "chart", ["pct_complete", "open_rfis"]),
    ("Board Monthly Brief", "executive", "dashboard", ["revenue", "roi", "pipeline"]),
    ("Partner Channel Report", "marketing", "table", ["partner_leads", "conversion_rate"]),
    ("Ops Workload Board", "operations", "kanban", ["open_tasks", "overdue_tasks"]),
]

AI_INSIGHTS = [
    ("Temple Meta CPL trending down", AIInsightCategory.CAMPAIGN, AIInsightSeverity.INFO),
    ("UniLoft organic traffic spike", AIInsightCategory.CHANNEL, AIInsightSeverity.INFO),
    ("NoMa form conversion dip", AIInsightCategory.FORM, AIInsightSeverity.WARNING),
    ("H Street audience overlap high", AIInsightCategory.AUDIENCE, AIInsightSeverity.INFO),
    ("Budget pacing ahead on retargeting", AIInsightCategory.BUDGET, AIInsightSeverity.WARNING),
    ("Turkey leads converting faster", AIInsightCategory.COUNTRY, AIInsightSeverity.INFO),
    ("Landing page bounce elevated", AIInsightCategory.LANDING_PAGE, AIInsightSeverity.WARNING),
    ("Creative fatigue on Temple ads", AIInsightCategory.CREATIVE, AIInsightSeverity.WARNING),
    ("Pipeline revenue forecast up", AIInsightCategory.REVENUE, AIInsightSeverity.INFO),
    ("Automation welcome journey stalled", AIInsightCategory.AUTOMATION, AIInsightSeverity.CRITICAL),
    ("Campus awareness underperforming", AIInsightCategory.PROJECT, AIInsightSeverity.INFO),
    ("General demo insight baseline", AIInsightCategory.GENERAL, AIInsightSeverity.INFO),
]

AUTOMATION_WORKFLOWS = [
    ("DEMO-AUTO-WELCOME", "Demo Welcome Journey"),
    ("DEMO-AUTO-NURTURE", "Demo Buyer Nurture"),
    ("DEMO-AUTO-ALERT", "Demo Lead Score Alert"),
]


def seed_ops_reports_ai(session: Session | None = None) -> dict[str, int]:
    own_session = session is None
    session = session or SessionLocal()
    counts = {"work_items": 0, "workflows": 0, "bi_reports": 0, "ai_insights": 0}
    try:
        superadmin = session.scalar(
            select(User).where(User.email == "superadmin@investhome.demo")
        )
        ops_user = session.scalar(select(User).where(User.email == "operations@investhome.demo"))
        owner_id = superadmin.id if superadmin else (ops_user.id if ops_user else None)
        if owner_id is None:
            any_user = session.scalar(select(User).where(User.is_demo.is_(True)).limit(1))
            owner_id = any_user.id if any_user else None
        if owner_id is None:
            return counts

        for name, domain, chart, metrics in BI_REPORTS:
            existing = session.scalar(
                select(BiSavedReport).where(
                    BiSavedReport.owner_user_id == owner_id,
                    BiSavedReport.name == name,
                )
            )
            if existing is not None:
                if not is_demo_metadata_safe(existing.layout_json):
                    existing.layout_json = {**(existing.layout_json or {}), **DEMO_METADATA}
                continue
            session.add(
                BiSavedReport(
                    owner_user_id=owner_id,
                    name=name,
                    description=f"Demo BI report — {INTEGRATED_DEMO_SOURCE}",
                    domain=domain,
                    chart_type=chart,
                    metric_keys_json=metrics,
                    filters_json={"demo_seed": True},
                    layout_json=dict(DEMO_METADATA),
                    is_shared=True,
                )
            )
            counts["bi_reports"] += 1

        session.flush()

        for title, category, severity in AI_INSIGHTS:
            existing = None
            for row in session.scalars(
                select(MarketingAIInsight).where(MarketingAIInsight.title == title)
            ).all():
                refs = row.evidence_refs or []
                if isinstance(refs, list) and any(
                    isinstance(r, dict) and r.get("source") == INTEGRATED_DEMO_SOURCE for r in refs
                ):
                    existing = row
                    break
            if existing is not None:
                continue
            session.add(
                MarketingAIInsight(
                    category=category,
                    severity=severity,
                    title=title,
                    summary=(
                        f"Static demo insight (no live AI). Seeded by {INTEGRATED_DEMO_SOURCE}."
                    ),
                    confidence=AIConfidenceLevel.MEDIUM,
                    evidence_refs=[dict(DEMO_METADATA)],
                    entity_type="demo",
                    is_active=True,
                )
            )
            counts["ai_insights"] += 1

        session.flush()

        try:
            from investhome_api.models.marketing_automation import (
                MarketingAutomationWorkflow,
                MarketingAutomationWorkflowStatus,
            )

            for code, name in AUTOMATION_WORKFLOWS:
                existing = session.scalar(
                    select(MarketingAutomationWorkflow).where(
                        MarketingAutomationWorkflow.code == code
                    )
                )
                if existing is not None:
                    continue
                session.add(
                    MarketingAutomationWorkflow(
                        name=name,
                        code=code,
                        description=f"Demo automation stub — {INTEGRATED_DEMO_SOURCE}",
                        status=MarketingAutomationWorkflowStatus.DRAFT,
                        trigger_json={**DEMO_METADATA, "event": "lead_created"},
                        conditions_json=[{"field": "is_demo", "eq": True}],
                        actions_json=[{"type": "notify", "channel": "email"}],
                        owner_user_id=owner_id,
                        created_by_user_id=owner_id,
                        timezone="America/New_York",
                        is_journey=True,
                    )
                )
                counts["workflows"] += 1
            session.flush()
        except Exception as exc:  # noqa: BLE001
            print(f"Skipping demo automation workflows: {exc}")
            session.expire_all()

        try:
            from investhome_api.models import sales_proposal as _sales_proposal  # noqa: F401
            from investhome_api.models.lead import Lead
            from investhome_api.models.project import Project
            from investhome_api.models.work_item import (
                WorkItem,
                WorkItemPriority,
                WorkItemStatus,
                WorkItemType,
            )

            now = datetime.now(UTC)
            leads = list(session.scalars(select(Lead).where(Lead.is_demo.is_(True)).limit(10)).all())
            projects = list(
                session.scalars(select(Project).where(Project.is_demo.is_(True)).limit(5)).all()
            )
            work_specs = [
                ("Call Ayşe Karaca — Temple interest", WorkItemType.CALL),
                ("Site visit UniLoft unit 2A", WorkItemType.SITE_VISIT),
                ("Prepare proposal for Natalie Brooks", WorkItemType.PROPOSAL_FOLLOW_UP),
                ("Follow up reservation deposit — Amelia", WorkItemType.RESERVATION_FOLLOW_UP),
                ("Schedule lender intro — Potomac", WorkItemType.MEETING),
                ("Document request — Horizon Law", WorkItemType.DOCUMENT_REQUEST),
                ("Contract follow-up Priya Nair", WorkItemType.CONTRACT_FOLLOW_UP),
                ("Ops checklist — 1313 facade inspection", WorkItemType.TASK),
                ("Partner sync — Bosporus Ventures", WorkItemType.FOLLOW_UP),
                ("Closing handoff Hannah Okafor", WorkItemType.CLOSING_FOLLOW_UP),
            ]
            for title, wtype in work_specs:
                existing = session.scalar(
                    select(WorkItem).where(
                        WorkItem.title == title,
                        WorkItem.description.contains(INTEGRATED_DEMO_SOURCE),
                    )
                )
                if existing is not None:
                    continue
                lead = leads[counts["work_items"] % len(leads)] if leads else None
                project = projects[counts["work_items"] % len(projects)] if projects else None
                session.add(
                    WorkItem(
                        title=title,
                        description=f"Demo work item seeded by {INTEGRATED_DEMO_SOURCE}.",
                        work_item_type=wtype,
                        status=WorkItemStatus.OPEN,
                        priority=WorkItemPriority.MEDIUM,
                        assigned_user_id=ops_user.id if ops_user else owner_id,
                        created_by_user_id=owner_id,
                        due_at=now + timedelta(days=5),
                        lead_id=lead.id if lead else None,
                        project_id=project.id if project else None,
                    )
                )
                counts["work_items"] += 1
            session.flush()
        except Exception as exc:  # noqa: BLE001
            print(f"Skipping demo work items: {exc}")
            session.expire_all()

        if own_session:
            session.commit()
        else:
            session.flush()
        return counts
    finally:
        if own_session:
            session.close()


def is_demo_metadata_safe(value: object | None) -> bool:
    from investhome_api.db.demo.markers import is_demo_metadata

    return is_demo_metadata(value)
