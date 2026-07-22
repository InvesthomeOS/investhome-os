'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import type { Route } from 'next';

import { Button, EmptyState, ErrorState, LoadingState, StatusChip, Tabs } from '@investhome/ui';

import { EntityDocumentsPanel } from '@/app/dashboard/_components/entity-documents-panel';
import { ProjectBudgetPanel } from '@/app/dashboard/projects/_components/project-budget-panel';
import { RelatedAssetsPanel } from '@/workspaces/marketing/components/related-assets-panel';
import {
  addProjectTeamMember,
  archiveProject,
  changeProjectStatus,
  fetchProjectConstruction,
  fetchProjectDetail,
  fetchProjectDetailActivity,
  fetchProjectFinancials,
  fetchProjectInvestors,
  fetchProjectLeasing,
  fetchProjectCampaigns,
  fetchProjectOverview,
  fetchProjectSales,
  fetchProjectSchedule,
  fetchProjectTeam,
  fetchProjectUnits,
  type ProjectRelatedCampaign,
  formatCompletion,
  formatLocation,
  formatMetricCurrency,
  formatMetricNumber,
  formatMetricPercent,
  formatShortDate,
  removeProjectTeamMember,
  restoreProject,
  searchProjectDirectoryUsers,
  updateProject,
  updateProjectTeamMember,
  type ProjectActivityListResponse,
  type ProjectConstructionResponse,
  type ProjectDetailShell,
  type ProjectDetailTabKey,
  type ProjectDirectoryUser,
  type ProjectFinancialsResponse,
  type ProjectInput,
  type ProjectInvestorsResponse,
  type ProjectLeasingResponse,
  type ProjectOverviewResponse,
  type ProjectSalesResponse,
  type ProjectScheduleResponse,
  type ProjectStatus,
  type ProjectTeamMember,
  type ProjectTeamRole,
  type ProjectUnitsResponse,
} from '@/lib/api/projects';
import { useProjectLabels } from '@/lib/i18n/project-labels';
import { isProjectDetailTab, projectDetailHref } from '@/lib/projects/project-detail-tabs';
import { ProjectFormModal } from './project-form-modal';

interface ProjectDetailWorkspaceProps {
  projectId: string;
  tab: string;
}

function MetricCard({
  label,
  value,
  note,
}: {
  label: string;
  value: string;
  note?: string | null;
}) {
  return (
    <article className="project-detail__metric">
      <p className="project-detail__metric-label">{label}</p>
      <p className="project-detail__metric-value">{value}</p>
      {note ? <p className="project-detail__metric-note">{note}</p> : null}
    </article>
  );
}

function SectionCard({
  title,
  children,
  empty,
}: {
  title: string;
  children: React.ReactNode;
  empty?: string | null;
}) {
  return (
    <section className="project-detail__card">
      <h3>{title}</h3>
      {empty ? <p className="project-detail__empty-inline">{empty}</p> : children}
    </section>
  );
}

