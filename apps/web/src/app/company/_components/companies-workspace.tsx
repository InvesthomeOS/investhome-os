'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useMemo, useRef, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, FilterBar, Input, LoadingState, PageHeader } from '@investhome/ui';

import { AdminDataTable, type AdminTableColumn } from '@/app/dashboard/admin/_components/admin-data-table';
import type { CompanyEntityType, CompanyListItem, CompanyStatus } from '@/lib/api/companies';
import {
  canArchiveCompany,
  canCreateCompany,
  canDeleteCompany,
  canExportCompanies,
  canReadCompany,
  canUpdateCompany,
} from '@/lib/company/company-permissions';
import { companiesMutations, companiesQueries, companiesQueryKeys } from '@/lib/query/companies-queries';
import { useAuth } from '@/lib/auth/auth-context';

import { CompanyFormModal } from './company-form-modal';
import { CompanyProfilePanel } from './company-profile-panel';
import { useCompanyToast } from './use-company-toast';

type FilterState = {
  search: string;
  status: CompanyStatus | '';
  country: string;
  entityType: CompanyEntityType | '';
  industry: string;
  dateFrom: string;
  dateTo: string;
};

const DEFAULT_FILTERS: FilterState = {
  search: '',
  status: '',
  country: '',
  entityType: '',
  industry: '',
  dateFrom: '',
  dateTo: '',
};

function formatDate(value: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: 'medium' }).format(new Date(value));
}

