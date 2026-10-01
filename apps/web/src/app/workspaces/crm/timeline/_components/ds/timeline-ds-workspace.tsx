'use client';

import type { Route } from 'next';
import { Suspense, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';

import { Button, ErrorState, Input, Select, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { fetchAgreements } from '@/workspaces/crm/api/agreements';
import { activityQueries, activityQueryKeys } from '@/workspaces/crm/hooks/use-activities';
import { contactQueries } from '@/workspaces/crm/hooks/use-contacts';
import type { ActivityListParams } from '@/workspaces/crm/types/activities';

import {
  CATEGORY_ICON,
  EMPTY_OPS_FILTERS,
  EVENT_KIND_OPTIONS,
  clusterCommunicationEvents,
  formatEventDateTime,
  formatEventTime,
  groupEventsByDay,
  mapTimelineEntry,
  type TimelineEvent,
  type TimelineFeedRow,
  type TimelineOpsFilters,
} from './timeline-ds-model';

import './timeline-ds.css';

function isLiveActivityId(id: string): boolean {
  return !id.startsWith('log-') && !id.startsWith('agreement-') && !id.startsWith('document-') && !id.startsWith('cluster-');
}

function EventRow({
  event,
  selected,
  nested,
  onSelect,
}: {
  event: TimelineEvent;
  selected: boolean;
  nested?: boolean;
  onSelect: (event: TimelineEvent) => void;
}) {
  const t = useTranslations('crm.timeline.ds');
  const locale = useLocale();
  const high = event.priorityTier === 'high';
  const person = event.personName?.trim() || null;
  return (
    <button
      type="button"
      className={`tl-ds__event${selected ? ' is-selected' : ''}${high ? ' is-high' : ''}${nested ? ' is-nested' : ''}`}
      onClick={() => onSelect(event)}
      data-testid={`timeline-ds-event-${event.id}`}
    >
      <span className="tl-ds__event-time">{formatEventTime(event.occurredAt, locale)}</span>
      <span className={`tl-ds__event-node is-${event.category}${high ? ' is-high' : ''}`} aria-hidden="true">
        <IhIcon name={CATEGORY_ICON[event.category]} size={11} />
      </span>
      <span className="tl-ds__event-body">
        <span className="tl-ds__event-title-row">
          <strong className="tl-ds__event-title">{event.title}</strong>
          <span className={`tl-ds__source-badge is-${event.eventKind}`}>{event.sourceBadge}</span>
          {event.status && event.status !== 'completed' ? (
            <StatusChip tone={event.status === 'cancelled' || event.status === 'missed' ? 'danger' : 'info'}>
              {t(`statuses.${event.status}`)}
            </StatusChip>
          ) : null}
        </span>
        <span className="tl-ds__event-meta">
          {person ? <span>{person}</span> : null}
          {event.projectLabel ? <span>{event.projectLabel}</span> : null}
          {event.unitNumber ? <span>Daire {event.unitNumber}</span> : null}
        </span>
      </span>
    </button>
  );
}

function EventDrawer({
  event,
  onClose,
}: {
  event: TimelineEvent;
  onClose: () => void;
}) {
  const t = useTranslations('crm.timeline.ds');
  const locale = useLocale();
  const router = useRouter();
  const liveId = isLiveActivityId(event.id) ? event.id : '';
  const detailQuery = useQuery({
    ...activityQueries.detail(liveId),
    enabled: Boolean(liveId),
  });
  const description =
    detailQuery.data?.description ||
    detailQuery.data?.summary ||
    event.fullDescription ||
    event.description;
  const relatedName = detailQuery.data?.attachments?.[0]?.file_name || event.documentName;

  return (
    <aside className="tl-ds__drawer" role="dialog" aria-label={t('detail.title')} data-testid="timeline-ds-drawer">
      <div className="tl-ds__card-head">
        <h3>{t('detail.title')}</h3>
        <button type="button" className="tl-ds__card-link" onClick={onClose}>
          {t('detail.close')}
        </button>
      </div>
      <div className="tl-ds__drawer-scroll">
        <dl className="tl-ds__kv">
          {event.personName ? (
            <>
              <dt>{t('detail.person')}</dt>
              <dd>{event.personName}</dd>
            </>
          ) : null}
          {event.projectLabel ? (
            <>
              <dt>{t('detail.project')}</dt>
              <dd>{event.projectLabel}</dd>
            </>
          ) : null}
          {event.unitNumber ? (
            <>
              <dt>{t('detail.unit')}</dt>
              <dd>{event.unitNumber}</dd>
            </>
          ) : null}
          <dt>{t('detail.eventType')}</dt>
          <dd>{event.sourceBadge}</dd>
          <dt>{t('detail.when')}</dt>
          <dd>{formatEventDateTime(event.occurredAt, locale)}</dd>
          <dt>{t('detail.source')}</dt>
          <dd>{event.sourceBadge}</dd>
        </dl>
        <section className="tl-ds__section">
          <div className="tl-ds__section-head">
            <h3>{t('detail.description')}</h3>
          </div>
          <p>{description || t('detail.noDescription')}</p>
        </section>
        {relatedName ? (
          <section className="tl-ds__section">
            <div className="tl-ds__section-head">
              <h3>{t('detail.relatedRecord')}</h3>
            </div>
            <p>{relatedName}</p>
          </section>
        ) : null}
        <div className="tl-ds__drawer-actions">
          {event.contactHref ? (
            <Button
              type="button"
              variant="primary"
              size="sm"
              onClick={() => router.push(event.contactHref as Route)}
            >
              {t('actions.openContact')}
            </Button>
          ) : null}
          {event.purchaseHref ? (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => router.push(event.purchaseHref as Route)}
            >
              {t('actions.openPurchase')}
            </Button>
          ) : null}
        </div>
      </div>
    </aside>
  );
}

function TimelineDsWorkspaceInner() {
  const t = useTranslations('crm.timeline.ds');
  const tRoot = useTranslations('crm.timeline');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { authLoading, canRead: canView } = useCrmAccess();

  const [filters, setFilters] = useState<TimelineOpsFilters>(EMPTY_OPS_FILTERS);
  const [searchDraft, setSearchDraft] = useState('');
  const [personDraft, setPersonDraft] = useState('');
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [expandedClusters, setExpandedClusters] = useState<Set<string>>(new Set());

  const canViewEnabled = !authLoading && canView;

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setFilters((prev) => ({ ...prev, search: searchDraft }));
    }, 220);
    return () => window.clearTimeout(timer);
  }, [searchDraft]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setFilters((prev) => ({
        ...prev,
        person: personDraft,
        personId: personDraft.trim() ? prev.personId : null,
      }));
    }, 220);
    return () => window.clearTimeout(timer);
  }, [personDraft]);

  const apiFilters = useMemo<ActivityListParams>(() => {
    const params: ActivityListParams = {
      page: 1,
      page_size: 40,
      sort_by: 'created_at',
      sort_dir: 'desc',
    };
    if (filters.search.trim()) params.search = filters.search.trim();
    if (filters.personId) {
      params.entity_type = 'contact';
      params.entity_id = filters.personId;
    } else if (filters.person.trim()) {
      params.contact_search = filters.person.trim();
    }
    if (filters.projectGroup) params.project_group = filters.projectGroup;
    if (filters.eventKind) params.event_kind = filters.eventKind;
    if (filters.dateFrom) params.date_from = `${filters.dateFrom}T00:00:00.000Z`;
    if (filters.dateTo) params.date_to = `${filters.dateTo}T23:59:59.999Z`;
    return params;
  }, [filters]);

  const timelineQuery = useInfiniteQuery({
    queryKey: activityQueryKeys.timeline(apiFilters),
    queryFn: ({ pageParam = 1 }) =>
      activityQueries.timeline({ ...apiFilters, page: pageParam }).queryFn(),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => (lastPage.page < lastPage.pages ? lastPage.page + 1 : undefined),
    enabled: canViewEnabled,
  });

  const liveItems = useMemo(
    () => timelineQuery.data?.pages.flatMap((page) => page.items) ?? [],
    [timelineQuery.data],
  );
  const events = useMemo(() => liveItems.map(mapTimelineEntry), [liveItems]);
  const total = timelineQuery.data?.pages[0]?.total ?? events.length;
  const grouped = useMemo(() => groupEventsByDay(events, locale), [events, locale]);

  const projectsQuery = useQuery({
    queryKey: ['crm', 'agreements', 'timeline-projects'],
    queryFn: () => fetchAgreements({ page: 1, page_size: 1 }),
    enabled: canViewEnabled,
  });

  const personSuggestQuery = useQuery({
    ...contactQueries.list({ search: personDraft.trim(), page: 1, page_size: 8 }),
    enabled: canViewEnabled && personDraft.trim().length >= 2 && !filters.personId,
  });

  const selectedEvent = events.find((event) => event.id === selectedEventId) ?? null;

  const resetFilters = () => {
    setFilters(EMPTY_OPS_FILTERS);
    setSearchDraft('');
    setPersonDraft('');
    setSelectedEventId(null);
  };

  const patchFilters = (patch: Partial<TimelineOpsFilters>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
  };

  const toggleCluster = (id: string) => {
    setExpandedClusters((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  if (authLoading) {
    return (
      <div className="tl-ds" data-testid="timeline-ds-workspace">
        <div className="tl-ds__skeleton" aria-hidden="true">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="tl-ds__skeleton-row" />
          ))}
        </div>
      </div>
    );
  }

  if (!canView) {
    return <ErrorState title={tRoot('accessDenied')} message={tRoot('accessDeniedHint')} />;
  }

  if (timelineQuery.isError) {
    return (
      <ErrorState
        title={tRoot('loadFailed')}
        message={timelineQuery.error?.message ?? tRoot('loadFailed')}
        action={
          <Button type="button" onClick={() => void timelineQuery.refetch()}>
            {tCommon('retry')}
          </Button>
        }
      />
    );
  }

  const loadingList = timelineQuery.isLoading;
  const suggestions = personSuggestQuery.data?.items ?? [];

  return (
    <div className="tl-ds tl-ds--ops" data-testid="timeline-ds-workspace">
      <header className="tl-ds__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
        <span className="tl-ds__panel-head-meta">{t('feed.count', { count: total })}</span>
      </header>

      <section className="tl-ds__toolbar" aria-label={t('filters.aria')}>
        <div className="tl-ds__toolbar-search">
          <Input
            label={t('filters.search')}
            value={searchDraft}
            onChange={(e) => setSearchDraft(e.target.value)}
            placeholder={t('filters.searchPlaceholder')}
            data-testid="timeline-ds-search"
          />
        </div>
        <div className="tl-ds__person-field">
          <Input
            label={t('filters.person')}
            value={personDraft}
            onChange={(e) => {
              setPersonDraft(e.target.value);
              patchFilters({ personId: null });
            }}
            placeholder={t('filters.personPlaceholder')}
            data-testid="timeline-ds-person"
          />
          {suggestions.length > 0 ? (
            <ul className="tl-ds__suggest" role="listbox">
              {suggestions.map((contact) => (
                <li key={contact.id}>
                  <button
                    type="button"
                    onClick={() => {
                      setPersonDraft(contact.display_name);
                      patchFilters({ person: contact.display_name, personId: contact.id });
                    }}
                  >
                    {contact.display_name}
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
        <Select
          label={t('filters.project')}
          value={filters.projectGroup}
          onChange={(e) => patchFilters({ projectGroup: e.target.value })}
          data-testid="timeline-ds-project"
        >
          <option value="">{t('filters.allProjects')}</option>
          {(projectsQuery.data?.project_groups ?? []).map((group) => (
            <option key={group.id} value={group.id}>
              {group.label}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.eventKind')}
          value={filters.eventKind}
          onChange={(e) => patchFilters({ eventKind: e.target.value })}
          data-testid="timeline-ds-event-kind"
        >
          <option value="">{t('filters.allEventKinds')}</option>
          {EVENT_KIND_OPTIONS.map((kind) => (
            <option key={kind} value={kind}>
              {t(`eventKinds.${kind}`)}
            </option>
          ))}
        </Select>
        <Input
          label={t('filters.dateFrom')}
          type="date"
          value={filters.dateFrom}
          onChange={(e) => patchFilters({ dateFrom: e.target.value })}
        />
        <Input
          label={t('filters.dateTo')}
          type="date"
          value={filters.dateTo}
          onChange={(e) => patchFilters({ dateTo: e.target.value })}
        />
        <div className="tl-ds__toolbar-actions">
          <Button type="button" variant="secondary" size="sm" onClick={resetFilters}>
            {t('filters.clear')}
          </Button>
        </div>
      </section>

      <div className="tl-ds__workspace tl-ds__workspace--ops">
        <section className="tl-ds__panel tl-ds__panel--feed" aria-label={t('feed.title')}>
          <div className="tl-ds__panel-body">
            {loadingList ? (
              <div className="tl-ds__skeleton" aria-hidden="true">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="tl-ds__skeleton-row" />
                ))}
              </div>
            ) : events.length === 0 ? (
              <div className="tl-ds__empty" data-testid="timeline-ds-empty">
                <IhIcon name="empty" size={22} />
                <strong>{t('empty.title')}</strong>
                <p>{t('empty.description')}</p>
              </div>
            ) : (
              grouped.map((group) => {
                const rows = clusterCommunicationEvents(group.events);
                return (
                  <section key={group.key} className="tl-ds__day">
                    <header className="tl-ds__day-label">
                      {group.labelKey === 'date' ? group.dateLabel : t(`feed.${group.labelKey}`)}
                    </header>
                    <div className="tl-ds__day-events">
                      {rows.map((row: TimelineFeedRow) => {
                        if (row.type === 'cluster') {
                          const expanded = expandedClusters.has(row.id);
                          return (
                            <div key={row.id} className="tl-ds__cluster">
                              <button
                                type="button"
                                className="tl-ds__cluster-toggle"
                                onClick={() => toggleCluster(row.id)}
                                data-testid={`timeline-ds-cluster-${row.eventKind}`}
                              >
                                <span className={`tl-ds__source-badge is-${row.eventKind}`}>{row.sourceBadge}</span>
                                <strong>
                                  {row.sourceBadge} — {t('feed.messageCount', { count: row.events.length })}
                                </strong>
                                {row.personName ? <span>{row.personName}</span> : null}
                                <span aria-hidden="true">{expanded ? '▾' : '▸'}</span>
                              </button>
                              {expanded
                                ? row.events.map((event) => (
                                    <EventRow
                                      key={event.id}
                                      event={event}
                                      nested
                                      selected={selectedEventId === event.id}
                                      onSelect={(item) => setSelectedEventId(item.id)}
                                    />
                                  ))
                                : null}
                            </div>
                          );
                        }
                        return (
                          <EventRow
                            key={row.event.id}
                            event={row.event}
                            selected={selectedEventId === row.event.id}
                            onSelect={(item) => setSelectedEventId(item.id)}
                          />
                        );
                      })}
                    </div>
                  </section>
                );
              })
            )}
            {timelineQuery.hasNextPage ? (
              <div className="tl-ds__load-more">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => void timelineQuery.fetchNextPage()}
                  disabled={timelineQuery.isFetchingNextPage}
                >
                  {timelineQuery.isFetchingNextPage ? tCommon('loading') : t('feed.loadMore')}
                </Button>
              </div>
            ) : null}
          </div>
        </section>
      </div>

      {selectedEvent ? (
        <>
          <button
            type="button"
            className="tl-ds__drawer-backdrop is-open"
            aria-label={t('detail.close')}
            onClick={() => setSelectedEventId(null)}
          />
          <EventDrawer event={selectedEvent} onClose={() => setSelectedEventId(null)} />
        </>
      ) : null}
    </div>
  );
}

export function TimelineDsWorkspace() {
  return (
    <Suspense
      fallback={
        <div className="tl-ds" data-testid="timeline-ds-workspace">
          <div className="tl-ds__skeleton" aria-hidden="true">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="tl-ds__skeleton-row" />
            ))}
          </div>
        </div>
      }
    >
      <TimelineDsWorkspaceInner />
    </Suspense>
  );
}
