"""Simple CRM reporting aggregates from existing tables. No BI, no invented totals."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from investhome_api.models.crm_activity import (
    CrmActivity,
    CrmActivityCategory,
    CrmActivityType,
    CrmTaskStatus,
)
from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_company import CrmCompany, CrmCompanyContact
from investhome_api.models.crm_contact import CrmContact, CrmContactStatus
from investhome_api.models.crm_relationship import CrmRelationship, CrmRelationshipEntityType
from investhome_api.models.sales import SalesOpportunity
from investhome_api.schemas.crm_reports import (
    CrmReportAmount,
    CrmReportCount,
    CrmReportsSummary,
)
from investhome_api.services.crm.contact_service import list_crm_contacts


def _enum_key(value: object) -> str:
    raw = getattr(value, "value", value)
    return str(raw or "").strip().lower()


def _contact_count(db: Session, **kwargs) -> int:
    _, total = list_crm_contacts(db, page=1, page_size=1, **kwargs)
    return int(total)


def _parse_investment_amount(raw: str | None) -> float | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    for token in (" ", ",", "$", "€", "₺", "TL", "tl"):
        text = text.replace(token, "")
    try:
        value = float(text)
    except ValueError:
        return None
    if value < 0:
        return None
    return value


def _grouped_counts(rows: list[tuple[object, int]]) -> list[CrmReportCount]:
    return [CrmReportCount(key=_enum_key(key) or "unknown", count=int(count or 0)) for key, count in rows]


def build_crm_reports_summary(db: Session) -> CrmReportsSummary:
    contacts_total = db.scalar(select(func.count()).select_from(CrmContact)) or 0
    contacts_active = _contact_count(db, status=CrmContactStatus.ACTIVE)
    contacts_junk = _contact_count(db, bitrix_list="current_junk")
    contacts_agents = _contact_count(db, role_group="agent")
    contacts_agreement = _contact_count(db, category="agreement")

    pipeline_total = db.scalar(
        select(func.count(func.distinct(SalesOpportunity.crm_contact_id))).where(
            SalesOpportunity.crm_contact_id.is_not(None)
        )
    ) or 0
    pipeline_by_stage = _grouped_counts(
        db.execute(
            select(SalesOpportunity.stage, func.count(func.distinct(SalesOpportunity.crm_contact_id)))
            .where(SalesOpportunity.crm_contact_id.is_not(None))
            .group_by(SalesOpportunity.stage)
        ).all()
    )

    activities_total = db.scalar(select(func.count()).select_from(CrmActivity)) or 0
    activities_by_type = _grouped_counts(
        db.execute(select(CrmActivity.activity_type, func.count()).group_by(CrmActivity.activity_type)).all()
    )

    task_match = or_(
        CrmActivity.activity_type == CrmActivityType.TASK,
        CrmActivity.activity_category == CrmActivityCategory.TASK,
    )
    completed_task = CrmActivity.task_status == CrmTaskStatus.COMPLETED
    cancelled_task = CrmActivity.task_status.in_([CrmTaskStatus.CANCELLED, CrmTaskStatus.DEFERRED])
    tasks_pending = db.scalar(
        select(func.count()).select_from(CrmActivity).where(task_match, ~completed_task, ~cancelled_task)
    ) or 0
    tasks_completed = db.scalar(
        select(func.count()).select_from(CrmActivity).where(task_match, completed_task)
    ) or 0
    now = datetime.now(tz=UTC)
    tasks_overdue = db.scalar(
        select(func.count())
        .select_from(CrmActivity)
        .where(
            task_match,
            ~completed_task,
            ~cancelled_task,
            CrmActivity.due_date.is_not(None),
            CrmActivity.due_date < now,
        )
    ) or 0

    agreements_total = db.scalar(select(func.count()).select_from(CrmAgreement)) or 0
    agreements_by_project = _grouped_counts(
        db.execute(select(CrmAgreement.project_group, func.count()).group_by(CrmAgreement.project_group)).all()
    )

    reit_rows = db.scalars(
        select(CrmAgreement.investment_amount).where(func.lower(CrmAgreement.project_group) == "reit")
    ).all()
    parsed_amounts = [value for value in (_parse_investment_amount(raw) for raw in reit_rows) if value is not None]
    reit_total = CrmReportAmount(
        populated_count=len(parsed_amounts),
        total=round(sum(parsed_amounts), 2) if parsed_amounts else None,
    )

    companies_total = db.scalar(select(func.count()).select_from(CrmCompany)) or 0
    company_contact_links = db.scalar(select(func.count()).select_from(CrmCompanyContact)) or 0

    relationships_total = db.scalar(select(func.count()).select_from(CrmRelationship)) or 0
    relationships_contact_company = db.scalar(
        select(func.count())
        .select_from(CrmRelationship)
        .where(
            CrmRelationship.source_entity_type == CrmRelationshipEntityType.CONTACT,
            CrmRelationship.target_entity_type == CrmRelationshipEntityType.COMPANY,
        )
    ) or 0
    relationships_investor_project = db.scalar(
        select(func.count())
        .select_from(CrmRelationship)
        .where(
            CrmRelationship.source_entity_type == CrmRelationshipEntityType.CONTACT,
            CrmRelationship.target_entity_type == CrmRelationshipEntityType.PROJECT,
            CrmRelationship.relationship_type == "investor",
        )
    ) or 0

    return CrmReportsSummary(
        contacts_total=int(contacts_total),
        contacts_active=int(contacts_active),
        contacts_junk=int(contacts_junk),
        contacts_agents=int(contacts_agents),
        contacts_agreement=int(contacts_agreement),
        pipeline_total=int(pipeline_total),
        pipeline_by_stage=pipeline_by_stage,
        activities_total=int(activities_total),
        activities_by_type=activities_by_type,
        tasks_pending=int(tasks_pending),
        tasks_completed=int(tasks_completed),
        tasks_overdue=int(tasks_overdue),
        agreements_total=int(agreements_total),
        agreements_by_project_group=agreements_by_project,
        reit_investment=reit_total,
        companies_total=int(companies_total),
        company_contact_links=int(company_contact_links),
        relationships_total=int(relationships_total),
        relationships_contact_company=int(relationships_contact_company),
        relationships_investor_project=int(relationships_investor_project),
    )
