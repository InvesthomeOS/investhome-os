"""Idempotent project seed — ensure ≥10 DC projects including street addresses."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.db.demo.markers import INTEGRATED_DEMO_SOURCE
from investhome_api.db.project_seed import DEMO_PROJECTS
from investhome_api.db.session import SessionLocal
from investhome_api.models.project import DevelopmentType, Project, ProjectStatus, ProjectType

STREET_PROJECTS: list[dict[str, object]] = [
    {
        "project_code": "PRJ-1307-008",
        "project_name": "1307",
        "address": "1307 Rhode Island Ave NE",
        "city": "Washington",
        "state": "DC",
        "postal_code": "20018",
        "country": "United States",
        "project_type": ProjectType.MULTIFAMILY,
        "development_type": DevelopmentType.VALUE_ADD,
        "project_status": ProjectStatus.ACQUISITION,
        "ownership_entity": "1307 RI Ave LLC",
        "total_units": 18,
        "residential_units": 18,
        "commercial_units": 0,
        "gross_square_feet": 21400,
        "acquisition_price": Decimal("3100000.00"),
        "total_development_cost": Decimal("7200000.00"),
        "current_project_value": Decimal("6800000.00"),
        "projected_sale_value": Decimal("9100000.00"),
        "equity_required": Decimal("2400000.00"),
        "equity_raised": Decimal("900000.00"),
        "debt_amount": Decimal("4800000.00"),
        "loan_to_cost": Decimal("66.7000"),
        "projected_revenue": Decimal("9100000.00"),
        "projected_profit": Decimal("1900000.00"),
        "projected_roi": Decimal("26.4000"),
        "projected_irr": Decimal("19.8000"),
        "start_date": date(2026, 6, 1),
        "target_completion_date": date(2028, 3, 31),
        "assigned_project_manager": "Emre Kaya",
        "description": "Demo project — value-add multifamily at 1307 Rhode Island Ave NE.",
        "notes": f"Demo data — {INTEGRATED_DEMO_SOURCE} — underwriting in progress.",
    },
    {
        "project_code": "PRJ-1313-009",
        "project_name": "1313",
        "address": "1313 H St NE",
        "city": "Washington",
        "state": "DC",
        "postal_code": "20002",
        "country": "United States",
        "project_type": ProjectType.MIXED_USE,
        "development_type": DevelopmentType.RENOVATION,
        "project_status": ProjectStatus.CONSTRUCTION,
        "ownership_entity": "1313 H Street Partners LLC",
        "total_units": 22,
        "residential_units": 18,
        "commercial_units": 4,
        "gross_square_feet": 26800,
        "acquisition_price": Decimal("4500000.00"),
        "total_development_cost": Decimal("11200000.00"),
        "current_project_value": Decimal("11800000.00"),
        "projected_sale_value": Decimal("14500000.00"),
        "equity_required": Decimal("3800000.00"),
        "equity_raised": Decimal("3200000.00"),
        "debt_amount": Decimal("7400000.00"),
        "loan_to_cost": Decimal("66.1000"),
        "projected_revenue": Decimal("14500000.00"),
        "projected_profit": Decimal("3300000.00"),
        "projected_roi": Decimal("29.5000"),
        "projected_irr": Decimal("21.2000"),
        "start_date": date(2025, 2, 1),
        "target_completion_date": date(2027, 5, 31),
        "assigned_project_manager": "Marcus Webb",
        "description": "Demo project — mixed-use renovation at 1313 H St NE.",
        "notes": f"Demo data — {INTEGRATED_DEMO_SOURCE} — construction underway.",
    },
    {
        "project_code": "PRJ-1331-010",
        "project_name": "1331",
        "address": "1331 Maryland Ave NE",
        "city": "Washington",
        "state": "DC",
        "postal_code": "20002",
        "country": "United States",
        "project_type": ProjectType.TOWNHOME,
        "development_type": DevelopmentType.GROUND_UP,
        "project_status": ProjectStatus.PERMITTING,
        "ownership_entity": "1331 Maryland LLC",
        "total_units": 8,
        "residential_units": 8,
        "commercial_units": 0,
        "gross_square_feet": 14200,
        "acquisition_price": Decimal("1800000.00"),
        "total_development_cost": Decimal("5400000.00"),
        "current_project_value": Decimal("5100000.00"),
        "projected_sale_value": Decimal("6900000.00"),
        "equity_required": Decimal("1800000.00"),
        "equity_raised": Decimal("1200000.00"),
        "debt_amount": Decimal("3600000.00"),
        "loan_to_cost": Decimal("66.7000"),
        "projected_revenue": Decimal("6900000.00"),
        "projected_profit": Decimal("1500000.00"),
        "projected_roi": Decimal("27.8000"),
        "projected_irr": Decimal("20.1000"),
        "start_date": date(2026, 8, 1),
        "target_completion_date": date(2028, 1, 31),
        "assigned_project_manager": "Sarah Chen",
        "description": "Demo project — boutique townhomes at 1331 Maryland Ave NE.",
        "notes": f"Demo data — {INTEGRATED_DEMO_SOURCE} — permitting in progress.",
    },
    {
        "project_code": "PRJ-1627-011",
        "project_name": "1627",
        "address": "1627 7th St NW",
        "city": "Washington",
        "state": "DC",
        "postal_code": "20001",
        "country": "United States",
        "project_type": ProjectType.RESIDENTIAL,
        "development_type": DevelopmentType.VALUE_ADD,
        "project_status": ProjectStatus.LEASING,
        "ownership_entity": "1627 Shaw Partners LLC",
        "total_units": 28,
        "residential_units": 28,
        "commercial_units": 0,
        "gross_square_feet": 31200,
        "acquisition_price": Decimal("5200000.00"),
        "total_development_cost": Decimal("9800000.00"),
        "current_project_value": Decimal("11200000.00"),
        "projected_sale_value": Decimal("12800000.00"),
        "equity_required": Decimal("3400000.00"),
        "equity_raised": Decimal("3400000.00"),
        "debt_amount": Decimal("6400000.00"),
        "loan_to_cost": Decimal("65.3000"),
        "projected_revenue": Decimal("12800000.00"),
        "projected_profit": Decimal("3000000.00"),
        "projected_roi": Decimal("30.6000"),
        "projected_irr": Decimal("22.4000"),
        "start_date": date(2024, 9, 1),
        "target_completion_date": date(2026, 6, 30),
        "actual_completion_date": date(2026, 5, 15),
        "assigned_project_manager": "Marcus Webb",
        "description": "Demo project — value-add residential at 1627 7th St NW.",
        "notes": f"Demo data — {INTEGRATED_DEMO_SOURCE} — leasing launched.",
    },
    {
        "project_code": "PRJ-2319-012",
        "project_name": "2319",
        "address": "2319 Champlain St NW",
        "city": "Washington",
        "state": "DC",
        "postal_code": "20009",
        "country": "United States",
        "project_type": ProjectType.CONDOMINIUM,
        "development_type": DevelopmentType.GROUND_UP,
        "project_status": ProjectStatus.SALES,
        "ownership_entity": "2319 Champlain LLC",
        "total_units": 16,
        "residential_units": 16,
        "commercial_units": 0,
        "gross_square_feet": 19800,
        "acquisition_price": Decimal("3900000.00"),
        "total_development_cost": Decimal("12400000.00"),
        "current_project_value": Decimal("13100000.00"),
        "projected_sale_value": Decimal("15800000.00"),
        "equity_required": Decimal("4200000.00"),
        "equity_raised": Decimal("4200000.00"),
        "debt_amount": Decimal("8200000.00"),
        "loan_to_cost": Decimal("66.1000"),
        "projected_revenue": Decimal("15800000.00"),
        "projected_profit": Decimal("3400000.00"),
        "projected_roi": Decimal("27.4000"),
        "projected_irr": Decimal("19.9000"),
        "start_date": date(2024, 1, 15),
        "target_completion_date": date(2026, 9, 30),
        "assigned_project_manager": "Emre Kaya",
        "description": "Demo project — boutique condominiums at 2319 Champlain St NW.",
        "notes": f"Demo data — {INTEGRATED_DEMO_SOURCE} — sales active.",
    },
]


def _upsert_project(session: Session, payload: dict[str, object]) -> bool:
    code = str(payload["project_code"])
    existing_id = session.scalar(select(Project.id).where(Project.project_code == code))
    if existing_id is not None:
        return False
    session.add(Project(**payload, is_demo=True))
    return True


def seed_projects_extended(session: Session | None = None) -> int:
    """Ensure all named demo projects exist (idempotent by project_code)."""
    own_session = session is None
    session = session or SessionLocal()
    try:
        by_code: dict[str, dict[str, object]] = {}
        for payload in [*DEMO_PROJECTS, *STREET_PROJECTS]:
            by_code[str(payload["project_code"])] = payload

        inserted = 0
        for payload in by_code.values():
            if _upsert_project(session, payload):
                inserted += 1

        if own_session:
            session.commit()
        else:
            session.flush()
        return inserted
    finally:
        if own_session:
            session.close()
