import { z } from 'zod';

export const crmSearchQuerySchema = z.object({
  query: z.string().max(500).optional(),
  entity_types: z.array(z.string()).optional(),
  sort: z.enum(['relevance', 'recency', 'title', 'updated_at', 'created_at']).optional(),
  sort_dir: z.enum(['asc', 'desc']).optional(),
  page: z.number().int().min(1).optional(),
  page_size: z.number().int().min(1).max(100).optional(),
  include_archived: z.boolean().optional(),
  include_restricted: z.boolean().optional(),
  exact_match: z.boolean().optional(),
  fuzzy_match: z.boolean().optional(),
  semantic_search: z.boolean().optional(),
  tags: z.array(z.string()).optional(),
  statuses: z.array(z.string()).optional(),
  saved_search_id: z.string().uuid().nullable().optional(),
  grouping: z.string().nullable().optional(),
});

export const crmSearchFilterConditionSchema = z.object({
  field: z.string().min(1),
  operator: z.string().min(1),
  value: z.union([z.string(), z.number(), z.boolean(), z.array(z.string()), z.null()]).optional(),
});

export const crmSearchFilterGroupSchema: z.ZodType<{
  logic: 'and' | 'or';
  conditions: z.infer<typeof crmSearchFilterConditionSchema>[];
  groups?: unknown[];
}> = z.lazy(() =>
  z.object({
    logic: z.enum(['and', 'or']),
    conditions: z.array(crmSearchFilterConditionSchema),
    groups: z.array(crmSearchFilterGroupSchema).optional(),
  }),
);

export const crmSavedSearchSchema = z.object({
  name: z.string().min(1).max(255),
  description: z.string().max(2000).optional(),
  query: z.string().max(500).optional(),
  entity_types: z.array(z.string()).optional(),
  view_mode: z.enum(['list', 'compact', 'table', 'card']).optional(),
  visibility: z.enum(['private', 'shared', 'team']).optional(),
});

export const crmEntityPickerSchema = z.object({
  query: z.string().optional(),
  entity_types: z.array(z.string()).optional(),
  page: z.number().int().min(1).optional(),
  page_size: z.number().int().min(1).max(50).optional(),
  exclude_ids: z.array(z.string().uuid()).optional(),
});

export type CrmSearchQueryInput = z.infer<typeof crmSearchQuerySchema>;
export type CrmSavedSearchInput = z.infer<typeof crmSavedSearchSchema>;
export type CrmEntityPickerInput = z.infer<typeof crmEntityPickerSchema>;
