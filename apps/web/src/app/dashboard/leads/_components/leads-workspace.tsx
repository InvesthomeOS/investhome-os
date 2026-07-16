'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import {
  archiveLead,
  createLead,
  fetchLead,
  fetchLeads,
  formatBudget,
  formatDate,
  type Lead,
  type LeadFilters,
  type LeadInput,
  updateLead,
} from '@/lib/api/leads';
import {
  useLeadLabels,
} from '@/lib/i18n/lead-labels';
import { useLeadQualificationLabels } from '@/lib/i18n/lead-qualification-labels';
import { useRecordDeepLink } from '@/lib/hooks/use-record-deep-link';

import { LeadFormModal } from './lead-form-modal';

const FILTER_STORAGE_KEY = 'investhome.leads.filters';

type FormMode = 'create' | 'edit' | null;

const EMPTY_FILTERS: LeadFilters = {
  search: '',
  status: '',
  source: '',
  qualification_status: '',
  preferred_market: '',
  lead_score_min: undefined,
  lead_score_max: undefined,
};

function loadStoredFilters(): LeadFilters {
  if (typeof window === 'undefined') return EMPTY_FILTERS;
  try {
    const raw = localStorage.getItem(FILTER_STORAGE_KEY);
    if (!raw) return EMPTY_FILTERS;
    return { ...EMPTY_FILTERS, ...JSON.parse(raw) };
  } catch {
    return EMPTY_FILTERS;
  }
}

