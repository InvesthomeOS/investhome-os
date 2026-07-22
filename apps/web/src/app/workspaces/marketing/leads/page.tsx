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
import { marketingLeadsQueries } from '@/workspaces/marketing/hooks/use-marketing-leads';
import type { MarketingLeadSummary } from '@/workspaces/marketing/api/marketing-leads';

import { AdminDataTable, type AdminTableColumn } from '@/app/dashboard/admin/_components/admin-data-table';

import { SummaryWidget, UnavailableValue } from '../_components/summary-widget';

export default function MarketingLeadsPage() {
  const t = useTranslations('marketing.leads');
  const tCommon = useTranslations('marketing.common');
  const { user } = useAuth();

  const listQuery = useQuery(marketingLeadsQueries.list(1));
  const summaryQuery = useQuery(marketingLeadsQueries.summary());

  const columns = useMemo<AdminTableColumn<MarketingLeadSummary>[]>(
    () => [
      {
        id: 'id',
        header: t('columns.context'),
        render: (row) => <Link href={`/workspaces/marketing/leads/${row.id}` as Route}>{row.id.slice(0, 8)}</Link>,
      },
      {
        id: 'utm',
        header: t('columns.utmSource'),
        render: (row) =>
          (row.utm_data_json as { utm_source?: string } | null)?.utm_source ?? (
            <UnavailableValue label={tCommon('noData')} />
          ),
      },
      {
        id: 'handoff',
        header: t('columns.handoff'),
        render: (row) => (
          <StatusChip tone={row.handoff_status === 'ready' ? 'success' : 'default'}>
            {t.has(`handoffStatus.${row.handoff_status}`)
              ? t(`handoffStatus.${row.handoff_status}` as 'handoffStatus.ready')
              : row.handoff_status.replace(/_/g, ' ')}
          </StatusChip>
        ),
      },
      {
        id: 'campaign',
        header: t('columns.campaign'),
        render: (row) => row.campaign_id ?? <UnavailableValue label={tCommon('noData')} />,
      },
    ],
    [t, tCommon],
  );

  if (!hasMarketingPermission(user, 'view_leads')) {
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
    <main className="dashboard marketing-leads">
      <header className="dashboard__header">
        <h1 className="dashboard__title">{t('title')}</h1>
        <p className="dashboard__subtitle">{t('description')}</p>
      </header>
      <div className="marketing-summary-row">
        <SummaryWidget title={t('summary.total')} state={summaryQuery.isLoading ? 'loading' : 'ready'} value={summaryQuery.data?.total ?? 0} />
        <SummaryWidget title={t('summary.ready')} state={summaryQuery.isLoading ? 'loading' : 'ready'} value={summaryQuery.data?.ready_for_handoff ?? 0} />
        <SummaryWidget title={t('summary.blocked')} state={summaryQuery.isLoading ? 'loading' : 'ready'} value={summaryQuery.data?.blocked ?? 0} />
      </div>
      <AdminDataTable columns={columns} rows={listQuery.data?.items ?? []} rowKey={(r) => r.id} />
    </main>
  );
}
