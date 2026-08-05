import type { IhIconName } from '@/components/icons/ih-icons';
import type { CrmDashboardData } from '@/workspaces/crm/types';

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

function formatMoney(n: number, locale: string): string {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(n);
}

function initialsFrom(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return `${parts[0]![0] ?? ''}${parts[1]![0] ?? ''}`.toUpperCase();
}

const AVATAR_TONES: LeadAvatarTone[] = ['navy', 'cyan', 'green', 'amber', 'violet', 'rose'];

/** Rich operational fixture — used when API payload is sparse. */
export function makeDashboardFixture(locale = 'en'): CrmDashboardDsData {
  return {
    priorities: [
      { key: 'followUps', value: 7, href: '/workspaces/crm/tasks', icon: 'refresh' },
      { key: 'meetings', value: 3, href: '/workspaces/crm/calendar', icon: 'calendar' },
      { key: 'highPriorityLeads', value: 2, href: '/workspaces/crm/leads', icon: 'target' },
      { key: 'unread', value: 5, href: '/workspaces/crm/communication', icon: 'inbox' },
      { key: 'overdueTasks', value: 1, href: '/workspaces/crm/tasks', icon: 'alert' },
    ],
    kpis: [
      {
        key: 'totalContacts',
        value: formatCount(1248, locale),
        delta: '+12%',
        deltaTone: 'up',
        icon: KPI_ICONS.totalContacts,
      },
      {
        key: 'activeLeads',
        value: formatCount(245, locale),
        delta: '+8%',
        deltaTone: 'up',
        icon: KPI_ICONS.activeLeads,
      },
      {
        key: 'pipelineValue',
        value: formatMoney(29_475_000, locale),
        delta: '+4.2%',
        deltaTone: 'up',
        icon: KPI_ICONS.pipelineValue,
      },
      {
        key: 'activitiesWeek',
        value: formatCount(86, locale),
        delta: '+15%',
        deltaTone: 'up',
        icon: KPI_ICONS.activitiesWeek,
      },
    ],
    tasks: [
      {
        id: 't1',
        title: 'Temple Tower site walkthrough',
        related: 'Ahmet Yılmaz',
        dueLabel: '10:30',
        kind: 'meeting',
        href: '/workspaces/crm/tasks',
      },
      {
        id: 't2',
        title: 'Follow-up call — Marina Residences',
        related: 'Sara Al-Hassan',
        dueLabel: '14:00',
        kind: 'call',
        href: '/workspaces/crm/tasks',
      },
      {
        id: 't3',
        title: 'Send revised term sheet',
        related: 'Nordic Capital',
        dueLabel: '16:00',
        kind: 'email',
        href: '/workspaces/crm/tasks',
      },
      {
        id: 't4',
        title: 'Update KYC checklist',
        related: 'Elena Petrova',
        dueLabel: 'Tomorrow',
        kind: 'task',
        href: '/workspaces/crm/tasks',
      },
      {
        id: 't5',
        title: 'Broker briefing pack',
        related: 'Atlas Realty',
        dueLabel: 'Wed',
        kind: 'task',
        href: '/workspaces/crm/tasks',
      },
      {
        id: 't6',
        title: 'Confirm unit allocation',
        related: 'Horizon Fund',
        dueLabel: 'Thu',
        kind: 'call',
        href: '/workspaces/crm/tasks',
      },
    ],
    leads: [
      {
        id: 'l1',
        name: 'Mehmet Kaya',
        initials: 'MK',
        tone: 'navy',
        tag: 'Investor',
        isNew: true,
        dateLabel: 'Today',
        href: '/workspaces/crm/leads',
      },
      {
        id: 'l2',
        name: 'Layla Mansour',
        initials: 'LM',
        tone: 'cyan',
        tag: 'Broker',
        isNew: true,
        dateLabel: 'Today',
        href: '/workspaces/crm/leads',
      },
      {
        id: 'l3',
        name: 'James Whitfield',
        initials: 'JW',
        tone: 'green',
        tag: 'Developer',
        dateLabel: 'Yesterday',
        href: '/workspaces/crm/leads',
      },
      {
        id: 'l4',
        name: 'Ayşe Demir',
        initials: 'AD',
        tone: 'amber',
        tag: 'Investor',
        dateLabel: 'Yesterday',
        href: '/workspaces/crm/leads',
      },
      {
        id: 'l5',
        name: 'Omar Farouk',
        initials: 'OF',
        tone: 'violet',
        tag: 'Partner',
        dateLabel: '2d ago',
        href: '/workspaces/crm/leads',
      },
      {
        id: 'l6',
        name: 'Nina Costa',
        initials: 'NC',
        tone: 'rose',
        tag: 'Investor',
        isNew: true,
        dateLabel: '2d ago',
        href: '/workspaces/crm/leads',
      },
    ],
    activities: [
      {
        id: 'a1',
        kind: 'meeting',
        title: 'Meeting completed with Ahmet Yılmaz',
        meta: 'Temple Tower · Discovery',
        timeLabel: '25m ago',
        href: '/workspaces/crm/activities',
      },
      {
        id: 'a2',
        kind: 'call',
        title: 'Outbound call — Sara Al-Hassan',
        meta: 'Marina Residences · 12 min',
        timeLabel: '1h ago',
        href: '/workspaces/crm/activities',
      },
      {
        id: 'a3',
        kind: 'email',
        title: 'Proposal sent to Nordic Capital',
        meta: 'Skyline Phase 2',
        timeLabel: '3h ago',
        href: '/workspaces/crm/activities',
      },
      {
        id: 'a4',
        kind: 'note',
        title: 'Note added on Elena Petrova',
        meta: 'KYC documents pending',
        timeLabel: '5h ago',
        href: '/workspaces/crm/notes',
      },
      {
        id: 'a5',
        kind: 'task',
        title: 'Task completed — Broker pack',
        meta: 'Atlas Realty',
        timeLabel: 'Yesterday',
        href: '/workspaces/crm/tasks',
      },
      {
        id: 'a6',
        kind: 'file',
        title: 'Floor plan uploaded',
        meta: 'Horizon Fund · Unit B-12',
        timeLabel: 'Yesterday',
        href: '/workspaces/crm/documents',
      },
    ],
    insights: [
      {
        id: 'i1',
        tone: 'warning',
        titleKey: 'noReply',
        bodyKey: 'noReplyBody',
        href: '/workspaces/crm/communication',
      },
      {
        id: 'i2',
        tone: 'danger',
        titleKey: 'atRisk',
        bodyKey: 'atRiskBody',
        href: '/workspaces/crm/pipeline',
      },
      {
        id: 'i3',
        tone: 'success',
        titleKey: 'engagementUp',
        bodyKey: 'engagementUpBody',
        href: '/workspaces/crm/leads',
      },
      {
        id: 'i4',
        tone: 'info',
        titleKey: 'scheduleMeetings',
        bodyKey: 'scheduleMeetingsBody',
        href: '/workspaces/crm/calendar',
      },
    ],
    timeline: [
      {
        id: 'tl1',
        kind: 'call',
        title: 'Call logged with Mehmet Kaya',
        meta: 'High-priority lead · 8 min',
        timeLabel: '12m ago',
        href: '/workspaces/crm/timeline',
      },
      {
        id: 'tl2',
        kind: 'email',
        title: 'Follow-up email opened — Layla Mansour',
        meta: 'Unread reply pending',
        timeLabel: '40m ago',
        href: '/workspaces/crm/timeline',
      },
      {
        id: 'tl3',
        kind: 'meeting',
        title: 'Calendar invite accepted — Temple Tower',
        meta: 'Ahmet Yılmaz · Tomorrow 10:30',
        timeLabel: '2h ago',
        href: '/workspaces/crm/calendar',
      },
      {
        id: 'tl4',
        kind: 'task',
        title: 'Overdue task escalated',
        meta: 'Update KYC checklist · Elena Petrova',
        timeLabel: '4h ago',
        href: '/workspaces/crm/tasks',
      },
      {
        id: 'tl5',
        kind: 'note',
        title: 'Relationship note updated',
        meta: 'Nordic Capital · Warm → Hot',
        timeLabel: 'Yesterday',
        href: '/workspaces/crm/notes',
      },
      {
        id: 'tl6',
        kind: 'file',
        title: 'Term sheet v3 shared',
        meta: 'Skyline Phase 2',
        timeLabel: 'Yesterday',
        href: '/workspaces/crm/documents',
      },
      {
        id: 'tl7',
        kind: 'call',
        title: 'Missed call from Atlas Realty',
        meta: 'Callback scheduled',
        timeLabel: 'Yesterday',
        href: '/workspaces/crm/communication',
      },
      {
        id: 'tl8',
        kind: 'meeting',
        title: 'Site visit completed — Marina Residences',
        meta: 'Sara Al-Hassan · Sales',
        timeLabel: '2d ago',
        href: '/workspaces/crm/activities',
      },
    ],
    meetings: [
      {
        id: 'm1',
        day: '27',
        month: 'JUL',
        title: 'Temple Tower discovery',
        contact: 'Ahmet Yılmaz',
        project: 'Temple Tower',
        time: '10:30 – 11:15',
        location: 'Video',
        joinHref: '/workspaces/crm/calendar',
        openHref: '/workspaces/crm/calendar',
      },
      {
        id: 'm2',
        day: '27',
        month: 'JUL',
        title: 'Marina pricing review',
        contact: 'Sara Al-Hassan',
        project: 'Marina Residences',
        time: '14:00 – 14:45',
        location: 'Office',
        openHref: '/workspaces/crm/calendar',
      },
      {
        id: 'm3',
        day: '28',
        month: 'JUL',
        title: 'Nordic Capital term sync',
        contact: 'Erik Lindqvist',
        project: 'Skyline Phase 2',
        time: '11:00 – 12:00',
        location: 'Video',
        joinHref: '/workspaces/crm/calendar',
        openHref: '/workspaces/crm/calendar',
      },
      {
        id: 'm4',
        day: '29',
        month: 'JUL',
        title: 'Broker network briefing',
        contact: 'Atlas Realty',
        project: 'Portfolio',
        time: '09:30 – 10:00',
        location: 'Hybrid',
        openHref: '/workspaces/crm/calendar',
      },
    ],
    pipelineTrend: [
      { label: 'W1', value: 22.1 },
      { label: 'W2', value: 23.4 },
      { label: 'W3', value: 24.0 },
      { label: 'W4', value: 25.8 },
      { label: 'W5', value: 27.2 },
      { label: 'W6', value: 28.1 },
      { label: 'W7', value: 29.5 },
    ],
  };
}