export function LeadsWorkspace() {
  const t = useTranslations('leads');
  const tQual = useTranslations('leadQualification');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const router = useRouter();
  const { getStatusLabel, getSourceLabel, statusOptions, sourceOptions } = useLeadLabels();
  const { qualificationStatusOptions } = useLeadQualificationLabels();

  const [leads, setLeads] = useState<Lead[]>([]);
  const [filters, setFilters] = useState<LeadFilters>(() => loadStoredFilters());
  const [appliedFilters, setAppliedFilters] = useState<LeadFilters>(() => loadStoredFilters());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [formMode, setFormMode] = useState<FormMode>(null);
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const activeFilterChips = useMemo(() => {
    const chips: string[] = [];
    if (appliedFilters.search) chips.push(`${t('searchLabel')}: ${appliedFilters.search}`);
    if (appliedFilters.status) chips.push(`${t('statusLabel')}: ${getStatusLabel(appliedFilters.status)}`);
    if (appliedFilters.source) chips.push(`${t('sourceLabel')}: ${getSourceLabel(appliedFilters.source)}`);
    if (appliedFilters.qualification_status) {
      chips.push(`${tQual('fields.qualificationStatus')}: ${appliedFilters.qualification_status}`);
    }
    if (appliedFilters.preferred_market) chips.push(`${tQual('overview.preferredMarket')}: ${appliedFilters.preferred_market}`);
    if (appliedFilters.lead_score_min != null) chips.push(`${tQual('filters.scoreMin')}: ${appliedFilters.lead_score_min}`);
    if (appliedFilters.lead_score_max != null) chips.push(`${tQual('filters.scoreMax')}: ${appliedFilters.lead_score_max}`);
    return chips;
  }, [appliedFilters, t, tQual, getStatusLabel, getSourceLabel]);

  const loadLeads = useCallback(async (nextFilters: LeadFilters) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchLeads(nextFilters);
      setLeads(response.items);
    } catch {
      setError(t('loadError'));
      setLeads([]);
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void loadLeads(appliedFilters);
  }, [appliedFilters, loadLeads]);

  const handleOpenLead = useCallback(
    (lead: Lead) => router.push(`/dashboard/leads/${lead.id}`),
    [router],
  );
  useRecordDeepLink(fetchLead, handleOpenLead);

  const handleApplyFilters = () => {
    const next = { ...filters };
    setAppliedFilters(next);
    localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(next));
  };

  const handleResetFilters = () => {
    setFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
    localStorage.removeItem(FILTER_STORAGE_KEY);
  };

  const demoCount = useMemo(() => leads.filter((lead) => lead.is_demo).length, [leads]);

  const handleOpenCreate = () => {
    setActionError(null);
    setFormMode('create');
  };

  const handleSubmitLead = async (input: LeadInput) => {
    setSubmitting(true);
    setActionError(null);

    try {
      if (formMode === 'create') {
        const created = await createLead(input);
        setLeads((current) => [created, ...current]);
        setSelectedLead(created);
      } else if (formMode === 'edit' && selectedLead) {
        const updated = await updateLead(selectedLead.id, input);
        setLeads((current) =>
          current.map((lead) => (lead.id === updated.id ? updated : lead)),
        );
        setSelectedLead(updated);
      }
      setFormMode(null);
    } catch {
      setActionError(t('saveError'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="dashboard leads">
      <header className="dashboard__header leads__header">
        <p className="dashboard__eyebrow">{t('eyebrow')}</p>
        <h1 className="dashboard__title">{t('title')}</h1>
        <p className="leads__subtitle">{t('subtitle')}</p>
      </header>

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
                    status: event.target.value as LeadFilters['status'],
                  }))
                }
              >
                <option value="">{t('allStatuses')}</option>
                {statusOptions.map((status) => (
                  <option key={status.value} value={status.value}>
                    {status.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="leads__field">
              <span>{t('sourceLabel')}</span>
              <select
                value={filters.source ?? ''}
                onChange={(event) =>
                  setFilters((current) => ({ ...current, source: event.target.value }))
                }
              >
                <option value="">{t('allSources')}</option>
                {sourceOptions.map((source) => (
                  <option key={source.value} value={source.value}>
                    {source.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="leads__field">
              <span>{tQual('fields.qualificationStatus')}</span>
              <select
                value={filters.qualification_status ?? ''}
                onChange={(event) =>
                  setFilters((current) => ({ ...current, qualification_status: event.target.value }))
                }
              >
                <option value="">{tQual('filters.allQualificationStatuses')}</option>
                {qualificationStatusOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="leads__field">
              <span>{tQual('overview.preferredMarket')}</span>
              <input
                type="text"
                value={filters.preferred_market ?? ''}
                onChange={(event) =>
                  setFilters((current) => ({ ...current, preferred_market: event.target.value }))
                }
              />
            </label>

            <label className="leads__field">
              <span>{tQual('filters.scoreMin')}</span>
              <input
                type="number"
                min={0}
                max={100}
                value={filters.lead_score_min ?? ''}
                onChange={(event) =>
                  setFilters((current) => ({
                    ...current,
                    lead_score_min: event.target.value ? Number(event.target.value) : undefined,
                  }))
                }
              />
            </label>

            <label className="leads__field">
              <span>{tQual('filters.scoreMax')}</span>
              <input
                type="number"
                min={0}
                max={100}
                value={filters.lead_score_max ?? ''}
                onChange={(event) =>
                  setFilters((current) => ({
                    ...current,
                    lead_score_max: event.target.value ? Number(event.target.value) : undefined,
                  }))
                }
              />
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
            {t('addLead')}
          </button>
        </div>

        {activeFilterChips.length > 0 && (
          <div className="leads__filter-chips" role="status">
            {activeFilterChips.map((chip) => (
              <span key={chip} className="leads__demo-tag">
                {chip}
              </span>
            ))}
          </div>
        )}

        {actionError && <p className="leads__error">{actionError}</p>}

        {loading && <p className="dashboard__placeholder">{t('loading')}</p>}

        {!loading && error && (
          <div className="leads__state leads__state--error">
            <p>{error}</p>
            <button
              type="button"
              className="leads__button leads__button--secondary"
              onClick={() => void loadLeads(appliedFilters)}
            >
              {tCommon('retry')}
            </button>
          </div>
        )}

        {!loading && !error && leads.length === 0 && (
          <div className="leads__state">
            <p>{t('emptyState')}</p>
            <button
              type="button"
              className="leads__button leads__button--primary"
              onClick={handleOpenCreate}
            >
              {t('addLead')}
            </button>
          </div>
        )}

        {!loading && !error && leads.length > 0 && (
          <div className="leads__table-wrap">
            <table className="leads__table">
              <thead>
                <tr>
                  <th>{t('table.name')}</th>
                  <th>{t('table.contact')}</th>
                  <th>{t('table.country')}</th>
                  <th>{t('table.source')}</th>
                  <th>{t('table.status')}</th>
                  <th>{t('table.assignedTo')}</th>
                  <th>{t('table.budget')}</th>
                  <th>{t('table.project')}</th>
                  <th>{tQual('overview.leadScore')}</th>
                  <th>{t('table.updated')}</th>
                </tr>
              </thead>
              <tbody>
                {leads.map((lead) => (
                  <tr
                    key={lead.id}
                    className="leads__row leads__row--link"
                    onClick={() => handleOpenLead(lead)}
                  >
                    <td>
                      <span className="leads__name">{lead.full_name}</span>
                      {lead.is_demo && (
                        <span className="leads__demo-tag">{tCommon('demo')}</span>
                      )}
                    </td>
                    <td>
                      <div className="leads__contact">
                        <span>{lead.email ?? tCommon('noValue')}</span>
                        <span className="leads__muted">{lead.phone ?? tCommon('noValue')}</span>
                      </div>
                    </td>
                    <td>{lead.country ?? tCommon('noValue')}</td>
                    <td>{getSourceLabel(lead.source)}</td>
                    <td>
                      <span
                        className={`leads__status leads__status--${lead.status.toLowerCase().replace(/\s+/g, '-')}`}
                      >
                        {getStatusLabel(lead.status)}
                      </span>
                    </td>
                    <td>{lead.assigned_to ?? tCommon('noValue')}</td>
                    <td>{formatBudget(lead.estimated_budget, locale)}</td>
                    <td>{lead.interested_project ?? tCommon('noValue')}</td>
                    <td>{lead.cached_lead_score ?? tCommon('noValue')}</td>
                    <td>{formatDate(lead.updated_at, locale)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <LeadFormModal
        mode={formMode}
        lead={formMode === 'edit' ? selectedLead : null}
        submitting={submitting}
        error={actionError}
        onClose={() => setFormMode(null)}
        onSubmit={(input) => void handleSubmitLead(input)}
      />
    </main>
  );
}
