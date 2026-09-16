import type { CrmContactListResponse, CrmDashboardData } from '@/workspaces/crm/types';

import { apiFetch } from '@/lib/api/client';

export type FetchCrmContactsParams = {
  page?: number;
  pageSize?: number;
  contactType?: string;
  includeArchived?: boolean;
};

export async function fetchCrmDashboard(): Promise<CrmDashboardData> {
  return apiFetch<CrmDashboardData>('/crm/dashboard');
}

export type CrmTagItem = {
  id: string;
  name: string;
  color: string | null;
  usage_count: number;
};

export type CrmTagListResponse = {
  items: CrmTagItem[];
};

export async function fetchCrmTags(): Promise<CrmTagListResponse> {
  return apiFetch<CrmTagListResponse>('/crm/tags');
}

export async function fetchCrmContacts(
  params: FetchCrmContactsParams = {},
): Promise<CrmContactListResponse> {
  const search = new URLSearchParams();
  search.set('page', String(params.page ?? 1));
  search.set('page_size', String(params.pageSize ?? 25));
  if (params.contactType) {
    search.set('contact_type', params.contactType);
  }
  if (params.includeArchived) {
    search.set('include_archived', 'true');
  }
  return apiFetch<CrmContactListResponse>(`/crm/contacts?${search.toString()}`);
}
