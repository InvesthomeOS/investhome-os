import { getApiBaseUrl } from './client';

export type CompanyDocumentCategory =
  | 'legal'
  | 'hr'
  | 'finance'
  | 'compliance'
  | 'operations'
  | 'marketing'
  | 'it'
  | 'contract'
  | 'policy'
  | 'other';

export type CompanyDocumentStatus =
  | 'draft'
  | 'active'
  | 'pending_approval'
  | 'approved'
  | 'rejected'
  | 'expired'
  | 'archived'
  | 'trash';

export type CompanyDocumentView =
  | 'all'
  | 'recent'
  | 'shared'
  | 'favorites'
  | 'expiring'
  | 'archived'
  | 'trash';

export type CompanyDocumentVersion = {
  id: string;
  version_number: number;
  version_notes: string | null;
  checksum: string;
  file_size: number;
  original_file_name: string;
  uploaded_by_user_id: string | null;
  uploaded_by_name: string | null;
  is_current: boolean;
  created_at: string;
  document_id: string;
};

export type CompanyDocument = {
  id: string;
  document_number: string;
  title: string;
  description: string | null;
  category: CompanyDocumentCategory;
  document_type: string;
  confidentiality_level: string;
  status: CompanyDocumentStatus;
  company_id: string;
  branch_id: string | null;
  department_id: string | null;
  team_id: string | null;
  employee_user_id: string | null;
  folder_id: string | null;
  related_record_type: string | null;
  related_record_id: string | null;
  owner_user_id: string | null;
  document_id: string;
  current_version_number: number;
  tags: string[];
  effective_date: string | null;
  expiration_date: string | null;
  renewal_date: string | null;
  is_favorited: boolean;
  created_by_user_id: string | null;
  created_by_name: string | null;
  owner_name: string | null;
  folder_name: string | null;
  company_name: string | null;
  file_name: string | null;
  file_size: number | null;
  file_extension: string | null;
  mime_type: string | null;
  checksum: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  deleted_at: string | null;
  retention_expires_at: string | null;
  has_legal_hold: boolean;
  versions: CompanyDocumentVersion[];
};

export type DocumentFolder = {
  id: string;
  company_id: string;
  parent_folder_id: string | null;
  name: string;
  slug: string;
  description: string | null;
  is_system: boolean;
  sort_order: number;
  document_count: number;
  children: DocumentFolder[];
};

export type CompanyDocumentListParams = {
  company_id?: string;
  folder_id?: string;
  search?: string;
  category?: CompanyDocumentCategory | '';
  status?: CompanyDocumentStatus | '';
  view?: CompanyDocumentView;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
};

export type CompanyDocumentListResponse = {
  items: CompanyDocument[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type StorageSummary = {
  total_documents: number;
  total_bytes: number;
  by_category: Record<string, number>;
  expiring_soon: number;
  in_trash: number;
  archived: number;
};

function buildQuery(params: Record<string, string | number | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, String(value));
    }
  }
  const q = search.toString();
  return q ? `?${q}` : '';
}

export async function fetchCompanyDocuments(
  params: CompanyDocumentListParams = {},
): Promise<CompanyDocumentListResponse> {
  const view = params.view && params.view !== 'all' ? params.view : undefined;
  const response = await fetch(
    `${getApiBaseUrl()}/company-documents${buildQuery({
      company_id: params.company_id,
      folder_id: params.folder_id,
      search: params.search,
      category: params.category || undefined,
      status: params.status || undefined,
      view,
      page: params.page,
      page_size: params.page_size,
      sort_by: params.sort_by,
      sort_dir: params.sort_dir,
    })}`,
    { credentials: 'include', cache: 'no-store' },
  );
  if (!response.ok) throw new Error('Failed to load company documents');
  return response.json() as Promise<CompanyDocumentListResponse>;
}

export async function fetchCompanyDocument(id: string): Promise<CompanyDocument> {
  const response = await fetch(`${getApiBaseUrl()}/company-documents/${id}`, {
    credentials: 'include',
    cache: 'no-store',
  });
  if (!response.ok) throw new Error('Document not found');
  return response.json() as Promise<CompanyDocument>;
}

export async function fetchDocumentFolders(companyId: string): Promise<{ items: DocumentFolder[]; total: number }> {
  const response = await fetch(`${getApiBaseUrl()}/company-documents/folders?company_id=${companyId}`, {
    credentials: 'include',
    cache: 'no-store',
  });
  if (!response.ok) throw new Error('Failed to load folders');
  return response.json() as Promise<{ items: DocumentFolder[]; total: number }>;
}

