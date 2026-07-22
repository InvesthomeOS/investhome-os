'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useLocale, useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, KpiCard, LoadingState } from '@investhome/ui';

import { formatActivityDate } from '@/lib/api/activity';
import {
  canCreateCompany,
  canReadCompany,
  canUpdateCompany,
} from '@/lib/company/company-permissions';
import { companyQueries } from '@/lib/query/company-queries';
import { useAuth } from '@/lib/auth/auth-context';
import { useActivityLabels } from '@/lib/i18n/activity-labels';

type QuickAction = {
  labelKey: string;
  href: string;
  permission: 'create' | 'update' | 'read';
  disabled?: boolean;
};

const QUICK_ACTIONS: QuickAction[] = [
  { labelKey: 'quickActions.createCompany', href: '/company/companies', permission: 'create' },
  { labelKey: 'quickActions.inviteEmployee', href: '/company/employees', permission: 'create' },
  { labelKey: 'quickActions.addBranch', href: '/company/branches', permission: 'update' },
  { labelKey: 'quickActions.uploadDocument', href: '/company/documents', permission: 'update' },
  { labelKey: 'quickActions.createDepartment', href: '/company/departments', permission: 'update' },
];

const KPI_KEYS = [
  'total_companies',
  'active_companies',
  'branches',
  'employees',
  'departments',
  'teams',
  'pending_tasks',
] as const;

export function CompanyDashboard() {
  const t = useTranslations('company');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { user } = useAuth();
  const { getActionLabel, getEntityTypeLabel, getDescription } = useActivityLabels();

  const canView = canReadCompany(user);
  const dashboardQuery = useQuery({
    ...companyQueries.dashboard(),
    enabled: canView,
  });
  const activityQuery = useQuery({
    ...companyQueries.recentActivity(12),
    enabled: canView,
  });

  if (!canView) {
    return (
      <main className="dashboard company-dashboard">
        <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />
      </main>
    );
  }

  if (dashboardQuery.isLoading) {
    return (
      <main className="dashboard company-dashboard">
        <LoadingState label={tCommon('loading')} />
      </main>
    );
  }

  if (dashboardQuery.isError) {
    return (
      <main className="dashboard company-dashboard">
        <ErrorState
          title={t('loadFailed')}
          message={dashboardQuery.error?.message ?? t('loadFailed')}
          action={
            <Button type="button" onClick={() => void dashboardQuery.refetch()}>
              {tCommon('retry')}
            </Button>
          }
        />
      </main>
    );
  }

  const kpis = dashboardQuery.data;

  return (
    <main className="dashboard company-dashboard">
      <header className="dashboard__header">
        <p className="dashboard__eyebrow">{t('eyebrow')}</p>
        <h1 className="dashboard__title">{t('title')}</h1>
        <p className="dashboard__subtitle">{t('subtitle')}</p>
      </header>

      <section className="company-dashboard__kpi-row" aria-label={t('kpi.section')}>
        {KPI_KEYS.map((key) => (
          <KpiCard
            key={key}
            label={t(`kpi.${key}` as 'kpi.total_companies')}
            value={kpis?.[key] ?? 0}
          />
        ))}
      </section>

      <section className="company-dashboard__quick-actions">
        <h2 className="company-dashboard__section-title">{t('quickActions.title')}</h2>
        <div className="company-dashboard__quick-actions-row">
          {QUICK_ACTIONS.map((action) => {
            const allowed =
              action.permission === 'create'
                ? canCreateCompany(user)
                : action.permission === 'update'
                  ? canUpdateCompany(user)
                  : canReadCompany(user);
            if (!allowed) {
              return null;
            }
            return (
              <Link key={action.labelKey} href={action.href as Route} className="company-dashboard__quick-action">
                {t(action.labelKey as 'quickActions.createCompany')}
              </Link>
            );
          })}
        </div>
      </section>

      <section className="company-dashboard__activity">
        <div className="company-dashboard__activity-header">
          <h2 className="company-dashboard__section-title">{t('activity.title')}</h2>
          <span className="company-dashboard__activity-count">
            {activityQuery.data?.total ?? 0}
          </span>
        </div>

        {activityQuery.isLoading ? (
          <LoadingState label={tCommon('loading')} />
        ) : activityQuery.isError ? (
          <ErrorState
            title={t('activity.loadFailed')}
            message={activityQuery.error?.message}
            action={
              <Button type="button" onClick={() => void activityQuery.refetch()}>
                {tCommon('retry')}
              </Button>
            }
          />
        ) : activityQuery.data && activityQuery.data.items.length === 0 ? (
          <EmptyState title={t('activity.empty')} description={t('activity.emptyHint')} />
        ) : (
          <ol className="company-dashboard__timeline">
            {activityQuery.data?.items.map((item) => (
              <li key={item.id} className="company-dashboard__timeline-item">
                <div className="company-dashboard__timeline-marker" aria-hidden="true" />
                <div className="company-dashboard__timeline-body">
                  <p className="company-dashboard__timeline-title">
                    {getDescription(
                      item.description_key,
                      item.metadata as Record<string, string> | undefined,
                    )}
                  </p>
                  <p className="company-dashboard__timeline-meta">
                    {getActionLabel(item.action)} · {getEntityTypeLabel(item.entity_type)}
                    {item.entity_label ? ` · ${item.entity_label}` : ''}
                  </p>
                  <time className="company-dashboard__timeline-time" dateTime={item.created_at}>
                    {formatActivityDate(item.created_at, locale)}
                  </time>
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>
    </main>
  );
}
