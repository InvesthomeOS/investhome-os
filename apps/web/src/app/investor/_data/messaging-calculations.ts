import { getAllAnnouncements } from './announcements';
import { getAllConversations, getVisibleMessages } from './conversations';
import { getAllInvestorNotifications } from './investor-notifications';
import { getAllTasks } from './investor-tasks';
import type {
  Announcement,
  Conversation,
  ConversationFilterState,
  ConversationSortState,
  InvestorNotificationItem,
  MessageCategory,
  MessagesSummaryKpis,
  MessagingSearchResult,
  SidebarMessagingBadges,
  Task,
  TaskFilterState,
  TaskSortState,
  TasksSummaryKpis,
} from './messaging-types';

export interface ConversationOverrides {
  isRead?: boolean;
  isArchived?: boolean;
  isStarred?: boolean;
  isDeleted?: boolean;
  status?: Conversation['status'];
  unreadCount?: number;
}

export interface MessageOverrides {
  isRead?: boolean;
  isPinned?: boolean;
}

export interface AnnouncementOverrides {
  isRead?: boolean;
}

export interface NotificationOverrides {
  isRead?: boolean;
  isDismissed?: boolean;
}

export interface TaskOverrides {
  status?: Task['status'];
  checklistItems?: Record<string, boolean>;
  comments?: Task['comments'];
}

const PRIORITY_ORDER = { urgent: 0, high: 1, normal: 2, low: 3 };
const TASK_PRIORITY_ORDER = { critical: 0, high: 1, medium: 2, low: 3 };

function startOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

function isToday(dateStr: string): boolean {
  const d = new Date(dateStr);
  const today = startOfDay(new Date('2025-07-16'));
  return startOfDay(d).getTime() === today.getTime();
}

function isThisWeek(dateStr: string): boolean {
  const d = new Date(dateStr);
  const today = new Date('2025-07-16');
  const weekEnd = new Date(today);
  weekEnd.setDate(weekEnd.getDate() + 7);
  return d >= startOfDay(today) && d <= weekEnd;
}

function isOverdue(dateStr: string): boolean {
  return new Date(dateStr) < startOfDay(new Date('2025-07-16'));
}

export function mergeConversations(
  conversationOverrides: Record<string, ConversationOverrides>,
  messageOverrides: Record<string, MessageOverrides>,
): Conversation[] {
  return getAllConversations()
    .filter((c) => !conversationOverrides[c.id]?.isDeleted)
    .map((conv) => {
      const override = conversationOverrides[conv.id] ?? {};
      const messages = conv.messages.map((m) => ({
        ...m,
        ...(messageOverrides[m.id] ?? {}),
      }));
      const visible = messages.filter((m) => !m.isInternal);
      const unreadCount =
        override.unreadCount ??
        visible.filter((m) => !m.isRead && !m.author.isInvestor).length;
      return {
        ...conv,
        ...override,
        messages,
        isStarred: override.isStarred ?? conv.isStarred,
        status: override.isArchived ? 'archived' : (override.status ?? conv.status),
        unreadCount,
      };
    });
}

export function mergeAnnouncements(
  overrides: Record<string, AnnouncementOverrides>,
): Announcement[] {
  return getAllAnnouncements().map((a) => ({
    ...a,
    isRead: overrides[a.id]?.isRead ?? a.isRead,
  }));
}

export function mergeNotifications(
  overrides: Record<string, NotificationOverrides>,
): InvestorNotificationItem[] {
  return getAllInvestorNotifications()
    .filter((n) => !(overrides[n.id]?.isDismissed ?? n.isDismissed))
    .map((n) => ({
      ...n,
      isRead: overrides[n.id]?.isRead ?? n.isRead,
      isDismissed: overrides[n.id]?.isDismissed ?? n.isDismissed,
    }));
}