export function ProjectDetailWorkspace({ projectId, tab }: ProjectDetailWorkspaceProps) {
  const t = useTranslations('projects');
  const tAi = useTranslations('marketing.ai.assistant');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const router = useRouter();
  const {
    getTypeLabel,
    getStatusLabel,
    getPriorityLabel,
    getStageLabel,
    getTeamRoleLabel,
    statusOptions,
  } = useProjectLabels();

  const activeTab: ProjectDetailTabKey = isProjectDetailTab(tab) ? tab : 'overview';

  const [shell, setShell] = useState<ProjectDetailShell | null>(null);
  const [shellLoading, setShellLoading] = useState(true);
  const [shellError, setShellError] = useState<string | null>(null);

  const [overview, setOverview] = useState<ProjectOverviewResponse | null>(null);
  const [relatedCampaigns, setRelatedCampaigns] = useState<ProjectRelatedCampaign[]>([]);
  const [financials, setFinancials] = useState<ProjectFinancialsResponse | null>(null);
  const [schedule, setSchedule] = useState<ProjectScheduleResponse | null>(null);
  const [construction, setConstruction] = useState<ProjectConstructionResponse | null>(null);
  const [units, setUnits] = useState<ProjectUnitsResponse | null>(null);
  const [sales, setSales] = useState<ProjectSalesResponse | null>(null);
  const [leasing, setLeasing] = useState<ProjectLeasingResponse | null>(null);
  const [investors, setInvestors] = useState<ProjectInvestorsResponse | null>(null);
  const [activity, setActivity] = useState<ProjectActivityListResponse | null>(null);
  const [team, setTeam] = useState<ProjectTeamMember[]>([]);
  const [tabLoading, setTabLoading] = useState(false);
  const [tabError, setTabError] = useState<string | null>(null);

  const [editOpen, setEditOpen] = useState(false);
  const [editSubmitting, setEditSubmitting] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [statusValue, setStatusValue] = useState<ProjectStatus | ''>('');
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState(false);

  const [userQuery, setUserQuery] = useState('');
  const [userResults, setUserResults] = useState<ProjectDirectoryUser[]>([]);
  const [userSearching, setUserSearching] = useState(false);
  const [selectedUser, setSelectedUser] = useState<ProjectDirectoryUser | null>(null);
  const [teamRole, setTeamRole] = useState<ProjectTeamRole>('project_manager');

  const [unitSearch, setUnitSearch] = useState('');

  const loadShell = useCallback(async () => {
    setShellLoading(true);
    setShellError(null);
    try {
      const data = await fetchProjectDetail(projectId);
      setShell(data);
      setStatusValue(data.project.project_status);
    } catch (error) {
      setShellError(error instanceof Error ? error.message : t('detailWorkspace.loadError'));
      setShell(null);
    } finally {
      setShellLoading(false);
    }
  }, [projectId, t]);

  useEffect(() => {
    void loadShell();
  }, [loadShell]);

  useEffect(() => {
    if (!shell) return;
    const visible = shell.navigation.find((item) => item.key === activeTab && item.visible);
    if (!visible) {
      router.replace(projectDetailHref(projectId, 'overview') as Route);
    }
  }, [shell, activeTab, projectId, router]);

  const loadTab = useCallback(async () => {
    if (!shell) return;
    setTabLoading(true);
    setTabError(null);
    try {
      switch (activeTab) {
        case 'overview': {
          const [overviewData, campaignsData] = await Promise.all([
            fetchProjectOverview(projectId),
            fetchProjectCampaigns(projectId).catch(() => ({ items: [], total: 0 })),
          ]);
          setOverview(overviewData);
          setRelatedCampaigns(campaignsData.items);
          break;
        }
        case 'financials':
          setFinancials(await fetchProjectFinancials(projectId));
          break;
        case 'schedule':
          setSchedule(await fetchProjectSchedule(projectId));
          break;
        case 'construction':
          setConstruction(await fetchProjectConstruction(projectId));
          break;
        case 'units':
          setUnits(await fetchProjectUnits(projectId, { search: unitSearch || undefined }));
          break;
        case 'sales':
          setSales(await fetchProjectSales(projectId));
          break;
        case 'leasing':
          setLeasing(await fetchProjectLeasing(projectId));
          break;
        case 'investors':
          setInvestors(await fetchProjectInvestors(projectId));
          break;
        case 'documents':
          break;
        case 'team': {
          const response = await fetchProjectTeam(projectId);
          setTeam(response.items);
          break;
        }
        case 'activity':
          setActivity(await fetchProjectDetailActivity(projectId));
          break;
        default:
          break;
      }
    } catch (error) {
      setTabError(error instanceof Error ? error.message : t('detailWorkspace.tabLoadError'));
    } finally {
      setTabLoading(false);
    }
  }, [activeTab, projectId, shell, t, unitSearch]);

  useEffect(() => {
    void loadTab();
  }, [loadTab]);

  useEffect(() => {
    if (activeTab !== 'team' || !shell?.permissions.can_manage_team) return;
    if (userQuery.trim().length < 1) {
      setUserResults([]);
      return;
    }
    const handle = window.setTimeout(() => {
      setUserSearching(true);
      void searchProjectDirectoryUsers(projectId, userQuery.trim())
        .then((response) => setUserResults(response.items))
        .catch(() => setUserResults([]))
        .finally(() => setUserSearching(false));
    }, 300);
    return () => window.clearTimeout(handle);
  }, [activeTab, projectId, shell?.permissions.can_manage_team, userQuery]);

  const visibleTabs = useMemo(() => {
    if (!shell) return [];
    return shell.navigation.filter((item) => item.visible);
  }, [shell]);

  const na = t('notAvailable');

  const runAction = async (action: () => Promise<unknown>) => {
    setActionBusy(true);
    setActionError(null);
    try {
      await action();
      await loadShell();
      await loadTab();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : t('detailWorkspace.actionError'));
    } finally {
      setActionBusy(false);
    }
  };

  if (shellLoading) {
    return <LoadingState label={t('detailWorkspace.loading')} />;
  }

  if (shellError || !shell) {
    return (
      <ErrorState
        title={t('detailWorkspace.loadError')}
        message={shellError ?? t('detailWorkspace.loadError')}
        action={
          <Button type="button" onClick={() => void loadShell()}>
            {tCommon('retry')}
          </Button>
        }
      />
    );
  }

  const project = shell.project;
  const permissions = shell.permissions;

  return (
    <div className="project-detail">
      <nav className="project-detail__crumbs" aria-label={t('detailWorkspace.breadcrumb')}>
        <ol>
          <li>
            <Link href={'/dashboard/projects' as Route}>{t('title')}</Link>
          </li>
          <li>
            <span>{project.project_name}</span>
          </li>
          <li aria-current="page">
            <span>{t(`detailWorkspace.tabs.${activeTab}`)}</span>
          </li>
        </ol>
      </nav>

      <header className="project-detail__header">
        <div className="project-detail__header-main">
          <div className="project-detail__badge-row">
            <StatusChip tone="info">{project.project_code}</StatusChip>
            <StatusChip>{getStatusLabel(project.project_status)}</StatusChip>
            {project.development_stage ? (
              <StatusChip tone="info">{getStageLabel(project.development_stage)}</StatusChip>
            ) : null}
            <StatusChip tone="info">{getPriorityLabel(project.priority)}</StatusChip>
            <StatusChip tone={shell.risk === 'critical' || shell.risk === 'high' ? 'danger' : 'info'}>
              {t(`risk.${shell.risk}`)}
            </StatusChip>
            {project.archived_at ? <StatusChip tone="warning">{t('archivedBadge')}</StatusChip> : null}
          </div>
          <h1>{project.project_name}</h1>
          <p className="project-detail__address">{formatLocation(project)}</p>
          <div className="project-detail__meta">
            <span>
              {t('completionLabel')}: {formatCompletion(project.completion_percentage, locale)}
            </span>
            <span>
              {t('detail.assignedProjectManager')}:{' '}
              {project.project_manager?.full_name || project.assigned_project_manager || '—'}
            </span>
            <span>
              {t('detail.targetCompletionDate')}:{' '}
              {formatShortDate(project.target_completion_date, locale)}
            </span>
            <span>
              {t('detailWorkspace.counts.alerts')}: {shell.alerts_count}
            </span>
            <span>
              {t('detailWorkspace.counts.milestones')}: {shell.milestones_count}
            </span>
          </div>
        </div>

        <div className="project-detail__actions">
          {permissions.can_edit ? (
            <Button type="button" variant="secondary" onClick={() => setEditOpen(true)}>
              {t('editProject')}
            </Button>
          ) : null}
          {permissions.can_manage_status && !project.archived_at ? (
            <div className="project-detail__status-action">
              <select
                value={statusValue}
                onChange={(event) => setStatusValue(event.target.value as ProjectStatus)}
                aria-label={t('changeStatus')}
              >
                {statusOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <Button
                type="button"
                variant="secondary"
                disabled={actionBusy || !statusValue || statusValue === project.project_status}
                onClick={() =>
                  void runAction(() =>
                    changeProjectStatus(project.id, statusValue as ProjectStatus),
                  )
                }
              >
                {t('applyStatus')}
              </Button>
            </div>
          ) : null}
          {permissions.can_archive && !project.archived_at ? (
            <Button
              type="button"
              variant="secondary"
              disabled={actionBusy}
              onClick={() => void runAction(() => archiveProject(project.id))}
            >
              {t('archive')}
            </Button>
          ) : null}
          {permissions.can_restore && project.archived_at ? (
            <Button
              type="button"
              disabled={actionBusy}
              onClick={() => void runAction(() => restoreProject(project.id))}
            >
              {t('restoreProject')}
            </Button>
          ) : null}
          {permissions.can_manage_team ? (
            <Button
              type="button"
              variant="secondary"
              onClick={() => router.push(projectDetailHref(project.id, 'team') as Route)}
            >
              {t('detailWorkspace.actions.addTeamMember')}
            </Button>
          ) : null}
          {shell.navigation.some((item) => item.key === 'documents' && item.visible) ? (
            <Button
              type="button"
              variant="secondary"
              onClick={() => router.push(projectDetailHref(project.id, 'documents') as Route)}
            >
              {t('detailWorkspace.actions.uploadDocument')}
            </Button>
          ) : null}
        </div>
      </header>

      {actionError ? <p className="project-detail__error">{actionError}</p> : null}

      <div className="project-detail__tabs">
        <Tabs
          activeId={activeTab}
          onChange={(next) => {
            if (isProjectDetailTab(next)) {
              router.push(projectDetailHref(projectId, next) as Route);
            }
          }}
          ariaLabel={t('detailWorkspace.tabsLabel')}
          tabs={visibleTabs.map((item) => ({
            id: item.key,
            label: t(`detailWorkspace.tabs.${item.key}`),
          }))}
        />
      </div>

      <div className="project-detail__body">
        {tabLoading ? <LoadingState label={t('detailWorkspace.loadingTab')} /> : null}
        {!tabLoading && tabError ? (
          <ErrorState
            title={t('detailWorkspace.tabLoadError')}
            message={tabError}
            action={
              <Button type="button" onClick={() => void loadTab()}>
                {tCommon('retry')}
              </Button>
            }
          />
        ) : null}

        {!tabLoading && !tabError && activeTab === 'overview' && overview ? (
          <div className="project-detail__overview">
            <div className="project-detail__metrics">
              <MetricCard
                label={t('detail.projectStatus')}
                value={getStatusLabel(project.project_status)}
              />
              <MetricCard
                label={t('completionLabel')}
                value={formatCompletion(project.completion_percentage, locale)}
              />
              <MetricCard
                label={t('detail.totalUnits')}
                value={formatMetricNumber(
                  { value: project.total_units, available: project.total_units != null, reason: null },
                  locale,
                  na,
                )}
              />
              <MetricCard
                label={t('detail.targetCompletionDate')}
                value={formatShortDate(project.target_completion_date, locale)}
              />
              <MetricCard label={t('detailWorkspace.risk')} value={t(`risk.${shell.risk}`)} />
              <MetricCard
                label={t('detail.developmentStage')}
                value={
                  project.development_stage ? getStageLabel(project.development_stage) : na
                }
              />
            </div>

            {overview.financial_snapshot ? (
              <div className="project-detail__metrics">
                <MetricCard
                  label={t('detail.totalDevelopmentCost')}
                  value={formatMetricCurrency(
                    overview.financial_snapshot.total_development_budget,
                    locale,
                    na,
                  )}
                />
                <MetricCard
                  label={t('detailWorkspace.budgetUsed')}
                  value={formatMetricCurrency(overview.financial_snapshot.budget_used, locale, na)}
                />
                <MetricCard
                  label={t('kpi.expectedRevenue')}
                  value={formatMetricCurrency(
                    overview.financial_snapshot.expected_revenue,
                    locale,
                    na,
                  )}
                />
                <MetricCard
                  label={t('kpi.expectedProfit')}
                  value={formatMetricCurrency(
                    overview.financial_snapshot.expected_profit,
                    locale,
                    na,
                  )}
                />
                <MetricCard
                  label={t('detail.currentProjectValue')}
                  value={formatMetricCurrency(
                    overview.financial_snapshot.current_value,
                    locale,
                    na,
                  )}
                />
              </div>
            ) : (
              <p className="project-detail__restricted">{t('restricted')}</p>
            )}

            <div className="project-detail__grid">
              <SectionCard title={t('detailWorkspace.sections.snapshot')}>
                <dl className="project-detail__dl">
                  <div>
                    <dt>{t('detail.projectType')}</dt>
                    <dd>{getTypeLabel(project.project_type)}</dd>
                  </div>
                  <div>
                    <dt>{t('detail.country')}</dt>
                    <dd>{project.country || '—'}</dd>
                  </div>
                  <div>
                    <dt>{t('detail.timezone')}</dt>
                    <dd>{project.timezone || '—'}</dd>
                  </div>
                  <div>
                    <dt>{t('detail.grossSquareFeet')}</dt>
                    <dd>{project.gross_square_feet ?? '—'}</dd>
                  </div>
                  <div>
                    <dt>{t('detail.netSellableSquareFeet')}</dt>
                    <dd>{project.net_sellable_square_feet ?? '—'}</dd>
                  </div>
                  <div>
                    <dt>{t('detail.ownershipEntity')}</dt>
                    <dd>{project.ownership_entity || '—'}</dd>
                  </div>
                </dl>
              </SectionCard>

              <SectionCard title={t('detailWorkspace.sections.schedule')}>
                <dl className="project-detail__dl">
                  <div>
                    <dt>{t('detailWorkspace.daysRemaining')}</dt>
                    <dd>
                      {overview.schedule.days_remaining != null
                        ? String(overview.schedule.days_remaining)
                        : na}
                    </dd>
                  </div>
                  <div>
                    <dt>{t('detailWorkspace.delayed')}</dt>
                    <dd>
                      {overview.schedule.is_delayed
                        ? t('detailWorkspace.yes')
                        : t('detailWorkspace.no')}
                    </dd>
                  </div>
                  <div>
                    <dt>{t('detail.startDate')}</dt>
                    <dd>{formatShortDate(project.start_date, locale)}</dd>
                  </div>
                  <div>
                    <dt>{t('detail.targetCompletionDate')}</dt>
                    <dd>{formatShortDate(project.target_completion_date, locale)}</dd>
                  </div>
                </dl>
              </SectionCard>

              <SectionCard
                title={t('panels.milestones')}
                empty={
                  overview.milestones.length === 0 ? t('detailWorkspace.empty.milestones') : null
                }
              >
                <ul className="project-detail__list">
                  {overview.milestones.map((item) => (
                    <li key={item.id}>
                      <strong>{item.title}</strong>
                      <span>{formatShortDate(item.date, locale)}</span>
                    </li>
                  ))}
                </ul>
              </SectionCard>

              <SectionCard
                title={t('panels.alerts')}
                empty={overview.alerts.length === 0 ? t('detailWorkspace.empty.alerts') : null}
              >
                <ul className="project-detail__list">
                  {overview.alerts.map((item) => (
                    <li key={item.id}>
                      <strong>{item.title}</strong>
                      <span>{item.message}</span>
                    </li>
                  ))}
                </ul>
              </SectionCard>

              <SectionCard
                title={t('sections.team')}
                empty={
                  overview.team.length === 0 ? t('detailWorkspace.empty.team') : null
                }
              >
                <ul className="project-detail__list">
                  {overview.team.map((member) => (
                    <li key={member.id}>
                      <strong>{member.user?.full_name || member.user_id}</strong>
                      <span>{getTeamRoleLabel(member.role)}</span>
                    </li>
                  ))}
                </ul>
              </SectionCard>

              <SectionCard
                title={t('panels.activity')}
                empty={
                  overview.activity.length === 0 ? t('detailWorkspace.empty.activity') : null
                }
              >
                <ul className="project-detail__list">
                  {overview.activity.map((item) => (
                    <li key={item.id}>
                      <strong>{item.title}</strong>
                      <span>
                        {item.actor || '—'} · {formatShortDate(item.created_at, locale)}
                      </span>
                    </li>
                  ))}
                </ul>
              </SectionCard>

              <SectionCard
                title={t('detailWorkspace.relatedCampaigns')}
                empty={
                  relatedCampaigns.length === 0 ? t('detailWorkspace.relatedCampaignsEmpty') : null
                }
              >
                <div style={{ marginBottom: '0.75rem' }}>
                  <Link
                    href={
                      `/workspaces/marketing/ai/assistant?mode=content_draft&projectId=${projectId}` as Route
                    }
                    className="button button--secondary"
                  >
                    {tAi('contextualEntry')}
                  </Link>
                </div>
                <ul className="project-detail__list">
                  {relatedCampaigns.map((campaign) => (
                    <li key={campaign.id}>
                      <Link href={`/workspaces/marketing/campaigns/${campaign.id}` as Route}>
                        <strong>{campaign.name}</strong>
                      </Link>
                      <span>
                        {campaign.status}
                        {campaign.budget_amount
                          ? ` · ${campaign.budget_amount} ${campaign.budget_currency ?? ''}`
                          : ''}
                      </span>
                    </li>
                  ))}
                </ul>
              </SectionCard>
            </div>
          </div>
        ) : null}

        {!tabLoading && !tabError && activeTab === 'financials' && financials ? (
          <ProjectBudgetPanel
            projectId={projectId}
            financials={financials}
            locale={locale}
            canEditFinancials={permissions?.can_edit_financial}
          />
        ) : null}

        {!tabLoading && !tabError && activeTab === 'schedule' && schedule ? (
          <div className="project-detail__stack">
            <div className="project-detail__metrics">
              <MetricCard
                label={t('detailWorkspace.daysRemaining')}
                value={schedule.days_remaining != null ? String(schedule.days_remaining) : na}
              />
              <MetricCard
                label={t('detailWorkspace.daysDelayed')}
                value={schedule.days_delayed != null ? String(schedule.days_delayed) : '0'}
              />
              <MetricCard
                label={t('detailWorkspace.delayed')}
                value={
                  schedule.is_delayed ? t('detailWorkspace.yes') : t('detailWorkspace.no')
                }
              />
            </div>
            <SectionCard title={t('detailWorkspace.sections.keyDates')}>
              <dl className="project-detail__dl">
                {Object.entries(schedule.key_dates).map(([key, value]) => (
                  <div key={key}>
                    <dt>{t(`detailWorkspace.dates.${key}` as 'detailWorkspace.dates.acquisition')}</dt>
                    <dd>{formatShortDate(value, locale)}</dd>
                  </div>
                ))}
              </dl>
            </SectionCard>
            <SectionCard
              title={t('panels.milestones')}
              empty={
                schedule.milestones.length === 0 ? t('detailWorkspace.empty.milestones') : null
              }
            >
              <ul className="project-detail__timeline">
                {schedule.milestones.map((item) => (
                  <li key={item.id}>
                    <span className="project-detail__timeline-date">
                      {formatShortDate(item.date, locale)}
                    </span>
                    <div>
                      <strong>{item.title}</strong>
                      <p>{item.status}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </SectionCard>
            {schedule.risks.length > 0 ? (
              <SectionCard title={t('detailWorkspace.sections.scheduleRisks')}>
                <ul className="project-detail__list">
                  {schedule.risks.map((risk) => (
                    <li key={risk}>{risk}</li>
                  ))}
                </ul>
              </SectionCard>
            ) : null}
          </div>
        ) : null}

        {!tabLoading && !tabError && activeTab === 'construction' && construction ? (
          <div className="project-detail__stack">
            <div className="project-detail__metrics">
              <MetricCard
                label={t('completionLabel')}
                value={formatCompletion(construction.completion_percentage, locale)}
              />
              <MetricCard
                label={t('detail.developmentStage')}
                value={
                  construction.development_stage
                    ? getStageLabel(construction.development_stage as never)
                    : na
                }
              />
              <MetricCard
                label={t('detailWorkspace.budgetUtilization')}
                value={formatMetricPercent(construction.budget_utilization, locale, na)}
              />
              <MetricCard label={t('detailWorkspace.risk')} value={t(`risk.${construction.risk}`)} />
            </div>
            {construction.warnings.map((warning) => (
              <EmptyState key={warning} title={t('detailWorkspace.empty.construction')} description={warning} />
            ))}
          </div>
        ) : null}

        {!tabLoading && !tabError && activeTab === 'units' && units ? (
          <div className="project-detail__stack">
            <div className="project-detail__toolbar">
              <input
                value={unitSearch}
                onChange={(event) => setUnitSearch(event.target.value)}
                placeholder={t('detailWorkspace.unitSearch')}
                aria-label={t('detailWorkspace.unitSearch')}
              />
              <Button type="button" variant="secondary" onClick={() => void loadTab()}>
                {t('refresh')}
              </Button>
            </div>
            <div className="project-detail__metrics">
              {Object.entries(units.summary).map(([key, metric]) => (
                <MetricCard
                  key={key}
                  label={t(`detailWorkspace.unitSummary.${key}` as 'detailWorkspace.unitSummary.total_units')}
                  value={formatMetricNumber(metric, locale, na)}
                />
              ))}
            </div>
            {units.items.length === 0 ? (
              <EmptyState
                title={t('detailWorkspace.empty.units')}
                description={units.warnings[0] ?? t('detailWorkspace.empty.unitsHint')}
              />
            ) : (
              <div className="project-detail__table-wrap">
                <table className="project-detail__table">
                  <thead>
                    <tr>
                      <th>{t('detailWorkspace.unitColumns.unit')}</th>
                      <th>{t('detailWorkspace.unitColumns.type')}</th>
                      <th>{t('detailWorkspace.unitColumns.status')}</th>
                      <th>{t('detailWorkspace.unitColumns.sales')}</th>
                      <th>{t('detailWorkspace.unitColumns.leasing')}</th>
                      <th>{t('detailWorkspace.unitColumns.price')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {units.items.map((item) => (
                      <tr key={String(item.id)}>
                        <td>{String(item.unit)}</td>
                        <td>{String(item.type ?? '—')}</td>
                        <td>{String(item.availability_status ?? '—')}</td>
                        <td>{String(item.sales_status ?? '—')}</td>
                        <td>{String(item.leasing_status ?? '—')}</td>
                        <td>
                          {item.price_available
                            ? formatMetricCurrency(
                                {
                                  value: item.price as string | number | null,
                                  available: true,
                                  reason: null,
                                },
                                locale,
                                na,
                              )
                            : na}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ) : null}

        {!tabLoading && !tabError && activeTab === 'sales' && sales ? (
          <div className="project-detail__stack">
            <div className="project-detail__metrics">
              {Object.entries(sales.summary).map(([key, metric]) => (
                <MetricCard
                  key={key}
                  label={t(`detailWorkspace.salesSummary.${key}` as 'detailWorkspace.salesSummary.sold_units')}
                  value={
                    key.includes('price') || key.includes('volume')
                      ? formatMetricCurrency(metric, locale, na)
                      : key.includes('rate')
                        ? formatMetricPercent(metric, locale, na)
                        : formatMetricNumber(metric, locale, na)
                  }
                />
              ))}
            </div>
            {sales.opportunities.length === 0 ? (
              <EmptyState
                title={t('detailWorkspace.empty.sales')}
                description={sales.warnings[0] ?? t('detailWorkspace.empty.salesHint')}
              />
            ) : (
              <ul className="project-detail__list">
                {sales.opportunities.map((item) => (
                  <li key={String(item.id)}>
                    <strong>{String(item.opportunity_code)}</strong>
                    <span>
                      {String(item.stage ?? '—')} ·{' '}
                      <Link href={(item.href as string) as Route}>{t('view')}</Link>
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : null}

        {!tabLoading && !tabError && activeTab === 'leasing' && leasing ? (
          <div className="project-detail__stack">
            <div className="project-detail__metrics">
              {Object.entries(leasing.summary).map(([key, metric]) => (
                <MetricCard
                  key={key}
                  label={t(`detailWorkspace.leasingSummary.${key}` as 'detailWorkspace.leasingSummary.occupied_units')}
                  value={
                    key.includes('rate')
                      ? formatMetricPercent(metric, locale, na)
                      : key.includes('rent')
                        ? formatMetricCurrency(metric, locale, na)
                        : formatMetricNumber(metric, locale, na)
                  }
                  note={!metric.available ? metric.reason : null}
                />
              ))}
            </div>
            {leasing.warnings.map((warning) => (
              <p key={warning} className="project-detail__note">
                {warning}
              </p>
            ))}
            {leasing.items.length === 0 ? (
              <EmptyState title={t('detailWorkspace.empty.leasing')} />
            ) : (
              <ul className="project-detail__list">
                {leasing.items.map((item) => (
                  <li key={String(item.id)}>
                    <strong>{String(item.unit)}</strong>
                    <span>{String(item.leasing_status)}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : null}

        {!tabLoading && !tabError && activeTab === 'investors' && investors ? (
          <div className="project-detail__stack">
            {investors.items.length === 0 ? (
              <EmptyState
                title={t('detailWorkspace.empty.investors')}
                description={investors.warnings[0]}
              />
            ) : (
              <ul className="project-detail__list">
                {investors.items.map((item) => (
                  <li key={String(item.commitment_id)}>
                    <strong>{String(item.investor_name)}</strong>
                    <span>
                      {String(item.status ?? '—')} ·{' '}
                      {investors.financial_access
                        ? formatMetricCurrency(
                            {
                              value: item.committed_amount as string | number | null,
                              available: item.committed_amount != null,
                              reason: null,
                            },
                            locale,
                            na,
                          )
                        : t('restricted')}{' '}
                      · <Link href={(item.href as string) as Route}>{t('view')}</Link>
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : null}

        {!tabLoading && !tabError && activeTab === 'documents' ? (
          <div className="project-detail__stack">
            <EntityDocumentsPanel entityType="project" entityId={projectId} projectId={projectId} />
            <RelatedAssetsPanel projectId={projectId} />
          </div>
        ) : null}

        {!tabLoading && !tabError && activeTab === 'team' ? (
          <div className="project-detail__stack">
            {permissions.can_manage_team ? (
              <section className="project-detail__card">
                <h3>{t('detailWorkspace.actions.addTeamMember')}</h3>
                <div className="project-detail__team-form">
                  <label>
                    {t('detailWorkspace.userSearch')}
                    <input
                      value={userQuery}
                      onChange={(event) => {
                        setUserQuery(event.target.value);
                        setSelectedUser(null);
                      }}
                      placeholder={t('detailWorkspace.userSearchPlaceholder')}
                    />
                  </label>
                  {userSearching ? <p>{tCommon('loading')}</p> : null}
                  {userResults.length > 0 && !selectedUser ? (
                    <ul className="project-detail__user-results">
                      {userResults.map((result) => (
                        <li key={result.id}>
                          <button type="button" onClick={() => setSelectedUser(result)}>
                            <strong>{result.full_name}</strong>
                            <span>
                              {result.email}
                              {result.job_title ? ` · ${result.job_title}` : ''}
                            </span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                  {selectedUser ? (
                    <p className="project-detail__note">
                      {selectedUser.full_name} ({selectedUser.email})
                    </p>
                  ) : null}
                  <label>
                    {t('detailWorkspace.teamRole')}
                    <select
                      value={teamRole}
                      onChange={(event) => setTeamRole(event.target.value as ProjectTeamRole)}
                    >
                      {[
                        'project_manager',
                        'development_manager',
                        'construction_manager',
                        'finance',
                        'sales',
                        'leasing',
                        'operations',
                      ].map((role) => (
                        <option key={role} value={role}>
                          {getTeamRoleLabel(role as ProjectTeamRole)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <Button
                    type="button"
                    disabled={!selectedUser || actionBusy}
                    onClick={() =>
                      void runAction(async () => {
                        if (!selectedUser) return;
                        await addProjectTeamMember(projectId, {
                          user_id: selectedUser.id,
                          role: teamRole,
                          is_primary: false,
                        });
                        setSelectedUser(null);
                        setUserQuery('');
                        setUserResults([]);
                      })
                    }
                  >
                    {t('detailWorkspace.actions.addTeamMember')}
                  </Button>
                </div>
              </section>
            ) : null}

            {team.length === 0 ? (
              <EmptyState title={t('detailWorkspace.empty.team')} />
            ) : (
              <ul className="project-detail__list">
                {team.map((member) => (
                  <li key={member.id} className="project-detail__team-row">
                    <div>
                      <strong>{member.user?.full_name || member.user_id}</strong>
                      <span>
                        {getTeamRoleLabel(member.role)}
                        {member.is_primary ? ` · ${t('detailWorkspace.primary')}` : ''}
                        {` · ${member.status}`}
                      </span>
                    </div>
                    {permissions.can_manage_team ? (
                      <div className="project-detail__row-actions">
                        {!member.is_primary ? (
                          <Button
                            type="button"
                            variant="secondary"
                            onClick={() =>
                              void runAction(() =>
                                updateProjectTeamMember(projectId, member.id, {
                                  is_primary: true,
                                }),
                              )
                            }
                          >
                            {t('detailWorkspace.actions.setPrimary')}
                          </Button>
                        ) : null}
                        <Button
                          type="button"
                          variant="secondary"
                          onClick={() =>
                            void runAction(() => removeProjectTeamMember(projectId, member.id))
                          }
                        >
                          {t('detailWorkspace.actions.remove')}
                        </Button>
                      </div>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : null}

        {!tabLoading && !tabError && activeTab === 'activity' && activity ? (
          <div className="project-detail__stack">
            {activity.items.length === 0 ? (
              <EmptyState title={t('detailWorkspace.empty.activity')} />
            ) : (
              <ul className="project-detail__timeline">
                {activity.items.map((item) => (
                  <li key={item.id}>
                    <span className="project-detail__timeline-date">
                      {formatShortDate(item.created_at, locale)}
                    </span>
                    <div>
                      <strong>{item.title}</strong>
                      <p>
                        {item.actor || '—'} · {item.type}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : null}
      </div>

      <ProjectFormModal
        mode={editOpen ? 'edit' : null}
        project={editOpen ? project : null}
        submitting={editSubmitting}
        error={editError}
        canEditFinancials={permissions.can_edit_financial}
        onClose={() => {
          setEditOpen(false);
          setEditError(null);
        }}
        onSubmit={(input: ProjectInput) => {
          void (async () => {
            setEditSubmitting(true);
            setEditError(null);
            try {
              await updateProject(project.id, input);
              setEditOpen(false);
              await loadShell();
              await loadTab();
            } catch (error) {
              setEditError(error instanceof Error ? error.message : t('saveError'));
            } finally {
              setEditSubmitting(false);
            }
          })();
        }}
      />
    </div>
  );
}
