import { getApiBaseUrl } from '@/lib/api/client';

export const DOCUMENT_TYPES = [
  'contract',
  'operating_agreement',
  'subscription_agreement',
  'offering_document',
  'investor_document',
  'project_document',
  'construction_drawing',
  'architectural_drawing',
  'permit',
  'inspection',
  'title_document',
  'closing_document',
  'loan_document',
  'insurance',
  'appraisal',
  'lease',
  'invoice',
  'receipt',
  'bank_statement',
  'financial_report',
  'presentation',
  'marketing_material',
  'photo',
  'spreadsheet',
  'correspondence',
  'legal_document',
  'tax_document',
  'pdf',
  'image',
  'word',
  'excel',
  'powerpoint',
  'video',
  'text',
  'zip',
  'other',
] as const;

export type DocumentType = (typeof DOCUMENT_TYPES)[number];

export const DOCUMENT_FILE_KINDS = [
  'pdf',
  'image',
  'word',
  'excel',
  'powerpoint',
  'video',
  'text',
  'zip',
  'other',
] as const;
export type DocumentFileKind = (typeof DOCUMENT_FILE_KINDS)[number];

export const DOCUMENT_FOLDERS = [
  'projects',
  'marketing',
  'contracts',
  'investors',
  'finance',
  'legal',
  'photos',
  'construction',
  'general',
] as const;
export type DocumentFolder = (typeof DOCUMENT_FOLDERS)[number];

export const DOCUMENT_VISIBILITIES = ['private', 'team', 'organization'] as const;
export type DocumentVisibility = (typeof DOCUMENT_VISIBILITIES)[number];

export const DOCUMENT_STATUSES = ['draft', 'active', 'expired', 'superseded', 'archived'] as const;
export type DocumentStatus = (typeof DOCUMENT_STATUSES)[number];

export const CONFIDENTIALITY_LEVELS = [
  'public',
  'internal',
  'confidential',
  'highly_confidential',
] as const;
export type ConfidentialityLevel = (typeof CONFIDENTIALITY_LEVELS)[number];

export interface DocumentLink {
  id: string;
  document_id: string;
  entity_type: string;
  entity_id: string;
  relationship_type: string | null;
  hidden_from_view?: boolean;
  created_at: string;
}

export interface Document {
  id: string;
  title: string;
  original_file_name: string;
  stored_file_name: string;
  file_extension: string;
  mime_type: string;
  file_size: number;
  storage_provider: string;
  checksum: string;
  document_type: DocumentType;
  category: string | null;
  folder: DocumentFolder;
  file_kind: DocumentFileKind;
  status: DocumentStatus;
  visibility: DocumentVisibility;
  confidentiality_level: ConfidentialityLevel;
  version_number: number;
  parent_document_id: string | null;
  uploaded_by_user_id: string | null;
  uploaded_by_name: string | null;
  owner_user_id: string | null;
  owner_name: string | null;
  company_id: string | null;
  project_id: string | null;
  investor_id: string | null;
  lead_id: string | null;
  transaction_id: string | null;
  description: string | null;
  notes: string | null;
  tags: string | null;
  document_date: string | null;
  expiration_date: string | null;
  is_latest_version: boolean;
  processing_status: string;
  version_notes: string | null;
  download_count: number;
  preview_count: number;
  is_previewable: boolean;
  hidden_from_view?: boolean;
  bitrix_file_id?: string | null;
  related_record_label: string | null;
  is_demo: boolean;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
  links: DocumentLink[];
}

export const DOCUMENT_RELATED_MODULES = [
  'lead',
  'contact',
  'company',
  'opportunity',
  'investor',
  'project',
  'marketing_campaign',
  'marketing_asset',
  'task',
  'calendar_event',
  'financial_record',
] as const;
export type DocumentRelatedModule = (typeof DOCUMENT_RELATED_MODULES)[number];

export const DOCUMENT_LINK_ENTITY_TYPES = [
  'lead',
  'contact',
  'crm_contact',
  'company',
  'crm_company',
  'opportunity',
  'investor',
  'project',
  'marketing_campaign',
  'marketing_asset',
  'campaign',
  'task',
  'calendar_event',
  'financial_record',
  'transaction',
] as const;

