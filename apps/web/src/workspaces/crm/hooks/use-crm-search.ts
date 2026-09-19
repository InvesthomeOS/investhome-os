import { queryOptions, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  buildSearchRequest,
  clearCrmRecentSearches,
  createCrmSavedSearch,
  deleteCrmSavedSearch,
  executeCrmSavedSearch,
  exportCrmSearchResults,
  fetchCrmGlobalSearch,
  fetchCrmQuickSearch,
  fetchCrmRecentSearches,
  fetchCrmSavedSearches,
  fetchCrmSearchSuggestions,
  fetchEntityPickerResults,
  parseCrmSearchQuery,
  recordCrmRecentSearch,
  removeCrmRecentSearch,
  updateCrmSavedSearch,
} from '@/workspaces/crm/api/search';
import type { CrmSearchQueryInput, CrmSavedSearchInput } from '@/workspaces/crm/schemas/search';
import type { CrmSearchQueryRequest } from '@/workspaces/crm/types/search';

export const crmSearchQueryKeys = {
  all: ['crm-search'] as const,
  global: (params: CrmSearchQueryRequest) => [...crmSearchQueryKeys.all, 'global', params] as const,
  quick: (query: string) => [...crmSearchQueryKeys.all, 'quick', query] as const,
  suggestions: (query: string) => [...crmSearchQueryKeys.all, 'suggestions', query] as const,
  recent: () => [...crmSearchQueryKeys.all, 'recent'] as const,
  saved: () => [...crmSearchQueryKeys.all, 'saved'] as const,
  entityPicker: (params: Record<string, unknown>) => [...crmSearchQueryKeys.all, 'entity-picker', params] as const,
  parse: (query: string) => [...crmSearchQueryKeys.all, 'parse', query] as const,
};

export const crmSearchQueries = {
  global: (params: CrmSearchQueryRequest) =>
    queryOptions({
      queryKey: crmSearchQueryKeys.global(params),
      queryFn: () => fetchCrmGlobalSearch(params),
      enabled: Boolean(params.query?.trim()),
    }),
  quick: (query: string, enabled = true) =>
    queryOptions({
      queryKey: crmSearchQueryKeys.quick(query),
      queryFn: () => fetchCrmQuickSearch(query),
      enabled: enabled && query.trim().length >= 2,
      staleTime: 30_000,
    }),
  suggestions: (query: string) =>
    queryOptions({
      queryKey: crmSearchQueryKeys.suggestions(query),
      queryFn: () => fetchCrmSearchSuggestions(query),
      enabled: query.trim().length >= 2,
    }),
  recent: () =>
    queryOptions({
      queryKey: crmSearchQueryKeys.recent(),
      queryFn: fetchCrmRecentSearches,
    }),
  saved: () =>
    queryOptions({
      queryKey: crmSearchQueryKeys.saved(),
      queryFn: fetchCrmSavedSearches,
    }),
  entityPicker: (params: Record<string, unknown>) =>
    queryOptions({
      queryKey: crmSearchQueryKeys.entityPicker(params),
      queryFn: () => fetchEntityPickerResults(params),
    }),
  parse: (query: string) =>
    queryOptions({
      queryKey: crmSearchQueryKeys.parse(query),
      queryFn: () => parseCrmSearchQuery(query),
      enabled: query.includes(':'),
    }),
};

export function useCrmGlobalSearch(params: CrmSearchQueryInput, enabled = true) {
  const request = buildSearchRequest(params);
  return useQuery({
    ...crmSearchQueries.global(request),
    enabled: enabled && Boolean(request.query?.trim()),
  });
}

export function useCrmQuickSearch(query: string, enabled = true) {
  return useQuery(crmSearchQueries.quick(query, enabled));
}

export function useCrmRecentSearches() {
  return useQuery(crmSearchQueries.recent());
}

export function useCrmSavedSearches() {
  return useQuery(crmSearchQueries.saved());
}

export function useRecordRecentSearch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: recordCrmRecentSearch,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: crmSearchQueryKeys.recent() });
    },
  });
}

export function useClearRecentSearches() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: clearCrmRecentSearches,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: crmSearchQueryKeys.recent() });
    },
  });
}

export function useRemoveRecentSearch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: removeCrmRecentSearch,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: crmSearchQueryKeys.recent() });
    },
  });
}

export function useCreateSavedSearch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CrmSavedSearchInput) => createCrmSavedSearch(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: crmSearchQueryKeys.saved() });
    },
  });
}

export function useUpdateSavedSearch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<CrmSavedSearchInput> }) =>
      updateCrmSavedSearch(id, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: crmSearchQueryKeys.saved() });
    },
  });
}

export function useDeleteSavedSearch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteCrmSavedSearch,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: crmSearchQueryKeys.saved() });
    },
  });
}

export function useExecuteSavedSearch() {
  return useMutation({ mutationFn: executeCrmSavedSearch });
}

export function useExportSearchResults() {
  return useMutation({ mutationFn: exportCrmSearchResults });
}

export function useEntityPicker(params: Record<string, unknown>, enabled = true) {
  return useQuery({ ...crmSearchQueries.entityPicker(params), enabled });
}
