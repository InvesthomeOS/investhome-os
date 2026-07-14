'use client';

import { useTranslations } from 'next-intl';

export function notificationTextPath(key: string): string {
  return key.startsWith('notifications.') ? key.slice('notifications.'.length) : key;
}

export function useNotificationLabels() {
  const t = useTranslations('notifications');

  return {
    getTitle: (titleKey: string, metadata?: Record<string, string>) => {
      try {
        return t(notificationTextPath(titleKey) as 'lead.no_followup.title', metadata ?? {});
      } catch {
        return titleKey;
      }
    },
    getMessage: (messageKey: string, metadata?: Record<string, string>) => {
      try {
        return t(notificationTextPath(messageKey) as 'lead.no_followup.message', metadata ?? {});
      } catch {
        return messageKey;
      }
    },
    getPriorityLabel: (priority: string) => t(`priorities.${priority}` as 'priorities.high'),
    getTypeLabel: (type: string) => t(`types.${type}` as 'types.payment'),
    getGroupLabel: (group: string) => t(`groups.${group}` as 'groups.today'),
  };
}
