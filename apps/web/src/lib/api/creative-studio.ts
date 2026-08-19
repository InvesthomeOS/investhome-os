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
  linked_project_id?: string | null;
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

export function getCreativeStudioMediaContentUrl(
  assetId: string,
  options?: { linked_project_id?: string | null },
): string {
  const base = `${getApiBaseUrl()}/creative-studio/media/assets/${assetId}/content`;
  const projectId = options?.linked_project_id?.trim();
  if (projectId) {
    return `${base}?linked_project_id=${encodeURIComponent(projectId)}`;
  }
  return base;
}

export async function fetchCreativeStudioMediaBlob(
  assetId: string,
  options?: { linked_project_id?: string | null },
): Promise<Blob> {
  const response = await fetch(getCreativeStudioMediaContentUrl(assetId, options), {
    credentials: 'include',
    cache: 'no-store',
  });
  if (!response.ok) await throwMediaApiError(response);
  return response.blob();
}

export async function listCreativeStudioMediaFolders(options?: {
  parent_id?: string | null;
  linked_project_id?: string | null;
  include_archived?: boolean;
}): Promise<CreativeStudioMediaFolderListResponse> {
  return apiFetch(
    `/creative-studio/media/folders${buildMediaQuery({
      parent_id: options?.parent_id,
      linked_project_id: options?.linked_project_id,
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

// --- Shared Creative Studio AI generation ---

export type CreativeStudioCitation = {
  asset_id: string | null;
  document_id: string;
  document_name: string;
  chunk_id: string;
  chunk_reference: string;
  chunk_order: number;
  project_id: string;
  score: number;
  excerpt: string | null;
  category: string | null;
};

export type CreativeStudioSelectedAsset = {
  asset_id: string;
  filename: string;
  project_id: string;
  folder_category: string | null;
  content_type: string | null;
};

export type CreativeStudioBrandContext = {
  available: boolean;
  reason: string | null;
  excerpts: string[];
  document_ids: string[];
  source_categories: string[];
};

export type CreativeStudioProjectIdentity = {
  project_id: string;
  project_code: string;
  project_name: string;
  project_type: string | null;
  project_status: string | null;
  city: string | null;
  country: string | null;
};

export type CreativeStudioGenerationContext = {
  project_identity: CreativeStudioProjectIdentity;
  verified_facts: string[];
  retrieved_content: Record<string, unknown>[];
  selected_assets: CreativeStudioSelectedAsset[];
  citations: CreativeStudioCitation[];
  brand_context: CreativeStudioBrandContext;
  builder_type: string;
  language: string | null;
  warnings: string[];
};

export type CreativeStudioGenerateRequest = {
  linked_project_id: string;
  builder_type: CreativeStudioDocumentType | string;
  instruction: string;
  selected_asset_ids?: string[];
  language?: string | null;
  builder_context?: Record<string, unknown> | null;
};

export type CreativeStudioGenerateResponse = {
  generated_content: string;
  project_id: string;
  builder_type: string;
  asset_ids_used: string[];
  citations: CreativeStudioCitation[];
  retrieval_confidence: number;
  warnings: string[];
  brand_context: CreativeStudioBrandContext;
  grounded: boolean;
  provider: string;
  model: string;
  search_time_ms: number;
  latency_ms: number;
  context: CreativeStudioGenerationContext | null;
};

export async function generateCreativeStudioContent(
  input: CreativeStudioGenerateRequest,
): Promise<CreativeStudioGenerateResponse> {
  return apiFetch('/ai/creative-studio/generate', {
    method: 'POST',
    body: JSON.stringify({
      linked_project_id: input.linked_project_id,
      builder_type: input.builder_type,
      instruction: input.instruction,
      selected_asset_ids: input.selected_asset_ids ?? [],
      language: input.language ?? undefined,
      builder_context: input.builder_context ?? undefined,
    }),
  });
}

/** Social Media Builder AI Design Engine (Phase 1) — structured Design Ops. */
export type SocialDesignMode = 'create' | 'edit';

export type SocialDesignOp = {
  op: string;
  linked_project_id: string;
  post_id: string;
  element_id: string | null;
  payload: Record<string, unknown>;
};

export type SocialDesignMediaCandidate = {
  asset_id: string;
  filename: string;
  content_type: string | null;
  folder_id: string | null;
  folder_category: string | null;
  tags: string[];
  score: number;
  linked_project_id: string;
};

export type SocialDesignProvider = 'native' | 'ideogram' | 'gpt-image' | 'openai-image';

export type SocialDesignRequest = {
  linked_project_id: string;
  instruction: string;
  mode?: SocialDesignMode;
  mode_explicit?: boolean;
  design_provider?: SocialDesignProvider;
  draft?: {
    posts?: Record<string, unknown>[];
    selected_post_id?: string | null;
  };
  selected_asset_ids?: string[];
  language?: string | null;
  builder_context?: Record<string, unknown> | null;
};

export type SocialDesignGenerationMeta = {
  citations: CreativeStudioCitation[];
  warnings: string[];
  grounded: boolean;
  retrieval_confidence: number;
  asset_ids_used: string[];
  provider: string;
  model: string;
  brand_context: CreativeStudioBrandContext;
  brand_context_status: string;
  search_time_ms: number;
  latency_ms: number;
  mode: SocialDesignMode;
  planner: string;
  generated_by?: string | null;
  project_id?: string | null;
  user_prompt?: string | null;
  generation_intent?: Record<string, unknown> | null;
  source_document_ids?: string[];
  selected_asset_ids?: string[];
  generated_at?: string | null;
  content_package?: Record<string, unknown> | null;
  design_plan?: Record<string, unknown> | null;
  campaign_facts?: Record<string, unknown>[];
  structured_metrics?: Record<string, unknown>[];
  metric_group?: Record<string, unknown> | null;
  creative_concept?: Record<string, unknown> | null;
  creative_plan?: Record<string, unknown> | null;
  composition_blueprint?: Record<string, unknown> | null;
  design_quality?: Record<string, unknown> | null;
  validation?: Record<string, unknown> | null;
  marketing_strategy?: Record<string, unknown> | null;
  copy_quality?: Record<string, unknown> | null;
  headline_candidates?: Record<string, unknown>[];
  campaign_intelligence?: Record<string, unknown> | null;
  verified_facts?: Record<string, unknown>[];
  missing_facts?: Record<string, unknown>[];
  campaign_context_id?: string | null;
  generation_context_id?: string | null;
  provenance?: Record<string, unknown> | null;
  selected_asset?: Record<string, unknown> | null;
  art_director?: Record<string, unknown> | null;
};

export type SocialDesignArtDirectorVariant = {
  key: 'A' | 'B' | 'C';
  label: string;
  creative_direction: string;
  composition: string;
  campaign_type: string;
  design_plan: Record<string, unknown>;
  post: Record<string, unknown>;
  provenance?: Record<string, unknown> | null;
};

export type SocialDesignResponse = {
  linked_project_id: string;
  mode: SocialDesignMode;
  ops: SocialDesignOp[];
  rejected_ops: { op: Record<string, unknown>; reason: string }[];
  posts: Record<string, unknown>[];
  selected_post_id: string | null;
  media_candidates: SocialDesignMediaCandidate[];
  meta: SocialDesignGenerationMeta;
  generated_content: string;
  design_variants?: SocialDesignArtDirectorVariant[];
  selected_variant?: 'A' | 'B' | 'C' | null;
  provenance?: Record<string, unknown> | null;
  selected_asset?: Record<string, unknown> | null;
};

export async function generateSocialDesign(
  input: SocialDesignRequest,
): Promise<SocialDesignResponse> {
  return apiFetch('/ai/creative-studio/social/design', {
    method: 'POST',
    body: JSON.stringify({
      linked_project_id: input.linked_project_id,
      instruction: input.instruction,
      mode: input.mode ?? 'create',
      mode_explicit: input.mode_explicit ?? false,
      design_provider: input.design_provider ?? 'native',
      draft: {
        posts: input.draft?.posts ?? [],
        selected_post_id: input.draft?.selected_post_id ?? null,
      },
      selected_asset_ids: input.selected_asset_ids ?? [],
      language: input.language ?? undefined,
      builder_context: input.builder_context ?? undefined,
    }),
  });
}

/** Ideogram External Design AI POC — isolated from Native SMB. */
export type IdeogramProviderStatus = {
  available: boolean;
  configured: boolean;
  enabled: boolean;
  provider: string;
  model: string;
  remix_endpoint: string;
  generate_endpoint: string;
  reason: string | null;
};

export type IdeogramDesignOutput = {
  variant: 'A' | 'B' | 'C';
  art_direction: string;
  remote_url: string | null;
  local_asset_id: string;
  local_asset_url: string;
  provider: string;
  provider_generation_id: string | null;
  original_remote_url: string | null;
  seed: number | null;
  resolution: string | null;
  metadata: Record<string, unknown>;
};

export type IdeogramDesignRequest = {
  linked_project_id: string;
  instruction: string;
  design_provider?: 'ideogram';
  language?: string | null;
  selected_asset_ids?: string[];
  draft?: {
    posts?: Record<string, unknown>[];
    selected_post_id?: string | null;
  };
  builder_context?: Record<string, unknown> | null;
  regenerate_variant?: 'A' | 'B' | 'C' | null;
  session_id?: string | null;
};

export type IdeogramDesignResponse = {
  provider: string;
  model: string;
  endpoint: string;
  session_id: string;
  linked_project_id: string;
  campaign_context_id: string | null;
  generation_context_id: string;
  aspect_ratio: '1:1';
  source_image: {
    asset_id: string;
    filename: string;
    content_type: string | null;
    folder_category: string | null;
    tags: string[];
  };
  brief: Record<string, unknown>;
  outputs: IdeogramDesignOutput[];
  warnings: string[];
  provider_call_count: number;
  latency_ms: number;
};

export async function getIdeogramProviderStatus(): Promise<IdeogramProviderStatus> {
  return apiFetch('/ai/creative-studio/social/ideogram/status');
}

export async function generateIdeogramDesign(
  input: IdeogramDesignRequest,
): Promise<IdeogramDesignResponse> {
  return apiFetch('/ai/creative-studio/social/ideogram/generate', {
    method: 'POST',
    body: JSON.stringify({
      linked_project_id: input.linked_project_id,
      instruction: input.instruction,
      design_provider: 'ideogram',
      aspect_ratio: '1:1',
      count: 3,
      language: input.language ?? undefined,
      selected_asset_ids: input.selected_asset_ids ?? [],
      draft: {
        posts: input.draft?.posts ?? [],
        selected_post_id: input.draft?.selected_post_id ?? null,
      },
      builder_context: input.builder_context ?? undefined,
      regenerate_variant: input.regenerate_variant ?? undefined,
      session_id: input.session_id ?? undefined,
    }),
  });
}

/** GPT Image visual engine — isolated from Native SMB and Ideogram. */
export type GptImageProviderStatus = {
  available: boolean;
  configured: boolean;
  enabled: boolean;
  provider: string;
  model: string;
  edits_endpoint: string;
  generate_endpoint: string;
  reason: string | null;
};

export type GptImageSourceImage = {
  asset_id: string;
  filename: string;
  content_type: string | null;
  folder_category: string | null;
  tags: string[];
  role?: string;
};

export type GptImageDesignOutput = {
  local_asset_id: string;
  local_asset_url: string;
  provider: string;
  provider_generation_id: string | null;
  resolution: string | null;
  canvas_width: number | null;
  canvas_height: number | null;
  metadata: Record<string, unknown>;
  layers?: Record<string, unknown>[];
  composition_base_asset_id?: string | null;
  composition_warnings?: string[];
};

export type GptImageDesignRequest = {
  linked_project_id?: string | null;
  instruction: string;
  design_provider?: 'gpt-image' | 'openai-image';
  campaign_mode?: 'project' | 'general';
  aspect_ratio?: '1:1' | '4:5' | '16:9' | '9:16' | null;
  format_preset?: string | null;
  language?: string | null;
  selected_asset_ids?: string[];
  draft?: {
    posts?: Record<string, unknown>[];
    selected_post_id?: string | null;
  };
  builder_context?: Record<string, unknown> | null;
  session_id?: string | null;
};

export type GptImageDesignResponse = {
  provider: string;
  model: string;
  endpoint: string;
  campaign_mode: 'project' | 'general';
  session_id: string;
  linked_project_id: string | null;
  campaign_context_id: string | null;
  generation_context_id: string;
  aspect_ratio: string;
  format_preset: string;
  source_image: GptImageSourceImage | null;
  extra_images: GptImageSourceImage[];
  brief: Record<string, unknown>;
  outputs: GptImageDesignOutput[];
  warnings: string[];
  provider_call_count: number;
  latency_ms: number;
};

export async function getGptImageProviderStatus(): Promise<GptImageProviderStatus> {
  return apiFetch('/ai/creative-studio/social/gpt-image/status');
}

export async function generateGptImageDesign(
  input: GptImageDesignRequest,
): Promise<GptImageDesignResponse> {
  return apiFetch('/ai/creative-studio/social/gpt-image/generate', {
    method: 'POST',
    body: JSON.stringify({
      linked_project_id: input.linked_project_id ?? undefined,
      instruction: input.instruction,
      design_provider: input.design_provider ?? 'gpt-image',
      campaign_mode: input.campaign_mode ?? 'project',
      aspect_ratio: input.aspect_ratio ?? undefined,
      format_preset: input.format_preset ?? undefined,
      language: input.language ?? undefined,
      selected_asset_ids: input.selected_asset_ids ?? [],
      draft: {
        posts: input.draft?.posts ?? [],
        selected_post_id: input.draft?.selected_post_id ?? null,
      },
      builder_context: input.builder_context ?? undefined,
      session_id: input.session_id ?? undefined,
    }),
  });
}

/** Creative Director — campaign brief + context (no image generation). */
export type CreativeDirectorCampaignRequest = {
  project_id: string;
  brief: string;
  mode?: 'project' | 'general';
  language?: string | null;
};

export type CreativeDirectorCampaignResponse = {
  campaign_id: string;
  project_id: string;
  brief: Record<string, unknown>;
  campaign_context: Record<string, unknown>;
};

export async function createCreativeDirectorCampaign(
  input: CreativeDirectorCampaignRequest,
): Promise<CreativeDirectorCampaignResponse> {
  return apiFetch('/ai/creative-studio/campaigns', {
    method: 'POST',
    body: JSON.stringify({
      project_id: input.project_id,
      brief: input.brief,
      mode: input.mode ?? 'project',
      language: input.language ?? undefined,
    }),
  });
}

/** Generate MASTER ad from approved Campaign Context → GPT Image → Media Library. */
export type CreativeDirectorGenerateAdRequest = {
  language?: string | null;
  aspect_ratio?: '1:1' | '4:5' | '16:9' | '9:16' | null;
  format_preset?: string | null;
};

export type CreativeDirectorGenerateAdResponse = {
  campaign_id: string;
  project_id: string;
  language: string;
  aspect_ratio: string;
  format_preset: string;
  interior_asset_id: string;
  logo_asset_id: string;
  final_asset_id: string;
  final_asset_url: string;
  composition_base_asset_id?: string | null;
  creative_brief_summary: Record<string, unknown>;
  final_turkish_texts: Record<string, string>;
  claim_guard: Record<string, unknown>;
  project_asset_lock: Record<string, unknown>;
  provider_call_count: number;
  latency_ms: number;
  warnings: string[];
  gpt_image: GptImageDesignResponse;
};

export async function generateCreativeDirectorAd(
  campaignId: string,
  input: CreativeDirectorGenerateAdRequest = {},
): Promise<CreativeDirectorGenerateAdResponse> {
  return apiFetch(`/ai/creative-studio/campaigns/${campaignId}/generate-ad`, {
    method: 'POST',
    body: JSON.stringify({
      language: input.language ?? undefined,
      aspect_ratio: input.aspect_ratio ?? '4:5',
      format_preset: input.format_preset ?? 'portrait',
    }),
  });
}
