import { apiFetch } from '@/lib/api/client';

export type PlatformOverview = {
  schema_name: string;
  isolation: string;
  oltp_queries_replaced: boolean;
  reporting_timezones: string[];
  supported_currencies: string[];
  reporting_currencies: string[];
  last_run: {
    id: string | null;
    status: string | null;
    mode: string | null;
    started_at: string | null;
    finished_at: string | null;
    rows_written: number;
    rows_rejected: number;
    error_message: string | null;
  };
  ingestion_counts: { succeeded: number; failed: number };
  metric_catalog: { certified: number; draft: number };
  row_counts: Record<string, number>;
  cost_estimate_monthly_usd: Record<string, unknown>;
};

export type IngestionRun = {
  id: string;
  domain: string;
  job_name: string;
  mode: string;
  status: string;
  rows_read: number;
  rows_written: number;
  rows_rejected: number;
  reject_reasons_json?: unknown[] | null;
  error_message?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
};

export type MetricCatalogEntry = {
  id: string;
  metric_key: string;
  name: string;
  domain: string;
  formula: string;
  source: string;
  grain: string;
  certification_status: string;
  classification: string;
  version: number;
};

export type LineageEdge = {
  id: string;
  source_object: string;
  target_object: string;
  relation: string;
  domain?: string | null;
};

export type DqCheck = {
  id: string;
  check_key: string;
  domain: string;
  status: string;
  expected_value?: string | null;
  actual_value?: string | null;
  message: string;
  checked_at?: string | null;
};

export type ReconResponse = {
  certified_keys: string[];
  checked_at: string;
  summary: Record<string, number>;
  checks: Array<{
    metric_key: string;
    domain: string;
    oltp_value: number | null;
    warehouse_value: number | null;
    status: string;
    note: string;
  }>;
  overall: string;
};

export type GovernedDataset = {
  id: string;
  dataset_key: string;
  name: string;
  description?: string | null;
  mart_table: string;
  allowed_columns_json: string[];
  classification: string;
  requires_permission: string;
};

export type ExploreResponse = {
  dataset_key?: string;
  mart_table?: string;
  classification?: string;
  allowed_columns: string[];
  row_count: number;
  rows: Record<string, unknown>[];
  error?: string | null;
};

export async function fetchPlatformOverview(): Promise<PlatformOverview> {
  return apiFetch<PlatformOverview>('/analytics/warehouse/overview');
}

export async function fetchIngestionRuns(): Promise<IngestionRun[]> {
  return apiFetch<IngestionRun[]>('/analytics/warehouse/ingestion-runs');
}

export async function triggerIngestion(
  mode: 'incremental' | 'full_refresh' = 'incremental',
): Promise<IngestionRun> {
  return apiFetch<IngestionRun>('/analytics/warehouse/ingestion-runs', {
    method: 'POST',
    body: JSON.stringify({ mode }),
  });
}

export async function fetchWarehouseMetricCatalog(
  certification?: string,
): Promise<MetricCatalogEntry[]> {
  const qs = certification ? `?certification=${encodeURIComponent(certification)}` : '';
  return apiFetch<MetricCatalogEntry[]>(`/analytics/warehouse/metric-catalog${qs}`);
}

export async function fetchLineage(): Promise<LineageEdge[]> {
  return apiFetch<LineageEdge[]>('/analytics/warehouse/lineage');
}

export async function fetchWarehouseDq(): Promise<DqCheck[]> {
  return apiFetch<DqCheck[]>('/analytics/warehouse/data-quality');
}

export async function runWarehouseDq(): Promise<DqCheck[]> {
  return apiFetch<DqCheck[]>('/analytics/warehouse/data-quality/run', { method: 'POST' });
}

export async function fetchReconciliation(): Promise<ReconResponse> {
  return apiFetch<ReconResponse>('/analytics/warehouse/reconciliation');
}

export async function fetchGovernedDatasets(): Promise<GovernedDataset[]> {
  return apiFetch<GovernedDataset[]>('/analytics/warehouse/datasets');
}

export async function exploreDataset(datasetKey: string): Promise<ExploreResponse> {
  return apiFetch<ExploreResponse>(`/analytics/warehouse/explore/${encodeURIComponent(datasetKey)}`);
}

export async function auditWarehouseExport(datasetKey: string, rowCount?: number): Promise<void> {
  const params = new URLSearchParams({ dataset_key: datasetKey, format: 'csv' });
  if (rowCount != null) params.set('row_count', String(rowCount));
  await apiFetch(`/analytics/warehouse/exports/audit?${params.toString()}`, { method: 'POST' });
}
