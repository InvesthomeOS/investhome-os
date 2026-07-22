import { z } from 'zod';

export const aiConfidenceSchema = z.enum(['unknown', 'low', 'medium', 'high']);

export const aiInsightSchema = z.object({
  id: z.string(),
  category: z.string(),
  severity: z.string(),
  title: z.string(),
  summary: z.string(),
  confidence: aiConfidenceSchema,
  confidence_pct: z.number().nullable().optional(),
  evidence_refs: z.array(z.record(z.string(), z.unknown())).nullable().optional(),
  entity_type: z.string().nullable().optional(),
  entity_id: z.string().nullable().optional(),
  created_at: z.string().nullable().optional(),
});

export const aiRecommendationSchema = z.object({
  id: z.string(),
  recommendation_type: z.string(),
  title: z.string(),
  rationale: z.string(),
  confidence: aiConfidenceSchema,
  confidence_pct: z.number().nullable().optional(),
  evidence_refs: z.array(z.record(z.string(), z.unknown())).nullable().optional(),
  requires_evidence: z.boolean(),
  entity_type: z.string().nullable().optional(),
  entity_id: z.string().nullable().optional(),
  status: z.string(),
  created_at: z.string().nullable().optional(),
});

export const aiPredictionItemSchema = z.object({
  id: z.string().nullable().optional(),
  framework: z.string(),
  prediction_key: z.string(),
  label: z.string(),
  value: z.string().nullable(),
  confidence: aiConfidenceSchema,
  confidence_pct: z.number().nullable().optional(),
  model_version: z.string().nullable().optional(),
  metadata_json: z.record(z.string(), z.unknown()).nullable().optional(),
});

export const aiPredictionFrameworkSchema = z.object({
  framework: z.string(),
  label: z.string(),
  description: z.string(),
  model_connected: z.boolean(),
  items: z.array(aiPredictionItemSchema),
});

export const aiAnomalySchema = z.object({
  id: z.string(),
  anomaly_type: z.string(),
  title: z.string(),
  description: z.string(),
  confidence: aiConfidenceSchema,
  severity: z.string(),
  evidence_refs: z.array(z.record(z.string(), z.unknown())).nullable().optional(),
  is_resolved: z.boolean(),
  detected_at: z.string().nullable().optional(),
});

export const aiBriefingSchema = z.object({
  id: z.string().nullable().optional(),
  period: z.string(),
  title: z.string(),
  summary: z.string(),
  confidence: aiConfidenceSchema,
  sections: z.array(z.record(z.string(), z.unknown())).nullable().optional(),
  generated_at: z.string().nullable().optional(),
});

export const aiHealthCategorySchema = z.object({
  key: z.string(),
  label: z.string(),
  status: z.string(),
  score: z.number().nullable().optional(),
  message: z.string().nullable().optional(),
});

export const aiDashboardSectionSchema = z.object({
  key: z.string(),
  title: z.string(),
  status: z.string(),
  confidence: aiConfidenceSchema,
  items: z.array(z.record(z.string(), z.unknown())),
});

export const aiDashboardSchema = z.object({
  executive_summary: z.string(),
  marketing_health: z.object({
    overall_status: z.string(),
    overall_score: z.number().nullable().optional(),
    confidence: aiConfidenceSchema,
    categories: z.array(aiHealthCategorySchema),
    data_freshness_at: z.string().nullable().optional(),
  }),
  critical_insights: z.array(aiInsightSchema),
  campaign_recommendations: z.array(aiRecommendationSchema),
  budget_recommendations: z.array(aiRecommendationSchema),
  lead_quality: aiDashboardSectionSchema,
  prediction_confidence: aiDashboardSectionSchema,
  anomaly_alerts: z.array(aiAnomalySchema),
  next_best_actions: z.array(aiRecommendationSchema),
  executive_briefing: aiBriefingSchema,
  data_freshness_at: z.string().nullable().optional(),
});

export const copilotResponseSchema = z.object({
  query: z.string(),
  intent: z.string().nullable().optional(),
  answer: z.string(),
  sections: z.array(
    z.object({
      heading: z.string(),
      content: z.string(),
      data_points: z.array(z.record(z.string(), z.unknown())).optional(),
    }),
  ),
  evidence_refs: z.array(z.record(z.string(), z.unknown())),
  confidence: aiConfidenceSchema,
  confidence_pct: z.number().nullable().optional(),
  insufficient_data: z.boolean(),
  model_connected: z.boolean(),
});

export const aiSettingsSchema = z.object({
  copilot_enabled: z.boolean(),
  predictions_enabled: z.boolean(),
  anomaly_detection_enabled: z.boolean(),
  briefing_auto_generate: z.boolean(),
  model_pipeline_connected: z.boolean(),
  default_confidence: aiConfidenceSchema,
});

export type AIInsight = z.infer<typeof aiInsightSchema>;
export type AIRecommendation = z.infer<typeof aiRecommendationSchema>;
export type AIPredictionFramework = z.infer<typeof aiPredictionFrameworkSchema>;
export type AIAnomaly = z.infer<typeof aiAnomalySchema>;
export type AIBriefing = z.infer<typeof aiBriefingSchema>;
export type AIDashboard = z.infer<typeof aiDashboardSchema>;
export type CopilotResponse = z.infer<typeof copilotResponseSchema>;
export type AISettings = z.infer<typeof aiSettingsSchema>;
