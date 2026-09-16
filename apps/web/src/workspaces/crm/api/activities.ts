import { apiFetch } from '@/lib/api/client';

import type {
  ActivityInput,
  ActivityListParams,
  CrmActivityDashboardWidgets,
  CrmActivityDetail,
  CrmActivityListResponse,
  CrmCalendarResponse,
  CrmTimelineResponse,
  FollowUpInput,
} from '@/workspaces/crm/types/activities';

function buildSearchParams(params: Record<string, string | number | boolean | undefined>): URLSearchParams {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === '') continue;
    if (Array.isArray(value)) {
      search.set(key, value.join(','));
    } else {
      search.set(key, String(value));
    }
  }
  return search;
}

function activityListParams(params: ActivityListParams): URLSearchParams {
  return buildSearchParams({
    ...params,
    activity_types: params.activity_types?.join(','),
    tags: params.tags?.join(','),
    has_attachments: params.has_attachments ? 'true' : undefined,
    completed: params.completed ? 'true' : undefined,
    pending: params.pending ? 'true' : undefined,
    include_archived: params.include_archived ? 'true' : undefined,
    page: params.page ?? 1,
    page_size: params.page_size ?? 25,
  });
}

export async function fetchTimeline(
  params: ActivityListParams = {},
): Promise<CrmTimelineResponse> {
  const search = activityListParams({ ...params, page_size: params.page_size ?? 30 });
  return apiFetch<CrmTimelineResponse>(`/crm/timeline?${search.toString()}`);
}

export async function fetchActivities(params: ActivityListParams = {}): Promise<CrmActivityListResponse> {
  return apiFetch<CrmActivityListResponse>(`/crm/activities?${activityListParams(params).toString()}`);
}

export async function fetchActivity(id: string): Promise<CrmActivityDetail> {
  return apiFetch<CrmActivityDetail>(`/crm/activities/${id}`);
}

export async function createActivity(payload: ActivityInput): Promise<{ activity: CrmActivityDetail }> {
  return apiFetch('/crm/activities', { method: 'POST', body: JSON.stringify(payload) });
}

