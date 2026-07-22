import { apiFetch } from '@/lib/api/client';

import type {
  CrmCommAnalyticsMetric,
  CrmCommChannel,
  CrmCommDetail,
  CrmCommDirection,
  CrmCommEntityType,
  CrmCommListResponse,
  CrmCommPriority,
  CrmCommProviderStatus,
  CrmCommStatus,
  CrmCommTemplateDetail,
  CrmCommTemplateSummary,
  CrmCommThreadDetail,
  CrmCommThreadListResponse,
  CrmCommVisibility,
} from '@/workspaces/crm/types';

export type ThreadListParams = {
  folder?: string;
  search?: string;
  channel?: CrmCommChannel;
  status?: string;
  owner_id?: string;
  assigned_user_id?: string;
  unread_only?: boolean;
  follow_up_due?: boolean;
  include_archived?: boolean;
  entity_type?: CrmCommEntityType;
  entity_id?: string;
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
};

export type CommunicationListParams = {
  folder?: string;
  search?: string;
  channel?: CrmCommChannel;
  direction?: CrmCommDirection;
  status?: CrmCommStatus;
  thread_id?: string;
  page?: number;
  page_size?: number;
};

export type CommunicationInput = {
  channel: CrmCommChannel;
  direction?: CrmCommDirection;
  status?: CrmCommStatus;
  subject?: string;
  body?: string;
  body_html?: string;
  body_text?: string;
  recipient_entity_type?: CrmCommEntityType;
  recipient_entity_id?: string;
  recipients?: Array<{ email?: string; phone?: string; name?: string; entity_type?: string; entity_id?: string }>;
  cc_recipients?: Array<{ email?: string; name?: string }>;
  bcc_recipients?: Array<{ email?: string; name?: string }>;
  related_entities?: Array<{ entity_type: CrmCommEntityType; entity_id: string; label?: string }>;
  thread_id?: string;
  scheduled_at?: string;
  priority?: CrmCommPriority;
  visibility?: CrmCommVisibility;
  tags?: string[];
  call_duration_seconds?: number;
  call_outcome?: string;
  call_direction?: string;
  meeting_url?: string;
  meeting_start_at?: string;
  meeting_end_at?: string;
  metadata_json?: Record<string, unknown>;
};

export type TemplateInput = {
  name: string;
  template_type: string;
  subject?: string;
  body: string;
  body_html?: string;
  variables?: string[];
  channel?: CrmCommChannel;
  is_shared?: boolean;
  tags?: string[];
};

export type SignatureInput = {
  name: string;
  body_html: string;
  body_text?: string;
  channel?: CrmCommChannel;
  scope?: string;
  is_default?: boolean;
};

export type SequenceInput = {
  name: string;
  description?: string;
  enrollment_type?: string;
  tags?: string[];
  steps?: Array<{
    step_order: number;
    step_type: string;
    template_id?: string;
    wait_days?: number;
    wait_hours?: number;
  }>;
};

export type PreferenceInput = {
  preferred_channel?: CrmCommChannel;
  allowed_channels?: string[];
  blocked_channels?: string[];
  consent_email?: boolean;
  consent_sms?: boolean;
  consent_whatsapp?: boolean;
  consent_phone?: boolean;
  do_not_contact?: boolean;
  do_not_contact_reason?: string;
};

function buildParams(params: Record<string, string | number | boolean | undefined>): URLSearchParams {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '' && value !== false) {
      search.set(key, String(value));
    }
  }
  return search;
}

export async function fetchCommunicationThreads(params: ThreadListParams = {}): Promise<CrmCommThreadListResponse> {
  const q = buildParams({
    folder: params.folder,
    search: params.search,
    channel: params.channel,
    status: params.status,
    owner_id: params.owner_id,
    assigned_user_id: params.assigned_user_id,
    unread_only: params.unread_only,
    follow_up_due: params.follow_up_due,
    include_archived: params.include_archived,
    entity_type: params.entity_type,
    entity_id: params.entity_id,
    sort_by: params.sort_by ?? 'last_communication_at',
    sort_dir: params.sort_dir ?? 'desc',
    page: params.page ?? 1,
    page_size: params.page_size ?? 30,
  });
  return apiFetch<CrmCommThreadListResponse>(`/crm/communications/threads?${q.toString()}`);
}

export async function fetchCommunicationThread(threadId: string): Promise<CrmCommThreadDetail> {
  return apiFetch<CrmCommThreadDetail>(`/crm/communications/threads/${threadId}`);
}

export async function fetchCommunications(params: CommunicationListParams = {}): Promise<CrmCommListResponse> {
  const q = buildParams({
    folder: params.folder,
    search: params.search,
    channel: params.channel,
    direction: params.direction,
    status: params.status,
    thread_id: params.thread_id,
    page: params.page ?? 1,
    page_size: params.page_size ?? 30,
  });
  return apiFetch<CrmCommListResponse>(`/crm/communications?${q.toString()}`);
}

