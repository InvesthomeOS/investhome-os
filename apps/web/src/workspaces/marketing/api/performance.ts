import { apiFetch } from '@/lib/api/client';

export type PerformanceMetric = {
  value: string | number | null;
  state: string;
  reason?: string | null;
};

export type PerformanceOverview = {
  total_campaigns: PerformanceMetric;
  active_campaigns: PerformanceMetric;
  total_budget: PerformanceMetric;
  total_spend: PerformanceMetric;
  total_leads: PerformanceMetric;
  qualified_leads: PerformanceMetric;
  converted_leads: PerformanceMetric;
  avg_cpl: PerformanceMetric;
  avg_conversion_rate: PerformanceMetric;
  campaigns_requiring_attention: PerformanceMetric;
  currency?: string | null;
};

export type CampaignPerformanceMetrics = {
  campaign_id: string;
  campaign_name: string;
  campaign_type?: string | null;
  primary_channel?: string | null;
  status: string;
  total_leads: PerformanceMetric;
  qualified_leads: PerformanceMetric;
  converted_leads: PerformanceMetric;
  actual_spend: PerformanceMetric;
  cpl: PerformanceMetric;
  conversion_rate: PerformanceMetric;
};

export type CampaignPerformanceList = {
  items: CampaignPerformanceMetrics[];
  page: number;
  page_size: number;
  total: number;
};

export type CampaignLeadBreakdown = {
  items: Array<{
    lead_id: string;
    full_name: string;
    email?: string | null;
    status: string;
    attribution_status: string;
    attribution_source?: string | null;
    utm_source?: string | null;
    first_touch_at?: string | null;
    converted_at?: string | null;
    created_at: string;
  }>;
  page: number;
  page_size: number;
  total: number;
  status_breakdown: Record<string, number>;
};

export type ChannelPerformanceList = {
  items: Array<{
    channel: string;
    campaign_count: number;
    spend: PerformanceMetric;
    leads: PerformanceMetric;
    qualified_leads: PerformanceMetric;
    conversions: PerformanceMetric;
    cpl: PerformanceMetric;
    conversion_rate: PerformanceMetric;
  }>;
};

export type ProjectPerformanceList = {
  items: Array<{
    project_id?: string | null;
    project_name: string;
    campaign_count: number;
    spend: PerformanceMetric;
    leads: PerformanceMetric;
    qualified_leads: PerformanceMetric;
    conversions: PerformanceMetric;
    cpl: PerformanceMetric;
    conversion_rate: PerformanceMetric;
  }>;
};

export type PerformanceQueryParams = {
  date_from?: string;
  date_to?: string;
  campaign_id?: string;
  project_id?: string;
  campaign_type?: string;
  owner_user_id?: string;
  status?: string;
  company_id?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
};

function buildSearch(params: PerformanceQueryParams = {}): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, String(value));
    }
  });
  const qs = search.toString();
  return qs ? `?${qs}` : '';
}

export async function fetchPerformanceOverview(params: PerformanceQueryParams = {}): Promise<PerformanceOverview> {
  return apiFetch<PerformanceOverview>(`/marketing/performance/overview${buildSearch(params)}`);
}

export async function fetchCampaignPerformanceList(
  params: PerformanceQueryParams = {},
): Promise<CampaignPerformanceList> {
  return apiFetch<CampaignPerformanceList>(`/marketing/performance/campaigns${buildSearch(params)}`);
}

export async function fetchCampaignPerformanceDetail(campaignId: string, params: PerformanceQueryParams = {}) {
  return apiFetch(`/marketing/performance/campaigns/${campaignId}${buildSearch(params)}`);
}

export async function fetchCampaignLeadBreakdown(
  campaignId: string,
  params: PerformanceQueryParams = {},
): Promise<CampaignLeadBreakdown> {
  return apiFetch<CampaignLeadBreakdown>(`/marketing/performance/campaigns/${campaignId}/leads${buildSearch(params)}`);
}

export async function fetchChannelPerformance(params: PerformanceQueryParams = {}): Promise<ChannelPerformanceList> {
  return apiFetch<ChannelPerformanceList>(`/marketing/performance/channels${buildSearch(params)}`);
}

export async function fetchProjectPerformance(params: PerformanceQueryParams = {}): Promise<ProjectPerformanceList> {
  return apiFetch<ProjectPerformanceList>(`/marketing/performance/projects${buildSearch(params)}`);
}

export async function exportPerformanceReport(reportType: string, params: PerformanceQueryParams = {}): Promise<Blob> {
  const response = await fetch(`/api/marketing/performance/export/${reportType}${buildSearch(params)}`, {
    credentials: 'include',
  });
  if (!response.ok) {
    throw new Error('Export failed');
  }
  return response.blob();
}
