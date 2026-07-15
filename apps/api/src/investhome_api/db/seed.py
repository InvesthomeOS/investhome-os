"""Development/demo seed data for leads and investors."""

from decimal import Decimal

from sqlalchemy import select

from investhome_api.db.company_foundation_seed import seed_company_foundation
from investhome_api.db.design_studio_seed import seed_demo_design_studio_sprint2
from investhome_api.db.document_seed import seed_demo_documents
from investhome_api.db.activity_seed import seed_activity_logs
from investhome_api.db.notification_seed import seed_notifications
from investhome_api.db.auth_seed import seed_demo_users, seed_permissions_and_roles, sync_system_permissions
from investhome_api.db.finance_seed import seed_demo_finance
from investhome_api.db.investor_seed import DEMO_INVESTORS
from investhome_api.db.project_seed import DEMO_PROJECTS
from investhome_api.db.session import SessionLocal
from investhome_api.models.investor import Investor
from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.models.project import Project

DEMO_LEADS: list[dict[str, object]] = [
    {
        "full_name": "Amelia Hartwell",
        "email": "amelia.hartwell@example.com",
        "phone": "+44 7700 900123",
        "country": "United Kingdom",
        "source": "Website",
        "status": LeadStatus.NEW,
        "assigned_to": "Sarah Chen",
        "estimated_budget": Decimal("850000.00"),
        "interested_project": "Riverside Residences",
        "notes": "Demo lead — requested brochure for 2-bed waterfront units.",
    },
    {
        "full_name": "Marco Delgado",
        "email": "marco.delgado@example.com",
        "phone": "+34 612 345 678",
        "country": "Spain",
        "source": "Referral",
        "status": LeadStatus.CONTACTED,
        "assigned_to": "James Okonkwo",
        "estimated_budget": Decimal("1200000.00"),
        "interested_project": "Sierra Heights",
        "notes": "Demo lead — referred by existing investor network in Madrid.",
    },
    {
        "full_name": "Priya Nair",
        "email": "priya.nair@example.com",
        "phone": "+971 50 123 4567",
        "country": "United Arab Emirates",
        "source": "Exhibition",
        "status": LeadStatus.QUALIFIED,
        "assigned_to": "Sarah Chen",
        "estimated_budget": Decimal("2500000.00"),
        "interested_project": "Palm Gate Towers",
        "notes": "Demo lead — met at Cityscape, interested in premium tier.",
    },
    {
        "full_name": "Daniel Weiss",
        "email": "daniel.weiss@example.com",
        "phone": "+49 151 23456789",
        "country": "Germany",
        "source": "LinkedIn",
        "status": LeadStatus.MEETING_SCHEDULED,
        "assigned_to": "Emily Ross",
        "estimated_budget": Decimal("675000.00"),
        "interested_project": "Harbor Point",
        "notes": "Demo lead — discovery call booked for next Tuesday.",
    },
    {
        "full_name": "Fatima Al-Khalil",
        "email": "fatima.alkhalil@example.com",
        "phone": "+966 55 987 6543",
        "country": "Saudi Arabia",
        "source": "Partner",
        "status": LeadStatus.PROPOSAL_SENT,
        "assigned_to": "James Okonkwo",
        "estimated_budget": Decimal("4100000.00"),
        "interested_project": "Oasis Gardens",
        "notes": "Demo lead — proposal sent for Phase 2 allocation.",
    },
    {
        "full_name": "Lucas Ferreira",
        "email": "lucas.ferreira@example.com",
        "phone": "+55 11 91234 5678",
        "country": "Brazil",
        "source": "Website",
        "status": LeadStatus.NEGOTIATION,
        "assigned_to": "Emily Ross",
        "estimated_budget": Decimal("980000.00"),
        "interested_project": "Atlantic View",
        "notes": "Demo lead — negotiating payment schedule and unit mix.",
    },
    {
        "full_name": "Hannah Okafor",
        "email": "hannah.okafor@example.com",
        "phone": "+234 803 456 7890",
        "country": "Nigeria",
        "source": "Referral",
        "status": LeadStatus.WON,
        "assigned_to": "Sarah Chen",
        "estimated_budget": Decimal("1550000.00"),
        "interested_project": "Greenwood Estates",
        "notes": "Demo lead — converted after site visit and legal review.",
    },
    {
        "full_name": "Thomas Berg",
        "email": "thomas.berg@example.com",
        "phone": "+47 412 34567",
        "country": "Norway",
        "source": "Cold Outreach",
        "status": LeadStatus.LOST,
        "assigned_to": "James Okonkwo",
        "estimated_budget": Decimal("520000.00"),
        "interested_project": "Nordic Quarter",
        "notes": "Demo lead — chose a competing development in Oslo.",
    },
    {
        "full_name": "Elena Popescu",
        "email": "elena.popescu@example.com",
        "phone": "+40 722 123 456",
        "country": "Romania",
        "source": "Exhibition",
        "status": LeadStatus.CONTACTED,
        "assigned_to": "Emily Ross",
        "estimated_budget": Decimal("430000.00"),
        "interested_project": "Danube Park",
        "notes": "Demo lead — follow-up email sent with investment summary.",
    },
    {
        "full_name": "Michael Tan",
        "email": "michael.tan@example.com",
        "phone": "+65 8123 4567",
        "country": "Singapore",
        "source": "Website",
        "status": LeadStatus.QUALIFIED,
        "assigned_to": "Sarah Chen",
        "estimated_budget": Decimal("3200000.00"),
        "interested_project": "Marina One Residences",
        "notes": "Demo lead — family office looking for long-hold rental yield.",
    },
]


