'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

import { OperationalStatus } from '@/app/dashboard/_components/operational-status';
import {
  archiveLead,
  createLead,
  fetchLeads,
  formatBudget,
  formatDate,
  LEAD_SOURCES,
  LEAD_STATUSES,
  type Lead,
  type LeadFilters,
  type LeadInput,
  updateLead,
} from '@/lib/api/leads';

import { LeadDetailDrawer } from './lead-detail-drawer';
import { LeadFormModal } from './lead-form-modal';

type FormMode = 'create' | 'edit' | null;

const EMPTY_FILTERS: LeadFilters = {
  search: '',
  status: '',
  source: '',
};

export function LeadsWorkspace() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [filters, setFilters] = useState<LeadFilters>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<LeadFilters>(EMPTY_FILTERS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [formMode, setFormMode] = useState<FormMode>(null);
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const loadLeads = useCallback(async (nextFilters: LeadFilters) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchLeads(nextFilters);
      setLeads(response.items);
    } catch (loadError) {
      const message =
        loadError instanceof Error ? loadError.message : 'Unable to load leads.';
      setError(message);
      setLeads([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadLeads(appliedFilters);
  }, [appliedFilters, loadLeads]);

  const demoCount = useMemo(() => leads.filter((lead) => lead.is_demo).length, [leads]);

  const handleApplyFilters = () => {
    setAppliedFilters({ ...filters });
  };

  const handleResetFilters = () => {
    setFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
  };

  const handleOpenCreate = () => {
    setActionError(null);
    setFormMode('create');
  };

  const handleOpenEdit = (lead: Lead) => {
    setActionError(null);
    setSelectedLead(lead);
    setFormMode('edit');
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
    } catch (submitError) {
      const message =
        submitError instanceof Error ? submitError.message : 'Unable to save lead.';
      setActionError(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleArchiveLead = async (lead: Lead) => {
    setSubmitting(true);
    setActionError(null);

    try {
      await archiveLead(lead.id);
      setLeads((current) => current.filter((item) => item.id !== lead.id));
      setSelectedLead(null);
    } catch (archiveError) {
      const message =
        archiveError instanceof Error ? archiveError.message : 'Unable to archive lead.';
      setActionError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="dashboard leads">
      <header className="dashboard__header leads__header">
        <div>
          <p className="dashboard__eyebrow">Pipeline</p>
          <h1 className="dashboard__title">Leads</h1>
          <p className="leads__subtitle">Pipeline visibility and acquisition funnel metrics.</p>
        </div>
        <OperationalStatus />
      </header>

      {demoCount > 0 && (
        <div className="leads__demo-banner" role="status">
          Showing {demoCount} development demo lead{demoCount === 1 ? '' : 's'} seeded for local
          testing.
        </div>
      )}

      <section className="dashboard__panel leads__panel">
        <div className="leads__toolbar">
          <div className="leads__filters">
            <label className="leads__field">
              <span>Search</span>
              <input
                type="search"
                value={filters.search ?? ''}
                placeholder="Name, email, phone, project"
                onChange={(event) =>
                  setFilters((current) => ({ ...current, search: event.target.value }))
                }
              />
            </label>

            <label className="leads__field">
              <span>Status</span>
              <select
                value={filters.status ?? ''}
                onChange={(event) =>
                  setFilters((current) => ({
                    ...current,
                    status: event.target.value as LeadFilters['status'],
                  }))
                }
              >
                <option value="">All statuses</option>
                {LEAD_STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {status}
                  </option>
                ))}
              </select>
            </label>

            <label className="leads__field">
              <span>Source</span>
              <select
                value={filters.source ?? ''}
                onChange={(event) =>
                  setFilters((current) => ({ ...current, source: event.target.value }))
                }
              >
                <option value="">All sources</option>
                {LEAD_SOURCES.map((source) => (
                  <option key={source} value={source}>
                    {source}
                  </option>
                ))}
              </select>
            </label>

            <div className="leads__filter-actions">
              <button type="button" className="leads__button leads__button--secondary" onClick={handleApplyFilters}>
                Apply
              </button>
              <button type="button" className="leads__button leads__button--ghost" onClick={handleResetFilters}>
                Reset
              </button>
            </div>
          </div>

          <button type="button" className="leads__button leads__button--primary" onClick={handleOpenCreate}>
            Add Lead
          </button>
        </div>

        {actionError && <p className="leads__error">{actionError}</p>}

        {loading && <p className="dashboard__placeholder">Loading leads…</p>}

        {!loading && error && (
          <div className="leads__state leads__state--error">
            <p>{error}</p>
            <button type="button" className="leads__button leads__button--secondary" onClick={() => void loadLeads(appliedFilters)}>
              Retry
            </button>
          </div>
        )}

        {!loading && !error && leads.length === 0 && (
          <div className="leads__state">
            <p>No leads match the current filters.</p>
            <button type="button" className="leads__button leads__button--primary" onClick={handleOpenCreate}>
              Add Lead
            </button>
          </div>
        )}

        {!loading && !error && leads.length > 0 && (
          <div className="leads__table-wrap">
            <table className="leads__table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Contact</th>
                  <th>Country</th>
                  <th>Source</th>
                  <th>Status</th>
                  <th>Assigned To</th>
                  <th>Budget</th>
                  <th>Project</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                {leads.map((lead) => (
                  <tr
                    key={lead.id}
                    className="leads__row"
                    onClick={() => setSelectedLead(lead)}
                  >
                    <td>
                      <span className="leads__name">{lead.full_name}</span>
                      {lead.is_demo && <span className="leads__demo-tag">Demo</span>}
                    </td>
                    <td>
                      <div className="leads__contact">
                        <span>{lead.email ?? '—'}</span>
                        <span className="leads__muted">{lead.phone ?? '—'}</span>
                      </div>
                    </td>
                    <td>{lead.country ?? '—'}</td>
                    <td>{lead.source ?? '—'}</td>
                    <td>
                      <span className={`leads__status leads__status--${lead.status.toLowerCase().replace(/\s+/g, '-')}`}>
                        {lead.status}
                      </span>
                    </td>
                    <td>{lead.assigned_to ?? '—'}</td>
                    <td>{formatBudget(lead.estimated_budget)}</td>
                    <td>{lead.interested_project ?? '—'}</td>
                    <td>{formatDate(lead.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <LeadDetailDrawer
        lead={selectedLead}
        onClose={() => setSelectedLead(null)}
        onEdit={handleOpenEdit}
        onArchive={(lead) => void handleArchiveLead(lead)}
        archiving={submitting}
      />

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
