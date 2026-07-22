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

import { getAllTasks } from '../_data/investor-tasks';
import {
  computeMessagesSummary,
  computeSidebarBadges,
  computeTasksSummary,
  mergeAnnouncements,
  mergeConversations,
  mergeNotifications,
  mergeTasks,
  type AnnouncementOverrides,
  type ConversationOverrides,
  type MessageOverrides,
  type NotificationOverrides,
  type TaskOverrides,
} from '../_data/messaging-calculations';
import type {
  Announcement,
  Conversation,
  InvestorNotificationItem,
  MessagesSummaryKpis,
  SidebarMessagingBadges,
  Task,
  TaskComment,
  TasksSummaryKpis,
} from '../_data/messaging-types';

const STORAGE_KEY = 'investor-messaging-state-v1';

interface PersistedState {
  conversationOverrides: Record<string, ConversationOverrides>;
  messageOverrides: Record<string, MessageOverrides>;
  announcementOverrides: Record<string, AnnouncementOverrides>;
  notificationOverrides: Record<string, NotificationOverrides>;
  taskOverrides: Record<string, TaskOverrides>;
  drafts: Record<string, string>;
}

interface MessagingStateContextValue {
  conversations: Conversation[];
  announcements: Announcement[];
  notifications: InvestorNotificationItem[];
  tasks: Task[];
  messagesSummary: MessagesSummaryKpis;
  tasksSummary: TasksSummaryKpis;
  sidebarBadges: SidebarMessagingBadges;
  selectedConversationIds: string[];
  setSelectedConversationIds: (ids: string[]) => void;
  toggleConversationSelection: (id: string) => void;
  clearConversationSelection: () => void;
  markConversationRead: (conversationId: string) => void;
  markConversationsRead: (conversationIds: string[]) => void;
  archiveConversation: (conversationId: string) => void;
  archiveConversations: (conversationIds: string[]) => void;
  unarchiveConversation: (conversationId: string) => void;
  deleteConversationFromView: (conversationId: string) => void;
  toggleStarConversation: (conversationId: string) => void;
  markAnnouncementRead: (announcementId: string) => void;
  markAllAnnouncementsRead: () => void;
  markNotificationRead: (notificationId: string) => void;
  dismissNotification: (notificationId: string) => void;
  markAllNotificationsRead: () => void;
  completeTask: (taskId: string) => void;
  toggleChecklistItem: (taskId: string, itemId: string) => void;
  addTaskComment: (taskId: string, body: string) => void;
  saveDraft: (conversationId: string, body: string) => void;
  getDraft: (conversationId: string) => string;
  clearDraft: (conversationId: string) => void;
  sendMessage: (conversationId: string, body: string) => void;
}

const MessagingStateContext = createContext<MessagingStateContextValue | null>(null);

function loadPersistedState(): Partial<PersistedState> {
  if (typeof window === 'undefined') return {};
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    return JSON.parse(raw) as Partial<PersistedState>;
  } catch {
    return {};
  }
}

function savePersistedState(state: PersistedState): void {
  if (typeof window === 'undefined') return;
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // ignore quota errors in demo
  }
}

