import { apiFetch, getApiBaseUrl } from '@/lib/api/client';

import type {
  CrmContactDetail,
  CrmContactListResponse,
  CrmContactSummary,
  CrmContactType,
  CrmLifecycleStage,
  CrmContactPriority,
  CrmContactStatus,
} from '@/workspaces/crm/types';

export type ContactListParams = {
  search?: string;
  contact_type?: CrmContactType;
  contact_types?: CrmContactType[];
  lifecycle_stage?: CrmLifecycleStage;
  priority?: CrmContactPriority;
  status?: CrmContactStatus;
  source_group?: 'bitrix' | 'other';
  role_group?: 'agent' | 'other';
  category?: 'customer' | 'agent' | 'agreement';
  junk_reason?: string;
  agreement_project?: string;
  bitrix_list?: 'current_junk';
  owner_user_id?: string;
  company_id?: string;
  include_archived?: boolean;
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
};

export type ContactInput = {
  contact_type: CrmContactType;
  contact_types?: CrmContactType[];
  record_kind: 'person' | 'organization';
  display_name: string;
  first_name?: string;
  last_name?: string;
  organization_name?: string | null;
  job_title?: string | null;
  department?: string;
  primary_email?: string | null;
  primary_phone?: string | null;
  linkedin_url?: string;
  whatsapp?: string;
  website?: string;
  lifecycle_stage?: CrmLifecycleStage;
  relationship_status?: string;
  relationship_strength?: string;
  priority?: CrmContactPriority;
  source?: string;
  tags?: string[];
  status?: CrmContactStatus;
  owner_user_id?: string;
  company_id?: string;
  lead_id?: string;
  investor_id?: string;
  notes?: string;
  is_favorite?: boolean;
  is_pinned?: boolean;
  last_contact_at?: string;
  next_follow_up_at?: string | null;
  junk_reason?: string | null;
  secondary_emails?: string[] | null;
  secondary_phones?: string[] | null;
  address_line1?: string | null;
  city?: string | null;
  state_province?: string | null;
  source?: string | null;
  investment_profile?: Record<string, unknown>;
  buyer_profile?: Record<string, unknown>;
  broker_profile?: Record<string, unknown>;
  vendor_profile?: Record<string, unknown>;
  compliance_data?: Record<string, unknown>;
  communication_prefs?: Record<string, unknown>;
};

export type DuplicateMatch = {
  contact_id: string;
  display_name: string;
  match_reason: string;
  match_score: number;
};

export type SavedView = {
  id: string;
  name: string;
  owner_user_id: string;
  is_shared: boolean;
  is_default: boolean;
  filters_json: Record<string, unknown> | null;
  sort_by: string | null;
  sort_dir: 'asc' | 'desc' | null;
  columns_json: string[] | null;
  density: string | null;
  created_at: string;
  updated_at: string;
};

export type ImportResult = {
  created: number;
  updated: number;
  skipped: number;
  errors: string[];
};

function buildSearchParams(params: ContactListParams): URLSearchParams {
  const search = new URLSearchParams();
  search.set('page', String(params.page ?? 1));
  search.set('page_size', String(params.page_size ?? 25));
  if (params.search) search.set('search', params.search);
  if (params.contact_type) search.set('contact_type', params.contact_type);
  if (params.contact_types) {
    for (const type of params.contact_types) {
      search.append('contact_types', type);
    }
  }
  if (params.lifecycle_stage) search.set('lifecycle_stage', params.lifecycle_stage);
  if (params.priority) search.set('priority', params.priority);
  if (params.status) search.set('status', params.status);
  if (params.source_group) search.set('source_group', params.source_group);
  if (params.role_group) search.set('role_group', params.role_group);
  if (params.category) search.set('category', params.category);
  if (params.junk_reason) search.set('junk_reason', params.junk_reason);
  if (params.agreement_project) search.set('agreement_project', params.agreement_project);
  if (params.bitrix_list) search.set('bitrix_list', params.bitrix_list);
  if (params.owner_user_id) search.set('owner_user_id', params.owner_user_id);
  if (params.company_id) search.set('company_id', params.company_id);
  if (params.include_archived) search.set('include_archived', 'true');
  if (params.sort_by) search.set('sort_by', params.sort_by);
  if (params.sort_dir) search.set('sort_dir', params.sort_dir);
  return search;
}

export async function fetchContacts(params: ContactListParams = {}): Promise<CrmContactListResponse> {
  return apiFetch<CrmContactListResponse>(`/crm/contacts?${buildSearchParams(params).toString()}`);
}

export async function fetchContact(id: string): Promise<CrmContactDetail> {
  return apiFetch<CrmContactDetail>(`/crm/contacts/${id}`);
}

export async function createContact(payload: ContactInput): Promise<{ contact: CrmContactDetail }> {
  return apiFetch('/crm/contacts', { method: 'POST', body: JSON.stringify(payload) });
}

export async function updateContact(
  id: string,
  payload: Partial<ContactInput>,
): Promise<{ contact: CrmContactDetail }> {
  return apiFetch(`/crm/contacts/${id}`, { method: 'PATCH', body: JSON.stringify(payload) });
}

export async function setCrmDocumentVisibility(payload: {
  document_id: string;
  entity_type: string;
  entity_id: string;
  hidden: boolean;
}): Promise<{ id: string; hidden_from_view?: boolean }> {
  return apiFetch('/crm/document-visibility', { method: 'POST', body: JSON.stringify(payload) });
}

