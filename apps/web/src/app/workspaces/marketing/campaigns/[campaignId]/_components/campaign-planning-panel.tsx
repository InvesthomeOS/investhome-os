'use client';

import { useTranslations } from 'next-intl';

import { EmptyState } from '@investhome/ui';

export function CampaignPlanningPanel({}: { campaignId: string }) {
  const t = useTranslations('marketing.campaigns.detail.panels.planning');
  return <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />;
}
