"""Company workspace dashboard aggregation."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.company import Company, CompanyStatus
from investhome_api.models.company_foundation import CompanyProfile, Department, Office, RecordStatus, Team
from investhome_api.models.branch import Branch, BranchStatus
from investhome_api.models.user_auth import User, UserStatus
from investhome_api.models.work_item import ACTIVE_WORK_ITEM_STATUSES, WorkItem


def build_dashboard_kpis(db: Session) -> dict[str, int]:
    managed_total = db.scalar(
        select(func.count()).select_from(Company).where(Company.archived_at.is_(None))
    ) or 0
    if managed_total:
        total_companies = managed_total
        active_companies = (
            db.scalar(
                select(func.count())
                .select_from(Company)
                .where(
                    Company.archived_at.is_(None),
                    Company.status == CompanyStatus.ACTIVE.value,
                )
            )
            or 0
        )
    else:
        total_companies = db.scalar(select(func.count()).select_from(CompanyProfile)) or 0
        active_companies = (
            db.scalar(
                select(func.count()).select_from(CompanyProfile).where(
                    CompanyProfile.status == RecordStatus.ACTIVE.value
                )
            )
            or 0
        )
    branches = (
        db.scalar(
            select(func.count()).select_from(Branch).where(
                Branch.archived_at.is_(None),
                Branch.status != BranchStatus.ARCHIVED.value,
            )
        )
        or 0
    )
    employees = (
        db.scalar(
            select(func.count()).select_from(User).where(
                User.archived_at.is_(None),
                User.status.in_([UserStatus.ACTIVE, UserStatus.INVITED]),
            )
        )
        or 0
    )
    departments = (
        db.scalar(
            select(func.count()).select_from(Department).where(
                Department.status == RecordStatus.ACTIVE.value,
            )
        )
        or 0
    )
    teams = (
        db.scalar(
            select(func.count()).select_from(Team).where(
                Team.status == RecordStatus.ACTIVE.value,
            )
        )
        or 0
    )
    pending_tasks = (
        db.scalar(
            select(func.count()).select_from(WorkItem).where(
                WorkItem.archived_at.is_(None),
                WorkItem.status.in_(list(ACTIVE_WORK_ITEM_STATUSES)),
            )
        )
        or 0
    )

    return {
        "total_companies": total_companies,
        "active_companies": active_companies,
        "branches": branches,
        "employees": employees,
        "departments": departments,
        "teams": teams,
        "pending_tasks": pending_tasks,
    }
