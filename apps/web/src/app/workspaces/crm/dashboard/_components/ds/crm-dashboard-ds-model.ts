import type { IhIconName } from '@/components/icons/ih-icons';
import type { CrmDashboardData } from '@/workspaces/crm/types';
import type { CrmReportsSummary } from '@/workspaces/crm/api/reports';

export type StatusTone = 'default' | 'success' | 'warning' | 'danger' | 'info';

export type PriorityKey =
  | 'followUps'
  | 'meetings'
  | 'highPriorityLeads'
  | 'unread'
  | 'overdueTasks';

export type KpiKey = 'totalContacts' | 'activeLeads' | 'pipelineValue' | 'activitiesWeek';

export type InsightTone = 'warning' | 'danger' | 'info' | 'success';

export type ActivityKind = 'call' | 'email' | 'meeting' | 'task' | 'note' | 'file';

export type TaskKind = 'meeting' | 'call' | 'email' | 'task';

export type LeadAvatarTone = 'navy' | 'cyan' | 'green' | 'amber' | 'violet' | 'rose';

export type PriorityCard = {
  key: PriorityKey;
  value: number;
  href: string;
  icon: IhIconName;
};

export type KpiItem = {
  key: KpiKey;
  value: string;
  delta?: string;
  deltaTone?: 'up' | 'down' | 'neutral';
  icon: IhIconName;
};

export type TaskItem = {
  id: string;
  title: string;
  related: string;
  dueLabel: string;
  kind: TaskKind;
  done?: boolean;
  href: string;
};

export type LeadItem = {
  id: string;
  name: string;
  initials: string;
  tone: LeadAvatarTone;
  tag: string;
  isNew?: boolean;
  dateLabel: string;
  href: string;
};

export type ActivityItem = {
  id: string;
  kind: ActivityKind;
  title: string;
  meta: string;
  timeLabel: string;
  href: string;
};

export type InsightItem = {
  id: string;
  tone: InsightTone;
  titleKey: string;
  bodyKey: string;
  href: string;
};

export type TimelineItem = {
  id: string;
  kind: ActivityKind;
  title: string;
  meta: string;
  timeLabel: string;
  href: string;
};

export type MeetingItem = {
  id: string;
  day: string;
  month: string;
  title: string;
  contact: string;
  project: string;
  time: string;
  location: string;
  joinHref?: string;
  openHref: string;
};

export type PipelinePoint = { label: string; value: number };

export type CrmDashboardDsData = {
  priorities: PriorityCard[];
  kpis: KpiItem[];
  tasks: TaskItem[];
  leads: LeadItem[];
  activities: ActivityItem[];
  insights: InsightItem[];
  timeline: TimelineItem[];
  meetings: MeetingItem[];
  pipelineTrend: PipelinePoint[];
};

export const PRIORITY_ORDER: PriorityKey[] = [
  'followUps',
  'meetings',
  'highPriorityLeads',
  'unread',
  'overdueTasks',
];

export const KPI_ICONS: Record<KpiKey, IhIconName> = {
  totalContacts: 'users',
  activeLeads: 'target',
  pipelineValue: 'trendingUp',
  activitiesWeek: 'activity',
};

export const TASK_KIND_TONE: Record<TaskKind, StatusTone> = {
  meeting: 'info',
  call: 'success',
  email: 'warning',
  task: 'default',
};

export const ACTIVITY_ICONS: Record<ActivityKind, IhIconName> = {
  call: 'meeting',
  email: 'inbox',
  meeting: 'calendar',
  task: 'check',
  note: 'documents',
  file: 'documents',
};

export const INSIGHT_ICONS: Record<InsightTone, IhIconName> = {
  warning: 'alert',
  danger: 'alert',
  info: 'sparkles',
  success: 'trendingUp',
};

function formatCount(n: number, locale: string): string {
  return new Intl.NumberFormat(locale).format(n);
}

function initialsFrom(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return `${parts[0]![0] ?? ''}${parts[1]![0] ?? ''}`.toUpperCase();
}

const AVATAR_TONES: LeadAvatarTone[] = ['navy', 'cyan', 'green', 'amber', 'violet', 'rose'];

const PRIORITY_HREFS: Record<PriorityKey, { href: string; icon: IhIconName }> = {
  followUps: { href: '/workspaces/crm/tasks', icon: 'refresh' },
  meetings: { href: '/workspaces/crm/calendar', icon: 'calendar' },
  highPriorityLeads: { href: '/workspaces/crm/leads', icon: 'target' },
  unread: { href: '/workspaces/crm/communication', icon: 'inbox' },
  overdueTasks: { href: '/workspaces/crm/tasks', icon: 'alert' },
};

function activityKindFromKey(key: string, fallback: ActivityKind): ActivityKind {
  const value = key.toLowerCase();
  if (value.includes('meeting')) return 'meeting';
  if (value.includes('call') || value.includes('phone')) return 'call';
  if (value.includes('email')) return 'email';
  if (value.includes('task')) return 'task';
  if (value.includes('note') || value.includes('comment')) return 'note';
  if (value.includes('file') || value.includes('document')) return 'file';
  return fallback;
}

