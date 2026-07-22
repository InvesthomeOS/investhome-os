import {
  createLeadSource,
  fetchLeadSource,
  fetchLeadSourceHierarchy,
  fetchLeadSourceSummary,
  fetchLeadSources,
  normalizeLeadSourceValue,
} from '@/workspaces/marketing/api/lead-sources';

export const leadSourcesQueryKeys = {
  all: ['marketing', 'leadSources'] as const,
  list: (page = 1) => ['marketing', 'leadSources', 'list', page] as const,
  summary: () => ['marketing', 'leadSources', 'summary'] as const,
  detail: (id: string) => ['marketing', 'leadSources', 'detail', id] as const,
  hierarchy: () => ['marketing', 'leadSources', 'hierarchy'] as const,
};

export const leadSourcesQueries = {
  list: (page = 1) => ({
    queryKey: leadSourcesQueryKeys.list(page),
    queryFn: () => fetchLeadSources(page),
  }),
  summary: () => ({
    queryKey: leadSourcesQueryKeys.summary(),
    queryFn: () => fetchLeadSourceSummary(),
  }),
  detail: (id: string) => ({
    queryKey: leadSourcesQueryKeys.detail(id),
    queryFn: () => fetchLeadSource(id),
  }),
  hierarchy: () => ({
    queryKey: leadSourcesQueryKeys.hierarchy(),
    queryFn: () => fetchLeadSourceHierarchy(),
  }),
};

export { createLeadSource, normalizeLeadSourceValue };