export interface DocumentListResponse {
  items: Document[];
  total: number;
  page: number;
  page_size: number;
}

export interface DocumentMetricValue {
  value: number | null;
  available: boolean;
  reason: string | null;
}

export interface DocumentStorageFileItem {
  id: string;
  title: string;
  file_size: number;
  file_kind: DocumentFileKind;
  preview_count: number;
  download_count: number;
}

export interface DocumentWorkspaceOverview {
  total: DocumentMetricValue;
  storage_used_bytes: DocumentMetricValue;
  recent_uploads: DocumentMetricValue;
  most_viewed: DocumentMetricValue;
  archived: DocumentMetricValue;
  without_relation: DocumentMetricValue;
  most_used_types: Array<{ file_kind: DocumentFileKind; count: number }>;
  documents_by_type: Array<{ file_kind: DocumentFileKind; count: number }>;
  largest_files: DocumentStorageFileItem[];
  most_viewed_files: DocumentStorageFileItem[];
}

export interface DocumentFilters {
  search?: string;
  document_type?: DocumentType | '';
  file_kind?: DocumentFileKind | '';
  folder?: DocumentFolder | '';
  tags?: string;
  visibility?: DocumentVisibility | '';
  category?: string;
  status?: DocumentStatus | '';
  confidentiality?: ConfidentialityLevel | '';
  project_id?: string;
  investor_id?: string;
  campaign_id?: string;
  company_id?: string;
  owner_user_id?: string;
  related_module?: DocumentRelatedModule | '';
  created_from?: string;
  created_to?: string;
  without_relation?: boolean;
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
  include_archived?: boolean;
}

export interface DocumentUploadMeta {
  title?: string;
  document_type?: DocumentType;
  category?: string;
  folder?: DocumentFolder;
  visibility?: DocumentVisibility;
  project_id?: string;
  investor_id?: string;
  lead_id?: string;
  transaction_id?: string;
  company_id?: string;
  confidentiality_level?: ConfidentialityLevel;
  document_date?: string;
  expiration_date?: string;
  tags?: string;
  description?: string;
  notes?: string;
}

export interface DocumentUploadResult {
  success: boolean;
  document: Document | null;
  file_name: string;
  error: string | null;
}

export interface DocumentVersion {
  id: string;
  version_number: number;
  title: string;
  original_file_name: string;
  file_size: number;
  uploaded_by_user_id: string | null;
  uploaded_by_name: string | null;
  version_notes: string | null;
  is_latest_version: boolean;
  created_at: string;
}

export interface DocumentUpdatePayload {
  title?: string;
  document_type?: DocumentType;
  category?: string | null;
  folder?: DocumentFolder;
  visibility?: DocumentVisibility;
  status?: DocumentStatus;
  confidentiality_level?: ConfidentialityLevel;
  description?: string | null;
  notes?: string | null;
  tags?: string | null;
  owner_user_id?: string | null;
  company_id?: string | null;
  project_id?: string | null;
  investor_id?: string | null;
  lead_id?: string | null;
  transaction_id?: string | null;
}

function buildQuery(filters: DocumentFilters = {}): string {
  const params = new URLSearchParams();
  if (filters.search?.trim()) params.set('search', filters.search.trim());
  if (filters.document_type) params.set('document_type', filters.document_type);
  if (filters.file_kind) params.set('file_kind', filters.file_kind);
  if (filters.folder) params.set('folder', filters.folder);
  if (filters.tags?.trim()) params.set('tags', filters.tags.trim());
  if (filters.visibility) params.set('visibility', filters.visibility);
  if (filters.category) params.set('category', filters.category);
  if (filters.status) params.set('status', filters.status);
  if (filters.confidentiality) params.set('confidentiality', filters.confidentiality);
  if (filters.project_id) params.set('project_id', filters.project_id);
  if (filters.investor_id) params.set('investor_id', filters.investor_id);
  if (filters.campaign_id) params.set('campaign_id', filters.campaign_id);
  if (filters.company_id) params.set('company_id', filters.company_id);
  if (filters.owner_user_id) params.set('owner_user_id', filters.owner_user_id);
  if (filters.related_module) params.set('related_module', filters.related_module);
  if (filters.created_from) params.set('created_from', filters.created_from);
  if (filters.created_to) params.set('created_to', filters.created_to);
  if (filters.without_relation) params.set('without_relation', 'true');
  if (filters.sort_by) params.set('sort_by', filters.sort_by);
  if (filters.sort_dir) params.set('sort_dir', filters.sort_dir);
  if (filters.page) params.set('page', String(filters.page));
  if (filters.page_size) params.set('page_size', String(filters.page_size));
  if (filters.include_archived) params.set('include_archived', 'true');
  const query = params.toString();
  return query ? `?${query}` : '';
}

