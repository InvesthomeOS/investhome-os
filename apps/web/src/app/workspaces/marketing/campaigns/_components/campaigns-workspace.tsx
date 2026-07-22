'use client';

import { useCallback, useMemo, useState } from 'react';
import Link from 'next/link';
import type { Route } from 'next';
import { useRouter, useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState, StatusChip, type StatusChipTone } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/auth-context';
import {
  canActivateCampaigns,
  canCreateCampaigns,
  canExportCampaigns,
  canManageCampaigns,
  canPauseCampaigns,
  canReadMarketing,
} from '@/lib/marketing/marketing-permissions';
import { campaignQueries, campaignQueryKeys } from '@/workspaces/marketing/hooks/use-campaigns';
import {
  bulkCampaignAction,
  exportCampaignsCsv,
  type CampaignListParams,
} from '@/workspaces/marketing/api/campaigns';
import { DEFAULT_CAMPAIGN_SAVED_VIEWS } from '@/workspaces/marketing/types';
import type { MarketingCampaignSummary } from '@/workspaces/marketing/types';
import { useCampaignUiStore } from '@/workspaces/marketing/stores/campaign-ui-store';

import { AdminDataTable, type AdminTableColumn } from '@/app/dashboard/admin/_components/admin-data-table';

import { CampaignFilters, type CampaignFilterState } from './campaign-filters';

const DEFAULT_FILTERS: CampaignFilterState = {
  search: '',
  status: '',
  campaign_type: '',
  primary_channel: '',
  project_id: '',
  owner_user_id: '',
  page: 1,
  page_size: 25,
};

function statusTone(status: string): StatusChipTone {
  switch (status) {
    case 'active':
    case 'approved':
    case 'completed':
      return 'success';
    case 'paused':
    case 'pending_approval':
    case 'scheduled':
      return 'warning';
    case 'cancelled':
    case 'archived':
      return 'danger';
    default:
      return 'default';
  }
}

function UnavailableValue({ label }: { label: string }) {
  return <span className="marketing-campaigns__unavailable">{label}</span>;
}

function CampaignStatusChip({ status, label }: { status: string; label: string }) {
  return <StatusChip tone={statusTone(status)}>{label}</StatusChip>;
}

