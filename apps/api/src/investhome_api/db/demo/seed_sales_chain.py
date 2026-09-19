"""Idempotent sales chain — leads, opportunities, reservations, project/unit links."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.db.demo.markers import INTEGRATED_DEMO_SOURCE
from investhome_api.db.session import SessionLocal
from investhome_api.models.inventory import (
    InventoryAsset,
    InventoryReservation,
    ReservationRecordStatus,
    ReservationSource,
    ReservationStatus,
    ReservationType,
)
from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.models.project import Project
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.sales import (
    OpportunityInventory,
    OpportunityPartyType,
    OpportunityPriority,
    OpportunityProject,
    OpportunityStage,
    SalesOpportunity,
)
from investhome_api.models.user_auth import User

EXTRA_LEADS: list[dict[str, object]] = [
    {
        "full_name": "Ayşe Karaca",
        "email": "ayse.karaca@example.com",
        "phone": "+90 532 111 2233",
        "country": "Turkey",
        "source": "Website",
        "status": LeadStatus.NEW,
        "assigned_to": "Sarah Chen",
        "estimated_budget": Decimal("750000.00"),
        "interested_project": "The Temple",
        "notes": f"Demo lead — {INTEGRATED_DEMO_SOURCE}",
    },
    {
        "full_name": "Benjamin Cross",
        "email": "benjamin.cross@example.com",
        "phone": "+1 202 555 2201",
        "country": "United States",
        "source": "Referral",
        "status": LeadStatus.CONTACTED,
        "assigned_to": "James Okonkwo",
        "estimated_budget": Decimal("1100000.00"),
        "interested_project": "UniLoft",
        "notes": f"Demo lead — {INTEGRATED_DEMO_SOURCE}",
    },
    {
        "full_name": "Merve Aydın",
        "email": "merve.aydin@example.com",
        "phone": "+90 533 444 5566",
        "country": "Turkey",
        "source": "Exhibition",
        "status": LeadStatus.QUALIFIED,
        "assigned_to": "Emily Ross",
        "estimated_budget": Decimal("950000.00"),
        "interested_project": "309 H St NE",
        "notes": f"Demo lead — {INTEGRATED_DEMO_SOURCE}",
    },
    {
        "full_name": "Christopher Lane",
        "email": "christopher.lane@example.com",
        "phone": "+1 202 555 2202",
        "country": "United States",
        "source": "LinkedIn",
        "status": LeadStatus.MEETING_SCHEDULED,
        "assigned_to": "Sarah Chen",
        "estimated_budget": Decimal("1400000.00"),
        "interested_project": "The Campus",
        "notes": f"Demo lead — {INTEGRATED_DEMO_SOURCE}",
    },
    {
        "full_name": "İrem Yalçın",
        "email": "irem.yalcin@example.com",
        "phone": "+90 534 777 8899",
        "country": "Turkey",
        "source": "Partner",
        "status": LeadStatus.PROPOSAL_SENT,
        "assigned_to": "James Okonkwo",
        "estimated_budget": Decimal("2100000.00"),
        "interested_project": "1812 H Place NE",
        "notes": f"Demo lead — {INTEGRATED_DEMO_SOURCE}",
    },
    {
        "full_name": "Natalie Brooks",
        "email": "natalie.brooks@example.com",
        "phone": "+1 202 555 2203",
        "country": "United States",
        "source": "Website",
        "status": LeadStatus.NEGOTIATION,
        "assigned_to": "Emily Ross",
        "estimated_budget": Decimal("1250000.00"),
        "interested_project": "NoMa Gateway",
        "notes": f"Demo lead — {INTEGRATED_DEMO_SOURCE}",
    },
    {
        "full_name": "Onur Polat",
        "email": "onur.polat@example.com",
        "phone": "+90 535 222 3344",
        "country": "Turkey",
        "source": "Referral",
        "status": LeadStatus.WON,
        "assigned_to": "Sarah Chen",
        "estimated_budget": Decimal("1650000.00"),
        "interested_project": "1627",
        "notes": f"Demo lead — {INTEGRATED_DEMO_SOURCE}",
    },
    {
        "full_name": "Grace Holloway",
        "email": "grace.holloway@example.com",
        "phone": "+1 202 555 2204",
        "country": "United States",
        "source": "Cold Outreach",
        "status": LeadStatus.LOST,
        "assigned_to": "James Okonkwo",
        "estimated_budget": Decimal("580000.00"),
        "interested_project": "1307",
        "notes": f"Demo lead — {INTEGRATED_DEMO_SOURCE}",
    },
    {
        "full_name": "Kerem Taş",
        "email": "kerem.tas@example.com",
        "phone": "+90 536 555 6677",
        "country": "Turkey",
        "source": "Exhibition",
        "status": LeadStatus.CONTACTED,
        "assigned_to": "Emily Ross",
        "estimated_budget": Decimal("890000.00"),
        "interested_project": "1313",
        "notes": f"Demo lead — {INTEGRATED_DEMO_SOURCE}",
    },
    {
        "full_name": "Isabella Romano",
        "email": "isabella.romano@example.com",
        "phone": "+39 333 123 4567",
        "country": "Italy",
        "source": "Website",
        "status": LeadStatus.QUALIFIED,
        "assigned_to": "Sarah Chen",
        "estimated_budget": Decimal("2800000.00"),
        "interested_project": "The Temple",
        "notes": f"Demo lead — {INTEGRATED_DEMO_SOURCE}",
    },
]

OPPORTUNITY_SPECS: list[dict[str, object]] = [
    {"code": "OPP-DEMO-001", "stage": OpportunityStage.NEW, "amount": "750000.00", "lead_email": "ayse.karaca@example.com", "project": "PRJ-TEMP-001", "unit": "302"},
    {"code": "OPP-DEMO-002", "stage": OpportunityStage.QUALIFIED, "amount": "1100000.00", "lead_email": "benjamin.cross@example.com", "project": "PRJ-UNIL-002", "unit": "2A"},
    {"code": "OPP-DEMO-003", "stage": OpportunityStage.MEETING_SCHEDULED, "amount": "950000.00", "lead_email": "merve.aydin@example.com", "project": "PRJ-309H-003", "unit": "101"},
    {"code": "OPP-DEMO-004", "stage": OpportunityStage.INVENTORY_MATCHING, "amount": "1400000.00", "lead_email": "christopher.lane@example.com", "project": "PRJ-CAMP-004", "unit": None},
    {"code": "OPP-DEMO-005", "stage": OpportunityStage.PROPOSAL_SENT, "amount": "2100000.00", "lead_email": "irem.yalcin@example.com", "project": "PRJ-1812H-005", "unit": "TH-1"},
    {"code": "OPP-DEMO-006", "stage": OpportunityStage.NEGOTIATION, "amount": "1250000.00", "lead_email": "natalie.brooks@example.com", "project": "PRJ-NOMA-006", "unit": "501"},
    {"code": "OPP-DEMO-007", "stage": OpportunityStage.SOFT_HOLD, "amount": "1650000.00", "lead_email": "onur.polat@example.com", "project": "PRJ-1627-011", "unit": "201"},
    {"code": "OPP-DEMO-008", "stage": OpportunityStage.RESERVATION, "amount": "980000.00", "lead_email": "amelia.hartwell@example.com", "project": "PRJ-TEMP-001", "unit": "301"},
    {"code": "OPP-DEMO-009", "stage": OpportunityStage.DEPOSIT_PENDING, "amount": "720000.00", "lead_email": "marco.delgado@example.com", "project": "PRJ-UNIL-002", "unit": "2B"},
    {"code": "OPP-DEMO-010", "stage": OpportunityStage.CONTRACT, "amount": "2500000.00", "lead_email": "priya.nair@example.com", "project": "PRJ-TEMP-001", "unit": "12A"},
    {"code": "OPP-DEMO-011", "stage": OpportunityStage.WON, "amount": "1550000.00", "lead_email": "hannah.okafor@example.com", "project": "PRJ-NOMA-006", "unit": "502"},
    {"code": "OPP-DEMO-012", "stage": OpportunityStage.LOST, "amount": "520000.00", "lead_email": "thomas.berg@example.com", "project": "PRJ-1307-008", "unit": None},
    {"code": "OPP-DEMO-013", "stage": OpportunityStage.QUALIFIED, "amount": "890000.00", "lead_email": "kerem.tas@example.com", "project": "PRJ-1313-009", "unit": None},
    {"code": "OPP-DEMO-014", "stage": OpportunityStage.PROPOSAL_PREPARATION, "amount": "2800000.00", "lead_email": "isabella.romano@example.com", "project": "PRJ-TEMP-001", "unit": "403"},
    {"code": "OPP-DEMO-015", "stage": OpportunityStage.MEETING_COMPLETED, "amount": "430000.00", "lead_email": "elena.popescu@example.com", "project": "PRJ-1331-010", "unit": None},
]


def seed_sales_chain(session: Session | None = None) -> dict[str, int]:
    own_session = session is None
    session = session or SessionLocal()
    counts = {"leads": 0, "opportunities": 0, "reservations": 0, "opp_projects": 0, "opp_inventory": 0}
    try:
        bitrix_present = session.scalar(
            select(func.count())
            .select_from(CrmContact)
            .where(func.lower(CrmContact.source) == "bitrix")
        )
        if bitrix_present:
            counts["skipped"] = 1
            return counts
        sales_user = session.scalar(select(User).where(User.email == "sales@investhome.demo"))
        sales_id = sales_user.id if sales_user else None

        for payload in EXTRA_LEADS:
            email = str(payload["email"]).lower()
            existing = session.scalar(select(Lead).where(Lead.email == email))
            if existing is not None:
                if not existing.is_demo:
                    existing.is_demo = True
                continue
            session.add(Lead(**payload, is_demo=True))
            counts["leads"] += 1
        session.flush()

        leads = {
            (lead.email or "").lower(): lead
            for lead in session.scalars(select(Lead)).all()
            if lead.email
        }
        projects = {
            p.project_code: p for p in session.scalars(select(Project)).all()
        }

        for spec in OPPORTUNITY_SPECS:
            code = str(spec["code"])
            existing = session.scalar(
                select(SalesOpportunity).where(SalesOpportunity.opportunity_code == code)
            )
            lead = leads.get(str(spec["lead_email"]).lower())
            if lead is None:
                continue
            amount = Decimal(str(spec["amount"]))
            project = projects.get(str(spec["project"]))
            unit_display = spec.get("unit")
            asset = None
            if project is not None and unit_display:
                asset = session.scalar(
                    select(InventoryAsset).where(
                        InventoryAsset.project_id == project.id,
                        InventoryAsset.display_id == str(unit_display),
                    )
                )

            reservation = None
            stage = spec["stage"]
            assert isinstance(stage, OpportunityStage)
            if (
                existing is None
                and asset is not None
                and stage
                in {
                    OpportunityStage.SOFT_HOLD,
                    OpportunityStage.RESERVATION,
                    OpportunityStage.DEPOSIT_PENDING,
                    OpportunityStage.CONTRACT,
                    OpportunityStage.WON,
                }
            ):
                # Avoid unique active reservation conflict
                active = session.scalar(
                    select(InventoryReservation).where(
                        InventoryReservation.inventory_asset_id == asset.id,
                        InventoryReservation.status.in_(
                            [
                                ReservationRecordStatus.ACTIVE,
                                ReservationRecordStatus.REQUESTED,
                                ReservationRecordStatus.APPROVED,
                                ReservationRecordStatus.DEPOSIT_PENDING,
                                ReservationRecordStatus.DEPOSIT_RECEIVED,
                            ]
                        ),
                    )
                )
                if active is None:
                    reservation = InventoryReservation(
                        inventory_asset_id=asset.id,
                        reservation_type=(
                            ReservationType.SOFT_HOLD
                            if stage == OpportunityStage.SOFT_HOLD
                            else ReservationType.RESERVATION
                        ),
                        status=(
                            ReservationRecordStatus.DEPOSIT_PENDING
                            if stage == OpportunityStage.DEPOSIT_PENDING
                            else ReservationRecordStatus.ACTIVE
                        ),
                        source=ReservationSource.SALES,
                        lead_id=lead.id,
                        reserved_by_user_id=sales_id,
                        expires_at=datetime.now(UTC) + timedelta(days=14),
                        deposit_amount=amount * Decimal("0.10"),
                        deposit_currency="USD",
                        notes=f"Demo reservation — {INTEGRATED_DEMO_SOURCE}",
                        requested_at=datetime.now(UTC),
                        is_demo=True,
                    )
                    session.add(reservation)
                    session.flush()
                    asset.reservation_status = ReservationStatus.SOFT_HOLD
                    asset.active_reservation_id = reservation.id
                    counts["reservations"] += 1

            if existing is not None:
                if not existing.is_demo:
                    existing.is_demo = True
                opp = existing
            else:
                opp = SalesOpportunity(
                    opportunity_code=code,
                    display_id=code,
                    lead_id=lead.id,
                    party_id=lead.id,
                    party_type=OpportunityPartyType.LEAD,
                    assigned_sales_user_id=sales_id,
                    stage=stage,
                    probability=40 if stage != OpportunityStage.WON else 100,
                    expected_close_date=date.today() + timedelta(days=60),
                    expected_revenue=amount,
                    currency="USD",
                    priority=OpportunityPriority.MEDIUM,
                    source=INTEGRATED_DEMO_SOURCE,
                    notes=f"Demo opportunity chain — amount {amount}",
                    reservation_id=reservation.id if reservation else None,
                    is_demo=True,
                    created_by_id=sales_id,
                )
                session.add(opp)
                session.flush()
                counts["opportunities"] += 1

            if project is not None:
                link = session.scalar(
                    select(OpportunityProject).where(
                        OpportunityProject.opportunity_id == opp.id,
                        OpportunityProject.project_id == project.id,
                    )
                )
                if link is None:
                    session.add(
                        OpportunityProject(opportunity_id=opp.id, project_id=project.id)
                    )
                    counts["opp_projects"] += 1

            if asset is not None:
                inv_link = session.scalar(
                    select(OpportunityInventory).where(
                        OpportunityInventory.opportunity_id == opp.id,
                        OpportunityInventory.inventory_asset_id == asset.id,
                    )
                )
                if inv_link is None:
                    session.add(
                        OpportunityInventory(
                            opportunity_id=opp.id,
                            inventory_asset_id=asset.id,
                            match_reason="Integrated demo inventory match",
                            is_primary=True,
                            is_favorite=True,
                        )
                    )
                    counts["opp_inventory"] += 1

        if own_session:
            session.commit()
        else:
            session.flush()
        return counts
    finally:
        if own_session:
            session.close()
