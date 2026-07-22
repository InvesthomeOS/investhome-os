'use client';

import { useParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { EmptyState, LoadingState } from '@investhome/ui';

import { audienceQueries } from '@/workspaces/marketing/hooks/use-audiences';

import { WidgetDataDisplay } from '../../../_components/widget-data-display';

export default function AudienceConsentPage() {
  const params = useParams<{ audienceId: string }>();
  const t = useTranslations('marketing.audiences.consent');
  const tCommon = useTranslations('marketing.common');
  const detailQuery = useQuery(audienceQueries.detail(params.audienceId));
  const readinessQuery = useQuery(audienceQueries.readiness(params.audienceId));

  if (detailQuery.isLoading || readinessQuery.isLoading) return <LoadingState label={tCommon('loading')} />;

  const consent = detailQuery.data?.consent_requirements_json;
  const blockers = readinessQuery.data?.blockers ?? [];

  if (!consent && blockers.length === 0) {
    return <EmptyState title={t('empty')} description={t('emptyDescription')} />;
  }

  return (
    <section className="marketing-detail-panel">
      {consent ? (
        <>
          <h2 className="marketing-dashboard__section-title">{t('requirements')}</h2>
          <WidgetDataDisplay data={consent} emptyLabel={tCommon('noData')} />
        </>
      ) : null}
      {blockers.length > 0 ? (
        <>
          <h2 className="marketing-dashboard__section-title">{t('blockers')}</h2>
          <ul className="marketing-list">
            {blockers.map((blocker) => (
              <li key={blocker}>{blocker}</li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}
