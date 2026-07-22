'use client';

import { useParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import { leadSourcesQueries } from '@/workspaces/marketing/hooks/use-lead-sources';

export default function LeadSourceDetailPage() {
  const params = useParams<{ sourceId: string }>();
  const t = useTranslations('marketing.sources');
  const tCommon = useTranslations('marketing.common');
  const detailQuery = useQuery(leadSourcesQueries.detail(params.sourceId));

  if (detailQuery.isLoading) return <LoadingState label={tCommon('loading')} />;
  if (detailQuery.isError) {
    return <ErrorState title={tCommon('error')} message={detailQuery.error?.message ?? tCommon('error')} />;
  }

  const source = detailQuery.data;
  if (!source) return <EmptyState title={tCommon('error')} description={tCommon('empty')} />;

  return (
    <main className="dashboard marketing-source-detail">
      <header className="dashboard__header">
        <h1 className="dashboard__title">{source.name}</h1>
        {source.description ? <p className="dashboard__subtitle">{source.description}</p> : null}
      </header>
      <dl className="marketing-detail-dl">
        <dt>{t('columns.type')}</dt>
        <dd>{source.source_type}</dd>
        <dt>{t('columns.tracking')}</dt>
        <dd>
          <StatusChip tone={source.tracking_readiness === 'ready' ? 'success' : 'warning'}>
            {source.tracking_readiness}
          </StatusChip>
        </dd>
        <dt>{t('columns.code')}</dt>
        <dd>{source.tracking_code ?? '—'}</dd>
      </dl>
    </main>
  );
}
