import { apiFetch } from '@/lib/api/client';

export type AutomationSummary = {
  id: string;
  name: string;
  code: string | null;
  description: string | null;
  status: string;
  version: number;
  is_journey: boolean;
  owner_user_id: string | null;
  created_by_user_id: string | null;
  team_id: string | null;
  activated_at: string | null;
  last_run_at: string | null;
  execution_count: number;
  execution_engine_available: boolean;
  created_at: string;
  updated_at: string;
};

export type AutomationDetail = AutomationSummary & {
  trigger: Record<string, unknown> | null;
  conditions: Record<string, unknown>[] | null;
  actions: Record<string, unknown>[] | null;
  journey_graph: Record<string, unknown> | null;
  timezone: string;
};

export type AutomationListResponse = {
  items: AutomationSummary[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type AutomationExecution = {
  id: string;
  workflow_id: string;
  workflow_version: number;
  status: string;
  trigger_type: string | null;
  error_message: string | null;
  duration_ms: number | null;
  retry_count: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
};

export type AutomationMetrics = {
  workflow_id: string;
  status: string;
  execution_count: number;
  completed_count: number;
  failed_count: number;
  skipped_count: number;
  not_connected_count: number;
  average_duration_ms: number | null;
  last_run_at: string | null;
  activated_at: string | null;
  execution_engine_available: boolean;
  execution_engine_message: string;
};

export type AutomationLogEntry = {
  id: string;
  execution_id: string;
  level: 'info' | 'warning' | 'error';
  message: string;
  trigger_type: string | null;
  actions_attempted: number;
  actions_completed: number;
  failure_reason: string | null;
  retry_count: number;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  created_at: string;
};

export type AutomationListParams = {
  page?: number;
  page_size?: number;
  search?: string;
  status?: string;
  is_journey?: boolean;
  include_archived?: boolean;
};

export type AutomationCreatePayload = {
  name: string;
  description?: string;
  trigger?: { type: string; config?: Record<string, unknown> };
  conditions?: { field: string; operator: string; value?: unknown }[];
  actions?: { type: string; config?: Record<string, unknown> }[];
  is_journey?: boolean;
};

function buildQuery(params: AutomationListParams = {}) {
  const query = new URLSearchParams();
  if (params.page) query.set('page', String(params.page));
  if (params.page_size) query.set('page_size', String(params.page_size));
  if (params.search) query.set('search', params.search);
  if (params.status) query.set('status', params.status);
  if (params.is_journey != null) query.set('is_journey', String(params.is_journey));
  if (params.include_archived) query.set('include_archived', 'true');
  const qs = query.toString();
  return qs ? `?${qs}` : '';
}

export async function fetchAutomations(params: AutomationListParams = {}) {
  return apiFetch<AutomationListResponse>(`/marketing/automations${buildQuery(params)}`);
}

export async function fetchAutomation(automationId: string) {
  return apiFetch<AutomationDetail>(`/marketing/automations/${automationId}`);
}

export async function createAutomation(payload: AutomationCreatePayload) {
  return apiFetch<AutomationDetail>('/marketing/automations', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateAutomation(automationId: string, payload: Partial<AutomationCreatePayload> & { change_summary?: string }) {
  return apiFetch<AutomationDetail>(`/marketing/automations/${automationId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function deleteAutomation(automationId: string) {
  return apiFetch<void>(`/marketing/automations/${automationId}`, { method: 'DELETE' });
}

export async function activateAutomation(automationId: string) {
  return apiFetch<AutomationDetail>(`/marketing/automations/${automationId}/activate`, { method: 'POST' });
}

export async function pauseAutomation(automationId: string) {
  return apiFetch<AutomationDetail>(`/marketing/automations/${automationId}/pause`, { method: 'POST' });
}

export async function archiveAutomation(automationId: string) {
  return apiFetch<AutomationDetail>(`/marketing/automations/${automationId}/archive`, { method: 'POST' });
}

export async function duplicateAutomation(automationId: string) {
  return apiFetch<AutomationDetail>(`/marketing/automations/${automationId}/duplicate`, { method: 'POST' });
}

export async function fetchAutomationExecutions(automationId: string, page = 1) {
  return apiFetch<{ items: AutomationExecution[]; total: number; pages: number }>(
    `/marketing/automations/${automationId}/executions?page=${page}&page_size=25`,
  );
}

export async function fetchAutomationLogs(automationId: string, page = 1) {
  return apiFetch<{ items: AutomationLogEntry[]; total: number; pages: number }>(
    `/marketing/automations/${automationId}/logs?page=${page}&page_size=25`,
  );
}

export async function fetchAutomationMetrics(automationId: string) {
  return apiFetch<AutomationMetrics>(`/marketing/automations/${automationId}/metrics`);
}
