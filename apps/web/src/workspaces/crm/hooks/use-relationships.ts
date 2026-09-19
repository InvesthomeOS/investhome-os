import {
  archiveRelationship,
  calculateRelationshipScores,
  checkRelationshipDuplicates,
  createRelationship,
  createSavedView,
  deleteRelationship,
  expandGraphNode,
  exportRelationshipsCsv,
  fetchDecisionMap,
  fetchIntroductionPaths,
  fetchIntelligenceDashboard,
  fetchRelationship,
  fetchRelationshipGraph,
  fetchRelationshipRecommendations,
  fetchRelationships,
  fetchSavedViews,
  restoreRelationship,
  updateRelationship,
  upsertDecisionMapRole,
  type RelationshipInput,
  type RelationshipListParams,
} from '@/workspaces/crm/api/relationships';

export const relationshipQueryKeys = {
  all: ['crm', 'relationships'] as const,
  list: (params: RelationshipListParams) => ['crm', 'relationships', 'list', params] as const,
  detail: (id: string) => ['crm', 'relationships', 'detail', id] as const,
  graph: (params: Record<string, unknown>) => ['crm', 'relationships', 'graph', params] as const,
  intelligence: ['crm', 'relationships', 'intelligence'] as const,
  recommendations: ['crm', 'relationships', 'recommendations'] as const,
  introductionPaths: (params: Record<string, unknown>) =>
    ['crm', 'relationships', 'introduction-paths', params] as const,
  savedViews: ['crm', 'relationships', 'saved-views'] as const,
  decisionMap: (companyId: string) => ['crm', 'relationships', 'decision-map', companyId] as const,
};

export const relationshipQueries = {
  list: (params: RelationshipListParams) => ({
    queryKey: relationshipQueryKeys.list(params),
    queryFn: () => fetchRelationships(params),
  }),
  detail: (id: string) => ({
    queryKey: relationshipQueryKeys.detail(id),
    queryFn: () => fetchRelationship(id),
    enabled: Boolean(id),
  }),
  graph: (params: Record<string, unknown>) => ({
    queryKey: relationshipQueryKeys.graph(params),
    queryFn: () => fetchRelationshipGraph(params),
  }),
  intelligence: () => ({
    queryKey: relationshipQueryKeys.intelligence,
    queryFn: () => fetchIntelligenceDashboard(),
  }),
  recommendations: () => ({
    queryKey: relationshipQueryKeys.recommendations,
    queryFn: () => fetchRelationshipRecommendations(),
  }),
  introductionPaths: (params: Record<string, unknown>) => ({
    queryKey: relationshipQueryKeys.introductionPaths(params),
    queryFn: () => fetchIntroductionPaths(params as Parameters<typeof fetchIntroductionPaths>[0]),
    enabled: Boolean(params.source_entity_id && params.target_entity_id),
  }),
  savedViews: () => ({
    queryKey: relationshipQueryKeys.savedViews,
    queryFn: () => fetchSavedViews(),
  }),
  decisionMap: (companyId: string) => ({
    queryKey: relationshipQueryKeys.decisionMap(companyId),
    queryFn: () => fetchDecisionMap(companyId),
    enabled: Boolean(companyId),
  }),
};

export const relationshipMutations = {
  create: createRelationship,
  update: updateRelationship,
  archive: archiveRelationship,
  restore: restoreRelationship,
  delete: deleteRelationship,
  checkDuplicates: checkRelationshipDuplicates,
  expandNode: expandGraphNode,
  calculateScores: calculateRelationshipScores,
  exportCsv: exportRelationshipsCsv,
  createSavedView,
  upsertDecisionMapRole,
};

export type { RelationshipInput, RelationshipListParams };
