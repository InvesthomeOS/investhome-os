'use client';

import type { Route } from 'next';
import { Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';

import {
  Button,
  Input,
  KpiCard,
  ProgressBar,
  SegmentedControl,
  Select,
  StatusChip,
} from '@investhome/ui';

import { useScreenshotDashboardInteractions } from '@/app/dashboard/_components/screenshot-dashboard-interactions';
import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';
import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';
import {
  createProject,
  fetchProjectStats,
  fetchProjects,
  formatLocation,
  formatShortDate,
  updateProject,
  type Project,
  type ProjectInput,
  type ProjectStats,
} from '@/lib/api/projects';
import { useProjectLabels } from '@/lib/i18n/project-labels';

import { ProjectFormModal } from '../project-form-modal';
import { projectCompletion, projectValue } from '../g4/project-types';
import {
  activityIcon,
  budgetDonutGradient,
  coverSceneFor,
  deriveAiRisk,
  deriveKpis,
  deriveNextMilestoneKey,
  deriveRail,
  EMPTY_DS_FILTERS,
  filterProjects,
  formatCompactCurrency,
  initials,
  projectedReturn,
  priorityTone,
  statusTone,
  teamAvatars,
  type DsFilters,
  type ProjectsKpiKey,
  type ProjectsViewMode,
} from './projects-ds-model';

import './projects-ds.css';

const PAGE_SIZE = 10;

const KPI_ICONS: Record<ProjectsKpiKey, IhIconName> = {
  total: 'projects',
  active: 'target',
  portfolioValue: 'trendingUp',
  constructionBudget: 'barChart',
  completionRate: 'clock',
};

function ProjectCover({ scene }: { scene: string }) {
  return (
    <div className={`proj-ds__cover is-${scene}`} aria-hidden="true">
      <i />
      <i />
      <i />
      <i />
      <i />
    </div>
  );
}

function ProjectsDsWorkspaceInner() {
  const t = useTranslations('projects');
  const tDs = useTranslations('projects.ds');
  const locale = useLocale();
  const router = useRouter();
  const { user } = useAuth();
  const { openAi } = useScreenshotDashboardInteractions();
  const {
    getStatusLabel,
    getTypeLabel,
    getStageLabel,
    getPriorityLabel,
    statusOptions,
    typeOptions,
    priorityOptions,
  } = useProjectLabels();

  const canView = user ? hasPermission(user, 'projects', 'view') : false;
  const canCreate = user ? hasPermission(user, 'projects', 'create') : false;
  const canUpdate = user ? hasPermission(user, 'projects', 'update') : false;

  const [projects, setProjects] = useState<Project[]>([]);
  const [stats, setStats] = useState<ProjectStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<DsFilters>(EMPTY_DS_FILTERS);
  const [view, setView] = useState<ProjectsViewMode>('card');
  const [page, setPage] = useState(1);
  const [formMode, setFormMode] = useState<'create' | 'edit' | null>(null);
  const [editProject, setEditProject] = useState<Project | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [menuId, setMenuId] = useState<string | null>(null);
  const [showMoreFilters, setShowMoreFilters] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [list, nextStats] = await Promise.all([
        fetchProjects({
          page: 1,
          page_size: 100,
          sort_by: 'updated_at',
          sort_order: 'desc',
          include_archived: false,
        }),
        fetchProjectStats().catch(() => null),
      ]);
      setProjects(list.items);
      setStats(nextStats);
    } catch {
      setError(t('loadError'));
      setProjects([]);
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    if (!canView) {
      setLoading(false);
      return;
    }
    void load();
  }, [canView, load]);

  const filtered = useMemo(() => filterProjects(projects, filters), [projects, filters]);

  const kpis = useMemo(() => deriveKpis(projects, stats, locale), [projects, stats, locale]);

  const rail = useMemo(
    () => deriveRail(filtered, locale, getStatusLabel),
    [filtered, locale, getStatusLabel],
  );

  const cities = useMemo(() => {
    const set = new Set<string>();
    for (const p of projects) {
      if (p.city) set.add(p.city);
    }
    return [...set].sort((a, b) => a.localeCompare(b));
  }, [projects]);

  const managers = useMemo(() => {
    const set = new Set<string>();
    for (const p of projects) {
      const name = p.project_manager?.full_name ?? p.assigned_project_manager;
      if (name) set.add(name);
    }
    return [...set].sort((a, b) => a.localeCompare(b));
  }, [projects]);

  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageSafe = Math.min(page, pages);
  const pageItems = filtered.slice((pageSafe - 1) * PAGE_SIZE, pageSafe * PAGE_SIZE);
  const heroCards = filtered.slice(0, 8);

  const openProject = (project: Project) => {
    router.push(`/dashboard/projects/${project.id}/overview` as Route);
  };

  const clearFilters = () => {
    setFilters(EMPTY_DS_FILTERS);
    setPage(1);
    setShowMoreFilters(false);
  };

  const handleExport = () => {
    const header = [
      'project',
      'location',
      'status',
      'progress',
      'budget',
      'manager',
      'updated',
    ].join(',');
    const rows = filtered.map((p) =>
      [
        JSON.stringify(p.project_name),
        JSON.stringify(formatLocation(p)),
        p.project_status,
        projectCompletion(p),
        p.construction_budget ?? p.total_development_cost ?? '',
        JSON.stringify(
          p.project_manager?.full_name ?? p.assigned_project_manager ?? '',
        ),
        p.updated_at,
      ].join(','),
    );
    const blob = new Blob([[header, ...rows].join('\n')], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'projects-export.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleSubmit = async (input: ProjectInput) => {
    setSubmitting(true);
    setActionError(null);
    try {
      if (formMode === 'edit' && editProject) {
        await updateProject(editProject.id, input);
      } else {
        await createProject(input);
      }
      setFormMode(null);
      setEditProject(null);
      await load();
    } catch {
      setActionError(t('saveError'));
    } finally {
      setSubmitting(false);
    }
  };

  if (!canView) {
    return (
      <div className="proj-ds" data-testid="projects-ds-workspace">
        <div className="proj-ds__empty">{tDs('accessDenied')}</div>
      </div>
    );
  }

  return (
    <div className="proj-ds" data-testid="projects-ds-workspace">
      <header className="proj-ds__header">
        <div>
          <h1>{tDs('title')}</h1>
          <p>{tDs('subtitle')}</p>
        </div>
        <div className="proj-ds__header-actions">
          <Button variant="secondary" size="sm" onClick={handleExport}>
            <IhIcon name="inbox" size={13} />
            {tDs('actions.export')}
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => openAi(tDs('ai.openPrompt'))}
          >
            <IhIcon name="sparkles" size={13} />
            {tDs('actions.ai')}
          </Button>
          {canCreate ? (
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                setFormMode('create');
                setEditProject(null);
                setActionError(null);
              }}
              data-testid="projects-ds-new"
            >
              <IhIcon name="plus" size={13} />
              {tDs('actions.new')}
            </Button>
          ) : null}
        </div>
      </header>

      <section className="proj-ds__kpi-row" aria-label={tDs('kpis.aria')}>
        {kpis.map((kpi) => (
          <KpiCard
            key={kpi.key}
            className="proj-ds__kpi"
            label={tDs(`kpis.${kpi.key}`)}
            value={loading ? '—' : kpi.value}
            hint={tDs(`kpis.hints.${kpi.key}`)}
            delta={kpi.delta ? `${kpi.delta} ${tDs('kpis.vsLastMonth')}` : undefined}
            {...(kpi.deltaTone ? { deltaTone: kpi.deltaTone } : {})}
            icon={<IhIcon name={KPI_ICONS[kpi.key]} size={18} />}
          />
        ))}
      </section>

      <section className="proj-ds__filters" aria-label={tDs('filters.aria')}>
        <Input
          label={tDs('filters.search')}
          value={filters.search}
          onChange={(e) => {
            setFilters((prev) => ({ ...prev, search: e.target.value }));
            setPage(1);
          }}
          placeholder={tDs('filters.searchPlaceholder')}
        />
        <Select
          label={tDs('filters.status')}
          value={filters.status}
          onChange={(e) => {
            setFilters((prev) => ({
              ...prev,
              status: e.target.value as DsFilters['status'],
            }));
            setPage(1);
          }}
        >
          <option value="">{tDs('filters.any')}</option>
          {statusOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>
        <Select
          label={tDs('filters.location')}
          value={filters.city}
          onChange={(e) => {
            setFilters((prev) => ({ ...prev, city: e.target.value }));
            setPage(1);
          }}
        >
          <option value="">{tDs('filters.any')}</option>
          {cities.map((city) => (
            <option key={city} value={city}>
              {city}
            </option>
          ))}
        </Select>
        <Select
          label={tDs('filters.type')}
          value={filters.project_type}
          onChange={(e) => {
            setFilters((prev) => ({ ...prev, project_type: e.target.value }));
            setPage(1);
          }}
        >
          <option value="">{tDs('filters.any')}</option>
          {typeOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>
        <Select
          label={tDs('filters.manager')}
          value={filters.manager}
          onChange={(e) => {
            setFilters((prev) => ({ ...prev, manager: e.target.value }));
            setPage(1);
          }}
        >
          <option value="">{tDs('filters.any')}</option>
          {managers.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </Select>
        {showMoreFilters ? (
          <>
            <Select
              label={tDs('filters.priority')}
              value={filters.priority}
              onChange={(e) => {
                setFilters((prev) => ({
                  ...prev,
                  priority: e.target.value as DsFilters['priority'],
                }));
                setPage(1);
              }}
            >
              <option value="">{tDs('filters.any')}</option>
              {priorityOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </Select>
            <Select
              label={tDs('filters.budget')}
              value={filters.budgetRange}
              onChange={(e) => {
                setFilters((prev) => ({
                  ...prev,
                  budgetRange: e.target.value as DsFilters['budgetRange'],
                }));
                setPage(1);
              }}
            >
              <option value="">{tDs('filters.any')}</option>
              <option value="under10">{tDs('filters.budgetRanges.under10')}</option>
              <option value="10to50">{tDs('filters.budgetRanges.10to50')}</option>
              <option value="50to100">{tDs('filters.budgetRanges.50to100')}</option>
              <option value="over100">{tDs('filters.budgetRanges.over100')}</option>
            </Select>
          </>
        ) : null}
        <Button
          variant="secondary"
          size="sm"
          onClick={() => setShowMoreFilters((v) => !v)}
        >
          <IhIcon name="settings" size={13} />
          {tDs('filters.more')}
        </Button>
        <Button variant="secondary" size="sm" onClick={clearFilters}>
          <IhIcon name="refresh" size={13} />
          {t('clearFilters')}
        </Button>
        <div className="proj-ds__view-toggle">
          <SegmentedControl
            ariaLabel={tDs('view.aria')}
            value={view}
            onChange={(next) => setView(next as ProjectsViewMode)}
            options={[
              { value: 'card', label: tDs('view.card') },
              { value: 'list', label: tDs('view.list') },
            ]}
          />
        </div>
      </section>

      {error ? <div className="proj-ds__banner">{error}</div> : null}

      <div className="proj-ds__layout">
        <div className="proj-ds__main">
          {loading ? <div className="proj-ds__empty">{t('loading')}</div> : null}

          {!loading && view === 'card' ? (
            <section className="proj-ds__grid" aria-label={tDs('grid.aria')}>
              {heroCards.length === 0 ? (
                <div className="proj-ds__empty">{t('emptyState')}</div>
              ) : (
                heroCards.map((project) => {
                  const completion = projectCompletion(project);
                  const manager =
                    project.project_manager?.full_name ??
                    project.assigned_project_manager ??
                    '—';
                  const avatars = teamAvatars(project);
                  const roi = projectedReturn(project);
                  const risk = deriveAiRisk(project);
                  const stageLabel = project.development_stage
                    ? getStageLabel(project.development_stage)
                    : getStatusLabel(project.project_status);
                  const nextMilestone = deriveNextMilestoneKey(project);
                  const budget = Number(
                    project.construction_budget ??
                      project.total_development_cost ??
                      project.current_project_value ??
                      0,
                  );
                  return (
                    <article
                      key={project.id}
                      className="proj-ds__card"
                      data-testid={`projects-ds-card-${project.id}`}
                    >
                      <button
                        type="button"
                        className="proj-ds__card-media"
                        onClick={() => openProject(project)}
                      >
                        <ProjectCover scene={coverSceneFor(project)} />
                        <span className="proj-ds__cover-scrim" aria-hidden="true" />
                        <StatusChip
                          tone={statusTone(project.project_status)}
                          className="proj-ds__card-badge"
                        >
                          {getStatusLabel(project.project_status)}
                        </StatusChip>
                        <span className="proj-ds__card-code">{project.project_code}</span>
                      </button>
                      <div className="proj-ds__card-body">
                        <div className="proj-ds__card-title-row">
                          <button
                            type="button"
                            className="proj-ds__card-title"
                            onClick={() => openProject(project)}
                          >
                            {project.project_name}
                          </button>
                          <div className="proj-ds__menu-wrap">
                            <button
                              type="button"
                              className="proj-ds__icon-btn"
                              aria-label={tDs('card.more')}
                              onClick={() =>
                                setMenuId((id) => (id === project.id ? null : project.id))
                              }
                            >
                              ⋮
                            </button>
                            {menuId === project.id ? (
                              <div className="proj-ds__menu" role="menu">
                                <button type="button" role="menuitem" onClick={() => openProject(project)}>
                                  {tDs('card.open')}
                                </button>
                                {canUpdate ? (
                                  <button
                                    type="button"
                                    role="menuitem"
                                    onClick={() => {
                                      setEditProject(project);
                                      setFormMode('edit');
                                      setMenuId(null);
                                    }}
                                  >
                                    {t('editProject')}
                                  </button>
                                ) : null}
                              </div>
                            ) : null}
                          </div>
                        </div>
                        <p className="proj-ds__card-location">
                          <IhIcon name="target" size={11} />
                          <span>
                            {[project.city, project.state].filter(Boolean).join(', ') ||
                              formatLocation(project)}
                          </span>
                        </p>
                        <div className="proj-ds__card-meta">
                          <span className="proj-ds__meta-pill" title={tDs('card.stage')}>
                            {stageLabel}
                          </span>
                          <span
                            className={`proj-ds__meta-pill is-risk-${risk}`}
                            title={tDs('card.risk')}
                          >
                            {tDs(`risk.${risk}`)}
                          </span>
                          <span className="proj-ds__meta-pill" title={tDs('card.nextMilestone')}>
                            {tDs(`phases.${nextMilestone}`)}
                          </span>
                        </div>
                        <div className="proj-ds__card-progress">
                          <ProgressBar
                            value={completion}
                            label={`${tDs('card.progress')} · ${completion}%`}
                            tone="default"
                            className="proj-ds__progress"
                          />
                        </div>
                        <div className="proj-ds__card-metrics">
                          <div>
                            <span>{tDs('card.budget')}</span>
                            <strong>{formatCompactCurrency(budget, locale)}</strong>
                          </div>
                          <div>
                            <span>{tDs('card.completion')}</span>
                            <strong>
                              {formatShortDate(project.target_completion_date, locale)}
                            </strong>
                          </div>
                          <div>
                            <span>{tDs('card.return')}</span>
                            <strong className="proj-ds__metric-roi">{roi ?? '—'}</strong>
                          </div>
                        </div>
                        <div className="proj-ds__card-footer">
                          <div className="proj-ds__avatars" title={manager}>
                            {(avatars.length ? avatars : [manager]).map((name) => (
                              <span key={name} className="proj-ds__avatar" aria-hidden="true">
                                {initials(name)}
                              </span>
                            ))}
                            <span className="proj-ds__manager">{manager}</span>
                          </div>
                          <div className="proj-ds__card-actions">
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => openProject(project)}
                            >
                              {tDs('card.open')}
                            </Button>
                          </div>
                        </div>
                      </div>
                    </article>
                  );
                })
              )}
            </section>
          ) : null}

          {!loading ? (
            <section className="proj-ds__table-section" aria-label={tDs('table.aria')}>
              <div className="proj-ds__main-toolbar">
                <h2>
                  {tDs('table.title')}
                  <span className="proj-ds__count">{filtered.length}</span>
                </h2>
                <div className="proj-ds__toolbar-actions">
                  <Button variant="secondary" size="sm" onClick={handleExport}>
                    {tDs('actions.export')}
                  </Button>
                </div>
              </div>
              <div className="proj-ds__table-wrap">
                <table className="proj-ds__table">
                  <thead>
                    <tr>
                      <th scope="col">{t('table.project')}</th>
                      <th scope="col">{t('table.location')}</th>
                      <th scope="col">{t('table.status')}</th>
                      <th scope="col">{tDs('table.progress')}</th>
                      <th scope="col">{tDs('table.budget')}</th>
                      <th scope="col">{tDs('table.completionPct')}</th>
                      <th scope="col">{t('table.projectManager')}</th>
                      <th scope="col">{t('table.updated')}</th>
                      <th scope="col">{t('table.actions')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pageItems.length === 0 ? (
                      <tr>
                        <td colSpan={9}>
                          <div className="proj-ds__empty">{t('emptyState')}</div>
                        </td>
                      </tr>
                    ) : (
                      pageItems.map((project) => {
                        const completion = projectCompletion(project);
                        const manager =
                          project.project_manager?.full_name ??
                          project.assigned_project_manager ??
                          '—';
                        const budget = Number(
                          project.construction_budget ??
                            project.total_development_cost ??
                            projectValue(project),
                        );
                        return (
                          <tr
                            key={project.id}
                            className="proj-ds__row"
                            data-testid={`projects-ds-row-${project.id}`}
                            onClick={() => openProject(project)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter' || e.key === ' ') {
                                e.preventDefault();
                                openProject(project);
                              }
                            }}
                            tabIndex={0}
                          >
                            <td>
                              <strong title={project.project_name}>{project.project_name}</strong>
                              <span className="proj-ds__code">{project.project_code}</span>
                            </td>
                            <td>
                              {[project.city, project.state].filter(Boolean).join(', ') || '—'}
                            </td>
                            <td>
                              <StatusChip tone={statusTone(project.project_status)}>
                                {getStatusLabel(project.project_status)}
                              </StatusChip>
                            </td>
                            <td>
                              <div className="proj-ds__mini-progress">
                                <ProgressBar value={completion} tone="default" />
                                <span>{completion}%</span>
                              </div>
                            </td>
                            <td>{formatCompactCurrency(budget, locale)}</td>
                            <td>{completion}%</td>
                            <td>
                              <div className="proj-ds__rep">
                                <span className="proj-ds__avatar" aria-hidden="true">
                                  {initials(manager)}
                                </span>
                                <span title={manager}>{manager}</span>
                              </div>
                            </td>
                            <td>{formatShortDate(project.updated_at, locale)}</td>
                            <td>
                              <button
                                type="button"
                                className="proj-ds__icon-btn"
                                aria-label={tDs('card.more')}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  openProject(project);
                                }}
                              >
                                ⋮
                              </button>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
              <div className="proj-ds__pagination">
                <span>
                  {t('pagination', {
                    page: pageSafe,
                    pages,
                    total: filtered.length,
                  })}
                </span>
                <div>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={pageSafe <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                  >
                    {t('prevPage')}
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={pageSafe >= pages}
                    onClick={() => setPage((p) => Math.min(pages, p + 1))}
                  >
                    {t('nextPage')}
                  </Button>
                </div>
              </div>
            </section>
          ) : null}
        </div>

        <aside className="proj-ds__rail" aria-label={tDs('rail.aria')}>
          <section className="proj-ds__rail-card">
            <h3>{tDs('rail.milestones')}</h3>
            <ol className="proj-ds__timeline">
              {rail.milestones.length === 0 ? (
                <li className="proj-ds__timeline-empty">
                  <strong>—</strong>
                  <span>{tDs('rail.empty')}</span>
                </li>
              ) : (
                rail.milestones.map((item) => (
                  <li key={item.id} className={`proj-ds__timeline-item is-${item.tone}`}>
                    <span className="proj-ds__timeline-dot" aria-hidden="true" />
                    <div className="proj-ds__timeline-body">
                      <div className="proj-ds__timeline-top">
                        <time dateTime={item.date}>{formatShortDate(item.date, locale)}</time>
                        <StatusChip tone={priorityTone(item.priority)} className="proj-ds__prio-chip">
                          {getPriorityLabel(item.priority)}
                        </StatusChip>
                      </div>
                      <strong title={item.title}>{item.title}</strong>
                      <span>
                        {item.project} · {tDs(`phases.${item.phase}`)}
                      </span>
                    </div>
                  </li>
                ))
              )}
            </ol>
          </section>

          <section className="proj-ds__rail-card">
            <h3>{tDs('rail.budget')}</h3>
            {rail.budget.length === 0 ? (
              <p className="proj-ds__rail-empty">{tDs('rail.empty')}</p>
            ) : (
              <div className="proj-ds__donut-wrap">
                <div
                  className="proj-ds__donut"
                  style={{ background: budgetDonutGradient(rail.budget) }}
                  aria-hidden="true"
                >
                  <span>
                    <strong>{rail.budget.reduce((s, b) => s + b.pct, 0) > 0 ? '100' : '0'}%</strong>
                    <small>{tDs('rail.budgetTotal')}</small>
                  </span>
                </div>
                <ul className="proj-ds__donut-legend">
                  {rail.budget.map((slice) => (
                    <li key={slice.key}>
                      <span
                        className="proj-ds__swatch"
                        style={{ background: slice.color }}
                        aria-hidden="true"
                      />
                      <div className="proj-ds__donut-meta">
                        <strong>{getTypeLabel(slice.key)}</strong>
                        <em>
                          {slice.pct}% · {formatCompactCurrency(slice.amount, locale)}
                        </em>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>

          <section className="proj-ds__rail-card">
            <h3>{tDs('rail.activities')}</h3>
            <ul className="proj-ds__activity-list">
              {rail.activities.map((item) => (
                <li key={item.id}>
                  <span className="proj-ds__list-icon">
                    <IhIcon name={activityIcon(item.type)} size={12} />
                  </span>
                  <div>
                    <strong title={item.project}>{item.project}</strong>
                    <span>
                      {item.user} · {tDs(`activityTypes.${item.type}`)}
                    </span>
                    <time dateTime={item.time}>{formatShortDate(item.time, locale)}</time>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="proj-ds__rail-card">
            <h3>{tDs('rail.timeline')}</h3>
            <ul className="proj-ds__budget-list">
              {rail.timeline.map((item) => (
                <li key={item.id}>
                  <div className="proj-ds__budget-meta">
                    <strong title={item.label}>{item.label}</strong>
                    <em>{item.pct}%</em>
                  </div>
                  <div className="proj-ds__team-bar">
                    <span style={{ width: `${item.pct}%` }} />
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="proj-ds__rail-card">
            <h3>{tDs('rail.health')}</h3>
            <ul className="proj-ds__health-list">
              {rail.health.map((item) => (
                <li key={item.id} className="proj-ds__health-item">
                  <div className="proj-ds__health-head">
                    <strong title={item.name}>{item.name}</strong>
                    <StatusChip tone={item.tone} className="proj-ds__health-chip">
                      {item.label}
                    </StatusChip>
                  </div>
                  <div className="proj-ds__health-score-row">
                    <div
                      className="proj-ds__health-ring"
                      style={{
                        background: `conic-gradient(var(--shot-navy) ${item.score}%, #e6eef1 0)`,
                      }}
                      aria-hidden="true"
                    >
                      <span>{item.score}</span>
                    </div>
                    <div className="proj-ds__health-stats">
                      <div>
                        <span>{tDs('rail.healthScore')}</span>
                        <strong>{item.score}</strong>
                      </div>
                      <div>
                        <span>{tDs('rail.healthProgress')}</span>
                        <strong>{item.progress}%</strong>
                      </div>
                      <div>
                        <span>{tDs('rail.healthRisk')}</span>
                        <strong className={`is-risk-${item.risk}`}>
                          {tDs(`risk.${item.risk}`)}
                        </strong>
                      </div>
                      <div>
                        <span>{tDs('rail.healthConfidence')}</span>
                        <strong>{item.confidence}%</strong>
                      </div>
                    </div>
                  </div>
                  <div className="proj-ds__health-progress">
                    <ProgressBar value={item.progress} tone="default" />
                  </div>
                  <p className="proj-ds__health-insight">
                    <IhIcon name="sparkles" size={11} />
                    <span>
                      <em>{tDs('rail.healthInsight')}</em>
                      {tDs(`rail.insights.${item.insightKey}`)}
                    </span>
                  </p>
                </li>
              ))}
            </ul>
          </section>
        </aside>
      </div>

      <ProjectFormModal
        mode={formMode}
        project={formMode === 'edit' ? editProject : null}
        submitting={submitting}
        error={actionError}
        canEditFinancials={canUpdate}
        onClose={() => {
          setFormMode(null);
          setEditProject(null);
          setActionError(null);
        }}
        onSubmit={(input) => {
          void handleSubmit(input);
        }}
      />
    </div>
  );
}

export function ProjectsDsWorkspace() {
  const t = useTranslations('common');
  return (
    <Suspense
      fallback={
        <div className="proj-ds">
          <div className="proj-ds__empty">{t('loading')}</div>
        </div>
      }
    >
      <ProjectsDsWorkspaceInner />
    </Suspense>
  );
}
