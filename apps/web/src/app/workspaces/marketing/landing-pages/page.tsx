'use client';

import { useMemo } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/auth-context';
import { hasMarketingPermission } from '@/lib/marketing/marketing-permissions';
import { fetchLandingPages, type LandingPageSummary } from '@/workspaces/marketing/api/landing-pages';

import { AdminDataTable, type AdminTableColumn } from '@/app/dashboard/admin/_components/admin-data-table';

export default function MarketingLandingPagesPage() {
  const t = useTranslations('marketing.landingPages');
  const tCommon = useTranslations('marketing.common');
  const { user } = useAuth();

  const listQuery = useQuery({
    queryKey: ['marketing', 'landingPages', 'list'],
    queryFn: () => fetchLandingPages(),
    enabled: hasMarketingPermission(user, 'manage_landing_pages'),
  });

  const columns = useMemo<AdminTableColumn<LandingPageSummary>[]>(
    () => [
      { id: 'name', header: t('columns.name'), render: (row) => row.name },
      { id: 'slug', header: t('columns.slug'), render: (row) => row.slug },
      {
        id: 'status',
        header: t('columns.status'),
        render: (row) => <StatusChip>{row.status}</StatusChip>,
      },
    ],
    [t],
  );

  if (!hasMarketingPermission(user, 'manage_landing_pages')) {
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
        <AdminDataTable columns={columns} rows={listQuery.data?.items ?? []} rowKey={(row) => row.id} />
      )}
    </main>
  );
}
