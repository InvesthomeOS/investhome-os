import { apiFetch, getApiBaseUrl } from '@/lib/api/client';

export type AssetAiPrep = {
  language?: string | null;
  audience?: string | null;
  market?: string | null;
  property_type?: string | null;
  country?: string | null;
  city?: string | null;
  keywords?: string[] | null;
};

export type AssetSummary = {
  id: string;
  name: string;
  title: string;
  asset_type: string;
  document_id: string | null;
  file_ref?: string | null;
  status: string;
  folder: string | null;
  project_id: string | null;
  campaign_id: string | null;
  project_name?: string | null;
  campaign_name?: string | null;
  rights_status: string;
  tags: string[];
  thumbnail_document_id?: string | null;
  uploaded_by?: string | null;
  created_at: string;
  updated_at: string;
};

export type AssetDetail = AssetSummary & {
  description: string | null;
  notes: string | null;
  ai_prep: AssetAiPrep;
  archived_at: string | null;
};

export type AssetListResponse = {
  items: AssetSummary[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
};

export type AssetMetricValue = {
  key: string;
  label: string;
  state: string;
  value: number | string | null;
  unit?: string | null;
  evidence?: Record<string, unknown> | null;
};

export type AssetListParams = {
  page?: number;
  pageSize?: number;
  assetType?: string;
  status?: string;
  folder?: string;
  projectId?: string;
  campaignId?: string;
  tag?: string;
  search?: string;
  includeArchived?: boolean;
  rightsStatus?: string;
};

function buildQuery(params: AssetListParams = {}) {
  const query = new URLSearchParams();
  query.set('page', String(params.page ?? 1));
  query.set('page_size', String(params.pageSize ?? 25));
  if (params.assetType) query.set('asset_type', params.assetType);
  if (params.status) query.set('status', params.status);
  if (params.folder) query.set('folder', params.folder);
  if (params.projectId) query.set('project_id', params.projectId);
  if (params.campaignId) query.set('campaign_id', params.campaignId);
  if (params.tag) query.set('tag', params.tag);
  if (params.search) query.set('search', params.search);
  if (params.rightsStatus) query.set('rights_status', params.rightsStatus);
  if (params.includeArchived) query.set('include_archived', 'true');
  return query.toString();
}

export async function fetchAssets(params: AssetListParams = {}) {
  return apiFetch<AssetListResponse>(`/marketing/assets?${buildQuery(params)}`);
}

export async function fetchAsset(assetId: string, includeArchived = false) {
  const suffix = includeArchived ? '?include_archived=true' : '';
  return apiFetch<AssetDetail>(`/marketing/assets/${assetId}${suffix}`);
}

export async function fetchAssetSummary() {
  return apiFetch<{ metrics: AssetMetricValue[] }>('/marketing/assets/summary');
}

export async function fetchAssetFolders() {
  return apiFetch<{ items: string[] }>('/marketing/assets/folders');
}

export async function createAssetFromDocument(payload: {
  document_id: string;
  name?: string;
  title?: string;
  asset_type?: string;
  description?: string;
  tags?: string[];
  folder?: string;
  project_id?: string;
  campaign_id?: string;
  notes?: string;
  status?: string;
  ai_prep?: AssetAiPrep;
}) {
  return apiFetch<{ asset: AssetDetail }>('/marketing/assets/from-document', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateAsset(assetId: string, payload: Record<string, unknown>) {
  return apiFetch<{ asset: AssetDetail }>(`/marketing/assets/${assetId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function archiveAsset(assetId: string) {
  return apiFetch<{ asset: AssetDetail }>(`/marketing/assets/${assetId}/archive`, { method: 'POST' });
}

export async function restoreAsset(assetId: string) {
  return apiFetch<{ asset: AssetDetail }>(`/marketing/assets/${assetId}/restore`, { method: 'POST' });
}

export async function linkAssetCampaign(assetId: string, campaignId: string | null) {
  return apiFetch<{ asset: AssetDetail }>(`/marketing/assets/${assetId}/link-campaign`, {
    method: 'POST',
    body: JSON.stringify({ campaign_id: campaignId }),
  });
}

export async function linkAssetProject(assetId: string, projectId: string | null) {
  return apiFetch<{ asset: AssetDetail }>(`/marketing/assets/${assetId}/link-project`, {
    method: 'POST',
    body: JSON.stringify({ project_id: projectId }),
  });
}

export async function fetchAssetRightsReadiness(assetId: string) {
  return apiFetch<{ state: string; rights_status: string; remediation: string[] }>(
    `/marketing/assets/${assetId}/rights-readiness`,
  );
}

export async function updateAssetRights(assetId: string, payload: { status?: string; license_type?: string }) {
  return apiFetch(`/marketing/assets/${assetId}/rights`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function fetchAssetUsage(assetId: string) {
  return apiFetch<{ items: unknown[] }>(`/marketing/assets/${assetId}/usage`);
}

export function assetExportUrl(params: AssetListParams = {}) {
  return `${getApiBaseUrl()}/marketing/assets/export?${buildQuery(params)}`;
}
