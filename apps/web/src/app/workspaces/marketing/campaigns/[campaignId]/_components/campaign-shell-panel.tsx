'use client';

import { useTranslations } from 'next-intl';

import { EmptyState } from '@investhome/ui';

export function CampaignShellPanel({ type }: { type: string; campaignId: string }) {
  const t = useTranslations('marketing.campaigns.detail.panels.shell');
  return (
    <EmptyState
      title={t('emptyTitle', { module: type })}
      description={t('emptyDescription')}
    />
  );
}
