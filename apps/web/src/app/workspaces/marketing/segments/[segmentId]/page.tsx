'use client';

import { useParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { EmptyState, LoadingState, StatusChip } from '@investhome/ui';

import { segmentQueries } from '@/workspaces/marketing/hooks/use-segments';

import { SegmentRulesList } from '../../_components/widget-data-display';

export default function SegmentDetailPage() {
  const params = useParams<{ segmentId: string }>();
  const t = useTranslations('marketing.segments');
  const tCommon = useTranslations('marketing.common');
  const detailQuery = useQuery(segmentQueries.detail(params.segmentId));
  const rulesQuery = useQuery(segmentQueries.rules(params.segmentId));

  if (detailQuery.isLoading) return <LoadingState label={tCommon('loading')} />;
  if (!detailQuery.data) return <EmptyState title={tCommon('error')} />;

  return (
    <main className="dashboard marketing-segment-detail">
      <header className="dashboard__header">
        <h1 className="dashboard__title">{detailQuery.data.name}</h1>
        <p className="dashboard__subtitle">
          <StatusChip tone={detailQuery.data.calculation_status === 'calculated' ? 'success' : 'warning'}>
            {detailQuery.data.calculation_status}
          </StatusChip>
        </p>
      </header>
      <section className="marketing-dashboard__section">
        <h2 className="marketing-dashboard__section-title">{t('detail.rules')}</h2>
        {rulesQuery.isLoading ? (
          <LoadingState label={tCommon('loading')} />
        ) : (
          <SegmentRulesList ruleGroups={rulesQuery.data?.rule_groups ?? []} emptyLabel={tCommon('empty')} />
        )}
      </section>
    </main>
  );
}
