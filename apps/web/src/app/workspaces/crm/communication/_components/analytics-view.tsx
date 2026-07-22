'use client';

import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';

import { EmptyState, ErrorState, KpiCard, LoadingState } from '@investhome/ui';

import { canViewCommAnalytics } from '@/lib/crm/crm-permissions';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { communicationQueries } from '@/workspaces/crm/hooks/use-communication';

export function AnalyticsView() {
  const t = useTranslations('crm.communication.analytics');
  const tCommon = useTranslations('common');
  const { authLoading, user, canViewCommunications } = useCrmAccess();
  const canViewAnalytics = canViewCommAnalytics(user);
  const analyticsQuery = useQuery({
    ...communicationQueries.analytics(),
    enabled: !authLoading && canViewAnalytics,
  });

  if (authLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (!canViewCommunications) {
    return <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />;
  }

  if (!canViewAnalytics) {
    return <ErrorState title={t('analyticsDenied')} message={t('analyticsDeniedHint')} />;
  }

  if (analyticsQuery.isLoading) {
    return <LoadingState label={t('loading')} />;
  }

  const metrics = analyticsQuery.data?.metrics ?? [];

  return (
    <div className="crm-communication-subview">
      <header className="crm-communication-subview__header">
        <h2>{t('title')}</h2>
        <p>{t('subtitle')}</p>
      </header>
      {metrics.length === 0 ? (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      ) : (
        <div className="crm-dashboard__grid">
          {metrics.map((metric) => (
            <KpiCard
              key={metric.key}
              label={metric.label}
              value={
                metric.unavailable
                  ? t('unavailable')
                  : metric.value != null
                    ? String(metric.value)
                    : '—'
              }
              delta={metric.unavailable ? metric.unavailable_reason ?? undefined : undefined}
            />
          ))}
        </div>
      )}
    </div>
  );
}