export async function fetchDocuments(filters: DocumentFilters = {}): Promise<DocumentListResponse> {
  const response = await fetch(`${getApiBaseUrl()}/documents${buildQuery(filters)}`, {
    credentials: 'include',
    cache: 'no-store',
  });
  if (response.status === 403) throw new Error('permission_denied');
  if (!response.ok) throw new Error('Failed to load documents');
  return response.json() as Promise<DocumentListResponse>;
}

export async function fetchDocumentsOverview(): Promise<DocumentWorkspaceOverview> {
  const response = await fetch(`${getApiBaseUrl()}/documents/overview`, {
    credentials: 'include',
    cache: 'no-store',
  });
  if (response.status === 403) throw new Error('permission_denied');
  if (!response.ok) throw new Error('Failed to load overview');
  return response.json() as Promise<DocumentWorkspaceOverview>;
}

export async function exportDocumentsMetadata(filters: DocumentFilters = {}): Promise<{
  filename: string;
  csv: string;
  row_count: number;
}> {
  const response = await fetch(`${getApiBaseUrl()}/documents/export${buildQuery(filters)}`, {
    credentials: 'include',
    cache: 'no-store',
  });
  if (response.status === 403) throw new Error('permission_denied');
  if (!response.ok) throw new Error('Export failed');
  return response.json() as Promise<{ filename: string; csv: string; row_count: number }>;
}

export async function fetchDocumentsByEntity(
  entityType: string,
  entityId: string,
  options: { includeHidden?: boolean; pageSize?: number } = {},
): Promise<DocumentListResponse> {
  const search = new URLSearchParams();
  if (options.includeHidden) search.set('include_hidden', 'true');
  search.set('page_size', String(options.pageSize ?? 100));
  const query = search.toString();
  const response = await fetch(
    `${getApiBaseUrl()}/documents/by-entity/${entityType}/${entityId}${query ? `?${query}` : ''}`,
    { credentials: 'include', cache: 'no-store' },
  );
  if (!response.ok) throw new Error('Failed to load entity documents');
  return response.json() as Promise<DocumentListResponse>;
}

export async function fetchDocument(id: string): Promise<Document> {
  const response = await fetch(`${getApiBaseUrl()}/documents/${id}`, {
    credentials: 'include',
    cache: 'no-store',
  });
  if (!response.ok) throw new Error('Document not found');
  return response.json() as Promise<Document>;
}

export async function updateDocument(id: string, payload: DocumentUpdatePayload): Promise<Document> {
  const response = await fetch(`${getApiBaseUrl()}/documents/${id}`, {
    method: 'PATCH',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error('Update failed');
  return response.json() as Promise<Document>;
}

export async function linkDocument(
  id: string,
  entityType: string,
  entityId: string,
  relationshipType?: string,
): Promise<DocumentLink> {
  const response = await fetch(`${getApiBaseUrl()}/documents/${id}/links`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      entity_type: entityType,
      entity_id: entityId,
      relationship_type: relationshipType ?? null,
    }),
  });
  if (!response.ok) throw new Error('Link failed');
  return response.json() as Promise<DocumentLink>;
}

