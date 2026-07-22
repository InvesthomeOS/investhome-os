import {
  createAudience,
  fetchAudience,
  fetchAudienceMembers,
  fetchAudienceReadiness,
  fetchAudienceSummary,
  fetchAudiences,
  refreshAudience,
  type AudienceListParams,
} from '@/workspaces/marketing/api/audiences';

export const audienceQueryKeys = {
  all: ['marketing', 'audiences'] as const,
  list: (params: AudienceListParams) => ['marketing', 'audiences', 'list', params] as const,
  summary: () => ['marketing', 'audiences', 'summary'] as const,
  detail: (id: string) => ['marketing', 'audiences', 'detail', id] as const,
  members: (id: string, page = 1) => ['marketing', 'audiences', 'members', id, page] as const,
  readiness: (id: string) => ['marketing', 'audiences', 'readiness', id] as const,
  savedViews: () => ['marketing', 'audiences', 'savedViews'] as const,
};

export const audienceQueries = {
  list: (params: AudienceListParams = {}) => ({
    queryKey: audienceQueryKeys.list(params),
    queryFn: () => fetchAudiences(params),
  }),
  summary: () => ({
    queryKey: audienceQueryKeys.summary(),
    queryFn: () => fetchAudienceSummary(),
  }),
  detail: (id: string) => ({
    queryKey: audienceQueryKeys.detail(id),
    queryFn: () => fetchAudience(id),
  }),
  members: (id: string, page = 1) => ({
    queryKey: audienceQueryKeys.members(id, page),
    queryFn: () => fetchAudienceMembers(id, page),
  }),
  readiness: (id: string) => ({
    queryKey: audienceQueryKeys.readiness(id),
    queryFn: () => fetchAudienceReadiness(id),
  }),
};

export { createAudience, refreshAudience };
