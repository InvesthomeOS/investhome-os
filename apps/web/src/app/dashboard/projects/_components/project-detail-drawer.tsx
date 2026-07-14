'use client';

import { useLocale, useTranslations } from 'next-intl';

import {
  formatCurrency,
  formatDate,
  formatNumber,
  formatPercent,
  formatShortDate,
  type Project,
} from '@/lib/api/projects';
import { useProjectLabels } from '@/lib/i18n/project-labels';

interface ProjectDetailDrawerProps {
  project: Project | null;
  archiving: boolean;
  onClose: () => void;
  onEdit: (project: Project) => void;
  onArchive: (project: Project) => void;
}

function DetailSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="leads-drawer__section">
      <h3>{title}</h3>
      <dl className="leads-drawer__grid">{children}</dl>
    </section>
  );
}

function DetailField({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

export function ProjectDetailDrawer({
  project,
  archiving,
  onClose,
  onEdit,
  onArchive,
}: ProjectDetailDrawerProps) {
  const t = useTranslations('projects');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { getTypeLabel, getDevelopmentTypeLabel, getStatusLabel } = useProjectLabels();

  if (!project) {
    return null;
  }

  return (
    <div className="leads-drawer" role="presentation" onClick={onClose}>
      <aside
        className="leads-drawer__panel leads-drawer__panel--wide"
        role="dialog"
        aria-modal="true"
        aria-labelledby="project-detail-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="leads-drawer__header">
          <div>
            <p className="dashboard__eyebrow">{t('detailEyebrow')}</p>
            <h2 id="project-detail-title">{project.project_name}</h2>
            <p className="leads__meta">{project.project_code}</p>
            {project.is_demo && (
              <span className="leads__demo-tag">{tCommon('demoData')}</span>
            )}
          </div>
          <button type="button" className="leads__button leads__button--ghost" onClick={onClose}>
            {tCommon('close')}
          </button>
        </header>

        <DetailSection title={t('sections.overview')}>
          <DetailField label={t('detail.projectType')} value={getTypeLabel(project.project_type)} />
          <DetailField
            label={t('detail.developmentType')}
            value={getDevelopmentTypeLabel(project.development_type)}
          />
          <DetailField
            label={t('detail.projectStatus')}
            value={getStatusLabel(project.project_status)}
          />
          <DetailField
            label={t('detail.ownershipEntity')}
            value={project.ownership_entity ?? tCommon('noValue')}
          />
          <DetailField
            label={t('detail.description')}
            value={project.description ?? t('noDescription')}
          />
        </DetailSection>

        <DetailSection title={t('sections.location')}>
          <DetailField label={t('detail.address')} value={project.address ?? tCommon('noValue')} />
          <DetailField label={t('detail.city')} value={project.city ?? tCommon('noValue')} />
          <DetailField label={t('detail.state')} value={project.state ?? tCommon('noValue')} />
          <DetailField
            label={t('detail.postalCode')}
            value={project.postal_code ?? tCommon('noValue')}
          />
          <DetailField label={t('detail.country')} value={project.country ?? tCommon('noValue')} />
        </DetailSection>

        <DetailSection title={t('sections.developmentProgram')}>
          <DetailField
            label={t('detail.totalUnits')}
            value={formatNumber(project.total_units, locale)}
          />
          <DetailField
            label={t('detail.residentialUnits')}
            value={formatNumber(project.residential_units, locale)}
          />
          <DetailField
            label={t('detail.commercialUnits')}
            value={formatNumber(project.commercial_units, locale)}
          />
          <DetailField
            label={t('detail.grossSquareFeet')}
            value={formatNumber(project.gross_square_feet, locale)}
          />
        </DetailSection>

        <DetailSection title={t('sections.financialSummary')}>
          <DetailField
            label={t('detail.acquisitionPrice')}
            value={formatCurrency(project.acquisition_price, locale)}
          />
          <DetailField
            label={t('detail.totalDevelopmentCost')}
            value={formatCurrency(project.total_development_cost, locale)}
          />
          <DetailField
            label={t('detail.currentProjectValue')}
            value={formatCurrency(project.current_project_value, locale)}
          />
          <DetailField
            label={t('detail.projectedSaleValue')}
            value={formatCurrency(project.projected_sale_value, locale)}
          />
          <DetailField
            label={t('detail.projectedRevenue')}
            value={formatCurrency(project.projected_revenue, locale)}
          />
          <DetailField
            label={t('detail.projectedProfit')}
            value={formatCurrency(project.projected_profit, locale)}
          />
          <DetailField
            label={t('detail.projectedRoi')}
            value={formatPercent(project.projected_roi, locale)}
          />
          <DetailField
            label={t('detail.projectedIrr')}
            value={formatPercent(project.projected_irr, locale)}
          />
        </DetailSection>

        <DetailSection title={t('sections.financing')}>
          <DetailField
            label={t('detail.equityRequired')}
            value={formatCurrency(project.equity_required, locale)}
          />
          <DetailField
            label={t('detail.equityRaised')}
            value={formatCurrency(project.equity_raised, locale)}
          />
          <DetailField
            label={t('detail.debtAmount')}
            value={formatCurrency(project.debt_amount, locale)}
          />
          <DetailField
            label={t('detail.loanToCost')}
            value={formatPercent(project.loan_to_cost, locale)}
          />
        </DetailSection>

        <DetailSection title={t('sections.timeline')}>
          <DetailField
            label={t('detail.startDate')}
            value={formatShortDate(project.start_date, locale)}
          />
          <DetailField
            label={t('detail.targetCompletionDate')}
            value={formatShortDate(project.target_completion_date, locale)}
          />
          <DetailField
            label={t('detail.actualCompletionDate')}
            value={formatShortDate(project.actual_completion_date, locale)}
          />
          <DetailField label={t('detail.created')} value={formatDate(project.created_at, locale)} />
          <DetailField label={t('detail.updated')} value={formatDate(project.updated_at, locale)} />
        </DetailSection>

        <DetailSection title={t('sections.team')}>
          <DetailField
            label={t('detail.assignedProjectManager')}
            value={project.assigned_project_manager ?? tCommon('noValue')}
          />
        </DetailSection>

        <DetailSection title={t('sections.notes')}>
          <DetailField label={t('detail.notes')} value={project.notes ?? t('noNotes')} />
        </DetailSection>

        <footer className="leads-drawer__footer">
          <button
            type="button"
            className="leads__button leads__button--ghost"
            onClick={() => onEdit(project)}
            disabled={archiving}
          >
            {t('editProject')}
          </button>
          <button
            type="button"
            className="leads__button leads__button--secondary"
            onClick={() => onArchive(project)}
            disabled={archiving}
          >
            {archiving ? t('archiving') : t('archiveProject')}
          </button>
        </footer>
      </aside>
    </div>
  );
}
