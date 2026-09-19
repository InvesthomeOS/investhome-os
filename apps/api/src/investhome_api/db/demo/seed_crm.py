"""Idempotent CRM demo data — contacts, companies, activities, notes, tasks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.db.demo.markers import DEMO_METADATA, INTEGRATED_DEMO_SOURCE
from investhome_api.db.session import SessionLocal
from investhome_api.models.crm_activity import (
    CrmActivity,
    CrmActivityCategory,
    CrmActivityEntityType,
    CrmActivityPriority,
    CrmActivityStatus,
    CrmActivityType,
    CrmTaskStatus,
)
from investhome_api.models.crm_company import (
    CrmCompany,
    CrmCompanyContact,
    CrmCompanyContactRole,
    CrmCompanyStatus,
    CrmCompanyType,
    CrmEntityType,
)
from investhome_api.models.crm_contact import (
    CrmContact,
    CrmContactStatus,
    CrmContactType,
    CrmLifecycleStage,
    CrmRecordKind,
    CrmRelationshipStatus,
)
from investhome_api.models.investor import Investor
from investhome_api.models.lead import Lead
from investhome_api.models.user_auth import User

DEMO_COMPANIES: list[dict[str, object]] = [
    {"display_name": "Marmara Capital Partners", "company_type": CrmCompanyType.INVESTMENT_COMPANY, "domain": "marmara.capital", "industry": "Private Equity"},
    {"display_name": "Capitol Realty Group", "company_type": CrmCompanyType.BROKERAGE, "domain": "capitolrealty.demo", "industry": "Real Estate Brokerage"},
    {"display_name": "Potomac Lending Partners", "company_type": CrmCompanyType.LENDER, "domain": "potomaclending.demo", "industry": "Commercial Lending"},
    {"display_name": "Ankara İnşaat A.Ş.", "company_type": CrmCompanyType.CONSTRUCTION, "domain": "ankarainsaat.demo", "industry": "Construction"},
    {"display_name": "Horizon Law LLP", "company_type": CrmCompanyType.LAW_FIRM, "domain": "horizonlaw.demo", "industry": "Legal"},
    {"display_name": "Blue Ridge Family Office", "company_type": CrmCompanyType.INVESTMENT_COMPANY, "domain": "blueridgefo.demo", "industry": "Family Office"},
    {"display_name": "DC Metro Architects", "company_type": CrmCompanyType.ARCHITECTURE, "domain": "dcmetroarch.demo", "industry": "Architecture"},
    {"display_name": "Atlas Property Management", "company_type": CrmCompanyType.PROPERTY_MANAGEMENT, "domain": "atlaspm.demo", "industry": "Property Management"},
    {"display_name": "Bosporus Ventures", "company_type": CrmCompanyType.PARTNER, "domain": "bosporus.ventures", "industry": "Investment"},
    {"display_name": "Summit Title Services", "company_type": CrmCompanyType.VENDOR, "domain": "summittitle.demo", "industry": "Title Services"},
    {"display_name": "Nordic Growth Advisors", "company_type": CrmCompanyType.CONSULTING, "domain": "nordicgrowth.demo", "industry": "Consulting"},
    {"display_name": "Chesapeake Insurance Brokers", "company_type": CrmCompanyType.INSURANCE, "domain": "chesapeakeins.demo", "industry": "Insurance"},
]

DEMO_CONTACTS: list[dict[str, object]] = [
    {"email": "zeynep.kaya@demo.crm", "first_name": "Zeynep", "last_name": "Kaya", "type": CrmContactType.PROSPECT, "company": "Marmara Capital Partners"},
    {"email": "ahmet.ozdemir@demo.crm", "first_name": "Ahmet", "last_name": "Özdemir", "type": CrmContactType.INVESTOR, "company": "Bosporus Ventures"},
    {"email": "elena.vasquez@demo.crm", "first_name": "Elena", "last_name": "Vasquez", "type": CrmContactType.BUYER, "company": "Blue Ridge Family Office"},
    {"email": "james.whitfield@demo.crm", "first_name": "James", "last_name": "Whitfield", "type": CrmContactType.INVESTOR, "company": "Blue Ridge Family Office"},
    {"email": "selin.arslan@demo.crm", "first_name": "Selin", "last_name": "Arslan", "type": CrmContactType.BROKER, "company": "Capitol Realty Group"},
    {"email": "michael.chen@demo.crm", "first_name": "Michael", "last_name": "Chen", "type": CrmContactType.BROKER, "company": "Capitol Realty Group"},
    {"email": "fatma.yildiz@demo.crm", "first_name": "Fatma", "last_name": "Yıldız", "type": CrmContactType.ATTORNEY, "company": "Horizon Law LLP"},
    {"email": "robert.hayes@demo.crm", "first_name": "Robert", "last_name": "Hayes", "type": CrmContactType.LENDER, "company": "Potomac Lending Partners"},
    {"email": "deniz.celik@demo.crm", "first_name": "Deniz", "last_name": "Çelik", "type": CrmContactType.CONTRACTOR, "company": "Ankara İnşaat A.Ş."},
    {"email": "sophia.nguyen@demo.crm", "first_name": "Sophia", "last_name": "Nguyen", "type": CrmContactType.ARCHITECT, "company": "DC Metro Architects"},
    {"email": "can.demir@demo.crm", "first_name": "Can", "last_name": "Demir", "type": CrmContactType.PROSPECT, "company": "Nordic Growth Advisors"},
    {"email": "olivia.brook@demo.crm", "first_name": "Olivia", "last_name": "Brook", "type": CrmContactType.PROPERTY_MANAGER, "company": "Atlas Property Management"},
    {"email": "burak.sahin@demo.crm", "first_name": "Burak", "last_name": "Şahin", "type": CrmContactType.PARTNER, "company": "Bosporus Ventures"},
    {"email": "nina.patel@demo.crm", "first_name": "Nina", "last_name": "Patel", "type": CrmContactType.CONSULTANT, "company": "Nordic Growth Advisors"},
    {"email": "emre.aksoy@demo.crm", "first_name": "Emre", "last_name": "Aksoy", "type": CrmContactType.BUYER, "company": None},
    {"email": "claire.morgan@demo.crm", "first_name": "Claire", "last_name": "Morgan", "type": CrmContactType.PROSPECT, "company": None},
    {"email": "hasan.kilic@demo.crm", "first_name": "Hasan", "last_name": "Kılıç", "type": CrmContactType.VENDOR, "company": "Summit Title Services"},
    {"email": "priya.nair@demo.crm", "first_name": "Priya", "last_name": "Nair", "type": CrmContactType.INVESTOR, "company": "Marmara Capital Partners"},
    {"email": "thomas.berg@demo.crm", "first_name": "Thomas", "last_name": "Berg", "type": CrmContactType.PROSPECT, "company": "Nordic Growth Advisors"},
    {"email": "leyla.guven@demo.crm", "first_name": "Leyla", "last_name": "Güven", "type": CrmContactType.REALTOR, "company": "Capitol Realty Group"},
    {"email": "david.okonkwo@demo.crm", "first_name": "David", "last_name": "Okonkwo", "type": CrmContactType.BUYER, "company": None},
    {"email": "melis.eroglu@demo.crm", "first_name": "Melis", "last_name": "Eroğlu", "type": CrmContactType.MEDIA_CONTACT, "company": None},
]


def seed_crm(session: Session | None = None) -> dict[str, int]:
    own_session = session is None
    session = session or SessionLocal()
    counts = {"companies": 0, "contacts": 0, "activities": 0, "notes": 0, "tasks": 0, "links": 0}
    try:
        bitrix_present = session.scalar(
            select(func.count())
            .select_from(CrmContact)
            .where(func.lower(CrmContact.source) == "bitrix")
        )
        if bitrix_present:
            counts["skipped"] = 1
            return counts
        owner = session.scalar(
            select(User).where(User.email == "sales@investhome.demo")
        ) or session.scalar(select(User).where(User.is_demo.is_(True)).limit(1))
        owner_id = owner.id if owner else None

        company_by_name: dict[str, CrmCompany] = {}
        for spec in DEMO_COMPANIES:
            name = str(spec["display_name"])
            existing = session.scalar(
                select(CrmCompany).where(CrmCompany.display_name == name)
            )
            if existing is not None:
                if not is_demo_source_or_meta(existing):
                    existing.source = INTEGRATED_DEMO_SOURCE
                    existing.metadata_json = {**(existing.metadata_json or {}), **DEMO_METADATA}
                company_by_name[name] = existing
                continue
            company = CrmCompany(
                display_name=name,
                legal_name=name,
                company_type=spec["company_type"],  # type: ignore[arg-type]
                entity_type=CrmEntityType.LLC,
                status=CrmCompanyStatus.ACTIVE,
                industry=str(spec.get("industry") or ""),
                domain=str(spec.get("domain") or ""),
                primary_email=f"info@{spec.get('domain') or 'demo.crm'}",
                primary_phone="+1 202 555 0100",
                source=INTEGRATED_DEMO_SOURCE,
                metadata_json=dict(DEMO_METADATA),
                owner_user_id=owner_id,
                notes="Integrated demo CRM company.",
            )
            session.add(company)
            session.flush()
            company_by_name[name] = company
            counts["companies"] += 1

        leads = list(session.scalars(select(Lead).where(Lead.is_demo.is_(True))).all())
        investors = list(session.scalars(select(Investor).where(Investor.is_demo.is_(True))).all())
        lead_by_email = {((lead.email or "").lower()): lead for lead in leads if lead.email}
        investor_by_name = {inv.full_name.lower(): inv for inv in investors}

        contacts: list[CrmContact] = []
        for idx, spec in enumerate(DEMO_CONTACTS):
            email = str(spec["email"]).lower()
            existing = session.scalar(
                select(CrmContact).where(CrmContact.primary_email == email)
            )
            first = str(spec["first_name"])
            last = str(spec["last_name"])
            lead = lead_by_email.get(email.replace("@demo.crm", "@example.com"))
            if lead is None:
                for candidate in leads:
                    if candidate.full_name.lower().startswith(first.lower()):
                        lead = candidate
                        break
            investor = investor_by_name.get(f"{first} {last}".lower())
            if investor is None and "whitfield" in last.lower():
                investor = investor_by_name.get("james whitfield")

            if existing is not None:
                if not existing.is_demo:
                    existing.is_demo = True
                    existing.source = INTEGRATED_DEMO_SOURCE
                    existing.metadata_json = {**(existing.metadata_json or {}), **DEMO_METADATA}
                contact = existing
            else:
                contact = CrmContact(
                    contact_type=spec["type"],  # type: ignore[arg-type]
                    record_kind=CrmRecordKind.PERSON,
                    display_name=f"{first} {last}",
                    first_name=first,
                    last_name=last,
                    primary_email=email,
                    primary_phone=f"+1 202 555 {1000 + idx:04d}",
                    city="Washington",
                    country="United States",
                    lifecycle_stage=CrmLifecycleStage.ENGAGED,
                    relationship_status=CrmRelationshipStatus.WARM,
                    status=CrmContactStatus.ACTIVE,
                    source=INTEGRATED_DEMO_SOURCE,
                    metadata_json=dict(DEMO_METADATA),
                    owner_user_id=owner_id,
                    lead_id=lead.id if lead else None,
                    investor_id=investor.id if investor else None,
                    notes="Integrated demo CRM contact.",
                    is_demo=True,
                )
                session.add(contact)
                session.flush()
                counts["contacts"] += 1

            contacts.append(contact)

            company_name = spec.get("company")
            if company_name and company_name in company_by_name:
                company = company_by_name[str(company_name)]
                link = session.scalar(
                    select(CrmCompanyContact).where(
                        CrmCompanyContact.company_id == company.id,
                        CrmCompanyContact.contact_id == contact.id,
                    )
                )
                if link is None:
                    session.add(
                        CrmCompanyContact(
                            company_id=company.id,
                            contact_id=contact.id,
                            role=CrmCompanyContactRole.PRIMARY,
                            is_primary=True,
                        )
                    )
                    counts["links"] += 1

        # Activities: mix of call/meeting/note/task (≥20 total, ≥10 notes, ≥10 tasks)
        now = datetime.now(UTC)
        activity_specs: list[dict[str, object]] = []
        for i in range(12):
            contact = contacts[i % len(contacts)]
            activity_specs.append(
                {
                    "key": f"demo-call-{i+1}",
                    "type": CrmActivityType.PHONE_CALL,
                    "category": CrmActivityCategory.COMMUNICATION,
                    "title": f"Discovery call with {contact.display_name}",
                    "contact": contact,
                }
            )
        for i in range(8):
            contact = contacts[i % len(contacts)]
            activity_specs.append(
                {
                    "key": f"demo-meet-{i+1}",
                    "type": CrmActivityType.MEETING,
                    "category": CrmActivityCategory.MEETING,
                    "title": f"Project tour meeting — {contact.display_name}",
                    "contact": contact,
                }
            )
        for i in range(12):
            contact = contacts[i % len(contacts)]
            activity_specs.append(
                {
                    "key": f"demo-note-{i+1}",
                    "type": CrmActivityType.NOTE,
                    "category": CrmActivityCategory.NOTE,
                    "title": f"Relationship note #{i+1} — {contact.display_name}",
                    "contact": contact,
                }
            )
        for i in range(12):
            contact = contacts[i % len(contacts)]
            activity_specs.append(
                {
                    "key": f"demo-task-{i+1}",
                    "type": CrmActivityType.TASK,
                    "category": CrmActivityCategory.TASK,
                    "title": f"Follow-up task #{i+1} — {contact.display_name}",
                    "contact": contact,
                }
            )

        existing_demo_keys: set[str] = set()
        for row in session.scalars(select(CrmActivity)).all():
            meta = row.metadata_json or {}
            demo_key = meta.get("demo_key")
            if isinstance(demo_key, str):
                existing_demo_keys.add(demo_key)

        for spec in activity_specs:
            key = str(spec["key"])
            if key in existing_demo_keys:
                continue

            contact = spec["contact"]
            assert isinstance(contact, CrmContact)
            activity_type = spec["type"]
            assert isinstance(activity_type, CrmActivityType)
            meta = {**DEMO_METADATA, "demo_key": key}
            activity = CrmActivity(
                entity_type=CrmActivityEntityType.CONTACT,
                entity_id=contact.id,
                activity_type=activity_type,
                activity_category=spec["category"],  # type: ignore[arg-type]
                title=str(spec["title"]),
                summary="Integrated demo CRM activity.",
                description=f"Demo activity seeded by {INTEGRATED_DEMO_SOURCE}.",
                status=(
                    CrmActivityStatus.COMPLETED
                    if activity_type != CrmActivityType.TASK
                    else CrmActivityStatus.PLANNED
                ),
                task_status=(
                    CrmTaskStatus.NOT_STARTED if activity_type == CrmActivityType.TASK else None
                ),
                priority=CrmActivityPriority.MEDIUM,
                owner_id=owner_id,
                assigned_user_id=owner_id,
                start_date=now - timedelta(days=len(activity_specs) % 14),
                due_date=now + timedelta(days=7) if activity_type == CrmActivityType.TASK else None,
                metadata_json=meta,
                created_by=owner_id,
            )
            session.add(activity)
            existing_demo_keys.add(key)
            counts["activities"] += 1
            if activity_type == CrmActivityType.NOTE:
                counts["notes"] += 1
            if activity_type == CrmActivityType.TASK:
                counts["tasks"] += 1

        if own_session:
            session.commit()
        else:
            session.flush()
        return counts
    finally:
        if own_session:
            session.close()


def is_demo_source_or_meta(company: CrmCompany) -> bool:
    if company.source == INTEGRATED_DEMO_SOURCE:
        return True
    meta = company.metadata_json or {}
    return bool(meta.get("demo_seed") or meta.get("source") == INTEGRATED_DEMO_SOURCE)
