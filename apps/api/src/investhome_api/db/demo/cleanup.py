"""Delete ONLY integrated-demo-marked records. Never touch user-created data."""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session

from investhome_api.db.demo.markers import INTEGRATED_DEMO_SOURCE, is_demo_metadata
from investhome_api.db.demo.safety import assert_demo_seed_allowed
from investhome_api.db.session import SessionLocal


def _ids_where_is_demo(session: Session, model: type) -> list[Any]:
    if not hasattr(model, "is_demo"):
        return []
    return list(session.scalars(select(model.id).where(model.is_demo.is_(True))).all())


def _ids_where_source(session: Session, model: type) -> list[Any]:
    if not hasattr(model, "source"):
        return []
    return list(
        session.scalars(select(model.id).where(model.source == INTEGRATED_DEMO_SOURCE)).all()
    )


def _ids_where_metadata(session: Session, model: type) -> list[Any]:
    if not hasattr(model, "metadata_json"):
        return []
    result = session.execute(select(model.id, model.metadata_json)).all()
    return [row_id for row_id, meta in result if is_demo_metadata(meta)]


def _demo_ids(session: Session, model: type) -> set[Any]:
    ids: set[Any] = set()
    ids.update(_ids_where_is_demo(session, model))
    ids.update(_ids_where_source(session, model))
    ids.update(_ids_where_metadata(session, model))
    return ids


def _delete_by_ids(session: Session, model: type, ids: set[Any]) -> int:
    if not ids:
        return 0
    result = session.execute(delete(model).where(model.id.in_(ids)))
    return int(result.rowcount or 0)