def seed_demo_leads() -> int:
    """Insert demo leads when the table is empty. Returns number of rows inserted."""
    with SessionLocal() as session:
        existing = session.scalar(select(Lead.id).limit(1))
        if existing is not None:
            return 0

        for payload in DEMO_LEADS:
            session.add(Lead(**payload, is_demo=True))

        session.commit()
        return len(DEMO_LEADS)


def seed_demo_investors() -> int:
    """Insert demo investors when the table is empty. Returns number of rows inserted."""
    with SessionLocal() as session:
        existing = session.scalar(select(Investor.id).limit(1))
        if existing is not None:
            return 0

        for payload in DEMO_INVESTORS:
            session.add(Investor(**payload, is_demo=True))

        session.commit()
        return len(DEMO_INVESTORS)


def seed_demo_projects() -> int:
    """Insert demo projects when the table is empty. Returns number of rows inserted."""
    with SessionLocal() as session:
        existing = session.scalar(select(Project.id).limit(1))
        if existing is not None:
            return 0

        for payload in DEMO_PROJECTS:
            session.add(Project(**payload, is_demo=True))

        session.commit()
        return len(DEMO_PROJECTS)


def main() -> None:
    permissions_inserted, roles_inserted = seed_permissions_and_roles()
    permissions_synced = sync_system_permissions()
    users_inserted = seed_demo_users()
    leads_inserted = seed_demo_leads()
    investors_inserted = seed_demo_investors()
    projects_inserted = seed_demo_projects()
    finance_inserted = seed_demo_finance()
    activity_inserted = seed_activity_logs()
    notifications_inserted = seed_notifications()
    documents_inserted = seed_demo_documents()
    foundation = seed_company_foundation()
    design_sprint2 = seed_demo_design_studio_sprint2()
    print(f"Seeded {permissions_inserted} permission(s) and {roles_inserted} role(s).")
    if permissions_synced:
        print(f"Synced {permissions_synced} permission grant(s).")
    print(f"Seeded {users_inserted} demo user(s).")
    print(f"Seeded {leads_inserted} demo lead(s).")
    print(f"Seeded {investors_inserted} demo investor(s).")
    print(f"Seeded {projects_inserted} demo project(s).")
    print(f"Seeded {finance_inserted} demo finance record(s).")
    print(f"Seeded {activity_inserted} activity log record(s).")
    print(f"Seeded {notifications_inserted} notification(s).")
    print(f"Seeded {documents_inserted} demo document(s).")
    if foundation["company"]:
        print(
            "Seeded company foundation: "
            f"{foundation['offices']} office(s), {foundation['departments']} department(s)."
        )
    if any(design_sprint2.values()):
        print(
            "Seeded design studio sprint 2: "
            f"{design_sprint2['material_packages']} material package(s), "
            f"{design_sprint2['furniture_items']} furniture item(s), "
            f"{design_sprint2['design_projects']} design project(s), "
            f"{design_sprint2['design_versions']} version(s)."
        )


if __name__ == "__main__":
    main()
