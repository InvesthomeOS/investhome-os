'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useMemo } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/auth-context';
import { hasMarketingPermission } from '@/lib/marketing/marketing-permissions';
import { audienceQueries } from '@/workspaces/marketing/hooks/use-audiences';
import type { AudienceSummary } from '@/workspaces/marketing/api/audiences';

import { AdminDataTable, type AdminTableColumn } from '@/app/dashboard/admin/_components/admin-data-table';

import { SummaryWidget, UnavailableValue } from '../../_components/summary-widget';

export function AudiencesWorkspace() {
  const t = useTranslations('marketing.audiences');
  const tCommon = useTranslations('marketing.common');
  const { user } = useAuth();
  const canCreate = hasMarketingPermission(user, 'create');

  const listQuery = useQuery(audienceQueries.list({ page: 1, page_size: 25 }));
  const summaryQuery = useQuery(audienceQueries.summary());

  const columns = useMemo<AdminTableColumn<AudienceSummary>[]>(
    () => [
      {
        id: 'name',
        header: t('columns.name'),
        render: (row) => (
          <Link href={`/workspaces/marketing/audiences/${row.id}` as Route}>{row.name}</Link>
        ),
      },
      {
        id: 'mode',
        header: t('columns.mode'),
        render: (row) => row.mode,
      },
      {
        id: 'status',
        header: t('columns.status'),
        render: (row) => <StatusChip tone={row.status === 'active' ? 'success' : 'default'}>{row.status}</StatusChip>,
      },
      {
        id: 'size',
        header: t('columns.size'),
        render: (row) =>
          row.calculated_size != null ? (
            String(row.calculated_size)
          ) : (
            <UnavailableValue label={tCommon('notCalculated')} />
          ),
      },
    ],
    [t, tCommon],
  );

  if (!hasMarketingPermission(user, 'view')) {
    return <EmptyState title={tCommon('permissionRestricted')} description={tCommon('permissionRestrictedDescription')} />;
  }

  if (listQuery.isLoading) return <LoadingState label={tCommon('loading')} />;
  if (listQuery.isError) {
    const err = listQuery.error;
    return (
      <ErrorState
        title={tCommon('error')}
        message={err instanceof ApiError ? err.message : tCommon('error')}
        action={
          <Button type="button" onClick={() => void listQuery.refetch()}>
            Retry
          </Button>
        }
      />
    );
  }

  const rows = listQuery.data?.items ?? [];

  return (
    <main className="dashboard marketing-audiences">
      <header className="dashboard__header">
        <div>
          <h1 className="dashboard__title">{t('title')}</h1>
          <p className="dashboard__subtitle">{t('description')}</p>
        </div>
        {canCreate && (
          <Link href={'/workspaces/marketing/audiences/new' as Route} className="button">
            {t('create')}
          </Link>
        )}
      </header>

      <div className="marketing-summary-row">
        <SummaryWidget
          title={t('summary.total')}
          state={summaryQuery.isLoading ? 'loading' : summaryQuery.isError ? 'error' : 'ready'}
          value={summaryQuery.data?.total ?? 0}
        />
        <SummaryWidget
          title={t('summary.active')}
          state={summaryQuery.isLoading ? 'loading' : summaryQuery.isError ? 'error' : 'ready'}
          value={summaryQuery.data?.active ?? 0}
        />
        <SummaryWidget
          title={t('summary.draft')}
          state={summaryQuery.isLoading ? 'loading' : summaryQuery.isError ? 'error' : 'ready'}
          value={summaryQuery.data?.draft ?? 0}
        />
      </div>

      {rows.length === 0 ? (
        <EmptyState title={t('empty.title')} description={t('empty.description')} />
      ) : (
        <AdminDataTable columns={columns} rows={rows} rowKey={(row) => row.id} />
      )}
    </main>
  );
}
