import { z } from 'zod';

import { CRM_COMM_CHANNELS } from '@/workspaces/crm/types';

export const communicationComposeSchema = z.object({
  channel: z.enum(CRM_COMM_CHANNELS as [string, ...string[]]),
  subject: z.string().max(500).optional().or(z.literal('')),
  body: z.string().min(1, 'Body is required'),
  body_html: z.string().optional(),
  recipient_entity_type: z.enum(['contact', 'company', 'opportunity', 'investor', 'property', 'project', 'transaction', 'internal_user', 'relationship']).optional(),
  recipient_entity_id: z.string().uuid().optional().or(z.literal('')),
  scheduled_at: z.string().optional(),
  visibility: z.enum(['private', 'team', 'organization', 'restricted']).default('organization'),
  priority: z.enum(['low', 'medium', 'high', 'critical']).default('medium'),
});

export type CommunicationComposeValues = z.infer<typeof communicationComposeSchema>;

export const communicationComposeDefaults: CommunicationComposeValues = {
  channel: 'email',
  subject: '',
  body: '',
  visibility: 'organization',
  priority: 'medium',
};

export const callLogSchema = z.object({
  subject: z.string().min(1).max(500),
  recipient_entity_type: z.enum(['contact', 'company']).default('contact'),
  recipient_entity_id: z.string().uuid(),
  call_duration_seconds: z.number().int().min(0).optional(),
  call_outcome: z.enum(['connected', 'no_answer', 'voicemail', 'busy', 'wrong_number', 'callback_requested']).optional(),
  call_direction: z.enum(['inbound', 'outbound']).default('outbound'),
  body: z.string().optional(),
});

export type CallLogFormValues = z.infer<typeof callLogSchema>;

export const templateFormSchema = z.object({
  name: z.string().min(1).max(255),
  template_type: z.enum(['email', 'whatsapp', 'sms', 'call_script', 'meeting_agenda', 'internal', 'follow_up']),
  subject: z.string().max(500).optional().or(z.literal('')),
  body: z.string().min(1),
  variables: z.array(z.string()).optional(),
  is_shared: z.boolean().default(false),
});

export type TemplateFormValues = z.infer<typeof templateFormSchema>;
