'use client';

import { useTranslations } from 'next-intl';

import { useNotifications } from '@/lib/notifications/notification-context';

const PRIORITY_DOT: Record<string, string> = {
  critical: 'notification-bell__dot--critical',
  high: 'notification-bell__dot--high',
  medium: 'notification-bell__dot--medium',
  low: 'notification-bell__dot--low',
  info: 'notification-bell__dot--info',
};

export function NotificationBell() {
  const t = useTranslations('notifications');
  const { canView, unreadCount, highestPriority, openDrawer } = useNotifications();

  if (!canView) return null;

  const dotClass = highestPriority ? PRIORITY_DOT[highestPriority] : 'notification-bell__dot--medium';

  return (
    <button
      type="button"
      className="notification-bell"
      aria-label={t('bellAriaLabel', { count: unreadCount })}
      onClick={openDrawer}
    >
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path
          d="M12 22a2.5 2.5 0 0 0 2.45-2h-4.9A2.5 2.5 0 0 0 12 22Zm7-6V11a7 7 0 1 0-14 0v5l-2 2v1h18v-1l-2-2Z"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
      </svg>
      {unreadCount > 0 && (
        <>
          <span className={`notification-bell__dot ${dotClass}`} aria-hidden="true" />
          <span className="notification-bell__badge">{unreadCount > 99 ? '99+' : unreadCount}</span>
        </>
      )}
    </button>
  );
}
