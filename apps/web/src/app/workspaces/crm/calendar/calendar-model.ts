import type { IhIconName } from '@/components/icons/ih-icons';

export type CalendarViewMode = 'day' | 'week' | 'month' | 'list';

export type CalendarEventTypeKey =
  | 'phone'
  | 'meeting'
  | 'investorMeeting'
  | 'siteVisit'
  | 'internalMeeting'
  | 'documentHandoff'
  | 'task'
  | 'presentation'
  | 'demo';

export type CalendarKpiKey =
  | 'todayEvents'
  | 'thisWeek'
  | 'upcomingMeetings'
  | 'completed'
  | 'attendanceRate';

export type CalendarWhenLabel = 'today' | 'tomorrow' | 'later';

export type CalendarSyncStatus = 'connected' | 'notConnected';

export type CalendarEvent = {
  id: string;
  titleKey: string;
  title?: string;
  customer: string;
  customerId?: string;
  project: string;
  type: CalendarEventTypeKey;
  activityType?: string;
  /** 0 = Monday … 6 = Sunday within the fixture week */
  dayIndex: number;
  dateIso?: string;
  /** Minutes from 08:00; null = all-day */
  startMinute: number | null;
  durationMinutes: number;
  participantCount: number;
  allDay?: boolean;
};

export type CalendarKpi = {
  key: CalendarKpiKey;
  value: string;
  hintKey: string;
  delta?: string;
  deltaTone?: 'up' | 'down' | 'neutral';
  tone?: 'default' | 'success' | 'warning';
};

export type CalendarUpcomingItem = {
  id: string;
  titleKey: string;
  title?: string;
  timeLabel: string;
  when: CalendarWhenLabel;
  type: CalendarEventTypeKey;
};

export type CalendarAiSuggestion = {
  id: string;
  bodyKey: string;
};

export type CalendarSyncItem = {
  id: string;
  providerKey: 'google' | 'outlook';
  status: CalendarSyncStatus;
};

export type CalendarWorkspacePreview = {
  /** Anchor Monday for the fixture week (ISO date YYYY-MM-DD). */
  weekStartIso: string;
  /** Current day index within the week (0–6). */
  currentDayIndex: number;
  /** Presentation current-time line (minutes from 08:00). */
  nowMinute: number;
  rangeLabelKey: string;
  rangeLabel?: string;
  kpis: CalendarKpi[];
  events: CalendarEvent[];
  upcoming: CalendarUpcomingItem[];
  aiSuggestions: CalendarAiSuggestion[];
  sync: CalendarSyncItem[];
};

export const CALENDAR_VIEW_ORDER: CalendarViewMode[] = ['month', 'week', 'day', 'list'];

export const CALENDAR_HOURS = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18] as const;

export const CALENDAR_DAY_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const;

/** Dashboard IhIcon map — phone/meeting/field/document/video scan cues (no new icons). */
export const CALENDAR_EVENT_TYPE_ICONS: Record<CalendarEventTypeKey, IhIconName> = {
  phone: 'activity',
  meeting: 'meeting',
  investorMeeting: 'users',
  siteVisit: 'target',
  internalMeeting: 'meeting',
  documentHandoff: 'documents',
  task: 'check',
  presentation: 'barChart',
  demo: 'sparkles',
};

export const CALENDAR_KPI_ICONS: Record<CalendarKpiKey, IhIconName> = {
  todayEvents: 'calendar',
  thisWeek: 'barChart',
  upcomingMeetings: 'users',
  completed: 'check',
  attendanceRate: 'clock',
};

export const CALENDAR_QUICK_CREATE: ReadonlyArray<{
  key: 'meeting' | 'call' | 'task' | 'reminder';
  icon: IhIconName;
}> = [
  { key: 'meeting', icon: 'meeting' },
  { key: 'call', icon: 'activity' },
  { key: 'task', icon: 'check' },
  { key: 'reminder', icon: 'bell' },
];
