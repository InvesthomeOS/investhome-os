'use client';

import type { Route } from 'next';
import { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';

import {
  Button,
  ErrorState,
  Input,
  Select,
  StatusChip,
} from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { activityQueries, activityQueryKeys } from '@/workspaces/crm/hooks/use-activities';
import type { ActivityListParams, CrmActivityType } from '@/workspaces/crm/types/activities';

import { ActivityFormModal } from '../../../_components/activity-form-modal';

import {
  CATEGORY_ICON,
  CATEGORY_TONE,
  EMPTY_TIMELINE_FILTERS,
  ENTITY_KIND_ORDER,
  STATUS_TONE,
  TIMELINE_CATEGORIES,
  TIMELINE_STATUSES,
  filterEntities,
  filterEvents,
  formatEventDateTime,
  formatEventTime,
  groupEventsByDay,
  makeTimelineFixture,
  mergeTimelineData,
  uniqueOwners,
  summarizeEntities,
  type TimelineAvatarTone,
  type TimelineDsFilters,
  type TimelineEntity,
  type TimelineEntityKind,
  type TimelineEvent,
  type TimelineEventCategory,
  type TimelineEventStatus,
} from './timeline-ds-model';

import './timeline-ds.css';

function Avatar({
  initials,
  tone,
  size = 'sm',
}: {
  initials: string;
  tone: TimelineAvatarTone;
  size?: 'sm' | 'lg';
}) {
  return (
    <span
      className={`tl-ds__avatar is-${tone}${size === 'lg' ? ' is-lg' : ''}`}
      aria-hidden="true"
    >
      {initials}
    </span>
  );
}

function EventDetailPanel({
  event,
  onClose,
  onCreateFollowUp,
  onCreateTask,
  onAddNote,
}: {
  event: TimelineEvent | null;
  onClose?: () => void;
  onCreateFollowUp: () => void;
  onCreateTask: () => void;
  onAddNote: () => void;
}) {
  const t = useTranslations('crm.timeline.ds');
  const locale = useLocale();
  const router = useRouter();

  if (!event) {
    return (
      <div className="tl-ds__panel-body">
        <div className="tl-ds__empty">
          <IhIcon name="activity" size={22} />
          <strong>{t('detail.emptyTitle')}</strong>
          <p>{t('detail.emptyDescription')}</p>
        </div>
      </div>
    );
  }

  const contactHref = event.contactHref ?? '/workspaces/crm/contacts';
  const companyHref = event.companyHref ?? '/workspaces/crm/companies';
  const leadHref = event.leadHref ?? '/workspaces/crm/leads';
  const projectHref = event.projectHref ?? '/workspaces/crm/projects';

  return (
    <div className="tl-ds__panel-body">
      {onClose ? (
        <div className="tl-ds__card-head">
          <h3>{t('detail.title')}</h3>
          <button type="button" className="tl-ds__card-link" onClick={onClose}>
            {t('detail.close')}
          </button>
        </div>
      ) : null}

      <section className="tl-ds__section" aria-label={t('detail.eventInformation')}>
        <div className="tl-ds__section-head">
          <h3>{t('detail.eventInformation')}</h3>
        </div>
        <div className="tl-ds__detail-hero">
          <span className={`tl-ds__detail-hero-icon is-${event.category}`} aria-hidden="true">
            <IhIcon name={CATEGORY_ICON[event.category]} size={16} />
          </span>
          <div>
            <div className="tl-ds__detail-title-row">
              <h3 className="tl-ds__detail-title">{event.title}</h3>
              <StatusChip tone={STATUS_TONE[event.status]}>
                {t(`statuses.${event.status}`)}
              </StatusChip>
            </div>
            <p className="tl-ds__detail-when">{formatEventDateTime(event.occurredAt, locale)}</p>
          </div>
        </div>
        <div className="tl-ds__person">
          <Avatar initials={event.ownerInitials} tone="cyan" />
          <div className="tl-ds__person-main">
            <span className="tl-ds__person-name">{event.owner}</span>
            {event.ownerTitle ? (
              <span className="tl-ds__person-meta">{event.ownerTitle}</span>
            ) : null}
          </div>
        </div>
        <dl className="tl-ds__dl">
          <div className="tl-ds__dl-row">
            <dt>{t('detail.category')}</dt>
            <dd>
              <StatusChip tone={CATEGORY_TONE[event.category]}>
                {t(`categories.${event.category}`)}
              </StatusChip>
            </dd>
          </div>
          {event.channel ? (
            <div className="tl-ds__dl-row">
              <dt>{t('detail.channel')}</dt>
              <dd>{event.channel}</dd>
            </div>
          ) : null}
        </dl>
        {event.attachments?.length ? (
          <div className="tl-ds__attachment-list">
            {event.attachments.map((att) => (
              <div key={att.id} className="tl-ds__attachment">
                <span className="tl-ds__attachment-icon" aria-hidden="true">
                  <IhIcon name="documents" size={13} />
                </span>
                <div>
                  <span className="tl-ds__attachment-name">{att.name}</span>
                  <span className="tl-ds__attachment-size">{att.sizeLabel}</span>
                </div>
              </div>
            ))}
          </div>
        ) : null}
      </section>

      <section className="tl-ds__section" aria-label={t('detail.relatedRecord')}>
        <div className="tl-ds__section-head">
          <h3>{t('detail.relatedRecord')}</h3>
        </div>
        <div className="tl-ds__person">
          <Avatar
            initials={event.entityName.slice(0, 2).toUpperCase()}
            tone="navy"
            size="lg"
          />
          <div className="tl-ds__person-main">
            <div className="tl-ds__detail-title-row">
              <span className="tl-ds__person-name">{event.entityName}</span>
              {event.entityStatus ? (
                <StatusChip tone={event.entityStatusTone ?? 'default'}>
                  {event.entityStatus}
                </StatusChip>
              ) : null}
            </div>
            <span className="tl-ds__person-meta">{t(`entities.${event.entityKind}`)}</span>
          </div>
        </div>
        {event.relatedRecords?.length ? (
          <div className="tl-ds__related">
            {event.relatedRecords.map((rec) => (
              <button
                key={rec.id}
                type="button"
                onClick={() => router.push(rec.href as Route)}
              >
                {rec.label}
              </button>
            ))}
          </div>
        ) : null}
      </section>

      <section className="tl-ds__section" aria-label={t('detail.description')}>
        <div className="tl-ds__section-head">
          <h3>{t('detail.description')}</h3>
        </div>
        <p>{event.description || t('detail.noDescription')}</p>
        {event.notes ? (
          <p className="tl-ds__section-note">{event.notes}</p>
        ) : null}
      </section>

      <section className="tl-ds__section tl-ds__section--actions" aria-label={t('detail.quickActions')}>
        <div className="tl-ds__section-head">
          <h3>{t('detail.quickActions')}</h3>
        </div>
        <div className="tl-ds__actions">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => router.push(contactHref as Route)}
          >
            {t('actions.openContact')}
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => router.push(companyHref as Route)}
          >
            {t('actions.openCompany')}
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => router.push(leadHref as Route)}
          >
            {t('actions.openLead')}
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => router.push(projectHref as Route)}
          >
            {t('actions.openProject')}
          </Button>
          <Button type="button" variant="secondary" size="sm" onClick={onCreateFollowUp}>
            {t('actions.createFollowUp')}
          </Button>
          <Button type="button" variant="secondary" size="sm" onClick={onCreateTask}>
            {t('actions.createTask')}
          </Button>
          <Button type="button" variant="secondary" size="sm" onClick={onAddNote}>
            {t('actions.addNote')}
          </Button>
          <Button
            type="button"
            variant="primary"
            size="sm"
            onClick={() => router.push('/workspaces/crm/communication' as Route)}
          >
            {t('actions.startCommunication')}
          </Button>
        </div>
      </section>
    </div>
  );
}

