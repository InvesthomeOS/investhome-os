'use client';

import { useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState } from '@investhome/ui';

import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { activityMutations, activityQueries, activityQueryKeys } from '@/workspaces/crm/hooks/use-activities';
import type { ActivityListParams } from '@/workspaces/crm/types/activities';
import { useActivityUiStore } from '@/workspaces/crm/stores/activity-ui-store';

import { ActivityCard } from '../../_components/activity-card';
import { ActivityDetailPanel } from '../../_components/activity-detail-panel';
import { ActivityFilters } from '../../_components/activity-filters';
import { ActivityFormModal } from '../../_components/activity-form-modal';

function groupByDate<T extends { created_at: string }>(
  items: T[],
  locale: string,
): Array<{ label: string; items: T[] }> {
  const formatter = new Intl.DateTimeFormat(locale, { dateStyle: 'full' });
  const groups = new Map<string, T[]>();
  for (const item of items) {
    const key = new Date(item.created_at).toDateString();
    const existing = groups.get(key) ?? [];
    existing.push(item);
    groups.set(key, existing);
  }
  return Array.from(groups.entries()).map(([key, groupItems]) => ({
    label: formatter.format(new Date(key)),
    items: groupItems,
  }));
}

export function TimelineWorkspace() {
  const t = useTranslations('crm.timeline');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { authLoading, canRead: canView, canCreate } = useCrmAccess();
  const queryClient = useQueryClient();
  const {
    filters,
    filterLogic,
    selectedActivityId,
    setSelectedActivityId,
    setFilters,
    resetFilters,
    setFilterLogic,
  } = useActivityUiStore();

  const [appliedFilters, setAppliedFilters] = useState<ActivityListParams>({
    page: 1,
    page_size: 30,
    sort_by: 'created_at',
    sort_dir: 'desc',
  });
  const [formOpen, setFormOpen] = useState(false);
  const [collapsedDates, setCollapsedDates] = useState<Set<string>>(new Set());

  const canViewEnabled = !authLoading && canView;

  const timelineQuery = useInfiniteQuery({
    queryKey: activityQueryKeys.timeline(appliedFilters),
    queryFn: ({ pageParam = 1 }) =>
      activityQueries.timeline({ ...appliedFilters, page: pageParam }).queryFn(),
    initialPageParam: 1,
    getNextPageParam: (lastPage) =>
      lastPage.page < lastPage.pages ? lastPage.page + 1 : undefined,
    enabled: canViewEnabled,
  });

  const detailQuery = useQuery({
    ...activityQueries.detail(selectedActivityId ?? ''),
    enabled: canViewEnabled && Boolean(selectedActivityId),
  });

  const completeMutation = useMutation({
    mutationFn: (id: string) => activityMutations.completeTask(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: activityQueryKeys.all });
      await queryClient.invalidateQueries({ queryKey: ['crm', 'timeline'] });
    },
  });

  const items = useMemo(
    () => timelineQuery.data?.pages.flatMap((page) => page.items) ?? [],
    [timelineQuery.data],
  );
  const grouped = useMemo(() => groupByDate(items, locale), [items, locale]);

  useEffect(() => {
    setAppliedFilters({ ...filters, page: 1, page_size: 30 });
  }, [filters]);

  if (authLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (!canView) {
    return <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />;
  }

  if (timelineQuery.isLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (timelineQuery.isError) {
    return (
      <ErrorState
        title={t('loadFailed')}
        message={timelineQuery.error?.message ?? t('loadFailed')}
        action={
          <Button type="button" onClick={() => void timelineQuery.refetch()}>
            {tCommon('retry')}
          </Button>
        }
      />
    );
  }

  return (
    <div className="crm-timeline">
      <header className="crm-timeline__header">
        <div>
          <h1 className="dashboard__title">{t('title')}</h1>
          <p className="dashboard__subtitle">{t('subtitle')}</p>
        </div>
        {canCreate && (
          <Button type="button" onClick={() => setFormOpen(true)}>
            {t('createActivity')}
          </Button>
        )}
      </header>

      <ActivityFilters
        filters={filters}
        filterLogic={filterLogic}
        onChange={setFilters}
        onFilterLogicChange={setFilterLogic}
        onApply={() => setAppliedFilters({ ...filters, page: 1, page_size: 30 })}
        onReset={() => {
          resetFilters();
          setAppliedFilters({ page: 1, page_size: 30, sort_by: 'created_at', sort_dir: 'desc' });
        }}
      />

      <div className="crm-timeline__layout">
        <div className="crm-timeline__feed">
          {items.length === 0 ? (
            <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
          ) : (
            grouped.map((group) => {
              const collapsed = collapsedDates.has(group.label);
              return (
                <section key={group.label} className="crm-timeline__group">
                  <button
                    type="button"
                    className="crm-timeline__date-sticky"
                    onClick={() => {
                      const next = new Set(collapsedDates);
                      if (collapsed) next.delete(group.label);
                      else next.add(group.label);
                      setCollapsedDates(next);
                    }}
                  >
                    {group.label}
                    <span aria-hidden="true">{collapsed ? '▸' : '▾'}</span>
                  </button>
                  {!collapsed && (
                    <div className="crm-timeline__items">
                      {group.items.map((item) => (
                        <ActivityCard
                          key={item.id}
                          item={item}
                          selected={selectedActivityId === item.id.replace(/^log-/, '')}
                          onSelect={(id) => setSelectedActivityId(id)}
                        />
                      ))}
                    </div>
                  )}
                </section>
              );
            })
          )}
          {timelineQuery.hasNextPage && (
            <div className="crm-timeline__load-more">
              <Button
                type="button"
                variant="secondary"
                onClick={() => void timelineQuery.fetchNextPage()}
                disabled={timelineQuery.isFetchingNextPage}
              >
                {timelineQuery.isFetchingNextPage ? tCommon('loading') : t('loadMore')}
              </Button>
            </div>
          )}
        </div>

        {selectedActivityId && (
          <ActivityDetailPanel
            activity={detailQuery.data}
            loading={detailQuery.isLoading}
            error={detailQuery.error?.message}
            onClose={() => setSelectedActivityId(null)}
            onComplete={(id) => completeMutation.mutate(id)}
          />
        )}
      </div>

      <ActivityFormModal open={formOpen} onClose={() => setFormOpen(false)} defaultType="note" />
    </div>
  );
}
