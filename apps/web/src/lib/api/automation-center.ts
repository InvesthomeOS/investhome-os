import { apiFetch } from '@/lib/api/client';

export type WorkflowCategory =
  | 'crm'
  | 'marketing'
  | 'investor'
  | 'finance'
  | 'projects'
  | 'website'
  | 'ai'
  | 'notifications'
  | 'administration';

export type AutomationWorkflowSummary = {
  id: string;
  name: string;
  category: WorkflowCategory;
  source: 'marketing_automation' | 'arq_cron' | 'catalog_placeholder';
  status: string;
  trigger: string | null;
  trigger_label: string | null;
  last_run_at: string | null;
  next_run_at: string | null;
  next_run_label: string | null;
  success_rate: number | null;
  success_rate_available: boolean;
  execution_count: number;
  description: string | null;
  manage_href: string | null;
  is_placeholder: boolean;
};

export type AutomationWorkflowDetail = AutomationWorkflowSummary & {
  timezone: string | null;
  steps: { id: string; type: string; label: string; config: Record<string, unknown> }[];
  dependencies: string[];
  conditions: Record<string, unknown>[];
  trigger_config: Record<string, unknown> | null;
  history: AutomationExecutionItem[];
  logs: { id: string; level: string; message: string; created_at: string | null; retry_count: number }[];
  execution_engine_available: boolean;
  execution_engine_message: string;
  can_retry: boolean;
  can_pause: boolean;
  can_resume: boolean;
};

export type AutomationExecutionItem = {
  id: string;
  workflow_id: string;
  workflow_name: string | null;
  status: string;
  trigger_type: string | null;
  retry_count: number;
  duration_ms: number | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string | null;
  category: WorkflowCategory | null;
};

export type AutomationErrorItem = {
  id: string;
  workflow_id: string;
  workflow_name: string | null;
  time: string | null;
  severity: string;
  message: string;
  retry_count: number;
  can_retry: boolean;
  status: string;
  category: WorkflowCategory | null;
};

export type AutomationScheduleItem = {
  id: string;
  name: string;
  category: WorkflowCategory;
  cadence: string;
  cadence_label: string;
  cron_expression: string | null;
  next_run_label: string | null;
  last_run_at: string | null;
  status: string;
  source: string;
  description: string | null;
};

export type AutomationIntegrationItem = {
  id: string;
  name: string;
  status: string;
  status_label: string;
  configured: boolean;
  feature_flag: string | null;
  env_keys: string[];
  notes: string | null;
  href: string | null;
};

export type AutomationAuditItem = {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  entity_label: string | null;
  description_key: string | null;
  actor_name: string | null;
  created_at: string;
  metadata: Record<string, unknown>;
};

export type SystemHealthSummary = {
  running_count: number;
  failed_count: number;
  queued_count: number;
  completed_count: number;
  average_runtime_ms: number | null;
  queue_size: number | null;
  queue_available: boolean;
  last_execution_at: string | null;
  availability: 'available' | 'degraded' | 'unavailable';
  execution_engine_available: boolean;
  execution_engine_message: string;
  workflow_total: number;
  workflow_active: number;
};

export type QueueHealthResponse = {
  available: boolean;
  redis_connected: boolean;
  queue_size: number | null;
  worker_registered: boolean;
  message: string;
  jobs: { name: string; id: string; cadence_label: string }[];
};

export type AutomationOverview = {
  health: SystemHealthSummary;
  workflow_status: { status: string; count: number }[];
  recent_failures: AutomationErrorItem[];
  recent_executions: AutomationExecutionItem[];
  scheduled_jobs: AutomationScheduleItem[];
  ai_workflows: AutomationWorkflowSummary[];
  integrations: AutomationIntegrationItem[];
  queue_health: QueueHealthResponse;
};

function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue;
    search.set(key, String(value));
  }
  const raw = search.toString();
  return raw ? `?${raw}` : '';
}

export function fetchAutomationOverview() {
  return apiFetch<AutomationOverview>('/automation/overview');
}

export function fetchAutomationWorkflows(params?: {
  page?: number;
  page_size?: number;
  category?: string;
  search?: string;
  include_placeholders?: boolean;
}) {
  return apiFetch<{
    items: AutomationWorkflowSummary[];
    total: number;
    page: number;
    page_size: number;
    pages: number;
    categories: WorkflowCategory[];
  }>(`/automation/workflows${qs(params ?? {})}`);
}

export function fetchAutomationWorkflow(id: string) {
  return apiFetch<AutomationWorkflowDetail>(`/automation/workflows/${encodeURIComponent(id)}`);
}

export function fetchAutomationExecutions(params?: { page?: number; page_size?: number; status?: string }) {
  return apiFetch<{
    items: AutomationExecutionItem[];
    total: number;
    page: number;
    page_size: number;
    pages: number;
    status_counts: Record<string, number>;
  }>(`/automation/executions${qs(params ?? {})}`);
}

export function fetchAutomationErrors(params?: { page?: number; page_size?: number }) {
  return apiFetch<{
    items: AutomationErrorItem[];
    total: number;
    page: number;
    page_size: number;
    pages: number;
  }>(`/automation/errors${qs(params ?? {})}`);
}

export function fetchAutomationSchedules() {
  return apiFetch<{ items: AutomationScheduleItem[]; total: number }>('/automation/schedules');
}

export function fetchAutomationIntegrations() {
  return apiFetch<{ items: AutomationIntegrationItem[]; total: number }>('/automation/integrations');
}

export function fetchAutomationAudit(params?: { page?: number; page_size?: number }) {
  return apiFetch<{
    items: AutomationAuditItem[];
    total: number;
    page: number;
    page_size: number;
    pages: number;
  }>(`/automation/audit${qs(params ?? {})}`);
}

export function retryAutomationError(executionId: string) {
  return apiFetch<{ accepted: boolean; message: string }>(
    `/automation/errors/${encodeURIComponent(executionId)}/retry`,
    { method: 'POST' },
  );
}
