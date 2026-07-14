'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { type Project, type ProjectInput } from '@/lib/api/projects';
import { useProjectLabels } from '@/lib/i18n/project-labels';

interface ProjectFormModalProps {
  mode: 'create' | 'edit' | null;
  project: Project | null;
  submitting: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (input: ProjectInput) => void;
}

const EMPTY_FORM: ProjectInput = {
  project_code: '',
  project_name: '',
  address: '',
  city: '',
  state: '',
  postal_code: '',
  country: '',
  project_type: 'residential',
  development_type: 'ground_up',
  project_status: 'pipeline',
  ownership_entity: '',
  total_units: null,
  residential_units: null,
  commercial_units: null,
  gross_square_feet: null,
  acquisition_price: null,
  total_development_cost: null,
  current_project_value: null,
  projected_sale_value: null,
  equity_required: null,
  equity_raised: null,
  debt_amount: null,
  loan_to_cost: null,
  projected_revenue: null,
  projected_profit: null,
  projected_roi: null,
  projected_irr: null,
  start_date: null,
  target_completion_date: null,
  actual_completion_date: null,
  assigned_project_manager: '',
  description: '',
  notes: '',
};

function parseOptionalNumber(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number(trimmed);
  return Number.isNaN(parsed) ? null : parsed;
}

function parseOptionalInt(value: string): number | null {
  const parsed = parseOptionalNumber(value);
  return parsed === null ? null : Math.trunc(parsed);
}

