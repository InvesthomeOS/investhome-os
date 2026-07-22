'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useMemo } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/auth-context';
import { hasMarketingPermission } from '@/lib/marketing/marketing-permissions';
import { segmentQueries } from '@/workspaces/marketing/hooks/use-segments';
import type { SegmentSummary } from '@/workspaces/marketing/api/segments';

import { AdminDataTable, type AdminTableColumn } from '@/app/dashboard/admin/_components/admin-data-table';

import { SummaryWidget, UnavailableValue } from '../_components/summary-widget';

export default function SegmentsWorkspacePage() {
  const t = useTranslations('marketing.segments');
  const tCommon = useTranslations('marketing.common');
  const { user } = useAuth();

  const listQuery = useQuery(segmentQueries.list(1));
  const summaryQuery = useQuery(segmentQueries.summary());

  const columns = useMemo<AdminTableColumn<SegmentSummary>[]>(
    () => [
      {
        id: 'name',
        header: t('columns.name'),
        render: (row) => <Link href={`/workspaces/marketing/segments/${row.id}` as Route}>{row.name}</Link>,
      },
      {
        id: 'type',
        header: t('columns.type'),
        render: (row) => row.segment_type,
      },
      {
        id: 'status',
        header: t('columns.calculation'),
        render: (row) => (
          <StatusChip tone={row.calculation_status === 'completed' ? 'success' : 'warning'}>
            {row.calculation_status}
          </StatusChip>
        ),
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
    return (
      <ErrorState
        title={tCommon('error')}
        message={listQuery.error instanceof ApiError ? listQuery.error.message : tCommon('error')}
      />
    );
  }

  return (
    <main className="dashboard marketing-segments">
      <header className="dashboard__header">
        <div>
          <h1 className="dashboard__title">{t('title')}</h1>
          <p className="dashboard__subtitle">{t('description')}</p>
        </div>
        {hasMarketingPermission(user, 'create') && (
          <Link href={'/workspaces/marketing/segments/new' as Route} className="button">
            {t('create')}
          </Link>
        )}
      </header>
      <div className="marketing-summary-row">
        <SummaryWidget title={t('summary.total')} state={summaryQuery.isLoading ? 'loading' : 'ready'} value={summaryQuery.data?.total ?? 0} />
        <SummaryWidget title={t('summary.calculated')} state={summaryQuery.isLoading ? 'loading' : 'ready'} value={summaryQuery.data?.calculated ?? 0} />
        <SummaryWidget title={t('summary.notCalculated')} state={summaryQuery.isLoading ? 'loading' : 'ready'} value={summaryQuery.data?.not_calculated ?? 0} />
      </div>
      <AdminDataTable columns={columns} rows={listQuery.data?.items ?? []} rowKey={(r) => r.id} />
    </main>
  );
}