function TimelineDsWorkspaceInner() {
  const t = useTranslations('crm.timeline.ds');
  const tRoot = useTranslations('crm.timeline');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const router = useRouter();
  const { authLoading, canRead: canView, canCreate } = useCrmAccess();

  const fixture = useMemo(() => makeTimelineFixture(), []);
  const [filters, setFilters] = useState<TimelineDsFilters>(EMPTY_TIMELINE_FILTERS);
  const [searchDraft, setSearchDraft] = useState('');
  const [entitySearch, setEntitySearch] = useState('');
  const [selectedEventId, setSelectedEventId] = useState<string | null>(
    fixture.events[0]?.id ?? null,
  );
  const [detailOpen, setDetailOpen] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [formDefaultType, setFormDefaultType] = useState<CrmActivityType>('note');
  const todayRef = useRef<HTMLElement | null>(null);

  const canViewEnabled = !authLoading && canView;

  const apiFilters = useMemo<ActivityListParams>(() => {
    const params: ActivityListParams = {
      page: 1,
      page_size: 40,
      sort_by: 'created_at',
      sort_dir: 'desc',
    };
    if (filters.search.trim()) params.search = filters.search.trim();
    if (filters.status) params.status = filters.status as ActivityListParams['status'];
    if (filters.dateFrom) params.date_from = `${filters.dateFrom}T00:00:00.000Z`;
    if (filters.dateTo) params.date_to = `${filters.dateTo}T23:59:59.999Z`;
    if (filters.entityId) params.entity_id = filters.entityId;
    return params;
  }, [filters]);

  const timelineQuery = useInfiniteQuery({
    queryKey: activityQueryKeys.timeline(apiFilters),
    queryFn: ({ pageParam = 1 }) =>
      activityQueries.timeline({ ...apiFilters, page: pageParam }).queryFn(),
    initialPageParam: 1,
    getNextPageParam: (lastPage) =>
      lastPage.page < lastPage.pages ? lastPage.page + 1 : undefined,
    enabled: canViewEnabled,
  });

  const liveItems = useMemo(
    () => timelineQuery.data?.pages.flatMap((page) => page.items) ?? [],
    [timelineQuery.data],
  );

  const merged = useMemo(
    () => mergeTimelineData(liveItems, fixture),
    [liveItems, fixture],
  );

  const filteredEvents = useMemo(
    () => filterEvents(merged.events, filters),
    [merged.events, filters],
  );

  const grouped = useMemo(
    () => groupEventsByDay(filteredEvents, locale),
    [filteredEvents, locale],
  );

  const entities = useMemo(
    () => filterEntities(merged.entities, filters.entityKindTab, entitySearch),
    [merged.entities, filters.entityKindTab, entitySearch],
  );

  const owners = useMemo(() => uniqueOwners(merged.events), [merged.events]);

  const entitySummary = useMemo(
    () => summarizeEntities(merged.entities),
    [merged.entities],
  );

  const selectedEvent =
    filteredEvents.find((e) => e.id === selectedEventId) ??
    merged.events.find((e) => e.id === selectedEventId) ??
    null;

  const detailQuery = useQuery({
    ...activityQueries.detail(selectedEventId ?? ''),
    enabled:
      canViewEnabled &&
      Boolean(selectedEventId) &&
      !merged.usingFixture &&
      Boolean(selectedEvent) &&
      selectedEvent?.source === 'live',
  });

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setFilters((prev) => ({ ...prev, search: searchDraft }));
    }, 220);
    return () => window.clearTimeout(timer);
  }, [searchDraft]);

  useEffect(() => {
    if (!selectedEventId && filteredEvents[0]) {
      setSelectedEventId(filteredEvents[0].id);
    } else if (
      selectedEventId &&
      filteredEvents.length > 0 &&
      !filteredEvents.some((e) => e.id === selectedEventId)
    ) {
      setSelectedEventId(filteredEvents[0]?.id ?? null);
    }
  }, [filteredEvents, selectedEventId]);

  const patchFilters = (patch: Partial<TimelineDsFilters>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
  };

  const resetFilters = () => {
    setFilters(EMPTY_TIMELINE_FILTERS);
    setSearchDraft('');
    setEntitySearch('');
  };

  const applyFilters = () => {
    setFilters((prev) => ({ ...prev, search: searchDraft }));
  };

  const jumpToToday = () => {
    const today = new Date();
    const iso = today.toISOString().slice(0, 10);
    patchFilters({ dateFrom: iso, dateTo: iso, entityId: null });
    todayRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const selectEvent = (event: TimelineEvent) => {
    setSelectedEventId(event.id);
    setDetailOpen(true);
  };

  const selectEntity = (entity: TimelineEntity) => {
    patchFilters({
      entityId: filters.entityId === entity.id ? null : entity.id,
    });
  };

  const openCreate = (type: CrmActivityType = 'note') => {
    setFormDefaultType(type);
    setFormOpen(true);
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

  if (timelineQuery.isError && !merged.usingFixture) {
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

  const loadingList = timelineQuery.isLoading && !merged.usingFixture;

  const enrichedSelected: TimelineEvent | null = selectedEvent
    ? detailQuery.data
      ? {
          ...selectedEvent,
          description:
            detailQuery.data.description ||
            detailQuery.data.summary ||
            selectedEvent.description,
          notes: detailQuery.data.comments?.[0]?.body ?? selectedEvent.notes,
          attachments:
            detailQuery.data.attachments?.map((a) => ({
              id: a.id,
              name: a.file_name,
              sizeLabel: a.file_size_bytes
                ? `${Math.max(1, Math.round(a.file_size_bytes / 1024))} KB`
                : '—',
              kind: 'other' as const,
            })) ?? selectedEvent.attachments,
        }
      : selectedEvent
    : null;

  return (
    <div className="tl-ds" data-testid="timeline-ds-workspace">
      <header className="tl-ds__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
        <div className="tl-ds__header-actions">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => router.push('/workspaces/crm/dashboard' as Route)}
            data-testid="timeline-ds-copilot"
          >
            <IhIcon name="sparkles" size={13} />
            {t('actions.copilot')}
          </Button>
          {canCreate ? (
            <Button
              type="button"
              variant="primary"
              size="sm"
              onClick={() => openCreate('note')}
              data-testid="timeline-ds-add"
            >
              <IhIcon name="plus" size={13} />
              {t('actions.addEvent')}
            </Button>
          ) : null}
        </div>
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
        <Select
          label={t('filters.status')}
          value={filters.status}
          onChange={(e) =>
            patchFilters({ status: e.target.value as TimelineEventStatus | '' })
          }
        >
          <option value="">{t('filters.allStatuses')}</option>
          {TIMELINE_STATUSES.map((status) => (
            <option key={status} value={status}>
              {t(`statuses.${status}`)}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.category')}
          value={filters.category}
          onChange={(e) =>
            patchFilters({ category: e.target.value as TimelineEventCategory | '' })
          }
        >
          <option value="">{t('filters.allCategories')}</option>
          {TIMELINE_CATEGORIES.map((cat) => (
            <option key={cat} value={cat}>
              {t(`categories.${cat}`)}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.owner')}
          value={filters.owner}
          onChange={(e) => patchFilters({ owner: e.target.value })}
        >
          <option value="">{t('filters.allOwners')}</option>
          {owners.map((owner) => (
            <option key={owner} value={owner}>
              {owner}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.entityType')}
          value={filters.entityType === 'all' ? '' : filters.entityType}
          onChange={(e) =>
            patchFilters({
              entityType: (e.target.value || 'all') as TimelineDsFilters['entityType'],
            })
          }
        >
          <option value="">{t('filters.allEntityTypes')}</option>
          {ENTITY_KIND_ORDER.filter((k) => k !== 'all' && k !== 'favorites').map((kind) => (
            <option key={kind} value={kind}>
              {t(`entities.${kind}`)}
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
          <Button type="button" variant="primary" size="sm" onClick={applyFilters}>
            {t('filters.apply')}
          </Button>
          <Button type="button" variant="secondary" size="sm" onClick={jumpToToday}>
            <IhIcon name="calendar" size={12} />
            {t('filters.today')}
          </Button>
          <Button type="button" variant="secondary" size="sm" onClick={resetFilters}>
            <IhIcon name="refresh" size={12} />
            {t('filters.reset')}
          </Button>
        </div>
      </section>

      <div className="tl-ds__workspace">
        {/* LEFT — Entities */}
        <section
          className="tl-ds__panel tl-ds__panel--entities"
          aria-label={t('entities.title')}
        >
          <div className="tl-ds__panel-head">
            <h2>
              <IhIcon name="users" size={14} />
              {t('entities.title')}
            </h2>
            <span className="tl-ds__panel-head-meta">
              {t('entities.count', { count: entities.length })}
            </span>
          </div>
          <div className="tl-ds__entity-search">
            <Input
              label={t('entities.search')}
              value={entitySearch}
              onChange={(e) => setEntitySearch(e.target.value)}
              placeholder={t('entities.searchPlaceholder')}
              data-testid="timeline-ds-entity-search"
            />
          </div>
          <div className="tl-ds__entity-tabs" role="tablist" aria-label={t('entities.tabsAria')}>
            {ENTITY_KIND_ORDER.map((tab) => (
              <button
                key={tab}
                type="button"
                role="tab"
                aria-selected={filters.entityKindTab === tab}
                className={`tl-ds__entity-tab${filters.entityKindTab === tab ? ' is-active' : ''}`}
                onClick={() =>
                  patchFilters({
                    entityKindTab: tab as TimelineEntityKind | 'all',
                    entityId: null,
                  })
                }
              >
                {t(`entities.${tab}`)}
              </button>
            ))}
          </div>
          <div className="tl-ds__entity-summary" aria-label={t('entities.summaryAria')}>
            <StatusChip tone="info">
              {t('entities.summaryTotal', { count: entitySummary.total })}
            </StatusChip>
            <StatusChip tone="success">
              {t('entities.summaryActive', { count: entitySummary.active })}
            </StatusChip>
            <StatusChip tone="default">
              {t('entities.summaryFavorites', { count: entitySummary.favorites })}
            </StatusChip>
          </div>
          <ul className="tl-ds__entity-list">
            {entities.length === 0 ? (
              <li>
                <div className="tl-ds__empty">
                  <strong>{t('entities.emptyTitle')}</strong>
                  <p>{t('entities.emptyDescription')}</p>
                </div>
              </li>
            ) : (
              entities.map((entity) => (
                <li key={entity.id}>
                  <button
                    type="button"
                    className={`tl-ds__entity${filters.entityId === entity.id ? ' is-selected' : ''}`}
                    onClick={() => selectEntity(entity)}
                  >
                    <Avatar initials={entity.initials} tone={entity.avatarTone} />
                    <div className="tl-ds__entity-main">
                      <span className="tl-ds__entity-name">{entity.name}</span>
                      <div className="tl-ds__entity-meta">
                        <StatusChip tone={entity.statusTone}>{entity.status}</StatusChip>
                        {entity.parent ? (
                          <span className="tl-ds__entity-parent">{entity.parent}</span>
                        ) : null}
                      </div>
                    </div>
                  </button>
                </li>
              ))
            )}
          </ul>
          <div className="tl-ds__panel-foot">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => router.push('/workspaces/crm/contacts/new' as Route)}
            >
              <IhIcon name="plus" size={12} />
              {t('entities.add')}
            </Button>
          </div>
        </section>

        {/* CENTER — Feed */}
        <section className="tl-ds__panel tl-ds__panel--feed" aria-label={t('feed.title')}>
          <div className="tl-ds__panel-head">
            <h2>
              <IhIcon name="activity" size={14} />
              {t('feed.title')}
            </h2>
            <div className="tl-ds__feed-controls">
              <span className="tl-ds__panel-head-meta">
                {t('feed.count', { count: filteredEvents.length })}
              </span>
              <Button type="button" variant="secondary" size="sm" onClick={jumpToToday}>
                {t('feed.backToToday')}
              </Button>
              <button
                type="button"
                className="tl-ds__icon-btn tl-ds__detail-toggle"
                aria-label={t('detail.open')}
                title={t('detail.open')}
                onClick={() => setDetailOpen(true)}
              >
                <IhIcon name="chevronRight" size={13} />
              </button>
            </div>
          </div>

          <div className="tl-ds__panel-body">
            {loadingList ? (
              <div className="tl-ds__skeleton" aria-hidden="true">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="tl-ds__skeleton-row" />
                ))}
              </div>
            ) : filteredEvents.length === 0 ? (
              <div className="tl-ds__empty" data-testid="timeline-ds-empty">
                <IhIcon name="empty" size={22} />
                <strong>{t('empty.title')}</strong>
                <p>{t('empty.description')}</p>
                <div className="tl-ds__empty-actions">
                  <Button type="button" variant="secondary" size="sm" onClick={resetFilters}>
                    {t('filters.reset')}
                  </Button>
                  {canCreate ? (
                    <Button type="button" variant="primary" size="sm" onClick={() => openCreate()}>
                      <IhIcon name="plus" size={12} />
                      {t('actions.addEvent')}
                    </Button>
                  ) : null}
                </div>
              </div>
            ) : (
              grouped.map((group) => (
                <section
                  key={group.key}
                  className="tl-ds__day"
                  ref={group.labelKey === 'today' ? todayRef : undefined}
                  aria-label={
                    group.labelKey === 'date'
                      ? group.dateLabel
                      : t(`feed.${group.labelKey}`)
                  }
                >
                  <div className={`tl-ds__day-label is-${group.labelKey}`}>
                    <StatusChip
                      tone={
                        group.labelKey === 'today'
                          ? 'info'
                          : group.labelKey === 'yesterday'
                            ? 'default'
                            : 'default'
                      }
                    >
                      {group.labelKey === 'date'
                        ? group.dateLabel
                        : `${t(`feed.${group.labelKey}`)} · ${group.dateLabel}`}
                    </StatusChip>
                  </div>
                  <div className="tl-ds__rail">
                    {group.events.map((event) => (
                      <button
                        key={event.id}
                        type="button"
                        className={`tl-ds__event${selectedEventId === event.id ? ' is-selected' : ''}`}
                        onClick={() => selectEvent(event)}
                        data-testid={`timeline-ds-event-${event.id}`}
                      >
                        <time
                          className="tl-ds__event-time"
                          dateTime={event.occurredAt}
                        >
                          {formatEventTime(event.occurredAt, locale)}
                        </time>
                        <span
                          className={`tl-ds__event-node is-${event.category}`}
                          aria-hidden="true"
                        >
                          <IhIcon name={CATEGORY_ICON[event.category]} size={12} />
                        </span>
                        <div className="tl-ds__event-body">
                          <div className="tl-ds__event-top">
                            <h3 className="tl-ds__event-title">{event.title}</h3>
                            <div className="tl-ds__event-side">
                              <span className="tl-ds__owner-chip">{event.owner}</span>
                              <StatusChip tone={CATEGORY_TONE[event.category]}>
                                {t(`categories.${event.category}`)}
                              </StatusChip>
                            </div>
                          </div>
                          <p className="tl-ds__event-desc">{event.description}</p>
                          <div className="tl-ds__event-foot">
                            <span className="tl-ds__event-entity">{event.entityName}</span>
                            <StatusChip tone={STATUS_TONE[event.status]}>
                              {t(`statuses.${event.status}`)}
                            </StatusChip>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </section>
              ))
            )}

            {!merged.usingFixture && timelineQuery.hasNextPage ? (
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

        {/* RIGHT — Detail (drawer on narrow) */}
        <div className={`tl-ds__drawer${detailOpen ? ' is-open' : ''}`}>
          <button
            type="button"
            className="tl-ds__drawer-backdrop"
            aria-label={t('detail.close')}
            onClick={() => setDetailOpen(false)}
          />
          <aside
            className="tl-ds__panel tl-ds__panel--detail"
            aria-label={t('detail.title')}
          >
            <div className="tl-ds__panel-head">
              <h2>
                <IhIcon name="documents" size={14} />
                {t('detail.title')}
              </h2>
              <button
                type="button"
                className="tl-ds__icon-btn tl-ds__detail-toggle"
                aria-label={t('detail.close')}
                onClick={() => setDetailOpen(false)}
              >
                <IhIcon name="chevronRight" size={13} />
              </button>
            </div>
            <EventDetailPanel
              event={enrichedSelected}
              onClose={detailOpen ? () => setDetailOpen(false) : undefined}
              onCreateFollowUp={() => openCreate('follow_up')}
              onCreateTask={() => openCreate('task')}
              onAddNote={() => openCreate('note')}
            />
          </aside>
        </div>
      </div>

      <ActivityFormModal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        defaultType={formDefaultType}
      />
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
