import type {
  ActivityPriorityKey,
  ActivityRow,
  ActivityStatusKey,
  ActivityTypeKey,
  ActivityWorkspacePreview,
} from '@/app/workspaces/crm/activities/activities-model';
import type {
  CalendarEvent,
  CalendarEventTypeKey,
  CalendarWorkspacePreview,
} from '@/app/workspaces/crm/calendar/calendar-model';
import type {
  TaskKanbanColumnKey,
  TaskPriorityKey,
  TaskRow,
  TaskStatusKey,
  TaskWorkspacePreview,
} from '@/app/workspaces/crm/tasks/tasks-model';
import type {
  CompanyCategoryKey,
  CompanyRelationKey,
  CompanyRow,
  CompanyStatusKey,
  CompanyWorkspacePreview,
} from '@/app/workspaces/crm/companies/companies-model';
import type {
  PeopleRow,
  PeopleWorkspacePreview,
} from '@/app/workspaces/crm/people/people-model';
import type {
  CrmActivitySummary,
  CrmActivityType,
  CrmCalendarEvent,
} from '@/workspaces/crm/types/activities';
import type { CrmCompanyListItem, CrmContactSummary } from '@/workspaces/crm/types';

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return '—';
  return parts
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('');
}

function startOfDay(value: Date): Date {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate());
}

function mondayOf(value: Date): Date {
  const date = startOfDay(value);
  const day = date.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  date.setDate(date.getDate() + diff);
  return date;
}

