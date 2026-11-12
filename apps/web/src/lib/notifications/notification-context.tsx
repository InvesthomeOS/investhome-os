'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { createPortal } from 'react-dom';
import { useRouter } from 'next/navigation';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';

import {
  NOTIFICATION_REFRESH_MS,
  dismissAllNotifications,
  dismissNotification,
  fetchNotificationUnreadCount,
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  notificationRecordHref,
  type NotificationItem,
  type NotificationPriority,
} from '@/lib/api/notifications';
import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';
import { useNotificationLabels } from '@/lib/i18n/notification-labels';
import { createNotificationRefreshGate } from './notification-refresh-gate.mjs';
import { observeNotificationIds } from './notification-toast-detector.mjs';

type NotificationContextValue = {
  items: NotificationItem[];
  unreadCount: number;
  highestPriority: NotificationPriority | null;
  loading: boolean;
  drawerOpen: boolean;
  openDrawer: () => void;
  closeDrawer: () => void;
  refresh: () => Promise<void>;
  markRead: (id: string) => Promise<void>;
  markAllRead: () => Promise<void>;
  dismiss: (id: string) => Promise<void>;
  dismissAll: () => Promise<void>;
  canView: boolean;
};

const NotificationContext = createContext<NotificationContextValue | null>(null);

type ToastItem = {
  id: string;
  title: string;
  message: string;
  related: string;
  href: Route | null;
};

function NotificationToasts({
  items,
  onOpen,
  onClose,
}: {
  items: ToastItem[];
  onOpen: (item: ToastItem) => void;
  onClose: (id: string) => void;
}) {
  const t = useTranslations('notifications');
  if (!items.length || typeof document === 'undefined') return null;
  return createPortal(
    <div className="notification-toast-stack" aria-live="polite" data-testid="notification-toast-stack">
      {items.map((item) => (
        <article key={item.id} className="notification-toast" data-testid="notification-toast">
          <button
            type="button"
            className="notification-toast__close"
            aria-label={t('actions.dismiss')}
            data-testid="notification-toast-close"
            onClick={() => onClose(item.id)}
          >
            ×
          </button>
          <strong>{item.title}</strong>
          {item.message ? <p>{item.message}</p> : null}
          {item.related ? <span>{item.related}</span> : null}
          {item.href ? (
            <button type="button" className="notification-toast__open" onClick={() => onOpen(item)}>
              {t('actions.openRecord')}
            </button>
          ) : null}
        </article>
      ))}
    </div>,
    document.body,
  );
}

