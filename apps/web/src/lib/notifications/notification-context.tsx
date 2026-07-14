'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import {
  NOTIFICATION_REFRESH_MS,
  dismissNotification,
  fetchNotificationUnreadCount,
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type NotificationItem,
  type NotificationPriority,
} from '@/lib/api/notifications';
import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';

type NotificationContextValue = {
  items: NotificationItem[];
  unreadCount: number;
  highestPriority: NotificationPriority | null;
  loading: boolean;
  drawerOpen: boolean;
  openDrawer: () => void;
  closeDrawer: () => void;
  refresh: (sync?: boolean) => Promise<void>;
  markRead: (id: string) => Promise<void>;
  markAllRead: () => Promise<void>;
  dismiss: (id: string) => Promise<void>;
  canView: boolean;
};

const NotificationContext = createContext<NotificationContextValue | null>(null);

export function NotificationProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const canView = user ? hasPermission(user, 'notifications', 'view') : false;
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [highestPriority, setHighestPriority] = useState<NotificationPriority | null>(null);
  const [loading, setLoading] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const refresh = useCallback(
    async (sync = true) => {
      if (!canView) return;
      setLoading(true);
      try {
        const [list, counts] = await Promise.all([
          fetchNotifications(sync),
          fetchNotificationUnreadCount(sync),
        ]);
        setItems(list.items);
        setUnreadCount(counts.unread_count);
        setHighestPriority(counts.highest_priority);
      } catch {
        setItems([]);
        setUnreadCount(0);
        setHighestPriority(null);
      } finally {
        setLoading(false);
      }
    },
    [canView],
  );

  useEffect(() => {
    if (!canView) return;
    void refresh(true);
    const timer = window.setInterval(() => void refresh(false), NOTIFICATION_REFRESH_MS);
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
      await refresh(false);
    },
    [refresh],
  );

  const markAllRead = useCallback(async () => {
    await markAllNotificationsRead();
    await refresh(false);
  }, [refresh]);

  const dismiss = useCallback(
    async (id: string) => {
      await dismissNotification(id);
      await refresh(false);
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
      canView,
    ],
  );

  return <NotificationContext.Provider value={value}>{children}</NotificationContext.Provider>;
}

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within NotificationProvider');
  }
  return context;
}
