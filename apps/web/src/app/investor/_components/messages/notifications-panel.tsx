'use client';

import Link from 'next/link';
import type { Route } from 'next';

import { formatInvestorDateTime } from '../../_data/mock-data';
import { useMessagingState } from '../../_state/messaging-state';

interface NotificationsPanelProps {
  open: boolean;
  onClose: () => void;
}

export function NotificationsPanel({ open, onClose }: NotificationsPanelProps) {
  const {
    notifications,
    markNotificationRead,
    dismissNotification,
    markAllNotificationsRead,
  } = useMessagingState();

  if (!open) return null;

  return (
    <>
      <button
        type="button"
        className="inv-panel-overlay"
        onClick={onClose}
        aria-label="Close notifications"
      />
      <aside
        className="inv-panel inv-panel--notifications"
        role="dialog"
        aria-labelledby="notifications-title"
        aria-modal="true"
      >
        <header className="inv-panel__header">
          <h2 id="notifications-title">Notification Center</h2>
          <div className="inv-panel__header-actions">
            <button type="button" onClick={markAllNotificationsRead}>
              Mark all read
            </button>
            <button type="button" onClick={onClose} aria-label="Close">
              ×
            </button>
          </div>
        </header>

        <div className="inv-panel__body">
          {notifications.length === 0 ? (
            <p className="inv-panel__empty">No notifications.</p>
          ) : (
            <ul className="inv-notifications-list">
              {notifications.map((notif) => (
                <li
                  key={notif.id}
                  className={`inv-notifications-list__item${!notif.isRead ? ' inv-notifications-list__item--unread' : ''}`}
                >
                  <div className="inv-notifications-list__meta">
                    <span className="inv-notifications-list__category">{notif.category}</span>
                    <span className={`inv-notifications-list__priority inv-notifications-list__priority--${notif.priority}`}>
                      {notif.priority}
                    </span>
                  </div>
                  <h3>{notif.title}</h3>
                  <p>{notif.message}</p>
                  <time dateTime={notif.timestamp}>{formatInvestorDateTime(notif.timestamp)}</time>
                  <div className="inv-notifications-list__actions">
                    {!notif.isRead ? (
                      <button type="button" onClick={() => markNotificationRead(notif.id)}>
                        Mark read
                      </button>
                    ) : null}
                    <button type="button" onClick={() => dismissNotification(notif.id)}>
                      Dismiss
                    </button>
                    {notif.actionHref ? (
                      <Link href={notif.actionHref as Route} onClick={onClose}>
                        {notif.actionLabel ?? 'Open'}
                      </Link>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>
    </>
  );
}
