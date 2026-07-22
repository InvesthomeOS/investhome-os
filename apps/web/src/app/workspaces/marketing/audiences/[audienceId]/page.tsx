'use client';

import { useParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { EmptyState, LoadingState } from '@investhome/ui';

import { audienceQueries } from '@/workspaces/marketing/hooks/use-audiences';

import { UnavailableValue } from '../../_components/summary-widget';

export default function AudienceOverviewPage() {
  const params = useParams<{ audienceId: string }>();
  const t = useTranslations('marketing.audiences');
  const tCommon = useTranslations('marketing.common');
  const detailQuery = useQuery(audienceQueries.detail(params.audienceId));

  if (detailQuery.isLoading) return <LoadingState label={tCommon('loading')} />;

  const audience = detailQuery.data;
  if (!audience) return <EmptyState title={tCommon('error')} />;

  return (
    <section className="marketing-detail-panel">
      <p>{audience.description ?? t('detail.noDescription')}</p>
      <dl>
        <dt>{t('detail.mode')}</dt>
        <dd>{audience.mode}</dd>
        <dt>{t('detail.type')}</dt>
        <dd>{audience.audience_type}</dd>
        <dt>{t('detail.language')}</dt>
        <dd>{audience.language ?? <UnavailableValue label={tCommon('noData')} />}</dd>
      </dl>
    </section>
  );
}
