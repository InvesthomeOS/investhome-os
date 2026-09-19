'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, Input, KpiCard, LoadingState, Select, StatusChip } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';
import { fetchUsers } from '@/lib/api/auth';
import { fetchContacts } from '@/workspaces/crm/api/contacts';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { activityQueries } from '@/workspaces/crm/hooks/use-activities';
import { buildActivitiesPreview, matchesDateFilter } from '@/workspaces/crm/lib/map-live-workspace';
import type { ActivityListParams, CrmActivityStatus, CrmActivityType } from '@/workspaces/crm/types/activities';

import {
  ACTIVITY_PRIORITY_ORDER,
  ACTIVITY_STATUS_ORDER,
  ACTIVITY_TYPE_ICONS,
  ACTIVITY_TYPE_ORDER,
  type ActivityAiActionKey,
  type ActivityKpiKey,
  type ActivityPriorityKey,
  type ActivityRow,
  type ActivityStatusKey,
  type ActivityTypeKey,
  type ActivityWorkspacePreview,
} from '../activities-model';

const AI_ACTIONS: ReadonlyArray<{ key: ActivityAiActionKey; icon: IhIconName }> = [
  { key: 'summarizeToday', icon: 'sparkles' },
  { key: 'showFollowUps', icon: 'clock' },
  { key: 'missedCustomers', icon: 'alert' },
  { key: 'aiSummary', icon: 'activity' },
];

const KPI_ICONS: Record<ActivityKpiKey, IhIconName> = {
  today: 'calendar',
  completed: 'check',
  pending: 'clock',
  overdue: 'alert',
};

const STATUS_TONE: Record<ActivityStatusKey, 'success' | 'warning' | 'info' | 'default' | 'danger'> = {
  completed: 'success',
  pending: 'warning',
  cancelled: 'default',
  inProgress: 'info',
};

const PRIORITY_TONE: Record<ActivityPriorityKey, 'success' | 'warning' | 'info' | 'default' | 'danger'> = {
  low: 'info',
  medium: 'warning',
  high: 'danger',
  critical: 'danger',
};

const UI_TYPE_TO_API: Record<ActivityTypeKey, CrmActivityType[]> = {
  phone: ['phone_call'],
  whatsapp: ['whatsapp'],
  email: ['email'],
  meeting: ['meeting', 'investor_meeting', 'construction_meeting', 'site_visit', 'property_tour'],
  note: ['note', 'comment', 'internal_discussion'],
  documentShared: ['document_sent', 'document_received'],
  missedCall: ['other'],
  sms: ['sms'],
  videoCall: ['zoom_meeting', 'teams_meeting'],
};

function dateFilterRange(value: string): { date_from?: string; date_to?: string } {
  if (!value) return {};
  const now = new Date();
  const end = now.toISOString();
  if (value === 'today') {
    const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    return { date_from: start.toISOString(), date_to: end };
  }
  const days = value === '7d' ? 7 : value === '30d' ? 30 : value === '90d' ? 90 : 0;
  if (!days) return {};
  const start = new Date(now.getTime() - days * 86_400_000);
  return { date_from: start.toISOString(), date_to: end };
}

function mapUiStatus(value: string): { status?: CrmActivityStatus; pending?: boolean; completed?: boolean } {
  if (value === 'completed') return { status: 'completed' };
  if (value === 'cancelled') return { status: 'cancelled' };
  if (value === 'inProgress') return { status: 'in_progress' };
  if (value === 'pending') return { pending: true };
  return {};
}

type FilterKey =
  | 'customer'
  | 'salesRep'
  | 'type'
  | 'status'
  | 'priority'
  | 'date'
  | 'search';

function ActivityTypeIcon({ type }: { type: ActivityTypeKey }) {
  return (
    <span className={`crm-activities-ds__type-icon is-${type}`} aria-hidden="true">
      <IhIcon name={ACTIVITY_TYPE_ICONS[type]} size={15} />
    </span>
  );
}

