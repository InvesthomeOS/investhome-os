'use client';

import { useCallback, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState } from '@investhome/ui';

import { canBulkActionsCrm } from '@/lib/crm/crm-permissions';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { activityMutations, activityQueries, activityQueryKeys } from '@/workspaces/crm/hooks/use-activities';
import type { ActivityListParams } from '@/workspaces/crm/types/activities';
import { useActivityUiStore } from '@/workspaces/crm/stores/activity-ui-store';

import { ActivityCard } from '../../_components/activity-card';
import { ActivityDetailPanel } from '../../_components/activity-detail-panel';
import { ActivityFilters, type ActivityFilterState } from '../../_components/activity-filters';
import { ActivityFormModal } from '../../_components/activity-form-modal';

const DEFAULT_FILTERS: ActivityFilterState = {
  page: 1,
  page_size: 25,
  sort_by: 'created_at',
  sort_dir: 'desc',
};

export function ActivitiesWorkspace() {
  const t = useTranslations('crm.activities');
  const tCommon = useTranslations('common');
  const { authLoading, user, canRead: canView, canCreate } = useCrmAccess();
  const queryClient = useQueryClient();
  const { selectedActivityId, selectedIds, setSelectedActivityId, toggleSelectedId, clearSelection } =
    useActivityUiStore();

  const [filters, setFilters] = useState<ActivityFilterState>(DEFAULT_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<ActivityFilterState>(DEFAULT_FILTERS);
  const [formOpen, setFormOpen] = useState(false);

  const canBulk = canBulkActionsCrm(user);
  const canQuery = !authLoading && canView;

  const listParams: ActivityListParams = useMemo(() => appliedFilters, [appliedFilters]);

  const listQuery = useQuery({
    ...activityQueries.list(listParams),
    enabled: canQuery,
  });
  const detailQuery = useQuery({
    ...activityQueries.detail(selectedActivityId ?? ''),
    enabled: canQuery && Boolean(selectedActivityId),
  });

  const bulkMutation = useMutation({
    mutationFn: (payload: { archive?: boolean; priority?: string }) =>
      activityMutations.bulkUpdate({
        activity_ids: selectedIds,
        archive: payload.archive,
        priority: payload.priority,
      }),
    onSuccess: async () => {
      clearSelection();
      await queryClient.invalidateQueries({ queryKey: activityQueryKeys.all });
    },
  });

  const invalidate = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: activityQueryKeys.all });
  }, [queryClient]);

  if (authLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (!canView) {
    return <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />;
  }

  if (listQuery.isLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

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

  return (
    <div className="crm-activities">
      <header className="crm-activities__header">
        <div>
          <h1 className="dashboard__title">{t('title')}</h1>
          <p className="dashboard__subtitle">{t('subtitle')}</p>
        </div>
        {canCreate && (
          <Button type="button" onClick={() => setFormOpen(true)}>
            {t('create')}
          </Button>
        )}
      </header>

      <ActivityFilters
        filters={filters}
        filterLogic="and"
        onChange={setFilters}
        onFilterLogicChange={() => undefined}
        onApply={() => setAppliedFilters({ ...filters, page: 1 })}
        onReset={() => {
          setFilters(DEFAULT_FILTERS);
          setAppliedFilters(DEFAULT_FILTERS);
        }}
      />

      {canBulk && selectedIds.length > 0 && (
        <div className="crm-bulk-bar">
          <span>{t('selectedCount', { count: selectedIds.length })}</span>
          <Button type="button" variant="secondary" onClick={() => bulkMutation.mutate({ priority: 'high' })}>
            {t('bulkPriorityHigh')}
          </Button>
          <Button type="button" variant="secondary" onClick={() => bulkMutation.mutate({ archive: true })}>
            {t('bulkArchive')}
          </Button>
          <Button type="button" variant="secondary" onClick={clearSelection}>
            {tCommon('cancel')}
          </Button>
        </div>
      )}

      <div className="crm-activities__layout">
        <div className="crm-activities__list">
          {items.length === 0 ? (
            <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
          ) : (
            items.map((item) => (
              <div key={item.id} className="crm-activities__list-row">
                {canBulk && (
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(item.id)}
                    onChange={() => toggleSelectedId(item.id)}
                    aria-label={t('selectActivity')}
                  />
                )}
                <ActivityCard
                  item={item}
                  selected={selectedActivityId === item.id}
                  onSelect={setSelectedActivityId}
                />
              </div>
            ))
          )}
        </div>

        {selectedActivityId && (
          <ActivityDetailPanel
            activity={detailQuery.data}
            loading={detailQuery.isLoading}
            error={detailQuery.error?.message}
            onClose={() => setSelectedActivityId(null)}
            onComplete={async (id) => {
              await activityMutations.completeTask(id);
              await invalidate();
            }}
          />
        )}
      </div>

      <ActivityFormModal open={formOpen} onClose={() => setFormOpen(false)} />
    </div>
  );
}
