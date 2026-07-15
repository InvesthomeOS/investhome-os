import type { Route } from 'next';

import { apiFetch } from '@/lib/api/client';

export type ActivityAction =
  | 'created'
  | 'viewed'
  | 'updated'
  | 'status_changed'
  | 'archived'
  | 'restored'
  | 'deleted'
  | 'exported'
  | 'approved'
  | 'rejected'
  | 'login'
  | 'logout'
  | 'login_failed'
  | 'role_assigned'
  | 'role_removed'
  | 'permission_changed'
  | 'password_changed'
  | 'invited'
  | 'activated'
  | 'deactivated'
  | 'payment_completed'
  | 'funding_added'
  | 'file_uploaded'
  | 'note_added'
  | 'other';

export type ActivityEntityType =
  | 'user'
  | 'role'
  | 'lead'
  | 'investor'
  | 'project'
  | 'financial_account'
  | 'transaction'
  | 'project_budget'
  | 'funding_commitment'
  | 'payment_obligation'
  | 'document'
  | 'design_project';

export type ActivitySource =
  | 'web'
  | 'api'
  | 'background_job'
  | 'automation'
  | 'import'
  | 'integration'
  | 'ai_service';

export interface ActivityLogEntry {
  id: string;
  event_type: string;
  action: ActivityAction;
  entity_type: ActivityEntityType;
  entity_id: string;
  actor_type: string;
  actor_user_id: string | null;
  actor_name: string | null;
  source: ActivitySource;
  description_key: string;
  metadata: Record<string, unknown> | null;
  changed_fields: string[] | null;
  previous_values: Record<string, unknown> | null;
  new_values: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string | null;
  request_id: string | null;
  is_demo: boolean;
  created_at: string;
  entity_label: string | null;
  link_module: string | null;
}

export interface ActivityListResponse {
  items: ActivityLogEntry[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ActivityFilters {
  search: string;
  entity_type: ActivityEntityType | '';
  action: ActivityAction | '';
  source: ActivitySource | '';
  date_from: string;
  date_to: string;
  sort_order: 'asc' | 'desc';
  page: number;
  page_size: number;
}

export const EMPTY_ACTIVITY_FILTERS: ActivityFilters = {
  search: '',
  entity_type: '',
  action: '',
  source: '',
  date_from: '',
  date_to: '',
  sort_order: 'desc',
  page: 1,
  page_size: 25,
};

function buildQuery(filters: Partial<ActivityFilters>): string {
  const params = new URLSearchParams();
  if (filters.search) params.set('search', filters.search);
  if (filters.entity_type) params.set('entity_type', filters.entity_type);
  if (filters.action) params.set('action', filters.action);
  if (filters.source) params.set('source', filters.source);
  if (filters.date_from) params.set('date_from', `${filters.date_from}T00:00:00Z`);
  if (filters.date_to) params.set('date_to', `${filters.date_to}T23:59:59Z`);
  if (filters.sort_order) params.set('sort_order', filters.sort_order);
  if (filters.page) params.set('page', String(filters.page));
  if (filters.page_size) params.set('page_size', String(filters.page_size));
  const query = params.toString();
  return query ? `?${query}` : '';
}

export async function fetchActivities(filters: ActivityFilters = EMPTY_ACTIVITY_FILTERS) {
  return apiFetch<ActivityListResponse>(`/activity${buildQuery(filters)}`);
}

export async function fetchActivityDetail(activityId: string) {
  return apiFetch<ActivityLogEntry>(`/activity/${activityId}`);
}

export async function fetchEntityActivity(
  entityType: ActivityEntityType,
  entityId: string,
  limit = 20,
) {
  return apiFetch<ActivityListResponse>(
    `/activity/entity/${entityType}/${entityId}?limit=${limit}`,
  );
}

export function activityRecordHref(entry: ActivityLogEntry): Route | null {
  if (!entry.link_module) return null;
  return `/dashboard/${entry.link_module}` as Route;
}

export function formatActivityDate(value: string, locale: string): string {
  const intlLocale = locale === 'tr' ? 'tr-TR' : 'en-US';
  return new Intl.DateTimeFormat(intlLocale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

export function metadataForI18n(metadata: Record<string, unknown> | null | undefined) {
  if (!metadata) return {};
  return Object.fromEntries(
    Object.entries(metadata).map(([key, value]) => [key, value == null ? '' : String(value)]),
  ) as Record<string, string>;
}
