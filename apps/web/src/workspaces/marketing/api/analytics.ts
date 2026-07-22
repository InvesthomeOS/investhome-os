import { apiFetch } from '@/lib/api/client';

import type {
  DashboardSavedView,
  ExecutiveDashboardData,
  MarketingDashboardFilters,
  MarketingTimeFilter,
  MetricValue,
  WidgetConfig,
} from '@/workspaces/marketing/schemas/analytics';

export type AnalyticsQueryParams = {
  preset?: MarketingTimeFilter['preset'];
  timezone?: string;
  campaign_id?: string;
  channel_id?: string;
  source_id?: string;
};

function buildSearch(params: AnalyticsQueryParams = {}): string {
  const search = new URLSearchParams();
  if (params.preset) search.set('preset', params.preset);
  if (params.timezone) search.set('timezone', params.timezone);
  if (params.campaign_id) search.set('campaign_id', params.campaign_id);
  if (params.channel_id) search.set('channel_id', params.channel_id);
  if (params.source_id) search.set('source_id', params.source_id);
  const qs = search.toString();
  return qs ? `?${qs}` : '';
}

export async function fetchExecutiveDashboard(params: AnalyticsQueryParams = {}): Promise<ExecutiveDashboardData> {
  return apiFetch<ExecutiveDashboardData>(`/marketing/analytics/executive${buildSearch(params)}`);
}

export async function fetchMarketingKPIs(params: AnalyticsQueryParams = {}): Promise<{ kpis: MetricValue[] }> {
  return apiFetch<{ kpis: MetricValue[] }>(`/marketing/analytics/kpis${buildSearch(params)}`);
}

export async function fetchMarketingHealth(): Promise<ExecutiveDashboardData['health']> {
  return apiFetch<ExecutiveDashboardData['health']>('/marketing/analytics/health');
}

export async function fetchTrackingHealth(): Promise<ExecutiveDashboardData['tracking_health']> {
  return apiFetch<ExecutiveDashboardData['tracking_health']>('/marketing/analytics/health/tracking');
}

export async function fetchAttributionHealth(): Promise<ExecutiveDashboardData['attribution_health']> {
  return apiFetch<ExecutiveDashboardData['attribution_health']>('/marketing/analytics/health/attribution');
}

export async function fetchDataHealth(): Promise<ExecutiveDashboardData['data_health']> {
  return apiFetch<ExecutiveDashboardData['data_health']>('/marketing/analytics/health/data');
}

export async function fetchMarketingFunnel(params: AnalyticsQueryParams = {}): Promise<ExecutiveDashboardData['funnel']> {
  return apiFetch<ExecutiveDashboardData['funnel']>(`/marketing/analytics/funnel${buildSearch(params)}`);
}

export async function fetchDashboardWidgets(
  dashboardKey = 'executive',
  params: AnalyticsQueryParams = {},
): Promise<{ widgets: WidgetConfig[]; dashboard_key: string }> {
  const search = new URLSearchParams(buildSearch(params).replace('?', ''));
  search.set('dashboard_key', dashboardKey);
  return apiFetch<{ widgets: WidgetConfig[]; dashboard_key: string }>(`/marketing/analytics/widgets?${search.toString()}`);
}

export async function fetchExecutiveAlerts(): Promise<{ items: ExecutiveDashboardData['alerts'] }> {
  return apiFetch<{ items: ExecutiveDashboardData['alerts'] }>('/marketing/analytics/alerts');
}

export async function fetchExecutiveRecommendations(): Promise<{ items: ExecutiveDashboardData['recommendations'] }> {
  return apiFetch<{ items: ExecutiveDashboardData['recommendations'] }>('/marketing/analytics/recommendations');
}

export async function fetchDashboardSavedViews(dashboardKey?: string): Promise<DashboardSavedView[]> {
  const qs = dashboardKey ? `?dashboard_key=${dashboardKey}` : '';
  return apiFetch<DashboardSavedView[]>(`/marketing/analytics/saved-views${qs}`);
}

export async function createDashboardSavedView(payload: {
  name: string;
  dashboard_key?: string;
  filters_json?: MarketingDashboardFilters;
  time_filter_json?: MarketingTimeFilter;
}): Promise<DashboardSavedView> {
  return apiFetch<DashboardSavedView>('/marketing/analytics/saved-views', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function deleteDashboardSavedView(viewId: string): Promise<void> {
  await apiFetch<void>(`/marketing/analytics/saved-views/${viewId}`, { method: 'DELETE' });
}
