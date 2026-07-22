import { apiFetch } from '@/lib/api/client';

import type {
  MarketingCampaignDetail,
  MarketingCampaignListResponse,
  MarketingCampaignSummary,
} from '../types';

export type CampaignListParams = {
  page?: number;
  page_size?: number;
  status?: string;
  campaign_type?: string;
  objective?: string;
  owner_user_id?: string;
  project_id?: string;
  primary_channel?: string;
  search?: string;
  include_archived?: boolean;
  missing_owner?: boolean;
  missing_budget?: boolean;
  missing_tracking?: boolean;
  my_campaigns?: boolean;
  sort_by?: string;
  sort_dir?: string;
};

export type CampaignSummaryStats = {
  total: number;
  draft: number;
  planning: number;
  pending_approval: number;
  approved: number;
  scheduled: number;
  active: number;
  paused: number;
  completed: number;
  cancelled: number;
  archived: number;
};

export type CampaignSavedView = {
  id: string;
  name: string;
  filters_json: Record<string, unknown> | null;
  is_default: boolean;
  is_shared: boolean;
  created_at: string;
  updated_at: string;
};

export type CampaignReadiness = {
  overall_state: 'ready' | 'warning' | 'blocked';
  checks: { key: string; label_key: string; state: string; message: string | null }[];
  can_activate: boolean;
  blockers: string[];
};

export type CampaignOverview = {
  campaign_id: string;
  readiness: CampaignReadiness;
  budget_summary: Record<string, unknown>;
  leads_summary: Record<string, unknown>;
  conversions_summary: Record<string, unknown>;
  spend_summary: Record<string, unknown>;
  approval_status: string | null;
  notes?: string | null;
  target_project_id?: string | null;
  lead_source_id?: string | null;
  primary_channel?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  remaining_budget?: string | null;
};

export type CampaignBrief = {
  id: string;
  campaign_id: string;
  executive_summary: string | null;
  objectives: string | null;
  messaging: string | null;
  strategies: string | null;
  risks: string | null;
  competitive_context: string | null;
  success_criteria: string | null;
  created_at: string;
  updated_at: string;
};

export type CampaignMilestone = {
  id: string;
  campaign_id: string;
  name: string;
  milestone_type: string;
  status: string;
  due_date: string | null;
  completed_at: string | null;
  notes: string | null;
  sort_order: number;
};

export type CampaignTracking = {
  id: string;
  campaign_id: string;
  utm_source: string | null;
  utm_medium: string | null;
  utm_campaign: string | null;
  utm_term: string | null;
  utm_content: string | null;
  tracking_code: string | null;
  landing_page_url: string | null;
  readiness_status: string;
  validation_errors: string[] | null;
};

export type CampaignBudgetAllocation = {
  id: string;
  campaign_id: string;
  name: string;
  currency: string;
  planned_amount: string | null;
  committed_amount: string | null;
  spent_amount: string | null;
};

export type CampaignLeadContext = {
  id: string;
  lead_id: string | null;
  contact_id: string | null;
  campaign_id: string | null;
  utm_data_json: Record<string, unknown> | null;
  created_at: string;
};

export type CampaignInput = {
  name: string;
  code?: string | null;
  description?: string | null;
  objective?: string;
  campaign_type?: string;
  priority?: string;
  owner_user_id?: string | null;
  team_id?: string | null;
  company_id?: string | null;
  target_project_id?: string | null;
  lead_source_id?: string | null;
  primary_channel?: string | null;
  project_ids?: string[] | null;
  property_ids?: string[] | null;
  audience_ids?: string[] | null;
  segment_ids?: string[] | null;
  channel_ids?: string[] | null;
  start_date?: string | null;
  end_date?: string | null;
  timezone?: string | null;
  budget_amount?: string | null;
  budget_currency?: string | null;
  targets_json?: Record<string, unknown> | null;
  tags?: string[] | null;
  notes?: string | null;
  metadata_json?: Record<string, unknown> | null;
};

function buildQuery(params: Record<string, string | number | boolean | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : '';
}

export async function fetchCampaigns(params: CampaignListParams = {}): Promise<MarketingCampaignListResponse> {
  return apiFetch<MarketingCampaignListResponse>(`/marketing/campaigns${buildQuery(params)}`);
}

export async function fetchCampaignSummary(myCampaigns = false): Promise<CampaignSummaryStats> {
  return apiFetch<CampaignSummaryStats>(`/marketing/campaigns/summary${buildQuery({ my_campaigns: myCampaigns })}`);
}

export async function fetchCampaignWorkspaceOverview() {
  return apiFetch<import('../types').MarketingWorkspaceOverview>('/marketing/campaigns/overview');
}

export async function exportCampaignsCsv(params: CampaignListParams = {}): Promise<Blob> {
  const { getApiBaseUrl } = await import('@/lib/api/client');
  const response = await fetch(`${getApiBaseUrl()}/marketing/campaigns/export${buildQuery(params)}`, {
    credentials: 'include',
  });
  if (!response.ok) {
    throw new Error('Campaign export failed');
  }
  return response.blob();
}

