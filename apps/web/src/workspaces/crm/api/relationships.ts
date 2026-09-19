import { apiFetch } from '@/lib/api/client';

export type RelationshipEntityType =
  | 'contact'
  | 'company'
  | 'project'
  | 'property'
  | 'opportunity'
  | 'investment'
  | 'transaction'
  | 'vendor'
  | 'internal_user'
  | 'external_organization'
  | 'other';

export type RelationshipListParams = {
  search?: string;
  status?: string;
  category?: string;
  relationship_type?: string;
  entity_type?: string;
  entity_id?: string;
  include_archived?: boolean;
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
};

export type CrmRelationshipSummary = {
  id: string;
  source_entity_type: RelationshipEntityType;
  source_entity_id: string;
  target_entity_type: RelationshipEntityType;
  target_entity_id: string;
  source_display_name: string | null;
  target_display_name: string | null;
  relationship_type: string;
  reciprocal_type: string | null;
  reciprocal_label: string | null;
  category: string;
  status: string;
  strength: string;
  direction: string;
  relationship_score: number;
  engagement_score: number;
  influence_score: number;
  trust_score: number;
  business_value_score: number;
  risk_score: number;
  is_confidential: boolean;
  is_verified: boolean;
  owner_user_id: string | null;
  last_interaction_at: string | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CrmRelationshipDetail = CrmRelationshipSummary & {
  notes: string | null;
  metadata_json: Record<string, unknown> | null;
  started_at: string | null;
  ended_at: string | null;
};

export type CrmRelationshipListResponse = {
  items: CrmRelationshipSummary[];
  total: number;
  page: number;
  page_size: number;
};

export type CrmGraphNode = {
  id: string;
  entity_type: RelationshipEntityType;
  entity_id: string;
  label: string;
  score: number;
  is_center: boolean;
  expanded: boolean;
};

export type CrmGraphEdge = {
  id: string;
  source: string;
  target: string;
  relationship_id: string;
  relationship_type: string;
  reciprocal_type: string | null;
  strength: string;
  relationship_score: number;
  is_confidential: boolean;
};

export type CrmRelationshipGraphResponse = {
  nodes: CrmGraphNode[];
  edges: CrmGraphEdge[];
  truncated: boolean;
  warning: string | null;
  depth: number;
  limit: number;
};

export type CrmIntroductionPath = {
  steps: Array<{
    node: CrmGraphNode;
    edge: CrmGraphEdge | null;
    explanation: string | null;
  }>;
  total_score: number;
  total_hops: number;
  strategy: string;
};

export type CrmIntelligenceDashboard = {
  total_relationships: number;
  active_relationships: number;
  average_score: number;
  at_risk_count: number;
  stale_count: number;
  top_influencers: Array<{ entity_type: RelationshipEntityType; entity_id: string; display_name: string | null }>;
  score_distribution: Record<string, number>;
  category_breakdown: Record<string, number>;
  open_alerts: number;
};

export type RelationshipInput = {
  source_entity_type: RelationshipEntityType;
  source_entity_id: string;
  target_entity_type: RelationshipEntityType;
  target_entity_id: string;
  relationship_type: string;
  category?: string;
  status?: string;
  strength?: string;
  direction?: string;
  is_confidential?: boolean;
  is_verified?: boolean;
  notes?: string;
  metadata_json?: Record<string, unknown>;
  started_at?: string;
  owner_user_id?: string;
};

function buildSearchParams(params: Record<string, string | number | boolean | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : '';
}

export function fetchRelationships(params: RelationshipListParams = {}) {
  return apiFetch<CrmRelationshipListResponse>(`/crm/relationships${buildSearchParams(params)}`);
}

export function fetchRelationship(id: string) {
  return apiFetch<CrmRelationshipDetail>(`/crm/relationships/${id}`);
}

export function createRelationship(input: RelationshipInput) {
  return apiFetch<CrmRelationshipDetail>('/crm/relationships', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function updateRelationship(id: string, input: Partial<RelationshipInput>) {
  return apiFetch<CrmRelationshipDetail>(`/crm/relationships/${id}`, {
    method: 'PUT',
    body: JSON.stringify(input),
  });
}

export function archiveRelationship(id: string) {
  return apiFetch<CrmRelationshipDetail>(`/crm/relationships/${id}/archive`, { method: 'POST' });
}

export function restoreRelationship(id: string) {
  return apiFetch<CrmRelationshipDetail>(`/crm/relationships/${id}/restore`, { method: 'POST' });
}

export function deleteRelationship(id: string) {
  return apiFetch<void>(`/crm/relationships/${id}`, { method: 'DELETE' });
}

export function checkRelationshipDuplicates(input: RelationshipInput) {
  return apiFetch<Array<{ existing_id: string; match_score: number }>>('/crm/relationships/check-duplicates', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function fetchRelationshipGraph(params: {
  center_entity_type?: string;
  center_entity_id?: string;
  depth?: number;
  limit?: number;
  category?: string;
  relationship_type?: string;
}) {
  return apiFetch<CrmRelationshipGraphResponse>(`/crm/relationships/graph${buildSearchParams(params)}`);
}

export function expandGraphNode(nodeId: string, depth = 1) {
  return apiFetch<CrmRelationshipGraphResponse>('/crm/relationships/expand-node', {
    method: 'POST',
    body: JSON.stringify({ node_id: nodeId, depth }),
  });
}

export function fetchIntroductionPaths(params: {
  source_entity_type: string;
  source_entity_id: string;
  target_entity_type: string;
  target_entity_id: string;
  strategy?: string;
}) {
  return apiFetch<{ paths: CrmIntroductionPath[] }>(`/crm/relationships/introduction-paths${buildSearchParams(params)}`);
}

export function fetchIntelligenceDashboard() {
  return apiFetch<CrmIntelligenceDashboard>('/crm/relationships/intelligence');
}

export function fetchRelationshipRecommendations() {
  return apiFetch<Array<{ id: string; title: string; description: string; priority: string; reason: string }>>(
    '/crm/relationships/recommendations',
  );
}

export function calculateRelationshipScores(relationshipId: string) {
  return apiFetch<{ calculated: number; results: Array<Record<string, unknown>> }>(
    `/crm/relationships/scores/calculate?relationship_id=${relationshipId}`,
  );
}

export function exportRelationshipsCsv() {
  return apiFetch<string>('/crm/relationships/export');
}

export function fetchSavedViews() {
  return apiFetch<Array<{ id: string; name: string; filters: Record<string, unknown> | null; is_default: boolean }>>(
    '/crm/relationships/saved-views',
  );
}

export function createSavedView(payload: { name: string; filters?: Record<string, unknown>; is_default?: boolean }) {
  return apiFetch<{ id: string; name: string }>('/crm/relationships/saved-views', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function fetchDecisionMap(companyId: string) {
  return apiFetch<{ company_id: string; roles: Array<Record<string, unknown>> }>(
    `/crm/relationships/company/${companyId}/decision-map`,
  );
}

export function upsertDecisionMapRole(companyId: string, payload: Record<string, unknown>) {
  return apiFetch<Record<string, unknown>>(`/crm/relationships/company/${companyId}/decision-map`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}
