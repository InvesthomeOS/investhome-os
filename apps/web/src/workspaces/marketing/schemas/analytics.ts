import { z } from 'zod';

export const marketingTimeFilterSchema = z.object({
  preset: z.enum([
    'today',
    'yesterday',
    'last_7_days',
    'last_30_days',
    'last_90_days',
    'this_month',
    'previous_month',
    'quarter',
    'year',
    'custom',
  ]).default('last_30_days'),
  timezone: z.string().default('UTC'),
  start_at: z.string().nullable().optional(),
  end_at: z.string().nullable().optional(),
});

export const marketingDashboardFiltersSchema = z.object({
  campaign_id: z.string().uuid().nullable().optional(),
  project_id: z.string().uuid().nullable().optional(),
  property_id: z.string().uuid().nullable().optional(),
  country: z.string().nullable().optional(),
  region: z.string().nullable().optional(),
  language: z.string().nullable().optional(),
  audience_id: z.string().uuid().nullable().optional(),
  segment_id: z.string().uuid().nullable().optional(),
  channel_id: z.string().uuid().nullable().optional(),
  source_id: z.string().uuid().nullable().optional(),
  owner_user_id: z.string().uuid().nullable().optional(),
  team_id: z.string().uuid().nullable().optional(),
  lead_type: z.string().nullable().optional(),
});

export const metricValueSchema = z.object({
  key: z.string(),
  label: z.string(),
  state: z.enum(['ready', 'unknown', 'unavailable', 'not_connected', 'permission_restricted', 'empty']),
  value: z.union([z.number(), z.string()]).nullable().optional(),
  unit: z.string().nullable().optional(),
  previous_value: z.number().nullable().optional(),
  change_percent: z.number().nullable().optional(),
  freshness_at: z.string().nullable().optional(),
  evidence: z.record(z.string(), z.unknown()).nullable().optional(),
});

export const widgetConfigSchema = z.object({
  key: z.string(),
  title: z.string(),
  subtitle: z.string().nullable().optional(),
  widget_type: z.string(),
  state: z.string(),
  refresh_interval_seconds: z.number().nullable().optional(),
  export_enabled: z.boolean().optional(),
  fullscreen_enabled: z.boolean().optional(),
  collapse_enabled: z.boolean().optional(),
  filters_enabled: z.boolean().optional(),
  data: z.union([z.record(z.string(), z.unknown()), z.array(z.unknown())]).nullable().optional(),
});

export const funnelStageSchema = z.object({
  key: z.string(),
  label: z.string(),
  count: z.number().nullable().optional(),
  state: z.string(),
  conversion_percent: z.number().nullable().optional(),
  drop_off_percent: z.number().nullable().optional(),
});

export const healthCategorySchema = z.object({
  key: z.string(),
  label: z.string(),
  status: z.enum(['healthy', 'warning', 'critical', 'unknown']),
  summary: z.string().nullable().optional(),
  evidence: z.record(z.string(), z.unknown()).nullable().optional(),
});

export const executiveAlertSchema = z.object({
  id: z.string().uuid(),
  title: z.string(),
  message: z.string().nullable().optional(),
  category: z.string(),
  severity: z.string(),
  evidence_json: z.record(z.string(), z.unknown()).nullable().optional(),
  is_resolved: z.boolean(),
  created_at: z.string(),
});

export const recommendationItemSchema = z.object({
  id: z.string().uuid(),
  title: z.string(),
  description: z.string().nullable().optional(),
  recommendation_type: z.string(),
  rationale: z.string().nullable().optional(),
  confidence_level: z.string().nullable().optional(),
  status: z.string(),
  created_at: z.string(),
});

export const executiveDashboardSchema = z.object({
  kpis: z.array(metricValueSchema),
  funnel: z.object({
    stages: z.array(funnelStageSchema),
    time_filter: marketingTimeFilterSchema,
    filters: marketingDashboardFiltersSchema,
  }),
  health: z.object({
    overall_status: z.string(),
    categories: z.array(healthCategorySchema),
    computed_at: z.string(),
    snapshot_id: z.string().uuid().nullable().optional(),
  }),
  tracking_health: z.object({
    overall_status: z.string(),
    categories: z.array(healthCategorySchema),
    computed_at: z.string(),
  }),
  attribution_health: z.object({
    overall_status: z.string(),
    categories: z.array(healthCategorySchema),
    computed_at: z.string(),
  }),
  data_health: z.object({
    overall_status: z.string(),
    categories: z.array(healthCategorySchema),
    computed_at: z.string(),
  }),
  alerts: z.array(executiveAlertSchema),
  recommendations: z.array(recommendationItemSchema),
  active_campaigns: z.array(z.object({
    id: z.string().uuid(),
    name: z.string(),
    status: z.string(),
    lead_count: z.number().nullable().optional(),
  })),
  channel_summaries: z.array(z.object({
    id: z.string().uuid(),
    name: z.string(),
    category: z.string(),
    connection_status: z.string(),
    lead_count: z.number().nullable().optional(),
  })),
  widgets: z.array(widgetConfigSchema),
  time_filter: marketingTimeFilterSchema,
  filters: marketingDashboardFiltersSchema,
  data_freshness_at: z.string().nullable().optional(),
});

export const dashboardSavedViewSchema = z.object({
  id: z.string().uuid(),
  user_id: z.string().uuid(),
  name: z.string(),
  dashboard_key: z.string(),
  filters_json: z.record(z.string(), z.unknown()).nullable().optional(),
  time_filter_json: z.record(z.string(), z.unknown()).nullable().optional(),
  is_default: z.boolean(),
  is_shared: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
});

export type MarketingTimeFilter = z.infer<typeof marketingTimeFilterSchema>;
export type MarketingDashboardFilters = z.infer<typeof marketingDashboardFiltersSchema>;
export type MetricValue = z.infer<typeof metricValueSchema>;
export type WidgetConfig = z.infer<typeof widgetConfigSchema>;
export type FunnelStage = z.infer<typeof funnelStageSchema>;
export type HealthCategory = z.infer<typeof healthCategorySchema>;
export type ExecutiveAlert = z.infer<typeof executiveAlertSchema>;
export type RecommendationItem = z.infer<typeof recommendationItemSchema>;
export type ExecutiveDashboardData = z.infer<typeof executiveDashboardSchema>;
export type DashboardSavedView = z.infer<typeof dashboardSavedViewSchema>;
