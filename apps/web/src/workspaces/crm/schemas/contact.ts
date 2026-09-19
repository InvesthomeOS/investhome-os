import { z } from 'zod';

import {
  CRM_CONTACT_TYPES,
  CRM_LIFECYCLE_STAGES,
  CRM_PRIORITIES,
} from '@/workspaces/crm/types';

export const crmContactFormSchema = z.object({
  contact_type: z.enum(CRM_CONTACT_TYPES as [string, ...string[]]),
  contact_types: z.array(z.enum(CRM_CONTACT_TYPES as [string, ...string[]])).optional(),
  record_kind: z.enum(['person', 'organization']),
  display_name: z.string().trim().min(1).max(255),
  first_name: z.string().trim().max(120).optional().or(z.literal('')),
  last_name: z.string().trim().max(120).optional().or(z.literal('')),
  organization_name: z.string().trim().max(255).optional().or(z.literal('')),
  job_title: z.string().trim().max(120).optional().or(z.literal('')),
  department: z.string().trim().max(120).optional().or(z.literal('')),
  primary_email: z.string().trim().email().max(255).optional().or(z.literal('')),
  primary_phone: z.string().trim().max(50).optional().or(z.literal('')),
  linkedin_url: z.string().trim().max(500).optional().or(z.literal('')),
  whatsapp: z.string().trim().max(50).optional().or(z.literal('')),
  website: z.string().trim().max(500).optional().or(z.literal('')),
  lifecycle_stage: z.enum(CRM_LIFECYCLE_STAGES as [string, ...string[]]).default('new'),
  relationship_status: z
    .enum(['unknown', 'cold', 'warm', 'hot', 'active', 'at_risk', 'lost'])
    .default('unknown'),
  relationship_strength: z.enum(['weak', 'moderate', 'strong', 'strategic']).default('moderate'),
  priority: z.enum(CRM_PRIORITIES as [string, ...string[]]).default('normal'),
  source: z.string().trim().max(120).optional().or(z.literal('')),
  status: z.enum(['active', 'inactive', 'prospect', 'archived']).default('active'),
  tags: z.array(z.string().trim().min(1)).optional(),
  notes: z.string().trim().max(5000).optional().or(z.literal('')),
  is_favorite: z.boolean().default(false),
  is_pinned: z.boolean().default(false),
  lead_id: z.string().uuid().optional().or(z.literal('')),
  investor_id: z.string().uuid().optional().or(z.literal('')),
  company_id: z.string().uuid().optional().or(z.literal('')),
});

export type CrmContactFormValues = z.infer<typeof crmContactFormSchema>;

export const crmContactFormDefaults: CrmContactFormValues = {
  contact_type: 'prospect',
  contact_types: ['prospect'],
  record_kind: 'person',
  display_name: '',
  first_name: '',
  last_name: '',
  organization_name: '',
  job_title: '',
  department: '',
  primary_email: '',
  primary_phone: '',
  linkedin_url: '',
  whatsapp: '',
  website: '',
  lifecycle_stage: 'new',
  relationship_status: 'unknown',
  relationship_strength: 'moderate',
  priority: 'normal',
  source: '',
  status: 'active',
  tags: [],
  notes: '',
  is_favorite: false,
  is_pinned: false,
  lead_id: '',
  investor_id: '',
  company_id: '',
};
