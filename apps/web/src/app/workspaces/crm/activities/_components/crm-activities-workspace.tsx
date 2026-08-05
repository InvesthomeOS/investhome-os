'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, Input, KpiCard, Select, StatusChip } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';

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
  const description = t(`rowDescriptions.${row.descriptionKey}`);

  return (
    <div className="crm-activities-ds__activity-cell">
      <ActivityTypeIcon type={row.type} />
      <div className="crm-activities-ds__activity-text">
        <strong>{t(`types.${row.titleKey}`)}</strong>
        <span className="crm-activities-ds__clamp-fade" title={description}>
          {description}
        </span>
      </div>
    </div>
  );
}

function AiSummaryCell({ summaryKey }: { summaryKey: string }) {
  const t = useTranslations('crm.activities');
  const [expanded, setExpanded] = useState(false);
  const summary = t(`aiSummaries.${summaryKey}`);
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
  preview,
  onOpenAi,
}: {
  preview: ActivityWorkspacePreview;
  /** Opens Dashboard Freeze AI drawer when provided by the shell. */
  onOpenAi?: (prompt?: string) => void;
}) {
  const t = useTranslations('crm.activities');
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

  const filteredActivities = useMemo(() => {
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
      if (filters.search) {
        const q = filters.search.trim().toLowerCase();
        const haystack = `${row.customer} ${row.customerDetail} ${row.project} ${row.salesRep}`.toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      return true;
    });
  }, [aiAction, filters, preview.activities]);

  const totalPages = Math.max(1, Math.ceil(preview.totalActivities / pageSize));
  const pageItems = filteredActivities.slice(0, Math.min(pageSize, filteredActivities.length));

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
          onChange={(e) => setFilters((prev) => ({ ...prev, customer: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          {preview.customers.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.salesRep')}
          value={filters.salesRep}
          onChange={(e) => setFilters((prev) => ({ ...prev, salesRep: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          {preview.salesReps.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.type')}
          value={filters.type}
          onChange={(e) => setFilters((prev) => ({ ...prev, type: e.target.value }))}
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
          onChange={(e) => setFilters((prev) => ({ ...prev, status: e.target.value }))}
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
          onChange={(e) => setFilters((prev) => ({ ...prev, priority: e.target.value }))}
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
          onChange={(e) => setFilters((prev) => ({ ...prev, date: e.target.value }))}
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
          onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value }))}
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
                      <strong title={row.customer}>{row.customer}</strong>
                      <span title={row.customerDetail}>{row.customerDetail}</span>
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
                      <AiSummaryCell summaryKey={row.aiSummaryKey} />
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
            <p>{t('pagination.total', { count: preview.totalActivities })}</p>
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
                <dd>{preview.daySummary.completed}</dd>
              </div>
              <div>
                <dt>{t('rail.pending')}</dt>
                <dd className="is-warning">{preview.daySummary.pending}</dd>
              </div>
              <div>
                <dt>{t('rail.overdue')}</dt>
                <dd className="is-danger">{preview.daySummary.overdue}</dd>
              </div>
            </dl>
            <p className="crm-activities-ds__assessment">
              {t(`rail.assessments.${preview.daySummary.assessmentKey}`)}
            </p>
            <Button variant="secondary" size="sm">
              {t('rail.viewDetailedSummary')}
            </Button>
          </section>

          <section className="crm-activities-ds__rail-card crm-activities-ds__rail-card--ai">
            <h3>{t('rail.aiRecommendations')}</h3>
            <ul className="crm-activities-ds__recs">
              {preview.aiRecommendations.map((item) => (
                <li key={item.id}>{t(`rail.recommendations.${item.bodyKey}`)}</li>
              ))}
            </ul>
          </section>

          <section className="crm-activities-ds__rail-card">
            <h3>{t('rail.upcomingMeetings')}</h3>
            <ul className="crm-activities-ds__list">
              {preview.upcomingMeetings.map((item) => (
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
          </section>

          <section className="crm-activities-ds__rail-card crm-activities-ds__rail-card--warn">
            <h3>{t('rail.overdueFollowUps')}</h3>
            <ul className="crm-activities-ds__list">
              {preview.overdueFollowUps.map((item) => (
                <li key={item.id}>
                  <span className="crm-activities-ds__list-icon is-warn" aria-hidden="true">
                    <IhIcon name="alert" size={12} />
                  </span>
                  <div>
                    <strong title={item.customer}>{item.customer}</strong>
                    <span>{t('rail.daysOverdue', { count: item.daysOverdue })}</span>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="crm-activities-ds__rail-card">
            <h3>{t('rail.recentNotes')}</h3>
            <ul className="crm-activities-ds__list">
              {preview.recentNotes.map((item) => (
                <li key={item.id}>
                  <span className="crm-activities-ds__list-icon" aria-hidden="true">
                    <IhIcon name="documents" size={12} />
                  </span>
                  <div>
                    <strong title={item.author}>{item.author}</strong>
                    <span title={t(`rail.notes.${item.bodyKey}`)}>
                      {t(`rail.notes.${item.bodyKey}`)}
                    </span>
                    <time>{t(`rail.noteTimes.${item.timeKey}`)}</time>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        </aside>
      </div>
    </div>
  );
}
