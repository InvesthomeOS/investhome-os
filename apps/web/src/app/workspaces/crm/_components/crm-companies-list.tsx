'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useMemo } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, FilterBar, Input, LoadingState } from '@investhome/ui';

import { AdminDataTable, type AdminTableColumn } from '@/app/dashboard/admin/_components/admin-data-table';
import { canCreateCrm } from '@/lib/crm/crm-permissions';
import { crmCompaniesQueries } from '@/lib/query/crm-companies-queries';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { DEFAULT_COMPANY_SAVED_VIEWS, type CrmCompanyListItem } from '@/workspaces/crm/types';
import { useCrmCompaniesStore } from '@/workspaces/crm/_stores/crm-companies-store';

function formatDate(value: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: 'medium' }).format(new Date(value));
}

export function CrmCompaniesList() {
  const t = useTranslations('crm.companies');
  const tCrm = useTranslations('crm');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { authLoading, user, canReadCompanies: canView } = useCrmAccess();

  const {
    search,
    statusFilter,
    companyTypeFilter,
    includeArchived,
    activeSavedView,
    setSearch,
    setStatusFilter,
    setCompanyTypeFilter,
    setIncludeArchived,
    setActiveSavedView,
    resetFilters,
  } = useCrmCompaniesStore();

  const savedViewFilters = useMemo((): Record<string, string | boolean> => {
    const view = DEFAULT_COMPANY_SAVED_VIEWS.find((v) => v.key === activeSavedView);
    return (view?.filters ?? {}) as Record<string, string | boolean>;
  }, [activeSavedView]);

  const listParams = useMemo(
    () => ({
      search: search || undefined,
      status: statusFilter || (savedViewFilters.status as string | undefined),
      companyType: companyTypeFilter || (savedViewFilters.company_type as string | undefined),
      includeArchived: includeArchived || Boolean(savedViewFilters.include_archived),
      sortBy: 'updated_at',
      sortOrder: 'desc' as const,
      page: 1,
      pageSize: 100,
    }),
    [search, statusFilter, companyTypeFilter, includeArchived, savedViewFilters],
  );

  const listQuery = useQuery({
    ...crmCompaniesQueries.list(listParams),
    enabled: !authLoading && canView,
  });

  const columns: AdminTableColumn<CrmCompanyListItem>[] = [
    {
      id: 'display_name',
      header: tCrm('fields.displayName'),
      render: (row) => (
        <Link href={`/workspaces/crm/companies/${row.id}` as Route} className="crm-link">
          {row.display_name}
        </Link>
      ),
    },
    {
      id: 'company_type',
      header: t('fields.companyType'),
      render: (row) => t(`companyTypes.${row.company_type}` as 'companyTypes.other'),
    },
    {
      id: 'primary_email',
      header: tCrm('fields.email'),
      render: (row) => row.primary_email ?? '—',
    },
    {
      id: 'domain',
      header: t('fields.domain'),
      render: (row) => row.domain ?? '—',
    },
    {
      id: 'industry',
      header: t('fields.industry'),
      render: (row) => row.industry ?? '—',
    },
    {
      id: 'status',
      header: tCrm('fields.status'),
      render: (row) => tCrm(`statuses.${row.status}` as 'statuses.active'),
    },
    {
      id: 'contact_count',
      header: t('fields.contacts'),
      render: (row) => String(row.contact_count),
    },
    {
      id: 'updated_at',
      header: t('fields.updated'),
      render: (row) => formatDate(row.updated_at, locale),
    },
  ];

  if (authLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (!canView) {
    return <ErrorState title={tCrm('accessDenied')} message={tCrm('accessDeniedHint')} />;
  }

  if (listQuery.isLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (listQuery.isError) {
    return (
      <ErrorState
        title={tCrm('loadFailed')}
        message={listQuery.error?.message ?? tCrm('loadFailed')}
        action={
          <Button type="button" onClick={() => void listQuery.refetch()}>
            {tCommon('retry')}
          </Button>
        }
      />
    );
  }

  const data = listQuery.data;

  return (
    <div className="crm-companies-workspace">
      <div className="crm-companies-workspace__toolbar">
        <FilterBar
          actions={
            canCreateCrm(user) ? (
              <>
                <Link href={'/workspaces/crm/companies/import' as Route} className="ih-btn ih-btn--secondary">
                  {t('actions.import')}
                </Link>
                <Link href={'/workspaces/crm/companies/new' as Route} className="ih-btn ih-btn--primary">
                  {t('actions.create')}
                </Link>
              </>
            ) : undefined
          }
        >
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t('filters.searchPlaceholder')}
            aria-label={t('filters.searchPlaceholder')}
          />
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            aria-label={tCrm('fields.status')}
          >
            <option value="">{t('filters.allStatuses')}</option>
            <option value="active">{tCrm('statuses.active')}</option>
            <option value="prospect">{tCrm('statuses.prospect')}</option>
            <option value="inactive">{tCrm('statuses.inactive')}</option>
            <option value="archived">{tCrm('statuses.archived')}</option>
          </select>
          <label className="crm-checkbox-label">
            <input
              type="checkbox"
              checked={includeArchived}
              onChange={(event) => setIncludeArchived(event.target.checked)}
            />
            {t('filters.includeArchived')}
          </label>
          <Button type="button" variant="secondary" onClick={resetFilters}>
            {tCommon('reset')}
          </Button>
        </FilterBar>
      </div>

      <div className="crm-saved-views">
        {DEFAULT_COMPANY_SAVED_VIEWS.map((view) => (
          <button
            key={view.key}
            type="button"
            className={activeSavedView === view.key ? 'crm-saved-view crm-saved-view--active' : 'crm-saved-view'}
            onClick={() => {
              setActiveSavedView(view.key);
              const filters = view.filters as Record<string, string | boolean>;
              if (filters.company_type) {
                setCompanyTypeFilter(String(filters.company_type));
              }
              if (filters.status) {
                setStatusFilter(String(filters.status));
              }
              if (filters.include_archived) {
                setIncludeArchived(true);
              }
            }}
          >
            {t(`savedViews.${view.key}` as 'savedViews.all')}
          </button>
        ))}
      </div>

      {!data || data.items.length === 0 ? (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      ) : (
        <>
          <p className="crm-dashboard__list-item-meta">
            {t('summary', { total: data.total, page: data.page, pages: data.pages })}
          </p>
          <AdminDataTable columns={columns} rows={data.items} rowKey={(row) => row.id} />
        </>
      )}
    </div>
  );
}
