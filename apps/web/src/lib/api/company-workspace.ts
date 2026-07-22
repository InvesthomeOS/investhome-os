import type { ActivityLogEntry } from '@/lib/api/activity';
import type { SearchResponse } from '@/lib/api/search';

import { apiFetch } from './client';

export type CompanyDashboardKpis = {
  total_companies: number;
  active_companies: number;
  branches: number;
  employees: number;
  departments: number;
  teams: number;
  pending_tasks: number;
};

export type CompanyRecentActivity = {
  items: ActivityLogEntry[];
  total: number;
};

export async function fetchCompanyDashboard(): Promise<CompanyDashboardKpis> {
  return apiFetch<CompanyDashboardKpis>('/companies/dashboard');
}

export async function fetchCompanyRecentActivity(limit = 20): Promise<CompanyRecentActivity> {
  return apiFetch<CompanyRecentActivity>(`/companies/recent-activity?limit=${limit}`);
}

export async function searchCompanyWorkspace(
  query: string,
  entityTypes?: string[],
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query });
  if (entityTypes?.length) {
    params.set('entity_types', entityTypes.join(','));
  }
  return apiFetch<SearchResponse>(`/companies/search?${params.toString()}`);
}
