'use client';

import type { Route } from 'next';
import { useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';

import { Button, ErrorState, Input, Select, StatusChip } from '@investhome/ui';

import { fetchUsers } from '@/lib/api/auth';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { fetchAgreements } from '@/workspaces/crm/api/agreements';
import { salesDetailUrl } from '@/workspaces/crm/contact-card/pilot-people';
import { activityQueries, activityQueryKeys } from '@/workspaces/crm/hooks/use-activities';
import { contactQueries } from '@/workspaces/crm/hooks/use-contacts';
import type { ActivityListParams, CrmActivityStatus } from '@/workspaces/crm/types/activities';

import {
  EVENT_KIND_OPTIONS,
  TIMELINE_STATUSES,
  clusterCommunicationEvents,
  formatEventDateTime,
  mapTimelineEntry,
  type TimelineEvent,
  type TimelineFeedRow,
} from '@/app/workspaces/crm/timeline/_components/ds/timeline-ds-model';

import '../activities.css';

type OpsFilters = {
  search: string;
  eventKind: string;
  person: string;
  personId: string | null;
  projectGroup: string;
  ownerId: string;
  status: string;
  dateFrom: string;
  dateTo: string;
};

const EMPTY_FILTERS: OpsFilters = {
  search: '',
  eventKind: '',
  person: '',
  personId: null,
  projectGroup: '',
  ownerId: '',
  status: '',
  dateFrom: '',
  dateTo: '',
};

function isLiveActivityId(id: string): boolean {
  return (
    !id.startsWith('log-') &&
    !id.startsWith('agreement-') &&
    !id.startsWith('document-') &&
    !id.startsWith('cluster-')
  );
}

function personLabel(event: TimelineEvent, unresolved: string): string {
  const name = event.personName?.trim();
  if (name) return name;
  if (event.entityKind === 'people' && event.entityId) return unresolved;
  return '—';
}

function projectUnit(event: TimelineEvent): string {
  const parts = [event.projectLabel, event.unitNumber ? `Daire ${event.unitNumber}` : null].filter(Boolean);
  return parts.join(' · ') || '—';
}

function statusKey(status?: string): 'completed' | 'planned' | 'scheduled' | 'in_progress' | 'cancelled' | 'missed' | 'deferred' {
  if (
    status === 'planned' ||
    status === 'scheduled' ||
    status === 'in_progress' ||
    status === 'cancelled' ||
    status === 'missed' ||
    status === 'deferred'
  ) {
    return status;
  }
  return 'completed';
}

function ActivityDrawer({
  event,
  onClose,
}: {
  event: TimelineEvent;
  onClose: () => void;
}) {
  const t = useTranslations('crm.activities');
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
  const related = detailQuery.data?.attachments?.[0]?.file_name || event.documentName;
  const person = personLabel(event, t('unresolvedIdentity'));
  const owner = event.owner?.trim() || detailQuery.data?.owner_name || detailQuery.data?.assigned_user_name || '—';
  const purchaseHref =
    event.agreementId && event.entityId && event.entityKind === 'people'
      ? salesDetailUrl(event.entityId, event.agreementId)
      : event.purchaseHref;

  return (
    <aside className="crm-activities-ds__drawer" role="dialog" aria-label={t('drawer.title')} data-testid="crm-activities-drawer">
      <div className="crm-activities-ds__drawer-head">
        <h3>{t('drawer.title')}</h3>
        <button type="button" className="crm-activities-ds__link-btn" onClick={onClose}>
          {t('actions.close')}
        </button>
      </div>
      <div className="crm-activities-ds__drawer-body">
        <dl className="crm-activities-ds__kv">
          <dt>{t('drawer.person')}</dt>
          <dd>{person}</dd>
          <dt>{t('drawer.project')}</dt>
          <dd>{event.projectLabel || '—'}</dd>
          <dt>{t('drawer.unit')}</dt>
          <dd>{event.unitNumber || '—'}</dd>
          <dt>{t('drawer.type')}</dt>
          <dd>{event.sourceBadge}</dd>
          <dt>{t('drawer.when')}</dt>
          <dd>{formatEventDateTime(event.occurredAt, locale)}</dd>
          <dt>{t('drawer.owner')}</dt>
          <dd>{owner}</dd>
          <dt>{t('drawer.status')}</dt>
          <dd>{t(`statuses.${statusKey(event.status)}`)}</dd>
          <dt>{t('drawer.source')}</dt>
          <dd>
            {[event.sourceBadge, event.recordSource].filter(Boolean).join(' · ') || '—'}
          </dd>
        </dl>
        <section>
          <h4>{t('drawer.description')}</h4>
          <p>{description || t('drawer.noDescription')}</p>
        </section>
        {related ? (
          <section>
            <h4>{t('drawer.related')}</h4>
            <p>{related}</p>
          </section>
        ) : null}
        <div className="crm-activities-ds__drawer-actions">
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
          {purchaseHref ? (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => router.push(purchaseHref as Route)}
            >
              {t('actions.openPurchase')}
            </Button>
          ) : null}
        </div>
      </div>
    </aside>
  );
}

