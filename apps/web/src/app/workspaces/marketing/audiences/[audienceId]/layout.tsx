'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { notFound, useParams, usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { audienceQueries } from '@/workspaces/marketing/hooks/use-audiences';

import { SummaryWidget, UnavailableValue } from '../../_components/summary-widget';

const TABS = ['overview', 'members', 'segments', 'campaigns', 'consent', 'activity', 'settings'] as const;

export default function AudienceDetailLayout({ children }: { children: React.ReactNode }) {
  const params = useParams<{ audienceId: string }>();
  const pathname = usePathname();
  const t = useTranslations('marketing.audiences');
  const tCommon = useTranslations('marketing.common');
  const audienceId = params.audienceId;
  const basePath = `/workspaces/marketing/audiences/${audienceId}`;

  const detailQuery = useQuery(audienceQueries.detail(audienceId));
  const readinessQuery = useQuery(audienceQueries.readiness(audienceId));

  if (detailQuery.isLoading) return <LoadingState label={tCommon('loading')} />;
  if (detailQuery.isError) {
    if (detailQuery.error instanceof ApiError && detailQuery.error.status === 404) {
      notFound();
    }
    return (
      <ErrorState
        title={tCommon('error')}
        message={detailQuery.error instanceof ApiError ? detailQuery.error.message : tCommon('error')}
      />
    );
  }
  if (!detailQuery.data) {
    notFound();
  }

  const audience = detailQuery.data;
  const activeTab =
    TABS.find((tab) => pathname === `${basePath}/${tab}` || (tab === 'overview' && pathname === basePath)) ??
    'overview';

  return (
    <main className="dashboard marketing-audience-detail">
      <header className="dashboard__header">
        <div>
          <Link href={'/workspaces/marketing/audiences' as Route}>{t('back')}</Link>
          <h1 className="dashboard__title">{audience.name}</h1>
          <StatusChip tone={audience.status === 'active' ? 'success' : 'default'}>{audience.status}</StatusChip>
        </div>
      </header>
      <nav className="marketing-detail-tabs" aria-label={t('tabsAriaLabel')}>
        {TABS.map((tab) => {
          const href = tab === 'overview' ? basePath : `${basePath}/${tab}`;
          const isActive = activeTab === tab;
          return (
            <Link
              key={tab}
              href={href as Route}
              className={isActive ? 'marketing-detail-tabs__tab marketing-detail-tabs__tab--active' : 'marketing-detail-tabs__tab'}
              aria-current={isActive ? 'page' : undefined}
            >
              {t(`tabs.${tab}`)}
            </Link>
          );
        })}
      </nav>
      <div className="marketing-summary-row">
        <SummaryWidget
          title={t('detail.size')}
          state={audience.calculated_size != null ? 'ready' : 'not_calculated'}
          value={audience.calculated_size ?? undefined}
        />
        <SummaryWidget
          title={t('detail.readiness')}
          state={readinessQuery.isLoading ? 'loading' : 'ready'}
          value={readinessQuery.data?.state ?? <UnavailableValue label={tCommon('noData')} />}
        />
      </div>
      {children}
    </main>
  );
}