export function mergeTasks(overrides: Record<string, TaskOverrides>): Task[] {
  return getAllTasks().map((task) => {
    const override = overrides[task.id];
    if (!override) return task;

    let checklist = task.checklist;
    if (override.checklistItems) {
      checklist = {
        ...task.checklist,
        items: task.checklist.items.map((item) => ({
          ...item,
          isCompleted: override.checklistItems?.[item.id] ?? item.isCompleted,
          completedAt:
            override.checklistItems?.[item.id] && !item.isCompleted
              ? new Date().toISOString()
              : item.completedAt,
        })),
      };
    }

    const completed = checklist.items.filter((i) => i.isCompleted).length;
    const total = checklist.items.length;
    const progressPercent = total > 0 ? Math.round((completed / total) * 100) : task.progressPercent;

    return {
      ...task,
      status: override.status ?? task.status,
      checklist,
      comments: override.comments ?? task.comments,
      progressPercent,
      completedAt:
        override.status === 'completed' && !task.completedAt
          ? new Date().toISOString()
          : task.completedAt,
    };
  });
}

export function computeMessagesSummary(
  conversations: Conversation[],
  announcements: Announcement[],
  notifications: InvestorNotificationItem[],
  tasks: Task[],
): MessagesSummaryKpis {
  const unreadMessages = conversations.reduce((sum, c) => sum + c.unreadCount, 0);
  return {
    totalConversations: conversations.filter((c) => c.status !== 'archived').length,
    unreadMessages,
    starredConversations: conversations.filter((c) => c.isStarred).length,
    pendingResponses: conversations.filter(
      (c) => c.unreadCount > 0 && c.status === 'active',
    ).length,
    unreadAnnouncements: announcements.filter((a) => !a.isRead).length,
    unreadNotifications: notifications.filter((n) => !n.isRead).length,
    openTasks: tasks.filter((t) => t.status === 'open' || t.status === 'in_progress' || t.status === 'overdue').length,
  };
}

export function computeTasksSummary(tasks: Task[]): TasksSummaryKpis {
  const openStatuses: Task['status'][] = ['open', 'in_progress', 'pending_review', 'overdue'];
  const open = tasks.filter((t) => openStatuses.includes(t.status)).length;
  return {
    open,
    dueToday: tasks.filter((t) => openStatuses.includes(t.status) && isToday(t.dueDate)).length,
    dueThisWeek: tasks.filter((t) => openStatuses.includes(t.status) && isThisWeek(t.dueDate)).length,
    completed: tasks.filter((t) => t.status === 'completed').length,
    overdue: tasks.filter((t) => t.status === 'overdue' || (openStatuses.includes(t.status) && isOverdue(t.dueDate))).length,
    highPriority: tasks.filter(
      (t) => openStatuses.includes(t.status) && (t.priority === 'high' || t.priority === 'critical'),
    ).length,
    pendingDocuments: tasks.filter(
      (t) => openStatuses.includes(t.status) && (t.category === 'document_upload' || t.category === 'signature'),
    ).length,
  };
}

export function computeSidebarBadges(
  conversations: Conversation[],
  tasks: Task[],
): SidebarMessagingBadges {
  const unreadMessages = conversations.reduce((sum, c) => sum + c.unreadCount, 0);
  const openTasks = tasks.filter(
    (t) => t.status === 'open' || t.status === 'in_progress' || t.status === 'overdue',
  ).length;
  return { unreadMessages, openTasks };
}

const CATEGORY_MAP: Record<MessageCategory, (c: Conversation) => boolean> = {
  inbox: (c) => c.category === 'inbox' && c.status !== 'archived',
  announcements: (c) => c.messageType === 'announcement' || c.category === 'announcements',
  project_updates: (c) =>
    c.messageType === 'project_update' || c.messageType === 'construction_update',
  financial: (c) =>
    c.messageType === 'financial_update' ||
    c.messageType === 'distribution_notice' ||
    c.messageType === 'tax_notice',
  documents: (c) => c.messageType === 'document_request' || c.messageType === 'legal_notice',
  signatures: (c) => c.messageType === 'signature_request',
  support: (c) => c.messageType === 'general_support' || c.type === 'support',
  archived: (c) => c.status === 'archived',
  starred: (c) => c.isStarred,
  unread: (c) => c.unreadCount > 0,
  all: () => true,
};