export async function archiveContact(id: string): Promise<{ contact: CrmContactDetail }> {
  return apiFetch(`/crm/contacts/${id}/archive`, { method: 'POST' });
}

export async function restoreContact(id: string): Promise<{ contact: CrmContactDetail }> {
  return apiFetch(`/crm/contacts/${id}/restore`, { method: 'POST' });
}

export async function deleteContact(id: string): Promise<void> {
  await apiFetch(`/crm/contacts/${id}`, { method: 'DELETE' });
}

export async function checkDuplicates(payload: {
  primary_email?: string;
  primary_phone?: string;
  display_name?: string;
  organization_name?: string;
  linkedin_url?: string;
  whatsapp?: string;
  exclude_contact_id?: string;
}): Promise<{ matches: DuplicateMatch[] }> {
  return apiFetch('/crm/contacts/check-duplicates', { method: 'POST', body: JSON.stringify(payload) });
}

export async function mergeContacts(
  survivorId: string,
  mergedId: string,
): Promise<{ contact: CrmContactDetail }> {
  return apiFetch('/crm/contacts/merge', {
    method: 'POST',
    body: JSON.stringify({ survivor_contact_id: survivorId, merged_contact_id: mergedId }),
  });
}

export async function bulkUpdateContacts(payload: {
  contact_ids: string[];
  owner_user_id?: string;
  lifecycle_stage?: CrmLifecycleStage;
  priority?: CrmContactPriority;
  tags?: string[];
  archive?: boolean;
}): Promise<{ updated: number }> {
  return apiFetch('/crm/contacts/bulk-update', { method: 'POST', body: JSON.stringify(payload) });
}

export async function importContacts(payload: {
  mode: 'create' | 'update' | 'skip' | 'merge';
  rows: Array<{
    display_name: string;
    contact_type?: CrmContactType;
    primary_email?: string;
    primary_phone?: string;
    organization_name?: string;
    tags?: string[];
  }>;
}): Promise<ImportResult> {
  return apiFetch('/crm/contacts/import', { method: 'POST', body: JSON.stringify(payload) });
}

export async function exportContactsCsv(): Promise<Blob> {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/crm/contacts/export`,
    { credentials: 'include' },
  );
  if (!response.ok) throw new Error('Export failed');
  return response.blob();
}

export type BitrixVerificationSummary = {
  total_contacts: number;
  bitrix_contacts: number;
  non_bitrix_contacts: number;
  active_bitrix: number;
  archived_bitrix: number;
  bitrix_with_phone: number;
  bitrix_with_email: number;
  bitrix_with_external_id: number;
  imported_historical_comments: number;
  imported_agents: number;
  imported_agreements: number;
  agreements_by_project: Record<string, number>;
};

export async function fetchBitrixVerificationSummary(): Promise<BitrixVerificationSummary> {
  return apiFetch<BitrixVerificationSummary>('/crm/contacts/bitrix-verification-summary');
}

export async function fetchJunkReasons(): Promise<{ items: Array<{ reason: string; count: number }>; total: number }> {
  return apiFetch('/crm/contacts/junk-reasons');
}

export async function assignContactOwner(
  id: string,
  ownerUserId: string,
): Promise<{ contact: CrmContactDetail }> {
  return apiFetch(`/crm/contacts/${id}/assign-owner`, {
    method: 'POST',
    body: JSON.stringify({ owner_user_id: ownerUserId }),
  });
}

export async function changeContactStatus(
  id: string,
  payload: { status: CrmContactStatus; junk_reason?: string; next_follow_up_at?: string },
): Promise<{ contact: CrmContactDetail }> {
  return apiFetch(`/crm/contacts/${id}/status`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export type ContactTimelineEntry = {
  id: string;
  source: string;
  activity_type: string;
  title: string;
  summary: string | null;
  status: string | null;
  actor_name: string | null;
  created_at: string;
  is_system_event: boolean;
  imported_historical_comment?: boolean;
  metadata?: Record<string, unknown> | null;
  project_contexts?: string[];
  project_assignment?: string | null;
};

export async function fetchContactTimeline(
  id: string,
): Promise<{ items: ContactTimelineEntry[] }> {
  return apiFetch(`/crm/contacts/${id}/timeline`);
}

export async function exportBitrixVerificationCsv(): Promise<Blob> {
  const response = await fetch(
    `${getApiBaseUrl()}/crm/contacts/export/bitrix-verification`,
    { credentials: 'include' },
  );
  if (!response.ok) throw new Error('Bitrix verification export failed');
  return response.blob();
}

export async function fetchSavedViews(): Promise<SavedView[]> {
  return apiFetch<SavedView[]>('/crm/contacts/saved-views');
}

export async function createSavedView(payload: {
  name: string;
  is_shared?: boolean;
  is_default?: boolean;
  filters_json?: Record<string, unknown>;
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
  columns_json?: string[];
  density?: string;
}): Promise<SavedView> {
  return apiFetch('/crm/contacts/saved-views', { method: 'POST', body: JSON.stringify(payload) });
}

export async function deleteSavedView(id: string): Promise<void> {
  await apiFetch(`/crm/contacts/saved-views/${id}`, { method: 'DELETE' });
}

export type { CrmContactSummary, CrmContactDetail };