def cleanup_integrated_demo() -> dict[str, int]:
    """Remove demo-marked rows in FK-safe order. Returns deleted counts by entity."""
    assert_demo_seed_allowed()

    from investhome_api.models.analytics_bi import BiSavedReport
    from investhome_api.models.crm_activity import CrmActivity
    from investhome_api.models.crm_company import CrmCompany, CrmCompanyContact
    from investhome_api.models.crm_contact import CrmContact
    from investhome_api.models.finance import (
        FinanceTransaction,
        FinancialAccount,
        FundingCommitment,
        PaymentObligation,
        ProjectBudget,
    )
    from investhome_api.models.inventory import (
        Building,
        Floor,
        InventoryAsset,
        InventoryReservation,
        InventoryReservationEvent,
    )
    from investhome_api.models.lead import Lead
    from investhome_api.models.marketing import (
        MarketingAudience,
        MarketingCampaign,
        MarketingChannel,
        MarketingContentAsset,
        MarketingLeadContext,
        MarketingLeadSource,
        MarketingSegment,
    )
    from investhome_api.models.marketing_ai import MarketingAIInsight
    from investhome_api.models.marketing_attribution import (
        MarketingAttributionAllocation,
        MarketingAttributionHealth,
        MarketingAttributionJourney,
        MarketingAttributionModel,
        MarketingAttributionRule,
        MarketingTouchpoint,
    )
    from investhome_api.models.marketing_automation import MarketingAutomationWorkflow
    from investhome_api.models.marketing_lead_attribution import MarketingLeadAttribution
    from investhome_api.models.project import Project
    from investhome_api.models.sales import (
        OpportunityInventory,
        OpportunityProbabilityHistory,
        OpportunityProject,
        OpportunityTimeline,
        SalesOpportunity,
    )
    from investhome_api.models.user_auth import User, UserRole
    from investhome_api.models.work_item import WorkItem

    counts: dict[str, int] = {}

    with SessionLocal() as session:
        # --- Sales opportunity children ---
        opp_ids = _demo_ids(session, SalesOpportunity)
        if opp_ids:
            for child in (
                OpportunityInventory,
                OpportunityProject,
                OpportunityTimeline,
                OpportunityProbabilityHistory,
            ):
                result = session.execute(delete(child).where(child.opportunity_id.in_(opp_ids)))
                counts[child.__tablename__] = int(result.rowcount or 0)
            session.execute(
                update(SalesOpportunity)
                .where(SalesOpportunity.id.in_(opp_ids))
                .values(reservation_id=None)
            )

        # --- Reservations ---
        reservation_ids = _demo_ids(session, InventoryReservation)
        if reservation_ids:
            session.execute(
                update(InventoryAsset)
                .where(InventoryAsset.active_reservation_id.in_(reservation_ids))
                .values(active_reservation_id=None)
            )
            session.execute(
                update(SalesOpportunity)
                .where(SalesOpportunity.reservation_id.in_(reservation_ids))
                .values(reservation_id=None)
            )
            result = session.execute(
                delete(InventoryReservationEvent).where(
                    InventoryReservationEvent.reservation_id.in_(reservation_ids)
                )
            )
            counts["inventory_reservation_events"] = int(result.rowcount or 0)
            counts["inventory_reservations"] = _delete_by_ids(
                session, InventoryReservation, reservation_ids
            )

        counts["sales_opportunities"] = _delete_by_ids(session, SalesOpportunity, opp_ids)

        # --- Marketing attribution / lead links ---
        journey_ids = {
            row_id
            for row_id, meta in session.execute(
                select(MarketingAttributionJourney.id, MarketingAttributionJourney.metadata_json)
            ).all()
            if is_demo_metadata(meta)
        }
        if journey_ids:
            result = session.execute(
                delete(MarketingAttributionAllocation).where(
                    MarketingAttributionAllocation.journey_id.in_(journey_ids)
                )
            )
            counts["marketing_attribution_allocations"] = int(result.rowcount or 0)
            result = session.execute(
                delete(MarketingAttributionHealth).where(
                    MarketingAttributionHealth.journey_id.in_(journey_ids)
                )
            )
            counts["marketing_attribution_health"] = int(result.rowcount or 0)
            counts["marketing_attribution_journeys"] = _delete_by_ids(
                session, MarketingAttributionJourney, journey_ids
            )

        touch_ids = {
            row_id
            for row_id, meta in session.execute(
                select(MarketingTouchpoint.id, MarketingTouchpoint.metadata_json)
            ).all()
            if is_demo_metadata(meta)
        }
        counts["marketing_touchpoints"] = _delete_by_ids(session, MarketingTouchpoint, touch_ids)

        model_ids = {
            row_id
            for row_id, cfg in session.execute(
                select(MarketingAttributionModel.id, MarketingAttributionModel.config_json)
            ).all()
            if is_demo_metadata(cfg)
        }
        if model_ids:
            result = session.execute(
                delete(MarketingAttributionRule).where(
                    MarketingAttributionRule.model_id.in_(model_ids)
                )
            )
            counts["marketing_attribution_rules"] = int(result.rowcount or 0)
            counts["marketing_attribution_models"] = _delete_by_ids(
                session, MarketingAttributionModel, model_ids
            )

        # Lead attributions: no is_demo — match via utm_campaign / reason marker
        attr_ids = {
            row_id
            for row_id, reason in session.execute(
                select(MarketingLeadAttribution.id, MarketingLeadAttribution.attribution_reason)
            ).all()
            if isinstance(reason, str) and INTEGRATED_DEMO_SOURCE in reason
        }
        counts["marketing_lead_attributions"] = _delete_by_ids(
            session, MarketingLeadAttribution, attr_ids
        )

        for model, key in (
            (MarketingLeadContext, "marketing_lead_contexts"),
            (MarketingContentAsset, "marketing_content_assets"),
            (MarketingCampaign, "marketing_campaigns"),
            (MarketingAudience, "marketing_audiences"),
            (MarketingSegment, "marketing_segments"),
            (MarketingLeadSource, "marketing_lead_sources"),
            (MarketingChannel, "marketing_channels"),
        ):
            counts[key] = _delete_by_ids(session, model, _demo_ids(session, model))

        # AI insights via evidence_refs marker
        ai_ids = {
            row_id
            for row_id, refs in session.execute(
                select(MarketingAIInsight.id, MarketingAIInsight.evidence_refs)
            ).all()
            if isinstance(refs, list) and any(is_demo_metadata(item) for item in refs if isinstance(item, dict))
        }
        counts["marketing_ai_insights"] = _delete_by_ids(session, MarketingAIInsight, ai_ids)

        # Automation workflows via code prefix / trigger_json marker
        wf_ids = {
            row_id
            for row_id, code, trigger in session.execute(
                select(
                    MarketingAutomationWorkflow.id,
                    MarketingAutomationWorkflow.code,
                    MarketingAutomationWorkflow.trigger_json,
                )
            ).all()
            if (isinstance(code, str) and code.startswith("DEMO-AUTO-"))
            or is_demo_metadata(trigger)
        }
        counts["marketing_automation_workflows"] = _delete_by_ids(
            session, MarketingAutomationWorkflow, wf_ids
        )

        # BI reports via layout_json marker
        bi_ids = {
            row_id
            for row_id, layout in session.execute(
                select(BiSavedReport.id, BiSavedReport.layout_json)
            ).all()
            if is_demo_metadata(layout)
        }
        counts["bi_saved_reports"] = _delete_by_ids(session, BiSavedReport, bi_ids)

        # Work items via description marker
        work_ids = {
            row_id
            for row_id, desc in session.execute(select(WorkItem.id, WorkItem.description)).all()
            if isinstance(desc, str) and INTEGRATED_DEMO_SOURCE in desc
        }
        counts["work_items"] = _delete_by_ids(session, WorkItem, work_ids)

        # CRM activities (metadata_json)
        activity_ids = _demo_ids(session, CrmActivity)
        # CrmActivity has no is_demo — metadata only
        activity_ids |= {
            row_id
            for row_id, meta in session.execute(
                select(CrmActivity.id, CrmActivity.metadata_json)
            ).all()
            if is_demo_metadata(meta)
        }
        counts["crm_activities"] = _delete_by_ids(session, CrmActivity, activity_ids)

        contact_ids = _demo_ids(session, CrmContact)
        company_ids = _demo_ids(session, CrmCompany)
        # CrmCompany has no is_demo
        company_ids |= set(_ids_where_source(session, CrmCompany))
        company_ids |= set(_ids_where_metadata(session, CrmCompany))

        if contact_ids or company_ids:
            conds = []
            if contact_ids:
                conds.append(CrmCompanyContact.contact_id.in_(contact_ids))
            if company_ids:
                conds.append(CrmCompanyContact.company_id.in_(company_ids))
            result = session.execute(delete(CrmCompanyContact).where(or_(*conds)))
            counts["crm_company_contacts"] = int(result.rowcount or 0)

        counts["crm_contacts"] = _delete_by_ids(session, CrmContact, contact_ids)
        counts["crm_companies"] = _delete_by_ids(session, CrmCompany, company_ids)

        # Inventory added by integrated seed: only assets/floors/buildings with is_demo
        # whose related project still exists OR orphaned demo inventory from street projects.
        # Prefer metadata/system_code patterns over wiping all foundation Temple/UniLoft units.
        asset_ids = {
            row_id
            for row_id, system_code in session.execute(
                select(InventoryAsset.id, InventoryAsset.system_code)
            ).all()
            if isinstance(system_code, str) and "DEMO-INT-" in system_code
        }
        # Fallback: demo assets on street projects only
        street_project_ids = {
            row_id
            for row_id, code in session.execute(select(Project.id, Project.project_code)).all()
            if isinstance(code, str)
            and code.startswith(("PRJ-1307-", "PRJ-1313-", "PRJ-1331-", "PRJ-1627-", "PRJ-2319-"))
        }
        if street_project_ids:
            asset_ids |= {
                row_id
                for row_id in session.scalars(
                    select(InventoryAsset.id).where(
                        InventoryAsset.project_id.in_(street_project_ids),
                        InventoryAsset.is_demo.is_(True),
                    )
                ).all()
            }
        counts["inventory_assets"] = _delete_by_ids(session, InventoryAsset, asset_ids)

        # Only delete floors/buildings that become unused after asset cleanup on street projects
        floor_ids = set()
        building_ids = set()
        if street_project_ids:
            building_ids = {
                row_id
                for row_id in session.scalars(
                    select(Building.id).where(
                        Building.project_id.in_(street_project_ids),
                        Building.is_demo.is_(True),
                    )
                ).all()
            }
            if building_ids:
                floor_ids = {
                    row_id
                    for row_id in session.scalars(
                        select(Floor.id).where(
                            Floor.building_id.in_(building_ids),
                            Floor.is_demo.is_(True),
                        )
                    ).all()
                }
        counts["floors"] = _delete_by_ids(session, Floor, floor_ids)
        counts["buildings"] = _delete_by_ids(session, Building, building_ids)

        # Finance: only integrated-marked notes/source (finance seed uses is_demo without integrated source)
        for model, key in (
            (PaymentObligation, "payment_obligations"),
            (FundingCommitment, "funding_commitments"),
            (FinanceTransaction, "finance_transactions"),
            (ProjectBudget, "project_budgets"),
            (FinancialAccount, "financial_accounts"),
        ):
            # Keep foundation finance; integrated finance_links uses notes/source markers where present
            ids = set(_ids_where_source(session, model)) | set(_ids_where_metadata(session, model))
            counts[key] = _delete_by_ids(session, model, ids)
        # Foundation tables: only remove rows explicitly stamped by integrated demo seed.
        # Do NOT wipe classic is_demo foundation rows (empty-table guards cannot re-seed them).
        lead_ids = {
            row_id
            for row_id, notes in session.execute(select(Lead.id, Lead.notes)).all()
            if isinstance(notes, str) and INTEGRATED_DEMO_SOURCE in notes
        }
        counts["leads"] = _delete_by_ids(session, Lead, lead_ids)

        project_ids = {
            row_id
            for row_id, notes, code in session.execute(
                select(Project.id, Project.notes, Project.project_code)
            ).all()
            if (isinstance(notes, str) and INTEGRATED_DEMO_SOURCE in notes)
            or (
                isinstance(code, str)
                and code.startswith(("PRJ-1307-", "PRJ-1313-", "PRJ-1331-", "PRJ-1627-", "PRJ-2319-"))
            )
        }
        if project_ids:
            # Detach FKs before deleting street/integrated projects
            for model in (FinanceTransaction, PaymentObligation, FundingCommitment, ProjectBudget):
                if hasattr(model, "project_id"):
                    session.execute(
                        update(model)
                        .where(model.project_id.in_(project_ids))
                        .values(project_id=None)
                    )
        counts["projects"] = _delete_by_ids(session, Project, project_ids)

        # Extended demo users only (keep classic foundation demo accounts)
        extended_emails = {
            "marketing@investhome.demo",
            "operations@investhome.demo",
            "partner@investhome.demo",
            "assistant@investhome.demo",
        }
        user_ids = {
            row_id
            for row_id, email in session.execute(select(User.id, User.email)).all()
            if isinstance(email, str) and email.lower() in extended_emails
        }
        if user_ids:
            result = session.execute(delete(UserRole).where(UserRole.user_id.in_(user_ids)))
            counts["user_roles"] = int(result.rowcount or 0)
            counts["users"] = _delete_by_ids(session, User, user_ids)

        session.commit()

    return {k: v for k, v in counts.items() if v}


__all__ = ["cleanup_integrated_demo"]
