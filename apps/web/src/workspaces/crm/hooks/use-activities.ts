import type { ActivityListParams } from '@/workspaces/crm/types/activities';
import {
  archiveActivity,
  bulkUpdateActivities,
  completeFollowUp,
  completeTask,
  createActivity,
  createFollowUp,
  createMeeting,
  createNote,
  createTask,
  deleteActivity,
  duplicateActivity,
  fetchActivities,
  fetchActivity,
  fetchActivityWidgets,
  fetchCalendar,
  fetchFollowUps,
  fetchMeetings,
  fetchNotes,
  fetchSavedActivityFilters,
  fetchTasks,
  fetchTimeline,
  restoreActivity,
  updateActivity,
} from '@/workspaces/crm/api/activities';

export const activityQueryKeys = {
  all: ['crm', 'activities'] as const,
  list: (params: ActivityListParams) => ['crm', 'activities', 'list', params] as const,
  detail: (id: string) => ['crm', 'activities', 'detail', id] as const,
  timeline: (params: ActivityListParams) => ['crm', 'timeline', params] as const,
  tasks: (params: ActivityListParams) => ['crm', 'tasks', params] as const,
  notes: (params: ActivityListParams) => ['crm', 'notes', params] as const,
  meetings: (params: ActivityListParams) => ['crm', 'meetings', params] as const,
  followUps: (params: ActivityListParams) => ['crm', 'follow-ups', params] as const,
  calendar: (params: { start: string; end: string; assigned_user_id?: string }) =>
    ['crm', 'calendar', params] as const,
  widgets: ['crm', 'activities', 'widgets'] as const,
  savedFilters: ['crm', 'activities', 'saved-filters'] as const,
};

export const activityQueries = {
  list: (params: ActivityListParams) => ({
    queryKey: activityQueryKeys.list(params),
    queryFn: () => fetchActivities(params),
  }),
  detail: (id: string) => ({
    queryKey: activityQueryKeys.detail(id),
    queryFn: () => fetchActivity(id),
    enabled: Boolean(id),
  }),
  timeline: (params: ActivityListParams) => ({
    queryKey: activityQueryKeys.timeline(params),
    queryFn: () => fetchTimeline(params),
  }),
  tasks: (params: ActivityListParams & { my_tasks?: boolean; team_tasks?: boolean }) => ({
    queryKey: activityQueryKeys.tasks(params),
    queryFn: () => fetchTasks(params),
  }),
  notes: (params: ActivityListParams) => ({
    queryKey: activityQueryKeys.notes(params),
    queryFn: () => fetchNotes(params),
  }),
  meetings: (params: ActivityListParams) => ({
    queryKey: activityQueryKeys.meetings(params),
    queryFn: () => fetchMeetings(params),
  }),
  followUps: (params: ActivityListParams) => ({
    queryKey: activityQueryKeys.followUps(params),
    queryFn: () => fetchFollowUps(params),
  }),
  calendar: (params: { start: string; end: string; assigned_user_id?: string }) => ({
    queryKey: activityQueryKeys.calendar(params),
    queryFn: () => fetchCalendar(params),
  }),
  widgets: () => ({
    queryKey: activityQueryKeys.widgets,
    queryFn: () => fetchActivityWidgets(),
  }),
  savedFilters: () => ({
    queryKey: activityQueryKeys.savedFilters,
    queryFn: () => fetchSavedActivityFilters(),
  }),
};

export const activityMutations = {
  create: createActivity,
  update: updateActivity,
  archive: archiveActivity,
  restore: restoreActivity,
  delete: deleteActivity,
  duplicate: duplicateActivity,
  bulkUpdate: bulkUpdateActivities,
  createTask,
  completeTask,
  createNote,
  createMeeting,
  createFollowUp,
  completeFollowUp,
};
