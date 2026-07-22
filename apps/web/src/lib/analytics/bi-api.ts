import { apiFetch } from '@/lib/api/client';

import type {
  BiAlertThreshold,
  BiDomainResponse,
  BiFilters,
  BiOverviewResponse,
  BiSavedReport,
  DataQualityResponse,
  MetricDefinition,
} from './bi-types';

function toQuery(filters: BiFilters, extra?: Record<string, string | undefined>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries({ ...filters, ...extra })) {
    if (value === undefined || value === null || value === '') continue;
    params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `?${qs}` : '';
}

export async function fetchBiOverview(filters: BiFilters = {}): Promise<BiOverviewResponse> {
  return apiFetch<BiOverviewResponse>(`/analytics/overview${toQuery(filters)}`);
}

export async function fetchBiDomain(
  domain: string,
  filters: BiFilters = {},
): Promise<BiDomainResponse> {
  return apiFetch<BiDomainResponse>(`/analytics/domains/${domain}${toQuery(filters)}`);
}

export async function fetchMetricRegistry(domain?: string): Promise<MetricDefinition[]> {
  return apiFetch<MetricDefinition[]>(
    `/analytics/metrics${domain ? `?domain=${encodeURIComponent(domain)}` : ''}`,
  );
}

export async function fetchDataQuality(): Promise<DataQualityResponse> {
  return apiFetch<DataQualityResponse>('/analytics/data-quality');
}

export async function fetchSavedReports(): Promise<BiSavedReport[]> {
  return apiFetch<BiSavedReport[]>('/analytics/saved-reports');
}

export async function createSavedReport(payload: {
  name: string;
  description?: string;
  domain: string;
  chart_type: string;
  metric_keys: string[];
  filters?: Record<string, unknown>;
  is_shared?: boolean;
}): Promise<BiSavedReport> {
  return apiFetch<BiSavedReport>('/analytics/saved-reports', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function deleteSavedReport(id: string): Promise<void> {
  await apiFetch(`/analytics/saved-reports/${id}`, { method: 'DELETE' });
}

export async function fetchAlertThresholds(): Promise<BiAlertThreshold[]> {
  return apiFetch<BiAlertThreshold[]>('/analytics/alert-thresholds');
}

export async function createAlertThreshold(payload: {
  metric_key: string;
  name: string;
  operator: 'gt' | 'gte' | 'lt' | 'lte' | 'eq';
  threshold_value: string;
  severity?: 'information' | 'warning' | 'critical';
  enabled?: boolean;
}): Promise<BiAlertThreshold> {
  return apiFetch<BiAlertThreshold>('/analytics/alert-thresholds', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function biExportUrl(
  format: 'csv' | 'xlsx' | 'pdf' | 'print',
  filters: BiFilters,
  domain = 'executive',
  metricKeys: string[] = [],
): string {
  const params = new URLSearchParams();
  params.set('format', format);
  params.set('domain', domain);
  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === null || value === '') continue;
    params.set(key, String(value));
  }
  for (const key of metricKeys) {
    params.append('metric_keys', key);
  }
  return `/analytics/export?${params.toString()}`;
}
