'use client';

import { useTranslations } from 'next-intl';
import { useQuery, type UseQueryOptions } from '@tanstack/react-query';

import { Button, ErrorState, LoadingState } from '@investhome/ui';

import { canViewMarketingDashboard } from '@/lib/marketing/marketing-permissions';
import { useAuth } from '@/lib/auth/auth-context';

import { DashboardPageShell } from '../_components/dashboard-shell';

type AnalyticsSectionPageProps<T> = {
  titleKey: string;
  subtitleKey: string;
  queryOptions: UseQueryOptions<T>;
  render: (
    data: T,
    t: ((key: string) => string) & { has: (key: string) => boolean },
  ) => React.ReactNode;
};

export function AnalyticsSectionPage<T>({
  titleKey,
  subtitleKey,
  queryOptions,
  render,
}: AnalyticsSectionPageProps<T>) {
  const t = useTranslations('marketing.analytics');
  const tCommon = useTranslations('common');
  const { user, loading: authLoading } = useAuth();
  const canView = canViewMarketingDashboard(user);

  const query = useQuery({
    ...queryOptions,
    enabled: !authLoading && canView && (queryOptions.enabled ?? true),
  });

  if (authLoading) {
    return (
      <DashboardPageShell title={t(titleKey as 'executive.title')} subtitle={t(subtitleKey as 'executive.subtitle')}>
        <LoadingState label={tCommon('loading')} />
      </DashboardPageShell>
    );
  }

  if (!canView) {
    return (
      <DashboardPageShell title={t(titleKey as 'executive.title')} subtitle={t(subtitleKey as 'executive.subtitle')}>
        <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />
      </DashboardPageShell>
    );
  }

  if (query.isLoading) {
    return (
      <DashboardPageShell title={t(titleKey as 'executive.title')} subtitle={t(subtitleKey as 'executive.subtitle')}>
        <LoadingState label={tCommon('loading')} />
      </DashboardPageShell>
    );
  }

  if (query.isError || !query.data) {
    return (
      <DashboardPageShell title={t(titleKey as 'executive.title')} subtitle={t(subtitleKey as 'executive.subtitle')}>
        <ErrorState
          title={t('loadFailed')}
          message={query.error?.message ?? t('loadFailed')}
          action={
            <Button type="button" onClick={() => void query.refetch()}>
              {tCommon('retry')}
            </Button>
          }
        />
      </DashboardPageShell>
    );
  }

  return (
    <DashboardPageShell title={t(titleKey as 'executive.title')} subtitle={t(subtitleKey as 'executive.subtitle')}>
      {render(query.data, t)}
    </DashboardPageShell>
  );
}
