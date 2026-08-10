import {
  apiFetch,
  getApiBaseUrl,
  parseApiErrorBody,
  ApiError,
  type ApiErrorBody,
} from '@/lib/api/client';

export const CREATIVE_STUDIO_DOCUMENT_TYPES = [
  'website',
  'landing',
  'blog',
  'email',
  'social',
  'ads',
  'proposal',
  'presentation',
  'brochure',
  'video',
  'image',
  'architectural',
] as const;

export type CreativeStudioDocumentType = (typeof CREATIVE_STUDIO_DOCUMENT_TYPES)[number];

export const CREATIVE_STUDIO_PROJECT_STATUSES = ['active', 'draft', 'archived'] as const;
export type CreativeStudioProjectStatus = (typeof CREATIVE_STUDIO_PROJECT_STATUSES)[number];

export const CREATIVE_STUDIO_DOCUMENT_STATUSES = ['draft', 'ready', 'published', 'archived'] as const;
export type CreativeStudioDocumentStatus = (typeof CREATIVE_STUDIO_DOCUMENT_STATUSES)[number];

export type CreativeStudioProject = {
  id: string;
  name: string;
  description: string | null;
  status: CreativeStudioProjectStatus;
  company_id: string | null;
  linked_project_id: string | null;
  owner_id: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  document_count: number;
};

export type CreativeStudioDocument = {
  id: string;
  project_id: string;
  title: string;
  description: string | null;
  document_type: CreativeStudioDocumentType;
  status: CreativeStudioDocumentStatus;
  language: string | null;
  thumbnail_url: string | null;
  draft_body_json: Record<string, unknown> | null;
  draft_updated_at: string | null;
  draft_updated_by_user_id: string | null;
  current_version_id: string | null;
  created_by_user_id: string | null;
  updated_by_user_id: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  version_count: number;
};

export type CreativeStudioVersion = {
  id: string;
  document_id: string;
  version_number: number;
  label: string | null;
  summary: string | null;
  body_json: Record<string, unknown> | null;
  created_by_user_id: string | null;
  created_at: string;
};

export type CreativeStudioProjectCreate = {
  name: string;
  description?: string | null;
  status?: CreativeStudioProjectStatus;
  company_id?: string | null;
  linked_project_id?: string | null;
};

export type CreativeStudioDocumentCreate = {
  title: string;
  description?: string | null;
  document_type: CreativeStudioDocumentType;
  status?: CreativeStudioDocumentStatus;
  language?: string | null;
  thumbnail_url?: string | null;
  draft_body_json?: Record<string, unknown> | null;
};

export type CreativeStudioVersionCreate = {
  body_json?: Record<string, unknown> | null;
  label?: string | null;
  summary?: string | null;
};

export type CreativeStudioRestoreRequest = {
  create_version?: boolean;
  label?: string | null;
  summary?: string | null;
};

export type CreativeStudioRestoreResponse = {
  document: CreativeStudioDocument;
  new_version: CreativeStudioVersion | null;
};

export async function listCreativeStudioProjects(options?: {
  includeArchived?: boolean;
}): Promise<{ items: CreativeStudioProject[]; total: number }> {
  const params = new URLSearchParams();
  if (options?.includeArchived) params.set('include_archived', 'true');
  const query = params.toString();
  return apiFetch(`/creative-studio/projects${query ? `?${query}` : ''}`);
}