export async function updateActivity(
  id: string,
  payload: Partial<ActivityInput> & { is_pinned?: boolean; is_favorite?: boolean },
): Promise<{ activity: CrmActivityDetail }> {
  return apiFetch(`/crm/activities/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
}

export async function archiveActivity(id: string): Promise<{ activity: CrmActivityDetail }> {
  return apiFetch(`/crm/activities/${id}/archive`, { method: 'POST' });
}

export async function restoreActivity(id: string): Promise<{ activity: CrmActivityDetail }> {
  return apiFetch(`/crm/activities/${id}/restore`, { method: 'POST' });
}

export async function deleteActivity(id: string): Promise<void> {
  await apiFetch(`/crm/activities/${id}`, { method: 'DELETE' });
}

export async function duplicateActivity(id: string): Promise<{ activity: CrmActivityDetail }> {
  return apiFetch(`/crm/activities/${id}/duplicate`, { method: 'POST' });
}

export async function bulkUpdateActivities(payload: {
  activity_ids: string[];
  assigned_user_id?: string;
  status?: string;
  priority?: string;
  archive?: boolean;
  restore?: boolean;
}): Promise<{ updated: number }> {
  return apiFetch('/crm/activities/bulk-update', { method: 'POST', body: JSON.stringify(payload) });
}

export async function addActivityComment(
  id: string,
  payload: { body: string; parent_id?: string; mentions?: string[] },
): Promise<{ activity: CrmActivityDetail }> {
  return apiFetch(`/crm/activities/${id}/comments`, { method: 'POST', body: JSON.stringify(payload) });
}

export async function fetchTasks(params: ActivityListParams & { my_tasks?: boolean; team_tasks?: boolean } = {}): Promise<CrmActivityListResponse> {
  const search = buildSearchParams({
    page: params.page ?? 1,
    page_size: params.page_size ?? 100,
    assigned_user_id: params.assigned_user_id,
    my_tasks: params.my_tasks ? 'true' : undefined,
    team_tasks: params.team_tasks ? 'true' : undefined,
    status: params.status,
    entity_id: params.entity_id,
    search: params.search,
  });
  return apiFetch<CrmActivityListResponse>(`/crm/tasks?${search.toString()}`);
}

export async function createTask(payload: ActivityInput): Promise<{ activity: CrmActivityDetail }> {
  return apiFetch('/crm/tasks', { method: 'POST', body: JSON.stringify({ ...payload, activity_type: 'task' }) });
}

export async function completeTask(id: string): Promise<{ activity: CrmActivityDetail }> {
  return apiFetch(`/crm/tasks/${id}/complete`, { method: 'POST' });
}

export async function reopenTask(id: string): Promise<{ activity: CrmActivityDetail }> {
  return updateActivity(id, { task_status: 'not_started', status: 'planned' });
}

export async function fetchNotes(params: ActivityListParams = {}): Promise<CrmActivityListResponse> {
  const search = activityListParams(params);
  return apiFetch<CrmActivityListResponse>(`/crm/notes?${search.toString()}`);
}

export async function createNote(payload: ActivityInput): Promise<{ activity: CrmActivityDetail }> {
  return apiFetch('/crm/notes', { method: 'POST', body: JSON.stringify({ ...payload, activity_type: 'note' }) });
}

export async function fetchMeetings(params: ActivityListParams = {}): Promise<CrmActivityListResponse> {
  return apiFetch<CrmActivityListResponse>(`/crm/meetings?${activityListParams(params).toString()}`);
}

export async function createMeeting(payload: ActivityInput): Promise<{ activity: CrmActivityDetail }> {
  return apiFetch('/crm/meetings', { method: 'POST', body: JSON.stringify(payload) });
}

export async function fetchFollowUps(params: ActivityListParams & { reason?: string; pending?: boolean } = {}): Promise<CrmActivityListResponse> {
  const search = buildSearchParams({
    entity_type: params.entity_type,
    entity_id: params.entity_id,
    reason: params.reason,
    pending: params.pending === false ? 'false' : 'true',
    page: params.page ?? 1,
    page_size: params.page_size ?? 25,
  });
  return apiFetch<CrmActivityListResponse>(`/crm/follow-ups?${search.toString()}`);
}

export async function createFollowUp(payload: FollowUpInput): Promise<{ activity: CrmActivityDetail }> {
  return apiFetch('/crm/follow-ups', { method: 'POST', body: JSON.stringify(payload) });
}

export async function completeFollowUp(id: string): Promise<{ activity: CrmActivityDetail }> {
  return apiFetch(`/crm/follow-ups/${id}/complete`, { method: 'POST' });
}

export async function fetchCalendar(params: {
  start: string;
  end: string;
  assigned_user_id?: string;
}): Promise<CrmCalendarResponse> {
  const search = buildSearchParams(params);
  return apiFetch<CrmCalendarResponse>(`/crm/calendar?${search.toString()}`);
}

export async function fetchActivityWidgets(): Promise<CrmActivityDashboardWidgets> {
  return apiFetch<CrmActivityDashboardWidgets>('/crm/activities/widgets');
}

export async function createSavedActivityFilter(payload: {
  name: string;
  filters_json: Record<string, unknown>;
  filter_logic?: 'and' | 'or';
  is_shared?: boolean;
}): Promise<{ id: string; name: string }> {
  return apiFetch('/crm/activities/saved-filters', { method: 'POST', body: JSON.stringify(payload) });
}

export async function fetchSavedActivityFilters(): Promise<
  Array<{ id: string; name: string; filters_json: Record<string, unknown>; filter_logic: string; is_shared: boolean }>
> {
  return apiFetch('/crm/activities/saved-filters');
}