export function CompaniesWorkspace() {
  const t = useTranslations('company.companies');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { user } = useAuth();
  const { notifySuccess, notifyError } = useCompanyToast();
  const queryClient = useQueryClient();
  const importInputRef = useRef<HTMLInputElement>(null);

  const [draftFilters, setDraftFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create');
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);

  const listParams = useMemo(
    () => ({
      search: appliedFilters.search || undefined,
      status: appliedFilters.status || undefined,
      country: appliedFilters.country || undefined,
      entity_type: appliedFilters.entityType || undefined,
      industry: appliedFilters.industry || undefined,
      created_from: appliedFilters.dateFrom ? `${appliedFilters.dateFrom}T00:00:00` : undefined,
      created_to: appliedFilters.dateTo ? `${appliedFilters.dateTo}T23:59:59` : undefined,
      sort_by: 'updated_at',
      sort_order: 'desc' as const,
      page: 1,
      page_size: 100,
    }),
    [appliedFilters],
  );

  const listQuery = useQuery({
    ...companiesQueries.list(listParams),
    enabled: canReadCompany(user),
  });

  const detailQuery = useQuery({
    ...companiesQueries.detail(selectedId ?? ''),
    enabled: Boolean(selectedId) && canReadCompany(user),
  });

  const createMutation = useMutation({
    ...companiesMutations.create(),
    onSuccess: async () => {
      notifySuccess(t('messages.created'));
      setFormOpen(false);
      await queryClient.invalidateQueries({ queryKey: companiesQueryKeys.all });
    },
    onError: (error) => notifyError(error, t('messages.saveFailed')),
  });

  const updateMutation = useMutation({
    ...companiesMutations.update(selectedId ?? ''),
    onSuccess: async () => {
      notifySuccess(t('messages.updated'));
      setFormOpen(false);
      await queryClient.invalidateQueries({ queryKey: companiesQueryKeys.all });
    },
    onError: (error) => notifyError(error, t('messages.saveFailed')),
  });

  const archiveMutation = useMutation({
    ...companiesMutations.archive(),
    onSuccess: async () => {
      notifySuccess(t('messages.archived'));
      await queryClient.invalidateQueries({ queryKey: companiesQueryKeys.all });
    },
    onError: (error) => notifyError(error, t('messages.actionFailed')),
  });

  const deactivateMutation = useMutation({
    ...companiesMutations.deactivate(),
    onSuccess: async () => {
      notifySuccess(t('messages.deactivated'));
      await queryClient.invalidateQueries({ queryKey: companiesQueryKeys.all });
    },
    onError: (error) => notifyError(error, t('messages.actionFailed')),
  });

  const duplicateMutation = useMutation({
    ...companiesMutations.duplicate(),
    onSuccess: async () => {
      notifySuccess(t('messages.duplicated'));
      await queryClient.invalidateQueries({ queryKey: companiesQueryKeys.all });
    },
    onError: (error) => notifyError(error, t('messages.actionFailed')),
  });

  const deleteMutation = useMutation({
    ...companiesMutations.delete(),
    onSuccess: async () => {
      notifySuccess(t('messages.deleted'));
      setSelectedId(null);
      await queryClient.invalidateQueries({ queryKey: companiesQueryKeys.all });
    },
    onError: (error) => notifyError(error, t('messages.actionFailed')),
  });

  const exportMutation = useMutation({
    ...companiesMutations.export(),
    onSuccess: (csv) => {
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = 'companies-export.csv';
      anchor.click();
      URL.revokeObjectURL(url);
      notifySuccess(t('messages.exported'));
    },
    onError: (error) => notifyError(error, t('messages.exportFailed')),
  });

  const importMutation = useMutation({
    ...companiesMutations.import(),
    onSuccess: async (result) => {
      notifySuccess(t('messages.imported', { count: result.imported }));
      await queryClient.invalidateQueries({ queryKey: companiesQueryKeys.all });
    },
    onError: (error) => notifyError(error, t('messages.importFailed')),
  });

  if (!canReadCompany(user)) {
    return <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />;
  }

  const columns: AdminTableColumn<CompanyListItem>[] = [
    {
      id: 'logo',
      header: t('columns.logo'),
      render: () => <span className="company-table__logo" aria-hidden="true">◆</span>,
      exportValue: () => '',
      defaultVisible: true,
    },
    {
      id: 'company_name',
      header: t('columns.companyName'),
      sortable: true,
      render: (row) => row.company_name,
      exportValue: (row) => row.company_name,
    },
    {
      id: 'legal_name',
      header: t('columns.legalName'),
      sortable: true,
      render: (row) => row.legal_name ?? '—',
      exportValue: (row) => row.legal_name ?? '',
    },
    {
      id: 'entity_type',
      header: t('columns.entityType'),
      sortable: true,
      render: (row) => t(`entityTypes.${row.entity_type}` as 'entityTypes.other'),
      exportValue: (row) => row.entity_type,
    },
    {
      id: 'registration_number',
      header: t('columns.registrationNumber'),
      sortable: true,
      render: (row) => row.registration_number ?? '—',
      exportValue: (row) => row.registration_number ?? '',
    },
    {
      id: 'tax_id',
      header: t('columns.taxId'),
      sortable: true,
      render: (row) => row.tax_id ?? '—',
      exportValue: (row) => row.tax_id ?? '',
    },
    {
      id: 'country',
      header: t('columns.country'),
      sortable: true,
      render: (row) => row.country ?? '—',
      exportValue: (row) => row.country ?? '',
    },
    {
      id: 'state',
      header: t('columns.state'),
      sortable: true,
      render: (row) => row.state ?? '—',
      exportValue: (row) => row.state ?? '',
    },
    {
      id: 'city',
      header: t('columns.city'),
      sortable: true,
      render: (row) => row.city ?? '—',
      exportValue: (row) => row.city ?? '',
    },
    {
      id: 'status',
      header: t('columns.status'),
      sortable: true,
      render: (row) => (
        <span className={`company-status company-status--${row.status}`}>
          {t(`statuses.${row.status}` as 'statuses.draft')}
        </span>
      ),
      exportValue: (row) => row.status,
    },
    {
      id: 'employee_count',
      header: t('columns.employees'),
      sortable: true,
      render: (row) => row.employee_count,
      exportValue: (row) => String(row.employee_count),
    },
    {
      id: 'branch_count',
      header: t('columns.branches'),
      sortable: true,
      render: (row) => row.branch_count,
      exportValue: (row) => String(row.branch_count),
    },
    {
      id: 'created_at',
      header: t('columns.createdDate'),
      sortable: true,
      render: (row) => formatDate(row.created_at, locale),
      exportValue: (row) => row.created_at,
    },
    {
      id: 'owner_name',
      header: t('columns.owner'),
      render: (row) => row.owner_name ?? '—',
      exportValue: (row) => row.owner_name ?? '',
    },
    {
      id: 'actions',
      header: t('columns.actions'),
      render: (row) => (
        <div className="company-table__actions">
          <Button type="button" variant="ghost" onClick={() => setSelectedId(row.id)}>
            {t('actions.view')}
          </Button>
          {canUpdateCompany(user) ? (
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                setSelectedId(row.id);
                setFormMode('edit');
                setFormOpen(true);
              }}
            >
              {t('actions.edit')}
            </Button>
          ) : null}
        </div>
      ),
      exportValue: () => '',
    },
  ];

  const handleFormSubmit = async (payload: Record<string, string>) => {
    const body = {
      company_name: payload.company_name || 'Untitled Company',
      legal_name: payload.legal_name || null,
      entity_type: payload.entity_type as CompanyEntityType,
      registration_number: payload.registration_number || null,
      tax_id: payload.tax_id || null,
      country: payload.country || null,
      state: payload.state || null,
      city: payload.city || null,
      industry: payload.industry || null,
      status: payload.status as CompanyStatus,
      notes: payload.notes || null,
    };
    if (formMode === 'create') {
      await createMutation.mutateAsync(body);
      return;
    }
    if (selectedId) {
      await updateMutation.mutateAsync(body);
    }
  };

  return (
    <main className="dashboard company-companies">
      <PageHeader
        title={t('title')}
        subtitle={t('subtitle')}
        actions={
          <div className="company-companies__header-actions">
            {canCreateCompany(user) ? (
              <Button
                type="button"
                onClick={() => {
                  setFormMode('create');
                  setFormOpen(true);
                }}
              >
                {t('actions.create')}
              </Button>
            ) : null}
            {canCreateCompany(user) ? (
              <>
                <Button type="button" variant="secondary" onClick={() => importInputRef.current?.click()}>
                  {t('actions.import')}
                </Button>
                <input
                  ref={importInputRef}
                  type="file"
                  accept=".csv,text/csv"
                  hidden
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    if (file) {
                      void importMutation.mutateAsync(file);
                    }
                    event.currentTarget.value = '';
                  }}
                />
              </>
            ) : null}
            {canExportCompanies(user) ? (
              <Button type="button" variant="secondary" onClick={() => void exportMutation.mutateAsync(false)}>
                {t('actions.export')}
              </Button>
            ) : null}
            <Button type="button" variant="secondary" onClick={() => setShowAdvancedFilters((current) => !current)}>
              {t('actions.advancedFilters')}
            </Button>
          </div>
        }
      />

      <FilterBar
        actions={
          <Button type="button" onClick={() => setAppliedFilters(draftFilters)}>
            {t('actions.applyFilters')}
          </Button>
        }
      >
        <Input
          value={draftFilters.search}
          placeholder={t('searchPlaceholder')}
          onChange={(event) => setDraftFilters((current) => ({ ...current, search: event.target.value }))}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              setAppliedFilters(draftFilters);
            }
          }}
        />
      </FilterBar>

      {showAdvancedFilters ? (
        <div className="company-companies__filters">
          <label>
            {t('filters.status')}
            <select
              value={draftFilters.status}
              onChange={(event) =>
                setDraftFilters((current) => ({ ...current, status: event.target.value as CompanyStatus | '' }))
              }
            >
              <option value="">{tCommon('all')}</option>
              {(['draft', 'pending_review', 'active', 'inactive', 'suspended', 'closed', 'archived'] as CompanyStatus[]).map(
                (status) => (
                  <option key={status} value={status}>
                    {t(`statuses.${status}` as 'statuses.draft')}
                  </option>
                ),
              )}
            </select>
          </label>
          <label>
            {t('filters.country')}
            <input
              value={draftFilters.country}
              onChange={(event) => setDraftFilters((current) => ({ ...current, country: event.target.value }))}
            />
          </label>
          <label>
            {t('filters.entityType')}
            <input
              value={draftFilters.entityType}
              onChange={(event) =>
                setDraftFilters((current) => ({ ...current, entityType: event.target.value as CompanyEntityType | '' }))
              }
            />
          </label>
          <label>
            {t('filters.industry')}
            <input
              value={draftFilters.industry}
              onChange={(event) => setDraftFilters((current) => ({ ...current, industry: event.target.value }))}
            />
          </label>
          <label>
            {t('filters.dateFrom')}
            <input
              type="date"
              value={draftFilters.dateFrom}
              onChange={(event) => setDraftFilters((current) => ({ ...current, dateFrom: event.target.value }))}
            />
          </label>
          <label>
            {t('filters.dateTo')}
            <input
              type="date"
              value={draftFilters.dateTo}
              onChange={(event) => setDraftFilters((current) => ({ ...current, dateTo: event.target.value }))}
            />
          </label>
          <Button type="button" onClick={() => setAppliedFilters(draftFilters)}>
            {t('actions.applyFilters')}
          </Button>
        </div>
      ) : null}

      <div className="company-companies__layout">
        <section className="company-companies__table-panel">
          {listQuery.isLoading ? (
            <LoadingState label={tCommon('loading')} />
          ) : listQuery.isError ? (
            <ErrorState
              title={t('loadFailed')}
              message={listQuery.error?.message}
              action={
                <Button type="button" onClick={() => void listQuery.refetch()}>
                  {tCommon('retry')}
                </Button>
              }
            />
          ) : listQuery.data && listQuery.data.items.length === 0 ? (
            <EmptyState title={t('empty.title')} description={t('empty.description')} />
          ) : (
            <AdminDataTable
              rows={listQuery.data?.items ?? []}
              columns={columns}
              rowKey={(row) => row.id}
              activeRowKey={selectedId}
              onRowClick={(row) => setSelectedId(row.id)}
              exportFileName="companies.csv"
              emptyMessage={t('empty.title')}
            />
          )}
        </section>

        <aside className="company-companies__detail-panel">
          <CompanyProfilePanel
            company={detailQuery.data ?? null}
            loading={detailQuery.isLoading && Boolean(selectedId)}
            canEdit={canUpdateCompany(user)}
            onEdit={() => {
              setFormMode('edit');
              setFormOpen(true);
            }}
          />

          {selectedId ? (
            <div className="company-companies__detail-actions">
              <Link href={`/company/companies/${selectedId}` as Route}>{t('actions.openFullProfile')}</Link>
              {canCreateCompany(user) ? (
                <Button type="button" variant="secondary" onClick={() => void duplicateMutation.mutateAsync(selectedId)}>
                  {t('actions.duplicate')}
                </Button>
              ) : null}
              {canUpdateCompany(user) ? (
                <Button type="button" variant="secondary" onClick={() => void deactivateMutation.mutateAsync(selectedId)}>
                  {t('actions.deactivate')}
                </Button>
              ) : null}
              {canArchiveCompany(user) ? (
                <Button type="button" variant="secondary" onClick={() => void archiveMutation.mutateAsync(selectedId)}>
                  {t('actions.archive')}
                </Button>
              ) : null}
              {canDeleteCompany(user) ? (
                <Button type="button" variant="danger" onClick={() => void deleteMutation.mutateAsync(selectedId)}>
                  {t('actions.delete')}
                </Button>
              ) : null}
            </div>
          ) : null}
        </aside>
      </div>

      <CompanyFormModal
        open={formOpen}
        mode={formMode}
        initial={formMode === 'edit' ? detailQuery.data ?? null : null}
        onClose={() => setFormOpen(false)}
        onSubmit={handleFormSubmit}
      />
    </main>
  );
}
