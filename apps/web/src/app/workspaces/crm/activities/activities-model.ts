import type { IhIconName } from '@/components/icons/ih-icons';

export type ActivityTypeKey =
  | 'phone'
  | 'whatsapp'
  | 'email'
  | 'meeting'
  | 'note'
  | 'documentShared'
  | 'missedCall'
  | 'sms'
  | 'videoCall';

export type ActivityStatusKey = 'completed' | 'pending' | 'cancelled' | 'inProgress';

export type ActivityPriorityKey = 'low' | 'medium' | 'high' | 'critical';

export type ActivityKpiKey = 'today' | 'completed' | 'pending' | 'overdue';

export type ActivityAiActionKey =
  | 'summarizeToday'
  | 'showFollowUps'
  | 'missedCustomers'
  | 'aiSummary';

export type ActivityRow = {
  id: string;
  type: ActivityTypeKey;
  titleKey: string;
  title?: string;
  descriptionKey: string;
  description?: string;
  customer: string;
  customerId?: string;
  customerDetail: string;
  project: string;
  projectTone: 'navy' | 'cyan' | 'green' | 'amber' | 'slate';
  salesRep: string;
  salesRepInitials: string;
  dateTime: string;
  occurredAt?: string;
  status: ActivityStatusKey;
  priority: ActivityPriorityKey;
  aiSummaryKey: string;
  aiSummary?: string;
};

export type ActivityKpi = {
  key: ActivityKpiKey;
  value: number;
  delta: string;
  deltaTone: 'up' | 'down' | 'neutral';
  hintKey: string;
};

export type ActivityDaySummary = {
  completed: number;
  pending: number;
  overdue: number;
  assessmentKey: string;
};

export type ActivityOverdueFollowUp = {
  id: string;
  customer: string;
  daysOverdue: number;
};

export type ActivityUpcomingMeeting = {
  id: string;
  title: string;
  customer: string;
  time: string;
};

export type ActivityAiRecommendation = {
  id: string;
  bodyKey: string;
};

export type ActivityRecentNote = {
  id: string;
  author: string;
  bodyKey: string;
  body?: string;
  timeKey: string;
  time?: string;
};

export type ActivityWorkspacePreview = {
  totalActivities: number;
  kpis: ActivityKpi[];
  daySummary: ActivityDaySummary;
  activities: ActivityRow[];
  customers: string[];
  salesReps: string[];
  projects: string[];
  overdueFollowUps: ActivityOverdueFollowUp[];
  upcomingMeetings: ActivityUpcomingMeeting[];
  aiRecommendations: ActivityAiRecommendation[];
  recentNotes: ActivityRecentNote[];
};

export const ACTIVITY_TYPE_ICONS: Record<ActivityTypeKey, IhIconName> = {
  phone: 'activity',
  whatsapp: 'inbox',
  email: 'roles',
  meeting: 'meeting',
  note: 'documents',
  documentShared: 'documents',
  missedCall: 'alert',
  sms: 'bell',
  videoCall: 'users',
};

export const ACTIVITY_TYPE_ORDER: ActivityTypeKey[] = [
  'phone',
  'whatsapp',
  'email',
  'meeting',
  'note',
  'documentShared',
  'missedCall',
  'sms',
  'videoCall',
];

export const ACTIVITY_STATUS_ORDER: ActivityStatusKey[] = [
  'completed',
  'pending',
  'cancelled',
  'inProgress',
];

export const ACTIVITY_PRIORITY_ORDER: ActivityPriorityKey[] = [
  'low',
  'medium',
  'high',
  'critical',
];
