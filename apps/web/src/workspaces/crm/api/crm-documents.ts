import { apiFetch } from '@/lib/api/client';

export type CrmDocumentFeedStats = {
  total: number;
  person: number;
  purchase: number;
  hidden: number;
  unresolved: number;
};

export type CrmDocumentFeedItem = {
  id: string;
  source_key: string;
  filename: string;
  category: string;
  category_label: string;
  mime_type: string | null;
  file_size: number;
  file_kind: string | null;
  source: string | null;
  source_type: string | null;
  occurred_at: string | null;
  hidden: boolean;
  scope: 'person' | 'purchase' | 'unresolved' | string;
  status: string;
  contact_id: string | null;
  contact_name: string | null;
  agreement_id: string | null;
  project_group: string | null;
  project_label: string | null;
  unit_number: string | null;
  current_unit: string | null;
  historical_unit: string | null;
  project_unit: string | null;
  checksum: string | null;
  bitrix_file_id: string | null;
  previewable: boolean;
  extra_contact_count: number;
};

export type CrmDocumentFeedResponse = {
  items: CrmDocumentFeedItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  stats: CrmDocumentFeedStats;
  request_id?: string;
};

export type CrmDocumentFeedParams = {
  search?: string;
  person?: string;
  project_group?: string;
  unit?: string;
  category?: string;
  source?: string;
  visibility?: string;
  scope?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
};

function buildParams(values: Record<string, string | number | undefined>): URLSearchParams {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value === undefined || value === '') continue;
    params.set(key, String(value));
  }
  return params;
}

export async function fetchCrmDocumentFeed(params: CrmDocumentFeedParams = {}): Promise<CrmDocumentFeedResponse> {
  const q = buildParams({
    search: params.search,
    person: params.person,
    project_group: params.project_group,
    unit: params.unit,
    category: params.category,
    source: params.source,
    visibility: params.visibility,
    scope: params.scope,
    date_from: params.date_from,
    date_to: params.date_to,
    page: params.page ?? 1,
    page_size: params.page_size ?? 25,
  });
  return apiFetch(`/crm/documents/feed?${q.toString()}`);
}

export async function setCrmDocumentHubVisibility(
  documentId: string,
  hidden: boolean,
): Promise<{ id: string; hidden: boolean; updated_links: number }> {
  return apiFetch(`/crm/documents/${documentId}/hub-visibility`, {
    method: 'POST',
    body: JSON.stringify({ hidden }),
  });
}
