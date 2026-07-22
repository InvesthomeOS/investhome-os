'use client';

import type { Route } from 'next';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import { ContextualAiActions } from '@/components/ai/contextual-ai-actions';
import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';
import {
  archiveProject,
  changeProjectStatus,
  createProject,
  fetchProject,
  fetchProjectStats,
  fetchProjects,
  formatCurrency,
  updateProject,
  type Project,
  type ProjectFilters,
  type ProjectInput,
  type ProjectStats,
  type ProjectStatus,
} from '@/lib/api/projects';
import { useRecordDeepLink } from '@/lib/hooks/use-record-deep-link';
import { useProjectLabels } from '@/lib/i18n/project-labels';

import { ProjectFormModal } from '../project-form-modal';
import { ConstructionBoard } from './construction-board';
import type { ConstructionStage, ConstructionTask } from './construction-domain';
import {
  ActivityPanel,
  AnalyticsStrip,
  BudgetPanel,
  ChangeOrdersPanel,
  ContractorsPanel,
  DocumentsPanel,
  InspectionsPanel,
  IssuesRisksPanel,
  MilestonesPanel,
  PermitsPanel,
  TasksListPanel,
  TimelinePanel,
} from './domain-panels';
import { listTasks, updateTaskStage } from './ops-store';
import { OpsDrawer } from './ops-drawer';
import { PortfolioView } from './portfolio-view';
import {
  parseLayout,
  parseView,
  PROJECT_VIEWS,
  projectValue,
  toPortfolioType,
  type PortfolioLayout,
  type ProjectPortfolioType,
  type ProjectViewId,
} from './project-types';
import { deleteSavedView, listSavedViews, saveView, type ProjectSavedView } from './saved-views';
import { TaskDrawer } from './task-drawer';

import './projects-g4.css';

type FormMode = 'create' | 'edit' | null;

const PAGE_SIZE = 100;

const EMPTY_FILTERS: ProjectFilters = {
  search: '',
  status: '',
  project_type: '',
  development_type: '',
  priority: '',
  development_stage: '',
  city: '',
  state: '',
  assigned_project_manager: '',
  include_archived: false,
  sort_by: 'updated_at',
  sort_order: 'desc',
  page: 1,
  page_size: PAGE_SIZE,
};

