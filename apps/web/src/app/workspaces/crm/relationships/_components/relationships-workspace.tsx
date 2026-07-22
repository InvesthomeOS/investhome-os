'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import { crmLabel } from '@/lib/crm/crm-labels';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import {
  relationshipQueries,
} from '@/workspaces/crm/hooks/use-relationships';
import type { CrmRelationshipSummary } from '@/workspaces/crm/api/relationships';
import { getScoreBandBg, getScoreBandColor } from '@/workspaces/crm/stores/relationship-graph-ui-store';

import { AdminDataTable, type AdminTableColumn } from '@/app/dashboard/admin/_components/admin-data-table';

import { RelationshipFilters, type RelationshipFilterState } from './relationship-filters';

const DEFAULT_FILTERS: RelationshipFilterState = {
  search: '',
  page: 1,
  page_size: 25,
  sort_by: 'updated_at',
  sort_dir: 'desc',
};

const DEFAULT_SAVED_VIEWS = [
  { id: 'all', nameKey: 'savedViews.all' },
  { id: 'active', nameKey: 'savedViews.active', status: 'active' },
  { id: 'stale', nameKey: 'savedViews.stale' },
  { id: 'atRisk', nameKey: 'savedViews.atRisk' },
  { id: 'confidential', nameKey: 'savedViews.confidential' },
];

export function RelationshipsWorkspace() {
  const t = useTranslations('crm.relationships');
  const tTypes = useTranslations('crm.relationships.types');
  const tCategories = useTranslations('crm.relationships.categories');
  const tStrengths = useTranslations('crm.relationships.strengths');
  const tStatuses = useTranslations('crm.relationships.filters');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const { authLoading, canRead, canCreate } = useCrmAccess();
  const [filters, setFilters] = useState<RelationshipFilterState>(DEFAULT_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<RelationshipFilterState>(DEFAULT_FILTERS);
  const [activeView, setActiveView] = useState('all');

  const listParams = useMemo(
    () => ({
      search: appliedFilters.search || undefined,
      status: appliedFilters.status || undefined,
      category: appliedFilters.category || undefined,
      relationship_type: appliedFilters.relationship_type || undefined,
      page: appliedFilters.page,
      page_size: appliedFilters.page_size,
      sort_by: appliedFilters.sort_by,
      sort_dir: appliedFilters.sort_dir,
    }),
    [appliedFilters],
  );

  const listQuery = useQuery({
    ...relationshipQueries.list(listParams),
    enabled: !authLoading && canRead,
  });

  const columns: AdminTableColumn<CrmRelationshipSummary>[] = [
    {
      id: 'source',
      header: t('fields.source'),
      render: (row) => row.source_display_name ?? row.source_entity_id.slice(0, 8),
    },
    {
      id: 'type',
      header: t('fields.type'),
      render: (row) => crmLabel(tTypes, row.relationship_type),
    },
    {
      id: 'target',
      header: t('fields.target'),
      render: (row) => row.target_display_name ?? row.target_entity_id.slice(0, 8),
    },
    {
      id: 'category',
      header: t('fields.category'),
      render: (row) => crmLabel(tCategories, row.category),
    },
    {
      id: 'strength',
      header: t('fields.strength'),
      render: (row) => <StatusChip>{crmLabel(tStrengths, row.strength)}</StatusChip>,
    },
    {
      id: 'score',
      header: t('fields.score'),
      render: (row) => (
        <span
          style={{
            color: getScoreBandColor(row.relationship_score),
            background: getScoreBandBg(row.relationship_score),
            padding: '2px 8px',
            borderRadius: '4px',
            fontWeight: 600,
          }}
        >
          {row.relationship_score}
        </span>
      ),
    },
    {
      id: 'status',
      header: t('fields.status'),
      render: (row) => (
        <StatusChip tone={row.status === 'active' ? 'success' : 'default'}>
          {crmLabel(tStatuses, row.status)}
        </StatusChip>
      ),
    },
  ];

  if (authLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (!canRead) {
    return <ErrorState title={t('accessDenied')} message={t('accessDenied')} />;
  }

  if (listQuery.isLoading) return <LoadingState label={t('loading')} />;
  if (listQuery.isError) {
    return (
      <ErrorState
        title={t('loadFailed')}
        message={listQuery.error?.message ?? t('loadFailed')}
        action={
          <Button type="button" onClick={() => void listQuery.refetch()}>
            {tCommon('retry')}
          </Button>
        }
      />
    );
  }

  const items = listQuery.data?.items ?? [];
  const total = listQuery.data?.total ?? 0;

  return (
    <div className="crm-relationships-workspace">
      <header className="crm-workspace-header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('description')}</p>
        </div>
        <div className="crm-workspace-actions">
          <Link href="/workspaces/crm/relationships/network">
            <Button variant="secondary">{t('networkView')}</Button>
          </Link>
          <Link href="/workspaces/crm/relationships/intelligence">
            <Button variant="secondary">{t('intelligenceView')}</Button>
          </Link>
          {canCreate && (
            <Link href="/workspaces/crm/relationships/new">
              <Button>{t('create')}</Button>
            </Link>
          )}
        </div>
      </header>

      <div className="crm-saved-views">
        {DEFAULT_SAVED_VIEWS.map((view) => (
          <button
            key={view.id}
            type="button"
            className={activeView === view.id ? 'active' : ''}
            onClick={() => {
              setActiveView(view.id);
              setAppliedFilters({ ...DEFAULT_FILTERS, status: view.status });
            }}
          >
            {t(view.nameKey)}
          </button>
        ))}
      </div>

      <RelationshipFilters
        filters={filters}
        onChange={setFilters}
        onApply={() => setAppliedFilters({ ...filters, page: 1 })}
        onClear={() => {
          setFilters(DEFAULT_FILTERS);
          setAppliedFilters(DEFAULT_FILTERS);
          setActiveView('all');
        }}
      />

      {items.length === 0 ? (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      ) : (
        <AdminDataTable
          columns={columns}
          rows={items}
          rowKey={(row) => row.id}
          onRowClick={(row) => router.push(`/workspaces/crm/relationships/${row.id}`)}
        />
      )}

      <footer className="crm-table-footer">
        <span>{t('summary', { total, page: appliedFilters.page })}</span>
      </footer>
    </div>
  );
}