function ActivityCell({ row }: { row: ActivityRow }) {
  const t = useTranslations('crm.activities');
  const description = row.description ?? t(`rowDescriptions.${row.descriptionKey}`);
  const title = row.title ?? t(`types.${row.titleKey}`);

  return (
    <div className="crm-activities-ds__activity-cell">
      <ActivityTypeIcon type={row.type} />
      <div className="crm-activities-ds__activity-text">
        <strong>{title}</strong>
        <span className="crm-activities-ds__clamp-fade" title={description}>
          {description}
        </span>
      </div>
    </div>
  );
}

function AiSummaryCell({ summaryKey, summaryText }: { summaryKey: string; summaryText?: string }) {
  const t = useTranslations('crm.activities');
  const [expanded, setExpanded] = useState(false);
  const summary = summaryText ?? t(`aiSummaries.${summaryKey}`);
  const needsToggle = summary.length > 48;

  return (
    <div className="crm-activities-ds__ai-summary">
      <p
        className={
          expanded
            ? 'crm-activities-ds__ai-cell is-expanded'
            : 'crm-activities-ds__ai-cell crm-activities-ds__clamp-fade'
        }
        title={summary}
      >
        {summary}
      </p>
      {needsToggle ? (
        <button
          type="button"
          className="crm-activities-ds__ai-more"
          aria-expanded={expanded}
          onClick={(e) => {
            e.stopPropagation();
            setExpanded((v) => !v);
          }}
        >
          {expanded ? t('actions.collapse') : t('actions.expand')}
          <IhIcon name="chevronDown" size={11} />
        </button>
      ) : null}
    </div>
  );
}

