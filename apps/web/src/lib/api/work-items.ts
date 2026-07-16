import { apiFetch } from '@/lib/api/client';

export const WORK_ITEM_TYPES = [
  'task',
  'call',
  'meeting',
  'follow_up',
  'site_visit',
  'document_request',
  'proposal_follow_up',
  'reservation_follow_up',
  'deposit_follow_up',
  'contract_follow_up',
  'closing_follow_up',
  'other',
] as const;

export const WORK_ITEM_STATUSES = [
  'open',
  'in_progress',
  'waiting',
  'blocked',
  'completed',
  'cancelled',
  'overdue',
  'archived',
] as const;

export const WORK_ITEM_PRIORITIES = ['low', 'medium', 'high', 'urgent'] as const;

export type WorkItemType = (typeof WORK_ITEM_TYPES)[number];
export type WorkItemStatus = (typeof WORK_ITEM_STATUSES)[number];
export type WorkItemPriority = (typeof WORK_ITEM_PRIORITIES)[number];

export type WorkViewName =
  | 'today'
  | 'overdue'
  | 'upcoming'
  | 'meetings'
  | 'calls'
  | 'follow_ups'
  | 'waiting'
  | 'blocked'
  | 'completed'
  | 'my_work'
  | 'team_work';

export interface MeetingRecord {
  id: string;
  work_item_id: string;
  meeting_type: string;
  location: string | null;
  meeting_url: string | null;
  agenda: string | null;
  notes: string | null;
  outcome: string | null;
  decision_summary: string | null;
  next_steps: string | null;
  started_at: string | null;
  ended_at: string | null;
}

export interface FollowUpRecord {
  id: string;
  work_item_id: string;
  follow_up_type: WorkItemType;
  contact_method: string;
  outcome: string | null;
  response_status: string;
  next_follow_up_at: string | null;
  notes: string | null;
}

export interface WorkItem {
  id: string;
  title: string;
  description: string | null;
  work_item_type: WorkItemType;
  status: WorkItemStatus;
  effective_status: WorkItemStatus | null;
  priority: WorkItemPriority;
  assigned_user_id: string | null;
  created_by_user_id: string | null;
  due_at: string | null;
  start_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  reminder_at: string | null;
  lead_id: string | null;
  opportunity_id: string | null;
  party_id: string | null;
  project_id: string | null;
  inventory_asset_id: string | null;
  proposal_id: string | null;
  outcome: string | null;
  is_private: boolean;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
  meeting: MeetingRecord | null;
  follow_up: FollowUpRecord | null;
}

export interface WorkItemListResponse {
  items: WorkItem[];
  total: number;
  offset: number;
  limit: number;
}

export interface WorkDashboardKpis {
  today_count: number;
  overdue_count: number;
  meetings_today_count: number;
  blocked_count: number;
  waiting_count: number;
  my_work_count: number;
  no_next_action_count: number;
}

export interface CalendarEvent {
  id: string;
  title: string;
  work_item_type: WorkItemType;
  status: WorkItemStatus;
  start_at: string | null;
  due_at: string | null;
  assigned_user_id: string | null;
  is_private: boolean;
}

export interface WorkItemInput {
  title: string;
  description?: string | null;
  work_item_type?: WorkItemType;
  priority?: WorkItemPriority;
  assigned_user_id?: string | null;
  due_at?: string | null;
  start_at?: string | null;
  lead_id?: string | null;
  opportunity_id?: string | null;
  party_id?: string | null;
  proposal_id?: string | null;
  is_private?: boolean;
}

export async function fetchWorkDashboardKpis(): Promise<WorkDashboardKpis> {
  return apiFetch<WorkDashboardKpis>('/sales/work/dashboard/kpis');
}

export async function fetchWorkView(view: WorkViewName, limit = 100): Promise<WorkItemListResponse> {
  return apiFetch<WorkItemListResponse>(`/sales/work/views/${view}?limit=${limit}`);
}

export async function fetchWorkItems(params: Record<string, string | number | boolean | undefined> = {}): Promise<WorkItemListResponse> {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') search.set(key, String(value));
  });
  const qs = search.toString();
  return apiFetch<WorkItemListResponse>(`/sales/work/items${qs ? `?${qs}` : ''}`);
}

export async function fetchWorkItem(id: string): Promise<WorkItem> {
  return apiFetch<WorkItem>(`/sales/work/items/${id}`);
}

export async function createWorkItem(payload: WorkItemInput): Promise<WorkItem> {
  return apiFetch<WorkItem>('/sales/work/items', { method: 'POST', body: JSON.stringify(payload) });
}

export async function updateWorkItem(id: string, payload: Partial<WorkItemInput>): Promise<WorkItem> {
  return apiFetch<WorkItem>(`/sales/work/items/${id}`, { method: 'PATCH', body: JSON.stringify(payload) });
}

export async function completeWorkItem(id: string, payload: { outcome?: string; next_follow_up?: Record<string, unknown> } = {}): Promise<WorkItem> {
  return apiFetch<WorkItem>(`/sales/work/items/${id}/complete`, { method: 'POST', body: JSON.stringify(payload) });
}

export async function cancelWorkItem(id: string, reason?: string): Promise<WorkItem> {
  return apiFetch<WorkItem>(`/sales/work/items/${id}/cancel`, {
    method: 'POST',
    body: JSON.stringify({ status: 'cancelled', reason }),
  });
}

export async function rescheduleWorkItem(id: string, due_at: string): Promise<WorkItem> {
  return apiFetch<WorkItem>(`/sales/work/items/${id}/reschedule`, {
    method: 'POST',
    body: JSON.stringify({ due_at }),
  });
}

export async function createMeeting(payload: WorkItemInput & { meeting_type?: string; meeting_url?: string; agenda?: string }): Promise<WorkItem> {
  return apiFetch<WorkItem>('/sales/work/meetings', { method: 'POST', body: JSON.stringify(payload) });
}

export async function createFollowUp(payload: WorkItemInput & { contact_method?: string }): Promise<WorkItem> {
  return apiFetch<WorkItem>('/sales/work/follow-ups', { method: 'POST', body: JSON.stringify(payload) });
}

export async function fetchCalendarEvents(from_at?: string, to_at?: string): Promise<CalendarEvent[]> {
  const params = new URLSearchParams();
  if (from_at) params.set('from_at', from_at);
  if (to_at) params.set('to_at', to_at);
  const qs = params.toString();
  return apiFetch<CalendarEvent[]>(`/sales/work/calendar${qs ? `?${qs}` : ''}`);
}

export async function fetchLeadWorkItems(leadId: string): Promise<WorkItemListResponse> {
  return apiFetch<WorkItemListResponse>(`/sales/work/leads/${leadId}/items`);
}

export async function fetchOpportunityWorkItems(opportunityId: string): Promise<WorkItemListResponse> {
  return apiFetch<WorkItemListResponse>(`/sales/work/opportunities/${opportunityId}/items`);
}
