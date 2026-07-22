import {
  createContent,
  fetchContent,
  fetchContentBrief,
  fetchContentCalendar,
  fetchContentDashboard,
  fetchContentReadiness,
  fetchContents,
  fetchContentVersions,
  transitionContent,
  updateContent,
  type ContentListParams,
} from '@/workspaces/marketing/api/content';

export const contentQueryKeys = {
  all: ['marketing', 'content'] as const,
  dashboard: () => ['marketing', 'content', 'dashboard'] as const,
  calendar: () => ['marketing', 'content', 'calendar'] as const,
  list: (params: ContentListParams) => ['marketing', 'content', 'list', params] as const,
  detail: (id: string) => ['marketing', 'content', 'detail', id] as const,
  readiness: (id: string) => ['marketing', 'content', 'readiness', id] as const,
  brief: (id: string) => ['marketing', 'content', 'brief', id] as const,
  versions: (id: string) => ['marketing', 'content', 'versions', id] as const,
};

export const contentQueries = {
  dashboard: () => ({ queryKey: contentQueryKeys.dashboard(), queryFn: () => fetchContentDashboard() }),
  calendar: () => ({ queryKey: contentQueryKeys.calendar(), queryFn: () => fetchContentCalendar() }),
  list: (params: ContentListParams = {}) => ({
    queryKey: contentQueryKeys.list(params),
    queryFn: () => fetchContents(params),
  }),
  detail: (id: string) => ({
    queryKey: contentQueryKeys.detail(id),
    queryFn: () => fetchContent(id),
    enabled: Boolean(id),
  }),
  readiness: (id: string) => ({
    queryKey: contentQueryKeys.readiness(id),
    queryFn: () => fetchContentReadiness(id),
    enabled: Boolean(id),
  }),
  brief: (id: string) => ({
    queryKey: contentQueryKeys.brief(id),
    queryFn: () => fetchContentBrief(id),
    enabled: Boolean(id),
  }),
  versions: (id: string) => ({
    queryKey: contentQueryKeys.versions(id),
    queryFn: () => fetchContentVersions(id),
    enabled: Boolean(id),
  }),
};

export const contentMutations = { createContent, updateContent, transitionContent };
