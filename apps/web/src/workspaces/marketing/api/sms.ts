import { apiFetch } from '@/lib/api/client';

import type { ChannelDashboardBase, ReadinessResult } from './channel';

export type SmsCampaignSummary = {
  id: string;
  name: string;
  status: string;
  approval_status: string;
  readiness_state: string;
  message_body: string | null;
  character_count: number | null;
  segment_count: number | null;
  recipient_count: number | null;
  eligible_recipient_count: number | null;
  scheduled_at: string | null;
  created_at: string;
};

export type SmsDashboard = ChannelDashboardBase & {
  total_campaigns: number;
};

export const smsQueryKeys = {
  all: ['marketing', 'sms'] as const,
  dashboard: () => ['marketing', 'sms', 'dashboard'] as const,
  list: (page = 1) => ['marketing', 'sms', 'list', page] as const,
  detail: (id: string) => ['marketing', 'sms', 'detail', id] as const,
  templates: () => ['marketing', 'sms', 'templates'] as const,
};

export async function fetchSmsDashboard() {
  return apiFetch<SmsDashboard>('/marketing/sms/dashboard');
}

export async function fetchSmsCampaigns(page = 1) {
  return apiFetch<{ items: SmsCampaignSummary[]; total: number; pages: number }>(
    `/marketing/sms/campaigns?page=${page}`,
  );
}

export async function createSmsCampaign(payload: Record<string, unknown>) {
  return apiFetch<SmsCampaignSummary>('/marketing/sms/campaigns', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function fetchSmsReadiness(campaignId: string) {
  return apiFetch<ReadinessResult>(`/marketing/sms/campaigns/${campaignId}/readiness`, { method: 'POST' });
}

export async function validateSmsBody(body: string) {
  return apiFetch<{ character_count: number; segment_count: number }>(
    `/marketing/sms/validate?body=${encodeURIComponent(body)}`,
    { method: 'POST' },
  );
}

export const smsQueries = {
  dashboard: () => ({ queryKey: smsQueryKeys.dashboard(), queryFn: () => fetchSmsDashboard() }),
  list: (page = 1) => ({ queryKey: smsQueryKeys.list(page), queryFn: () => fetchSmsCampaigns(page) }),
};
