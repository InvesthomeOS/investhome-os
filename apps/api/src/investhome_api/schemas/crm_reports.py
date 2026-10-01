"""CRM report summary and management workspace schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CrmReportCount(BaseModel):
    key: str
    count: int
    label: str | None = None
    href: str | None = None


class CrmReportAmount(BaseModel):
    populated_count: int = 0
    total: float | None = None


class CrmReportMoney(BaseModel):
    currency: str
    total: float
    populated_count: int = 0


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


class CrmReportOption(BaseModel):
    key: str
    label: str


class CrmReportsFilterOptions(BaseModel):
    projects: list[CrmReportOption] = Field(default_factory=list)
    sources: list[CrmReportOption] = Field(default_factory=list)
    currencies: list[CrmReportOption] = Field(default_factory=list)


class CrmReportsKpis(BaseModel):
    current_purchases: int
    investors: int
    sales_totals: list[CrmReportMoney] = Field(default_factory=list)
    active_tasks: int
    open_leads: int
    documents_review: int


class CrmReportsSalesProjectRow(BaseModel):
    key: str
    label: str
    current_count: int
    historical_count: int
    amounts: list[CrmReportMoney] = Field(default_factory=list)
    href: str | None = None


class CrmReportsSales(BaseModel):
    current_count: int
    historical_count: int
    by_project: list[CrmReportsSalesProjectRow] = Field(default_factory=list)
    by_month: list[CrmReportCount] = Field(default_factory=list)
    table: list[CrmReportsSalesProjectRow] = Field(default_factory=list)


class CrmReportsInvestorRow(BaseModel):
    contact_id: str
    name: str
    purchases: int
    projects: list[str] = Field(default_factory=list)
    amounts: list[CrmReportMoney] = Field(default_factory=list)
    href: str | None = None


class CrmReportsInvestors(BaseModel):
    count: int
    purchases_per_investor: list[CrmReportCount] = Field(default_factory=list)
    by_project: list[CrmReportCount] = Field(default_factory=list)
    table: list[CrmReportsInvestorRow] = Field(default_factory=list)


class CrmReportsLeadConversion(BaseModel):
    key: str
    label: str
    won: int
    lost: int
    rate: float | None = None


class CrmReportsLeadRow(BaseModel):
    id: str
    name: str
    source: str | None = None
    stage: str
    owner: str | None = None
    project: str | None = None
    href: str | None = None


class CrmReportsLeads(BaseModel):
    total: int
    open_count: int
    by_source: list[CrmReportCount] = Field(default_factory=list)
    by_stage: list[CrmReportCount] = Field(default_factory=list)
    by_owner: list[CrmReportCount] = Field(default_factory=list)
    by_project: list[CrmReportCount] = Field(default_factory=list)
    conversion: list[CrmReportsLeadConversion] = Field(default_factory=list)
    table: list[CrmReportsLeadRow] = Field(default_factory=list)


class CrmReportsCommunication(BaseModel):
    total: int
    email: int
    whatsapp: int
    calls: int
    meetings: int
    tasks: int
    notes: int
    by_channel: list[CrmReportCount] = Field(default_factory=list)
    by_month: list[CrmReportCount] = Field(default_factory=list)
    by_owner: list[CrmReportCount] = Field(default_factory=list)
    table: list[CrmReportCount] = Field(default_factory=list)


class CrmReportsTasks(BaseModel):
    active: int
    in_progress: int
    completed: int
    overdue: int
    by_owner: list[CrmReportCount] = Field(default_factory=list)
    table: list[CrmReportCount] = Field(default_factory=list)


class CrmReportsDocuments(BaseModel):
    total: int
    person: int
    purchase: int
    hidden: int
    review_required: int
    by_category: list[CrmReportCount] = Field(default_factory=list)
    by_project: list[CrmReportCount] = Field(default_factory=list)
    table: list[CrmReportCount] = Field(default_factory=list)


class CrmReportsWorkspace(BaseModel):
    kpis: CrmReportsKpis
    sales: CrmReportsSales
    investors: CrmReportsInvestors
    leads: CrmReportsLeads
    communication: CrmReportsCommunication
    tasks: CrmReportsTasks
    documents: CrmReportsDocuments
    filter_options: CrmReportsFilterOptions
