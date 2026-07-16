"""Centralized proposal number generation.

Pattern: {COMPANY_CODE}-{PROJECT_CODE}-{YEAR}-{SEQUENCE}
Example: IH-TEM-2026-000123

Numbers are unique, immutable, and human-readable.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.company_foundation import CompanyProfile
from investhome_api.models.project import Project
from investhome_api.models.sales_proposal import SalesProposal


def _normalize_code(value: str, *, fallback: str, max_len: int = 10) -> str:
    cleaned = "".join(ch for ch in value.upper() if ch.isalnum() or ch == "-")
    if not cleaned:
        return fallback
    return cleaned[:max_len]


def get_company_code(db: Session) -> str:
    company = db.scalar(select(CompanyProfile).limit(1))
    if company and company.company_code:
        return _normalize_code(company.company_code, fallback="IH")
    return "IH"


def get_project_code(db: Session, project_id) -> str:
    if project_id is None:
        return "GEN"
    project = db.get(Project, project_id)
    if project and project.project_code:
        return _normalize_code(project.project_code, fallback="GEN")
    return "GEN"


def generate_proposal_number(
    db: Session,
    *,
    project_id=None,
    year: int | None = None,
) -> str:
    """Generate next proposal number for company + project + year."""
    company_code = get_company_code(db)
    project_code = get_project_code(db, project_id)
    seq_year = year or date.today().year
    prefix = f"{company_code}-{project_code}-{seq_year}-"

    count = db.scalar(
        select(func.count())
        .select_from(SalesProposal)
        .where(SalesProposal.proposal_number.like(f"{prefix}%"))
    )
    sequence = (count or 0) + 1
    return f"{prefix}{sequence:06d}"
