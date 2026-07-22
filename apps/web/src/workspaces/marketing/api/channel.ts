import { apiFetch } from '@/lib/api/client';

export type ProviderStatus = {
  channel: string;
  status: string;
  connected: boolean;
  message: string | null;
};

export type ChannelDashboardBase = {
  provider_status: ProviderStatus;
};

export async function fetchChannelProviderStatuses() {
  return apiFetch<ProviderStatus[]>('/marketing/channel/provider-status');
}

export async function fetchChannelCalendar() {
  return apiFetch<{ items: Array<{ id: string; channel: string; title: string; status: string; scheduled_at: string | null }> }>(
    '/marketing/channel/calendar',
  );
}

export type ReadinessResult = {
  state: string;
  ready: boolean;
  checks: Array<{ key: string; label: string; passed: boolean; message?: string }>;
  recipients?: { total: number; eligible: number; excluded: number };
};

export async function fetchAudienceEligibility(audienceId: string, channel: string) {
  return apiFetch<{ total: number; eligible: number; excluded: number; duplicate_count: number }>(
    `/marketing/channel/eligibility/${audienceId}?channel=${channel}`,
  );
}