export async function createCreativeStudioProject(
  input: CreativeStudioProjectCreate,
): Promise<CreativeStudioProject> {
  return apiFetch('/creative-studio/projects', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function listCreativeStudioDocuments(
  projectId: string,
  options?: { includeArchived?: boolean },
): Promise<{ items: CreativeStudioDocument[]; total: number }> {
  const params = new URLSearchParams();
  if (options?.includeArchived) params.set('include_archived', 'true');
  const query = params.toString();
  return apiFetch(
    `/creative-studio/projects/${projectId}/documents${query ? `?${query}` : ''}`,
  );
}

export async function createCreativeStudioDocument(
  projectId: string,
  input: CreativeStudioDocumentCreate,
): Promise<CreativeStudioDocument> {
  return apiFetch(`/creative-studio/projects/${projectId}/documents`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function getCreativeStudioDocument(
  documentId: string,
): Promise<CreativeStudioDocument> {
  return apiFetch(`/creative-studio/documents/${documentId}`);
}

export async function saveCreativeStudioDraft(
  documentId: string,
  draftBodyJson: Record<string, unknown>,
): Promise<CreativeStudioDocument> {
  return apiFetch(`/creative-studio/documents/${documentId}/draft`, {
    method: 'PUT',
    body: JSON.stringify({ draft_body_json: draftBodyJson }),
  });
}

export async function createCreativeStudioVersion(
  documentId: string,
  input: CreativeStudioVersionCreate = {},
): Promise<CreativeStudioVersion> {
  return apiFetch(`/creative-studio/documents/${documentId}/versions`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function listCreativeStudioVersions(
  documentId: string,
  options?: { includeBody?: boolean },
): Promise<{ items: CreativeStudioVersion[]; total: number }> {
  const params = new URLSearchParams();
  if (options?.includeBody) params.set('include_body', 'true');
  const query = params.toString();
  return apiFetch(
    `/creative-studio/documents/${documentId}/versions${query ? `?${query}` : ''}`,
  );
}

export async function restoreCreativeStudioVersion(
  documentId: string,
  versionId: string,
  input: CreativeStudioRestoreRequest = {},
): Promise<CreativeStudioRestoreResponse> {
  return apiFetch(
    `/creative-studio/documents/${documentId}/versions/${versionId}/restore`,
    {
      method: 'POST',
      body: JSON.stringify(input),
    },
  );
}

// --- Media Library ---

export type MediaAssetSourceType = 'upload' | 'google_drive';
export type MediaAssetSyncStatus = 'active' | 'changed' | 'missing' | 'error';

export type CreativeStudioMediaAsset = {
  id: string;
  filename: string;
  content_type: string;
  file_size: number;
  width: number | null;
  height: number | null;
  storage_provider: string;
  storage_key: string;
  thumbnail_storage_key: string | null;
  url: string;
  thumbnail_url: string | null;
  folder_id: string | null;
  tags: string[] | null;
  company_id: string | null;
  linked_project_id: string | null;
  uploaded_by_user_id: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  thumbnail_pending: boolean;
  /** Drive sync visibility — omitted/null for classic uploads. */
  source_type?: MediaAssetSourceType | string | null;
  external_file_id?: string | null;
  external_modified_at?: string | null;
  sync_status?: MediaAssetSyncStatus | string | null;
  folder_category?: string | null;
  possible_duplicate?: boolean;
  web_view_link?: string | null;
  external_checksum?: string | null;
};

export type CreativeStudioMediaAssetListResponse = {
  items: CreativeStudioMediaAsset[];
  total: number;
  page: number;
  page_size: number;
};

export type CreativeStudioMediaFolder = {
  id: string;
  name: string;
  parent_id: string | null;
  company_id: string | null;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
};

export type CreativeStudioMediaFolderListResponse = {
  items: CreativeStudioMediaFolder[];
  total: number;
};

export type CreativeStudioMediaUploadInput = {
  file: File | Blob;
  folder_id?: string | null;
  tags?: string | string[] | null;
  company_id?: string | null;
  linked_project_id?: string | null;
};

export type CreativeStudioMediaListParams = {
  folder_id?: string | null;
  tag?: string | null;
  linked_project_id?: string | null;
  include_archived?: boolean;
  page?: number;
  page_size?: number;
};

export type CreativeStudioMediaSearchParams = CreativeStudioMediaListParams & {
  q: string;
};

function buildMediaQuery(
  params?: CreativeStudioMediaListParams & { q?: string; parent_id?: string | null },
): string {
  const search = new URLSearchParams();
  if (params?.q) search.set('q', params.q);
  if (params?.folder_id) search.set('folder_id', params.folder_id);
  if (params?.tag) search.set('tag', params.tag);
  if (params?.linked_project_id) search.set('linked_project_id', params.linked_project_id);
  if (params?.include_archived) search.set('include_archived', 'true');
  if (params?.page != null) search.set('page', String(params.page));
  if (params?.page_size != null) search.set('page_size', String(params.page_size));
  if (params?.parent_id) search.set('parent_id', params.parent_id);
  const query = search.toString();
  return query ? `?${query}` : '';
}

async function throwMediaApiError(response: Response): Promise<never> {
  const requestId = response.headers.get('X-Request-Id');
  let message = `Request failed with status ${response.status}`;
  let code: string | undefined;
  let details: ApiErrorBody['details'];
  try {
    const body = (await response.json()) as ApiErrorBody;
    const parsed = parseApiErrorBody(body, response.status);
    message = parsed.message;
    code = parsed.code;
    details = parsed.details;
  } catch {
    // Keep default message when response is not JSON.
  }
  throw new ApiError(message, response.status, code, requestId, details);
}

export async function listCreativeStudioMediaAssets(
  params?: CreativeStudioMediaListParams,
): Promise<CreativeStudioMediaAssetListResponse> {
  return apiFetch(`/creative-studio/media/assets${buildMediaQuery(params)}`);
}

export async function searchCreativeStudioMediaAssets(
  params: CreativeStudioMediaSearchParams,
): Promise<CreativeStudioMediaAssetListResponse> {
  return apiFetch(`/creative-studio/media/search${buildMediaQuery(params)}`);
}

export async function getCreativeStudioMediaAsset(
  assetId: string,
): Promise<CreativeStudioMediaAsset> {
  return apiFetch(`/creative-studio/media/assets/${assetId}`);
}

export async function uploadCreativeStudioMediaAsset(
  input: CreativeStudioMediaUploadInput,
): Promise<CreativeStudioMediaAsset> {
  const form = new FormData();
  form.append('file', input.file);
  if (input.folder_id) form.append('folder_id', input.folder_id);
  if (input.tags != null) {
    form.append(
      'tags',
      Array.isArray(input.tags) ? JSON.stringify(input.tags) : input.tags,
    );
  }
  if (input.company_id) form.append('company_id', input.company_id);
  if (input.linked_project_id) form.append('linked_project_id', input.linked_project_id);

  const response = await fetch(`${getApiBaseUrl()}/creative-studio/media/upload`, {
    method: 'POST',
    credentials: 'include',
    body: form,
    cache: 'no-store',
  });
  if (!response.ok) await throwMediaApiError(response);
  return response.json() as Promise<CreativeStudioMediaAsset>;
}

export function getCreativeStudioMediaContentUrl(assetId: string): string {
  return `${getApiBaseUrl()}/creative-studio/media/assets/${assetId}/content`;
}

export async function fetchCreativeStudioMediaBlob(assetId: string): Promise<Blob> {
  const response = await fetch(getCreativeStudioMediaContentUrl(assetId), {
    credentials: 'include',
    cache: 'no-store',
  });
  if (!response.ok) await throwMediaApiError(response);
  return response.blob();
}

export async function listCreativeStudioMediaFolders(options?: {
  parent_id?: string | null;
  include_archived?: boolean;
}): Promise<CreativeStudioMediaFolderListResponse> {
  return apiFetch(
    `/creative-studio/media/folders${buildMediaQuery({
      parent_id: options?.parent_id,
      include_archived: options?.include_archived,
    })}`,
  );
}

export type CreativeStudioMediaFolderCreate = {
  name: string;
  parent_id?: string | null;
  company_id?: string | null;
};

export async function createCreativeStudioMediaFolder(
  input: CreativeStudioMediaFolderCreate,
): Promise<CreativeStudioMediaFolder> {
  return apiFetch('/creative-studio/media/folders', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function updateCreativeStudioMediaTags(
  assetId: string,
  tags: string[],
): Promise<CreativeStudioMediaAsset> {
  return apiFetch(`/creative-studio/media/assets/${assetId}/tags`, {
    method: 'PATCH',
    body: JSON.stringify({ tags }),
  });
}

export async function deleteCreativeStudioMediaAsset(
  assetId: string,
): Promise<CreativeStudioMediaAsset> {
  return apiFetch(`/creative-studio/media/assets/${assetId}`, {
    method: 'DELETE',
  });
}
