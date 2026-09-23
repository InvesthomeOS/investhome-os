import { apiFetch } from '@/lib/api/client';

import type { CrmContactListResponse, CrmDashboardData } from '@/workspaces/crm/types';

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
  description?: string | null;
  status: 'active' | 'inactive' | string;
  color: string | null;
  usage_count: number;
  created_at?: string | null;
  updated_at?: string | null;
};

export type CrmTagStats = {
  total_tags: number;
  tagged_people: number;
  untagged_people: number;
};

export type CrmTagListResponse = {
  items: CrmTagItem[];
  stats?: CrmTagStats;
};

export type CrmTagContactRef = {
  id: string;
  display_name: string;
};

export type CrmTagDetail = CrmTagItem & {
  people: CrmTagContactRef[];
};

export async function fetchCrmTags(params: { search?: string; status?: string } = {}): Promise<CrmTagListResponse> {
  const search = new URLSearchParams();
  if (params.search) search.set('search', params.search);
  if (params.status) search.set('status', params.status);
  const suffix = search.toString() ? `?${search.toString()}` : '';
  return apiFetch<CrmTagListResponse>(`/crm/tags${suffix}`);
}

export async function fetchCrmTag(tagId: string): Promise<CrmTagDetail> {
  return apiFetch<CrmTagDetail>(`/crm/tags/${tagId}`);
}

export async function createCrmTag(payload: {
  name: string;
  description?: string;
  status?: string;
}): Promise<CrmTagDetail> {
  return apiFetch<CrmTagDetail>('/crm/tags', { method: 'POST', body: JSON.stringify(payload) });
}

export async function updateCrmTag(
  tagId: string,
  payload: { name?: string; description?: string; status?: string },
): Promise<CrmTagDetail> {
  return apiFetch<CrmTagDetail>(`/crm/tags/${tagId}`, { method: 'PATCH', body: JSON.stringify(payload) });
}

export async function deactivateCrmTag(tagId: string): Promise<CrmTagDetail> {
  return apiFetch<CrmTagDetail>(`/crm/tags/${tagId}/deactivate`, { method: 'POST' });
}

export async function activateCrmTag(tagId: string): Promise<CrmTagDetail> {
  return apiFetch<CrmTagDetail>(`/crm/tags/${tagId}/activate`, { method: 'POST' });
}

export async function assignContactTag(contactId: string, tagId: string) {
  return apiFetch<Array<{ id: string; name: string; status: string }>>(`/crm/contacts/${contactId}/tags`, {
    method: 'POST',
    body: JSON.stringify({ tag_id: tagId }),
  });
}

export async function removeContactTag(contactId: string, tagId: string) {
  return apiFetch<Array<{ id: string; name: string; status: string }>>(
    `/crm/contacts/${contactId}/tags/${tagId}`,
    { method: 'DELETE' },
  );
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
