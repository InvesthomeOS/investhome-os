'use client';

import Link from 'next/link';
import { useLocale, useTranslations } from 'next-intl';

import {
  groupNotificationsByDate,
  metadataForNotification,
  notificationRecordHref,
  type NotificationItem,
  type NotificationPriority,
} from '@/lib/api/notifications';
import { useNotificationLabels } from '@/lib/i18n/notification-labels';
import { useNotifications } from '@/lib/notifications/notification-context';

const PRIORITY_CLASS: Record<NotificationPriority, string> = {
  critical: 'notification-priority--critical',
  high: 'notification-priority--high',
  medium: 'notification-priority--medium',
  low: 'notification-priority--low',
  info: 'notification-priority--info',
};

function NotificationRow({
  item,
  onMarkRead,
  onDismiss,
}: {
  item: NotificationItem;
  onMarkRead: (id: string) => void;
  onDismiss: (id: string) => void;
}) {
  const t = useTranslations('notifications');
  const { getTitle, getMessage, getPriorityLabel } = useNotificationLabels();
  const meta = metadataForNotification(item.metadata);
  const href = notificationRecordHref(item);
  const isUnread = item.status === 'unread';
  const locale = useLocale();

  const content = (
    <>
      <div className="notification-item__header">
        <span className={`notification-priority ${PRIORITY_CLASS[item.priority]}`}>
          {getPriorityLabel(item.priority)}
        </span>
        <time dateTime={item.created_at}>
          {new Intl.DateTimeFormat(locale === 'tr' ? 'tr-TR' : 'en-US', {
            hour: '2-digit',
            minute: '2-digit',
          }).format(new Date(item.created_at))}
        </time>
      </div>
      <strong>{getTitle(item.title_key, meta)}</strong>
      <p>{getMessage(item.message_key, meta)}</p>
      {item.related_label && <span className="notification-item__related">{item.related_label}</span>}
    </>
  );

  return (
    <li className={`notification-item${isUnread ? ' notification-item--unread' : ''}`}>
      {href ? (
        <Link href={href} className="notification-item__link" onClick={() => isUnread && onMarkRead(item.id)}>
          {content}
        </Link>
      ) : (
        <div className="notification-item__body">{content}</div>
      )}
      <div className="notification-item__actions">
        {isUnread && (
          <button type="button" onClick={() => void onMarkRead(item.id)}>
            {t('actions.markRead')}
          </button>
        )}
        <button type="button" onClick={() => void onDismiss(item.id)}>
          {t('actions.dismiss')}
        </button>
        {href && (
          <Link href={href} className="notification-item__open">
            {t('actions.openRecord')}
          </Link>
        )}
      </div>
    </li>
  );
}

export function NotificationDrawer() {
  const t = useTranslations('notifications');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { getGroupLabel } = useNotificationLabels();
  const {
    items,
    loading,
    drawerOpen,
    closeDrawer,
    markRead,
    markAllRead,
    dismiss,
    unreadCount,
  } = useNotifications();

  if (!drawerOpen) return null;

  const groups = groupNotificationsByDate(items, locale);

  return (
    <div className="notification-drawer" role="presentation" onClick={closeDrawer}>
      <aside
        className="notification-drawer__panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="notification-drawer-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="notification-drawer__header">
          <div>
            <p className="dashboard__eyebrow">{t('drawerEyebrow')}</p>
            <h2 id="notification-drawer-title">{t('title')}</h2>
            <p className="notification-drawer__count">{t('unreadCount', { count: unreadCount })}</p>
          </div>
          <button type="button" className="leads__button leads__button--ghost" onClick={closeDrawer}>
            {tCommon('close')}
          </button>
        </header>

        <div className="notification-drawer__toolbar">
          <button
            type="button"
            className="leads__button leads__button--secondary"
            disabled={unreadCount === 0}
            onClick={() => void markAllRead()}
          >
            {t('actions.markAllRead')}
          </button>
        </div>

        {loading && <p className="leads__state">{tCommon('loading')}</p>}
        {!loading && items.length === 0 && <p className="leads__state">{t('empty')}</p>}

        {!loading &&
          (['today', 'yesterday', 'earlier'] as const).map((group) =>
            groups[group].length > 0 ? (
              <section key={group} className="notification-group">
                <h3>{getGroupLabel(group)}</h3>
                <ul>
                  {groups[group].map((item) => (
                    <NotificationRow
                      key={item.id}
                      item={item}
                      onMarkRead={(id) => void markRead(id)}
                      onDismiss={(id) => void dismiss(id)}
                    />
                  ))}
                </ul>
              </section>
            ) : null,
          )}
      </aside>
    </div>
  );
}