export function filterConversations(
  conversations: Conversation[],
  filters: ConversationFilterState,
): Conversation[] {
  let result = [...conversations];

  if (filters.category !== 'all') {
    const predicate = CATEGORY_MAP[filters.category];
    result = result.filter(predicate);
  }

  if (filters.search.trim()) {
    const q = filters.search.toLowerCase();
    result = result.filter(
      (c) =>
        c.subject.toLowerCase().includes(q) ||
        c.investmentName.toLowerCase().includes(q) ||
        c.irMember.name.toLowerCase().includes(q) ||
        getVisibleMessages(c).some((m) => m.body.toLowerCase().includes(q)),
    );
  }

  if (filters.investmentId !== 'all') {
    result = result.filter((c) => c.investmentId === filters.investmentId);
  }

  if (filters.status !== 'all') {
    result = result.filter((c) => c.status === filters.status);
  }

  if (filters.unreadOnly) {
    result = result.filter((c) => c.unreadCount > 0);
  }

  if (filters.archivedOnly) {
    result = result.filter((c) => c.status === 'archived');
  } else if (filters.category !== 'archived') {
    result = result.filter((c) => c.status !== 'archived' || filters.category === 'all');
  }

  if (filters.priority !== 'all') {
    result = result.filter((c) => c.priority === filters.priority);
  }

  if (filters.hasAttachments === true) {
    result = result.filter((c) => c.hasAttachments);
  }

  if (filters.dateFrom) {
    result = result.filter((c) => c.lastMessageAt >= filters.dateFrom);
  }

  if (filters.dateTo) {
    result = result.filter((c) => c.lastMessageAt <= `${filters.dateTo}T23:59:59Z`);
  }

  return result;
}

export function sortConversations(
  conversations: Conversation[],
  sort: ConversationSortState,
): Conversation[] {
  const sorted = [...conversations];
  const dir = sort.direction === 'asc' ? 1 : -1;

  sorted.sort((a, b) => {
    switch (sort.field) {
      case 'subject':
        return dir * a.subject.localeCompare(b.subject);
      case 'priority':
        return dir * (PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority]);
      case 'unreadCount':
        return dir * (a.unreadCount - b.unreadCount);
      case 'lastMessageAt':
      default:
        return dir * (new Date(a.lastMessageAt).getTime() - new Date(b.lastMessageAt).getTime());
    }
  });

  return sorted;
}

export function filterTasks(tasks: Task[], filters: TaskFilterState): Task[] {
  let result = [...tasks];

  if (filters.search.trim()) {
    const q = filters.search.toLowerCase();
    result = result.filter(
      (t) =>
        t.title.toLowerCase().includes(q) ||
        t.description.toLowerCase().includes(q) ||
        t.investmentName.toLowerCase().includes(q),
    );
  }

  if (filters.investmentId !== 'all') {
    result = result.filter((t) => t.investmentId === filters.investmentId);
  }

  if (filters.status !== 'all') {
    result = result.filter((t) => t.status === filters.status);
  }

  if (filters.priority !== 'all') {
    result = result.filter((t) => t.priority === filters.priority);
  }

  if (filters.category !== 'all') {
    result = result.filter((t) => t.category === filters.category);
  }

  if (filters.dueFrom) {
    result = result.filter((t) => t.dueDate >= filters.dueFrom);
  }

  if (filters.dueTo) {
    result = result.filter((t) => t.dueDate <= filters.dueTo);
  }

  return result;
}

export function sortTasks(tasks: Task[], sort: TaskSortState): Task[] {
  const sorted = [...tasks];
  const dir = sort.direction === 'asc' ? 1 : -1;

  sorted.sort((a, b) => {
    switch (sort.field) {
      case 'title':
        return dir * a.title.localeCompare(b.title);
      case 'priority':
        return dir * (TASK_PRIORITY_ORDER[a.priority] - TASK_PRIORITY_ORDER[b.priority]);
      case 'status':
        return dir * a.status.localeCompare(b.status);
      case 'updatedAt':
        return dir * (new Date(a.updatedAt).getTime() - new Date(b.updatedAt).getTime());
      case 'dueDate':
      default:
        return dir * (new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime());
    }
  });

  return sorted;
}