export function CampaignsWorkspace() {
  const t = useTranslations('marketing.campaigns');
  const tStatus = useTranslations('marketing.campaigns.status');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const { selectedIds, setSelectedIds, clearSelection, viewMode, setViewMode, activeSavedView, setActiveSavedView } =
    useCampaignUiStore();

  const [filters, setFilters] = useState<CampaignFilterState>(() => ({
    ...DEFAULT_FILTERS,
    search: searchParams.get('search') ?? '',
    status: searchParams.get('status') ?? '',
    campaign_type: searchParams.get('campaign_type') ?? '',
  }));
  const [appliedFilters, setAppliedFilters] = useState(filters);

  const listParams: CampaignListParams = useMemo(
    () => ({
      search: appliedFilters.search || undefined,
      status: appliedFilters.status || undefined,
      campaign_type: appliedFilters.campaign_type || undefined,
      primary_channel: appliedFilters.primary_channel || undefined,
      project_id: appliedFilters.project_id || undefined,
      owner_user_id: appliedFilters.owner_user_id || undefined,
      objective: appliedFilters.objective || undefined,
      missing_owner: appliedFilters.missing_owner || undefined,
      missing_budget: appliedFilters.missing_budget || undefined,
      missing_tracking: appliedFilters.missing_tracking || undefined,
      my_campaigns: appliedFilters.my_campaigns || undefined,
      include_archived: appliedFilters.include_archived || undefined,
      page: appliedFilters.page,
      page_size: appliedFilters.page_size,
    }),
    [appliedFilters],
  );

  const listQuery = useQuery(campaignQueries.list(listParams));
  const summaryQuery = useQuery(campaignQueries.summary(appliedFilters.my_campaigns));

  const invalidate = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: campaignQueryKeys.all });
  }, [queryClient]);

  const bulkMutation = useMutation({
    mutationFn: (action: string) => bulkCampaignAction(selectedIds, action),
    onSuccess: async () => {
      clearSelection();
      await invalidate();
    },
  });

  const columns = useMemo<AdminTableColumn<MarketingCampaignSummary>[]>(
    () => [
      {
        id: 'name',
        header: t('columns.name'),
        sortable: true,
        exportValue: (row) => row.name,
        render: (row) => (
          <Link href={`/workspaces/marketing/campaigns/${row.id}` as Route} className="marketing-campaigns__link">
            {row.name}
          </Link>
        ),
      },
      {
        id: 'code',
        header: t('columns.code'),
        exportValue: (row) => row.code ?? '',
        render: (row) => row.code ?? '—',
      },
      {
        id: 'status',
        header: t('columns.status'),
        exportValue: (row) => row.status,
        render: (row) => <CampaignStatusChip status={row.status} label={tStatus(row.status)} />,
      },
      {
        id: 'campaign_type',
        header: t('columns.type'),
        exportValue: (row) => row.campaign_type,
        render: (row) => t(`types.${row.campaign_type}` as 'types.other'),
      },
      {
        id: 'objective',
        header: t('columns.objective'),
        exportValue: (row) => row.objective,
        render: (row) => t(`objectives.${row.objective}` as 'objectives.awareness'),
      },
      {
        id: 'budget',
        header: t('columns.budget'),
        exportValue: (row) => (row.budget_amount ? `${row.budget_amount} ${row.budget_currency ?? ''}` : ''),
        render: (row) =>
          row.budget_amount ? (
            `${row.budget_amount} ${row.budget_currency ?? ''}`
          ) : (
            <UnavailableValue label={t('notSet')} />
          ),
      },
      {
        id: 'spend',
        header: t('columns.spend'),
        exportValue: (row) => row.spent_amount ?? '',
        render: (row) =>
          row.spent_amount != null ? (
            `${row.spent_amount} ${row.budget_currency ?? ''}`
          ) : (
            <UnavailableValue label={t('noData')} />
          ),
      },
      {
        id: 'leads',
        header: t('columns.leads'),
        exportValue: (row) => (row.actual_leads != null ? String(row.actual_leads) : ''),
        render: (row) =>
          row.actual_leads != null ? String(row.actual_leads) : <UnavailableValue label={t('noData')} />,
      },
      {
        id: 'start_date',
        header: t('columns.startDate'),
        exportValue: (row) => row.start_date ?? '',
        render: (row) => (row.start_date ? new Date(row.start_date).toLocaleDateString() : '—'),
      },
      {
        id: 'end_date',
        header: t('columns.endDate'),
        exportValue: (row) => row.end_date ?? '',
        render: (row) => (row.end_date ? new Date(row.end_date).toLocaleDateString() : '—'),
      },
    ],
    [t, tStatus],
  );

  if (!canReadMarketing(user) && !canManageCampaigns(user)) {
    return <EmptyState title={t('accessDenied')} description={t('accessDeniedDescription')} />;
  }

  if (listQuery.isLoading) return <LoadingState label={tCommon('loading')} />;
  if (listQuery.isError) {
    const err = listQuery.error;
    return (
      <ErrorState
        title={tCommon('error')}
        message={err instanceof ApiError ? err.message : tCommon('unknownError')}
        action={
          <Button type="button" onClick={() => void listQuery.refetch()}>
            {tCommon('retry')}
          </Button>
        }
      />
    );
  }

  const rows = listQuery.data?.items ?? [];
  const summary = summaryQuery.data;

  return (
    <div className="marketing-campaigns">
      <div className="marketing-campaigns__toolbar">
        <div>
          <h1 className="marketing-detail__title">{t('title')}</h1>
          <p className="marketing-campaign-card__meta">{t('subtitle')}</p>
        </div>
        <div className="marketing-campaigns__toolbar-actions">
          {canExportCampaigns(user) && (
            <Button
              variant="secondary"
              onClick={() => {
                void exportCampaignsCsv(listParams).then((blob) => {
                  const url = URL.createObjectURL(blob);
                  const anchor = document.createElement('a');
                  anchor.href = url;
                  anchor.download = 'marketing-campaigns-export.csv';
                  anchor.click();
                  URL.revokeObjectURL(url);
                });
              }}
            >
              {t('export')}
            </Button>
          )}
          {canCreateCampaigns(user) && (
            <Button onClick={() => router.push('/workspaces/marketing/campaigns/new' as Route)}>{t('create')}</Button>
          )}
        </div>
      </div>

      {summary && (
        <div className="marketing-summary__grid">
          {[
            { key: 'total', value: summary.total, filter: {} },
            { key: 'draft', value: summary.draft, filter: { status: 'draft' } },
            { key: 'pending_approval', value: summary.pending_approval, filter: { status: 'pending_approval' } },
            { key: 'active', value: summary.active, filter: { status: 'active' } },
            { key: 'paused', value: summary.paused, filter: { status: 'paused' } },
          ].map((item) => (
            <button
              key={item.key}
              type="button"
              className={
                appliedFilters.status === (item.filter as { status?: string }).status
                  ? 'marketing-summary__card marketing-summary__card--active'
                  : 'marketing-summary__card'
              }
              onClick={() => {
                const next = { ...appliedFilters, status: (item.filter as { status?: string }).status ?? '', page: 1 };
                setAppliedFilters(next);
                setFilters(next);
              }}
            >
              <div className="marketing-summary__card-value">{item.value}</div>
              <div className="marketing-summary__card-label">{t(`summary.${item.key}` as 'summary.total')}</div>
            </button>
          ))}
        </div>
      )}

      <div className="marketing-saved-views">
        {DEFAULT_CAMPAIGN_SAVED_VIEWS.map((view) => (
          <button
            key={view.key}
            type="button"
            className={
              activeSavedView === view.key ? 'marketing-saved-view marketing-saved-view--active' : 'marketing-saved-view'
            }
            onClick={() => {
              setActiveSavedView(view.key);
              const next = { ...DEFAULT_FILTERS, ...view.filters, page: 1 } as CampaignFilterState;
              setFilters(next);
              setAppliedFilters(next);
            }}
          >
            {t(`savedViews.${view.key}` as 'savedViews.all')}
          </button>
        ))}
      </div>

      <CampaignFilters
        filters={filters}
        onChange={setFilters}
        onApply={() => setAppliedFilters({ ...filters, page: 1 })}
        onReset={() => {
          setFilters(DEFAULT_FILTERS);
          setAppliedFilters(DEFAULT_FILTERS);
          setActiveSavedView('all');
        }}
      />

      <div className="marketing-campaigns__toolbar">
        <div className="marketing-campaigns__view-modes">
          {(['table', 'card'] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              className={
                viewMode === mode
                  ? 'marketing-campaigns__view-mode marketing-campaigns__view-mode--active'
                  : 'marketing-campaigns__view-mode'
              }
              onClick={() => setViewMode(mode)}
            >
              {t(`viewModes.${mode}`)}
            </button>
          ))}
        </div>
      </div>

      {selectedIds.length > 0 && (
        <div className="marketing-bulk-bar">
          <span>{t('bulk.selected', { count: selectedIds.length })}</span>
          {canActivateCampaigns(user) && (
            <Button onClick={() => bulkMutation.mutate('activate')} disabled={bulkMutation.isPending}>
              {t('bulk.activate')}
            </Button>
          )}
          {canPauseCampaigns(user) && (
            <Button variant="secondary" onClick={() => bulkMutation.mutate('pause')} disabled={bulkMutation.isPending}>
              {t('bulk.pause')}
            </Button>
          )}
          <Button variant="secondary" onClick={() => bulkMutation.mutate('submit_approval')} disabled={bulkMutation.isPending}>
            {t('bulk.submitApproval')}
          </Button>
          <Button variant="ghost" onClick={clearSelection}>
            {tCommon('cancel')}
          </Button>
        </div>
      )}

      {rows.length === 0 ? (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      ) : viewMode === 'card' ? (
        <div className="marketing-card-grid">
          {rows.map((row) => (
            <Link key={row.id} href={`/workspaces/marketing/campaigns/${row.id}` as Route} className="marketing-campaign-card">
              <div className="marketing-campaign-card__title">{row.name}</div>
              <div className="marketing-campaign-card__meta">
                <CampaignStatusChip status={row.status} label={tStatus(row.status)} />
                {' · '}
                {t(`types.${row.campaign_type}` as 'types.other')}
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <AdminDataTable
          columns={columns}
          rows={rows}
          rowKey={(row) => row.id}
          pageSize={appliedFilters.page_size}
          exportFileName="marketing-campaigns.csv"
          selectedIds={selectedIds}
          onSelectedIdsChange={setSelectedIds}
          emptyMessage={t('emptyTitle')}
        />
      )}
    </div>
  );
}