export function ProjectFormModal({
  mode,
  project,
  submitting,
  error,
  onClose,
  onSubmit,
}: ProjectFormModalProps) {
  const t = useTranslations('projects');
  const tCommon = useTranslations('common');
  const { typeOptions, developmentTypeOptions, statusOptions } = useProjectLabels();
  const [form, setForm] = useState<ProjectInput>(EMPTY_FORM);

  useEffect(() => {
    if (mode === 'edit' && project) {
      setForm({
        project_code: project.project_code,
        project_name: project.project_name,
        address: project.address ?? '',
        city: project.city ?? '',
        state: project.state ?? '',
        postal_code: project.postal_code ?? '',
        country: project.country ?? '',
        project_type: project.project_type,
        development_type: project.development_type,
        project_status: project.project_status,
        ownership_entity: project.ownership_entity ?? '',
        total_units: project.total_units,
        residential_units: project.residential_units,
        commercial_units: project.commercial_units,
        gross_square_feet: project.gross_square_feet,
        acquisition_price: project.acquisition_price ? Number(project.acquisition_price) : null,
        total_development_cost: project.total_development_cost
          ? Number(project.total_development_cost)
          : null,
        current_project_value: project.current_project_value
          ? Number(project.current_project_value)
          : null,
        projected_sale_value: project.projected_sale_value
          ? Number(project.projected_sale_value)
          : null,
        equity_required: project.equity_required ? Number(project.equity_required) : null,
        equity_raised: project.equity_raised ? Number(project.equity_raised) : null,
        debt_amount: project.debt_amount ? Number(project.debt_amount) : null,
        loan_to_cost: project.loan_to_cost ? Number(project.loan_to_cost) : null,
        projected_revenue: project.projected_revenue ? Number(project.projected_revenue) : null,
        projected_profit: project.projected_profit ? Number(project.projected_profit) : null,
        projected_roi: project.projected_roi ? Number(project.projected_roi) : null,
        projected_irr: project.projected_irr ? Number(project.projected_irr) : null,
        start_date: project.start_date,
        target_completion_date: project.target_completion_date,
        actual_completion_date: project.actual_completion_date,
        assigned_project_manager: project.assigned_project_manager ?? '',
        description: project.description ?? '',
        notes: project.notes ?? '',
      });
      return;
    }

    if (mode === 'create') {
      setForm(EMPTY_FORM);
    }
  }, [project, mode]);

  if (!mode) {
    return null;
  }

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit({
      ...form,
      address: form.address?.trim() || null,
      city: form.city?.trim() || null,
      state: form.state?.trim() || null,
      postal_code: form.postal_code?.trim() || null,
      country: form.country?.trim() || null,
      ownership_entity: form.ownership_entity?.trim() || null,
      assigned_project_manager: form.assigned_project_manager?.trim() || null,
      description: form.description?.trim() || null,
      notes: form.notes?.trim() || null,
      start_date: form.start_date || null,
      target_completion_date: form.target_completion_date || null,
      actual_completion_date: form.actual_completion_date || null,
    });
  };

  const numberField = (
    key:
      | 'total_units'
      | 'residential_units'
      | 'commercial_units'
      | 'gross_square_feet'
      | 'acquisition_price'
      | 'total_development_cost'
      | 'current_project_value'
      | 'projected_sale_value'
      | 'equity_required'
      | 'equity_raised'
      | 'debt_amount'
      | 'loan_to_cost'
      | 'projected_revenue'
      | 'projected_profit'
      | 'projected_roi'
      | 'projected_irr',
    label: string,
    parser: (value: string) => number | null = parseOptionalNumber,
  ) => (
    <label className="leads__field" key={key}>
      <span>{label}</span>
      <input
        type="number"
        step={key.includes('units') || key === 'gross_square_feet' ? '1' : '0.01'}
        value={form[key] ?? ''}
        onChange={(event) =>
          setForm((current) => ({ ...current, [key]: parser(event.target.value) }))
        }
      />
    </label>
  );

  return (
    <div className="leads-modal" role="presentation" onClick={onClose}>
      <div
        className="leads-modal__dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="project-form-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="leads-modal__header">
          <h2 id="project-form-title">
            {mode === 'create' ? t('addProject') : t('editProject')}
          </h2>
          <button type="button" className="leads__button leads__button--ghost" onClick={onClose}>
            {tCommon('close')}
          </button>
        </header>

        <form className="leads-form" onSubmit={handleSubmit}>
          <p className="leads-form__section-title">{t('sections.overview')}</p>

          <div className="leads-form__grid">
            <label className="leads__field">
              <span>{t('form.projectCode')}</span>
              <input
                required
                value={form.project_code}
                onChange={(event) =>
                  setForm((current) => ({ ...current, project_code: event.target.value }))
                }
              />
            </label>
            <label className="leads__field">
              <span>{t('form.projectName')}</span>
              <input
                required
                value={form.project_name}
                onChange={(event) =>
                  setForm((current) => ({ ...current, project_name: event.target.value }))
                }
              />
            </label>
          </div>

          <div className="leads-form__grid">
            <label className="leads__field">
              <span>{t('form.projectType')}</span>
              <select
                value={form.project_type ?? 'residential'}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    project_type: event.target.value as ProjectInput['project_type'],
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
              <span>{t('form.developmentType')}</span>
              <select
                value={form.development_type ?? 'ground_up'}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    development_type: event.target.value as ProjectInput['development_type'],
                  }))
                }
              >
                {developmentTypeOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="leads-form__grid">
            <label className="leads__field">
              <span>{t('form.projectStatus')}</span>
              <select
                value={form.project_status ?? 'pipeline'}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    project_status: event.target.value as ProjectInput['project_status'],
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
            <label className="leads__field">
              <span>{t('form.ownershipEntity')}</span>
              <input
                value={form.ownership_entity ?? ''}
                onChange={(event) =>
                  setForm((current) => ({ ...current, ownership_entity: event.target.value }))
                }
              />
            </label>
          </div>

          <label className="leads__field">
            <span>{t('form.description')}</span>
            <textarea
              rows={3}
              value={form.description ?? ''}
              onChange={(event) =>
                setForm((current) => ({ ...current, description: event.target.value }))
              }
            />
          </label>

          <p className="leads-form__section-title">{t('sections.location')}</p>

          <label className="leads__field">
            <span>{t('form.address')}</span>
            <input
              value={form.address ?? ''}
              onChange={(event) =>
                setForm((current) => ({ ...current, address: event.target.value }))
              }
            />
          </label>

          <div className="leads-form__grid">
            <label className="leads__field">
              <span>{t('form.city')}</span>
              <input
                value={form.city ?? ''}
                onChange={(event) => setForm((current) => ({ ...current, city: event.target.value }))}
              />
            </label>
            <label className="leads__field">
              <span>{t('form.state')}</span>
              <input
                value={form.state ?? ''}
                onChange={(event) =>
                  setForm((current) => ({ ...current, state: event.target.value }))
                }
              />
            </label>
          </div>

          <div className="leads-form__grid">
            <label className="leads__field">
              <span>{t('form.postalCode')}</span>
              <input
                value={form.postal_code ?? ''}
                onChange={(event) =>
                  setForm((current) => ({ ...current, postal_code: event.target.value }))
                }
              />
            </label>
            <label className="leads__field">
              <span>{t('form.country')}</span>
              <input
                value={form.country ?? ''}
                onChange={(event) =>
                  setForm((current) => ({ ...current, country: event.target.value }))
                }
              />
            </label>
          </div>

          <p className="leads-form__section-title">{t('sections.developmentProgram')}</p>

          <div className="leads-form__grid">
            {numberField('total_units', t('form.totalUnits'), parseOptionalInt)}
            {numberField('gross_square_feet', t('form.grossSquareFeet'), parseOptionalInt)}
          </div>

          <div className="leads-form__grid">
            {numberField('residential_units', t('form.residentialUnits'), parseOptionalInt)}
            {numberField('commercial_units', t('form.commercialUnits'), parseOptionalInt)}
          </div>

          <p className="leads-form__section-title">{t('sections.financialSummary')}</p>

          <div className="leads-form__grid">
            {numberField('acquisition_price', t('form.acquisitionPrice'))}
            {numberField('total_development_cost', t('form.totalDevelopmentCost'))}
          </div>

          <div className="leads-form__grid">
            {numberField('current_project_value', t('form.currentProjectValue'))}
            {numberField('projected_sale_value', t('form.projectedSaleValue'))}
          </div>

          <div className="leads-form__grid">
            {numberField('projected_revenue', t('form.projectedRevenue'))}
            {numberField('projected_profit', t('form.projectedProfit'))}
          </div>

          <div className="leads-form__grid">
            {numberField('projected_roi', t('form.projectedRoi'))}
            {numberField('projected_irr', t('form.projectedIrr'))}
          </div>

          <p className="leads-form__section-title">{t('sections.financing')}</p>

          <div className="leads-form__grid">
            {numberField('equity_required', t('form.equityRequired'))}
            {numberField('equity_raised', t('form.equityRaised'))}
          </div>

          <div className="leads-form__grid">
            {numberField('debt_amount', t('form.debtAmount'))}
            {numberField('loan_to_cost', t('form.loanToCost'))}
          </div>

          <p className="leads-form__section-title">{t('sections.timeline')}</p>

          <div className="leads-form__grid">
            <label className="leads__field">
              <span>{t('form.startDate')}</span>
              <input
                type="date"
                value={form.start_date ?? ''}
                onChange={(event) =>
                  setForm((current) => ({ ...current, start_date: event.target.value || null }))
                }
              />
            </label>
            <label className="leads__field">
              <span>{t('form.targetCompletionDate')}</span>
              <input
                type="date"
                value={form.target_completion_date ?? ''}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    target_completion_date: event.target.value || null,
                  }))
                }
              />
            </label>
          </div>

          <label className="leads__field">
            <span>{t('form.actualCompletionDate')}</span>
            <input
              type="date"
              value={form.actual_completion_date ?? ''}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  actual_completion_date: event.target.value || null,
                }))
              }
            />
          </label>

          <p className="leads-form__section-title">{t('sections.team')}</p>

          <label className="leads__field">
            <span>{t('form.assignedProjectManager')}</span>
            <input
              value={form.assigned_project_manager ?? ''}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  assigned_project_manager: event.target.value,
                }))
              }
            />
          </label>

          <p className="leads-form__section-title">{t('sections.notes')}</p>

          <label className="leads__field">
            <span>{t('form.notes')}</span>
            <textarea
              rows={4}
              value={form.notes ?? ''}
              onChange={(event) =>
                setForm((current) => ({ ...current, notes: event.target.value }))
              }
            />
          </label>

          {error && <p className="leads__error">{error}</p>}

          <footer className="leads-modal__footer">
            <button
              type="button"
              className="leads__button leads__button--ghost"
              onClick={onClose}
              disabled={submitting}
            >
              {tCommon('cancel')}
            </button>
            <button type="submit" className="leads__button leads__button--primary" disabled={submitting}>
              {submitting
                ? t('saving')
                : mode === 'create'
                  ? t('createProject')
                  : t('saveChanges')}
            </button>
          </footer>
        </form>
      </div>
    </div>
  );
}
