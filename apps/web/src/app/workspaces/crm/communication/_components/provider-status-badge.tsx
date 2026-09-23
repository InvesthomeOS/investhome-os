'use client';

import { useTranslations } from 'next-intl';

import { StatusChip } from '@investhome/ui';

import type { CrmCommProviderStatus } from '@/workspaces/crm/types';

const STATUS_TONE: Record<CrmCommProviderStatus['status'], 'success' | 'warning' | 'default' | 'danger'> = {
  available: 'success',
  pending_sync: 'warning',
  unavailable: 'default',
  not_connected: 'danger',
};

type ProviderStatusBadgeProps = {
  status: CrmCommProviderStatus['status'];
  label?: string;
};

export function ProviderStatusBadge({ status, label }: ProviderStatusBadgeProps) {
  const t = useTranslations('crm.communication.providers');
  return (
    <StatusChip tone={STATUS_TONE[status]}>
      {label ?? t(`status.${status}`)}
    </StatusChip>
  );
}
