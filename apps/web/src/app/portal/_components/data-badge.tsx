'use client';

import { StatusBadge } from '@investhome/ui';
import { useTranslations } from 'next-intl';

import type { DataClass } from '../_data/types';

const TONE: Record<DataClass, 'success' | 'warning' | 'danger' | 'info'> = {
  LIVE: 'success',
  PARTIAL: 'warning',
  BLOCKED: 'danger',
  DEMO: 'info',
};

/** Portal data classification — maps to shared StatusBadge tones (G9.5). */
export function DataBadge({ kind }: { kind: DataClass }) {
  const t = useTranslations('portalG9');
  const label =
    kind === 'LIVE'
      ? t('dataLive')
      : kind === 'PARTIAL'
        ? t('dataPartial')
        : kind === 'BLOCKED'
          ? t('dataBlocked')
          : t('dataDemo');
  return (
    <StatusBadge tone={TONE[kind]} className={`portal-badge portal-badge--${kind.toLowerCase()}`}>
      {label}
    </StatusBadge>
  );
}
