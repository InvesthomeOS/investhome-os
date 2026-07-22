import {
  calculateSegment,
  createSegment,
  fetchSegment,
  fetchSegmentFieldRegistry,
  fetchSegmentRules,
  fetchSegmentSummary,
  fetchSegments,
  previewSegment,
} from '@/workspaces/marketing/api/segments';

export const segmentQueryKeys = {
  all: ['marketing', 'segments'] as const,
  list: (page = 1) => ['marketing', 'segments', 'list', page] as const,
  summary: () => ['marketing', 'segments', 'summary'] as const,
  detail: (id: string) => ['marketing', 'segments', 'detail', id] as const,
  rules: (id: string) => ['marketing', 'segments', 'rules', id] as const,
  preview: (id: string) => ['marketing', 'segments', 'preview', id] as const,
  fieldRegistry: () => ['marketing', 'segments', 'fieldRegistry'] as const,
  savedViews: () => ['marketing', 'segments', 'savedViews'] as const,
};

export const segmentQueries = {
  list: (page = 1) => ({
    queryKey: segmentQueryKeys.list(page),
    queryFn: () => fetchSegments(page),
  }),
  summary: () => ({
    queryKey: segmentQueryKeys.summary(),
    queryFn: () => fetchSegmentSummary(),
  }),
  detail: (id: string) => ({
    queryKey: segmentQueryKeys.detail(id),
    queryFn: () => fetchSegment(id),
  }),
  rules: (id: string) => ({
    queryKey: segmentQueryKeys.rules(id),
    queryFn: () => fetchSegmentRules(id),
  }),
  fieldRegistry: () => ({
    queryKey: segmentQueryKeys.fieldRegistry(),
    queryFn: () => fetchSegmentFieldRegistry(),
  }),
};

export { createSegment, previewSegment, calculateSegment };