export async function fetchCommunication(id: string): Promise<CrmCommDetail> {
  return apiFetch<CrmCommDetail>(`/crm/communications/${id}`);
}

export async function createCommunication(
  payload: CommunicationInput,
): Promise<{ communication: CrmCommDetail; warnings: string[] }> {
  return apiFetch(`/crm/communications`, { method: 'POST', body: JSON.stringify(payload) });
}

export async function updateCommunication(
  id: string,
  payload: Partial<CommunicationInput>,
): Promise<{ communication: CrmCommDetail; warnings: string[] }> {
  return apiFetch(`/crm/communications/${id}`, { method: 'PATCH', body: JSON.stringify(payload) });
}

export async function archiveCommunication(id: string): Promise<void> {
  await apiFetch(`/crm/communications/${id}/archive`, { method: 'POST' });
}

export async function markThreadRead(threadId: string): Promise<void> {
  await apiFetch(`/crm/communications/threads/${threadId}/read`, { method: 'POST' });
}

export async function markThreadUnread(threadId: string): Promise<void> {
  await apiFetch(`/crm/communications/threads/${threadId}/unread`, { method: 'POST' });
}

export async function pinThread(threadId: string, pinned = true): Promise<void> {
  await apiFetch(`/crm/communications/threads/${threadId}/pin?pinned=${pinned}`, { method: 'POST' });
}

export async function archiveThread(threadId: string): Promise<void> {
  await apiFetch(`/crm/communications/threads/${threadId}/archive`, { method: 'POST' });
}

export async function assignThread(
  threadId: string,
  payload: { assigned_user_id?: string; assigned_team_id?: string },
): Promise<void> {
  await apiFetch(`/crm/communications/threads/${threadId}/assign`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function setThreadFollowUp(threadId: string, follow_up_date: string | null): Promise<void> {
  await apiFetch(`/crm/communications/threads/${threadId}/follow-up`, {
    method: 'POST',
    body: JSON.stringify({ follow_up_date }),
  });
}

export async function fetchCallLogs(params: CommunicationListParams = {}): Promise<CrmCommListResponse> {
  const q = buildParams({ page: params.page ?? 1, page_size: params.page_size ?? 30 });
  return apiFetch<CrmCommListResponse>(`/crm/communications/calls/list?${q.toString()}`);
}

export async function fetchMeetings(params: CommunicationListParams = {}): Promise<CrmCommListResponse> {
  const q = buildParams({ page: params.page ?? 1, page_size: params.page_size ?? 30 });
  return apiFetch<CrmCommListResponse>(`/crm/communications/meetings/list?${q.toString()}`);
}

export async function fetchTemplates(params: { search?: string; page?: number; page_size?: number } = {}): Promise<{
  items: CrmCommTemplateSummary[];
  total: number;
  pages: number;
  page: number;
  page_size: number;
}> {
  const q = buildParams({ search: params.search, page: params.page ?? 1, page_size: params.page_size ?? 30 });
  return apiFetch(`/crm/communications/templates/list?${q.toString()}`);
}

export async function createTemplate(payload: TemplateInput): Promise<CrmCommTemplateDetail> {
  return apiFetch(`/crm/communications/templates`, { method: 'POST', body: JSON.stringify(payload) });
}

export async function archiveTemplate(id: string): Promise<void> {
  await apiFetch(`/crm/communications/templates/${id}/archive`, { method: 'POST' });
}

export async function fetchSignatures(): Promise<{ items: Array<{ id: string; name: string; scope: string; is_default: boolean }> }> {
  return apiFetch(`/crm/communications/signatures/list`);
}

export async function createSignature(payload: SignatureInput): Promise<{ id: string; name: string }> {
  return apiFetch(`/crm/communications/signatures`, { method: 'POST', body: JSON.stringify(payload) });
}

export async function fetchSequences(params: { page?: number; page_size?: number } = {}): Promise<{
  items: Array<{ id: string; name: string; step_count: number; is_active: boolean; enrollment_type: string }>;
  total: number;
}> {
  const q = buildParams({ page: params.page ?? 1, page_size: params.page_size ?? 30 });
  return apiFetch(`/crm/communications/sequences/list?${q.toString()}`);
}

export async function createSequence(payload: SequenceInput): Promise<{ id: string; name: string }> {
  return apiFetch(`/crm/communications/sequences`, { method: 'POST', body: JSON.stringify(payload) });
}

export async function fetchCommunicationAnalytics(): Promise<{ metrics: CrmCommAnalyticsMetric[] }> {
  return apiFetch(`/crm/communications/analytics/dashboard`);
}

export async function fetchProviderStatuses(): Promise<{ items: CrmCommProviderStatus[] }> {
  return apiFetch(`/crm/communications/providers/status`);
}

export async function upsertCommunicationPreferences(
  entityType: CrmCommEntityType,
  entityId: string,
  payload: PreferenceInput,
): Promise<Record<string, unknown>> {
  return apiFetch(`/crm/communications/preferences/${entityType}/${entityId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}