export function MessagingStateProvider({ children }: { children: ReactNode }) {
  const [conversationOverrides, setConversationOverrides] = useState<
    Record<string, ConversationOverrides>
  >({});
  const [messageOverrides, setMessageOverrides] = useState<
    Record<string, MessageOverrides>
  >({});
  const [announcementOverrides, setAnnouncementOverrides] = useState<
    Record<string, AnnouncementOverrides>
  >({});
  const [notificationOverrides, setNotificationOverrides] = useState<
    Record<string, NotificationOverrides>
  >({});
  const [taskOverrides, setTaskOverrides] = useState<Record<string, TaskOverrides>>({});
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [localMessages, setLocalMessages] = useState<
    Record<string, Conversation['messages']>
  >({});
  const [selectedConversationIds, setSelectedConversationIds] = useState<string[]>([]);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const persisted = loadPersistedState();
    if (persisted.conversationOverrides) setConversationOverrides(persisted.conversationOverrides);
    if (persisted.messageOverrides) setMessageOverrides(persisted.messageOverrides);
    if (persisted.announcementOverrides) setAnnouncementOverrides(persisted.announcementOverrides);
    if (persisted.notificationOverrides) setNotificationOverrides(persisted.notificationOverrides);
    if (persisted.taskOverrides) setTaskOverrides(persisted.taskOverrides);
    if (persisted.drafts) setDrafts(persisted.drafts);
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    savePersistedState({
      conversationOverrides,
      messageOverrides,
      announcementOverrides,
      notificationOverrides,
      taskOverrides,
      drafts,
    });
  }, [
    hydrated,
    conversationOverrides,
    messageOverrides,
    announcementOverrides,
    notificationOverrides,
    taskOverrides,
    drafts,
  ]);

  const conversations = useMemo(() => {
    const merged = mergeConversations(conversationOverrides, messageOverrides);
    return merged.map((c) => {
      const extra = localMessages[c.id];
      if (!extra?.length) return c;
      return { ...c, messages: [...c.messages, ...extra] };
    });
  }, [conversationOverrides, messageOverrides, localMessages]);

  const announcements = useMemo(
    () => mergeAnnouncements(announcementOverrides),
    [announcementOverrides],
  );

  const notifications = useMemo(
    () => mergeNotifications(notificationOverrides),
    [notificationOverrides],
  );

  const tasks = useMemo(() => mergeTasks(taskOverrides), [taskOverrides]);

  const messagesSummary = useMemo(
    () => computeMessagesSummary(conversations, announcements, notifications, tasks),
    [conversations, announcements, notifications, tasks],
  );

  const tasksSummary = useMemo(() => computeTasksSummary(tasks), [tasks]);

  const sidebarBadges = useMemo(
    () => computeSidebarBadges(conversations, tasks),
    [conversations, tasks],
  );

  const markConversationRead = useCallback((conversationId: string) => {
    setConversationOverrides((prev) => ({
      ...prev,
      [conversationId]: { ...prev[conversationId], unreadCount: 0 },
    }));
  }, []);

  const markConversationsRead = useCallback((conversationIds: string[]) => {
    setConversationOverrides((prev) => {
      const next = { ...prev };
      for (const id of conversationIds) {
        next[id] = { ...next[id], unreadCount: 0 };
      }
      return next;
    });
  }, []);

  const archiveConversation = useCallback((conversationId: string) => {
    setConversationOverrides((prev) => ({
      ...prev,
      [conversationId]: { ...prev[conversationId], isArchived: true, status: 'archived' },
    }));
  }, []);

  const archiveConversations = useCallback((conversationIds: string[]) => {
    setConversationOverrides((prev) => {
      const next = { ...prev };
      for (const id of conversationIds) {
        next[id] = { ...next[id], isArchived: true, status: 'archived' };
      }
      return next;
    });
  }, []);

  const unarchiveConversation = useCallback((conversationId: string) => {
    setConversationOverrides((prev) => ({
      ...prev,
      [conversationId]: { ...prev[conversationId], isArchived: false, status: 'active' },
    }));
  }, []);

  const deleteConversationFromView = useCallback((conversationId: string) => {
    setConversationOverrides((prev) => ({
      ...prev,
      [conversationId]: { ...prev[conversationId], isDeleted: true },
    }));
  }, []);

  const toggleStarConversation = useCallback((conversationId: string) => {
    setConversationOverrides((prev) => {
      const base = mergeConversations(prev, {}).find((c) => c.id === conversationId);
      const current = prev[conversationId]?.isStarred ?? base?.isStarred ?? false;
      return {
        ...prev,
        [conversationId]: {
          ...prev[conversationId],
          isStarred: !current,
        },
      };
    });
  }, []);

  const markAnnouncementRead = useCallback((announcementId: string) => {
    setAnnouncementOverrides((prev) => ({
      ...prev,
      [announcementId]: { isRead: true },
    }));
  }, []);

  const markAllAnnouncementsRead = useCallback(() => {
    setAnnouncementOverrides((prev) => {
      const next = { ...prev };
      for (const a of mergeAnnouncements(prev)) {
        next[a.id] = { isRead: true };
      }
      return next;
    });
  }, []);

  const markNotificationRead = useCallback((notificationId: string) => {
    setNotificationOverrides((prev) => ({
      ...prev,
      [notificationId]: { ...prev[notificationId], isRead: true },
    }));
  }, []);

  const dismissNotification = useCallback((notificationId: string) => {
    setNotificationOverrides((prev) => ({
      ...prev,
      [notificationId]: { ...prev[notificationId], isDismissed: true },
    }));
  }, []);

  const markAllNotificationsRead = useCallback(() => {
    setNotificationOverrides((prev) => {
      const next = { ...prev };
      for (const n of mergeNotifications(prev)) {
        next[n.id] = { ...next[n.id], isRead: true };
      }
      return next;
    });
  }, []);

  const completeTask = useCallback((taskId: string) => {
    setTaskOverrides((prev) => ({
      ...prev,
      [taskId]: { ...prev[taskId], status: 'completed' },
    }));
  }, []);

  const toggleChecklistItem = useCallback((taskId: string, itemId: string) => {
    setTaskOverrides((prev) => {
      const baseTask = getAllTasks().find((t) => t.id === taskId);
      const baseItem = baseTask?.checklist.items.find((i) => i.id === itemId);
      const overrideCompleted = prev[taskId]?.checklistItems?.[itemId];
      const currentCompleted =
        overrideCompleted !== undefined ? overrideCompleted : (baseItem?.isCompleted ?? false);
      const existing = prev[taskId]?.checklistItems ?? {};
      return {
        ...prev,
        [taskId]: {
          ...prev[taskId],
          checklistItems: { ...existing, [itemId]: !currentCompleted },
        },
      };
    });
  }, []);

  const addTaskComment = useCallback((taskId: string, body: string) => {
    const comment: TaskComment = {
      id: `tc-local-${Date.now()}`,
      author: {
        id: 'inv-001',
        name: 'Eleanor Whitmore',
        role: 'Investor',
        avatarInitials: 'EW',
        emailMasked: 'e***@whitmorecapital.com',
      },
      body,
      createdAt: new Date().toISOString(),
      isInternal: false,
    };
    setTaskOverrides((prev) => {
      const existingComments = prev[taskId]?.comments ?? [];
      return {
        ...prev,
        [taskId]: {
          ...prev[taskId],
          comments: [...existingComments, comment],
        },
      };
    });
  }, []);

  const saveDraft = useCallback((conversationId: string, body: string) => {
    setDrafts((prev) => ({ ...prev, [conversationId]: body }));
  }, []);

  const getDraft = useCallback(
    (conversationId: string) => drafts[conversationId] ?? '',
    [drafts],
  );

  const clearDraft = useCallback((conversationId: string) => {
    setDrafts((prev) => {
      const next = { ...prev };
      delete next[conversationId];
      return next;
    });
  }, []);

  const sendMessage = useCallback(
    (conversationId: string, body: string) => {
      const newMsg: Conversation['messages'][number] = {
        id: `msg-local-${Date.now()}`,
        conversationId,
        author: {
          id: 'inv-001',
          name: 'Eleanor Whitmore',
          role: 'Investor',
          avatarInitials: 'EW',
          isInvestor: true,
          emailMasked: 'e***@whitmorecapital.com',
        },
        body,
        messageType: 'general_support',
        sentAt: new Date().toISOString(),
        isRead: true,
        isInternal: false,
        attachments: [],
        references: [],
        isPinned: false,
      };
      setLocalMessages((prev) => ({
        ...prev,
        [conversationId]: [...(prev[conversationId] ?? []), newMsg],
      }));
      clearDraft(conversationId);
    },
    [clearDraft],
  );

  const toggleConversationSelection = useCallback((id: string) => {
    setSelectedConversationIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }, []);

  const clearConversationSelection = useCallback(() => setSelectedConversationIds([]), []);

  const value = useMemo<MessagingStateContextValue>(
    () => ({
      conversations,
      announcements,
      notifications,
      tasks,
      messagesSummary,
      tasksSummary,
      sidebarBadges,
      selectedConversationIds,
      setSelectedConversationIds,
      toggleConversationSelection,
      clearConversationSelection,
      markConversationRead,
      markConversationsRead,
      archiveConversation,
      archiveConversations,
      unarchiveConversation,
      deleteConversationFromView,
      toggleStarConversation,
      markAnnouncementRead,
      markAllAnnouncementsRead,
      markNotificationRead,
      dismissNotification,
      markAllNotificationsRead,
      completeTask,
      toggleChecklistItem,
      addTaskComment,
      saveDraft,
      getDraft,
      clearDraft,
      sendMessage,
    }),
    [
      conversations,
      announcements,
      notifications,
      tasks,
      messagesSummary,
      tasksSummary,
      sidebarBadges,
      selectedConversationIds,
      toggleConversationSelection,
      clearConversationSelection,
      markConversationRead,
      markConversationsRead,
      archiveConversation,
      archiveConversations,
      unarchiveConversation,
      deleteConversationFromView,
      toggleStarConversation,
      markAnnouncementRead,
      markAllAnnouncementsRead,
      markNotificationRead,
      dismissNotification,
      markAllNotificationsRead,
      completeTask,
      toggleChecklistItem,
      addTaskComment,
      saveDraft,
      getDraft,
      clearDraft,
      sendMessage,
    ],
  );

  return (
    <MessagingStateContext.Provider value={value}>{children}</MessagingStateContext.Provider>
  );
}

export function useMessagingState(): MessagingStateContextValue {
  const ctx = useContext(MessagingStateContext);
  if (!ctx) {
    throw new Error('useMessagingState must be used within MessagingStateProvider');
  }
  return ctx;
}

export function useMessagingStateOptional(): MessagingStateContextValue | null {
  return useContext(MessagingStateContext);
}
