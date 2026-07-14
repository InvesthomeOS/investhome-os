'use client';

import { useTranslations } from 'next-intl';
import { useMemo } from 'react';

import type { ActivityAction, ActivityEntityType, ActivitySource } from '@/lib/api/activity';

export function activityDescriptionPath(descriptionKey: string): string {
  const normalized = descriptionKey.startsWith('activity.')
    ? descriptionKey.slice('activity.'.length)
    : descriptionKey;
  return `descriptions.${normalized}`;
}

export function useActivityLabels() {
  const t = useTranslations('activity');

  const actionOptions = useMemo(
    () =>
      (
        [
          'created',
          'updated',
          'status_changed',
          'archived',
          'login',
          'logout',
          'login_failed',
          'role_assigned',
          'permission_changed',
          'password_changed',
          'invited',
          'deactivated',
          'payment_completed',
        ] as ActivityAction[]
      ).map((value) => ({ value, label: t(`actions.${value}`) })),
    [t],
  );

  const entityTypeOptions = useMemo(
    () =>
      (
        [
          'lead',
          'investor',
          'project',
          'transaction',
          'payment_obligation',
          'funding_commitment',
          'financial_account',
          'user',
          'role',
        ] as ActivityEntityType[]
      ).map((value) => ({ value, label: t(`entityTypes.${value}`) })),
    [t],
  );

  const sourceOptions = useMemo(
    () =>
      (
        [
          'web',
          'api',
          'background_job',
          'automation',
          'import',
          'integration',
          'ai_service',
        ] as ActivitySource[]
      ).map((value) => ({ value, label: t(`sources.${value}`) })),
    [t],
  );

  return {
    getActionLabel: (action: ActivityAction) => t(`actions.${action}`),
    getEntityTypeLabel: (entityType: ActivityEntityType) => t(`entityTypes.${entityType}`),
    getSourceLabel: (source: ActivitySource) => t(`sources.${source}`),
    getDescription: (descriptionKey: string, metadata?: Record<string, string>) => {
      const path = activityDescriptionPath(descriptionKey);
      try {
        return t(path as 'descriptions.lead.created', metadata ?? {});
      } catch {
        return descriptionKey;
      }
    },
    actionOptions,
    entityTypeOptions,
    sourceOptions,
  };
}
