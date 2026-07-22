export const MESSAGE_TYPES = [
  'investor_relations',
  'project_update',
  'construction_update',
  'financial_update',
  'distribution_notice',
  'document_request',
  'signature_request',
  'tax_notice',
  'general_support',
  'legal_notice',
  'announcement',
  'system_notification',
] as const;

export type MessageType = (typeof MESSAGE_TYPES)[number];

export const CONVERSATION_TYPES = [
  'direct',
  'project_thread',
  'support',
  'announcement',
] as const;

export type ConversationType = (typeof CONVERSATION_TYPES)[number];

export const CONVERSATION_STATUSES = ['active', 'archived', 'closed'] as const;

export type ConversationStatus = (typeof CONVERSATION_STATUSES)[number];

export const MESSAGE_PRIORITIES = ['low', 'normal', 'high', 'urgent'] as const;

export type MessagePriority = (typeof MESSAGE_PRIORITIES)[number];

export const MESSAGE_CATEGORIES = [
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
] as const;

export type MessageCategory = (typeof MESSAGE_CATEGORIES)[number];

export interface MessageAuthor {
  id: string;
  name: string;
  role: string;
  avatarInitials: string;
  isInvestor: boolean;
  /** Masked email for display — never full PII */
  emailMasked: string;
}

export interface Attachment {
  id: string;
  fileName: string;
  fileType: 'pdf' | 'docx' | 'png' | 'jpeg' | 'xlsx';
  fileSizeBytes: number;
  /** Demo-only — no real download */
  isMock: true;
}

export interface MessageReference {
  type: 'investment' | 'document' | 'signature' | 'distribution' | 'task';
  id: string;
  label: string;
}

export interface Message {
  id: string;
  conversationId: string;
  author: MessageAuthor;
  body: string;
  messageType: MessageType;
  sentAt: string;
  isRead: boolean;
  /** Internal-only notes — never shown in investor UI */
  isInternal: boolean;
  attachments: Attachment[];
  references: MessageReference[];
  isPinned: boolean;
}

export interface TimelineEvent {
  id: string;
  type:
    | 'construction'
    | 'distribution'
    | 'document'
    | 'task'
    | 'signature'
    | 'project_update'
    | 'message';
  title: string;
  description: string;
  timestamp: string;
  referenceId?: string;
}

export interface Conversation {
  id: string;
  subject: string;
  investmentId: string | null;
  investmentName: string;
  type: ConversationType;
  status: ConversationStatus;
  category: MessageCategory;
  messageType: MessageType;
  priority: MessagePriority;
  irMember: MessageAuthor;
  lastMessagePreview: string;
  lastMessageAt: string;
  unreadCount: number;
  hasAttachments: boolean;
  isStarred: boolean;
  messages: Message[];
  timelineEvents: TimelineEvent[];
  relatedTaskIds: string[];
  relatedDocumentIds: string[];
  relatedSignatureIds: string[];
  relatedDistributionIds: string[];
}

export const ANNOUNCEMENT_CATEGORIES = [
  'platform',
  'portfolio',
  'compliance',
  'events',
  'maintenance',
] as const;

export type AnnouncementCategory = (typeof ANNOUNCEMENT_CATEGORIES)[number];

export interface Announcement {
  id: string;
  title: string;
  summary: string;
  body: string;
  category: AnnouncementCategory;
  publishedAt: string;
  expiresAt: string | null;
  isRead: boolean;
  priority: MessagePriority;
  attachments: Attachment[];
  actionLabel: string | null;
  actionHref: string | null;
}

export const NOTIFICATION_CATEGORIES = [
  'distribution',
  'document',
  'signature',
  'message',
  'task',
  'tax',
  'investment',
  'system',
  'compliance',
] as const;

export type NotificationCategory = (typeof NOTIFICATION_CATEGORIES)[number];

export interface InvestorNotificationItem {
  id: string;
  title: string;
  message: string;
  category: NotificationCategory;
  timestamp: string;
  isRead: boolean;
  isDismissed: boolean;
  priority: MessagePriority;
  actionLabel: string | null;
  actionHref: string | null;
  relatedId: string | null;
}

export const TASK_STATUSES = [
  'open',
  'in_progress',
  'pending_review',
  'completed',
  'overdue',
  'cancelled',
] as const;