export function CrmActivitiesWorkspace({
  preview: previewProp,
  onOpenAi,
}: {
  preview?: ActivityWorkspacePreview;
  /** Opens Dashboard Freeze AI drawer when provided by the shell. */
  onOpenAi?: (prompt?: string) => void;
}) {
  const t = useTranslations('crm.activities');
  const { openContact } = useContactCard();
  const [aiAction, setAiAction] = useState<ActivityAiActionKey>('summarizeToday');
  const [filters, setFilters] = useState<Record<FilterKey, string>>({
    customer: '',
    salesRep: '',
    type: '',
    status: '',
    priority: '',
    date: '',
    search: '',
  });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const patchFilters = (patch: Partial<Record<FilterKey, string>>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
    setPage(1);
  };

  const listParams = useMemo<ActivityListParams>(() => {
    const statusBits = mapUiStatus(filters.status);
    return {
      page,
      page_size: pageSize,
      sort_by: 'created_at',
      sort_dir: 'desc',
      search: filters.search.trim() || undefined,
      entity_type: filters.customer ? 'contact' : undefined,
      entity_id: filters.customer || undefined,
      activity_types: filters.type ? UI_TYPE_TO_API[filters.type as ActivityTypeKey] : undefined,
      priority: (filters.priority as ActivityPriorityKey) || undefined,
      responsible_user_id: filters.salesRep || undefined,
      ...dateFilterRange(filters.date),
      ...statusBits,
    };
  }, [filters, page, pageSize]);

  const liveQuery = useQuery({
    ...activityQueries.list(listParams),
    enabled: !previewProp,
  });
  const widgetsQuery = useQuery({
    ...activityQueries.widgets(),
    enabled: !previewProp,
  });
  const usersQuery = useQuery({
    queryKey: ['users', 'activity-filter'],
    queryFn: () => fetchUsers({ status: 'active' }),
    enabled: !previewProp,
  });
  const contactsQuery = useQuery({
    queryKey: ['crm', 'contacts', 'activity-filter'],
    queryFn: () => fetchContacts({ page: 1, page_size: 100, sort_by: 'last_contact_at', sort_dir: 'desc' }),
    enabled: !previewProp,
  });
  const preview = previewProp ?? buildActivitiesPreview(liveQuery.data?.items ?? [], liveQuery.data?.total ?? 0);

  const filteredActivities = useMemo(() => {
    if (!previewProp) return preview.activities;
    let items = [...preview.activities];
    if (aiAction === 'showFollowUps') {
      items = items.filter((a) => a.status === 'pending' || a.priority === 'critical');
    } else if (aiAction === 'missedCustomers') {
      items = items.filter((a) => a.type === 'missedCall' || a.status === 'pending');
    }
    return items.filter((row) => {
      if (filters.customer && row.customer !== filters.customer) return false;
      if (filters.salesRep && row.salesRep !== filters.salesRep) return false;
      if (filters.type && row.type !== filters.type) return false;
      if (filters.status && row.status !== filters.status) return false;
      if (filters.priority && row.priority !== filters.priority) return false;
      if (filters.date && !matchesDateFilter(row.occurredAt, filters.date)) return false;
      if (filters.search) {
        const q = filters.search.trim().toLowerCase();
        const haystack = `${row.title ?? ''} ${row.description ?? ''} ${row.aiSummary ?? ''} ${row.customer} ${row.customerDetail} ${row.project} ${row.salesRep}`.toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      return true;
    });
  }, [aiAction, filters, preview.activities, previewProp]);

  const totalActivities = previewProp ? filteredActivities.length : preview.totalActivities;
  const totalPages = Math.max(1, Math.ceil(totalActivities / pageSize));
  const pageItems = previewProp
    ? filteredActivities.slice((page - 1) * pageSize, page * pageSize)
    : filteredActivities;

  const widgets = widgetsQuery.data;
  const dayCompleted = widgets?.recent_activities.filter((item) => item.status === 'completed').length ?? preview.daySummary.completed;
  const dayPending = widgets?.todays_tasks.length ?? preview.daySummary.pending;
  const dayOverdue = widgets?.overdue_tasks.length ?? preview.daySummary.overdue;
  const upcomingMeetings = widgets
    ? widgets.upcoming_meetings.map((item) => ({
        id: item.id,
        title: item.title,
        customer: item.entity_name || '—',
        time: item.start_date || item.due_date || item.created_at,
      }))
    : preview.upcomingMeetings;
  const overdueFollowUps = widgets
    ? widgets.follow_ups_due.map((item) => ({
        id: item.id,
        customer: item.entity_name || '—',
        daysOverdue: 0,
      }))
    : preview.overdueFollowUps;
  const recentNotes = widgets
    ? widgets.recent_notes.map((item) => ({
        id: item.id,
        author: item.created_by_name || item.assigned_user_name || '—',
        bodyKey: '',
        body: item.summary || item.title,
        timeKey: '',
        time: item.created_at,
      }))
    : preview.recentNotes;

  const clearFilters = () => {
    setFilters({
      customer: '',
      salesRep: '',
      type: '',
      status: '',
      priority: '',
      date: '',
      search: '',
    });
    setPage(1);
  };

  if (!previewProp && liveQuery.isLoading) {
    return <LoadingState />;
  }

  return (
    <div className="crm-activities-ds" data-testid="crm-activities-workspace">
      <header className="crm-activities-ds__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
      </header>

      <section className="crm-activities-ds__kpi-row" aria-label={t('kpis.aria')}>
        {preview.kpis.map((kpi) => (
          <KpiCard
            key={kpi.key}
            className="crm-activities-ds__kpi"
            label={t(`kpis.${kpi.key}`)}
            value={kpi.value}
            hint={t(`kpis.hints.${kpi.hintKey}`)}
            delta={`${kpi.delta} ${t('kpis.thisMonth')}`}
            deltaTone={kpi.deltaTone}
            tone={kpi.key === 'overdue' ? 'warning' : 'default'}
            icon={<IhIcon name={KPI_ICONS[kpi.key]} size={18} />}
          />
        ))}
      </section>

      <nav className="screenshot-dashboard__intro-ai crm-activities-ds__ai" aria-label={t('ai.aria')}>
        {AI_ACTIONS.map((action) => (
          <button
            key={action.key}
            type="button"
            className={aiAction === action.key ? 'is-featured' : undefined}
            onClick={() => setAiAction(action.key)}
          >
            <span className="crm-activities-ds__ai-icon" aria-hidden="true">
              <IhIcon name={action.icon} size={16} />
            </span>
            <span>{t(`ai.actions.${action.key}`)}</span>
          </button>
        ))}
        <button
          type="button"
          className="screenshot-dashboard__intro-ai-primary"
          onClick={() => onOpenAi?.(t('ai.openPrompt'))}
        >
          <IhIcon name="sparkles" size={15} />
          {t('ai.title')}
        </button>
      </nav>

      <section className="crm-activities-ds__filters" aria-label={t('filters.aria')}>
        <Select
          label={t('filters.customer')}
          value={filters.customer}
          onChange={(e) => patchFilters({ customer: e.target.value })}
        >
          <option value="">{t('filters.any')}</option>
          {previewProp
            ? preview.customers.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))
            : (contactsQuery.data?.items ?? []).map((contact) => (
                <option key={contact.id} value={contact.id}>
                  {contact.display_name}
                </option>
              ))}
        </Select>
        <Select
          label={t('filters.salesRep')}
          value={filters.salesRep}
          onChange={(e) => patchFilters({ salesRep: e.target.value })}
        >
          <option value="">{t('filters.any')}</option>
          {previewProp
            ? preview.salesReps.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))
            : (usersQuery.data?.items ?? []).map((user) => (
                <option key={user.id} value={user.id}>
                  {user.full_name}
                </option>
              ))}
        </Select>
        <Select
          label={t('filters.type')}
          value={filters.type}
          onChange={(e) => patchFilters({ type: e.target.value })}
        >
          <option value="">{t('filters.any')}</option>
          {ACTIVITY_TYPE_ORDER.map((type) => (
            <option key={type} value={type}>
              {t(`types.${type}`)}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.status')}
          value={filters.status}
          onChange={(e) => patchFilters({ status: e.target.value })}
        >
          <option value="">{t('filters.any')}</option>
          {ACTIVITY_STATUS_ORDER.map((status) => (
            <option key={status} value={status}>
              {t(`status.${status}`)}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.priority')}
          value={filters.priority}
          onChange={(e) => patchFilters({ priority: e.target.value })}
        >
          <option value="">{t('filters.any')}</option>
          {ACTIVITY_PRIORITY_ORDER.map((priority) => (
            <option key={priority} value={priority}>
              {t(`priority.${priority}`)}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.date')}
          value={filters.date}
          onChange={(e) => patchFilters({ date: e.target.value })}
        >
          <option value="">{t('filters.any')}</option>
          <option value="today">{t('filters.dateRanges.today')}</option>
          <option value="7d">{t('filters.dateRanges.last7')}</option>
          <option value="30d">{t('filters.dateRanges.last30')}</option>
          <option value="90d">{t('filters.dateRanges.last90')}</option>
        </Select>
        <Input
          label={t('filters.search')}
          value={filters.search}
          onChange={(e) => patchFilters({ search: e.target.value })}
          placeholder={t('filters.searchPlaceholder')}
        />
        <Button variant="secondary" size="sm" onClick={clearFilters}>
          <IhIcon name="refresh" size={13} />
          {t('filters.clear')}
        </Button>
      </section>

      <div className="crm-activities-ds__layout">
        <div className="crm-activities-ds__main">
          <div className="crm-activities-ds__table-wrap" role="region" aria-label={t('table.aria')}>
            <table className="crm-activities-ds__table">
              <thead>
                <tr>
                  <th scope="col">{t('table.activity')}</th>
                  <th scope="col">{t('table.customer')}</th>
                  <th scope="col">{t('table.project')}</th>
                  <th scope="col">{t('table.salesRep')}</th>
                  <th scope="col">{t('table.dateTime')}</th>
                  <th scope="col">{t('table.status')}</th>
                  <th scope="col">{t('table.priority')}</th>
                  <th scope="col">{t('table.aiSummary')}</th>
                  <th scope="col">{t('table.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {pageItems.map((row) => (
                  <tr
                    key={row.id}
                    className={`crm-activities-ds__row is-${row.status}`}
                    data-testid={`activity-row-${row.id}`}
                  >
                    <td>
                      <ActivityCell row={row} />
                    </td>
                    <td>
                      <button
                        type="button"
                        className="crm-activities-ds__contact-btn"
                        onClick={() => row.customerId && openContact(row.customerId)}
                        disabled={!row.customerId}
                      >
                        <strong title={row.customer}>{row.customer}</strong>
                        <span title={row.customerDetail}>{row.customerDetail}</span>
                      </button>
                    </td>
                    <td>
                      <span className={`crm-activities-ds__project is-${row.projectTone}`}>
                        {row.project}
                      </span>
                    </td>
                    <td>
                      <div className="crm-activities-ds__rep">
                        <span className="crm-activities-ds__avatar" aria-hidden="true">
                          {row.salesRepInitials}
                        </span>
                        <span title={row.salesRep}>{row.salesRep}</span>
                      </div>
                    </td>
                    <td>
                      <time dateTime={row.dateTime}>{row.dateTime}</time>
                    </td>
                    <td>
                      <StatusChip tone={STATUS_TONE[row.status]} className="crm-activities-ds__badge">
                        {t(`status.${row.status}`)}
                      </StatusChip>
                    </td>
                    <td>
                      <StatusChip
                        tone={PRIORITY_TONE[row.priority]}
                        className={
                          row.priority === 'critical'
                            ? 'crm-activities-ds__badge crm-activities-ds__priority--critical'
                            : 'crm-activities-ds__badge'
                        }
                      >
                        {t(`priority.${row.priority}`)}
                      </StatusChip>
                    </td>
                    <td>
                      <AiSummaryCell summaryKey={row.aiSummaryKey} summaryText={row.aiSummary} />
                    </td>
                    <td>
                      <div className="crm-activities-ds__row-actions">
                        <button
                          type="button"
                          className="crm-activities-ds__icon-action"
                          aria-label={t('actions.detail')}
                          title={t('actions.detail')}
                        >
                          <IhIcon name="search" size={14} />
                        </button>
                        <button
                          type="button"
                          className="crm-activities-ds__icon-action"
                          aria-label={t('actions.edit')}
                          title={t('actions.edit')}
                        >
                          <IhIcon name="settings" size={14} />
                        </button>
                        <button
                          type="button"
                          className="crm-activities-ds__icon-action"
                          aria-label={t('actions.more')}
                          title={t('actions.more')}
                        >
                          <IhIcon name="chevronDown" size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <footer className="crm-activities-ds__pagination" aria-label={t('pagination.aria')}>
            <p>{t('pagination.total', { count: totalActivities })}</p>
            <div className="crm-activities-ds__page-numbers" role="navigation">
              {Array.from({ length: Math.min(totalPages, 3) }, (_, i) => i + 1).map((n) => (
                <button
                  key={n}
                  type="button"
                  className={page === n ? 'is-active' : undefined}
                  onClick={() => setPage(n)}
                  aria-current={page === n ? 'page' : undefined}
                >
                  {n}
                </button>
              ))}
              {totalPages > 4 ? <span className="crm-activities-ds__page-ellipsis">…</span> : null}
              {totalPages > 3 ? (
                <button
                  type="button"
                  className={page === totalPages ? 'is-active' : undefined}
                  onClick={() => setPage(totalPages)}
                  aria-current={page === totalPages ? 'page' : undefined}
                >
                  {totalPages}
                </button>
              ) : null}
            </div>
            <label className="ih-field crm-activities-ds__page-size">
              <span className="ih-field__label">{t('pagination.perPage')}</span>
              <select
                className="ih-select"
                value={String(pageSize)}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(1);
                }}
                aria-label={t('pagination.perPage')}
              >
                <option value="10">10 / {t('pagination.pageUnit')}</option>
                <option value="20">20 / {t('pagination.pageUnit')}</option>
                <option value="40">40 / {t('pagination.pageUnit')}</option>
              </select>
            </label>
          </footer>
        </div>

        <aside className="crm-activities-ds__rail" aria-label={t('rail.aria')}>
          <section className="crm-activities-ds__rail-card crm-activities-ds__rail-card--ai">
            <h3>{t('rail.daySummary')}</h3>
            <dl className="crm-activities-ds__day-counts">
              <div>
                <dt>{t('rail.completed')}</dt>
                <dd>{dayCompleted}</dd>
              </div>
              <div>
                <dt>{t('rail.pending')}</dt>
                <dd className="is-warning">{dayPending}</dd>
              </div>
              <div>
                <dt>{t('rail.overdue')}</dt>
                <dd className="is-danger">{dayOverdue}</dd>
              </div>
            </dl>
            {previewProp ? (
              <p className="crm-activities-ds__assessment">
                {t(`rail.assessments.${preview.daySummary.assessmentKey}`)}
              </p>
            ) : null}
          </section>

          {previewProp ? (
            <section className="crm-activities-ds__rail-card crm-activities-ds__rail-card--ai">
              <h3>{t('rail.aiRecommendations')}</h3>
              <ul className="crm-activities-ds__recs">
                {preview.aiRecommendations.map((item) => (
                  <li key={item.id}>{t(`rail.recommendations.${item.bodyKey}`)}</li>
                ))}
              </ul>
            </section>
          ) : widgets?.overdue_tasks.length ? (
            <section className="crm-activities-ds__rail-card crm-activities-ds__rail-card--ai">
              <h3>{t('rail.aiRecommendations')}</h3>
              <ul className="crm-activities-ds__recs">
                {widgets.overdue_tasks.slice(0, 4).map((item) => (
                  <li key={item.id}>{item.title}</li>
                ))}
              </ul>
            </section>
          ) : null}

          <section className="crm-activities-ds__rail-card">
            <h3>{t('rail.upcomingMeetings')}</h3>
            {upcomingMeetings.length ? (
              <ul className="crm-activities-ds__list">
                {upcomingMeetings.map((item) => (
                  <li key={item.id}>
                    <span className="crm-activities-ds__list-icon" aria-hidden="true">
                      <IhIcon name="meeting" size={12} />
                    </span>
                    <div>
                      <strong title={item.title}>{item.title}</strong>
                      <span>
                        {item.customer} · {item.time}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="crm-activities-ds__assessment">—</p>
            )}
          </section>

          <section className="crm-activities-ds__rail-card crm-activities-ds__rail-card--warn">
            <h3>{t('rail.overdueFollowUps')}</h3>
            {overdueFollowUps.length ? (
              <ul className="crm-activities-ds__list">
                {overdueFollowUps.map((item) => (
                  <li key={item.id}>
                    <span className="crm-activities-ds__list-icon is-warn" aria-hidden="true">
                      <IhIcon name="alert" size={12} />
                    </span>
                    <div>
                      <strong title={item.customer}>{item.customer}</strong>
                      {item.daysOverdue ? (
                        <span>{t('rail.daysOverdue', { count: item.daysOverdue })}</span>
                      ) : (
                        <span>{item.customer}</span>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="crm-activities-ds__assessment">—</p>
            )}
          </section>

          <section className="crm-activities-ds__rail-card">
            <h3>{t('rail.recentNotes')}</h3>
            {recentNotes.length ? (
              <ul className="crm-activities-ds__list">
                {recentNotes.map((item) => (
                  <li key={item.id}>
                    <span className="crm-activities-ds__list-icon" aria-hidden="true">
                      <IhIcon name="documents" size={12} />
                    </span>
                    <div>
                      <strong title={item.author}>{item.author}</strong>
                      <span title={item.body ?? (item.bodyKey ? t(`rail.notes.${item.bodyKey}`) : '')}>
                        {item.body ?? (item.bodyKey ? t(`rail.notes.${item.bodyKey}`) : '')}
                      </span>
                      <time>
                        {item.time ?? (item.timeKey ? t(`rail.noteTimes.${item.timeKey}`) : '')}
                      </time>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="crm-activities-ds__assessment">—</p>
            )}
          </section>
        </aside>
      </div>
    </div>
  );
}
