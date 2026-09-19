import type {
  CrmCompanyDetail,
  CrmCompanyListResponse,
  CrmCompanyHierarchyResponse,
  CrmCompanyImportResult,
  CrmCompanySavedView,
  CrmCompanyTimelineResponse,
} from '@/workspaces/crm/types';

import { apiFetch, getApiBaseUrl } from '@/lib/api/client';

export type FetchCrmCompaniesParams = {
  page?: number;
  pageSize?: number;
  search?: string;
  status?: string;
  companyType?: string;
  lifecycleStage?: string;
  industry?: string;
  includeArchived?: boolean;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
};

function buildSearchParams(params: FetchCrmCompaniesParams): string {
  const search = new URLSearchParams();
  search.set('page', String(params.page ?? 1));
  search.set('page_size', String(params.pageSize ?? 25));
  if (params.search) search.set('search', params.search);
  if (params.status) search.set('status', params.status);
  if (params.companyType) search.set('company_type', params.companyType);
  if (params.lifecycleStage) search.set('lifecycle_stage', params.lifecycleStage);
  if (params.industry) search.set('industry', params.industry);
  if (params.includeArchived) search.set('include_archived', 'true');
  if (params.sortBy) search.set('sort_by', params.sortBy);
  if (params.sortOrder) search.set('sort_order', params.sortOrder);
  return search.toString();
}

export async function fetchCrmCompanies(
  params: FetchCrmCompaniesParams = {},
): Promise<CrmCompanyListResponse> {
  return apiFetch<CrmCompanyListResponse>(`/crm/companies?${buildSearchParams(params)}`);
}

export async function fetchCrmCompany(companyId: string): Promise<CrmCompanyDetail> {
  return apiFetch<CrmCompanyDetail>(`/crm/companies/${companyId}`);
}

export async function createCrmCompany(payload: Record<string, unknown>): Promise<CrmCompanyDetail> {
  return apiFetch<CrmCompanyDetail>('/crm/companies', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateCrmCompany(
  companyId: string,
  payload: Record<string, unknown>,
): Promise<CrmCompanyDetail> {
  return apiFetch<CrmCompanyDetail>(`/crm/companies/${companyId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function archiveCrmCompany(companyId: string): Promise<CrmCompanyDetail> {
  return apiFetch<CrmCompanyDetail>(`/crm/companies/${companyId}/archive`, { method: 'PATCH' });
}

export async function restoreCrmCompany(companyId: string): Promise<CrmCompanyDetail> {
  return apiFetch<CrmCompanyDetail>(`/crm/companies/${companyId}/restore`, { method: 'PATCH' });
}

export async function deleteCrmCompany(companyId: string): Promise<void> {
  await apiFetch<void>(`/crm/companies/${companyId}`, { method: 'DELETE' });
}

export async function fetchCrmCompanyHierarchy(): Promise<CrmCompanyHierarchyResponse> {
  return apiFetch<CrmCompanyHierarchyResponse>('/crm/companies/hierarchy');
}

export async function fetchCrmCompanyTimeline(companyId: string): Promise<CrmCompanyTimelineResponse> {
  return apiFetch<CrmCompanyTimelineResponse>(`/crm/companies/${companyId}/timeline`);
}

export async function fetchCrmCompanySavedViews(): Promise<CrmCompanySavedView[]> {
  return apiFetch<CrmCompanySavedView[]>('/crm/companies/saved-views');
}

export async function importCrmCompanies(file: File): Promise<CrmCompanyImportResult> {
  const formData = new FormData();
  formData.append('file', file);
  return apiFetch<CrmCompanyImportResult>('/crm/companies/import', {
    method: 'POST',
    body: formData,
  });
}

export async function exportCrmCompanies(includeArchived = false): Promise<string> {
  const params = includeArchived ? '?include_archived=true' : '';
  const response = await fetch(`${getApiBaseUrl()}/crm/companies/export${params}`, { credentials: 'include' });
  return response.text();
}

export async function mergeCrmCompanies(sourceId: string, targetId: string): Promise<{ merged_id: string }> {
  return apiFetch<{ merged_id: string }>('/crm/companies/merge', {
    method: 'POST',
    body: JSON.stringify({ source_id: sourceId, target_id: targetId }),
  });
}

export async function addCrmCompanyContact(
  companyId: string,
  payload: Record<string, unknown>,
): Promise<unknown> {
  return apiFetch(`/crm/companies/${companyId}/contacts`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