export function CrmActivitiesWorkspace() {
  const t = useTranslations('crm.activities');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { authLoading, canRead: canView } = useCrmAccess();
  const [filters, setFilters] = useState<OpsFilters>(EMPTY_FILTERS);
  const [searchDraft, setSearchDraft] = useState('');
  const [personDraft, setPersonDraft] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [expandedClusters, setExpandedClusters] = useState<Set<string>>(new Set());

  const canQuery = !authLoading && canView;

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
    if (filters.ownerId) params.owner_id = filters.ownerId;
    if (filters.status) params.status = filters.status as CrmActivityStatus;
    if (filters.dateFrom) params.date_from = `${filters.dateFrom}T00:00:00.000Z`;
    if (filters.dateTo) params.date_to = `${filters.dateTo}T23:59:59.999Z`;
    return params;
  }, [filters]);

  const listQuery = useInfiniteQuery({
    queryKey: activityQueryKeys.timeline(apiFilters),
    queryFn: ({ pageParam = 1 }) =>
      activityQueries.timeline({ ...apiFilters, page: pageParam }).queryFn(),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => (lastPage.page < lastPage.pages ? lastPage.page + 1 : undefined),
    enabled: canQuery,
  });

  const liveItems = useMemo(
    () => listQuery.data?.pages.flatMap((page) => page.items) ?? [],
    [listQuery.data],
  );
  const events = useMemo(() => liveItems.map(mapTimelineEntry), [liveItems]);
  const rows = useMemo(() => clusterCommunicationEvents(events), [events]);
  const total = listQuery.data?.pages[0]?.total ?? events.length;
  const selected = events.find((event) => event.id === selectedId) ?? null;

  const projectsQuery = useQuery({
    queryKey: ['crm', 'agreements', 'activity-projects'],
    queryFn: () => fetchAgreements({ page: 1, page_size: 1 }),
    enabled: canQuery,
  });
  const usersQuery = useQuery({
    queryKey: ['users', 'activity-filter'],
    queryFn: () => fetchUsers({ status: 'active' }),
    enabled: canQuery,
  });
  const personSuggestQuery = useQuery({
    ...contactQueries.list({ search: personDraft.trim(), page: 1, page_size: 8 }),
    enabled: canQuery && personDraft.trim().length >= 2 && !filters.personId,
  });

  const patchFilters = (patch: Partial<OpsFilters>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
  };

  const clearFilters = () => {
    setFilters(EMPTY_FILTERS);
    setSearchDraft('');
    setPersonDraft('');
    setSelectedId(null);
  };

  if (authLoading) {
    return (
      <div className="crm-activities-ds crm-activities-ds--ops" data-testid="crm-activities-workspace">
        <div className="crm-activities-ds__skeleton" aria-hidden="true">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="crm-activities-ds__skeleton-row" />
          ))}
        </div>
      </div>
    );
  }

  if (!canView) {
    return <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />;
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

  const suggestions = personSuggestQuery.data?.items ?? [];

  const renderEventRow = (event: TimelineEvent, nested = false) => {
    const unresolved = t('unresolvedIdentity');
    const person = personLabel(event, unresolved);
    const high = event.priorityTier === 'high';
    return (
      <tr
        key={event.id}
        className={`crm-activities-ds__row${selectedId === event.id ? ' is-selected' : ''}${high ? ' is-high' : ''}${nested ? ' is-nested' : ''}`}
        onClick={() => setSelectedId(event.id)}
        data-testid={`crm-activity-row-${event.id}`}
      >
        <td>{formatEventDateTime(event.occurredAt, locale)}</td>
        <td>
          <strong>{event.title}</strong>
        </td>
        <td>{person}</td>
        <td>{projectUnit(event)}</td>
        <td>
          <span className={`crm-activities-ds__type-pill is-${event.eventKind}`}>{event.sourceBadge}</span>
        </td>
        <td>{event.owner?.trim() || '—'}</td>
        <td>
          <StatusChip
            tone={
              event.status === 'cancelled' || event.status === 'missed'
                ? 'danger'
                : event.status === 'completed'
                  ? 'success'
                  : 'info'
            }
          >
            {t(`statuses.${statusKey(event.status)}`)}
          </StatusChip>
        </td>
      </tr>
    );
  };

  const renderFeedRow = (row: TimelineFeedRow) => {
    if (row.type === 'cluster') {
      const expanded = expandedClusters.has(row.id);
      return (
        <tbody key={row.id}>
          <tr className="crm-activities-ds__cluster-row">
            <td colSpan={7}>
              <button
                type="button"
                className="crm-activities-ds__cluster-toggle"
                onClick={() =>
                  setExpandedClusters((prev) => {
                    const next = new Set(prev);
                    if (next.has(row.id)) next.delete(row.id);
                    else next.add(row.id);
                    return next;
                  })
                }
              >
                <span className={`crm-activities-ds__type-pill is-${row.eventKind}`}>{row.sourceBadge}</span>
                <strong>
                  {row.sourceBadge} — {t('group.messages', { count: row.events.length })}
                </strong>
                {row.personName ? <span>{row.personName}</span> : null}
                <span aria-hidden="true">{expanded ? '▾' : '▸'}</span>
              </button>
            </td>
          </tr>
          {expanded ? row.events.map((event) => renderEventRow(event, true)) : null}
        </tbody>
      );
    }
    return <tbody key={row.event.id}>{renderEventRow(row.event)}</tbody>;
  };

  return (
    <div className="crm-activities-ds crm-activities-ds--ops" data-testid="crm-activities-workspace">
      <header className="crm-activities-ds__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
        <span className="crm-activities-ds__count">{t('pagination.total', { count: total })}</span>
      </header>

      <section className="crm-activities-ds__filters" aria-label={t('filters.aria')}>
        <div className="crm-activities-ds__search">
          <Input
            label={t('filters.search')}
            value={searchDraft}
            onChange={(e) => setSearchDraft(e.target.value)}
            placeholder={t('filters.searchPlaceholder')}
            data-testid="crm-activities-search"
          />
        </div>
        <Select
          label={t('filters.type')}
          value={filters.eventKind}
          onChange={(e) => patchFilters({ eventKind: e.target.value })}
        >
          <option value="">{t('filters.any')}</option>
          {EVENT_KIND_OPTIONS.map((kind) => (
            <option key={kind} value={kind}>
              {t(`eventKinds.${kind}`)}
            </option>
          ))}
        </Select>
        <div className="crm-activities-ds__person-field">
          <Input
            label={t('filters.person')}
            value={personDraft}
            onChange={(e) => {
              setPersonDraft(e.target.value);
              patchFilters({ personId: null });
            }}
            placeholder={t('filters.personPlaceholder')}
          />
          {suggestions.length > 0 ? (
            <ul className="crm-activities-ds__suggest">
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
        >
          <option value="">{t('filters.allProjects')}</option>
          {(projectsQuery.data?.project_groups ?? []).map((group) => (
            <option key={group.id} value={group.id}>
              {group.label}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.owner')}
          value={filters.ownerId}
          onChange={(e) => patchFilters({ ownerId: e.target.value })}
        >
          <option value="">{t('filters.allOwners')}</option>
          {(usersQuery.data?.items ?? []).map((user) => (
            <option key={user.id} value={user.id}>
              {user.full_name}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.status')}
          value={filters.status}
          onChange={(e) => patchFilters({ status: e.target.value })}
        >
          <option value="">{t('filters.any')}</option>
          {TIMELINE_STATUSES.map((status) => (
            <option key={status} value={status}>
              {t(`statuses.${status}`)}
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
        <div className="crm-activities-ds__filter-actions">
          <Button type="button" variant="secondary" size="sm" onClick={clearFilters}>
            {t('filters.clear')}
          </Button>
        </div>
      </section>

      <div className="crm-activities-ds__table-wrap" role="region" aria-label={t('table.aria')}>
        {listQuery.isLoading ? (
          <div className="crm-activities-ds__skeleton" aria-hidden="true">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="crm-activities-ds__skeleton-row" />
            ))}
          </div>
        ) : events.length === 0 ? (
          <div className="crm-activities-ds__empty" data-testid="crm-activities-empty">
            <strong>{t('emptyTitle')}</strong>
            <p>{t('emptyDescription')}</p>
          </div>
        ) : (
          <table className="crm-activities-ds__table crm-activities-ds__table--ops">
            <thead>
              <tr>
                <th>{t('table.dateTime')}</th>
                <th>{t('table.activity')}</th>
                <th>{t('table.person')}</th>
                <th>{t('table.project')}</th>
                <th>{t('table.type')}</th>
                <th>{t('table.owner')}</th>
                <th>{t('table.status')}</th>
              </tr>
            </thead>
            {rows.map(renderFeedRow)}
          </table>
        )}
        {listQuery.hasNextPage ? (
          <div className="crm-activities-ds__load-more">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => void listQuery.fetchNextPage()}
              disabled={listQuery.isFetchingNextPage}
            >
              {listQuery.isFetchingNextPage ? tCommon('loading') : t('loadMore')}
            </Button>
          </div>
        ) : null}
      </div>

      {selected ? (
        <>
          <button
            type="button"
            className="crm-activities-ds__drawer-backdrop"
            aria-label={t('actions.close')}
            onClick={() => setSelectedId(null)}
          />
          <ActivityDrawer event={selected} onClose={() => setSelectedId(null)} />
        </>
      ) : null}
    </div>
  );
}
