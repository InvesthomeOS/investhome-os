'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import {
  type Lead,
  type LeadInput,
} from '@/lib/api/leads';
import { useLeadLabels } from '@/lib/i18n/lead-labels';

interface LeadFormModalProps {
  mode: 'create' | 'edit' | null;
  lead: Lead | null;
  submitting: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (input: LeadInput) => void;
}

const EMPTY_FORM: LeadInput = {
  full_name: '',
  email: '',
  phone: '',
  country: '',
  source: 'Website',
  status: 'New',
  assigned_to: '',
  estimated_budget: null,
  interested_project: '',
  notes: '',
};

export function LeadFormModal({
  mode,
  lead,
  submitting,
  error,
  onClose,
  onSubmit,
}: LeadFormModalProps) {
  const t = useTranslations('leads');
  const tCommon = useTranslations('common');
  const { statusOptions, sourceOptions } = useLeadLabels();
  const [form, setForm] = useState<LeadInput>(EMPTY_FORM);

  useEffect(() => {
    if (mode === 'edit' && lead) {
      setForm({
        full_name: lead.full_name,
        email: lead.email ?? '',
        phone: lead.phone ?? '',
        country: lead.country ?? '',
        source: lead.source ?? 'Website',
        status: lead.status,
        assigned_to: lead.assigned_to ?? '',
        estimated_budget: lead.estimated_budget ? Number(lead.estimated_budget) : null,
        interested_project: lead.interested_project ?? '',
        notes: lead.notes ?? '',
      });
      return;
    }

    if (mode === 'create') {
      setForm(EMPTY_FORM);
    }
  }, [lead, mode]);

  if (!mode) {
    return null;
  }

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit({
      ...form,
      email: form.email?.trim() || null,
      phone: form.phone?.trim() || null,
      country: form.country?.trim() || null,
      source: form.source?.trim() || null,
      assigned_to: form.assigned_to?.trim() || null,
      interested_project: form.interested_project?.trim() || null,
      notes: form.notes?.trim() || null,
    });
  };

  return (
    <div className="leads-modal" role="presentation" onClick={onClose}>
      <div
        className="leads-modal__dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="lead-form-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="leads-modal__header">
          <h2 id="lead-form-title">{mode === 'create' ? t('addLead') : t('editLead')}</h2>
          <button type="button" className="leads__button leads__button--ghost" onClick={onClose}>
            {tCommon('close')}
          </button>
        </header>

        <form className="leads-form" onSubmit={handleSubmit}>
          <label className="leads__field">
            <span>{t('form.fullName')}</span>
            <input
              required
              value={form.full_name}
              onChange={(event) => setForm((current) => ({ ...current, full_name: event.target.value }))}
            />
          </label>

          <div className="leads-form__grid">
            <label className="leads__field">
              <span>{t('form.email')}</span>
              <input
                type="email"
                value={form.email ?? ''}
                onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
              />
            </label>
            <label className="leads__field">
              <span>{t('form.phone')}</span>
              <input
                value={form.phone ?? ''}
                onChange={(event) => setForm((current) => ({ ...current, phone: event.target.value }))}
              />
            </label>
          </div>

          <div className="leads-form__grid">
            <label className="leads__field">
              <span>{t('form.country')}</span>
              <input
                value={form.country ?? ''}
                onChange={(event) => setForm((current) => ({ ...current, country: event.target.value }))}
              />
            </label>
            <label className="leads__field">
              <span>{t('form.source')}</span>
              <select
                value={form.source ?? ''}
                onChange={(event) => setForm((current) => ({ ...current, source: event.target.value }))}
              >
                {sourceOptions.map((source) => (
                  <option key={source.value} value={source.value}>
                    {source.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="leads-form__grid">
            <label className="leads__field">
              <span>{t('form.status')}</span>
              <select
                value={form.status ?? 'New'}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    status: event.target.value as LeadInput['status'],
                  }))
                }
              >
                {statusOptions.map((status) => (
                  <option key={status.value} value={status.value}>
                    {status.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="leads__field">
              <span>{t('form.assignedTo')}</span>
              <input
                value={form.assigned_to ?? ''}
                onChange={(event) =>
                  setForm((current) => ({ ...current, assigned_to: event.target.value }))
                }
              />
            </label>
          </div>

          <div className="leads-form__grid">
            <label className="leads__field">
              <span>{t('form.estimatedBudget')}</span>
              <input
                type="number"
                min="0"
                step="1000"
                value={form.estimated_budget ?? ''}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    estimated_budget: event.target.value ? Number(event.target.value) : null,
                  }))
                }
              />
            </label>
            <label className="leads__field">
              <span>{t('form.interestedProject')}</span>
              <input
                value={form.interested_project ?? ''}
                onChange={(event) =>
                  setForm((current) => ({ ...current, interested_project: event.target.value }))
                }
              />
            </label>
          </div>

          <label className="leads__field">
            <span>{t('form.notes')}</span>
            <textarea
              rows={4}
              value={form.notes ?? ''}
              onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))}
            />
          </label>

          {error && <p className="leads__error">{error}</p>}

          <footer className="leads-modal__footer">
            <button type="button" className="leads__button leads__button--ghost" onClick={onClose}>
              {tCommon('cancel')}
            </button>
            <button type="submit" className="leads__button leads__button--primary" disabled={submitting}>
              {submitting
                ? t('saving')
                : mode === 'create'
                  ? t('createLead')
                  : t('saveChanges')}
            </button>
          </footer>
        </form>
      </div>
    </div>
  );
}
