import type { Route } from 'next';

import { apiFetch } from '@/lib/api/client';

export type NotificationType =
  | 'reminder'
  | 'warning'
  | 'approval'
  | 'payment'
  | 'investor'
  | 'project'
  | 'finance'
  | 'system'
  | 'ai'
  | 'document'
  | 'construction';

export type NotificationPriority = 'info' | 'low' | 'medium' | 'high' | 'critical';
export type NotificationStatus = 'unread' | 'read' | 'dismissed';
export type NotificationSource =
  | 'user'
  | 'automation'
  | 'activity'
  | 'ai'
  | 'integration'
  | 'scheduled_job';

export interface NotificationItem {
  id: string;
  type: NotificationType;
  priority: NotificationPriority;
  title_key: string;
  message_key: string;
  metadata: Record<string, unknown> | null;
  related_entity_type: string | null;
  related_entity_id: string | null;
  recipient_user_id: string;
  created_by: string | null;
  source: NotificationSource;
  status: NotificationStatus;
  read_at: string | null;
  dismissed_at: string | null;
  expires_at: string | null;
  is_demo: boolean;
  created_at: string;
  link_module: string | null;
  link_query: Record<string, string> | null;
  related_label: string | null;
}

export interface NotificationListResponse {
  items: NotificationItem[];
  total: number;
  unread_count: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface NotificationSummary {
  critical: number;
  high: number;
  medium: number;
  unread: number;
}

export async function fetchNotifications(sync = true) {
  return apiFetch<NotificationListResponse>(
    `/notifications?sync=${sync ? 'true' : 'false'}&page_size=50`,
  );
}

export async function fetchNotificationUnreadCount(sync = true) {
  return apiFetch<{ unread_count: number; highest_priority: NotificationPriority | null }>(
    `/notifications/unread-count?sync=${sync ? 'true' : 'false'}`,
  );
}

export async function fetchNotificationSummary(sync = true) {
  return apiFetch<NotificationSummary>(`/notifications/summary?sync=${sync ? 'true' : 'false'}`);
}

export async function markNotificationRead(notificationId: string) {
  return apiFetch<NotificationItem>(`/notifications/${notificationId}/read`, { method: 'POST' });
}

export async function markAllNotificationsRead() {
  return apiFetch<{ updated: number }>('/notifications/read-all', { method: 'POST' });
}

export async function dismissNotification(notificationId: string) {
  return apiFetch<NotificationItem>(`/notifications/${notificationId}/dismiss`, { method: 'POST' });
}

export function notificationRecordHref(item: NotificationItem): Route | null {
  if (!item.link_module) return null;
  const base = `/dashboard/${item.link_module}`;
  if (!item.link_query || Object.keys(item.link_query).length === 0) {
    return base as Route;
  }
  const params = new URLSearchParams(item.link_query);
  return `${base}?${params.toString()}` as Route;
}

export function metadataForNotification(metadata: Record<string, unknown> | null | undefined) {
  if (!metadata) return {};
  return Object.fromEntries(
    Object.entries(metadata).map(([key, value]) => [key, value == null ? '' : String(value)]),
  ) as Record<string, string>;
}

export type NotificationTimeGroup = 'today' | 'yesterday' | 'earlier';

export function groupNotificationsByDate(
  items: NotificationItem[],
  locale: string,
): Record<NotificationTimeGroup, NotificationItem[]> {
  const intlLocale = locale === 'tr' ? 'tr-TR' : 'en-US';
  const today = new Intl.DateTimeFormat(intlLocale).format(new Date());
  const yesterdayDate = new Date();
  yesterdayDate.setDate(yesterdayDate.getDate() - 1);
  const yesterday = new Intl.DateTimeFormat(intlLocale).format(yesterdayDate);

  const groups: Record<NotificationTimeGroup, NotificationItem[]> = {
    today: [],
    yesterday: [],
    earlier: [],
  };

  for (const item of items) {
    const label = new Intl.DateTimeFormat(intlLocale).format(new Date(item.created_at));
    if (label === today) {
      groups.today.push(item);
    } else if (label === yesterday) {
      groups.yesterday.push(item);
    } else {
      groups.earlier.push(item);
    }
  }

  return groups;
}

export const NOTIFICATION_REFRESH_MS = 60_000;
