import { apiFetch } from '@/lib/api/client';

export type CrmReportCount = {
  key: string;
  count: number;
  label?: string | null;
  href?: string | null;
};

export type CrmReportAmount = {
  populated_count: number;
  total: number | null;
};

export type CrmReportMoney = {
  currency: string;
  total: number;
  populated_count: number;
};

export type CrmReportOption = {
  key: string;
  label: string;
};

export type CrmReportsSummary = {
  contacts_total: number;
  contacts_active: number;
  contacts_junk: number;
  contacts_agents: number;
  contacts_agreement: number;
  pipeline_total: number;
  pipeline_by_stage: CrmReportCount[];
  activities_total: number;
  activities_by_type: CrmReportCount[];
  tasks_pending: number;
  tasks_completed: number;
  tasks_overdue: number;
  agreements_total: number;
  agreements_by_project_group: CrmReportCount[];
  reit_investment: CrmReportAmount;
  companies_total: number;
  company_contact_links: number;
  relationships_total: number;
  relationships_contact_company: number;
  relationships_investor_project: number;
};

export type CrmReportsWorkspace = {
  kpis: {
    current_purchases: number;
    investors: number;
    sales_totals: CrmReportMoney[];
    active_tasks: number;
    open_leads: number;
    documents_review: number;
  };
  sales: {
    current_count: number;
    historical_count: number;
    by_project: CrmReportsSalesRow[];
    by_month: CrmReportCount[];
    table: CrmReportsSalesRow[];
  };
  investors: {
    count: number;
    purchases_per_investor: CrmReportCount[];
    by_project: CrmReportCount[];
    table: CrmReportsInvestorRow[];
  };
  leads: {
    total: number;
    open_count: number;
    by_source: CrmReportCount[];
    by_stage: CrmReportCount[];
    by_owner: CrmReportCount[];
    by_project: CrmReportCount[];
    conversion: Array<{ key: string; label: string; won: number; lost: number; rate: number | null }>;
    table: Array<{
      id: string;
      name: string;
      source: string | null;
      stage: string;
      owner: string | null;
      project: string | null;
      href: string | null;
    }>;
  };
  communication: {
    total: number;
    email: number;
    whatsapp: number;
    calls: number;
    meetings: number;
    tasks: number;
    notes: number;
    by_channel: CrmReportCount[];
    by_month: CrmReportCount[];
    by_owner: CrmReportCount[];
    table: CrmReportCount[];
  };
  tasks: {
    active: number;
    in_progress: number;
    completed: number;
    overdue: number;
    by_owner: CrmReportCount[];
    table: CrmReportCount[];
  };
  documents: {
    total: number;
    person: number;
    purchase: number;
    hidden: number;
    review_required: number;
    by_category: CrmReportCount[];
    by_project: CrmReportCount[];
    table: CrmReportCount[];
  };
  filter_options: {
    projects: CrmReportOption[];
    sources: CrmReportOption[];
    currencies: CrmReportOption[];
  };
};

export type CrmReportsSalesRow = {
  key: string;
  label: string;
  current_count: number;
  historical_count: number;
  amounts: CrmReportMoney[];
  href?: string | null;
};

export type CrmReportsInvestorRow = {
  contact_id: string;
  name: string;
  purchases: number;
  projects: string[];
  amounts: CrmReportMoney[];
  href?: string | null;
};

export type CrmReportsWorkspaceParams = {
  date_from?: string;
  date_to?: string;
  project_group?: string;
  owner_id?: string;
  source?: string;
  currency?: string;
};

export async function fetchCrmReportsSummary(): Promise<CrmReportsSummary> {
  return apiFetch<CrmReportsSummary>('/crm/reports/summary');
}

export async function fetchCrmReportsWorkspace(
  params: CrmReportsWorkspaceParams = {},
): Promise<CrmReportsWorkspace> {
  const query = new URLSearchParams();
  if (params.date_from) query.set('date_from', params.date_from);
  if (params.date_to) query.set('date_to', params.date_to);
  if (params.project_group) query.set('project_group', params.project_group);
  if (params.owner_id) query.set('owner_id', params.owner_id);
  if (params.source) query.set('source', params.source);
  if (params.currency) query.set('currency', params.currency);
  const suffix = query.toString() ? `?${query.toString()}` : '';
  return apiFetch<CrmReportsWorkspace>(`/crm/reports/workspace${suffix}`);
}
