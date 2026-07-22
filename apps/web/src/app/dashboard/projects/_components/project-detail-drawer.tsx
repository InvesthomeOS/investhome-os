'use client';

import { useCallback, useEffect, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import {
  fetchProjectStatusTransitions,
  formatCompletion,
  formatCurrency,
  formatDate,
  formatLocation,
  formatNumber,
  formatPercent,
  formatShortDate,
  type Project,
  type ProjectStatus,
  type ProjectTeamMemberInput,
  type ProjectTeamRole,
} from '@/lib/api/projects';
import { EntityActivityTimeline } from '@/app/dashboard/_components/entity-activity-timeline';
import { EntityDocumentsPanel } from '@/app/dashboard/_components/entity-documents-panel';
import { useProjectLabels } from '@/lib/i18n/project-labels';

interface ProjectDetailDrawerProps {
  project: Project | null;
  archiving: boolean;
  statusUpdating: boolean;
  teamUpdating: boolean;
  canUpdate: boolean;
  canArchive: boolean;
  canRestore: boolean;
  canManageStatus: boolean;
  canViewFinancials: boolean;
  canViewTeam: boolean;
  canManageTeam: boolean;
  onClose: () => void;
  onEdit: (project: Project) => void;
  onArchive: (project: Project) => void;
  onRestore: (project: Project) => void;
  onStatusChange: (project: Project, status: ProjectStatus) => void;
  onAddTeamMember: (project: Project, input: ProjectTeamMemberInput) => void;
  onRemoveTeamMember: (project: Project, memberId: string) => void;
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

function CompletionBar({ value, locale }: { value: string | null; locale: string }) {
  const amount = value ? Number(value) : 0;
  const pct = Number.isNaN(amount) ? 0 : Math.min(100, Math.max(0, amount));

  return (
    <div className="projects__progress">
      <div className="projects__progress-track">
        <div className="projects__progress-bar" style={{ width: `${pct}%` }} />
      </div>
      <span className="projects__progress-label">{formatCompletion(value, locale)}</span>
    </div>
  );
}

export function ProjectDetailDrawer({
  project,
  archiving,
  statusUpdating,
  teamUpdating,
  canUpdate,
  canArchive,
  canRestore,
  canManageStatus,
  canViewFinancials,
  canViewTeam,
  canManageTeam,
  onClose,
  onEdit,
  onArchive,
  onRestore,
  onStatusChange,
  onAddTeamMember,
  onRemoveTeamMember,
}: ProjectDetailDrawerProps) {
  const t = useTranslations('projects');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { getTypeLabel, getDevelopmentTypeLabel, getStatusLabel, getPriorityLabel, getStageLabel, getTeamRoleLabel, teamRoleOptions } =
    useProjectLabels();

  const [allowedStatuses, setAllowedStatuses] = useState<ProjectStatus[]>([]);
  const [transitionsLoading, setTransitionsLoading] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState<ProjectStatus | ''>('');
  const [teamUserId, setTeamUserId] = useState('');
  const [teamRole, setTeamRole] = useState<ProjectTeamRole>('project_manager');

  const loadTransitions = useCallback(async (projectId: string) => {
    setTransitionsLoading(true);
    try {
      const response = await fetchProjectStatusTransitions(projectId);
      setAllowedStatuses(response.allowed);
    } catch {
      setAllowedStatuses([]);
    } finally {
      setTransitionsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (project && canManageStatus) {
      setSelectedStatus('');
      void loadTransitions(project.id);
    } else {
      setAllowedStatuses([]);
    }
  }, [project, canManageStatus, loadTransitions]);

  useEffect(() => {
    setTeamUserId('');
    setTeamRole('project_manager');
  }, [project?.id]);

  if (!project) {
    return null;
  }

  const handleApplyStatus = () => {
    if (!selectedStatus) return;
    onStatusChange(project, selectedStatus);
  };

  const handleAddTeamMember = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedUserId = teamUserId.trim();
    if (!trimmedUserId) return;
    onAddTeamMember(project, { user_id: trimmedUserId, role: teamRole });
    setTeamUserId('');
  };

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
            {project.archived_at && (
              <span className="ih-badge ih-badge--warning">{t('archivedBadge')}</span>
            )}
          </div>
          <button type="button" className="leads__button leads__button--ghost" onClick={onClose}>
            {tCommon('close')}
          </button>
        </header>

        <section className="leads-drawer__section">
          <div className="projects__badge-row">
            <span className="leads__status">{getStatusLabel(project.project_status)}</span>
            <span className="ih-badge ih-badge--info">{getPriorityLabel(project.priority)}</span>
            {project.development_stage && (
              <span className="ih-badge ih-badge--info">{getStageLabel(project.development_stage)}</span>
            )}
          </div>
          <div className="projects__completion-row">
            <span className="leads__muted">{t('completionLabel')}</span>
            <CompletionBar value={project.completion_percentage} locale={locale} />
          </div>
        </section>

        {canManageStatus && (
          <section className="leads-drawer__section">
            <h3>{t('changeStatus')}</h3>
            {transitionsLoading ? (
              <p className="leads__state">{tCommon('loading')}</p>
            ) : allowedStatuses.length === 0 ? (
              <p className="leads__state">{tCommon('noValue')}</p>
            ) : (
              <div className="projects__status-row">
                <select
                  value={selectedStatus}
                  onChange={(event) => setSelectedStatus(event.target.value as ProjectStatus)}
                >
                  <option value="">{tCommon('noValue')}</option>
                  {allowedStatuses.map((status) => (
                    <option key={status} value={status}>
                      {getStatusLabel(status)}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="leads__button leads__button--secondary"
                  disabled={statusUpdating || !selectedStatus}
                  onClick={handleApplyStatus}
                >
                  {statusUpdating ? t('saving') : t('applyStatus')}
                </button>
              </div>
            )}
          </section>
        )}

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
          <DetailField label={t('detail.priority')} value={getPriorityLabel(project.priority)} />
          <DetailField
            label={t('detail.developmentStage')}
            value={project.development_stage ? getStageLabel(project.development_stage) : tCommon('noValue')}
          />
          <DetailField
            label={t('detail.ownershipEntity')}
            value={project.ownership_entity ?? tCommon('noValue')}
          />
          <DetailField label={t('detail.currency')} value={project.currency} />
          <DetailField
            label={t('detail.description')}
            value={project.description ?? t('noDescription')}
          />
        </DetailSection>

        <DetailSection title={t('sections.location')}>
          <DetailField label={t('detail.location')} value={formatLocation(project)} />
          <DetailField label={t('detail.address')} value={project.address ?? tCommon('noValue')} />
          <DetailField
            label={t('detail.addressLine2')}
            value={project.address_line2 ?? tCommon('noValue')}
          />
          <DetailField label={t('detail.city')} value={project.city ?? tCommon('noValue')} />
          <DetailField label={t('detail.state')} value={project.state ?? tCommon('noValue')} />
          <DetailField
            label={t('detail.postalCode')}
            value={project.postal_code ?? tCommon('noValue')}
          />
          <DetailField label={t('detail.country')} value={project.country ?? tCommon('noValue')} />
          <DetailField
            label={t('detail.timezone')}
            value={project.timezone ?? tCommon('noValue')}
          />
          <DetailField
            label={t('detail.latitude')}
            value={project.latitude ?? tCommon('noValue')}
          />
          <DetailField
            label={t('detail.longitude')}
            value={project.longitude ?? tCommon('noValue')}
          />
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
          <DetailField
            label={t('detail.netSellableSquareFeet')}
            value={formatNumber(project.net_sellable_square_feet, locale)}
          />
          <DetailField
            label={t('detail.lotSize')}
            value={project.lot_size ?? tCommon('noValue')}
          />
        </DetailSection>

        {canViewFinancials && (
          <>
            <DetailSection title={t('sections.financialSummary')}>
              <DetailField
                label={t('detail.acquisitionPrice')}
                value={formatCurrency(project.acquisition_price, locale)}
              />
              <DetailField
                label={t('detail.landCost')}
                value={formatCurrency(project.land_cost, locale)}
              />
              <DetailField
                label={t('detail.constructionBudget')}
                value={formatCurrency(project.construction_budget, locale)}
              />
              <DetailField
                label={t('detail.softCostBudget')}
                value={formatCurrency(project.soft_cost_budget, locale)}
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
          </>
        )}

        <DetailSection title={t('sections.timeline')}>
          <DetailField
            label={t('detail.acquisitionDate')}
            value={formatShortDate(project.acquisition_date, locale)}
          />
          <DetailField
            label={t('detail.startDate')}
            value={formatShortDate(project.start_date, locale)}
          />
          <DetailField
            label={t('detail.actualStartDate')}
            value={formatShortDate(project.actual_start_date, locale)}
          />
          <DetailField
            label={t('detail.targetCompletionDate')}
            value={formatShortDate(project.target_completion_date, locale)}
          />
          <DetailField
            label={t('detail.actualCompletionDate')}
            value={formatShortDate(project.actual_completion_date, locale)}
          />
          <DetailField
            label={t('detail.estimatedClosingDate')}
            value={formatShortDate(project.estimated_closing_date, locale)}
          />
          <DetailField label={t('detail.created')} value={formatDate(project.created_at, locale)} />
          <DetailField label={t('detail.updated')} value={formatDate(project.updated_at, locale)} />
        </DetailSection>

        <section className="leads-drawer__section">
          <h3>{t('sections.team')}</h3>
          <dl className="leads-drawer__grid">
            <DetailField
              label={t('detail.assignedProjectManager')}
              value={project.assigned_project_manager ?? tCommon('noValue')}
            />
          </dl>

          {canViewTeam && (
            <div className="projects__team">
              {project.team_summary.length === 0 ? (
                <p className="leads__state">{t('team.empty')}</p>
              ) : (
                <ul className="projects__team-list">
                  {project.team_summary.map((member) => (
                    <li key={member.id} className="projects__team-item">
                      <div>
                        <strong>{member.user?.full_name ?? member.user_id}</strong>
                        <span className="leads__muted"> · {getTeamRoleLabel(member.role)}</span>
                        {member.is_primary && (
                          <span className="ih-badge ih-badge--info">{t('team.primary')}</span>
                        )}
                      </div>
                      {canManageTeam && (
                        <button
                          type="button"
                          className="leads__button leads__button--ghost leads__button--sm"
                          disabled={teamUpdating}
                          onClick={() => onRemoveTeamMember(project, member.id)}
                        >
                          {t('team.remove')}
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
              )}

              {canManageTeam && (
                <form className="projects__team-form" onSubmit={handleAddTeamMember}>
                  <label className="leads__field">
                    <span>{t('team.userId')}</span>
                    <input
                      value={teamUserId}
                      placeholder="00000000-0000-0000-0000-000000000000"
                      onChange={(event) => setTeamUserId(event.target.value)}
                    />
                  </label>
                  <label className="leads__field">
                    <span>{t('team.role')}</span>
                    <select
                      value={teamRole}
                      onChange={(event) => setTeamRole(event.target.value as ProjectTeamRole)}
                    >
                      {teamRoleOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    type="submit"
                    className="leads__button leads__button--secondary"
                    disabled={teamUpdating || !teamUserId.trim()}
                  >
                    {t('team.add')}
                  </button>
                </form>
              )}
            </div>
          )}
        </section>

        <DetailSection title={t('sections.notes')}>
          <DetailField label={t('detail.notes')} value={project.notes ?? t('noNotes')} />
        </DetailSection>

        <EntityDocumentsPanel entityType="project" entityId={project.id} projectId={project.id} />

        <EntityActivityTimeline entityType="project" entityId={project.id} />

        <footer className="leads-drawer__footer">
          {canUpdate && (
            <button
              type="button"
              className="leads__button leads__button--ghost"
              onClick={() => onEdit(project)}
              disabled={archiving}
            >
              {t('editProject')}
            </button>
          )}
          {canArchive && !project.archived_at && (
            <button
              type="button"
              className="leads__button leads__button--secondary"
              onClick={() => onArchive(project)}
              disabled={archiving}
            >
              {archiving ? t('archiving') : t('archiveProject')}
            </button>
          )}
          {canRestore && project.archived_at && (
            <button
              type="button"
              className="leads__button leads__button--secondary"
              onClick={() => onRestore(project)}
              disabled={archiving}
            >
              {archiving ? t('restoring') : t('restoreProject')}
            </button>
          )}
        </footer>
      </aside>
    </div>
  );
}
