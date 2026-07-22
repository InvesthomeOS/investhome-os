import { apiFetch } from '@/lib/api/client';

export type LeadSourceSummary = {
  id: string;
  name: string;
  normalized_name: string | null;
  parent_id: string | null;
  source_type: string;
  channel_id: string | null;
  tracking_code: string | null;
  tracking_readiness: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export async function fetchLeadSources(page = 1, pageSize = 25) {
  return apiFetch<{ items: LeadSourceSummary[]; total: number; pages: number }>(
    `/marketing/sources?page=${page}&page_size=${pageSize}`,
  );
}

export async function fetchLeadSourceSummary() {
  return apiFetch<{ total: number; active: number }>('/marketing/sources/summary');
}

export async function fetchLeadSourceHierarchy() {
  return apiFetch<{ items: Array<{ id: string; name: string; children: unknown[] }> }>(
    '/marketing/sources/hierarchy',
  );
}

export async function fetchLeadSource(sourceId: string) {
  return apiFetch<LeadSourceSummary & { description: string | null; utm_defaults_json: Record<string, unknown> | null }>(
    `/marketing/sources/${sourceId}`,
  );
}

export async function createLeadSource(payload: Record<string, unknown>) {
  return apiFetch<LeadSourceSummary>('/marketing/sources', { method: 'POST', body: JSON.stringify(payload) });
}

export async function normalizeLeadSourceValue(sourceId: string, rawValue: string) {
  return apiFetch<{ raw_value: string; normalized_value: string; from_cache: boolean }>(
    `/marketing/sources/${sourceId}/normalize`,
    { method: 'POST', body: JSON.stringify({ raw_value: rawValue }) },
  );
}