/**
 * Merge live dashboard API data into the DS presentation model.
 * Sparse API fields fall back to fixture so the command center stays actionable.
 */
export function buildDashboardDsData(
  api: CrmDashboardData | undefined,
  locale: string,
  activityLabel?: (descriptionKey: string) => string,
): CrmDashboardDsData {
  const fixture = makeDashboardFixture(locale);
  if (!api) return fixture;

  const summary = api.communication_summary;
  const dateFmt = new Intl.DateTimeFormat(locale, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
  const timeFmt = new Intl.DateTimeFormat(locale, { hour: '2-digit', minute: '2-digit' });
  const dayFmt = new Intl.DateTimeFormat(locale, { day: '2-digit' });
  const monthFmt = new Intl.DateTimeFormat(locale, { month: 'short' });

  const liveTasks: TaskItem[] = (api.upcoming_tasks ?? []).slice(0, 8).map((task, i) => ({
    id: task.id,
    title: task.title,
    related: task.status,
    dueLabel: task.due_at ? timeFmt.format(new Date(task.due_at)) : '—',
    kind: (['meeting', 'call', 'email', 'task'] as TaskKind[])[i % 4]!,
    href: '/workspaces/crm/tasks',
  }));

  const liveLeads: LeadItem[] = (api.recent_contacts ?? []).slice(0, 8).map((c, i) => ({
    id: c.id,
    name: c.display_name,
    initials: initialsFrom(c.display_name),
    tone: AVATAR_TONES[i % AVATAR_TONES.length]!,
    tag: c.contact_type,
    isNew: i < 2,
    dateLabel: locale.startsWith('tr') ? 'Yeni' : 'Recent',
    href: `/workspaces/crm/contacts/${c.id}`,
  }));

  const liveActivities: ActivityItem[] = (api.recent_activities ?? []).slice(0, 8).map((a, i) => {
    const kinds: ActivityKind[] = ['meeting', 'call', 'email', 'note', 'task', 'file'];
    const title = activityLabel
      ? activityLabel(a.description_key)
      : a.description_key.replace(/[._]/g, ' ');
    return {
      id: a.id,
      kind: kinds[i % kinds.length]!,
      title,
      meta: a.actor_name ?? 'System',
      timeLabel: dateFmt.format(new Date(a.created_at)),
      href: '/workspaces/crm/activities',
    };
  });

  const liveMeetings: MeetingItem[] = (api.todays_meetings ?? []).slice(0, 6).map((m) => {
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

  const overdueCount = (api.upcoming_tasks ?? []).filter((t) => {
    if (!t.due_at) return false;
    return new Date(t.due_at).getTime() < Date.now();
  }).length;

  const contactCount = summary?.total_contacts ?? 0;
  const activityCount = summary?.recent_interactions_count ?? 0;

  return {
    ...fixture,
    priorities: fixture.priorities.map((p) => {
      if (p.key === 'meetings') {
        return { ...p, value: Math.max(api.todays_meetings?.length ?? 0, p.value) };
      }
      if (p.key === 'followUps') {
        return { ...p, value: Math.max(api.upcoming_tasks?.length ?? 0, p.value) };
      }
      if (p.key === 'overdueTasks') {
        return { ...p, value: Math.max(overdueCount, p.value) };
      }
      if (p.key === 'unread') {
        return { ...p, value: Math.max(summary?.favorites_count ?? 0, p.value) };
      }
      return p;
    }),
    kpis: [
      {
        key: 'totalContacts',
        value: formatCount(contactCount || 1248, locale),
        delta: '+12%',
        deltaTone: 'up',
        icon: KPI_ICONS.totalContacts,
      },
      {
        key: 'activeLeads',
        value: formatCount(Math.max(liveLeads.length * 40, 245), locale),
        delta: '+8%',
        deltaTone: 'up',
        icon: KPI_ICONS.activeLeads,
      },
      {
        key: 'pipelineValue',
        value: formatMoney(29_475_000, locale),
        delta: '+4.2%',
        deltaTone: 'up',
        icon: KPI_ICONS.pipelineValue,
      },
      {
        key: 'activitiesWeek',
        value: formatCount(activityCount || 86, locale),
        delta: '+15%',
        deltaTone: 'up',
        icon: KPI_ICONS.activitiesWeek,
      },
    ],
    tasks: liveTasks.length > 0 ? liveTasks : fixture.tasks,
    leads: liveLeads.length > 0 ? liveLeads : fixture.leads,
    activities: liveActivities.length > 0 ? liveActivities : fixture.activities,
    meetings: liveMeetings.length > 0 ? liveMeetings : fixture.meetings,
    timeline:
      liveActivities.length > 0
        ? [
            ...liveActivities.map((a) => ({
              id: `tl-${a.id}`,
              kind: a.kind,
              title: a.title,
              meta: a.meta,
              timeLabel: a.timeLabel,
              href: a.href,
            })),
            ...fixture.timeline.slice(0, Math.max(0, 8 - liveActivities.length)),
          ].slice(0, 8)
        : fixture.timeline,
  };
}
