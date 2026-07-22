"""Validate integrated demo data against minimum entity counts."""

from __future__ import annotations

from sqlalchemy import func, select

from investhome_api.db.demo.markers import INTEGRATED_DEMO_SOURCE, is_demo_metadata
from investhome_api.db.session import SessionLocal

# entity_key -> minimum total count expected after integrated demo seed
MINIMUMS: dict[str, int] = {
    "users": 11,
    "projects": 10,
    "inventory_assets": 30,
    "crm_contacts": 20,
    "crm_companies": 10,
    "crm_activities": 20,
    "crm_notes": 10,
    "crm_tasks": 10,
    "leads": 20,
    "sales_opportunities": 15,
    "bi_saved_reports": 10,
    "marketing_ai_insights": 10,
}


def _count(session, model) -> int:
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


def collect_counts() -> dict[str, int]:
    from investhome_api.models.analytics_bi import BiSavedReport
    from investhome_api.models.crm_activity import CrmActivity, CrmActivityType
    from investhome_api.models.crm_company import CrmCompany
    from investhome_api.models.crm_contact import CrmContact
    from investhome_api.models.inventory import InventoryAsset
    from investhome_api.models.lead import Lead
    from investhome_api.models.marketing import (
        MarketingAudience,
        MarketingCampaign,
        MarketingContentAsset,
        MarketingLeadSource,
        MarketingSegment,
    )
    from investhome_api.models.marketing_ai import MarketingAIInsight
    from investhome_api.models.marketing_automation import MarketingAutomationWorkflow
    from investhome_api.models.project import Project
    from investhome_api.models.sales import SalesOpportunity
    from investhome_api.models.user_auth import User
    from investhome_api.models.work_item import WorkItem

    with SessionLocal() as session:
        notes = int(
            session.scalar(
                select(func.count()).select_from(CrmActivity).where(
                    CrmActivity.activity_type == CrmActivityType.NOTE
                )
            )
            or 0
        )
        tasks = int(
            session.scalar(
                select(func.count()).select_from(CrmActivity).where(
                    CrmActivity.activity_type == CrmActivityType.TASK
                )
            )
            or 0
        )
        bi_demo = 0
        for layout in session.scalars(select(BiSavedReport.layout_json)).all():
            if is_demo_metadata(layout):
                bi_demo += 1
        ai_demo = 0
        for refs in session.scalars(select(MarketingAIInsight.evidence_refs)).all():
            if isinstance(refs, list) and any(
                is_demo_metadata(item) for item in refs if isinstance(item, dict)
            ):
                ai_demo += 1
        work_demo = 0
        for desc in session.scalars(select(WorkItem.description)).all():
            if isinstance(desc, str) and INTEGRATED_DEMO_SOURCE in desc:
                work_demo += 1
        auto_demo = int(
            session.scalar(
                select(func.count()).select_from(MarketingAutomationWorkflow).where(
                    MarketingAutomationWorkflow.code.like("DEMO-AUTO-%")
                )
            )
            or 0
        )

        return {
            "users": _count(session, User),
            "projects": _count(session, Project),
            "inventory_assets": _count(session, InventoryAsset),
            "crm_contacts": _count(session, CrmContact),
            "crm_companies": _count(session, CrmCompany),
            "crm_activities": _count(session, CrmActivity),
            "crm_notes": notes,
            "crm_tasks": tasks,
            "leads": _count(session, Lead),
            "sales_opportunities": _count(session, SalesOpportunity),
            "marketing_campaigns": _count(session, MarketingCampaign),
            "marketing_lead_sources": _count(session, MarketingLeadSource),
            "marketing_audiences": _count(session, MarketingAudience),
            "marketing_segments": _count(session, MarketingSegment),
            "marketing_content_assets": _count(session, MarketingContentAsset),
            "bi_saved_reports": bi_demo or _count(session, BiSavedReport),
            "marketing_ai_insights": ai_demo or _count(session, MarketingAIInsight),
            "work_items_demo": work_demo,
            "automation_workflows_demo": auto_demo,
        }


def validate_integrated_demo(*, print_report: bool = True) -> int:
    """Assert minimums; print report; return process exit code (0=ok, 1=fail)."""
    counts = collect_counts()
    failures: list[str] = []
    skipped_notes: list[str] = []

    # Document domains that rely on JSON markers rather than is_demo
    skipped_notes.append(
        "BiSavedReport / MarketingAIInsight / WorkItem / CrmActivity / CrmCompany "
        "use metadata_json, layout_json, evidence_refs, or source markers "
        f"(source={INTEGRATED_DEMO_SOURCE}) because is_demo is absent."
    )

    if print_report:
        print("=== Integrated demo validation ===")
        for key, value in sorted(counts.items()):
            minimum = MINIMUMS.get(key)
            if minimum is None:
                print(f"  {key}: {value}")
            else:
                status = "OK" if value >= minimum else "FAIL"
                print(f"  {key}: {value} (min {minimum}) [{status}]")
        for note in skipped_notes:
            print(f"  note: {note}")

    for key, minimum in MINIMUMS.items():
        actual = counts.get(key, 0)
        if actual < minimum:
            failures.append(f"{key}: {actual} < {minimum}")

    if print_report:
        if failures:
            print("RESULT: FAIL")
            for item in failures:
                print(f"  - {item}")
        else:
            print("RESULT: PASS")

    return 1 if failures else 0
