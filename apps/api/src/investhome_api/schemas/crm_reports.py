"""Simple CRM report summary schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CrmReportCount(BaseModel):
    key: str
    count: int


class CrmReportAmount(BaseModel):
    populated_count: int = 0
    total: float | None = None


class CrmReportsSummary(BaseModel):
    contacts_total: int
    contacts_active: int
    contacts_junk: int
    contacts_agents: int
    contacts_agreement: int
    pipeline_total: int
    pipeline_by_stage: list[CrmReportCount] = Field(default_factory=list)
    activities_total: int
    activities_by_type: list[CrmReportCount] = Field(default_factory=list)
    tasks_pending: int
    tasks_completed: int
    tasks_overdue: int
    agreements_total: int
    agreements_by_project_group: list[CrmReportCount] = Field(default_factory=list)
    reit_investment: CrmReportAmount
    companies_total: int
    company_contact_links: int
    relationships_total: int
    relationships_contact_company: int
    relationships_investor_project: int
