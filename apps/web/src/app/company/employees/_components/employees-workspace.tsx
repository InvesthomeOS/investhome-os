'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { EmptyState, ErrorState, LoadingState, PageHeader, StatusChip } from '@investhome/ui';

import { fetchUsers, type UserRecord } from '@/lib/api/auth';
import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';

import { CompanyDataTable, type CompanyTableColumn } from '../../_components/company-data-table';
import { CompanyFilters, DEFAULT_COMPANY_FILTERS, type CompanyFilterState } from '../../_components/company-filters';

function canViewEmployees(user: ReturnType<typeof useAuth>['user']): boolean {
  return Boolean(user && hasPermission(user, 'users', 'view'));
}

export function EmployeesWorkspace() {
  const t = useTranslations('company.employees');
  const tCommon = useTranslations('common');
  const { user } = useAuth();
  const [draftFilters, setDraftFilters] = useState<CompanyFilterState>(DEFAULT_COMPANY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<CompanyFilterState>(DEFAULT_COMPANY_FILTERS);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const listQuery = useQuery({
    queryKey: ['company', 'employees', appliedFilters.search, appliedFilters.status],
    queryFn: () =>
      fetchUsers({
        search: appliedFilters.search || undefined,
        status: appliedFilters.status || undefined,
      }),
    enabled: canViewEmployees(user),
  });

  const columns: CompanyTableColumn<UserRecord>[] = useMemo(
    () => [
      {
        id: 'name',
        header: t('columns.name'),
        sortable: true,
        exportValue: (row) => row.full_name,
        render: (row) => row.full_name,
      },
      {
        id: 'email',
        header: t('columns.email'),
        exportValue: (row) => row.email,
        render: (row) => row.email,
      },
      {
        id: 'jobTitle',
        header: t('columns.jobTitle'),
        exportValue: (row) => row.job_title ?? '',
        render: (row) => row.job_title ?? '—',
      },
      {
        id: 'department',
        header: t('columns.department'),
        exportValue: (row) => row.department ?? '',
        render: (row) => row.department ?? '—',
      },
      {
        id: 'status',
        header: t('columns.status'),
        exportValue: (row) => row.status,
        render: (row) => <StatusChip tone={row.status === 'active' ? 'success' : 'default'}>{row.status}</StatusChip>,
      },
    ],
    [t],
  );

  if (!canViewEmployees(user)) {
    return (
      <main className="dashboard company-dashboard">
        <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />
      </main>
    );
  }

  const rows = listQuery.data?.items ?? [];

  return (
    <main className="dashboard company-dashboard">
      <PageHeader eyebrow={t('eyebrow')} title={t('title')} subtitle={t('subtitle')} />

      <CompanyFilters
        filters={draftFilters}
        onChange={setDraftFilters}
        onApply={() => setAppliedFilters(draftFilters)}
        onReset={() => {
          setDraftFilters(DEFAULT_COMPANY_FILTERS);
          setAppliedFilters(DEFAULT_COMPANY_FILTERS);
        }}
        showDate={false}
        statusOptions={[
          { value: '', label: t('allStatuses') },
          { value: 'active', label: t('statusActive') },
          { value: 'inactive', label: t('statusInactive') },
          { value: 'suspended', label: t('statusSuspended') },
        ]}
      />

      {listQuery.isLoading ? <LoadingState label={t('loading')} /> : null}
      {listQuery.isError ? <ErrorState title={t('loadError')} message={t('loadError')} /> : null}

      {!listQuery.isLoading && !listQuery.isError && rows.length === 0 ? (
        <EmptyState title={t('emptyTitle')} description={t('emptyHint')} />
      ) : null}

      {rows.length > 0 ? (
        <CompanyDataTable
          rows={rows}
          columns={columns}
          rowKey={(row) => row.id}
          activeRowKey={selectedId}
          onRowClick={(row) => setSelectedId(row.id)}
          exportFileName="company-employees.csv"
          emptyMessage={tCommon('noResults')}
        />
      ) : null}

      <p className="company-workspace-note">
        {t('adminLinkPrefix')}{' '}
        <Link href="/dashboard/admin/users">{t('adminLinkLabel')}</Link>
      </p>
    </main>
  );
}
