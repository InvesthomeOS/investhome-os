import { apiFetch } from '@/lib/api/client';

import type { ChannelDashboardBase, ReadinessResult } from './channel';

export type EmailCampaignSummary = {
  id: string;
  name: string;
  status: string;
  approval_status: string;
  readiness_state: string;
  subject: string | null;
  recipient_count: number | null;
  eligible_recipient_count: number | null;
  scheduled_at: string | null;
  created_at: string;
};

export type EmailDashboard = ChannelDashboardBase & {
  total_campaigns: number;
  scheduled_campaigns: number;
};

export const emailQueryKeys = {
  all: ['marketing', 'email'] as const,
  dashboard: () => ['marketing', 'email', 'dashboard'] as const,
  list: (page = 1) => ['marketing', 'email', 'list', page] as const,
  detail: (id: string) => ['marketing', 'email', 'detail', id] as const,
  templates: () => ['marketing', 'email', 'templates'] as const,
  senders: () => ['marketing', 'email', 'senders'] as const,
  domains: () => ['marketing', 'email', 'domains'] as const,
};

export async function fetchEmailDashboard() {
  return apiFetch<EmailDashboard>('/marketing/email/dashboard');
}

export async function fetchEmailCampaigns(page = 1) {
  return apiFetch<{ items: EmailCampaignSummary[]; total: number; pages: number }>(
    `/marketing/email/campaigns?page=${page}`,
  );
}

export async function createEmailCampaign(payload: Record<string, unknown>) {
  return apiFetch<EmailCampaignSummary>('/marketing/email/campaigns', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateEmailCampaign(campaignId: string, payload: Record<string, unknown>) {
  return apiFetch<EmailCampaignSummary>(`/marketing/email/campaigns/${campaignId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function fetchEmailCampaign(campaignId: string) {
  return apiFetch<EmailCampaignSummary & { preview_text?: string | null; audience_id?: string | null; template_id?: string | null; sender_profile_id?: string | null; wizard_state_json?: Record<string, unknown> | null }>(
    `/marketing/email/campaigns/${campaignId}`,
  );
}

export async function fetchEmailTemplates() {
  return apiFetch<Array<{ id: string; name: string; status: string }>>('/marketing/email/templates');
}

export async function fetchEmailSenders() {
  return apiFetch<Array<{ id: string; from_name: string; from_email: string; status: string }>>('/marketing/email/senders');
}

export async function fetchEmailReadiness(campaignId: string) {
  return apiFetch<ReadinessResult>(`/marketing/email/campaigns/${campaignId}/readiness`, { method: 'POST' });
}

export const emailQueries = {
  dashboard: () => ({ queryKey: emailQueryKeys.dashboard(), queryFn: () => fetchEmailDashboard() }),
  list: (page = 1) => ({ queryKey: emailQueryKeys.list(page), queryFn: () => fetchEmailCampaigns(page) }),
};
