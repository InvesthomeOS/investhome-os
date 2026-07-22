'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState, PageHeader, StatusChip } from '@investhome/ui';

import type { DepartmentSummary } from '@/lib/api/departments';
import { exportDepartmentsCsv } from '@/lib/api/departments';
import {
  canExportDepartments,
  canReadDepartment,
} from '@/lib/company/department-permissions';
import { departmentQueries } from '@/lib/query/department-queries';
import { useAuth } from '@/lib/auth/auth-context';

import { CompanyDataTable, type CompanyTableColumn } from '../../_components/company-data-table';
import { CompanyFilters, DEFAULT_COMPANY_FILTERS, type CompanyFilterState } from '../../_components/company-filters';

export function DepartmentsWorkspace() {
  const t = useTranslations('company.departments');
  const tCommon = useTranslations('common');
  const { user } = useAuth();

  const [draftFilters, setDraftFilters] = useState<CompanyFilterState>(DEFAULT_COMPANY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<CompanyFilterState>(DEFAULT_COMPANY_FILTERS);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const listParams = useMemo(
    () => ({
      search: appliedFilters.search || undefined,
      status: appliedFilters.status || undefined,
      company_id: appliedFilters.companyId || undefined,
      branch_id: appliedFilters.branchId || undefined,
      sort_by: 'updated_at',
      sort_dir: 'desc' as const,
      page: 1,
      page_size: 100,
    }),
    [appliedFilters],
  );

  const listQuery = useQuery({
    ...departmentQueries.list(listParams),
    enabled: canReadDepartment(user),
  });

  const columns: CompanyTableColumn<DepartmentSummary>[] = useMemo(
    () => [
      {
        id: 'code',
        header: t('columns.code'),
        sortable: true,
        exportValue: (row) => row.department_code,
        render: (row) => row.department_code,
      },
      {
        id: 'name',
        header: t('columns.name'),
        sortable: true,
        exportValue: (row) => row.department_name,
        render: (row) => row.department_name,
      },
      {
        id: 'company',
        header: t('columns.company'),
        exportValue: (row) => row.company_name ?? '',
        render: (row) => row.company_name ?? '—',
      },
      {
        id: 'branch',
        header: t('columns.branch'),
        exportValue: (row) => row.branch_name ?? '',
        render: (row) => row.branch_name ?? '—',
      },
      {
        id: 'head',
        header: t('columns.head'),
        exportValue: (row) => row.head_name ?? '',
        render: (row) => row.head_name ?? '—',
      },
      {
        id: 'employees',
        header: t('columns.employees'),
        sortable: true,
        exportValue: (row) => String(row.employee_count),
        render: (row) => row.employee_count,
      },
      {
        id: 'teams',
        header: t('columns.teams'),
        exportValue: (row) => String(row.team_count),
        render: (row) => row.team_count,
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

  if (!canReadDepartment(user)) {
    return (
      <main className="dashboard company-dashboard">
        <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />
      </main>
    );
  }

  const rows = listQuery.data?.items ?? [];

  return (
    <main className="dashboard company-dashboard">
      <PageHeader
        eyebrow={t('eyebrow')}
        title={t('title')}
        subtitle={t('subtitle')}
        actions={
          canExportDepartments(user) ? (
            <Button
              type="button"
              variant="secondary"
              onClick={async () => {
                const blob = await exportDepartmentsCsv(listParams);
                const url = URL.createObjectURL(blob);
                const anchor = document.createElement('a');
                anchor.href = url;
                anchor.download = 'departments-export.csv';
                anchor.click();
                URL.revokeObjectURL(url);
              }}
            >
              {t('export')}
            </Button>
          ) : null
        }
      />

      <CompanyFilters
        filters={draftFilters}
        onChange={setDraftFilters}
        onApply={() => setAppliedFilters(draftFilters)}
        onReset={() => {
          setDraftFilters(DEFAULT_COMPANY_FILTERS);
          setAppliedFilters(DEFAULT_COMPANY_FILTERS);
        }}
        showCompany
        showBranch
        statusOptions={[
          { value: '', label: t('allStatuses') },
          { value: 'active', label: t('statusActive') },
          { value: 'draft', label: t('statusDraft') },
          { value: 'inactive', label: t('statusInactive') },
          { value: 'archived', label: t('statusArchived') },
        ]}
      />

      {listQuery.isLoading ? <LoadingState label={t('loading')} /> : null}
      {listQuery.isError ? (
        <ErrorState title={t('loadError')} message={t('loadError')} />
      ) : null}

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
          exportFileName="company-departments.csv"
          emptyMessage={tCommon('noResults')}
        />
      ) : null}
    </main>
  );
}
