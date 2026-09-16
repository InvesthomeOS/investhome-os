import { apiFetch } from '@/lib/api/client';

export type CrmReportCount = {
  key: string;
  count: number;
};

export type CrmReportAmount = {
  populated_count: number;
  total: number | null;
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

export async function fetchCrmReportsSummary(): Promise<CrmReportsSummary> {
  return apiFetch<CrmReportsSummary>('/crm/reports/summary');
}
