'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import {
  archiveProject,
  createProject,
  fetchProject,
  fetchProjectStats,
  fetchProjects,
  formatCurrency,
  formatLocation,
  formatNumber,
  formatShortDate,
  type Project,
  type ProjectFilters,
  type ProjectInput,
  type ProjectStats,
  updateProject,
} from '@/lib/api/projects';
import { useProjectLabels } from '@/lib/i18n/project-labels';
import { useRecordDeepLink } from '@/lib/hooks/use-record-deep-link';

import { ProjectDetailDrawer } from './project-detail-drawer';
import { ProjectFormModal } from './project-form-modal';

type FormMode = 'create' | 'edit' | null;

const PAGE_SIZE = 20;

const EMPTY_FILTERS: ProjectFilters = {
  search: '',
  status: '',
  project_type: '',
  development_type: '',
  city: '',
  assigned_project_manager: '',
  sort_by: 'updated_at',
  sort_order: 'desc',
  page: 1,
  page_size: PAGE_SIZE,
};

export function ProjectsWorkspace() {
  const t = useTranslations('projects');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { getTypeLabel, getStatusLabel, typeOptions, developmentTypeOptions, statusOptions } =
    useProjectLabels();

  const [projects, setProjects] = useState<Project[]>([]);
  const [stats, setStats] = useState<ProjectStats | null>(null);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(0);
  const [filters, setFilters] = useState<ProjectFilters>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<ProjectFilters>(EMPTY_FILTERS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [formMode, setFormMode] = useState<FormMode>(null);
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const loadStats = useCallback(async () => {
    try {
      const response = await fetchProjectStats();
      setStats(response);
    } catch {
      setStats(null);
    }
  }, []);

  const loadProjects = useCallback(
    async (nextFilters: ProjectFilters) => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetchProjects(nextFilters);
        setProjects(response.items);
        setTotal(response.total);
        setPages(response.pages);
      } catch {
        setError(t('loadError'));
        setProjects([]);
        setTotal(0);
        setPages(0);
      } finally {
        setLoading(false);
      }
    },
    [t],
  );

  useEffect(() => {
    void loadStats();
  }, [loadStats]);

  useEffect(() => {
    void loadProjects(appliedFilters);
  }, [appliedFilters, loadProjects]);

  const handleOpenProject = useCallback((project: Project) => setSelectedProject(project), []);
  useRecordDeepLink(fetchProject, handleOpenProject);

  const demoCount = useMemo(
    () => projects.filter((project) => project.is_demo).length,
    [projects],
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

  const handleOpenEdit = (project: Project) => {
    setActionError(null);
    setSelectedProject(project);
    setFormMode('edit');
  };

  const handleSubmitProject = async (input: ProjectInput) => {
    setSubmitting(true);
    setActionError(null);

    try {
      if (formMode === 'create') {
        await createProject(input);
      } else if (formMode === 'edit' && selectedProject) {
        await updateProject(selectedProject.id, input);
      }
      setFormMode(null);
      await Promise.all([loadProjects(appliedFilters), loadStats()]);
    } catch {
      setActionError(t('saveError'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleArchiveProject = async (project: Project) => {
    setSubmitting(true);
    setActionError(null);

    try {
      await archiveProject(project.id);
      setSelectedProject(null);
      await Promise.all([loadProjects(appliedFilters), loadStats()]);
    } catch {
      setActionError(t('archiveError'));
    } finally {
      setSubmitting(false);
    }
  };

  const sortValue = `${appliedFilters.sort_by}:${appliedFilters.sort_order}`;

  return (
    <main className="dashboard leads investors projects">
      <header className="dashboard__header leads__header">
        <p className="dashboard__eyebrow">{t('eyebrow')}</p>
        <h1 className="dashboard__title">{t('title')}</h1>
        <p className="leads__subtitle">{t('subtitle')}</p>
      </header>

      {stats && (
        <section className="projects__stats">
          <article className="investors__stat-card">
            <p>{t('stats.total')}</p>
            <strong>{stats.total}</strong>
          </article>
          <article className="investors__stat-card">
            <p>{t('stats.active')}</p>
            <strong>{stats.active}</strong>
          </article>
          <article className="investors__stat-card">
            <p>{t('stats.units')}</p>
            <strong>{formatNumber(stats.units_under_development, locale)}</strong>
          </article>
          <article className="investors__stat-card">
            <p>{t('stats.developmentCost')}</p>
            <strong>{formatCurrency(stats.total_development_cost, locale)}</strong>
          </article>
          <article className="investors__stat-card">
            <p>{t('stats.portfolioValue')}</p>
            <strong>{formatCurrency(stats.current_portfolio_value, locale)}</strong>
          </article>
          <article className="investors__stat-card">
            <p>{t('stats.equityRaised')}</p>
            <strong>{formatCurrency(stats.equity_raised, locale)}</strong>
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
                    status: event.target.value as ProjectFilters['status'],
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
                value={filters.project_type ?? ''}
                onChange={(event) =>
                  setFilters((current) => ({
                    ...current,
                    project_type: event.target.value as ProjectFilters['project_type'],
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
              <span>{t('developmentTypeLabel')}</span>
              <select
                value={filters.development_type ?? ''}
                onChange={(event) =>
                  setFilters((current) => ({
                    ...current,
                    development_type: event.target.value as ProjectFilters['development_type'],
                  }))
                }
              >
                <option value="">{t('allDevelopmentTypes')}</option>
                {developmentTypeOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="leads__field">
              <span>{t('cityLabel')}</span>
              <input
                value={filters.city ?? ''}
                placeholder={t('cityPlaceholder')}
                onChange={(event) =>
                  setFilters((current) => ({ ...current, city: event.target.value }))
                }
              />
            </label>

            <label className="leads__field">
              <span>{t('managerLabel')}</span>
              <input
                value={filters.assigned_project_manager ?? ''}
                placeholder={t('managerPlaceholder')}
                onChange={(event) =>
                  setFilters((current) => ({
                    ...current,
                    assigned_project_manager: event.target.value,
                  }))
                }
              />
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
                <option value="project_name:asc">{t('sortNameAsc')}</option>
                <option value="project_name:desc">{t('sortNameDesc')}</option>
                <option value="total_development_cost:desc">{t('sortCostDesc')}</option>
                <option value="target_completion_date:asc">{t('sortTargetAsc')}</option>
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
            {t('addProject')}
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
              onClick={() => void loadProjects(appliedFilters)}
            >
              {tCommon('retry')}
            </button>
          </div>
        )}

        {!loading && !error && projects.length === 0 && (
          <div className="leads__state">
            <p>{t('emptyState')}</p>
            <button
              type="button"
              className="leads__button leads__button--primary"
              onClick={handleOpenCreate}
            >
              {t('addProject')}
            </button>
          </div>
        )}

        {!loading && !error && projects.length > 0 && (
          <>
            <div className="leads__table-wrap">
              <table className="leads__table">
                <thead>
                  <tr>
                    <th>{t('table.project')}</th>
                    <th>{t('table.location')}</th>
                    <th>{t('table.type')}</th>
                    <th>{t('table.status')}</th>
                    <th>{t('table.units')}</th>
                    <th>{t('table.developmentCost')}</th>
                    <th>{t('table.currentValue')}</th>
                    <th>{t('table.equityRequired')}</th>
                    <th>{t('table.equityRaised')}</th>
                    <th>{t('table.targetCompletion')}</th>
                    <th>{t('table.projectManager')}</th>
                  </tr>
                </thead>
                <tbody>
                  {projects.map((project) => (
                    <tr
                      key={project.id}
                      className="leads__row"
                      onClick={() => setSelectedProject(project)}
                    >
                      <td>
                        <span className="leads__name">{project.project_name}</span>
                        {project.is_demo && (
                          <span className="leads__demo-tag">{tCommon('demo')}</span>
                        )}
                        <span className="leads__meta">{project.project_code}</span>
                      </td>
                      <td>{formatLocation(project)}</td>
                      <td>{getTypeLabel(project.project_type)}</td>
                      <td>
                        <span className="leads__status">
                          {getStatusLabel(project.project_status)}
                        </span>
                      </td>
                      <td>{formatNumber(project.total_units, locale)}</td>
                      <td>{formatCurrency(project.total_development_cost, locale)}</td>
                      <td>{formatCurrency(project.current_project_value, locale)}</td>
                      <td>{formatCurrency(project.equity_required, locale)}</td>
                      <td>{formatCurrency(project.equity_raised, locale)}</td>
                      <td>{formatShortDate(project.target_completion_date, locale)}</td>
                      <td>{project.assigned_project_manager ?? tCommon('noValue')}</td>
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

      <ProjectDetailDrawer
        project={selectedProject}
        onClose={() => setSelectedProject(null)}
        onEdit={handleOpenEdit}
        onArchive={(project) => void handleArchiveProject(project)}
        archiving={submitting}
      />

      <ProjectFormModal
        mode={formMode}
        project={formMode === 'edit' ? selectedProject : null}
        submitting={submitting}
        error={actionError}
        onClose={() => setFormMode(null)}
        onSubmit={(input) => void handleSubmitProject(input)}
      />
    </main>
  );
}
