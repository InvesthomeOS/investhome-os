import { z } from 'zod';

export const utmParamsSchema = z.object({
  utm_source: z.string().max(120).optional().nullable(),
  utm_medium: z.string().max(120).optional().nullable(),
  utm_campaign: z.string().max(120).optional().nullable(),
  utm_term: z.string().max(120).optional().nullable(),
  utm_content: z.string().max(120).optional().nullable(),
});

export const campaignSchema = z.object({
  name: z.string().min(1).max(255),
  code: z.string().max(80).optional().nullable(),
  description: z.string().optional().nullable(),
  objective: z.enum([
    'awareness',
    'reach',
    'engagement',
    'traffic',
    'lead_generation',
    'conversion',
    'retention',
    'revenue',
  ]).default('awareness'),
  campaign_type: z.enum([
    'brand_awareness',
    'lead_generation',
    'investor_acquisition',
    'buyer_acquisition',
    'broker_acquisition',
    'property_launch',
    'project_launch',
    'retargeting',
    'nurture',
    'event_promotion',
    'other',
  ]).default('other'),
  status: z.enum([
    'draft',
    'planning',
    'pending_approval',
    'approved',
    'scheduled',
    'active',
    'paused',
    'completed',
    'cancelled',
    'archived',
  ]).default('draft'),
  priority: z.enum(['low', 'normal', 'high', 'urgent']).default('normal'),
  budget_amount: z.string().optional().nullable(),
  budget_currency: z.string().max(3).optional().nullable(),
  tags: z.array(z.string()).optional().nullable(),
});

export const audienceSchema = z.object({
  name: z.string().min(1).max(255),
  description: z.string().optional().nullable(),
  audience_type: z.enum(['static', 'dynamic', 'lookalike', 'imported', 'crm_segment']),
  source: z.string().optional().nullable(),
  language: z.string().max(10).optional().nullable(),
});

export const segmentSchema = z.object({
  name: z.string().min(1).max(255),
  description: z.string().optional().nullable(),
  segment_type: z.enum(['static', 'dynamic', 'behavioral']),
  refresh_frequency: z.string().optional().nullable(),
  visibility: z.enum(['private', 'team', 'organization']).default('team'),
});

export const leadSourceSchema = z.object({
  name: z.string().min(1).max(255),
  source_type: z.enum(['organic', 'paid', 'referral', 'event', 'partner', 'direct', 'social', 'email', 'other']),
  tracking_code: z.string().max(120).optional().nullable(),
  description: z.string().optional().nullable(),
});

export const leadContextSchema = z.object({
  lead_id: z.string().uuid().optional().nullable(),
  contact_id: z.string().uuid().optional().nullable(),
  company_id: z.string().uuid().optional().nullable(),
  campaign_id: z.string().uuid().optional().nullable(),
  source_id: z.string().uuid().optional().nullable(),
  utm_data: utmParamsSchema.optional().nullable(),
});

export const contentAssetSchema = z.object({
  name: z.string().min(1).max(255),
  content_type: z.enum([
    'article',
    'blog_post',
    'social_post',
    'email_template',
    'landing_page',
    'video',
    'image',
    'document',
    'ad_creative',
    'other',
  ]),
  format: z.string().optional().nullable(),
  campaign_id: z.string().uuid().optional().nullable(),
});

export const eventSchema = z.object({
  name: z.string().min(1).max(255),
  event_type: z.enum(['webinar', 'open_house', 'conference', 'networking', 'launch', 'workshop', 'other']),
  campaign_id: z.string().uuid().optional().nullable(),
  start_at: z.string().datetime().optional().nullable(),
  end_at: z.string().datetime().optional().nullable(),
});

export const budgetSchema = z.object({
  name: z.string().min(1).max(255),
  campaign_id: z.string().uuid().optional().nullable(),
  currency: z.string().max(3).default('USD'),
  planned_amount: z.string().optional().nullable(),
});

export const approvalSchema = z.object({
  entity_type: z.string(),
  entity_id: z.string().uuid(),
  approval_type: z.enum(['campaign', 'content', 'budget', 'creative', 'event']),
  notes: z.string().optional().nullable(),
});

export const alertSchema = z.object({
  title: z.string().min(1).max(255),
  message: z.string().optional().nullable(),
  category: z.enum(['campaign', 'budget', 'provider', 'compliance', 'performance', 'system']),
  severity: z.enum(['info', 'warning', 'error', 'critical']).default('info'),
});

export const recommendationSchema = z.object({
  title: z.string().min(1).max(255),
  description: z.string().optional().nullable(),
  recommendation_type: z.string(),
  rationale: z.string().optional().nullable(),
  confidence_level: z.string().optional().nullable(),
});

export type CampaignFormValues = z.infer<typeof campaignSchema>;
export type UtmParamsFormValues = z.infer<typeof utmParamsSchema>;