export function toDateIso(value: Date): string {
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${value.getFullYear()}-${month}-${day}`;
}

function parseStamp(value: string | null | undefined): Date | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatStamp(value: string | null | undefined): string {
  const date = parseStamp(value);
  if (!date) return '—';
  return date.toLocaleString('tr-TR', { dateStyle: 'short', timeStyle: 'short' });
}

function mapActivityType(type: CrmActivityType): ActivityTypeKey {
  switch (type) {
    case 'phone_call':
      return 'phone';
    case 'whatsapp':
      return 'whatsapp';
    case 'email':
      return 'email';
    case 'sms':
      return 'sms';
    case 'meeting':
    case 'investor_meeting':
    case 'construction_meeting':
    case 'site_visit':
    case 'property_tour':
      return 'meeting';
    case 'zoom_meeting':
    case 'teams_meeting':
      return 'videoCall';
    case 'document_sent':
    case 'document_received':
      return 'documentShared';
    case 'note':
    case 'comment':
      return 'note';
    default:
      return 'note';
  }
}

function mapActivityStatus(status: string, taskStatus?: string | null): ActivityStatusKey {
  if (status === 'completed' || taskStatus === 'completed') return 'completed';
  if (status === 'cancelled' || status === 'missed') return 'cancelled';
  if (status === 'in_progress') return 'inProgress';
  return 'pending';
}

function mapActivityPriority(priority: string): ActivityPriorityKey {
  if (priority === 'low' || priority === 'medium' || priority === 'high' || priority === 'critical') {
    return priority;
  }
  return 'medium';
}

function projectTone(name: string): ActivityRow['projectTone'] {
  if (!name || name === '—') return 'slate';
  const tones: ActivityRow['projectTone'][] = ['navy', 'cyan', 'green', 'amber', 'slate'];
  return tones[name.length % tones.length] ?? 'slate';
}

export function mapActivityRow(item: CrmActivitySummary): ActivityRow {
  const customer = item.entity_name || '—';
  const salesRep = item.assigned_user_name || item.created_by_name || item.owner_name || '—';
  const occurred = item.start_date || item.due_date || item.created_at;
  const summary = item.summary || item.title;
  return {
    id: item.id,
    type: mapActivityType(item.activity_type),
    titleKey: item.activity_type,
    title: item.title,
    descriptionKey: item.activity_type,
    description: summary,
    customer,
    customerId: item.entity_type === 'contact' ? item.entity_id : undefined,
    customerDetail: item.activity_type.replaceAll('_', ' '),
    project: item.related_entity_name || '—',
    projectTone: projectTone(item.related_entity_name || ''),
    salesRep,
    salesRepInitials: initials(salesRep),
    dateTime: formatStamp(occurred),
    occurredAt: occurred,
    status: mapActivityStatus(item.status, item.task_status),
    priority: mapActivityPriority(item.priority),
    aiSummaryKey: item.id,
    aiSummary: summary,
  };
}

export function buildActivitiesPreview(items: CrmActivitySummary[], total: number): ActivityWorkspacePreview {
  const now = new Date();
  const today = startOfDay(now).getTime();
  const rows = items.map(mapActivityRow);
  const completed = rows.filter((row) => row.status === 'completed').length;
  const pending = rows.filter((row) => row.status === 'pending' || row.status === 'inProgress').length;
  const overdue = items.filter((item) => {
    const due = parseStamp(item.due_date);
    return Boolean(due && due.getTime() < now.getTime() && item.status !== 'completed' && item.task_status !== 'completed');
  }).length;
  const todayCount = items.filter((item) => {
    const stamp = parseStamp(item.start_date || item.due_date || item.created_at);
    return Boolean(stamp && startOfDay(stamp).getTime() === today);
  }).length;
  const customers = [...new Set(rows.map((row) => row.customer).filter((name) => name && name !== '—'))];
  const salesReps = [...new Set(rows.map((row) => row.salesRep).filter((name) => name && name !== '—'))];
  const projects = [...new Set(rows.map((row) => row.project).filter((name) => name && name !== '—'))];
  const upcomingMeetings = items
    .filter((item) => ['meeting', 'zoom_meeting', 'teams_meeting', 'investor_meeting', 'site_visit'].includes(item.activity_type))
    .slice(0, 4)
    .map((item) => ({
      id: item.id,
      title: item.title,
      customer: item.entity_name || '—',
      time: formatStamp(item.start_date || item.due_date),
    }));
  const recentNotes = items
    .filter((item) => item.activity_type === 'note' || item.activity_category === 'note')
    .slice(0, 4)
    .map((item) => ({
      id: item.id,
      author: item.created_by_name || item.assigned_user_name || '—',
      bodyKey: item.id,
      body: item.summary || item.title,
      timeKey: item.created_at,
      time: formatStamp(item.created_at),
    }));

  return {
    totalActivities: total,
    kpis: [
      { key: 'today', value: todayCount, delta: '', deltaTone: 'neutral', hintKey: 'todayHint' },
      { key: 'completed', value: completed, delta: '', deltaTone: 'up', hintKey: 'completedHint' },
      { key: 'pending', value: pending, delta: '', deltaTone: 'neutral', hintKey: 'pendingHint' },
      { key: 'overdue', value: overdue, delta: '', deltaTone: 'down', hintKey: 'overdueHint' },
    ],
    daySummary: {
      completed,
      pending,
      overdue,
      assessmentKey: 'dayAssessment',
    },
    activities: rows,
    customers,
    salesReps,
    projects,
    overdueFollowUps: items
      .filter((item) => item.activity_type === 'follow_up' && item.status !== 'completed')
      .slice(0, 4)
      .map((item) => ({
        id: item.id,
        customer: item.entity_name || '—',
        daysOverdue: Math.max(
          0,
          Math.floor((now.getTime() - (parseStamp(item.due_date)?.getTime() ?? now.getTime())) / 86_400_000),
        ),
      })),
    upcomingMeetings,
    aiRecommendations: [],
    recentNotes,
  };
}

function mapTaskStatus(taskStatus: string | null, status: string): TaskStatusKey {
  if (taskStatus === 'completed' || status === 'completed') return 'completed';
  if (taskStatus === 'in_progress' || status === 'in_progress') return 'inProgress';
  if (taskStatus === 'waiting') return 'waiting';
  if (taskStatus === 'cancelled' || status === 'cancelled') return 'cancelled';
  return 'open';
}

function mapKanban(status: TaskStatusKey): TaskKanbanColumnKey {
  if (status === 'inProgress') return 'inProgress';
  if (status === 'waiting') return 'review';
  if (status === 'completed') return 'completed';
  return 'todo';
}

function dueTone(due: Date | null, status: TaskStatusKey): TaskRow['dueTone'] {
  if (status === 'completed') return 'done';
  if (!due) return 'neutral';
  const today = startOfDay(new Date()).getTime();
  const dueDay = startOfDay(due).getTime();
  if (dueDay < today) return 'overdue';
  if (dueDay === today) return 'today';
  if (dueDay - today <= 86_400_000 * 2) return 'soon';
  return 'neutral';
}

export function mapTaskRow(item: CrmActivitySummary): TaskRow {
  const customer = item.entity_name || '—';
  const assignee = item.assigned_user_name || item.owner_name || '—';
  const due = parseStamp(item.due_date);
  const status = mapTaskStatus(item.task_status, item.status);
  const note = item.summary || item.title;
  return {
    id: item.id,
    titleKey: item.id,
    title: item.title,
    descriptionKey: item.id,
    description: item.summary || item.title,
    customer,
    customerId: item.entity_type === 'contact' ? item.entity_id : undefined,
    project: item.related_entity_name || '—',
    dueLabelKey: item.id,
    dueLabel: due ? formatStamp(item.due_date) : '—',
    dueTone: dueTone(due, status),
    priority: mapActivityPriority(item.priority) as TaskPriorityKey,
    status,
    kanbanColumn: mapKanban(status),
    assignee,
    assigneeId: item.assigned_user_id ?? undefined,
    assigneeInitials: initials(assignee),
    tag: item.activity_type,
    aiNoteKey: item.id,
    aiNote: note,
  };
}

export function buildTasksPreview(items: CrmActivitySummary[], total: number): TaskWorkspacePreview {
  const now = new Date();
  const today = startOfDay(now).getTime();
  const rows = items.map(mapTaskRow);
  const open = rows.filter((row) => row.status !== 'completed' && row.status !== 'cancelled').length;
  const dueToday = items.filter((item) => {
    const due = parseStamp(item.due_date);
    return Boolean(due && startOfDay(due).getTime() === today && item.task_status !== 'completed');
  }).length;
  const overdue = rows.filter((row) => row.dueTone === 'overdue').length;
  const completed = rows.filter((row) => row.status === 'completed').length;
  return {
    totalTasks: total,
    kpis: [
      { key: 'open', value: open, delta: '', deltaTone: 'neutral', hintKey: 'openHint' },
      { key: 'dueToday', value: dueToday, delta: '', deltaTone: 'neutral', hintKey: 'dueTodayHint' },
      { key: 'overdue', value: overdue, delta: '', deltaTone: 'down', hintKey: 'overdueHint' },
      { key: 'completed', value: completed, delta: '', deltaTone: 'up', hintKey: 'completedHint' },
    ],
    daySummary: {
      open,
      dueToday,
      overdue,
      assessmentKey: 'dayAssessment',
    },
    tasks: rows,
    customers: [...new Set(rows.map((row) => row.customer).filter((name) => name !== '—'))],
    assignees: [...new Set(rows.map((row) => row.assignee).filter((name) => name !== '—'))],
    projects: [...new Set(rows.map((row) => row.project).filter((name) => name !== '—'))],
    tags: [...new Set(rows.map((row) => row.tag).filter(Boolean))],
    todayPriorities: rows
      .filter((row) => row.dueTone === 'today' || row.priority === 'critical' || row.priority === 'high')
      .slice(0, 5)
      .map((row) => ({ id: row.id, titleKey: row.id, title: row.title, dueLabelKey: row.id, dueLabel: row.dueLabel })),
    upcomingDeadlines: rows
      .filter((row) => row.dueTone === 'soon' || row.dueTone === 'today')
      .slice(0, 5)
      .map((row) => ({ id: row.id, titleKey: row.id, title: row.title, dueLabelKey: row.id, dueLabel: row.dueLabel })),
    aiRecommendations: [],
    teamPerformance: [],
  };
}

function mapCalendarType(type: string): CalendarEventTypeKey {
  switch (type) {
    case 'phone_call':
      return 'phone';
    case 'task':
    case 'reminder':
      return 'task';
    case 'site_visit':
    case 'property_tour':
    case 'inspection':
      return 'siteVisit';
    case 'investor_meeting':
      return 'investorMeeting';
    case 'document_sent':
    case 'document_received':
      return 'documentHandoff';
    case 'internal_discussion':
      return 'internalMeeting';
    default:
      return 'meeting';
  }
}

export function mapCalendarEvent(item: CrmCalendarEvent, weekStart: Date): CalendarEvent {
  const stamp = parseStamp(item.start_date) || parseStamp(item.due_date);
  const date = stamp ?? weekStart;
  const monday = mondayOf(weekStart);
  const dayIndex = Math.max(0, Math.min(6, Math.round((startOfDay(date).getTime() - monday.getTime()) / 86_400_000)));
  const minutes = stamp ? stamp.getHours() * 60 + stamp.getMinutes() : null;
  const startMinute = minutes == null ? null : Math.max(0, minutes - 8 * 60);
  const duration =
    parseStamp(item.start_date) && parseStamp(item.end_date)
      ? Math.max(30, Math.round((parseStamp(item.end_date)!.getTime() - parseStamp(item.start_date)!.getTime()) / 60_000))
      : 60;
  const allDay = item.all_day || (!item.start_date && Boolean(item.due_date));
  return {
    id: item.id,
    titleKey: item.id,
    title: item.title,
    customer: item.entity_name || '—',
    customerId: item.entity_type === 'contact' ? item.entity_id : undefined,
    project: item.assigned_user_name || '—',
    type: mapCalendarType(item.activity_type),
    activityType: item.activity_type,
    dayIndex,
    dateIso: toDateIso(date),
    startMinute: allDay ? null : startMinute,
    durationMinutes: duration,
    participantCount: 0,
    allDay,
  };
}

export function buildCalendarPreview(events: CrmCalendarEvent[], weekStart = mondayOf(new Date())): CalendarWorkspacePreview {
  const now = new Date();
  const mapped = events.map((event) => mapCalendarEvent(event, weekStart));
  const todayIso = toDateIso(now);
  const weekEnd = new Date(weekStart);
  weekEnd.setDate(weekEnd.getDate() + 7);
  const todayEvents = mapped.filter((event) => event.dateIso === todayIso).length;
  const thisWeek = mapped.filter((event) => {
    if (!event.dateIso) return false;
    return event.dateIso >= toDateIso(weekStart) && event.dateIso < toDateIso(weekEnd);
  }).length;
  const meetings = events.filter((event) => event.activity_type.includes('meeting')).length;
  const completed = events.filter((event) => event.status === 'completed').length;
  const nowMinute = Math.max(0, now.getHours() * 60 + now.getMinutes() - 8 * 60);
  return {
    weekStartIso: toDateIso(weekStart),
    currentDayIndex: Math.max(0, Math.min(6, Math.round((startOfDay(now).getTime() - weekStart.getTime()) / 86_400_000))),
    nowMinute,
    rangeLabelKey: 'jul21to27',
    rangeLabel: `${toDateIso(weekStart)}`,
    kpis: [
      { key: 'todayEvents', value: String(todayEvents), hintKey: 'todayEventsHint' },
      { key: 'thisWeek', value: String(thisWeek), hintKey: 'thisWeekHint' },
      { key: 'upcomingMeetings', value: String(meetings), hintKey: 'upcomingMeetingsHint' },
      { key: 'completed', value: String(completed), hintKey: 'completedHint' },
      { key: 'attendanceRate', value: '—', hintKey: 'attendanceRateHint' },
    ],
    events: mapped,
    upcoming: mapped.slice(0, 6).map((event) => ({
      id: event.id,
      titleKey: event.id,
      title: event.title,
      timeLabel: event.dateIso ?? '',
      when: event.dateIso === todayIso ? 'today' : 'later',
      type: event.type,
    })),
    aiSuggestions: [],
    sync: [],
  };
}

export function matchesDateFilter(iso: string | undefined, filter: string): boolean {
  if (!filter || !iso) return !filter;
  const stamp = parseStamp(iso);
  if (!stamp) return false;
  const now = Date.now();
  const age = now - stamp.getTime();
  if (filter === 'today') return startOfDay(stamp).getTime() === startOfDay(new Date()).getTime();
  if (filter === '7d' || filter === 'soon') return age <= 7 * 86_400_000 && age >= -2 * 86_400_000;
  if (filter === '30d') return age <= 30 * 86_400_000;
  if (filter === '90d') return age <= 90 * 86_400_000;
  if (filter === 'overdue') return stamp.getTime() < now;
  return true;
}

function mapCompanyCategory(type: string): CompanyCategoryKey {
  switch (type) {
    case 'investment_company':
      return 'investor';
    case 'brokerage':
      return 'broker';
    case 'law_firm':
      return 'legal';
    case 'bank':
    case 'lender':
      return 'bank';
    case 'architecture':
      return 'architecture';
    case 'construction':
    case 'contractor':
      return 'developer';
    case 'partner':
      return 'partner';
    default:
      return 'partner';
  }
}

function mapCompanyStatus(status: string): CompanyStatusKey {
  if (status === 'prospect' || status === 'inactive' || status === 'archived') return status;
  return 'active';
}

function mapCompanyRelation(status: string): CompanyRelationKey {
  if (status === 'vendor' || status === 'client' || status === 'investor') return status;
  if (status === 'advisor') return 'advisor';
  return 'strategicPartner';
}

export function mapCompanyRow(item: CrmCompanyListItem): CompanyRow {
  const phoneEmail = [item.primary_phone, item.primary_email].filter(Boolean).join(' · ') || '—';
  return {
    id: item.id,
    name: item.display_name,
    subtitleKey: 'templeSubtitle',
    subtitle: item.legal_name || item.industry || item.company_type.replace(/_/g, ' '),
    initials: initials(item.display_name),
    logoTone: 'navy',
    category: mapCompanyCategory(item.company_type),
    country: 'tr',
    contactName: phoneEmail,
    contactRoleKey: 'managingPartner',
    contactDetail: item.relationship_status || undefined,
    contactInitials: initials(phoneEmail === '—' ? item.display_name : phoneEmail),
    openProjects: item.contact_count ?? 0,
    lastActivityKey: 'call',
    lastActivityLabel: 'Güncellendi',
    lastActivityDate: formatStamp(item.updated_at),
    healthScore: 50,
    health: 'medium',
    aiSummaryKey: 'kw',
    aiSummary: `${item.contact_count ?? 0} ilgili kişi`,
    status: mapCompanyStatus(item.status),
    relation: mapCompanyRelation(item.relationship_status),
    owner: '—',
    tags: item.tags ?? [],
  };
}

export function buildCompaniesPreview(
  items: CrmCompanyListItem[],
  total = items.length,
  pageSize = 20,
): CompanyWorkspacePreview {
  const companies = items.map(mapCompanyRow);
  const active = companies.filter((row) => row.status === 'active').length;
  const investors = companies.filter((row) => row.category === 'investor').length;
  return {
    totalCompanies: total,
    totalPages: Math.max(1, Math.ceil(total / pageSize)),
    kpis: [
      { key: 'total', value: total, hintKey: 'totalHint', delta: '—', deltaTone: 'neutral' },
      { key: 'activePartners', value: active, hintKey: 'activePartnersHint', delta: '—', deltaTone: 'neutral' },
      { key: 'investors', value: investors, hintKey: 'investorsHint', delta: '—', deltaTone: 'neutral' },
      { key: 'newThisMonth', value: 0, hintKey: 'newThisMonthHint', delta: '—', deltaTone: 'neutral' },
      { key: 'openCollaborations', value: companies.reduce((sum, row) => sum + row.openProjects, 0), hintKey: 'openCollaborationsHint', delta: '—', deltaTone: 'neutral' },
    ],
    companies,
    recentCompanies: companies.slice(0, 4).map((row) => ({
      id: row.id,
      name: row.name,
      initials: row.initials,
      logoTone: row.logoTone,
      addedAtKey: 'yesterday',
    })),
    upcomingMeetings: [],
    recommendations: [],
    categoryDistribution: COMPANY_CATEGORY_SLICES(companies),
    activePartners: companies.slice(0, 4).map((row) => ({
      id: row.id,
      name: row.name,
      initials: row.initials,
      logoTone: row.logoTone,
      activityCount: row.openProjects,
      lastContactKey: 'daysAgo1',
    })),
    owners: [],
    tags: Array.from(new Set(companies.flatMap((row) => row.tags))),
    countries: ['tr'],
  };
}

function COMPANY_CATEGORY_SLICES(companies: CompanyRow[]): CompanyWorkspacePreview['categoryDistribution'] {
  const counts = new Map<string, number>();
  for (const row of companies) {
    counts.set(row.category, (counts.get(row.category) ?? 0) + 1);
  }
  const total = Math.max(companies.length, 1);
  return Array.from(counts.entries()).map(([key, count]) => ({
    key: key as CompanyCategoryKey,
    pct: Math.round((count / total) * 100),
  }));
}

export function mapInvestorRow(item: CrmContactSummary): PeopleRow {
  const projects = item.agreement_projects?.join(', ') || '—';
  return {
    id: item.id,
    name: item.display_name,
    titleKey: 'investmentLead',
    title: item.job_title || 'Yatırımcı',
    initials: initials(item.display_name),
    avatarTone: 'navy',
    company: projects,
    companyInitials: initials(projects === '—' ? item.display_name : projects),
    companyTone: 'cyan',
    role: 'investor',
    department: 'investment',
    country: 'tr',
    hasEmail: Boolean(item.primary_email),
    hasPhone: Boolean(item.primary_phone),
    hasLinkedIn: false,
    hasWhatsApp: Boolean(item.whatsapp),
    lastActivityKey: 'call',
    lastActivityLabel: item.last_contact_at ? 'Son aktivite' : 'Aktivite yok',
    lastActivityDate: formatStamp(item.last_contact_at),
    relationScore: Math.round(item.relationship_score || 0),
    relation: item.has_agreements ? 'strong' : 'medium',
    aiNoteKey: 'noteElif',
    aiNote: projects === '—' ? 'Anlaşma ilişkisi' : projects,
    owner: item.owner_name || item.bitrix_responsible || '—',
    tags: item.tags ?? [],
  };
}

export function buildInvestorsPreview(
  items: CrmContactSummary[],
  total = items.length,
  pageSize = 20,
): PeopleWorkspacePreview {
  const people = items.map(mapInvestorRow);
  return {
    totalPeople: total,
    totalPages: Math.max(1, Math.ceil(total / pageSize)),
    kpis: [
      { key: 'total', value: total, hintKey: 'totalHint', delta: '—', deltaTone: 'neutral' },
      { key: 'active', value: people.filter((row) => row.hasPhone || row.hasEmail).length, hintKey: 'activeHint', delta: '—', deltaTone: 'neutral' },
      { key: 'decisionMakers', value: total, hintKey: 'decisionMakersHint', delta: '—', deltaTone: 'neutral' },
      { key: 'newThisMonth', value: 0, hintKey: 'newThisMonthHint', delta: '—', deltaTone: 'neutral' },
      { key: 'meetingPending', value: 0, hintKey: 'meetingPendingHint', delta: '—', deltaTone: 'neutral' },
    ],
    people,
    recentPeople: people.slice(0, 4).map((row) => ({
      id: row.id,
      name: row.name,
      company: row.company,
      initials: row.initials,
      avatarTone: row.avatarTone,
      addedAtKey: 'yesterday',
    })),
    upcomingMeetings: [],
    sourceDistribution: [{ key: 'referral', pct: 100 }],
    activePeople: people.slice(0, 4).map((row) => ({
      id: row.id,
      name: row.name,
      initials: row.initials,
      avatarTone: row.avatarTone,
      lastContactLabel: row.lastActivityDate,
    })),
    owners: Array.from(new Set(people.map((row) => row.owner).filter((name) => name && name !== '—'))),
    tags: Array.from(new Set(people.flatMap((row) => row.tags))),
    companies: Array.from(new Set(people.map((row) => row.company))),
    countries: ['tr'],
  };
}
