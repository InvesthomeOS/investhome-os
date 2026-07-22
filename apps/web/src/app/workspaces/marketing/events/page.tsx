'use client';

import { useMemo } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/auth-context';
import { hasMarketingPermission } from '@/lib/marketing/marketing-permissions';
import { marketingQueries } from '@/lib/query/marketing-queries';

import { AdminDataTable, type AdminTableColumn } from '@/app/dashboard/admin/_components/admin-data-table';

type EventRow = {
  id: string;
  name: string;
  event_type: string;
  status: string;
  start_at: string | null;
};

export default function MarketingEventsPage() {
  const t = useTranslations('marketing.events');
  const tCommon = useTranslations('marketing.common');
  const { user } = useAuth();

  const listQuery = useQuery({
    ...marketingQueries.events(),
    enabled: hasMarketingPermission(user, 'manage_events'),
  });

  const columns = useMemo<AdminTableColumn<EventRow>[]>(
    () => [
      { id: 'name', header: t('columns.name'), render: (row) => row.name },
      { id: 'type', header: t('columns.type'), render: (row) => row.event_type },
      { id: 'start', header: t('columns.start'), render: (row) => row.start_at ?? tCommon('noData') },
      {
        id: 'status',
        header: t('columns.status'),
        render: (row) => <StatusChip>{row.status}</StatusChip>,
      },
    ],
    [t, tCommon],
  );

  if (!hasMarketingPermission(user, 'manage_events')) {
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
      <header className="dashboard__header">
        <h1 className="dashboard__title">{t('title')}</h1>
        <p className="dashboard__subtitle">{t('description')}</p>
      </header>
      {listQuery.isLoading ? (
        <LoadingState label={tCommon('loading')} />
      ) : listQuery.isError ? (
        <ErrorState
          title={tCommon('error')}
          message={listQuery.error instanceof ApiError ? listQuery.error.message : tCommon('error')}
        />
      ) : listQuery.data?.total === 0 ? (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      ) : (
        <AdminDataTable columns={columns} rows={(listQuery.data?.items as EventRow[]) ?? []} rowKey={(row) => row.id} />
      )}
    </main>
  );
}