export async function fetchStorageSummary(companyId?: string): Promise<StorageSummary> {
  const response = await fetch(
    `${getApiBaseUrl()}/company-documents/storage-summary${buildQuery({ company_id: companyId })}`,
    { credentials: 'include', cache: 'no-store' },
  );
  if (!response.ok) throw new Error('Failed to load storage summary');
  return response.json() as Promise<StorageSummary>;
}

export async function uploadCompanyDocument(
  file: File,
  meta: {
    company_id: string;
    title?: string;
    description?: string;
    category?: CompanyDocumentCategory;
    folder_id?: string;
    confidentiality_level?: string;
    expiration_date?: string;
  },
  onProgress?: (pct: number) => void,
): Promise<CompanyDocument> {
  const form = new FormData();
  form.append('file', file);
  form.append('company_id', meta.company_id);
  if (meta.title) form.append('title', meta.title);
  if (meta.description) form.append('description', meta.description);
  if (meta.category) form.append('category', meta.category);
  if (meta.folder_id) form.append('folder_id', meta.folder_id);
  if (meta.confidentiality_level) form.append('confidentiality_level', meta.confidentiality_level);
  if (meta.expiration_date) form.append('expiration_date', meta.expiration_date);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${getApiBaseUrl()}/company-documents/upload`);
    xhr.withCredentials = true;
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText) as CompanyDocument);
      } else {
        reject(new Error('Upload failed'));
      }
    };
    xhr.onerror = () => reject(new Error('Upload failed'));
    xhr.send(form);
  });
}

export async function bulkUploadCompanyDocuments(
  files: File[],
  companyId: string,
  folderId?: string,
): Promise<CompanyDocument[]> {
  const form = new FormData();
  for (const file of files) form.append('files', file);
  form.append('company_id', companyId);
  if (folderId) form.append('folder_id', folderId);
  const response = await fetch(`${getApiBaseUrl()}/company-documents/bulk-upload`, {
    method: 'POST',
    credentials: 'include',
    body: form,
  });
  if (!response.ok) throw new Error('Bulk upload failed');
  return response.json() as Promise<CompanyDocument[]>;
}

export function getPreviewUrl(id: string): string {
  return `${getApiBaseUrl()}/company-documents/${id}/preview`;
}

export function getDownloadUrl(id: string): string {
  return `${getApiBaseUrl()}/company-documents/${id}/download`;
}

export async function archiveCompanyDocument(id: string): Promise<CompanyDocument> {
  const response = await fetch(`${getApiBaseUrl()}/company-documents/${id}/archive`, {
    method: 'POST',
    credentials: 'include',
  });
  if (!response.ok) throw new Error('Archive failed');
  return response.json() as Promise<CompanyDocument>;
}

export async function restoreCompanyDocument(id: string): Promise<CompanyDocument> {
  const response = await fetch(`${getApiBaseUrl()}/company-documents/${id}/restore`, {
    method: 'POST',
    credentials: 'include',
  });
  if (!response.ok) throw new Error('Restore failed');
  return response.json() as Promise<CompanyDocument>;
}

export async function trashCompanyDocument(id: string): Promise<CompanyDocument> {
  const response = await fetch(`${getApiBaseUrl()}/company-documents/${id}/trash`, {
    method: 'POST',
    credentials: 'include',
  });
  if (!response.ok) throw new Error('Trash failed');
  return response.json() as Promise<CompanyDocument>;
}

export async function toggleFavorite(id: string, favorited: boolean): Promise<CompanyDocument> {
  const response = await fetch(`${getApiBaseUrl()}/company-documents/${id}/favorite`, {
    method: favorited ? 'POST' : 'DELETE',
    credentials: 'include',
  });
  if (!response.ok) throw new Error('Favorite action failed');
  return response.json() as Promise<CompanyDocument>;
}

export async function createShareLink(
  id: string,
  options: { expires_in_hours?: number; password?: string; max_downloads?: number },
): Promise<{ token: string; secure_url: string | null; expires_at: string }> {
  const response = await fetch(`${getApiBaseUrl()}/company-documents/${id}/share`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(options),
  });
  if (!response.ok) throw new Error('Share link creation failed');
  return response.json();
}

export async function bulkAction(
  documentIds: string[],
  action: 'archive' | 'restore' | 'trash' | 'favorite' | 'unfavorite',
): Promise<{ affected: number }> {
  const response = await fetch(`${getApiBaseUrl()}/company-documents/bulk-action`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_ids: documentIds, action }),
  });
  if (!response.ok) throw new Error('Bulk action failed');
  return response.json() as Promise<{ affected: number }>;
}

export function formatFileSize(bytes: number | null | undefined): string {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
