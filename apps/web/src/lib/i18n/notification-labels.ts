'use client';

import { useCallback, useMemo, useRef } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import {
  isRawMessageKey,
  notificationFallback,
  notificationTextPath,
} from '@/lib/i18n/notification-text.mjs';

export { notificationTextPath };

export function useNotificationLabels() {
  const t = useTranslations('notifications');
  const locale = useLocale();
  const tRef = useRef(t);
  const localeRef = useRef(locale);
  tRef.current = t;
  localeRef.current = locale;

  const readText = (key: string, metadata?: Record<string, string>) => {
    const path = notificationTextPath(key);
    let translated = '';
    try {
      translated = String(tRef.current(path as 'lead.no_followup.title', metadata ?? {}));
    } catch {
      translated = '';
    }
    if (!translated || isRawMessageKey(translated) || translated === key || translated === path) {
      return notificationFallback(key, metadata, localeRef.current);
    }
    return translated;
  };

  const getTitle = useCallback((titleKey: string, metadata?: Record<string, string>) => {
    return readText(titleKey, metadata);
  }, []);

  const getMessage = useCallback((messageKey: string, metadata?: Record<string, string>) => {
    return readText(messageKey, metadata);
  }, []);

  const getPriorityLabel = useCallback(
    (priority: string) => tRef.current(`priorities.${priority}` as 'priorities.high'),
    [],
  );
  const getTypeLabel = useCallback(
    (type: string) => tRef.current(`types.${type}` as 'types.payment'),
    [],
  );
  const getGroupLabel = useCallback(
    (group: string) => tRef.current(`groups.${group}` as 'groups.today'),
    [],
  );

  return useMemo(
    () => ({ getTitle, getMessage, getPriorityLabel, getTypeLabel, getGroupLabel }),
    [getTitle, getMessage, getPriorityLabel, getTypeLabel, getGroupLabel],
  );
}
