import { apiFetch } from '@/lib/api/client';

export type MarketingLeadSummary = {
  id: string;
  lead_id: string | null;
  contact_id: string | null;
  company_id: string | null;
  campaign_id: string | null;
  source_id: string | null;
  channel_id: string | null;
  utm_data_json: Record<string, unknown> | null;
  marketing_status: string | null;
  verification_status: string | null;
  handoff_status: string;
  created_at: string;
};

export async function fetchMarketingLeads(page = 1, pageSize = 25) {
  return apiFetch<{ items: MarketingLeadSummary[]; total: number; pages: number }>(
    `/marketing/leads?page=${page}&page_size=${pageSize}`,
  );
}

export async function fetchMarketingLeadSummary() {
  return apiFetch<{ total: number; ready_for_handoff: number; blocked: number }>('/marketing/leads/summary');
}

export async function fetchMarketingLeadDetail(contextId: string) {
  return apiFetch<MarketingLeadSummary & { consent_status: Record<string, string | null>; scores_json: Record<string, unknown> | null }>(
    `/marketing/leads/${contextId}`,
  );
}

export async function fetchHandoffReadiness(contextId: string) {
  return apiFetch<{ ready: boolean; blockers: string[] }>(`/marketing/leads/${contextId}/handoff-readiness`);
}

export async function handoffMarketingLead(contextId: string) {
  return apiFetch<{ lead_id: string; linked_existing: boolean }>(
    `/marketing/leads/${contextId}/handoff`,
    { method: 'POST' },
  );
}