export type TaskStatus = (typeof TASK_STATUSES)[number];

export const TASK_PRIORITIES = ['low', 'medium', 'high', 'critical'] as const;

export type TaskPriority = (typeof TASK_PRIORITIES)[number];

export const TASK_CATEGORIES = [
  'signature',
  'document_upload',
  'review',
  'compliance',
  'tax',
  'distribution',
  'general',
  'accreditation',
] as const;

export type TaskCategory = (typeof TASK_CATEGORIES)[number];

export interface TaskOwner {
  id: string;
  name: string;
  role: string;
  avatarInitials: string;
  emailMasked: string;
}

export interface TaskChecklistItem {
  id: string;
  label: string;
  isCompleted: boolean;
  completedAt: string | null;
}

export interface TaskChecklist {
  id: string;
  title: string;
  items: TaskChecklistItem[];
}

export interface TaskComment {
  id: string;
  author: TaskOwner;
  body: string;
  createdAt: string;
  /** Internal comments hidden from investor */
  isInternal: boolean;
}

export interface TaskAttachment {
  id: string;
  fileName: string;
  fileType: 'pdf' | 'docx' | 'png' | 'jpeg';
  fileSizeBytes: number;
  uploadedAt: string;
  uploadedBy: string;
  isMock: true;
}

export interface TaskActivity {
  id: string;
  type: 'created' | 'updated' | 'comment' | 'status_change' | 'attachment' | 'reminder';
  description: string;
  actor: string;
  timestamp: string;
}

export const REMINDER_STATUSES = ['upcoming', 'due_today', 'overdue', 'sent', 'dismissed'] as const;

export type ReminderStatus = (typeof REMINDER_STATUSES)[number];

export interface TaskReminder {
  id: string;
  label: string;
  scheduledAt: string;
  status: ReminderStatus;
}

export interface Task {
  id: string;
  title: string;
  description: string;
  investmentId: string | null;
  investmentName: string;
  status: TaskStatus;
  priority: TaskPriority;
  category: TaskCategory;
  dueDate: string;
  createdAt: string;
  updatedAt: string;
  completedAt: string | null;
  owner: TaskOwner;
  assignee: TaskOwner;
  checklist: TaskChecklist;
  comments: TaskComment[];
  attachments: TaskAttachment[];
  activity: TaskActivity[];
  reminders: TaskReminder[];
  relatedDocumentIds: string[];
  relatedSignatureIds: string[];
  relatedConversationIds: string[];
  relatedDistributionIds: string[];
  progressPercent: number;
}

export interface MessagesSummaryKpis {
  totalConversations: number;
  unreadMessages: number;
  starredConversations: number;
  pendingResponses: number;
  unreadAnnouncements: number;
  unreadNotifications: number;
  openTasks: number;
}

export interface TasksSummaryKpis {
  open: number;
  dueToday: number;
  dueThisWeek: number;
  completed: number;
  overdue: number;
  highPriority: number;
  pendingDocuments: number;
}

export interface ConversationFilterState {
  search: string;
  investmentId: string;
  category: MessageCategory;
  status: ConversationStatus | 'all';
  unreadOnly: boolean;
  archivedOnly: boolean;
  priority: MessagePriority | 'all';
  hasAttachments: boolean | null;
  dateFrom: string;
  dateTo: string;
}

export interface ConversationSortState {
  field: 'lastMessageAt' | 'subject' | 'priority' | 'unreadCount';
  direction: 'asc' | 'desc';
}

export interface TaskFilterState {
  search: string;
  investmentId: string;
  status: TaskStatus | 'all';
  priority: TaskPriority | 'all';
  category: TaskCategory | 'all';
  dueFrom: string;
  dueTo: string;
}

export interface TaskSortState {
  field: 'dueDate' | 'title' | 'priority' | 'status' | 'updatedAt';
  direction: 'asc' | 'desc';
}

export interface SidebarMessagingBadges {
  unreadMessages: number;
  openTasks: number;
}

export interface MessagingSearchResult {
  type: 'conversation' | 'message' | 'announcement' | 'notification' | 'task';
  id: string;
  title: string;
  subtitle: string;
  href: string;
  timestamp: string;
}
