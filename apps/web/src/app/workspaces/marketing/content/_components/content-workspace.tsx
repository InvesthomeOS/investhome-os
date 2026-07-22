'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/auth-context';
import { hasMarketingPermission } from '@/lib/marketing/marketing-permissions';
import { contentQueries } from '@/workspaces/marketing/hooks/use-content';
import type { ContentSummary } from '@/workspaces/marketing/api/content';
import { useContentUiStore } from '@/workspaces/marketing/stores/content-ui-store';

import { AdminDataTable, type AdminTableColumn } from '@/app/dashboard/admin/_components/admin-data-table';

import { SummaryWidget } from '../../_components/summary-widget';

function statusTone(status: string): 'default' | 'success' | 'warning' | 'danger' {
  if (status === 'published' || status === 'approved') return 'success';
  if (status === 'pending_approval' || status === 'scheduled') return 'warning';
  if (status === 'archived' || status === 'expired') return 'danger';
  return 'default';
}

export function ContentWorkspace() {
  const t = useTranslations('marketing.content');
  const tCommon = useTranslations('common');
  const { user } = useAuth();
  const { viewMode, setViewMode } = useContentUiStore();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);

  const canCreate = hasMarketingPermission(user, 'publish_content');

  const dashboardQuery = useQuery(contentQueries.dashboard());
  const listQuery = useQuery(contentQueries.list({ page, search: search || undefined, status: statusFilter || undefined }));

  const columns: AdminTableColumn<ContentSummary>[] = useMemo(
    () => [
      {
        id: 'title',
        header: t('columns.title'),
        exportValue: (row) => row.title,
        render: (row) => (
          <Link href={`/workspaces/marketing/content/${row.id}` as Route} className="marketing-link">
            {row.title}
          </Link>
        ),
      },
      {
        id: 'content_type',
        header: t('columns.type'),
        exportValue: (row) => row.content_type,
        render: (row) => row.content_type,
      },
      {
        id: 'status',
        header: t('columns.status'),
        exportValue: (row) => row.status,
        render: (row) => <StatusChip tone={statusTone(row.status)}>{t(`status.${row.status}` as 'status.idea')}</StatusChip>,
      },
      {
        id: 'scheduled_at',
        header: t('columns.scheduled'),
        exportValue: (row) => row.scheduled_at ?? '',
        render: (row) => (row.scheduled_at ? new Date(row.scheduled_at).toLocaleDateString() : t('notSet')),
      },
      {
        id: 'updated_at',
        header: t('columns.updated'),
        exportValue: (row) => row.updated_at,
        render: (row) => new Date(row.updated_at).toLocaleDateString(),
      },
    ],
    [t],
  );

  if (!canCreate) {
    return (
      <main className="dashboard marketing-module-shell">
        <EmptyState title={t('accessDenied')} description={t('accessDeniedDescription')} />
      </main>
    );
  }

  return (
    <main className="dashboard marketing-module-shell">
      <header className="dashboard__header marketing-content__header">
        <div>
          <h1 className="dashboard__title">{t('title')}</h1>
          <p className="dashboard__subtitle">{t('subtitle')}</p>
        </div>
        <div className="marketing-content__actions">
          <Link href={'/workspaces/marketing/content/new' as Route}>
            <Button type="button">{t('create')}</Button>
          </Link>
        </div>
      </header>

      <section className="marketing-content__widgets">
        {dashboardQuery.isLoading ? (
          <LoadingState label={tCommon('loading')} />
        ) : dashboardQuery.isError ? (
          <ErrorState title={t('loadFailed')} message={dashboardQuery.error instanceof ApiError ? dashboardQuery.error.message : tCommon('unknownError')} />
        ) : (
          <>
            <SummaryWidget title={t('summary.total')} state="ready" value={String(dashboardQuery.data?.total ?? t('notSet'))} />
            <SummaryWidget
              title={t('summary.inReview')}
              state="ready"
              value={String(
                (dashboardQuery.data?.by_status?.pending_approval ?? 0) +
                  (dashboardQuery.data?.by_status?.internal_review ?? 0),
              )}
            />
            <SummaryWidget
              title={t('summary.published')}
              state="ready"
              value={String(dashboardQuery.data?.by_status?.published ?? 0)}
            />
          </>
        )}
      </section>

      <section className="marketing-content__toolbar">
        <input
          type="search"
          className="marketing-content__search"
          placeholder={t('searchPlaceholder')}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          className="marketing-content__filter"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          aria-label={t('filterStatus')}
        >
          <option value="">{t('allStatuses')}</option>
          <option value="draft">{t('status.draft')}</option>
          <option value="pending_approval">{t('status.pending_approval')}</option>
          <option value="approved">{t('status.approved')}</option>
          <option value="published">{t('status.published')}</option>
        </select>
        <div className="marketing-content__view-modes" role="group" aria-label={t('viewMode')}>
          {(['table', 'grid', 'pipeline', 'calendar'] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              className={viewMode === mode ? 'marketing-content__view-btn marketing-content__view-btn--active' : 'marketing-content__view-btn'}
              onClick={() => setViewMode(mode)}
            >
              {t(`viewModes.${mode}` as 'viewModes.table')}
            </button>
          ))}
        </div>
      </section>

      {listQuery.isLoading ? (
        <LoadingState label={tCommon('loading')} />
      ) : listQuery.isError ? (
        <ErrorState title={t('loadFailed')} message={listQuery.error instanceof ApiError ? listQuery.error.message : tCommon('unknownError')} />
      ) : listQuery.data?.items.length === 0 ? (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      ) : viewMode === 'table' ? (
        <AdminDataTable columns={columns} rows={listQuery.data?.items ?? []} rowKey={(row) => row.id} />
      ) : (
        <div className="marketing-content__cards">
          {(listQuery.data?.items ?? []).map((item) => (
            <Link key={item.id} href={`/workspaces/marketing/content/${item.id}` as Route} className="marketing-content__card">
              <h3>{item.title}</h3>
              <StatusChip tone={statusTone(item.status)}>{t(`status.${item.status}` as 'status.idea')}</StatusChip>
              <span className="marketing-content__card-meta">{item.content_type}</span>
            </Link>
          ))}
        </div>
      )}

      {(listQuery.data?.pages ?? 0) > 1 && (
        <div className="marketing-content__pagination">
          <Button type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            {tCommon('previous')}
          </Button>
          <span>{t('pageLabel', { page, pages: listQuery.data?.pages ?? 1 })}</span>
          <Button type="button" disabled={page >= (listQuery.data?.pages ?? 1)} onClick={() => setPage((p) => p + 1)}>
            {tCommon('next')}
          </Button>
        </div>
      )}
    </main>
  );
}
