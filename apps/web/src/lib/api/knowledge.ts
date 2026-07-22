import { apiFetch } from '@/lib/api/client';

export type ProviderCapabilityStatus = {
  provider: string;
  available: boolean;
  reason: string | null;
  required_env: string[];
  endpoints: string[];
};

export type KnowledgeMetricValue = {
  value: number | null;
  available: boolean;
  reason: string | null;
  drilldown: string | null;
};

export type KnowledgeOverview = {
  total_documents: KnowledgeMetricValue;
  recent_uploads: KnowledgeMetricValue;
  awaiting_review: KnowledgeMetricValue;
  expiring_soon: KnowledgeMetricValue;
  failed_jobs: KnowledgeMetricValue;
  unlinked: KnowledgeMetricValue;
  duplicate_candidates: KnowledgeMetricValue;
  storage_used_bytes: KnowledgeMetricValue;
  collections: KnowledgeMetricValue;
  indexing_status: ProviderCapabilityStatus;
  ocr_status: ProviderCapabilityStatus;
  ai_status: ProviderCapabilityStatus;
  malware_scan_status: ProviderCapabilityStatus;
  vector_search_status: ProviderCapabilityStatus;
};

export type KnowledgeCategory = {
  id: string;
  code: string;
  name_en: string;
  name_tr: string;
  description: string | null;
  sort_order: number;
  is_active: boolean;
  is_system: boolean;
};

export type KnowledgeCollection = {
  id: string;
  name: string;
  description: string | null;
  collection_type: string;
  smart_rules_json: string | null;
  owner_user_id: string | null;
  is_shared: boolean;
  document_count: number;
  created_at: string;
  updated_at: string;
};

export type KnowledgeReviewItem = {
  id: string;
  document_id: string;
  document_title: string | null;
  reason: string;
  status: string;
  priority: string;
  details: string | null;
  confidence_score: string | null;
  assigned_to_user_id: string | null;
  resolved_by_user_id: string | null;
  resolved_at: string | null;
  resolution_notes: string | null;
  created_at: string;
  updated_at: string;
};

export type KnowledgeRetentionPolicy = {
  id: string;
  name: string;
  description: string | null;
  category_code: string | null;
  retention_days: number | null;
  action_on_expiry: string;
  is_active: boolean;
  legal_hold_capable: boolean;
  created_at: string;
  updated_at: string;
};

export type KnowledgeAiSearchHit = {
  document_id: string;
  title: string;
  snippet: string;
  citation: string | null;
  page: number | null;
  score: number | null;
  source: string;
  ai_summary: string | null;
};

export type KnowledgeAiSearchResponse = {
  query: string;
  hits: KnowledgeAiSearchHit[];
  provider: ProviderCapabilityStatus;
  note: string | null;
};

export type KnowledgeSettings = {
  auto_enqueue_review_on_low_confidence: boolean;
  expiration_alert_days: number;
  enable_duplicate_detection: boolean;
  vector_indexing_enabled: boolean;
  malware_scanning_enabled: boolean;
  providers: Record<string, ProviderCapabilityStatus>;
  placeholders: Record<string, string>;
};

export type KnowledgePipelineStage = {
  stage: string;
  label: string;
  count: number;
  status: string;
};

export type KnowledgePipelineStatus = {
  stages: KnowledgePipelineStage[];
  automation_hook: string;
  note: string | null;
};

export type KnowledgePlaceholder = {
  feature: string;
  status: string;
  description: string;
  required_env: string[];
  endpoints: string[];
};

export async function fetchKnowledgeOverview() {
  return apiFetch<KnowledgeOverview>('/knowledge/overview');
}

export async function fetchKnowledgePipeline() {
  return apiFetch<KnowledgePipelineStatus>('/knowledge/pipeline');
}

export async function fetchKnowledgeCategories() {
  return apiFetch<KnowledgeCategory[]>('/knowledge/categories');
}

export async function createKnowledgeCategory(body: {
  code: string;
  name_en: string;
  name_tr: string;
  description?: string;
  sort_order?: number;
}) {
  return apiFetch<KnowledgeCategory>('/knowledge/categories', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export async function fetchKnowledgeCollections() {
  return apiFetch<KnowledgeCollection[]>('/knowledge/collections');
}

export async function createKnowledgeCollection(body: {
  name: string;
  description?: string;
  collection_type?: string;
  smart_rules?: Record<string, unknown>;
  is_shared?: boolean;
}) {
  return apiFetch<KnowledgeCollection>('/knowledge/collections', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export async function addDocumentToCollection(collectionId: string, documentId: string) {
  return apiFetch<KnowledgeCollection>(`/knowledge/collections/${collectionId}/items`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_id: documentId }),
  });
}

export async function fetchKnowledgeReview(params?: { status?: string; reason?: string }) {
  const qs = new URLSearchParams();
  if (params?.status) qs.set('status', params.status);
  if (params?.reason) qs.set('reason', params.reason);
  const suffix = qs.toString() ? `?${qs}` : '';
  return apiFetch<KnowledgeReviewItem[]>(`/knowledge/review${suffix}`);
}

export async function syncKnowledgeReview() {
  return apiFetch<{ created: number }>('/knowledge/review/sync', { method: 'POST' });
}

export async function resolveKnowledgeReview(
  itemId: string,
  body: { status: string; resolution_notes?: string },
) {
  return apiFetch<KnowledgeReviewItem>(`/knowledge/review/${itemId}/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export async function fetchKnowledgeRetention() {
  return apiFetch<KnowledgeRetentionPolicy[]>('/knowledge/retention');
}

export async function createKnowledgeRetention(body: {
  name: string;
  description?: string;
  category_code?: string;
  retention_days?: number;
  action_on_expiry?: string;
  legal_hold_capable?: boolean;
}) {
  return apiFetch<KnowledgeRetentionPolicy>('/knowledge/retention', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export async function knowledgeAiSearch(query: string, limit = 20) {
  return apiFetch<KnowledgeAiSearchResponse>('/knowledge/ai-search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, limit }),
  });
}

export async function fetchKnowledgeSettings() {
  return apiFetch<KnowledgeSettings>('/knowledge/settings');
}

export async function updateKnowledgeSettings(body: {
  auto_enqueue_review_on_low_confidence?: boolean;
  expiration_alert_days?: number;
  enable_duplicate_detection?: boolean;
}) {
  return apiFetch<KnowledgeSettings>('/knowledge/settings', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export async function fetchKnowledgePlaceholders() {
  return apiFetch<KnowledgePlaceholder[]>('/knowledge/placeholders');
}
