'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import {
  EMPTY_ACTIVITY_FILTERS,
  activityRecordHref,
  fetchActivities,
  fetchActivityDetail,
  formatActivityDate,
  metadataForI18n,
  type ActivityFilters,
  type ActivityLogEntry,
} from '@/lib/api/activity';
import { useActivityLabels } from '@/lib/i18n/activity-labels';

type ViewMode = 'timeline' | 'table';
type LoadState = 'idle' | 'loading' | 'error' | 'success';

export function ActivityWorkspace() {
  const t = useTranslations('activity');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const {
    getActionLabel,
    getEntityTypeLabel,
    getSourceLabel,
    getDescription,
    actionOptions,
    entityTypeOptions,
    sourceOptions,
  } = useActivityLabels();

  const [filters, setFilters] = useState<ActivityFilters>(EMPTY_ACTIVITY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<ActivityFilters>(EMPTY_ACTIVITY_FILTERS);
  const [viewMode, setViewMode] = useState<ViewMode>('timeline');
  const [items, setItems] = useState<ActivityLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(0);
  const [loadState, setLoadState] = useState<LoadState>('loading');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ActivityLogEntry | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const loadActivities = useCallback(async (nextFilters: ActivityFilters) => {
    setLoadState('loading');
    try {
      const response = await fetchActivities(nextFilters);
      setItems(response.items);
      setTotal(response.total);
      setPages(response.pages);
      setLoadState('success');
    } catch {
      setItems([]);
      setTotal(0);
      setPages(0);
      setLoadState('error');
    }
  }, []);

  useEffect(() => {
    void loadActivities(appliedFilters);
  }, [appliedFilters, loadActivities]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    setDetailLoading(true);
    void fetchActivityDetail(selectedId)
      .then(setDetail)
      .catch(() => setDetail(null))
      .finally(() => setDetailLoading(false));
  }, [selectedId]);

  const handleApplyFilters = () => {
    setAppliedFilters({ ...filters, page: 1 });
  };

  const handleResetFilters = () => {
    setFilters(EMPTY_ACTIVITY_FILTERS);
    setAppliedFilters(EMPTY_ACTIVITY_FILTERS);
  };

  const handlePageChange = (page: number) => {
    setAppliedFilters((current) => ({ ...current, page }));
  };

  const renderSummary = (item: ActivityLogEntry) =>
    getDescription(item.description_key, metadataForI18n(item.metadata));

  return (
    <main className="dashboard__main">
      <header className="dashboard__header">
        <p className="dashboard__eyebrow">{tCommon('appName')}</p>
        <h1>{t('title')}</h1>
        <p className="dashboard__subtitle">{t('subtitle')}</p>
      </header>

      <section className="dashboard__panel leads__panel">
        <div className="activity__toolbar">
          <div className="activity__view-toggle" role="group" aria-label={t('viewMode.label')}>
            <button
              type="button"
              className={`leads__button${viewMode === 'timeline' ? ' leads__button--secondary' : ' leads__button--ghost'}`}
              onClick={() => setViewMode('timeline')}
            >
              {t('viewMode.timeline')}
            </button>
            <button
              type="button"
              className={`leads__button${viewMode === 'table' ? ' leads__button--secondary' : ' leads__button--ghost'}`}
              onClick={() => setViewMode('table')}
            >
              {t('viewMode.table')}
            </button>
          </div>
          <span className="activity__count">{t('resultsCount', { count: total })}</span>
        </div>

        <form
          className="leads__filters"
          onSubmit={(event) => {
            event.preventDefault();
            handleApplyFilters();
          }}
        >
          <label>
            {t('filters.search')}
            <input
              type="search"
              value={filters.search}
              onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))}
              placeholder={t('filters.searchPlaceholder')}
            />
          </label>
          <label>
            {t('filters.dateFrom')}
            <input
              type="date"
              value={filters.date_from}
              onChange={(event) => setFilters((current) => ({ ...current, date_from: event.target.value }))}
            />
          </label>
          <label>
            {t('filters.dateTo')}
            <input
              type="date"
              value={filters.date_to}
              onChange={(event) => setFilters((current) => ({ ...current, date_to: event.target.value }))}
            />
          </label>
          <label>
            {t('filters.entityType')}
            <select
              value={filters.entity_type}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  entity_type: event.target.value as ActivityFilters['entity_type'],
                }))
              }
            >
              <option value="">{t('filters.all')}</option>
              {entityTypeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t('filters.action')}
            <select
              value={filters.action}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  action: event.target.value as ActivityFilters['action'],
                }))
              }
            >
              <option value="">{t('filters.all')}</option>
              {actionOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t('filters.source')}
            <select
              value={filters.source}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  source: event.target.value as ActivityFilters['source'],
                }))
              }
            >
              <option value="">{t('filters.all')}</option>
              {sourceOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <div className="leads__filter-actions">
            <button type="submit" className="leads__primary-button">
              {tCommon('apply')}
            </button>
            <button type="button" className="leads__button leads__button--secondary" onClick={handleResetFilters}>
              {tCommon('reset')}
            </button>
          </div>
        </form>

        {loadState === 'loading' && <p className="leads__state">{tCommon('loading')}</p>}
        {loadState === 'error' && (
          <div className="leads__state leads__state--error">
            <p>{t('loadError')}</p>
            <button
              type="button"
              className="leads__button leads__button--secondary"
              onClick={() => void loadActivities(appliedFilters)}
            >
              {tCommon('retry')}
            </button>
          </div>
        )}

        {loadState === 'success' && items.length === 0 && (
          <p className="leads__state">{t('empty')}</p>
        )}

        {loadState === 'success' && items.length > 0 && viewMode === 'timeline' && (
          <ol className="activity-timeline__list activity-timeline__list--page">
            {items.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  className="activity-timeline__card"
                  onClick={() => setSelectedId(item.id)}
                >
                  <time dateTime={item.created_at}>{formatActivityDate(item.created_at, locale)}</time>
                  <strong>{item.actor_name ?? t('systemActor')}</strong>
                  <p>{renderSummary(item)}</p>
                  <span>{getEntityTypeLabel(item.entity_type)}</span>
                </button>
              </li>
            ))}
          </ol>
        )}

        {loadState === 'success' && items.length > 0 && viewMode === 'table' && (
          <div className="leads__table-wrap">
            <table className="leads__table">
              <thead>
                <tr>
                  <th>{t('columns.dateTime')}</th>
                  <th>{t('columns.actor')}</th>
                  <th>{t('columns.action')}</th>
                  <th>{t('columns.entityType')}</th>
                  <th>{t('columns.record')}</th>
                  <th>{t('columns.source')}</th>
                  <th>{t('columns.summary')}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>{formatActivityDate(item.created_at, locale)}</td>
                    <td>{item.actor_name ?? t('systemActor')}</td>
                    <td>{getActionLabel(item.action)}</td>
                    <td>{getEntityTypeLabel(item.entity_type)}</td>
                    <td>{item.entity_label ?? tCommon('noValue')}</td>
                    <td>{getSourceLabel(item.source)}</td>
                    <td>
                      <button type="button" className="activity__link-button" onClick={() => setSelectedId(item.id)}>
                        {renderSummary(item)}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {loadState === 'success' && pages > 1 && (
          <div className="leads__pagination">
            <button
              type="button"
              className="leads__button leads__button--secondary"
              disabled={appliedFilters.page <= 1}
              onClick={() => handlePageChange(appliedFilters.page - 1)}
            >
              {t('pagination.previous')}
            </button>
            <span>{t('pagination.pageOf', { page: appliedFilters.page, pages })}</span>
            <button
              type="button"
              className="leads__button leads__button--secondary"
              disabled={appliedFilters.page >= pages}
              onClick={() => handlePageChange(appliedFilters.page + 1)}
            >
              {t('pagination.next')}
            </button>
          </div>
        )}
      </section>

      {selectedId && (
        <div className="leads-drawer" role="presentation" onClick={() => setSelectedId(null)}>
          <aside
            className="leads-drawer__panel leads-drawer__panel--wide"
            role="dialog"
            aria-modal="true"
            aria-labelledby="activity-detail-title"
            onClick={(event) => event.stopPropagation()}
          >
            <header className="leads-drawer__header">
              <div>
                <p className="dashboard__eyebrow">{t('detail.eyebrow')}</p>
                <h2 id="activity-detail-title">{t('detail.title')}</h2>
              </div>
              <button type="button" className="leads__button leads__button--ghost" onClick={() => setSelectedId(null)}>
                {tCommon('close')}
              </button>
            </header>

            {detailLoading && <p className="leads__state">{tCommon('loading')}</p>}
            {!detailLoading && !detail && <p className="leads__state">{t('detail.notFound')}</p>}
            {!detailLoading && detail && (
              <>
                <dl className="leads-drawer__grid">
                  <div>
                    <dt>{t('columns.dateTime')}</dt>
                    <dd>{formatActivityDate(detail.created_at, locale)}</dd>
                  </div>
                  <div>
                    <dt>{t('columns.actor')}</dt>
                    <dd>{detail.actor_name ?? t('systemActor')}</dd>
                  </div>
                  <div>
                    <dt>{t('columns.action')}</dt>
                    <dd>{getActionLabel(detail.action)}</dd>
                  </div>
                  <div>
                    <dt>{t('columns.source')}</dt>
                    <dd>{getSourceLabel(detail.source)}</dd>
                  </div>
                  <div>
                    <dt>{t('columns.entityType')}</dt>
                    <dd>{getEntityTypeLabel(detail.entity_type)}</dd>
                  </div>
                  <div>
                    <dt>{t('columns.record')}</dt>
                    <dd>{detail.entity_label ?? tCommon('noValue')}</dd>
                  </div>
                  {detail.request_id && (
                    <div>
                      <dt>{t('detail.requestId')}</dt>
                      <dd>{detail.request_id}</dd>
                    </div>
                  )}
                </dl>

                <div className="leads-drawer__notes">
                  <h3>{t('columns.summary')}</h3>
                  <p>{renderSummary(detail)}</p>
                </div>

                {detail.changed_fields && detail.changed_fields.length > 0 && (
                  <div className="activity__changes">
                    <h3>{t('detail.changedFields')}</h3>
                    <ul>
                      {detail.changed_fields.map((field) => (
                        <li key={field}>
                          <strong>{field}</strong>
                          <span>
                            {String(detail.previous_values?.[field] ?? tCommon('noValue'))} →{' '}
                            {String(detail.new_values?.[field] ?? tCommon('noValue'))}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {activityRecordHref(detail) && (
                  <footer className="leads-drawer__footer">
                    <Link href={activityRecordHref(detail)!} className="leads__primary-button">
                      {t('detail.viewRecord')}
                    </Link>
                  </footer>
                )}
              </>
            )}
          </aside>
        </div>
      )}
    </main>
  );
}
