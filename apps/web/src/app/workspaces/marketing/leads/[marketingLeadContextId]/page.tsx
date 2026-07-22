'use client';

import { useParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { EmptyState, LoadingState, StatusChip } from '@investhome/ui';

import { marketingLeadsQueries } from '@/workspaces/marketing/hooks/use-marketing-leads';

import { ScoreSummary } from '../../_components/widget-data-display';
import { UnavailableValue } from '../../_components/summary-widget';

export default function MarketingLeadDetailPage() {
  const params = useParams<{ marketingLeadContextId: string }>();
  const t = useTranslations('marketing.leads');
  const tCommon = useTranslations('marketing.common');
  const detailQuery = useQuery(marketingLeadsQueries.detail(params.marketingLeadContextId));
  const handoffQuery = useQuery(marketingLeadsQueries.handoffReadiness(params.marketingLeadContextId));

  if (detailQuery.isLoading) return <LoadingState label={tCommon('loading')} />;

  const lead = detailQuery.data;
  if (!lead) return <EmptyState title={tCommon('error')} />;

  const scores =
    lead.scores_json && typeof lead.scores_json === 'object' && !Array.isArray(lead.scores_json)
      ? (lead.scores_json as Record<string, unknown>)
      : null;

  return (
    <main className="dashboard marketing-lead-detail">
      <header className="dashboard__header">
        <h1 className="dashboard__title">{t('detail.title')}</h1>
      </header>
      <dl className="marketing-detail-dl">
        <dt>{t('detail.handoff')}</dt>
        <dd>
          <StatusChip tone={lead.handoff_status === 'ready' ? 'success' : 'warning'}>
            {t.has(`handoffStatus.${lead.handoff_status}`)
              ? t(`handoffStatus.${lead.handoff_status}` as 'handoffStatus.ready')
              : lead.handoff_status.replace(/_/g, ' ')}
          </StatusChip>
        </dd>
        <dt>{t('detail.utm')}</dt>
        <dd>
          {(lead.utm_data_json as { utm_source?: string } | null)?.utm_source ?? (
            <UnavailableValue label={tCommon('noData')} />
          )}
        </dd>
        <dt>{t('detail.score')}</dt>
        <dd>{scores ? <ScoreSummary scores={scores} /> : <UnavailableValue label={tCommon('notCalculated')} />}</dd>
      </dl>
      {handoffQuery.data && !handoffQuery.data.ready && (
        <p className="marketing-lead-detail__blockers">
          {t('detail.blockers')}: {handoffQuery.data.blockers.join(', ')}
        </p>
      )}
    </main>
  );
}
