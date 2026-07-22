export type CrmSearchEntityType =
  | 'crm_contact'
  | 'crm_company'
  | 'crm_relationship'
  | 'crm_activity'
  | 'crm_communication'
  | 'crm_task'
  | 'sales_opportunity'
  | 'investor'
  | 'project'
  | 'inventory_asset'
  | 'financial_transaction'
  | 'document'
  | 'file'
  | 'action';

export type CrmSearchViewMode = 'list' | 'compact' | 'table' | 'card';

export type CrmSearchSortField = 'relevance' | 'recency' | 'title' | 'updated_at' | 'created_at';

export interface CrmSearchHighlightField {
  field: string;
  snippet: string;
  highlighted_html?: string | null;
}

export interface CrmSearchResultItem {
  id: string;
  entity_type: string;
  entity_id: string;
  title: string;
  subtitle?: string | null;
  description?: string | null;
  preview?: string | null;
  highlighted_fields: CrmSearchHighlightField[];
  matched_fields: string[];
  score: number;
  relevance_score: number;
  recency_score: number;
  relationship_score: number;
  entity_status?: string | null;
  owner_id?: string | null;
  owner_name?: string | null;
  tags: string[];
  url: string;
  icon?: string | null;
  thumbnail?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  last_activity_at?: string | null;
  permission_level: string;
  metadata: Record<string, unknown>;
}

export interface CrmSearchResultGroup {
  entity_type: string;
  label_key: string;
  items: CrmSearchResultItem[];
  total: number;
}

export interface CrmSearchFilterGroup {
  logic: 'and' | 'or';
  conditions: Array<{ field: string; operator: string; value?: unknown }>;
  groups?: CrmSearchFilterGroup[];
}

export interface CrmSearchQueryRequest {
  query?: string;
  entity_types?: string[];
  filters?: CrmSearchFilterGroup | null;
  sort?: CrmSearchSortField;
  sort_dir?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
  cursor?: string | null;
  include_archived?: boolean;
  include_restricted?: boolean;
  exact_match?: boolean;
  fuzzy_match?: boolean;
  semantic_search?: boolean;
  date_range?: { from_date?: string; to_date?: string; relative?: string } | null;
  owner_ids?: string[];
  team_ids?: string[];
  tags?: string[];
  statuses?: string[];
  locations?: string[];
  related_entity_ids?: string[];
  saved_search_id?: string | null;
  grouping?: string | null;
}

export interface CrmSearchResponse {
  query: string;
  parsed_query?: Record<string, unknown> | null;
  groups: CrmSearchResultGroup[];
  items: CrmSearchResultItem[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
  next_cursor?: string | null;
  took_ms: number;
  suggestions?: string[];
  did_you_mean?: string | null;
  explanation?: string | null;
  active_filters?: string[];
}

export interface CrmRecentSearch {
  id: string;
  query: string;
  filters?: Record<string, unknown> | null;
  entity_types?: string[] | null;
  result_count: number;
  opened_result_id?: string | null;
  opened_entity_type?: string | null;
  searched_at: string;
}

export interface CrmSavedSearch {
  id: string;
  owner_id: string;
  name: string;
  description?: string | null;
  query?: string | null;
  filters?: Record<string, unknown> | null;
  entity_types?: string[] | null;
  sort?: Record<string, unknown> | null;
  grouping?: string | null;
  visible_fields?: string[] | null;
  view_mode: string;
  visibility: string;
  shared_with?: string[] | null;
  notification_settings?: Record<string, unknown> | null;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface CrmSearchSuggestion {
  text: string;
  type: string;
  entity_type?: string | null;
}

export const CRM_SEARCH_ENTITY_TYPES: CrmSearchEntityType[] = [
  'crm_contact',
  'crm_company',
  'crm_relationship',
  'crm_activity',
  'crm_communication',
  'crm_task',
  'sales_opportunity',
  'investor',
  'project',
  'inventory_asset',
  'financial_transaction',
  'document',
];

export const CRM_SEARCH_DEBOUNCE_MS = 300;
export const CRM_SEARCH_MIN_QUERY_LENGTH = 2;
