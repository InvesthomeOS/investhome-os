/** CRM Activity system types — aligned with API schemas. */

export type CrmActivityEntityType =
  | 'contact'
  | 'company'
  | 'opportunity'
  | 'investor'
  | 'property'
  | 'project'
  | 'transaction'
  | 'investment'
  | 'vendor'
  | 'internal_user'
  | 'relationship';

export type CrmActivityType =
  | 'note'
  | 'phone_call'
  | 'email'
  | 'whatsapp'
  | 'sms'
  | 'meeting'
  | 'zoom_meeting'
  | 'teams_meeting'
  | 'site_visit'
  | 'property_tour'
  | 'investor_meeting'
  | 'construction_meeting'
  | 'inspection'
  | 'document_sent'
  | 'document_received'
  | 'proposal_sent'
  | 'proposal_received'
  | 'reservation'
  | 'contract_signed'
  | 'closing'
  | 'payment'
  | 'task'
  | 'reminder'
  | 'follow_up'
  | 'internal_discussion'
  | 'comment'
  | 'system_event'
  | 'automation_event'
  | 'other';

export type CrmActivityCategory =
  | 'communication'
  | 'meeting'
  | 'task'
  | 'note'
  | 'document'
  | 'transaction'
  | 'follow_up'
  | 'system'
  | 'other';

export type CrmActivityStatus =
  | 'planned'
  | 'scheduled'
  | 'in_progress'
  | 'completed'
  | 'cancelled'
  | 'missed'
  | 'deferred'
  | 'archived';

export type CrmTaskStatus =
  | 'not_started'
  | 'in_progress'
  | 'waiting'
  | 'completed'
  | 'cancelled'
  | 'deferred';

export type CrmActivityPriority = 'low' | 'medium' | 'high' | 'critical';

export type CrmActivityVisibility = 'private' | 'team' | 'organization' | 'restricted';

export type CrmFollowUpReason =
  | 'investor'
  | 'broker'
  | 'lender'
  | 'property'
  | 'opportunity'
  | 'relationship_review'
  | 'contract'
  | 'payment'
  | 'inspection'
  | 'custom';

export type CrmActivityEntityLink = {
  entity_type: CrmActivityEntityType;
  entity_id: string;
  is_primary: boolean;
};

export type CrmActivityChecklistItem = {
  id: string;
  title: string;
  sort_order: number;
  is_completed: boolean;
  completed_by: string | null;
  completed_at: string | null;
};

export type CrmActivityAttachment = {
  id: string;
  file_name: string;
  file_url: string | null;
  mime_type: string | null;
  file_size_bytes: number | null;
  document_id: string | null;
  created_at: string;
};

export type CrmActivityComment = {
  id: string;
  parent_id: string | null;
  body: string;
  mentions: string[] | null;
  reactions: Record<string, string[]> | null;
  created_by: string | null;
  created_at: string;
  updated_at: string | null;
};

export type CrmActivitySummary = {
  id: string;
  entity_type: CrmActivityEntityType;
  entity_id: string;
  related_entity_type: CrmActivityEntityType | null;
  related_entity_id: string | null;
  activity_type: CrmActivityType;
  activity_category: CrmActivityCategory;
  title: string;
  summary: string | null;
  status: CrmActivityStatus;
  task_status: CrmTaskStatus | null;
  priority: CrmActivityPriority;
  owner_id: string | null;
  assigned_user_id: string | null;
  assigned_team_id: string | null;
  start_date: string | null;
  end_date: string | null;
  due_date: string | null;
  completed_at: string | null;
  reminder_date: string | null;
  timezone: string | null;
  location: string | null;
  meeting_url: string | null;
  tags: string[] | null;
  visibility: CrmActivityVisibility;
  is_pinned: boolean;
  is_favorite: boolean;
  follow_up_reason: CrmFollowUpReason | null;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  archived_at: string | null;
  has_attachments: boolean;
  comment_count: number;
  entity_name?: string | null;
  assigned_user_name?: string | null;
  owner_name?: string | null;
  created_by_name?: string | null;
  related_entity_name?: string | null;
};

export type CrmActivityDetail = CrmActivitySummary & {
  description: string | null;
  outcome: string | null;
  duration_minutes: number | null;
  estimated_duration_minutes: number | null;
  actual_duration_minutes: number | null;
  recurrence_frequency: string | null;
  recurrence_rule: string | null;
  metadata_json: Record<string, unknown> | null;
  entity_links: CrmActivityEntityLink[];
  checklist_items: CrmActivityChecklistItem[];
  attachments: CrmActivityAttachment[];
  reminders: Array<{
    id: string;
    channel: string;
    remind_at: string;
    offset_minutes: number | null;
    is_sent: boolean;
  }>;
  comments: CrmActivityComment[];
};

