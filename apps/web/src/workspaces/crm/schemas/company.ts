import { z } from 'zod';

import { CRM_COMPANY_TYPES, CRM_LIFECYCLE_STAGES } from '@/workspaces/crm/types';

export const crmCompanyFormSchema = z.object({
  display_name: z.string().trim().min(1).max(255),
  legal_name: z.string().trim().max(255).optional().or(z.literal('')),
  trade_name: z.string().trim().max(255).optional().or(z.literal('')),
  company_type: z.enum(CRM_COMPANY_TYPES as [string, ...string[]]),
  company_types: z.array(z.enum(CRM_COMPANY_TYPES as [string, ...string[]])).optional(),
  entity_type: z
    .enum(['corporation', 'llc', 'partnership', 'trust', 'sole_proprietorship', 'non_profit', 'government', 'other'])
    .optional()
    .or(z.literal('')),
  status: z.enum(['active', 'inactive', 'prospect', 'archived']),
  lifecycle_stage: z.enum(CRM_LIFECYCLE_STAGES as [string, ...string[]]),
  registration_number: z.string().trim().max(80).optional().or(z.literal('')),
  tax_id: z.string().trim().max(80).optional().or(z.literal('')),
  ein: z.string().trim().max(80).optional().or(z.literal('')),
  primary_email: z.string().trim().email().max(255).optional().or(z.literal('')),
  primary_phone: z.string().trim().max(50).optional().or(z.literal('')),
  website: z.string().trim().max(500).optional().or(z.literal('')),
  domain: z.string().trim().max(255).optional().or(z.literal('')),
  linkedin_url: z.string().trim().max(500).optional().or(z.literal('')),
  industry: z.string().trim().max(120).optional().or(z.literal('')),
  employee_count: z.coerce.number().int().min(0).optional(),
  description: z.string().trim().max(5000).optional().or(z.literal('')),
  source: z.string().trim().max(120).optional().or(z.literal('')),
  notes: z.string().trim().max(5000).optional().or(z.literal('')),
  tags: z.array(z.string().trim().min(1)).optional(),
  investment_profile: z
    .object({
      aum: z.coerce.number().optional(),
      investment_focus: z.array(z.string()).optional(),
      ticket_size_min: z.coerce.number().optional(),
      ticket_size_max: z.coerce.number().optional(),
      notes: z.string().optional(),
    })
    .optional(),
  brokerage_profile: z
    .object({
      license_number: z.string().optional(),
      specialization: z.string().optional(),
      agent_count: z.coerce.number().optional(),
    })
    .optional(),
  lender_profile: z
    .object({
      lender_type: z.string().optional(),
      nmls_id: z.string().optional(),
      loan_types: z.array(z.string()).optional(),
    })
    .optional(),
  vendor_profile: z
    .object({
      vendor_category: z.string().optional(),
      payment_terms: z.string().optional(),
    })
    .optional(),
  law_firm_profile: z
    .object({
      bar_number: z.string().optional(),
      practice_areas: z.array(z.string()).optional(),
    })
    .optional(),
  property_management_profile: z
    .object({
      units_managed: z.coerce.number().optional(),
      service_areas: z.array(z.string()).optional(),
    })
    .optional(),
});

export type CrmCompanyFormValues = z.infer<typeof crmCompanyFormSchema>;

export const crmCompanyFormDefaults: CrmCompanyFormValues = {
  display_name: '',
  legal_name: '',
  trade_name: '',
  company_type: 'other',
  company_types: ['other'],
  entity_type: '',
  status: 'active',
  lifecycle_stage: 'new',
  registration_number: '',
  tax_id: '',
  ein: '',
  primary_email: '',
  primary_phone: '',
  website: '',
  domain: '',
  linkedin_url: '',
  industry: '',
  employee_count: undefined,
  description: '',
  source: '',
  notes: '',
  tags: [],
};
