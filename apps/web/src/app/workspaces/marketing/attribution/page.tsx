'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState } from '@investhome/ui';

import { marketingQueries } from '@/lib/query/marketing-queries';
import { canViewCampaignAttribution } from '@/lib/marketing/marketing-permissions';
import { useAuth } from '@/lib/auth/auth-context';

import { StatusGrid } from '../dashboard/_components/analytics-widgets';
import { SummaryWidget } from '../_components/summary-widget';

export default function MarketingAttributionPage() {
  const t = useTranslations('marketing.modules.attribution');
  const tAnalytics = useTranslations('marketing.analytics');
  const tCommon = useTranslations('marketing.common');
  const tGlobal = useTranslations('common');
  const tNav = useTranslations('marketing.analytics.tabs');
  const { user } = useAuth();
  const canView = canViewCampaignAttribution(user);

  const healthQuery = useQuery({
    ...marketingQueries.dashboardAttributionHealth(),
    enabled: canView,
  });

  if (!canView) {
    return (
      <main className="dashboard marketing-module-shell">
        <header className="dashboard__header">
          <h1 className="dashboard__title">{t('title')}</h1>
          <p className="dashboard__subtitle">{t('description')}</p>
        </header>
        <EmptyState title={tCommon('permissionRestricted')} description={tCommon('permissionRestrictedDescription')} />
      </main>
    );
  }

  return (
    <main className="dashboard marketing-module-shell">
      <header className="dashboard__header dashboard__header--row">
        <div>
          <h1 className="dashboard__title">{t('title')}</h1>
          <p className="dashboard__subtitle">{t('description')}</p>
        </div>
        <Link href={'/workspaces/marketing/dashboard/tracking' as Route} className="button">
          {tNav('tracking')}
        </Link>
      </header>

      {healthQuery.isLoading ? (
        <LoadingState label={tCommon('loading')} />
      ) : healthQuery.isError ? (
        <ErrorState
          title={tCommon('error')}
          message={healthQuery.error?.message ?? tAnalytics('loadFailed')}
          action={
            <Button type="button" onClick={() => void healthQuery.refetch()}>
              {tGlobal('retry')}
            </Button>
          }
        />
      ) : !healthQuery.data ? (
        <EmptyState title={tCommon('notConnected')} description={tCommon('notConnected')} />
      ) : (
        <>
          <div className="marketing-summary-row">
            <SummaryWidget title={tAnalytics('dataFreshness')} state="ready" value={healthQuery.data.overall_status} />
          </div>
          {healthQuery.data.categories.length > 0 ? (
            <section className="marketing-dashboard__section">
              <h2 className="marketing-dashboard__section-title">{tAnalytics('sections.health')}</h2>
              <StatusGrid items={healthQuery.data.categories} />
            </section>
          ) : (
            <EmptyState title={tAnalytics('empty')} description={tCommon('noData')} />
          )}
        </>
      )}
    </main>
  );
}
