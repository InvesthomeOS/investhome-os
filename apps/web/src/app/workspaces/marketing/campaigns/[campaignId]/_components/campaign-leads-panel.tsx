'use client';

import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { EmptyState, ErrorState, LoadingState } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { fetchCampaignLeadBreakdown } from '@/workspaces/marketing/api/performance';

import { TableWidget } from '../../../dashboard/_components/analytics-widgets';

export function CampaignLeadsPanel({ campaignId }: { campaignId: string }) {
  const t = useTranslations('marketing.campaigns.detail.panels.leads');
  const tCommon = useTranslations('marketing.common');

  const query = useQuery({
    queryKey: ['marketing', 'performance', 'campaign-leads', campaignId],
    queryFn: () => fetchCampaignLeadBreakdown(campaignId),
  });

  if (query.isLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (query.isError) {
    return (
      <ErrorState
        title={tCommon('error')}
        message={query.error instanceof ApiError ? query.error.message : tCommon('error')}
      />
    );
  }

  if (!query.data || query.data.total === 0) {
    return <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />;
  }

  return (
    <section className="marketing-dashboard__section">
      <TableWidget
        columns={['full_name', 'attribution_status', 'utm_source', 'attribution_source']}
        columnLabels={{
          full_name: t('columns.name'),
          attribution_status: t('columns.status'),
          utm_source: t('columns.utmSource'),
          attribution_source: t('columns.method'),
        }}
        rows={query.data.items.map((item) => ({
          full_name: item.full_name,
          attribution_status: item.attribution_status,
          utm_source: item.utm_source ?? '—',
          attribution_source: item.attribution_source ?? '—',
        }))}
      />
    </section>
  );
}
