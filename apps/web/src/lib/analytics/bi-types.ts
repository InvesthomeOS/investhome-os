export type BiMetricState = 'ready' | 'empty' | 'unavailable' | 'permission';
export type BiChartType = 'line' | 'bar' | 'area' | 'donut' | 'funnel' | 'kpi' | 'table';
export type BiDomain =
  | 'executive'
  | 'sales'
  | 'marketing'
  | 'investor'
  | 'finance'
  | 'project'
  | 'website'
  | 'operational';

export type BiFilterPreset = 'today' | '7d' | '30d' | 'quarter' | 'ytd' | 'custom';

export type BiFilters = {
  date_from?: string;
  date_to?: string;
  comparison?: 'previous_period' | 'none';
  workspace?: string;
  project_id?: string;
  assigned_to?: string;
  lead_source?: string;
  investor_id?: string;
  campaign_id?: string;
  currency?: string;
  status?: string;
  preset?: BiFilterPreset | string;
};

export type MetricComparison = {
  previous?: number | string | null;
  change_pct?: number | null;
  change_available: boolean;
  reason?: string | null;
};

export type BiMetricValue = {
  key: string;
  name: string;
  value: number | string | null;
  state: BiMetricState;
  unit?: string | null;
  currency?: string | null;
  reason?: string | null;
  definition?: string | null;
  source?: string | null;
  date_from?: string | null;
  date_to?: string | null;
  comparison?: MetricComparison | null;
  freshness_at?: string | null;
  freshness_seconds?: number | null;
  drilldown_path?: string | null;
  attribution?: 'first' | 'last' | 'multi' | 'unattributed' | null;
};

export type MetricDefinition = {
  key: string;
  name: string;
  description: string;
  formula: string;
  source: string;
  domain: string;
  unit: string;
  currency_aware: boolean;
  permission: string;
  supports_comparison: boolean;
  freshness_seconds: number;
  drilldown_path: string;
  filters: string[];
};

export type BiOverviewResponse = {
  generated_at: string;
  filters: BiFilters;
  metrics: BiMetricValue[];
  attention_count: number;
  missing_sources: string[];
};

export type BiDomainSeriesPoint = {
  label: string;
  value: number | null;
  state: BiMetricState;
};

export type BiDomainSection = {
  key: string;
  title: string;
  metrics: BiMetricValue[];
  series: BiDomainSeriesPoint[];
  rows: Record<string, unknown>[];
  attribution_breakdown?: Record<string, number> | null;
  notes: string[];
};

export type BiDomainResponse = {
  domain: string;
  generated_at: string;
  filters: BiFilters;
  sections: BiDomainSection[];
  missing_sources: string[];
};

export type DataQualityFinding = {
  key: string;
  severity: 'info' | 'warning' | 'critical';
  title: string;
  description: string;
  source: string;
  metric_keys: string[];
};

export type DataQualityResponse = {
  generated_at: string;
  findings: DataQualityFinding[];
  freshness: Record<string, string | null>;
};

export type BiSavedReport = {
  id: string;
  owner_user_id: string;
  name: string;
  description: string | null;
  domain: string;
  chart_type: string;
  metric_keys: string[];
  filters: Record<string, unknown> | null;
  layout: Record<string, unknown> | null;
  is_shared: boolean;
  created_at: string;
  updated_at: string;
};

export type BiAlertThreshold = {
  id: string;
  metric_key: string;
  name: string;
  operator: string;
  threshold_value: string;
  severity: string;
  enabled: boolean;
  filters: Record<string, unknown> | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
};
