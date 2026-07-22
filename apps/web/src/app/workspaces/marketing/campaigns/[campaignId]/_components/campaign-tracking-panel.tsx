'use client';

import { useTranslations } from 'next-intl';

import { EmptyState } from '@investhome/ui';

export function CampaignTrackingPanel({}: { campaignId: string }) {
  const t = useTranslations('marketing.campaigns.detail.panels.tracking');
  return <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />;
}
