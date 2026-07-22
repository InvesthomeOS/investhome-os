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

type BudgetRow = {
  id: string;
  name: string;
  status: string;
  currency: string;
  planned_amount: string | null;
  spent_amount: string | null;
};

export default function MarketingBudgetsPage() {
  const t = useTranslations('marketing.budgets');
  const tCommon = useTranslations('marketing.common');
  const { user } = useAuth();

  const listQuery = useQuery({
    ...marketingQueries.budgets(),
    enabled: hasMarketingPermission(user, 'manage_budgets'),
  });

  const columns = useMemo<AdminTableColumn<BudgetRow>[]>(
    () => [
      { id: 'name', header: t('columns.name'), render: (row) => row.name },
      { id: 'currency', header: t('columns.currency'), render: (row) => row.currency },
      { id: 'planned', header: t('columns.planned'), render: (row) => row.planned_amount ?? tCommon('noData') },
      { id: 'spent', header: t('columns.spent'), render: (row) => row.spent_amount ?? tCommon('noData') },
      {
        id: 'status',
        header: t('columns.status'),
        render: (row) => <StatusChip>{row.status}</StatusChip>,
      },
    ],
    [t, tCommon],
  );

  if (!hasMarketingPermission(user, 'manage_budgets')) {
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
        <AdminDataTable columns={columns} rows={(listQuery.data?.items as BudgetRow[]) ?? []} rowKey={(row) => row.id} />
      )}
    </main>
  );
}