export async function fetchCampaign(id: string): Promise<MarketingCampaignDetail> {
  return apiFetch<MarketingCampaignDetail>(`/marketing/campaigns/${id}`);
}

export async function createCampaign(payload: CampaignInput): Promise<{ campaign: MarketingCampaignDetail }> {
  return apiFetch('/marketing/campaigns', { method: 'POST', body: JSON.stringify(payload) });
}

export async function updateCampaign(
  id: string,
  payload: Partial<CampaignInput> & { status?: string },
): Promise<{ campaign: MarketingCampaignDetail }> {
  return apiFetch(`/marketing/campaigns/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
}

export async function duplicateCampaign(
  id: string,
  payload: { name?: string; include_budget?: boolean; include_tracking?: boolean },
): Promise<{ campaign: MarketingCampaignDetail }> {
  return apiFetch(`/marketing/campaigns/${id}/duplicate`, { method: 'POST', body: JSON.stringify(payload) });
}

export async function archiveCampaign(id: string, reason: string): Promise<{ campaign: MarketingCampaignDetail }> {
  return apiFetch(`/marketing/campaigns/${id}/archive`, { method: 'POST', body: JSON.stringify({ reason }) });
}

export async function restoreCampaign(id: string): Promise<{ campaign: MarketingCampaignDetail }> {
  return apiFetch(`/marketing/campaigns/${id}/restore`, { method: 'POST' });
}

export async function activateCampaign(id: string): Promise<{ campaign: MarketingCampaignDetail }> {
  return apiFetch(`/marketing/campaigns/${id}/activate`, { method: 'POST' });
}

export async function pauseCampaign(id: string): Promise<{ campaign: MarketingCampaignDetail }> {
  return apiFetch(`/marketing/campaigns/${id}/pause`, { method: 'POST' });
}

export async function submitCampaignApproval(id: string): Promise<{ campaign: MarketingCampaignDetail }> {
  return apiFetch(`/marketing/campaigns/${id}/submit-approval`, { method: 'POST' });
}

export async function approveCampaign(id: string, notes?: string): Promise<{ campaign: MarketingCampaignDetail }> {
  return apiFetch(`/marketing/campaigns/${id}/approve`, { method: 'POST', body: JSON.stringify({ notes }) });
}

export async function bulkCampaignAction(
  campaignIds: string[],
  action: string,
): Promise<{ eligible_count: number; ineligible_count: number; ineligible: { id: string; reason: string }[] }> {
  return apiFetch('/marketing/campaigns/bulk', {
    method: 'POST',
    body: JSON.stringify({ campaign_ids: campaignIds, action }),
  });
}

export async function fetchCampaignOverview(id: string): Promise<CampaignOverview> {
  return apiFetch<CampaignOverview>(`/marketing/campaigns/${id}/overview`);
}

export async function fetchCampaignReadiness(id: string): Promise<CampaignReadiness> {
  return apiFetch<CampaignReadiness>(`/marketing/campaigns/${id}/readiness`);
}

export async function fetchCampaignBrief(id: string): Promise<CampaignBrief> {
  return apiFetch<CampaignBrief>(`/marketing/campaigns/${id}/brief`);
}

export async function updateCampaignBrief(id: string, payload: Partial<CampaignBrief>): Promise<CampaignBrief> {
  return apiFetch(`/marketing/campaigns/${id}/brief`, { method: 'PUT', body: JSON.stringify(payload) });
}

export async function fetchCampaignMilestones(id: string): Promise<CampaignMilestone[]> {
  return apiFetch<CampaignMilestone[]>(`/marketing/campaigns/${id}/milestones`);
}

export async function fetchCampaignTracking(id: string): Promise<CampaignTracking> {
  return apiFetch<CampaignTracking>(`/marketing/campaigns/${id}/tracking`);
}

export async function updateCampaignTracking(
  id: string,
  payload: Partial<CampaignTracking>,
): Promise<CampaignTracking> {
  return apiFetch(`/marketing/campaigns/${id}/tracking`, { method: 'PUT', body: JSON.stringify(payload) });
}

export async function validateCampaignTracking(id: string): Promise<CampaignTracking> {
  return apiFetch(`/marketing/campaigns/${id}/tracking/validate`, { method: 'POST' });
}

export async function fetchCampaignBudget(id: string): Promise<CampaignBudgetAllocation[]> {
  return apiFetch<CampaignBudgetAllocation[]>(`/marketing/campaigns/${id}/budget`);
}

export async function fetchCampaignLeads(id: string): Promise<CampaignLeadContext[]> {
  return apiFetch<CampaignLeadContext[]>(`/marketing/campaigns/${id}/leads`);
}

export async function fetchCampaignSavedViews(): Promise<CampaignSavedView[]> {
  return apiFetch<CampaignSavedView[]>('/marketing/campaigns/saved-views');
}

export async function createCampaignSavedView(payload: {
  name: string;
  filters_json?: Record<string, unknown>;
}): Promise<CampaignSavedView> {
  return apiFetch('/marketing/campaigns/saved-views', { method: 'POST', body: JSON.stringify(payload) });
}

export type { MarketingCampaignSummary };
