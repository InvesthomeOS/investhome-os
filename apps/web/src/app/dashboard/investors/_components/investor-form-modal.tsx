'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import {
  type Investor,
  type InvestorInput,
} from '@/lib/api/investors';
import { useInvestorLabels } from '@/lib/i18n/investor-labels';

interface InvestorFormModalProps {
  mode: 'create' | 'edit' | null;
  investor: Investor | null;
  submitting: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (input: InvestorInput) => void;
}

const EMPTY_FORM: InvestorInput = {
  full_name: '',
  email: '',
  phone: '',
  country: '',
  city: '',
  investor_type: 'individual',
  accreditation_status: 'unknown',
  preferred_investment_model: 'rental_income',
  investment_capacity: null,
  minimum_ticket: null,
  maximum_ticket: null,
  preferred_markets: '',
  preferred_projects: '',
  risk_profile: 'balanced',
  status: 'prospect',
  assigned_to: '',
  source: '',
  notes: '',
  last_contact_date: null,
  next_follow_up_date: null,
};

export function InvestorFormModal({
  mode,
  investor,
  submitting,
  error,
  onClose,
  onSubmit,
}: InvestorFormModalProps) {
  const t = useTranslations('investors');
  const tCommon = useTranslations('common');
  const {
    typeOptions,
    statusOptions,
    modelOptions,
    accreditationOptions,
    riskOptions,
  } = useInvestorLabels();
  const [form, setForm] = useState<InvestorInput>(EMPTY_FORM);

  useEffect(() => {
    if (mode === 'edit' && investor) {
      setForm({
        full_name: investor.full_name,
        email: investor.email ?? '',
        phone: investor.phone ?? '',
        country: investor.country ?? '',
        city: investor.city ?? '',
        investor_type: investor.investor_type,
        accreditation_status: investor.accreditation_status,
        preferred_investment_model: investor.preferred_investment_model,
        investment_capacity: investor.investment_capacity
          ? Number(investor.investment_capacity)
          : null,
        minimum_ticket: investor.minimum_ticket ? Number(investor.minimum_ticket) : null,
        maximum_ticket: investor.maximum_ticket ? Number(investor.maximum_ticket) : null,
        preferred_markets: investor.preferred_markets ?? '',
        preferred_projects: investor.preferred_projects ?? '',
        risk_profile: investor.risk_profile,
        status: investor.status,
        assigned_to: investor.assigned_to ?? '',
        source: investor.source ?? '',
        notes: investor.notes ?? '',
        last_contact_date: investor.last_contact_date,
        next_follow_up_date: investor.next_follow_up_date,
      });
      return;
    }

    if (mode === 'create') {
      setForm(EMPTY_FORM);
    }
  }, [investor, mode]);

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
      city: form.city?.trim() || null,
      preferred_investment_model: form.preferred_investment_model || null,
      preferred_markets: form.preferred_markets?.trim() || null,
      preferred_projects: form.preferred_projects?.trim() || null,
      assigned_to: form.assigned_to?.trim() || null,
      source: form.source?.trim() || null,
      notes: form.notes?.trim() || null,
      risk_profile: form.risk_profile || null,
      last_contact_date: form.last_contact_date || null,
      next_follow_up_date: form.next_follow_up_date || null,
    });
  };

  return (
    <div className="leads-modal" role="presentation" onClick={onClose}>
      <div
        className="leads-modal__dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="investor-form-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="leads-modal__header">
          <h2 id="investor-form-title">
            {mode === 'create' ? t('addInvestor') : t('editInvestor')}
          </h2>
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
              onChange={(event) =>
                setForm((current) => ({ ...current, full_name: event.target.value }))
              }
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
                onChange={(event) =>
                  setForm((current) => ({ ...current, country: event.target.value }))
                }
              />
            </label>
            <label className="leads__field">
              <span>{t('form.city')}</span>
              <input
                value={form.city ?? ''}
                onChange={(event) => setForm((current) => ({ ...current, city: event.target.value }))}
              />
            </label>
          </div>

          <div className="leads-form__grid">
            <label className="leads__field">
              <span>{t('form.investorType')}</span>
              <select
                value={form.investor_type ?? 'individual'}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    investor_type: event.target.value as InvestorInput['investor_type'],
                  }))
                }
              >
                {typeOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="leads__field">
              <span>{t('form.accreditationStatus')}</span>
              <select
                value={form.accreditation_status ?? 'unknown'}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    accreditation_status: event.target.value as InvestorInput['accreditation_status'],
                  }))
                }
              >
                {accreditationOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="leads-form__grid">
            <label className="leads__field">
              <span>{t('form.preferredModel')}</span>
              <select
                value={form.preferred_investment_model ?? ''}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    preferred_investment_model: event.target.value as InvestorInput['preferred_investment_model'],
                  }))
                }
              >
                {modelOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="leads__field">
              <span>{t('form.riskProfile')}</span>
              <select
                value={form.risk_profile ?? ''}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    risk_profile: event.target.value as InvestorInput['risk_profile'],
                  }))
                }
              >
                {riskOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="leads-form__grid">
            <label className="leads__field">
              <span>{t('form.investmentCapacity')}</span>
              <input
                type="number"
                min="0"
                step="10000"
                value={form.investment_capacity ?? ''}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    investment_capacity: event.target.value ? Number(event.target.value) : null,
                  }))
                }
              />
            </label>
            <label className="leads__field">
              <span>{t('form.status')}</span>
              <select
                value={form.status ?? 'prospect'}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    status: event.target.value as InvestorInput['status'],
                  }))
                }
              >
                {statusOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="leads-form__grid">
            <label className="leads__field">
              <span>{t('form.minimumTicket')}</span>
              <input
                type="number"
                min="0"
                step="10000"
                value={form.minimum_ticket ?? ''}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    minimum_ticket: event.target.value ? Number(event.target.value) : null,
                  }))
                }
              />
            </label>
            <label className="leads__field">
              <span>{t('form.maximumTicket')}</span>
              <input
                type="number"
                min="0"
                step="10000"
                value={form.maximum_ticket ?? ''}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    maximum_ticket: event.target.value ? Number(event.target.value) : null,
                  }))
                }
              />
            </label>
          </div>

          <label className="leads__field">
            <span>{t('form.preferredMarkets')}</span>
            <input
              value={form.preferred_markets ?? ''}
              onChange={(event) =>
                setForm((current) => ({ ...current, preferred_markets: event.target.value }))
              }
            />
          </label>

          <label className="leads__field">
            <span>{t('form.preferredProjects')}</span>
            <input
              value={form.preferred_projects ?? ''}
              onChange={(event) =>
                setForm((current) => ({ ...current, preferred_projects: event.target.value }))
              }
            />
          </label>

          <div className="leads-form__grid">
            <label className="leads__field">
              <span>{t('form.assignedTo')}</span>
              <input
                value={form.assigned_to ?? ''}
                onChange={(event) =>
                  setForm((current) => ({ ...current, assigned_to: event.target.value }))
                }
              />
            </label>
            <label className="leads__field">
              <span>{t('form.source')}</span>
              <input
                value={form.source ?? ''}
                onChange={(event) => setForm((current) => ({ ...current, source: event.target.value }))}
              />
            </label>
          </div>

          <div className="leads-form__grid">
            <label className="leads__field">
              <span>{t('form.lastContactDate')}</span>
              <input
                type="date"
                value={form.last_contact_date ?? ''}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    last_contact_date: event.target.value || null,
                  }))
                }
              />
            </label>
            <label className="leads__field">
              <span>{t('form.nextFollowUpDate')}</span>
              <input
                type="date"
                value={form.next_follow_up_date ?? ''}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    next_follow_up_date: event.target.value || null,
                  }))
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
                  ? t('createInvestor')
                  : t('saveChanges')}
            </button>
          </footer>
        </form>
      </div>
    </div>
  );
}
