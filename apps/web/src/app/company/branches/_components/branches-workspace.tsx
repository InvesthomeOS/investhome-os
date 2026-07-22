'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import {
  createBranch,
  exportBranchesCsv,
  updateBranch,
  archiveBranch,
  deactivateBranch,
  duplicateBranch,
  deleteBranch,
  assignBranchManager,
  type BranchDetail,
  type BranchInput,
  type BranchSummary,
} from '@/lib/api/branches';
import { ApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/auth-context';
import {
  canCreateBranch,
  canExportBranches,
  canReadBranch,
} from '@/lib/company/branch-permissions';
import { branchQueries, branchQueryKeys } from '@/lib/query/branch-queries';

import { AdminDataTable, type AdminTableColumn } from '@/app/dashboard/admin/_components/admin-data-table';

import { BranchDetailDrawer } from './branch-detail-drawer';
import { BranchFilters, type BranchFilterState } from './branch-filters';
import { BranchFormModal } from './branch-form-modal';

const DEFAULT_FILTERS: BranchFilterState = {
  search: '',
  page: 1,
  page_size: 25,
  sort_by: 'updated_at',
  sort_dir: 'desc',
  showAdvanced: false,
};

export function BranchesWorkspace() {
  const t = useTranslations('company.branches');
  const tTypes = useTranslations('company.branches.types');
  const tStatuses = useTranslations('company.branches.statuses');
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const [filters, setFilters] = useState<BranchFilterState>(DEFAULT_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<BranchFilterState>(DEFAULT_FILTERS);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [formMode, setFormMode] = useState<'create' | 'edit' | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const listQuery = useQuery(branchQueries.list(appliedFilters));
  const detailQuery = useQuery({
    ...branchQueries.detail(selectedId ?? ''),
    enabled: Boolean(selectedId) && drawerOpen,
  });

  const invalidate = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: branchQueryKeys.all });
  }, [queryClient]);

  const createMutation = useMutation({
    mutationFn: (payload: BranchInput) => createBranch(payload),
    onSuccess: async (result) => {
      await invalidate();
      setFormMode(null);
      setSelectedId(result.branch.id);
      setDrawerOpen(true);
    },
    onError: (error: Error) => setFormError(error.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<BranchInput> }) => updateBranch(id, payload),
    onSuccess: async () => {
      await invalidate();
      setFormMode(null);
    },
    onError: (error: Error) => setFormError(error.message),
  });

  const actionMutation = useMutation({
    mutationFn: async (action: { type: string; id: string }) => {
      switch (action.type) {
        case 'archive':
          return archiveBranch(action.id);
        case 'deactivate':
          return deactivateBranch(action.id);
        case 'duplicate':
          return duplicateBranch(action.id);
        case 'delete':
          return deleteBranch(action.id);
        case 'assign':
          return assignBranchManager(action.id, null);
        case 'transfer':
          return assignBranchManager(action.id, null);
        default:
          throw new Error('Unknown action');
      }
    },
    onSuccess: async () => {
      await invalidate();
      if (actionMutation.variables?.type === 'delete') {
        setDrawerOpen(false);
        setSelectedId(null);
      }
    },
  });

  useEffect(() => {
    setFormError(null);
  }, [formMode]);

  const columns = useMemo<AdminTableColumn<BranchSummary>[]>(
    () => [
      { id: 'code', header: t('columns.code'), sortable: true, exportValue: (row) => row.branch_code, render: (row) => row.branch_code },
      { id: 'name', header: t('columns.name'), sortable: true, exportValue: (row) => row.branch_name, render: (row) => row.branch_name },
      { id: 'company', header: t('columns.company'), exportValue: (row) => row.company_name ?? '', render: (row) => row.company_name ?? '—' },
      { id: 'type', header: t('columns.type'), exportValue: (row) => row.branch_type, render: (row) => tTypes(row.branch_type) },
      { id: 'city', header: t('columns.city'), sortable: true, exportValue: (row) => row.city, render: (row) => row.city },
      { id: 'country', header: t('columns.country'), exportValue: (row) => row.country, render: (row) => row.country },
      { id: 'manager', header: t('columns.manager'), exportValue: (row) => row.manager_name ?? '', render: (row) => row.manager_name ?? '—' },
      { id: 'employees', header: t('columns.employees'), exportValue: (row) => String(row.employee_count), render: (row) => row.employee_count },
      { id: 'departments', header: t('columns.departments'), exportValue: (row) => String(row.department_count), render: (row) => row.department_count },
      {
        id: 'status',
        header: t('columns.status'),
        exportValue: (row) => row.status,
        render: (row) => <StatusChip tone={row.status === 'active' ? 'success' : 'default'}>{tStatuses(row.status)}</StatusChip>,
      },
    ],
    [t, tStatuses, tTypes],
  );

  const handleExport = async () => {
    const blob = await exportBranchesCsv();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'branches-export.csv';
    anchor.click();
    URL.revokeObjectURL(url);
  };

  if (!canReadBranch(user)) {
    return <EmptyState title={t('accessDenied')} description={t('accessDeniedHint')} />;
  }

  if (listQuery.isLoading) {
    return <LoadingState label={t('loading')} />;
  }

  if (listQuery.isError) {
    return (
      <ErrorState
        title={t('loadError')}
        message={listQuery.error instanceof ApiError ? listQuery.error.message : t('loadError')}
        action={
          <Button type="button" variant="secondary" onClick={() => void listQuery.refetch()}>
            {t('applyFilters')}
          </Button>
        }
      />
    );
  }

  const rows = listQuery.data?.items ?? [];

  return (
    <div className="company-workspace">
      <header className="company-workspace__header">
        <div>
          <p className="company-workspace__eyebrow">{t('eyebrow')}</p>
          <h1>{t('title')}</h1>
          <p className="company-workspace__subtitle">{t('subtitle')}</p>
        </div>
        <div className="company-workspace__header-actions">
          {canCreateBranch(user) ? (
            <Button type="button" onClick={() => setFormMode('create')}>{t('createBranch')}</Button>
          ) : null}
          {canExportBranches(user) ? (
            <Button type="button" variant="secondary" onClick={handleExport}>{t('export')}</Button>
          ) : null}
        </div>
      </header>

      <BranchFilters
        filters={filters}
        onChange={setFilters}
        onApply={() => setAppliedFilters({ ...filters, page: 1 })}
        onClear={() => {
          setFilters(DEFAULT_FILTERS);
          setAppliedFilters(DEFAULT_FILTERS);
        }}
      />

      {rows.length === 0 ? (
        <EmptyState title={t('emptyTitle')} description={t('emptyHint')} />
      ) : (
        <AdminDataTable
          rows={rows}
          columns={columns}
          rowKey={(row) => row.id}
          exportFileName="branches.csv"
          onRowClick={(row) => {
            setSelectedId(row.id);
            setDrawerOpen(true);
          }}
          activeRowKey={selectedId}
        />
      )}

      <BranchDetailDrawer
        branch={(detailQuery.data as BranchDetail | undefined) ?? null}
        open={drawerOpen}
        loading={detailQuery.isLoading}
        onClose={() => setDrawerOpen(false)}
        onEdit={() => setFormMode('edit')}
        onDuplicate={() => selectedId && actionMutation.mutate({ type: 'duplicate', id: selectedId })}
        onAssignManager={() => selectedId && actionMutation.mutate({ type: 'assign', id: selectedId })}
        onTransferEmployees={() => selectedId && actionMutation.mutate({ type: 'transfer', id: selectedId })}
        onArchive={() => selectedId && actionMutation.mutate({ type: 'archive', id: selectedId })}
        onDeactivate={() => selectedId && actionMutation.mutate({ type: 'deactivate', id: selectedId })}
        onDelete={() => selectedId && actionMutation.mutate({ type: 'delete', id: selectedId })}
      />

      <BranchFormModal
        open={formMode !== null}
        mode={formMode ?? 'create'}
        initial={formMode === 'edit' ? (detailQuery.data as BranchDetail | undefined) ?? null : null}
        saving={createMutation.isPending || updateMutation.isPending}
        error={formError}
        onClose={() => setFormMode(null)}
        onSubmit={async (payload) => {
          if (formMode === 'edit' && selectedId) {
            await updateMutation.mutateAsync({ id: selectedId, payload });
            return;
          }
          await createMutation.mutateAsync(payload);
        }}
      />
    </div>
  );
}
