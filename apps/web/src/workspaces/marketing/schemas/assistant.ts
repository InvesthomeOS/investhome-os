import { z } from 'zod';

export const assistantModeSchema = z.enum([
  'marketing_summary',
  'campaign_analysis',
  'content_draft',
  'campaign_brief',
  'audience_suggestion',
  'channel_suggestion',
  'translation',
  'next_actions',
]);

export type AssistantMode = z.infer<typeof assistantModeSchema>;

export const assistantGenerateRequestSchema = z.object({
  mode: assistantModeSchema,
  organization_id: z.string().uuid().nullable().optional(),
  project_id: z.string().uuid().nullable().optional(),
  campaign_id: z.string().uuid().nullable().optional(),
  asset_ids: z.array(z.string().uuid()).optional(),
  audience_id: z.string().uuid().nullable().optional(),
  language: z.enum(['tr', 'en']).default('en'),
  target_language: z.enum(['tr', 'en']).nullable().optional(),
  tone: z.string().nullable().optional(),
  channel: z.string().nullable().optional(),
  content_type: z.string().nullable().optional(),
  length: z.string().nullable().optional(),
  call_to_action: z.string().nullable().optional(),
  source_text: z.string().nullable().optional(),
  adaptation_style: z.string().nullable().optional(),
  user_instruction: z.string().nullable().optional(),
  client_request_id: z.string().nullable().optional(),
  regenerate_of_id: z.string().uuid().nullable().optional(),
});

export type AssistantGenerateRequest = z.infer<typeof assistantGenerateRequestSchema>;

export const assistantOutputSchema = z.object({
  id: z.string(),
  output_type: z.string(),
  status: z.string(),
  title: z.string().nullable().optional(),
  language: z.string().nullable().optional(),
  generated_content: z.string(),
  structured_output: z.record(z.string(), z.unknown()).nullable().optional(),
  data_sources: z.array(z.record(z.string(), z.unknown())).default([]),
  data_warnings: z.array(z.string()).default([]),
  assumptions: z.array(z.string()).default([]),
  safety_flags: z.array(z.string()).default([]),
  safety_blocked: z.boolean().optional(),
  safety_message: z.string().nullable().optional(),
  model_provider: z.string().nullable().optional(),
  model_name: z.string().nullable().optional(),
  prompt_key: z.string().nullable().optional(),
  prompt_version: z.string().nullable().optional(),
  token_usage: z.record(z.string(), z.unknown()).nullable().optional(),
  action_links: z
    .array(
      z.object({
        label: z.string(),
        href: z.string(),
        reason: z.string().nullable().optional(),
      }),
    )
    .default([]),
  data_freshness_at: z.string().nullable().optional(),
  organization_id: z.string().nullable().optional(),
  project_id: z.string().nullable().optional(),
  campaign_id: z.string().nullable().optional(),
  asset_id: z.string().nullable().optional(),
  created_at: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
});

export type AssistantOutput = z.infer<typeof assistantOutputSchema>;

export const assistantModesResponseSchema = z.object({
  modes: z.array(
    z.object({
      key: assistantModeSchema,
      prompt_key: z.string(),
      label_key: z.string(),
      requires_campaign: z.boolean(),
      requires_source_text: z.boolean(),
    }),
  ),
  content_draft_types: z.array(z.string()),
  tones: z.array(z.string()),
  languages: z.array(z.string()),
  provider_available: z.boolean(),
  provider_name: z.string().nullable().optional(),
});

export type AssistantModesResponse = z.infer<typeof assistantModesResponseSchema>;

export function createClientRequestId(prefix = 'mkt-ai'): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export function modeRequiresCampaign(mode: AssistantMode): boolean {
  return mode === 'campaign_analysis';
}

export function modeRequiresSourceText(mode: AssistantMode): boolean {
  return mode === 'translation';
}
