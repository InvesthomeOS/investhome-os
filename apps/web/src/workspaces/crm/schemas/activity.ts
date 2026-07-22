import { z } from 'zod';

export const activityInputSchema = z.object({
  entity_type: z.enum([
    'contact',
    'company',
    'opportunity',
    'investor',
    'property',
    'project',
    'transaction',
    'investment',
    'vendor',
    'internal_user',
    'relationship',
  ]),
  entity_id: z.string().uuid(),
  activity_type: z.enum([
    'note',
    'phone_call',
    'email',
    'whatsapp',
    'sms',
    'meeting',
    'zoom_meeting',
    'teams_meeting',
    'site_visit',
    'property_tour',
    'investor_meeting',
    'construction_meeting',
    'inspection',
    'document_sent',
    'document_received',
    'proposal_sent',
    'proposal_received',
    'reservation',
    'contract_signed',
    'closing',
    'payment',
    'task',
    'reminder',
    'follow_up',
    'internal_discussion',
    'comment',
    'system_event',
    'automation_event',
    'other',
  ]),
  title: z.string().min(1).max(500),
  summary: z.string().max(1000).optional(),
  description: z.string().optional(),
  status: z
    .enum(['planned', 'scheduled', 'in_progress', 'completed', 'cancelled', 'missed', 'deferred'])
    .optional(),
  task_status: z
    .enum(['not_started', 'in_progress', 'waiting', 'completed', 'cancelled', 'deferred'])
    .optional(),
  priority: z.enum(['low', 'medium', 'high', 'critical']).optional(),
  due_date: z.string().datetime().optional(),
  start_date: z.string().datetime().optional(),
  end_date: z.string().datetime().optional(),
  reminder_date: z.string().datetime().optional(),
  timezone: z.string().max(64).optional(),
  location: z.string().max(500).optional(),
  meeting_url: z.string().url().max(1000).optional().or(z.literal('')),
  visibility: z.enum(['private', 'team', 'organization', 'restricted']).optional(),
  tags: z.array(z.string()).optional(),
  assigned_user_id: z.string().uuid().optional(),
});

export const followUpInputSchema = z.object({
  entity_type: activityInputSchema.shape.entity_type,
  entity_id: z.string().uuid(),
  reason: z.enum([
    'investor',
    'broker',
    'lender',
    'property',
    'opportunity',
    'relationship_review',
    'contract',
    'payment',
    'inspection',
    'custom',
  ]),
  title: z.string().max(500).optional(),
  due_date: z.string().datetime(),
  notes: z.string().optional(),
});

export const activityFilterSchema = z.object({
  search: z.string().optional(),
  entity_type: activityInputSchema.shape.entity_type.optional(),
  entity_id: z.string().uuid().optional(),
  activity_type: activityInputSchema.shape.activity_type.optional(),
  status: activityInputSchema.shape.status.optional(),
  priority: activityInputSchema.shape.priority.optional(),
  pending: z.boolean().optional(),
  completed: z.boolean().optional(),
  date_from: z.string().optional(),
  date_to: z.string().optional(),
});

export type ActivityInputForm = z.infer<typeof activityInputSchema>;
export type FollowUpInputForm = z.infer<typeof followUpInputSchema>;
export type ActivityFilterForm = z.infer<typeof activityFilterSchema>;