export async function unlinkDocument(id: string, linkId: string): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/documents/${id}/links/${linkId}`, {
    method: 'DELETE',
    credentials: 'include',
  });
  if (!response.ok) throw new Error('Unlink failed');
}

export async function uploadDocuments(
  files: File[],
  meta: DocumentUploadMeta = {},
): Promise<DocumentUploadResult[]> {
  const form = new FormData();
  for (const file of files) {
    form.append('files', file);
  }
  if (meta.title) form.append('title', meta.title);
  if (meta.document_type) form.append('document_type', meta.document_type);
  if (meta.category) form.append('category', meta.category);
  if (meta.folder) form.append('folder', meta.folder);
  if (meta.visibility) form.append('visibility', meta.visibility);
  if (meta.project_id) form.append('project_id', meta.project_id);
  if (meta.investor_id) form.append('investor_id', meta.investor_id);
  if (meta.lead_id) form.append('lead_id', meta.lead_id);
  if (meta.transaction_id) form.append('transaction_id', meta.transaction_id);
  if (meta.company_id) form.append('company_id', meta.company_id);
  if (meta.confidentiality_level) form.append('confidentiality_level', meta.confidentiality_level);
  if (meta.document_date) form.append('document_date', meta.document_date);
  if (meta.expiration_date) form.append('expiration_date', meta.expiration_date);
  if (meta.tags) form.append('tags', meta.tags);
  if (meta.description) form.append('description', meta.description);
  if (meta.notes) form.append('notes', meta.notes);

  const response = await fetch(`${getApiBaseUrl()}/documents/upload`, {
    method: 'POST',
    credentials: 'include',
    body: form,
  });
  if (!response.ok) throw new Error('Upload failed');
  const payload = (await response.json()) as { results: DocumentUploadResult[] };
  return payload.results;
}

export function documentDownloadUrl(id: string): string {
  return `${getApiBaseUrl()}/documents/${id}/download`;
}

export function documentPreviewUrl(id: string): string {
  return `${getApiBaseUrl()}/documents/${id}/preview`;
}

export async function archiveDocument(id: string): Promise<Document> {
  const response = await fetch(`${getApiBaseUrl()}/documents/${id}/archive`, {
    method: 'POST',
    credentials: 'include',
  });
  if (!response.ok) throw new Error('Archive failed');
  return response.json() as Promise<Document>;
}

export async function restoreDocument(id: string): Promise<Document> {
  const response = await fetch(`${getApiBaseUrl()}/documents/${id}/restore`, {
    method: 'POST',
    credentials: 'include',
  });
  if (!response.ok) throw new Error('Restore failed');
  return response.json() as Promise<Document>;
}

export async function fetchDocumentVersions(id: string): Promise<{
  current_version: number;
  items: DocumentVersion[];
}> {
  const response = await fetch(`${getApiBaseUrl()}/documents/${id}/versions`, {
    credentials: 'include',
    cache: 'no-store',
  });
  if (!response.ok) throw new Error('Failed to load versions');
  return response.json() as Promise<{ current_version: number; items: DocumentVersion[] }>;
}

export async function restoreDocumentVersion(
  documentId: string,
  versionId: string,
): Promise<Document> {
  const response = await fetch(
    `${getApiBaseUrl()}/documents/${documentId}/versions/${versionId}/restore`,
    {
      method: 'POST',
      credentials: 'include',
    },
  );
  if (!response.ok) throw new Error('Version restore failed');
  return response.json() as Promise<Document>;
}

export async function uploadDocumentVersion(
  documentId: string,
  file: File,
  versionNotes?: string,
): Promise<Document> {
  const form = new FormData();
  form.append('file', file);
  if (versionNotes) form.append('version_notes', versionNotes);
  const response = await fetch(`${getApiBaseUrl()}/documents/${documentId}/versions`, {
    method: 'POST',
    credentials: 'include',
    body: form,
  });
  if (!response.ok) throw new Error('Version upload failed');
  return response.json() as Promise<Document>;
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatDocumentDate(value: string | null, locale: string): string {
  if (!value) return '—';
  const trimmed = value.trim();
  const date = /^\d{4}-\d{2}-\d{2}$/.test(trimmed)
    ? new Date(`${trimmed}T12:00:00.000Z`)
    : new Date(trimmed);
  return new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeZone: 'UTC' }).format(date);
}

export function downloadCsvFile(filename: string, csv: string): void {
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