export function globalMessagingSearch(
  conversations: Conversation[],
  announcements: Announcement[],
  notifications: InvestorNotificationItem[],
  tasks: Task[],
  query: string,
): MessagingSearchResult[] {
  if (!query.trim()) return [];
  const q = query.toLowerCase();
  const results: MessagingSearchResult[] = [];

  for (const c of conversations) {
    if (c.subject.toLowerCase().includes(q) || c.investmentName.toLowerCase().includes(q)) {
      results.push({
        type: 'conversation',
        id: c.id,
        title: c.subject,
        subtitle: c.investmentName,
        href: `/investor/messages/${c.id}`,
        timestamp: c.lastMessageAt,
      });
    }
    for (const m of getVisibleMessages(c)) {
      if (m.body.toLowerCase().includes(q)) {
        results.push({
          type: 'message',
          id: m.id,
          title: m.body.slice(0, 80),
          subtitle: c.subject,
          href: `/investor/messages/${c.id}`,
          timestamp: m.sentAt,
        });
      }
    }
  }

  for (const a of announcements) {
    if (a.title.toLowerCase().includes(q) || a.summary.toLowerCase().includes(q)) {
      results.push({
        type: 'announcement',
        id: a.id,
        title: a.title,
        subtitle: a.category,
        href: '/investor/messages',
        timestamp: a.publishedAt,
      });
    }
  }

  for (const n of notifications) {
    if (n.title.toLowerCase().includes(q) || n.message.toLowerCase().includes(q)) {
      results.push({
        type: 'notification',
        id: n.id,
        title: n.title,
        subtitle: n.category,
        href: n.actionHref ?? '/investor/messages',
        timestamp: n.timestamp,
      });
    }
  }

  for (const t of tasks) {
    if (t.title.toLowerCase().includes(q)) {
      results.push({
        type: 'task',
        id: t.id,
        title: t.title,
        subtitle: t.investmentName,
        href: `/investor/tasks/${t.id}`,
        timestamp: t.updatedAt,
      });
    }
  }

  return results.sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
  );
}

export function getCategoryCounts(conversations: Conversation[]): Record<MessageCategory, number> {
  const counts = {} as Record<MessageCategory, number>;
  const categories: MessageCategory[] = [
    'inbox',
    'announcements',
    'project_updates',
    'financial',
    'documents',
    'signatures',
    'support',
    'archived',
    'starred',
    'unread',
    'all',
  ];
  for (const cat of categories) {
    counts[cat] = filterConversations(conversations, {
      search: '',
      investmentId: 'all',
      category: cat,
      status: 'all',
      unreadOnly: false,
      archivedOnly: cat === 'archived',
      priority: 'all',
      hasAttachments: null,
      dateFrom: '',
      dateTo: '',
    }).length;
  }
  return counts;
}

export const DEFAULT_CONVERSATION_FILTERS: ConversationFilterState = {
  search: '',
  investmentId: 'all',
  category: 'inbox',
  status: 'all',
  unreadOnly: false,
  archivedOnly: false,
  priority: 'all',
  hasAttachments: null,
  dateFrom: '',
  dateTo: '',
};

export const DEFAULT_CONVERSATION_SORT: ConversationSortState = {
  field: 'lastMessageAt',
  direction: 'desc',
};

export const DEFAULT_TASK_FILTERS: TaskFilterState = {
  search: '',
  investmentId: 'all',
  status: 'all',
  priority: 'all',
  category: 'all',
  dueFrom: '',
  dueTo: '',
};

export const DEFAULT_TASK_SORT: TaskSortState = {
  field: 'dueDate',
  direction: 'asc',
};
