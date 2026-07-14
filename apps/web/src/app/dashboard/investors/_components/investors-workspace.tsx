'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { DashboardHeaderActions } from '@/app/dashboard/_components/dashboard-header-actions';
import {
  archiveInvestor,
  createInvestor,
  fetchInvestor,
  fetchInvestorStats,
  fetchInvestors,
  formatCurrency,
  formatShortDate,
  type Investor,
  type InvestorFilters,
  type InvestorInput,
  type InvestorStats,
  updateInvestor,
} from '@/lib/api/investors';
import { useInvestorLabels } from '@/lib/i18n/investor-labels';
import { useRecordDeepLink } from '@/lib/hooks/use-record-deep-link';

import { InvestorDetailDrawer } from './investor-detail-drawer';
import { InvestorFormModal } from './investor-form-modal';

type FormMode = 'create' | 'edit' | null;

const PAGE_SIZE = 20;

const EMPTY_FILTERS: InvestorFilters = {
  search: '',
  status: '',
  investor_type: '',
  country: '',
  preferred_investment_model: '',
  sort_by: 'updated_at',
  sort_order: 'desc',
  page: 1,
  page_size: PAGE_SIZE,
};

export function InvestorsWorkspace() {
  const t = useTranslations('investors');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { getTypeLabel, getStatusLabel, getModelLabel, typeOptions, statusOptions, modelOptions } =
    useInvestorLabels();

  const [investors, setInvestors] = useState<Investor[]>([]);
  const [stats, setStats] = useState<InvestorStats | null>(null);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(0);
  const [filters, setFilters] = useState<InvestorFilters>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<InvestorFilters>(EMPTY_FILTERS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedInvestor, setSelectedInvestor] = useState<Investor | null>(null);
  const [formMode, setFormMode] = useState<FormMode>(null);
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const loadStats = useCallback(async () => {
    try {
      const response = await fetchInvestorStats();
      setStats(response);
    } catch {
      setStats(null);
    }
  }, []);

  const loadInvestors = useCallback(async (nextFilters: InvestorFilters) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchInvestors(nextFilters);
      setInvestors(response.items);
      setTotal(response.total);
      setPages(response.pages);
    } catch {
      setError(t('loadError'));
      setInvestors([]);
      setTotal(0);
      setPages(0);
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void loadStats();
  }, [loadStats]);

  useEffect(() => {
    void loadInvestors(appliedFilters);
  }, [appliedFilters, loadInvestors]);

  const handleOpenInvestor = useCallback((investor: Investor) => setSelectedInvestor(investor), []);
  useRecordDeepLink(fetchInvestor, handleOpenInvestor);

  const demoCount = useMemo(
    () => investors.filter((investor) => investor.is_demo).length,
    [investors],
  );

  const handleApplyFilters = () => {
    setAppliedFilters({ ...filters, page: 1 });
  };

  const handleResetFilters = () => {
    setFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
  };

  const handlePageChange = (page: number) => {
    setAppliedFilters((current) => ({ ...current, page }));
  };

  const handleOpenCreate = () => {
    setActionError(null);
    setFormMode('create');
  };

  const handleOpenEdit = (investor: Investor) => {
    setActionError(null);
    setSelectedInvestor(investor);
    setFormMode('edit');
  };

  const handleSubmitInvestor = async (input: InvestorInput) => {
    setSubmitting(true);
    setActionError(null);

    try {
      if (formMode === 'create') {
        await createInvestor(input);
      } else if (formMode === 'edit' && selectedInvestor) {
        await updateInvestor(selectedInvestor.id, input);
      }
      setFormMode(null);
      await Promise.all([loadInvestors(appliedFilters), loadStats()]);
    } catch {
      setActionError(t('saveError'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleArchiveInvestor = async (investor: Investor) => {
    setSubmitting(true);
    setActionError(null);

    try {
      await archiveInvestor(investor.id);
      setSelectedInvestor(null);
      await Promise.all([loadInvestors(appliedFilters), loadStats()]);
    } catch {
      setActionError(t('archiveError'));
    } finally {
      setSubmitting(false);
    }
  };

  const sortValue = `${appliedFilters.sort_by}:${appliedFilters.sort_order}`;

  return (
    <main className="dashboard leads investors">
      <header className="dashboard__header leads__header">
        <div>
          <p className="dashboard__eyebrow">{t('eyebrow')}</p>
          <h1 className="dashboard__title">{t('title')}</h1>
          <p className="leads__subtitle">{t('subtitle')}</p>
        </div>
        <DashboardHeaderActions />
      </header>

      {stats && (
        <section className="investors__stats">
          <article className="investors__stat-card">
            <p>{t('stats.total')}</p>
            <strong>{stats.total}</strong>
          </article>
          <article className="investors__stat-card">
            <p>{t('stats.active')}</p>
            <strong>{stats.active}</strong>
          </article>
          <article className="investors__stat-card">
            <p>{t('stats.invested')}</p>
            <strong>{stats.invested}</strong>
          </article>
          <article className="investors__stat-card">
            <p>{t('stats.capacity')}</p>
            <strong>{formatCurrency(stats.total_investment_capacity, locale)}</strong>
          </article>
        </section>
      )}

      {demoCount > 0 && (
        <div className="leads__demo-banner" role="status">
          {t('demoBanner', { count: demoCount })}
        </div>
      )}

      <section className="dashboard__panel leads__panel">
        <div className="leads__toolbar">
          <div className="leads__filters">
            <label className="leads__field">
              <span>{t('searchLabel')}</span>
              <input
                type="search"
                value={filters.search ?? ''}
                placeholder={t('searchPlaceholder')}
                onChange={(event) =>
                  setFilters((current) => ({ ...current, search: event.target.value }))
                }
              />
            </label>

            <label className="leads__field">
              <span>{t('statusLabel')}</span>
              <select
                value={filters.status ?? ''}
                onChange={(event) =>
                  setFilters((current) => ({
                    ...current,
                    status: event.target.value as InvestorFilters['status'],
                  }))
                }
              >
                <option value="">{t('allStatuses')}</option>
                {statusOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="leads__field">
              <span>{t('typeLabel')}</span>
              <select
                value={filters.investor_type ?? ''}
                onChange={(event) =>
                  setFilters((current) => ({
                    ...current,
                    investor_type: event.target.value as InvestorFilters['investor_type'],
                  }))
                }
              >
                <option value="">{t('allTypes')}</option>
                {typeOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="leads__field">
              <span>{t('countryLabel')}</span>
              <input
                value={filters.country ?? ''}
                placeholder={t('countryPlaceholder')}
                onChange={(event) =>
                  setFilters((current) => ({ ...current, country: event.target.value }))
                }
              />
            </label>

            <label className="leads__field">
              <span>{t('modelLabel')}</span>
              <select
                value={filters.preferred_investment_model ?? ''}
                onChange={(event) =>
                  setFilters((current) => ({
                    ...current,
                    preferred_investment_model: event.target
                      .value as InvestorFilters['preferred_investment_model'],
                  }))
                }
              >
                <option value="">{t('allModels')}</option>
                {modelOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="leads__field">
              <span>{t('sortLabel')}</span>
              <select
                value={sortValue}
                onChange={(event) => {
                  const [sort_by, sort_order] = event.target.value.split(':') as [
                    string,
                    'asc' | 'desc',
                  ];
                  setFilters((current) => ({ ...current, sort_by, sort_order }));
                }}
              >
                <option value="updated_at:desc">{t('sortUpdatedDesc')}</option>
                <option value="updated_at:asc">{t('sortUpdatedAsc')}</option>
                <option value="full_name:asc">{t('sortNameAsc')}</option>
                <option value="full_name:desc">{t('sortNameDesc')}</option>
                <option value="investment_capacity:desc">{t('sortCapacityDesc')}</option>
              </select>
            </label>

            <div className="leads__filter-actions">
              <button
                type="button"
                className="leads__button leads__button--secondary"
                onClick={handleApplyFilters}
              >
                {tCommon('apply')}
              </button>
              <button
                type="button"
                className="leads__button leads__button--ghost"
                onClick={handleResetFilters}
              >
                {tCommon('reset')}
              </button>
            </div>
          </div>

          <button
            type="button"
            className="leads__button leads__button--primary"
            onClick={handleOpenCreate}
          >
            {t('addInvestor')}
          </button>
        </div>

        {actionError && <p className="leads__error">{actionError}</p>}

        {loading && <p className="dashboard__placeholder">{t('loading')}</p>}

        {!loading && error && (
          <div className="leads__state leads__state--error">
            <p>{error}</p>
            <button
              type="button"
              className="leads__button leads__button--secondary"
              onClick={() => void loadInvestors(appliedFilters)}
            >
              {tCommon('retry')}
            </button>
          </div>
        )}

        {!loading && !error && investors.length === 0 && (
          <div className="leads__state">
            <p>{t('emptyState')}</p>
            <button
              type="button"
              className="leads__button leads__button--primary"
              onClick={handleOpenCreate}
            >
              {t('addInvestor')}
            </button>
          </div>
        )}

        {!loading && !error && investors.length > 0 && (
          <>
            <div className="leads__table-wrap">
              <table className="leads__table">
                <thead>
                  <tr>
                    <th>{t('table.name')}</th>
                    <th>{t('table.country')}</th>
                    <th>{t('table.type')}</th>
                    <th>{t('table.status')}</th>
                    <th>{t('table.capacity')}</th>
                    <th>{t('table.model')}</th>
                    <th>{t('table.assignedTo')}</th>
                    <th>{t('table.lastContact')}</th>
                    <th>{t('table.nextFollowUp')}</th>
                  </tr>
                </thead>
                <tbody>
                  {investors.map((investor) => (
                    <tr
                      key={investor.id}
                      className="leads__row"
                      onClick={() => setSelectedInvestor(investor)}
                    >
                      <td>
                        <span className="leads__name">{investor.full_name}</span>
                        {investor.is_demo && (
                          <span className="leads__demo-tag">{tCommon('demo')}</span>
                        )}
                      </td>
                      <td>{investor.country ?? tCommon('noValue')}</td>
                      <td>{getTypeLabel(investor.investor_type)}</td>
                      <td>
                        <span className="leads__status">{getStatusLabel(investor.status)}</span>
                      </td>
                      <td>{formatCurrency(investor.investment_capacity, locale)}</td>
                      <td>{getModelLabel(investor.preferred_investment_model)}</td>
                      <td>{investor.assigned_to ?? tCommon('noValue')}</td>
                      <td>{formatShortDate(investor.last_contact_date, locale)}</td>
                      <td>{formatShortDate(investor.next_follow_up_date, locale)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {pages > 1 && (
              <div className="investors__pagination">
                <p>{t('pagination', { page: appliedFilters.page ?? 1, pages, total })}</p>
                <div className="investors__pagination-actions">
                  <button
                    type="button"
                    className="leads__button leads__button--ghost"
                    disabled={(appliedFilters.page ?? 1) <= 1}
                    onClick={() => handlePageChange((appliedFilters.page ?? 1) - 1)}
                  >
                    {t('prevPage')}
                  </button>
                  <button
                    type="button"
                    className="leads__button leads__button--ghost"
                    disabled={(appliedFilters.page ?? 1) >= pages}
                    onClick={() => handlePageChange((appliedFilters.page ?? 1) + 1)}
                  >
                    {t('nextPage')}
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </section>

      <InvestorDetailDrawer
        investor={selectedInvestor}
        onClose={() => setSelectedInvestor(null)}
        onEdit={handleOpenEdit}
        onArchive={(investor) => void handleArchiveInvestor(investor)}
        archiving={submitting}
      />

      <InvestorFormModal
        mode={formMode}
        investor={formMode === 'edit' ? selectedInvestor : null}
        submitting={submitting}
        error={actionError}
        onClose={() => setFormMode(null)}
        onSubmit={(input) => void handleSubmitInvestor(input)}
      />
    </main>
  );
}