/**
 * Map live dashboard + reports APIs into the DS presentation model.
 * Widgets without a real data source stay empty — no fixture merge.
 */
export function buildDashboardDsData(
  api: CrmDashboardData | undefined,
  locale: string,
  activityLabel?: (descriptionKey: string) => string,
  reports?: CrmReportsSummary,
): CrmDashboardDsData {
  const dateFmt = new Intl.DateTimeFormat(locale, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
  const timeFmt = new Intl.DateTimeFormat(locale, { hour: '2-digit', minute: '2-digit' });
  const dayFmt = new Intl.DateTimeFormat(locale, { day: '2-digit' });
  const monthFmt = new Intl.DateTimeFormat(locale, { month: 'short' });

  const liveTasks: TaskItem[] = (api?.upcoming_tasks ?? []).slice(0, 8).map((task, i) => ({
    id: task.id,
    title: task.title,
    related: task.status,
    dueLabel: task.due_at ? timeFmt.format(new Date(task.due_at)) : '—',
    kind: (['meeting', 'call', 'email', 'task'] as TaskKind[])[i % 4]!,
    href: '/workspaces/crm/tasks',
  }));

  const liveLeads: LeadItem[] = (api?.recent_contacts ?? []).slice(0, 8).map((c, i) => ({
    id: c.id,
    name: c.display_name,
    initials: initialsFrom(c.display_name),
    tone: AVATAR_TONES[i % AVATAR_TONES.length]!,
    tag: c.contact_type,
    isNew: i < 2,
    dateLabel: locale.startsWith('tr') ? 'Yeni' : 'Recent',
    href: `/workspaces/crm/contacts/${c.id}`,
  }));

  const liveActivities: ActivityItem[] = (api?.recent_activities ?? []).slice(0, 8).map((a) => {
    const title = activityLabel
      ? activityLabel(a.description_key)
      : a.description_key.replace(/[._]/g, ' ');
    return {
      id: a.id,
      kind: activityKindFromKey(a.action || a.description_key, 'note'),
      title,
      meta: a.actor_name ?? 'System',
      timeLabel: dateFmt.format(new Date(a.created_at)),
      href: '/workspaces/crm/activities',
    };
  });

  const liveMeetings: MeetingItem[] = (api?.todays_meetings ?? []).slice(0, 6).map((m) => {
    const start = m.start_at ? new Date(m.start_at) : null;
    return {
      id: m.id,
      day: start ? dayFmt.format(start) : '—',
      month: start ? monthFmt.format(start).toUpperCase().slice(0, 3) : '—',
      title: m.title,
      contact: m.status ?? '—',
      project: 'CRM',
      time: start ? timeFmt.format(start) : '—',
      location: 'Meeting',
      openHref: '/workspaces/crm/calendar',
      joinHref: '/workspaces/crm/calendar',
    };
  });

  const overdueCount =
    reports?.tasks_overdue ??
    (api?.upcoming_tasks ?? []).filter((t) => {
      if (!t.due_at) return false;
      return new Date(t.due_at).getTime() < Date.now();
    }).length;

  const contactCount = reports?.contacts_total ?? api?.communication_summary.total_contacts ?? 0;
  const pipelineCount = reports?.pipeline_total ?? 0;
  const activityCount = reports?.activities_total ?? api?.communication_summary.recent_interactions_count ?? 0;
  const followUps = reports?.tasks_pending ?? api?.upcoming_tasks?.length ?? 0;
  const meetings = api?.todays_meetings?.length ?? 0;

  return {
    priorities: [
      { key: 'followUps', value: followUps, ...PRIORITY_HREFS.followUps },
      { key: 'meetings', value: meetings, ...PRIORITY_HREFS.meetings },
      { key: 'highPriorityLeads', value: 0, ...PRIORITY_HREFS.highPriorityLeads },
      { key: 'unread', value: 0, ...PRIORITY_HREFS.unread },
      { key: 'overdueTasks', value: overdueCount, ...PRIORITY_HREFS.overdueTasks },
    ],
    kpis: [
      {
        key: 'totalContacts',
        value: formatCount(contactCount, locale),
        icon: KPI_ICONS.totalContacts,
      },
      {
        key: 'activeLeads',
        value: formatCount(pipelineCount, locale),
        icon: KPI_ICONS.activeLeads,
      },
      {
        key: 'pipelineValue',
        value: '—',
        icon: KPI_ICONS.pipelineValue,
      },
      {
        key: 'activitiesWeek',
        value: formatCount(activityCount, locale),
        icon: KPI_ICONS.activitiesWeek,
      },
    ],
    tasks: liveTasks,
    leads: liveLeads,
    activities: liveActivities,
    insights: [],
    meetings: liveMeetings,
    timeline: liveActivities.map((a) => ({
      id: `tl-${a.id}`,
      kind: a.kind,
      title: a.title,
      meta: a.meta,
      timeLabel: a.timeLabel,
      href: a.href,
    })),
    pipelineTrend: [],
  };
}
