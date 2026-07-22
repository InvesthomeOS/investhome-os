import { apiFetch } from '@/lib/api/client';

import type { ChannelDashboardBase, ReadinessResult } from './channel';

export type WhatsAppCampaignSummary = {
  id: string;
  name: string;
  status: string;
  approval_status: string;
  readiness_state: string;
  recipient_count: number | null;
  eligible_recipient_count: number | null;
  scheduled_at: string | null;
  created_at: string;
};

export type WhatsAppDashboard = ChannelDashboardBase & {
  total_campaigns: number;
};

export const whatsappQueryKeys = {
  all: ['marketing', 'whatsapp'] as const,
  dashboard: () => ['marketing', 'whatsapp', 'dashboard'] as const,
  list: (page = 1) => ['marketing', 'whatsapp', 'list', page] as const,
  detail: (id: string) => ['marketing', 'whatsapp', 'detail', id] as const,
  templates: () => ['marketing', 'whatsapp', 'templates'] as const,
};

export async function fetchWhatsAppDashboard() {
  return apiFetch<WhatsAppDashboard>('/marketing/whatsapp/dashboard');
}

export async function fetchWhatsAppCampaigns(page = 1) {
  return apiFetch<{ items: WhatsAppCampaignSummary[]; total: number; pages: number }>(
    `/marketing/whatsapp/campaigns?page=${page}`,
  );
}

export async function createWhatsAppCampaign(payload: Record<string, unknown>) {
  return apiFetch<WhatsAppCampaignSummary>('/marketing/whatsapp/campaigns', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function fetchWhatsAppReadiness(campaignId: string) {
  return apiFetch<ReadinessResult>(`/marketing/whatsapp/campaigns/${campaignId}/readiness`, { method: 'POST' });
}

export const whatsappQueries = {
  dashboard: () => ({ queryKey: whatsappQueryKeys.dashboard(), queryFn: () => fetchWhatsAppDashboard() }),
  list: (page = 1) => ({ queryKey: whatsappQueryKeys.list(page), queryFn: () => fetchWhatsAppCampaigns(page) }),
};
