'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useMemo } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { EmptyState, ErrorState, LoadingState } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/auth-context';
import { hasMarketingPermission } from '@/lib/marketing/marketing-permissions';
import { leadSourcesQueries } from '@/workspaces/marketing/hooks/use-lead-sources';
import type { LeadSourceSummary } from '@/workspaces/marketing/api/lead-sources';

import { AdminDataTable, type AdminTableColumn } from '@/app/dashboard/admin/_components/admin-data-table';

import { SummaryWidget, UnavailableValue } from '../_components/summary-widget';

export default function LeadSourcesPage() {
  const t = useTranslations('marketing.sources');
  const tCommon = useTranslations('marketing.common');
  const { user } = useAuth();

  const listQuery = useQuery(leadSourcesQueries.list(1));
  const summaryQuery = useQuery(leadSourcesQueries.summary());
  const hierarchyQuery = useQuery(leadSourcesQueries.hierarchy());

  const columns = useMemo<AdminTableColumn<LeadSourceSummary>[]>(
    () => [
      {
        id: 'name',
        header: t('columns.name'),
        render: (row) => <Link href={`/workspaces/marketing/sources/${row.id}` as Route}>{row.name}</Link>,
      },
      {
        id: 'type',
        header: t('columns.type'),
        render: (row) => row.source_type,
      },
      {
        id: 'tracking',
        header: t('columns.tracking'),
        render: (row) => row.tracking_readiness ?? <UnavailableValue label={tCommon('notCalculated')} />,
      },
      {
        id: 'code',
        header: t('columns.code'),
        render: (row) => row.tracking_code ?? <UnavailableValue label={tCommon('noData')} />,
      },
    ],
    [t, tCommon],
  );

  if (!hasMarketingPermission(user, 'view')) {
    return <EmptyState title={tCommon('permissionRestricted')} description={tCommon('permissionRestrictedDescription')} />;
  }
  if (listQuery.isLoading) return <LoadingState label={tCommon('loading')} />;
  if (listQuery.isError) {
    return (
      <ErrorState
        title={tCommon('error')}
        message={listQuery.error instanceof ApiError ? listQuery.error.message : tCommon('error')}
      />
    );
  }

  return (
    <main className="dashboard marketing-sources">
      <header className="dashboard__header">
        <div>
          <h1 className="dashboard__title">{t('title')}</h1>
          <p className="dashboard__subtitle">{t('description')}</p>
        </div>
        {hasMarketingPermission(user, 'create') && (
          <Link href={'/workspaces/marketing/sources/new' as Route} className="button">
            {t('create')}
          </Link>
        )}
      </header>
      <div className="marketing-summary-row">
        <SummaryWidget title={t('summary.total')} state={summaryQuery.isLoading ? 'loading' : 'ready'} value={summaryQuery.data?.total ?? 0} />
        <SummaryWidget title={t('summary.active')} state={summaryQuery.isLoading ? 'loading' : 'ready'} value={summaryQuery.data?.active ?? 0} />
      </div>
      {hierarchyQuery.data?.items?.length ? (
        <section className="marketing-sources__hierarchy">
          <h2>{t('hierarchy')}</h2>
          <ul>
            {hierarchyQuery.data.items.map((node) => (
              <li key={node.id}>{node.name}</li>
            ))}
          </ul>
        </section>
      ) : null}
      <AdminDataTable columns={columns} rows={listQuery.data?.items ?? []} rowKey={(r) => r.id} />
    </main>
  );
}
