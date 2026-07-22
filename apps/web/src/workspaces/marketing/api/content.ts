import { apiFetch } from '@/lib/api/client';

export type ContentSummary = {
  id: string;
  title: string;
  code: string | null;
  content_type: string;
  format: string | null;
  status: string;
  owner_user_id: string | null;
  primary_language: string;
  scheduled_at: string | null;
  published_at: string | null;
  tags: string[] | null;
  created_at: string;
  updated_at: string;
};

export type ContentDetail = ContentSummary & {
  description: string | null;
  team_id: string | null;
  project_ids: string[] | null;
  property_ids: string[] | null;
  audience_ids: string[] | null;
  campaign_ids: string[] | null;
  asset_ids: string[] | null;
  channel_ids: string[] | null;
  current_version_id: string | null;
  expires_at: string | null;
  archived_at: string | null;
};

export type ContentListParams = {
  page?: number;
  page_size?: number;
  status?: string;
  content_type?: string;
  search?: string;
};

export type ContentListResponse = {
  items: ContentSummary[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
};

export type PublishingReadiness = {
  state: 'ready' | 'warning' | 'blocked';
  remediation: string[];
  content_id: string;
  status: string;
};

export async function fetchContentDashboard() {
  return apiFetch<{ total: number; by_status: Record<string, number> }>('/marketing/content/dashboard');
}

export async function fetchContents(params: ContentListParams = {}) {
  const search = new URLSearchParams();
  search.set('page', String(params.page ?? 1));
  search.set('page_size', String(params.page_size ?? 25));
  if (params.status) search.set('status', params.status);
  if (params.content_type) search.set('content_type', params.content_type);
  if (params.search) search.set('search', params.search);
  return apiFetch<ContentListResponse>(`/marketing/content?${search.toString()}`);
}

export async function fetchContent(contentId: string) {
  return apiFetch<ContentDetail>(`/marketing/content/${contentId}`);
}

export async function createContent(payload: {
  title: string;
  content_type?: string;
  description?: string;
  format?: string;
}) {
  return apiFetch<{ content: ContentDetail }>('/marketing/content', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateContent(contentId: string, payload: Partial<ContentDetail>) {
  return apiFetch<{ content: ContentDetail }>(`/marketing/content/${contentId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function transitionContent(contentId: string, targetStatus: string) {
  return apiFetch<{ content: ContentDetail }>(`/marketing/content/${contentId}/transition`, {
    method: 'POST',
    body: JSON.stringify({ target_status: targetStatus }),
  });
}

export async function fetchContentReadiness(contentId: string) {
  return apiFetch<PublishingReadiness>(`/marketing/content/${contentId}/readiness`);
}

export async function submitContentApproval(contentId: string) {
  return apiFetch(`/marketing/content/${contentId}/submit-approval`, { method: 'POST' });
}

export async function fetchContentCalendar() {
  return apiFetch<{ items: Array<{ id: string; title: string; status: string; scheduled_at: string | null }> }>(
    '/marketing/content/calendar',
  );
}

export async function fetchContentBrief(contentId: string) {
  return apiFetch<{ brief: Record<string, unknown> }>(`/marketing/content/${contentId}/brief`);
}

export async function fetchContentVersions(contentId: string) {
  return apiFetch<{ items: unknown[] }>(`/marketing/content/${contentId}/versions`);
}

export async function requestAiGeneration(contentId: string, prompt: string) {
  return apiFetch<{ record: unknown; provider_available: boolean; requires_review: boolean; auto_publish: boolean }>(
    `/marketing/content/${contentId}/ai/generate`,
    { method: 'POST', body: JSON.stringify({ prompt }) },
  );
}
