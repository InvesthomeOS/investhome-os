import type {
  MarketingCampaignDetail,
  MarketingCampaignListResponse,
  MarketingDashboardData,
  MarketingNavigationData,
  MarketingProviderStatus,
  MarketingQuickActionsData,
} from '@/workspaces/marketing/types';

import { apiFetch } from '@/lib/api/client';

export async function fetchMarketingDashboard(): Promise<MarketingDashboardData> {
  return apiFetch<MarketingDashboardData>('/marketing/dashboard');
}

export async function fetchMarketingNavigation(): Promise<MarketingNavigationData> {
  return apiFetch<MarketingNavigationData>('/marketing/navigation');
}

export async function fetchMarketingQuickActions(): Promise<MarketingQuickActionsData> {
  return apiFetch<MarketingQuickActionsData>('/marketing/quick-actions');
}

export async function fetchMarketingProviderStatuses(): Promise<{ providers: MarketingProviderStatus[] }> {
  return apiFetch<{ providers: MarketingProviderStatus[] }>('/marketing/provider-statuses');
}

export type CampaignListParams = {
  page?: number;
  page_size?: number;
  status?: string;
  include_archived?: boolean;
};

export async function fetchCampaigns(params: CampaignListParams = {}): Promise<MarketingCampaignListResponse> {
  const search = new URLSearchParams();
  search.set('page', String(params.page ?? 1));
  search.set('page_size', String(params.page_size ?? 25));
  if (params.status) search.set('status', params.status);
  if (params.include_archived) search.set('include_archived', 'true');
  return apiFetch<MarketingCampaignListResponse>(`/marketing/campaigns?${search.toString()}`);
}

export async function fetchCampaign(campaignId: string): Promise<MarketingCampaignDetail> {
  return apiFetch<MarketingCampaignDetail>(`/marketing/campaigns/${campaignId}`);
}

export type CreateCampaignPayload = {
  name: string;
  code?: string | null;
  description?: string | null;
  objective?: string;
  campaign_type?: string;
  status?: string;
  priority?: string;
};

export async function createCampaign(payload: CreateCampaignPayload): Promise<{ campaign: MarketingCampaignDetail }> {
  return apiFetch<{ campaign: MarketingCampaignDetail }>('/marketing/campaigns', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateCampaign(
  campaignId: string,
  payload: Partial<CreateCampaignPayload>,
): Promise<{ campaign: MarketingCampaignDetail }> {
  return apiFetch<{ campaign: MarketingCampaignDetail }>(`/marketing/campaigns/${campaignId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function activateCampaign(campaignId: string): Promise<{ campaign: MarketingCampaignDetail }> {
  return apiFetch<{ campaign: MarketingCampaignDetail }>(`/marketing/campaigns/${campaignId}/activate`, {
    method: 'POST',
  });
}

export async function pauseCampaign(campaignId: string): Promise<{ campaign: MarketingCampaignDetail }> {
  return apiFetch<{ campaign: MarketingCampaignDetail }>(`/marketing/campaigns/${campaignId}/pause`, {
    method: 'POST',
  });
}

export async function archiveCampaign(campaignId: string): Promise<{ campaign: MarketingCampaignDetail }> {
  return apiFetch<{ campaign: MarketingCampaignDetail }>(`/marketing/campaigns/${campaignId}/archive`, {
    method: 'POST',
  });
}

export async function fetchAudiences(page = 1, pageSize = 25) {
  return apiFetch<{ items: unknown[]; total: number }>(`/marketing/audiences?page=${page}&page_size=${pageSize}`);
}

export async function fetchContentAssets(page = 1, pageSize = 25) {
  return apiFetch<{ items: unknown[]; total: number }>(`/marketing/content?page=${page}&page_size=${pageSize}`);
}

export async function fetchMarketingEvents(page = 1, pageSize = 25) {
  return apiFetch<{ items: unknown[]; total: number }>(`/marketing/events?page=${page}&page_size=${pageSize}`);
}

export async function fetchMarketingBudgets(page = 1, pageSize = 25) {
  return apiFetch<{ items: unknown[]; total: number }>(`/marketing/budgets?page=${page}&page_size=${pageSize}`);
}

export async function fetchMarketingApprovals(page = 1, pageSize = 25) {
  return apiFetch<{ items: unknown[]; total: number }>(`/marketing/approvals?page=${page}&page_size=${pageSize}`);
}

export async function fetchMarketingAlerts(page = 1, pageSize = 25) {
  return apiFetch<{ items: unknown[]; total: number }>(`/marketing/alerts?page=${page}&page_size=${pageSize}`);
}

export async function fetchMarketingRecommendations(page = 1, pageSize = 25) {
  return apiFetch<{ items: unknown[]; total: number }>(
    `/marketing/recommendations?page=${page}&page_size=${pageSize}`,
  );
}

export async function fetchMarketingChannels() {
  return apiFetch<{ items: unknown[] }>('/marketing/channels');
}
