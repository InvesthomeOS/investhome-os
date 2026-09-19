import { apiFetch } from '@/lib/api/client';

import type {
  CrmEntityPickerInput,
  CrmSavedSearchInput,
  CrmSearchQueryInput,
} from '@/workspaces/crm/schemas/search';
import type {
  CrmRecentSearch,
  CrmSavedSearch,
  CrmSearchQueryRequest,
  CrmSearchResponse,
  CrmSearchResultItem,
  CrmSearchSuggestion,
} from '@/workspaces/crm/types/search';

export async function fetchCrmGlobalSearch(payload: CrmSearchQueryRequest): Promise<CrmSearchResponse> {
  return apiFetch<CrmSearchResponse>('/crm/search/global', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function fetchCrmQuickSearch(query: string, limit = 25): Promise<CrmSearchResponse> {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  return apiFetch<CrmSearchResponse>(`/crm/search/quick?${params.toString()}`);
}

export async function fetchCrmSearchSuggestions(query: string): Promise<{ query: string; suggestions: CrmSearchSuggestion[] }> {
  const params = new URLSearchParams({ q: query });
  return apiFetch(`/crm/search/suggestions?${params.toString()}`);
}

export async function parseCrmSearchQuery(query: string): Promise<{ query: string; parsed: Record<string, unknown>; errors: string[]; warnings: string[] }> {
  return apiFetch('/crm/search/parse', { method: 'POST', body: JSON.stringify({ query }) });
}

export async function fetchCrmRecentSearches(): Promise<CrmRecentSearch[]> {
  return apiFetch('/crm/search/recent');
}

export async function recordCrmRecentSearch(payload: {
  query: string;
  result_count?: number;
  entity_types?: string[];
  filters?: Record<string, unknown>;
}): Promise<CrmRecentSearch> {
  return apiFetch('/crm/search/recent', { method: 'POST', body: JSON.stringify(payload) });
}

export async function clearCrmRecentSearches(): Promise<void> {
  await apiFetch('/crm/search/recent', { method: 'DELETE' });
}

export async function removeCrmRecentSearch(id: string): Promise<void> {
  await apiFetch(`/crm/search/recent/${id}`, { method: 'DELETE' });
}

export async function fetchCrmSavedSearches(): Promise<CrmSavedSearch[]> {
  return apiFetch('/crm/search/saved');
}

export async function createCrmSavedSearch(payload: CrmSavedSearchInput): Promise<CrmSavedSearch> {
  return apiFetch('/crm/search/saved', { method: 'POST', body: JSON.stringify(payload) });
}

export async function updateCrmSavedSearch(id: string, payload: Partial<CrmSavedSearchInput>): Promise<CrmSavedSearch> {
  return apiFetch(`/crm/search/saved/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
}

export async function deleteCrmSavedSearch(id: string): Promise<void> {
  await apiFetch(`/crm/search/saved/${id}`, { method: 'DELETE' });
}

export async function executeCrmSavedSearch(id: string): Promise<CrmSearchResponse> {
  return apiFetch(`/crm/search/saved/${id}/execute`, { method: 'POST' });
}

export async function fetchEntityPickerResults(payload: CrmEntityPickerInput): Promise<{
  items: CrmSearchResultItem[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}> {
  return apiFetch('/crm/search/entity-picker', { method: 'POST', body: JSON.stringify(payload) });
}

export async function exportCrmSearchResults(payload: {
  format?: string;
  query?: string;
  result_ids?: string[];
  visible_fields?: string[];
}): Promise<{ format: string; content?: string; row_count: number }> {
  return apiFetch('/crm/search/export', { method: 'POST', body: JSON.stringify(payload) });
}

export async function interpretNaturalLanguageSearch(query: string): Promise<{
  query: string;
  available: boolean;
  message?: string;
  interpreted_filters?: Record<string, unknown>;
}> {
  return apiFetch('/crm/search/natural-language', { method: 'POST', body: JSON.stringify({ query }) });
}

export function buildSearchRequest(input: CrmSearchQueryInput): CrmSearchQueryRequest {
  return {
    query: input.query ?? '',
    entity_types: input.entity_types,
    sort: input.sort,
    sort_dir: input.sort_dir,
    page: input.page,
    page_size: input.page_size,
    include_archived: input.include_archived,
    include_restricted: input.include_restricted,
    exact_match: input.exact_match,
    fuzzy_match: input.fuzzy_match,
    semantic_search: input.semantic_search,
    tags: input.tags,
    statuses: input.statuses,
    saved_search_id: input.saved_search_id,
    grouping: input.grouping,
  };
}