export type CrmActivityListResponse = {
  items: CrmActivitySummary[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
  request_id: string;
};

export type CrmTimelineEntry = {
  id: string;
  source: string;
  activity_type: string;
  title: string;
  summary: string | null;
  status: string | null;
  priority: string | null;
  entity_type: string | null;
  entity_id: string | null;
  actor_name: string | null;
  created_at: string;
  is_system_event: boolean;
  metadata_json: Record<string, unknown> | null;
};

export type CrmTimelineResponse = {
  items: CrmTimelineEntry[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
  request_id: string;
};

export type CrmCalendarEvent = {
  id: string;
  title: string;
  activity_type: CrmActivityType;
  status: CrmActivityStatus;
  start_date: string | null;
  end_date: string | null;
  due_date: string | null;
  all_day: boolean;
  entity_type: CrmActivityEntityType;
  entity_id: string;
  assigned_user_id: string | null;
  color: string | null;
  entity_name?: string | null;
  assigned_user_name?: string | null;
};

export type CrmCalendarResponse = {
  events: CrmCalendarEvent[];
  start: string;
  end: string;
};

export type CrmActivityDashboardWidgets = {
  todays_tasks: CrmActivitySummary[];
  overdue_tasks: CrmActivitySummary[];
  upcoming_meetings: CrmActivitySummary[];
  follow_ups_due: CrmActivitySummary[];
  recent_notes: CrmActivitySummary[];
  recent_activities: CrmActivitySummary[];
  missed_activities: CrmActivitySummary[];
};

export type ActivityListParams = {
  search?: string;
  entity_type?: CrmActivityEntityType;
  entity_id?: string;
  activity_type?: CrmActivityType;
  activity_types?: CrmActivityType[];
  activity_category?: CrmActivityCategory;
  status?: CrmActivityStatus;
  priority?: CrmActivityPriority;
  owner_id?: string;
  assigned_user_id?: string;
  created_by?: string;
  responsible_user_id?: string;
  visibility?: CrmActivityVisibility;
  tags?: string[];
  has_attachments?: boolean;
  completed?: boolean;
  pending?: boolean;
  date_from?: string;
  date_to?: string;
  include_archived?: boolean;
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
};

export type ActivityInput = {
  entity_type: CrmActivityEntityType;
  entity_id: string;
  related_entity_type?: CrmActivityEntityType;
  related_entity_id?: string;
  activity_type: CrmActivityType;
  activity_category?: CrmActivityCategory;
  title: string;
  summary?: string;
  description?: string;
  outcome?: string;
  status?: CrmActivityStatus;
  task_status?: CrmTaskStatus;
  priority?: CrmActivityPriority;
  owner_id?: string;
  assigned_user_id?: string;
  assigned_team_id?: string;
  start_date?: string;
  end_date?: string;
  duration_minutes?: number;
  due_date?: string;
  reminder_date?: string;
  timezone?: string;
  location?: string;
  meeting_url?: string;
  tags?: string[];
  visibility?: CrmActivityVisibility;
  follow_up_reason?: CrmFollowUpReason;
  metadata_json?: Record<string, unknown>;
  entity_links?: CrmActivityEntityLink[];
  checklist_items?: Array<{ title: string; sort_order?: number; is_completed?: boolean }>;
};

export type FollowUpInput = {
  entity_type: CrmActivityEntityType;
  entity_id: string;
  reason: CrmFollowUpReason;
  title?: string;
  due_date: string;
  reminder_date?: string;
  notes?: string;
  owner_id?: string;
  assigned_user_id?: string;
};

export const CRM_ACTIVITY_TYPES: CrmActivityType[] = [
  'note',
  'phone_call',
  'email',
  'whatsapp',
  'meeting',
  'task',
  'follow_up',
  'site_visit',
  'proposal_sent',
  'document_sent',
  'other',
];

export const CRM_ACTIVITY_STATUSES: CrmActivityStatus[] = [
  'planned',
  'scheduled',
  'in_progress',
  'completed',
  'cancelled',
  'missed',
  'deferred',
];

export const CRM_TASK_STATUSES: CrmTaskStatus[] = [
  'not_started',
  'in_progress',
  'waiting',
  'completed',
  'cancelled',
  'deferred',
];

export const CRM_ACTIVITY_PRIORITIES: CrmActivityPriority[] = [
  'low',
  'medium',
  'high',
  'critical',
];

export const CRM_ACTIVITY_ENTITY_TYPES: CrmActivityEntityType[] = [
  'contact',
  'company',
  'opportunity',
  'investor',
  'property',
  'project',
  'relationship',
  'vendor',
];

export type TaskViewMode = 'list' | 'kanban' | 'calendar' | 'my' | 'team';

export type CalendarViewMode = 'day' | 'week' | 'month' | 'agenda';
