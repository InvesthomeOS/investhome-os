"""Remove ONLY deterministically marked CRM/Sales demo records.

Never deletes Bitrix imports, real agreements, or unmarked manually created rows.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from investhome_api.db.demo.markers import INTEGRATED_DEMO_SOURCE, is_demo_metadata
from investhome_api.models.crm_activity import CrmActivity, CrmActivityEntityType
from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_company import CrmCompany, CrmCompanyContact
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.lead import Lead
from investhome_api.models.sales import (
    OpportunityInventory,
    OpportunityProbabilityHistory,
    OpportunityProject,
    OpportunityTimeline,
    SalesOpportunity,
)

KNOWN_DEMO_OPPORTUNITY_CODES = frozenset({"OPP-20260716-0001"})
KNOWN_DEMO_PARTY_NAMES = frozenset({"api verify lead"})



@dataclass
class CrmDemoCleanupReport:
    dry_run: bool
    planned: dict[str, int]
    deleted: dict[str, int]
    preserved: dict[str, int]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def format_console(self) -> str:
        payload = self.to_dict()
        lines = ["CRM DEMO CLEANUP " + ("DRY-RUN" if self.dry_run else "COMMIT"), ""]
        for key, value in payload.items():
            if key == "notes":
                continue
            lines.append(f"{key}: {value}")
        if self.notes:
            lines.append("notes:")
            lines.extend(f"  - {note}" for note in self.notes)
        return "\n".join(lines)


def _ids_where_is_demo(session: Session, model: type) -> set[Any]:
    if not hasattr(model, "is_demo"):
        return set()
    return set(session.scalars(select(model.id).where(model.is_demo.is_(True))).all())


def _ids_where_source(session: Session, model: type) -> set[Any]:
    if not hasattr(model, "source"):
        return set()
    return set(
        session.scalars(select(model.id).where(model.source == INTEGRATED_DEMO_SOURCE)).all()
    )


def _ids_where_metadata(session: Session, model: type) -> set[Any]:
    if not hasattr(model, "metadata_json"):
        return set()
    result = session.execute(select(model.id, model.metadata_json)).all()
    return {row_id for row_id, meta in result if is_demo_metadata(meta)}


def _is_bitrix_opportunity(opportunity: SalesOpportunity) -> bool:
    code = (opportunity.opportunity_code or "").upper()
    if code.startswith("BITRIX"):
        return True
    source = (opportunity.source or "").lower()
    return "bitrix" in source


def _known_seed_opportunity_ids(session: Session) -> set[Any]:
    """QA/seed opportunities identified by code or party name. Never Bitrix history."""
    opportunities = list(session.scalars(select(SalesOpportunity)).all())
    lead_ids = {item.lead_id for item in opportunities if item.lead_id}
    leads: dict[Any, Lead] = {}
    if lead_ids:
        for lead in session.scalars(select(Lead).where(Lead.id.in_(lead_ids))).all():
            leads[lead.id] = lead
    found: set[Any] = set()
    for opportunity in opportunities:
        if _is_bitrix_opportunity(opportunity):
            continue
        code = opportunity.opportunity_code or ""
        if code in KNOWN_DEMO_OPPORTUNITY_CODES or code.startswith("OPP-DEMO-"):
            found.add(opportunity.id)
            continue
        lead = leads.get(opportunity.lead_id) if opportunity.lead_id else None
        if lead and (lead.full_name or "").strip().casefold() in KNOWN_DEMO_PARTY_NAMES:
            found.add(opportunity.id)
    return found


def _demo_ids(session: Session, model: type) -> set[Any]:
    return _ids_where_is_demo(session, model) | _ids_where_source(session, model) | _ids_where_metadata(
        session, model
    )


def _delete_by_ids(session: Session, model: type, ids: set[Any]) -> int:
    if not ids:
        return 0
    result = session.execute(delete(model).where(model.id.in_(ids)))
    return int(result.rowcount or 0)


def plan_crm_demo_cleanup(db: Session) -> dict[str, int]:
    contact_ids = _demo_ids(db, CrmContact)
    company_ids = _demo_ids(db, CrmCompany)
    activity_ids = _demo_ids(db, CrmActivity)
    lead_ids = _ids_where_is_demo(db, Lead)
    lead_ids |= {
        row_id
        for row_id, notes in db.execute(select(Lead.id, Lead.notes)).all()
        if isinstance(notes, str) and INTEGRATED_DEMO_SOURCE in notes
    }
    lead_ids |= {
        row_id
        for row_id, name in db.execute(select(Lead.id, Lead.full_name)).all()
        if (name or "").strip().casefold() in KNOWN_DEMO_PARTY_NAMES
    }
    opp_ids = _demo_ids(db, SalesOpportunity) | _known_seed_opportunity_ids(db)
    return {
        "crm_contacts": len(contact_ids),
        "crm_companies": len(company_ids),
        "crm_activities": len(activity_ids),
        "leads": len(lead_ids),
        "sales_opportunities": len(opp_ids),
    }


def cleanup_crm_demo_records(db: Session, *, dry_run: bool) -> CrmDemoCleanupReport:
    before = {
        "crm_contacts": db.query(CrmContact).count(),
        "crm_contacts_bitrix": db.query(CrmContact)
        .filter(func.lower(CrmContact.source) == "bitrix")
        .count(),
        "leads": db.query(Lead).count(),
        "sales_opportunities": db.query(SalesOpportunity).count(),
        "crm_activities": db.query(CrmActivity).count(),
        "crm_agreements": db.query(CrmAgreement).count(),
    }
    planned = plan_crm_demo_cleanup(db)
    deleted = {key: 0 for key in planned}
    notes = [
        "Deletes only is_demo / integrated_demo_seed / known QA seed identifiers.",
        "Bitrix contacts, agreements, and Bitrix pipeline rows are preserved.",
    ]
    if dry_run:
        return CrmDemoCleanupReport(
            dry_run=True,
            planned=planned,
            deleted=deleted,
            preserved=before,
            notes=notes,
        )

    contact_ids = _demo_ids(db, CrmContact)
    company_ids = _demo_ids(db, CrmCompany)
    activity_ids = _demo_ids(db, CrmActivity)
    lead_ids = _ids_where_is_demo(db, Lead)
    lead_ids |= {
        row_id
        for row_id, notes_text in db.execute(select(Lead.id, Lead.notes)).all()
        if isinstance(notes_text, str) and INTEGRATED_DEMO_SOURCE in notes_text
    }
    lead_ids |= {
        row_id
        for row_id, name in db.execute(select(Lead.id, Lead.full_name)).all()
        if (name or "").strip().casefold() in KNOWN_DEMO_PARTY_NAMES
    }
    opp_ids = _demo_ids(db, SalesOpportunity) | _known_seed_opportunity_ids(db)

    if opp_ids:
        for child in (
            OpportunityInventory,
            OpportunityProject,
            OpportunityTimeline,
            OpportunityProbabilityHistory,
        ):
            db.execute(delete(child).where(child.opportunity_id.in_(opp_ids)))
        db.execute(
            update(SalesOpportunity)
            .where(SalesOpportunity.id.in_(opp_ids))
            .values(reservation_id=None)
        )
        deleted["sales_opportunities"] = _delete_by_ids(db, SalesOpportunity, opp_ids)

    deleted["crm_activities"] = _delete_by_ids(db, CrmActivity, activity_ids)

    if contact_ids:
        db.execute(
            delete(CrmActivity).where(
                CrmActivity.entity_type == CrmActivityEntityType.CONTACT,
                CrmActivity.entity_id.in_(contact_ids),
            )
        )

    if contact_ids or company_ids:
        conds = []
        if contact_ids:
            conds.append(CrmCompanyContact.contact_id.in_(contact_ids))
        if company_ids:
            conds.append(CrmCompanyContact.company_id.in_(company_ids))
        db.execute(delete(CrmCompanyContact).where(or_(*conds)))

    deleted["crm_contacts"] = _delete_by_ids(db, CrmContact, contact_ids)
    deleted["crm_companies"] = _delete_by_ids(db, CrmCompany, company_ids)
    remaining_lead_ids = {
        row_id
        for row_id in db.scalars(select(SalesOpportunity.lead_id).where(SalesOpportunity.lead_id.is_not(None))).all()
        if row_id
    }
    lead_ids = {lead_id for lead_id in lead_ids if lead_id not in remaining_lead_ids}
    deleted["leads"] = _delete_by_ids(db, Lead, lead_ids)
    db.flush()

    after = {
        "crm_contacts": db.query(CrmContact).count(),
        "crm_contacts_bitrix": db.query(CrmContact)
        .filter(func.lower(CrmContact.source) == "bitrix")
        .count(),
        "leads": db.query(Lead).count(),
        "sales_opportunities": db.query(SalesOpportunity).count(),
        "crm_activities": db.query(CrmActivity).count(),
    }
    notes.append(f"counts_after: {after}")
    return CrmDemoCleanupReport(
        dry_run=False,
        planned=planned,
        deleted=deleted,
        preserved=before,
        notes=notes,
    )