export function NotificationProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const canView = user ? hasPermission(user, 'notifications', 'view') : false;
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [highestPriority, setHighestPriority] = useState<NotificationPriority | null>(null);
  const [loading, setLoading] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const seenIds = useRef<Set<string> | null>(null);
  const refreshGate = useRef(createNotificationRefreshGate());
  const router = useRouter();
  const { getTitle, getMessage } = useNotificationLabels();

  const refresh = useCallback(
    async () => {
      if (!canView) return;
      await refreshGate.current(async () => {
        const firstLoad = seenIds.current === null;
        if (firstLoad) setLoading(true);
        try {
          const [list, counts] = await Promise.all([
            fetchNotifications(),
            fetchNotificationUnreadCount(),
          ]);
          setItems(list.items);
          setUnreadCount(counts.unread_count);
          setHighestPriority(counts.highest_priority);
          const observed = observeNotificationIds(seenIds.current, list.items);
          seenIds.current = observed.seen;
          const fresh = observed.fresh;
          if (fresh.length) {
              const visible = typeof document !== 'undefined' && document.visibilityState === 'visible';
              if (!visible && typeof Notification !== 'undefined' && Notification.permission === 'granted') {
                fresh.forEach((item) => {
                  const meta = {
                    title: String(item.metadata?.title || item.metadata?.name || item.related_label || ''),
                    name: String(item.metadata?.name || item.metadata?.title || item.related_label || ''),
                    minutes: String(item.metadata?.minutes || ''),
                    project: String(item.metadata?.project || ''),
                  };
                  const title = getTitle(item.title_key, meta);
                  const message = getMessage(item.message_key, meta);
                  const desktop = new Notification(title, {
                    body: [message, item.related_label || meta.name || meta.project].filter(Boolean).join(' · '),
                    tag: item.id,
                    requireInteraction: true,
                  });
                  desktop.onclick = () => {
                    window.focus();
                    const href = notificationRecordHref(item);
                    if (href) router.push(href);
                  };
                });
              } else {
              setToasts((current) =>
                [
                  ...fresh.map((item) => {
                    const meta = {
                      title: String(item.metadata?.title || item.metadata?.name || item.related_label || ''),
                      name: String(item.metadata?.name || item.metadata?.title || item.related_label || ''),
                      minutes: String(item.metadata?.minutes || ''),
                      project: String(item.metadata?.project || ''),
                    };
                    return {
                      id: item.id,
                      title: getTitle(item.title_key, meta),
                      message: getMessage(item.message_key, meta),
                      related: item.related_label || meta.name || meta.title,
                      href: notificationRecordHref(item),
                    };
                  }),
                  ...current,
                ].slice(0, 4),
              );
              }
          }
        } catch {
          if (seenIds.current === null) {
            setItems([]);
            setUnreadCount(0);
            setHighestPriority(null);
          }
        } finally {
          if (firstLoad) setLoading(false);
        }
      });
    },
    [canView, getTitle, getMessage, router],
  );

  useEffect(() => {
    if (!canView || typeof navigator === 'undefined' || !navigator.serviceWorker) return;
    const onMessage = (event: MessageEvent) => {
      if (event.data?.type === 'notification-refresh') void refresh();
    };
    navigator.serviceWorker.addEventListener('message', onMessage);
    return () => navigator.serviceWorker.removeEventListener('message', onMessage);
  }, [canView, refresh]);

  useEffect(() => {
    if (!canView) return;
    void refresh();
    const timer = window.setInterval(() => void refresh(), NOTIFICATION_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [canView, refresh]);

  useEffect(() => {
    if (!canView || typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    if (params.get('openNotifications') === '1') {
      setDrawerOpen(true);
    }
  }, [canView]);

  const markRead = useCallback(
    async (id: string) => {
      await markNotificationRead(id);
      await refresh();
    },
    [refresh],
  );

  const markAllRead = useCallback(async () => {
    await markAllNotificationsRead();
    await refresh();
  }, [refresh]);

  const closeToast = useCallback((id: string) => {
    setToasts((current) => current.filter((item) => item.id !== id));
  }, []);

  const openToast = useCallback(
    (toast: ToastItem) => {
      setToasts((current) => current.filter((item) => item.id !== toast.id));
      void markRead(toast.id);
      if (toast.href) router.push(toast.href);
    },
    [markRead, router],
  );

  const dismissAll = useCallback(async () => {
    await dismissAllNotifications();
    await refresh();
  }, [refresh]);

  const dismiss = useCallback(
    async (id: string) => {
      await dismissNotification(id);
      await refresh();
    },
    [refresh],
  );

  const value = useMemo(
    () => ({
      items,
      unreadCount,
      highestPriority,
      loading,
      drawerOpen,
      openDrawer: () => setDrawerOpen(true),
      closeDrawer: () => setDrawerOpen(false),
      refresh,
      markRead,
      markAllRead,
      dismiss,
      dismissAll,
      canView,
    }),
    [
      items,
      unreadCount,
      highestPriority,
      loading,
      drawerOpen,
      refresh,
      markRead,
      markAllRead,
          dismiss,
          dismissAll,
          canView,
        ],
  );

  return (
    <NotificationContext.Provider value={value}>
      {children}
      <NotificationToasts items={toasts} onOpen={openToast} onClose={closeToast} />
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within NotificationProvider');
  }
  return context;
}