export function ProjectsG4Workspace() {
  const t = useTranslations('projects');
  const tG4 = useTranslations('projects.g4');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { user } = useAuth();
  const { getStatusLabel, statusOptions, typeOptions } =
    useProjectLabels();

  const canView = user ? hasPermission(user, 'projects', 'view') : false;
  const canCreate = user ? hasPermission(user, 'projects', 'create') : false;
  const canUpdate = user ? hasPermission(user, 'projects', 'update') : false;
  const canArchive = user ? hasPermission(user, 'projects', 'archive') : false;

  const view = parseView(searchParams.get('view'));
  const layout = parseLayout(searchParams.get('layout'));
  const selectedProjectId = searchParams.get('id');

  const setView = (next: ProjectViewId) => {
    const params = new URLSearchParams(searchParams.toString());
    if (next === 'portfolio') params.delete('view');
    else params.set('view', next);
    const qs = params.toString();
    router.replace((qs ? `${pathname}?${qs}` : pathname) as Route);
  };

  const setLayout = (next: PortfolioLayout) => {
    const params = new URLSearchParams(searchParams.toString());
    if (next === 'grid') params.delete('layout');
    else params.set('layout', next);
    const qs = params.toString();
    router.replace((qs ? `${pathname}?${qs}` : pathname) as Route);
  };

  const [projects, setProjects] = useState<Project[]>([]);
  const [stats, setStats] = useState<ProjectStats | null>(null);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(0);
  const [filters, setFilters] = useState<ProjectFilters>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<ProjectFilters>(EMPTY_FILTERS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [selectedTask, setSelectedTask] = useState<ConstructionTask | null>(null);
  const [tasks, setTasks] = useState<ConstructionTask[]>([]);
  const [formMode, setFormMode] = useState<FormMode>(null);
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [overStage, setOverStage] = useState<ConstructionStage | null>(null);
  const [savedViews, setSavedViews] = useState<ProjectSavedView[]>([]);
  const [viewName, setViewName] = useState('');
  const [taskStoreVersion, setTaskStoreVersion] = useState(0);

  const typeLabel = useCallback(
    (type: ProjectPortfolioType) => tG4(`portfolioTypes.${type}`),
    [tG4],
  );

  const stageLabel = useCallback(
    (stage: ConstructionStage) => tG4(`stages.${stage}`),
    [tG4],
  );

  const priorityLabel = useCallback(
    (p: string) => tG4(`priority.${p}`),
    [tG4],
  );

  const loadStats = useCallback(async () => {
    try {
      setStats(await fetchProjectStats());
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
        setTasks(listTasks(response.items));
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
    setSavedViews(listSavedViews());
  }, [loadStats]);

  useEffect(() => {
    if (!canView) {
      setLoading(false);
      return;
    }
    void loadProjects(appliedFilters);
  }, [appliedFilters, loadProjects, canView]);

  useEffect(() => {
    setTasks(listTasks(projects));
  }, [projects, taskStoreVersion]);

  const handleOpenProject = useCallback((project: Project) => setSelectedProject(project), []);
  useRecordDeepLink(fetchProject, handleOpenProject);

  const demoCount = useMemo(
    () => projects.filter((project) => project.is_demo).length,
    [projects],
  );

  const portfolioTotals = useMemo(() => {
    const value = projects.reduce((s, p) => s + projectValue(p), 0);
    const construction = projects.filter(
      (p) => toPortfolioType(p) === 'construction' || p.project_status === 'construction',
    ).length;
    return { value, construction };
  }, [projects]);

  const panelLabels = useMemo(() => {
    const keys = [
      'kpiTotal',
      'kpiActive',
      'kpiConstruction',
      'kpiValue',
      'kpiCompletion',
      'chartTypeDist',
      'chartValueTrend',
      'analyticsNote',
      'liveTag',
      'partialTag',
      'demoTag',
      'blockedTag',
      'tasksTitle',
      'tasksGap',
      'title',
      'project',
      'stage',
      'priorityLabel',
      'due',
      'timelineTitle',
      'timelineHint',
      'empty',
      'milestonesTitle',
      'milestonesGap',
      'status',
      'actions',
      'customMilestone',
      'add',
      'budgetTitle',
      'budgetHint',
      'budgetLoadError',
      'category',
      'original',
      'current',
      'lines',
      'loading',
      'contractorsTitle',
      'contractorsHint',
      'committed',
      'paid',
      'permitsTitle',
      'permitsGap',
      'authority',
      'submitted',
      'inspectionsTitle',
      'inspectionsGap',
      'inspector',
      'scheduled',
      'issuesTitle',
      'issuesGap',
      'severity',
      'owner',
      'changeOrdersTitle',
      'changeOrdersGap',
      'commitmentsWithCos',
      'amount',
      'documentsTitle',
      'documentsHint',
      'openDocuments',
      'activityTitle',
      'activityHint',
      'filterActivity',
      'msStatus_not_started',
      'msStatus_in_progress',
      'msStatus_at_risk',
      'msStatus_completed',
      'msStatus_skipped',
      'fieldTitle',
    ] as const;
    const out: Record<string, string> = {};
    for (const key of keys) {
      try {
        out[key] = tG4(key);
      } catch {
        out[key] = key;
      }
    }
    out.title = out.fieldTitle ?? 'Title';
    out.priority = out.priorityLabel ?? 'Priority';
    // default milestone labels
    const msKeys = [
      'site_survey',
      'design_freeze',
      'permit_application',
      'permit_approval',
      'groundbreaking',
      'foundation',
      'structure',
      'envelope',
      'mep_rough_in',
      'insulation',
      'drywall',
      'finishes',
      'mep_final',
      'landscaping',
      'punch_list',
      'final_inspection',
      'certificate_occupancy',
      'handover',
      'warranty_start',
      'stabilization',
    ];
    for (const key of msKeys) {
      try {
        out[`ms_${key}`] = tG4(`milestones.${key}`);
      } catch {
        out[`ms_${key}`] = key;
      }
    }
    return out;
  }, [tG4]);

  const drawerLabels = useMemo(() => {
    const map: Record<string, string> = {
      close: tCommon('close'),
      openFull: tG4('openFull'),
      edit: tCommon('edit'),
      archive: t('archive'),
      tabs: tG4('drawerTabs'),
      location: tG4('location'),
      value: tG4('value'),
      target: tG4('target'),
      manager: t('managerLabel'),
      stage: tG4('stage'),
      portfolioType: tG4('portfolioType'),
      applyStage: tG4('applyStage'),
      description: tG4('description'),
      aiHint: tG4('aiHint'),
      useWorkspaceView: tG4('useWorkspaceView'),
      openView: tG4('openView'),
    };
    for (const tab of [
      'overview',
      'board',
      'tasks',
      'timeline',
      'milestones',
      'budget',
      'contractors',
      'permits',
      'inspections',
      'issues',
      'documents',
      'change_orders',
      'activity',
      'ai',
      'audit',
    ]) {
      map[`tab_${tab}`] = tG4(`tabs.${tab}`);
    }
    return map;
  }, [t, tG4, tCommon]);

  const taskDrawerLabels = useMemo(
    () => ({
      close: tCommon('close'),
      demoTag: tG4('demoTag'),
      save: t('saveChanges'),
      tabs: tG4('drawerTabs'),
      tab_overview: tG4('tabs.overview'),
      tab_details: tG4('tabs.details'),
      tab_activity: tG4('tabs.activity'),
      tab_comments: tG4('tabs.comments'),
      tab_ai: tG4('tabs.ai'),
      stage: tG4('stage'),
      priority: tG4('priorityLabel'),
      assignee: tG4('assignee'),
      due: tG4('due'),
      description: tG4('description'),
      title: tG4('fieldTitle'),
      activityGap: tG4('taskActivityGap'),
      commentsGap: tG4('taskCommentsGap'),
      aiHint: tG4('aiHint'),
    }),
    [tG4, tCommon, t],
  );

  const onDropTask = async (stage: ConstructionStage) => {
    if (!draggingId) return;
    const prev = tasks.find((t) => t.id === draggingId);
    if (!prev || prev.stage === stage) {
      setDraggingId(null);
      setOverStage(null);
      return;
    }
    // optimistic
    setTasks((list) => list.map((t) => (t.id === draggingId ? { ...t, stage } : t)));
    setDraggingId(null);
    setOverStage(null);
    try {
      updateTaskStage(draggingId, stage);
      setTaskStoreVersion((v) => v + 1);
    } catch {
      setTasks(listTasks(projects));
      setToast(tG4('stageError'));
    }
  };

  const handleStatusChange = async (project: Project, status: ProjectStatus) => {
    const prev = project.project_status;
    setProjects((list) =>
      list.map((p) => (p.id === project.id ? { ...p, project_status: status } : p)),
    );
    if (selectedProject?.id === project.id) {
      setSelectedProject({ ...project, project_status: status });
    }
    try {
      const updated = await changeProjectStatus(project.id, status);
      setProjects((list) => list.map((p) => (p.id === updated.id ? updated : p)));
      setSelectedProject(updated);
      setToast(tG4('stageUpdated'));
    } catch {
      setProjects((list) =>
        list.map((p) => (p.id === project.id ? { ...p, project_status: prev } : p)),
      );
      if (selectedProject?.id === project.id) {
        setSelectedProject({ ...project, project_status: prev });
      }
      setToast(tG4('stageError'));
    }
  };

  const handleSubmit = async (input: ProjectInput) => {
    setSubmitting(true);
    setActionError(null);
    try {
      if (formMode === 'create') {
        await createProject(input);
        setToast(tG4('created'));
      } else if (formMode === 'edit' && selectedProject) {
        const updated = await updateProject(selectedProject.id, input);
        setSelectedProject(updated);
        setToast(tG4('updated'));
      }
      setFormMode(null);
      await loadProjects(appliedFilters);
      await loadStats();
    } catch {
      setActionError(t('saveError'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleArchive = async (project: Project) => {
    if (!canArchive) return;
    try {
      await archiveProject(project.id);
      setSelectedProject(null);
      setToast(tG4('archived'));
      await loadProjects(appliedFilters);
      await loadStats();
    } catch {
      setToast(t('archiveError'));
    }
  };

  if (!canView) {
    return (
      <main className="proj-g4" data-testid="proj-g4-workspace">
        <div className="proj-g4__empty">{tG4('accessDenied')}</div>
      </main>
    );
  }

  return (
    <main className="proj-g4" data-testid="proj-g4-workspace">
      <header className="proj-g4__top">
        <div>
          <p className="proj-g4__eyebrow">{t('eyebrow')}</p>
          <h1 className="proj-g4__title">{tG4('title')}</h1>
          <p className="proj-g4__subtitle">
            {tG4('subtitle', {
              count: total,
              value: formatCurrency(String(portfolioTotals.value), locale),
              construction: portfolioTotals.construction,
            })}
          </p>
        </div>
        <div className="proj-g4__top-actions">
          <ContextualAiActions module="projects" />
          {canCreate ? (
            <button
              type="button"
              className="proj-g4__btn proj-g4__btn--primary"
              onClick={() => {
                setFormMode('create');
                setActionError(null);
              }}
              data-testid="proj-g4-add"
            >
              {t('addProject')}
            </button>
          ) : null}
        </div>
      </header>

      <nav className="proj-g4__nav" aria-label={tG4('viewsLabel')}>
        {PROJECT_VIEWS.map((id) => (
          <button
            key={id}
            type="button"
            className={`proj-g4__nav-btn${view === id ? ' is-active' : ''}`}
            onClick={() => setView(id)}
            data-testid={`proj-g4-nav-${id}`}
          >
            {tG4(`views.${id}`)}
          </button>
        ))}
      </nav>

      <div className="proj-g4__body">
        {demoCount > 0 ? (
          <div className="proj-g4__banner proj-g4__banner--info">{t('demoBanner', { count: demoCount })}</div>
        ) : null}
        {toast ? (
          <div className="proj-g4__toast">
            <span>{toast}</span>
            <button type="button" className="proj-g4__btn proj-g4__btn--ghost" onClick={() => setToast(null)}>
              {tCommon('close')}
            </button>
          </div>
        ) : null}
        {error ? <div className="proj-g4__banner">{error}</div> : null}

        {(view === 'portfolio' || view === 'board' || view === 'tasks') && (
          <>
            <div className="proj-g4__filters">
              <label>
                {t('searchLabel')}
                <input
                  value={filters.search ?? ''}
                  onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
                  placeholder={t('searchPlaceholder')}
                />
              </label>
              <label>
                {t('statusLabel')}
                <select
                  value={filters.status ?? ''}
                  onChange={(e) =>
                    setFilters((f) => ({
                      ...f,
                      status: e.target.value as ProjectFilters['status'],
                    }))
                  }
                >
                  <option value="">{t('allStatuses')}</option>
                  {statusOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                {t('typeLabel')}
                <select
                  value={filters.project_type ?? ''}
                  onChange={(e) =>
                    setFilters((f) => ({
                      ...f,
                      project_type: e.target.value as ProjectFilters['project_type'],
                    }))
                  }
                >
                  <option value="">{t('allTypes')}</option>
                  {typeOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                {t('cityLabel')}
                <input
                  value={filters.city ?? ''}
                  onChange={(e) => setFilters((f) => ({ ...f, city: e.target.value }))}
                  placeholder={t('cityPlaceholder')}
                />
              </label>
              <div className="proj-g4__toolbar-right" style={{ alignSelf: 'end' }}>
                <button
                  type="button"
                  className="proj-g4__btn proj-g4__btn--primary"
                  onClick={() => setAppliedFilters({ ...filters, page: 1 })}
                >
                  {tCommon('apply')}
                </button>
                <button
                  type="button"
                  className="proj-g4__btn"
                  onClick={() => {
                    setFilters(EMPTY_FILTERS);
                    setAppliedFilters(EMPTY_FILTERS);
                  }}
                >
                  {t('clearFilters')}
                </button>
              </div>
            </div>

            <div className="proj-g4__toolbar">
              <div className="proj-g4__toolbar-left">
                {view === 'portfolio' ? (
                  <div className="proj-g4__seg" role="group" aria-label={tG4('layoutLabel')}>
                    {(['grid', 'list', 'table'] as const).map((l) => (
                      <button
                        key={l}
                        type="button"
                        className={layout === l || (l === 'table' && layout === 'list') ? 'is-active' : ''}
                        onClick={() => setLayout(l === 'table' ? 'table' : l)}
                      >
                        {tG4(`layout.${l}`)}
                      </button>
                    ))}
                  </div>
                ) : null}
                {savedViews.map((sv) => (
                  <button
                    key={sv.id}
                    type="button"
                    className="proj-g4__chip"
                    title={tG4('savedViewHint')}
                    onClick={() => {
                      const next: ProjectFilters = {
                        ...EMPTY_FILTERS,
                        search: sv.filters.search ?? '',
                        status: (sv.filters.status as ProjectFilters['status']) ?? '',
                        project_type: (sv.filters.project_type as ProjectFilters['project_type']) ?? '',
                        development_type:
                          (sv.filters.development_type as ProjectFilters['development_type']) ?? '',
                        priority: (sv.filters.priority as ProjectFilters['priority']) ?? '',
                        development_stage:
                          (sv.filters.development_stage as ProjectFilters['development_stage']) ?? '',
                        city: sv.filters.city ?? '',
                        assigned_project_manager: sv.filters.assigned_project_manager ?? '',
                        sort_by: (sv.filters.sort_by as ProjectFilters['sort_by']) ?? 'updated_at',
                        sort_order: sv.filters.sort_order ?? 'desc',
                        page: 1,
                        page_size: PAGE_SIZE,
                      };
                      setFilters(next);
                      setAppliedFilters(next);
                      if (sv.view) setView(parseView(sv.view));
                      if (sv.layout) setLayout(parseLayout(sv.layout));
                    }}
                    onContextMenu={(e) => {
                      e.preventDefault();
                      deleteSavedView(sv.id);
                      setSavedViews(listSavedViews());
                    }}
                  >
                    {sv.name}
                  </button>
                ))}
              </div>
              <div className="proj-g4__toolbar-right">
                <input
                  value={viewName}
                  onChange={(e) => setViewName(e.target.value)}
                  placeholder={tG4('saveViewPlaceholder')}
                  style={{
                    padding: '0.35rem 0.5rem',
                    border: '1px solid var(--proj-border)',
                    borderRadius: 6,
                    fontSize: '0.75rem',
                  }}
                />
                <button
                  type="button"
                  className="proj-g4__btn"
                  onClick={() => {
                    if (!viewName.trim()) return;
                    saveView({
                      name: viewName.trim(),
                      scope: 'personal',
                      filters: {
                        search: appliedFilters.search,
                        status: appliedFilters.status || undefined,
                        project_type: appliedFilters.project_type || undefined,
                        city: appliedFilters.city,
                        sort_by: appliedFilters.sort_by,
                        sort_order: appliedFilters.sort_order,
                      },
                      view,
                      layout,
                    });
                    setSavedViews(listSavedViews());
                    setToast(tG4('viewSaved', { name: viewName.trim() }));
                    setViewName('');
                  }}
                >
                  {tG4('saveView')}
                </button>
              </div>
            </div>
          </>
        )}

        {loading ? <div className="proj-g4__empty">{t('loading')}</div> : null}

        {!loading && view === 'portfolio' ? (
          <PortfolioView
            projects={projects}
            locale={locale}
            layout={layout === 'list' ? 'table' : layout}
            typeLabel={typeLabel}
            statusLabel={getStatusLabel}
            onOpen={handleOpenProject}
          />
        ) : null}

        {!loading && view === 'board' ? (
          <>
            <p className="proj-g4__banner proj-g4__banner--gap">
              <span className="proj-g4__data-tag proj-g4__data-tag--demo">{tG4('demoTag')}</span>{' '}
              {tG4('boardGap')}
            </p>
            <ConstructionBoard
              tasks={
                selectedProjectId
                  ? tasks.filter((task) => task.projectId === selectedProjectId)
                  : tasks
              }
              stageLabel={stageLabel}
              priorityLabel={priorityLabel}
              canMove={canUpdate}
              draggingId={draggingId}
              overStage={overStage}
              onDragStart={setDraggingId}
              onDragEnd={() => {
                setDraggingId(null);
                setOverStage(null);
              }}
              onDragOver={setOverStage}
              onDrop={(stage) => void onDropTask(stage)}
              onOpen={setSelectedTask}
            />
          </>
        ) : null}

        {!loading && view === 'tasks' ? (
          <TasksListPanel
            tasks={tasks}
            labels={panelLabels}
            onOpen={(id) => {
              const task = tasks.find((x) => x.id === id);
              if (task) setSelectedTask(task);
            }}
          />
        ) : null}

        {!loading && view === 'timeline' ? (
          <TimelinePanel
            projects={projects}
            locale={locale}
            labels={panelLabels}
            typeLabel={typeLabel}
            selectedProjectId={selectedProjectId}
          />
        ) : null}

        {!loading && view === 'milestones' ? (
          <MilestonesPanel
            projects={projects}
            locale={locale}
            labels={panelLabels}
            typeLabel={typeLabel}
            selectedProjectId={selectedProjectId}
          />
        ) : null}

        {!loading && view === 'budget' ? (
          <BudgetPanel
            projects={projects}
            locale={locale}
            labels={panelLabels}
            typeLabel={typeLabel}
            selectedProjectId={selectedProjectId}
          />
        ) : null}

        {!loading && view === 'contractors' ? (
          <ContractorsPanel
            projects={projects}
            locale={locale}
            labels={panelLabels}
            typeLabel={typeLabel}
            selectedProjectId={selectedProjectId}
          />
        ) : null}

        {!loading && view === 'permits' ? (
          <PermitsPanel
            projects={projects}
            locale={locale}
            labels={panelLabels}
            typeLabel={typeLabel}
            selectedProjectId={selectedProjectId}
          />
        ) : null}

        {!loading && view === 'inspections' ? (
          <InspectionsPanel
            projects={projects}
            locale={locale}
            labels={panelLabels}
            typeLabel={typeLabel}
            selectedProjectId={selectedProjectId}
          />
        ) : null}

        {!loading && view === 'issues' ? (
          <IssuesRisksPanel
            projects={projects}
            locale={locale}
            labels={panelLabels}
            typeLabel={typeLabel}
            selectedProjectId={selectedProjectId}
          />
        ) : null}

        {!loading && view === 'documents' ? (
          <DocumentsPanel
            projects={projects}
            locale={locale}
            labels={panelLabels}
            typeLabel={typeLabel}
            selectedProjectId={selectedProjectId}
          />
        ) : null}

        {!loading && view === 'change_orders' ? (
          <ChangeOrdersPanel
            projects={projects}
            locale={locale}
            labels={panelLabels}
            typeLabel={typeLabel}
            selectedProjectId={selectedProjectId}
          />
        ) : null}

        {!loading && view === 'analytics' ? (
          <AnalyticsStrip
            projects={projects}
            locale={locale}
            labels={panelLabels}
            typeLabel={typeLabel}
            selectedProjectId={selectedProjectId}
          />
        ) : null}

        {!loading && view === 'activity' ? <ActivityPanel labels={panelLabels} /> : null}

        {!loading && pages > 1 && (view === 'portfolio' || view === 'board') ? (
          <div className="proj-g4__pagination">
            <span>
              {t('pagination', {
                page: appliedFilters.page ?? 1,
                pages,
                total,
              })}
            </span>
            <div>
              <button
                type="button"
                className="proj-g4__btn"
                disabled={(appliedFilters.page ?? 1) <= 1}
                onClick={() =>
                  setAppliedFilters((f) => ({ ...f, page: Math.max(1, (f.page ?? 1) - 1) }))
                }
              >
                {t('prevPage')}
              </button>
              <button
                type="button"
                className="proj-g4__btn"
                disabled={(appliedFilters.page ?? 1) >= pages}
                onClick={() =>
                  setAppliedFilters((f) => ({ ...f, page: Math.min(pages, (f.page ?? 1) + 1) }))
                }
              >
                {t('nextPage')}
              </button>
            </div>
          </div>
        ) : null}

        {stats ? (
          <p className="proj-g4__subtitle" style={{ marginTop: 'auto' }}>
            {stats.active} {tG4('kpiActive').toLowerCase()} · {stats.under_construction}{' '}
            {tG4('kpiConstruction').toLowerCase()}
          </p>
        ) : null}
      </div>

      <OpsDrawer
        project={selectedProject}
        locale={locale}
        canUpdate={canUpdate}
        typeLabel={typeLabel}
        statusLabel={getStatusLabel}
        labels={drawerLabels}
        onClose={() => setSelectedProject(null)}
        onEdit={(p) => {
          setSelectedProject(p);
          setFormMode('edit');
        }}
        onArchive={(p) => void handleArchive(p)}
        onStatusChange={handleStatusChange}
      />

      <TaskDrawer
        task={selectedTask}
        stageLabel={stageLabel}
        priorityLabel={priorityLabel}
        labels={taskDrawerLabels}
        canUpdate={canUpdate}
        onClose={() => setSelectedTask(null)}
        onSaved={() => {
          setTaskStoreVersion((v) => v + 1);
          setSelectedTask(null);
          setToast(tG4('taskSaved'));
        }}
      />

      {formMode ? (
        <ProjectFormModal
          mode={formMode}
          project={formMode === 'edit' ? selectedProject : null}
          submitting={submitting}
          error={actionError}
          canEditFinancials={canUpdate}
          onClose={() => setFormMode(null)}
          onSubmit={handleSubmit}
        />
      ) : null}
    </main>
  );
}
