import { apiFetch } from '@/lib/api/client';

export type AudienceListParams = {
  page?: number;
  page_size?: number;
  search?: string;
  mode?: string;
  status?: string;
};

export type AudienceSummary = {
  id: string;
  name: string;
  audience_type: string;
  mode: string;
  status: string;
  source: string | null;
  estimated_size: number | null;
  calculated_size: number | null;
  language: string | null;
  last_refreshed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AudienceDetail = AudienceSummary & {
  description: string | null;
  contact_ids: string[] | null;
  company_ids: string[] | null;
  segment_ids: string[] | null;
  consent_requirements_json: Record<string, unknown> | null;
  channel_eligibility_json: Record<string, unknown> | null;
  version: number;
};

export type AudienceMembership = {
  id: string;
  audience_id: string;
  contact_id: string | null;
  company_id: string | null;
  is_included: boolean;
  inclusion_source: string | null;
  exclusion_reason: string | null;
  explainability_json: Record<string, unknown> | null;
};

export async function fetchAudiences(params: AudienceListParams = {}) {
  const search = new URLSearchParams();
  search.set('page', String(params.page ?? 1));
  search.set('page_size', String(params.page_size ?? 25));
  if (params.search) search.set('search', params.search);
  if (params.mode) search.set('mode', params.mode);
  if (params.status) search.set('status', params.status);
  return apiFetch<{ items: AudienceSummary[]; total: number; pages: number }>(
    `/marketing/audiences?${search.toString()}`,
  );
}

export async function fetchAudienceSummary() {
  return apiFetch<{ active: number; draft: number; total: number }>('/marketing/audiences/summary');
}

export async function fetchAudience(audienceId: string) {
  return apiFetch<AudienceDetail>(`/marketing/audiences/${audienceId}`);
}

export async function createAudience(payload: Record<string, unknown>) {
  return apiFetch<AudienceDetail>('/marketing/audiences', { method: 'POST', body: JSON.stringify(payload) });
}

export async function updateAudience(audienceId: string, payload: Record<string, unknown>) {
  return apiFetch<AudienceDetail>(`/marketing/audiences/${audienceId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function fetchAudienceMembers(audienceId: string, page = 1) {
  return apiFetch<{ items: AudienceMembership[]; total: number }>(
    `/marketing/audiences/${audienceId}/members?page=${page}`,
  );
}

export async function fetchAudienceReadiness(audienceId: string) {
  return apiFetch<{ state: string; blockers: string[]; member_count: number | null }>(
    `/marketing/audiences/${audienceId}/readiness`,
  );
}

export async function refreshAudience(audienceId: string) {
  return apiFetch<AudienceDetail>(`/marketing/audiences/${audienceId}/refresh`, { method: 'POST' });
}
