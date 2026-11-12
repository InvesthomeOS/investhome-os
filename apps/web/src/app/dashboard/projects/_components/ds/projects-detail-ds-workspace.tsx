'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import {
  Button,
  KpiCard,
  ProgressBar,
  Select,
  StatusChip,
  Tabs,
} from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';
import { hasPermission } from '@/lib/api/auth';
import { uiError } from '@/lib/i18n/ui-error';
import { useAuth } from '@/lib/auth/auth-context';
import {
  listCreativeStudioMediaAssets,
  listCreativeStudioMediaFolders,
  type CreativeStudioMediaAsset,
  type CreativeStudioMediaFolder,
} from '@/lib/api/creative-studio';
import { documentDownloadUrl, formatFileSize } from '@/lib/api/documents';
import {
  fetchProjectAlerts,
  fetchProjectDetail,
  fetchProjectDetailActivity,
  fetchProjectDocuments,
  fetchProjectFinancials,
  fetchProjectInvestors,
  fetchProjectLocationIntelligence,
  fetchProjectUnits,
  fetchProjects,
  formatShortDate,
  refreshProjectLocationIntelligence,
  type LocationIntelligenceResponse,
  type Project,
  type ProjectActivityItem,
  type ProjectAlertItem,
  type MetricValue,
  type ProjectFinancialsResponse,
} from '@/lib/api/projects';
import { fetchProjectPhases } from '@/lib/api/project-phases';
import { useProjectLabels } from '@/lib/i18n/project-labels';
import { ProjectPhaseEditor } from '../project-phase-editor';
import { canViewProjectFinancials } from '@/lib/projects/projects-permissions';
import { createLocationRefreshController } from '@/lib/projects/location-refresh-action';
import { collectLinkedProjectMedia } from '@/lib/projects/project-gallery-media';

import {
  buildProjectDetailDsModel,
  formatCompactCurrency,
  PROJECT_DETAIL_NAV_TABS,
  priorityTone,
  projectDetailDsHref,
  resolveProjectDetailDsTab,
  statusTone,
  type DetailKpiKey,
  type ProjectDetailDsTab,
} from './projects-detail-ds-model';
import { ProjectDriveSyncPanel } from './project-drive-sync-panel';
import { ProjectAssistantPanel } from './project-assistant-panel';
import { ProjectsDetailDigitalTwin } from './projects-detail-digital-twin';
import type { AmenityItem } from './projects-detail-media-model';
import {
  buildOverviewMedia,
  isOperationalProjectDocument,
  metricText,
  overlayLocationIntelligence,
  readOverviewDocument,
  type OverviewDocument,
  type OverviewMedia,
} from './projects-detail-overview-live';

import './projects-ds.css';
import './projects-detail-ds.css';

const KPI_ICONS: Record<DetailKpiKey, IhIconName> = {
  acquisition: 'barChart',
  equityRequired: 'investors',
  totalBudget: 'barChart',
  spent: 'trendingUp',
  remaining: 'inbox',
  expectedRoi: 'target',
  units: 'projects',
  investors: 'investors',
  completion: 'check',
  targetDelivery: 'calendar',
};

const KPI_ORDER: DetailKpiKey[] = [
  'acquisition',
  'equityRequired',
  'units',
  'investors',
  'completion',
  'targetDelivery',
  'totalBudget',
  'spent',
  'remaining',
  'expectedRoi',
];

function kpiValue(
  key: DetailKpiKey,
  values: {
    acquisition: string | null;
    equity: string | null;
    budget: string | null;
    spent: string | null;
    remaining: string | null;
    roi: string | null;
    units: string | null;
    investors: string | null;
    completion: string | null;
    target: string | null;
  },
): string | null {
  switch (key) {
    case 'acquisition':
      return values.acquisition;
    case 'equityRequired':
      return values.equity;
    case 'totalBudget':
      return values.budget;
    case 'spent':
      return values.spent;
    case 'remaining':
      return values.remaining;
    case 'expectedRoi':
      return values.roi;
    case 'units':
      return values.units;
    case 'investors':
      return values.investors;
    case 'completion':
      return values.completion;
    case 'targetDelivery':
      return values.target;
  }
}

function salesTone(status: string) {
  switch (status) {
    case 'sold':
      return 'success' as const;
    case 'under_contract':
      return 'info' as const;
    case 'not_for_sale':
      return 'warning' as const;
    default:
      return 'default' as const;
  }
}

function taskTone(status: string) {
  switch (status) {
    case 'done':
      return 'success' as const;
    case 'blocked':
      return 'danger' as const;
    case 'in_progress':
      return 'info' as const;
    default:
      return 'default' as const;
  }
}

interface ProjectsDetailDsWorkspaceProps {
  projectId: string;
  tab: string;
}

export function ProjectsDetailDsWorkspace({
  projectId,
  tab,
}: ProjectsDetailDsWorkspaceProps) {
  const t = useTranslations('projects');
  const tD = useTranslations('projects.detail');
  const tDs = useTranslations('projects.ds');
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const phaseId = searchParams.get('phase') ?? '';
  const { user } = useAuth();
  const {
    getStatusLabel,
    getTypeLabel,
    getStageLabel,
    getPriorityLabel,
    getDevelopmentTypeLabel,
  } = useProjectLabels();

  const canView = user ? hasPermission(user, 'projects', 'view') : false;
  const resolvedTab = resolveProjectDetailDsTab(tab) ?? 'overview';

  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [projectMedia, setProjectMedia] = useState<CreativeStudioMediaAsset[]>([]);
  const [activity, setActivity] = useState<ProjectActivityItem[]>([]);
  const [alerts, setAlerts] = useState<ProjectAlertItem[]>([]);
  const [financials, setFinancials] = useState<ProjectFinancialsResponse | null>(null);
  const [financialsLoading, setFinancialsLoading] = useState(false);
  const [financialsError, setFinancialsError] = useState(false);
  const [financeAudience, setFinanceAudience] = useState<'internal' | 'customer'>('internal');
  const [projectPhases, setProjectPhases] = useState<Array<{ id: string; name: string }>>([]);
  const usesPhases = project?.uses_phases === true;
  const phaseFilter = usesPhases ? phaseId : '';
  const shownTab = resolvedTab === 'phases' && !usesPhases ? 'overview' : resolvedTab;
  const [unitSummary, setUnitSummary] = useState<Record<string, MetricValue> | null>(null);
  const [investorCount, setInvestorCount] = useState<number | null>(null);
  const [investorItems, setInvestorItems] = useState<Array<Record<string, unknown>>>([]);
  const [locationIntel, setLocationIntel] = useState<LocationIntelligenceResponse | null>(null);
  const [refreshState, setRefreshState] = useState<string | null>(null);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const refreshControllerRef = useRef<ReturnType<typeof createLocationRefreshController> | null>(null);
  const refreshLocaleRef = useRef<string | null>(null);
  if (refreshControllerRef.current?.projectId !== projectId || refreshLocaleRef.current !== locale) {
    refreshControllerRef.current?.stop();
    refreshControllerRef.current = createLocationRefreshController({
      projectId,
      post: (path: string) => {
        if (path !== `/projects/${projectId}/location-intelligence/refresh`) {
          return Promise.reject(new Error('unexpected location refresh path'));
        }
        return refreshProjectLocationIntelligence(projectId);
      },
      read: (path: string) => {
        if (path !== `/projects/${projectId}/location-intelligence`) {
          return Promise.reject(new Error('unexpected location read path'));
        }
        return fetchProjectLocationIntelligence(projectId, locale);
      },
    });
    refreshLocaleRef.current = locale;
  }

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const shell = await fetchProjectDetail(projectId).catch(() => null);
      if (shell?.project) {
        setProject(shell.project);
        return;
      }
      const list = await fetchProjects({
        page: 1,
        page_size: 100,
        sort_by: 'updated_at',
        sort_order: 'desc',
        include_archived: false,
      });
      const found = list.items.find((item) => item.id === projectId) ?? list.items[0] ?? null;
      setProject(found);
    } catch {
      setError(t('loadError'));
      setProject(null);
    } finally {
      setLoading(false);
    }
  }, [projectId, t]);

  useEffect(() => {
    if (!canView) {
      setLoading(false);
      return;
    }
    void load();
  }, [canView, load]);

  useEffect(() => {
    if (!canView) return;
    let cancelled = false;
    void Promise.all([
      fetchProjectDetailActivity(projectId, { page: 1, page_size: 20 }),
      fetchProjectAlerts(projectId),
      fetchProjectInvestors(projectId, phaseFilter || undefined).catch(() => null),
    ]).then(([activityPage, alertPage, investors]) => {
      if (cancelled) return;
      setActivity(activityPage.items);
      setAlerts(alertPage.items);
      setInvestorItems(investors?.items ?? []);
      setInvestorCount(investors ? investors.total : null);
    }).catch(() => {
      if (cancelled) return;
      setActivity([]);
      setAlerts([]);
      setInvestorItems([]);
      setInvestorCount(null);
    });
    return () => {
      cancelled = true;
    };
  }, [canView, phaseFilter, projectId]);

  useEffect(() => {
    if (!canView) return;
    let cancelled = false;
    void fetchProjectPhases(projectId)
      .then((items) => {
        if (!cancelled) {
          setProjectPhases(items.filter((item) => item.active).map((item) => ({ id: item.id, name: item.name })));
        }
      })
      .catch(() => {
        if (!cancelled) setProjectPhases([]);
      });
    return () => {
      cancelled = true;
    };
  }, [canView, projectId]);

  useEffect(() => {
    if (!canView) return;
    let cancelled = false;
    void fetchProjectUnits(projectId, {
      page: 1,
      page_size: 1,
      ...(phaseFilter ? { phase_id: phaseFilter } : {}),
    })
      .then((page) => {
        if (!cancelled) setUnitSummary(page.summary as Record<string, MetricValue>);
      })
      .catch(() => {
        if (!cancelled) setUnitSummary(null);
      });
    return () => {
      cancelled = true;
    };
  }, [canView, phaseFilter, projectId]);

  const canViewFinancials = canViewProjectFinancials(user);

  useEffect(() => {
    if (!canView || !canViewFinancials) {
      setFinancials(null);
      setFinancialsError(false);
      setFinancialsLoading(false);
      return;
    }
    let cancelled = false;
    setFinancialsLoading(true);
    setFinancialsError(false);
    void fetchProjectFinancials(projectId, financeAudience, phaseFilter || undefined)
      .then((finance) => {
        if (!cancelled) setFinancials(finance);
      })
      .catch(() => {
        if (!cancelled) {
          setFinancials(null);
          setFinancialsError(true);
        }
      })
      .finally(() => {
        if (!cancelled) setFinancialsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [canView, canViewFinancials, financeAudience, phaseFilter, projectId]);

  useEffect(() => {
    if (!canView) return;
    let cancelled = false;
    void collectLinkedProjectMedia(
      (params) => listCreativeStudioMediaAssets(params),
      projectId,
    )
      .then((items) => {
        if (!cancelled) setProjectMedia(items);
      })
      .catch(() => {
        if (!cancelled) setProjectMedia([]);
      });
    return () => {
      cancelled = true;
    };
  }, [canView, projectId]);

  useEffect(() => {
    if (!canView) return;
    let cancelled = false;
    fetchProjectLocationIntelligence(projectId, locale)
      .then((data) => {
        if (!cancelled) setLocationIntel(data);
      })
      .catch(() => {
        if (!cancelled) setLocationIntel(null);
      });
    return () => {
      cancelled = true;
    };
  }, [canView, projectId, locale]);

  useEffect(() => {
    const controller = refreshControllerRef.current;
    if (!controller || controller.projectId !== projectId) return;
    const unsubscribe = controller.subscribe((event: {
      type: string;
      status?: string;
      error?: string | null;
      intel?: LocationIntelligenceResponse;
    }) => {
      if (event.type === 'status') {
        setRefreshState(event.status ?? 'error');
        setRefreshError(event.error ?? null);
        return;
      }
      if (event.type === 'intel' && event.intel) {
        setLocationIntel(event.intel);
        return;
      }
      setRefreshState(null);
      setRefreshError(null);
    });
    return () => {
      unsubscribe();
    };
  }, [projectId, locale]);

  const model = useMemo(
    () => buildProjectDetailDsModel(project, projectId, locale),
    [project, projectId, locale],
  );
  const media = useMemo(
    () => buildOverviewMedia(project, projectMedia),
    [project, projectMedia],
  );
  const locationView = useMemo(
    () => overlayLocationIntelligence(media.location, locationIntel),
    [media.location, locationIntel],
  );
  const refreshLocation = useCallback(() => {
    const controller = refreshControllerRef.current;
    if (!controller) {
      setRefreshState('error');
      setRefreshError('Location refresh is unavailable.');
      return;
    }
    void controller.click();
  }, []);
  const financeSummary = financials?.summary ?? null;
  const hasBudgetBaseline = Boolean(
    financeSummary?.total_development_budget?.available ||
      financeSummary?.construction_budget?.available ||
      model.financial.budget != null,
  );
  const spentLabel = hasBudgetBaseline ? metricText(financeSummary?.budget_paid, locale) : null;
  const remainingLabel = metricText(financeSummary?.budget_remaining, locale);
  const budgetLabel =
    model.kpis.totalBudget.value ||
    metricText(financeSummary?.total_development_budget, locale) ||
    metricText(financeSummary?.construction_budget, locale);

  const tabItems = useMemo(
    () =>
      PROJECT_DETAIL_NAV_TABS.filter((id) => id !== 'phases' || usesPhases).map((id) => ({
        id,
        label: tD(`tabs.${id}`),
      })),
    [tD, usesPhases],
  );

  const onTabChange = (id: string) => {
    const next = resolveProjectDetailDsTab(id);
    if (!next) return;
    const params = new URLSearchParams(searchParams.toString());
    const query = params.toString();
    router.push(`${projectDetailDsHref(projectId, next)}${query ? `?${query}` : ''}` as Route);
  };

  const onPhaseChange = (value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value) params.set('phase', value);
    else params.delete('phase');
    const query = params.toString();
    router.replace(`${pathname}${query ? `?${query}` : ''}` as Route);
  };

  if (!canView) {
    return (
      <div className="proj-detail-ds" data-testid="projects-detail-ds-workspace">
        <div className="proj-detail-ds__empty">{tDs('accessDenied')}</div>
      </div>
    );
  }

  return (
    <div className="proj-detail-ds" data-testid="projects-detail-ds-workspace">
      <nav className="proj-detail-ds__crumb" aria-label={tD('breadcrumb.aria')}>
        <Link href={'/dashboard/projects' as Route}>{tD('breadcrumb.projects')}</Link>
        <span className="proj-detail-ds__crumb-sep" aria-hidden="true">
          /
        </span>
        <span className="proj-detail-ds__crumb-current">{model.name}</span>
      </nav>

      <section className="proj-detail-ds__hero" aria-label={tD('hero.aria')}>
        <div className="proj-detail-ds__hero-media">
          {media.heroImageUrl ? (
            // Cookie-authenticated project media; next/image cannot attach the session.
            // eslint-disable-next-line @next/next/no-img-element
            <img
              className="proj-ds__cover"
              src={media.heroImageUrl}
              alt=""
              data-testid="project-hero-image"
            />
          ) : (
            <div className="proj-detail-ds__hero-placeholder" data-testid="project-hero-placeholder">
              <span>{tD('empty.added')}</span>
            </div>
          )}
          <span className="proj-detail-ds__hero-code">{model.code}</span>
        </div>
        <div className="proj-detail-ds__hero-body">
          <div className="proj-detail-ds__hero-top">
            <div>
              <h1 className="proj-detail-ds__hero-title">
                {loading ? '—' : model.name}
              </h1>
              <div className="proj-detail-ds__hero-meta">
                <span>{model.location}</span>
                <span>·</span>
                <span>{getTypeLabel(model.projectType)}</span>
                <span>·</span>
                <span>{getDevelopmentTypeLabel(model.developmentType)}</span>
              </div>
            </div>
            <div className="proj-detail-ds__hero-actions">
              <Button variant="secondary" size="sm" type="button">
                <IhIcon name="settings" size={13} />
                {tD('actions.edit')}
              </Button>
              <Button variant="secondary" size="sm" type="button">
                <IhIcon name="inbox" size={13} />
                {tD('actions.upload')}
              </Button>
              <Button variant="secondary" size="sm" type="button">
                <IhIcon name="users" size={13} />
                {tD('actions.share')}
              </Button>
              <Button variant="secondary" size="sm" type="button">
                <IhIcon name="inbox" size={13} />
                {tD('actions.export')}
              </Button>
              <Button
                variant="secondary"
                size="sm"
                type="button"
                data-testid="project-detail-reports"
                onClick={() => router.push(projectDetailDsHref(projectId, 'reports') as Route)}
              >
                {tD('tabs.reports')}
              </Button>
              <Button
                variant="primary"
                size="sm"
                type="button"
                data-testid="project-detail-ai"
                onClick={() => router.push(projectDetailDsHref(projectId, 'ai-insights') as Route)}
              >
                <IhIcon name="sparkles" size={13} />
                {tD('actions.ai')}
              </Button>
            </div>
          </div>

          <div className="proj-detail-ds__hero-stats">
            <div className="proj-detail-ds__stat">
              <span>{tD('hero.stage')}</span>
              <strong>
                {model.stage ? getStageLabel(model.stage) : getStatusLabel(model.status)}
              </strong>
            </div>
            <div className="proj-detail-ds__stat">
              <span>{tD('hero.progress')}</span>
              <strong>{model.completion == null ? '—' : `${model.completion}%`}</strong>
            </div>
            <div className="proj-detail-ds__stat">
              <span>{tD('hero.investmentStatus')}</span>
              <strong>
                {model.investmentStatus
                  ? tD(`investmentStatus.${model.investmentStatus}`)
                  : '—'}
              </strong>
            </div>
            <div className="proj-detail-ds__stat">
              <span>{tD('hero.lastUpdated')}</span>
              <strong>{formatShortDate(model.lastUpdated, locale)}</strong>
            </div>
          </div>

          {model.healthScore != null || model.aiConfidence != null ? (
          <div className="proj-detail-ds__score-row">
            {model.healthScore != null ? (
            <div className="proj-detail-ds__score">
              <div
                className="proj-detail-ds__score-ring"
                style={{ ['--pct' as string]: model.healthScore }}
                aria-hidden="true"
              />
              <div>
                <em>{tD('hero.healthScore')}</em>
                <strong>{model.healthScore}</strong>
              </div>
            </div>
            ) : null}
            {model.aiConfidence != null ? (
            <div className="proj-detail-ds__score">
              <div
                className="proj-detail-ds__score-ring"
                style={{ ['--pct' as string]: model.aiConfidence }}
                aria-hidden="true"
              />
              <div>
                <em>{tD('hero.aiConfidence')}</em>
                <strong>{model.aiConfidence}</strong>
              </div>
            </div>
            ) : null}
          </div>
          ) : null}
        </div>
      </section>

      <section className="proj-detail-ds__kpi-row" aria-label={tD('kpis.aria')}>
        {KPI_ORDER.map((key) => {
          const value = kpiValue(key, {
            acquisition: model.kpis.acquisition.value,
            equity: model.kpis.equityRequired.value,
            budget: budgetLabel,
            spent: spentLabel,
            remaining: remainingLabel,
            roi: model.kpis.expectedRoi.value,
            units: model.kpis.units.value,
            investors: investorCount && investorCount > 0 ? String(investorCount) : null,
            completion: model.kpis.completion.value,
            target: model.kpis.targetDelivery.value,
          });
          return (
            <KpiCard
              key={key}
              className="proj-detail-ds__kpi"
              label={tD(`kpis.${key}`)}
              value={loading ? '—' : value ?? '—'}
              hint={value ? tD(`kpis.hints.${key}`) : tD('empty.short')}
              icon={<IhIcon name={KPI_ICONS[key]} size={16} />}
            />
          );
        })}
      </section>

      <div className="proj-detail-ds__tabs-bar">
        {usesPhases && projectPhases.length ? (
          <Select
            className="proj-detail-ds__phase-filter"
            label={locale === 'tr' ? 'Faz' : 'Phase'}
            value={phaseId}
            onChange={(event) => onPhaseChange(event.target.value)}
          >
            <option value="">{locale === 'tr' ? 'Tüm Proje' : 'Entire Project'}</option>
            {projectPhases.map((phase) => (
              <option key={phase.id} value={phase.id}>
                {phase.name}
              </option>
            ))}
          </Select>
        ) : null}
        <Tabs
          className="proj-detail-ds__tabs"
          tabs={tabItems}
          activeId={shownTab === 'timeline' ? 'tasks' : shownTab}
          onChange={onTabChange}
          ariaLabel={tD('tabs.aria')}
        />
        <div className="proj-detail-ds__tabs-mobile">
          <Select
            className="proj-detail-ds__tabs-select"
            label={tD('tabs.aria')}
            value={shownTab === 'timeline' ? 'tasks' : shownTab}
            onChange={(e) => onTabChange(e.target.value)}
          >
            {(resolvedTab === 'reports' || resolvedTab === 'ai-insights'
              ? [...PROJECT_DETAIL_NAV_TABS, resolvedTab]
              : [...PROJECT_DETAIL_NAV_TABS]
            )
              .filter((id) => id !== 'phases' || usesPhases)
              .map((id) => (
              <option key={id} value={id}>
                {tD(`tabs.${id}`)}
              </option>
            ))}
          </Select>
        </div>
      </div>

      {error ? <div className="proj-detail-ds__banner">{error}</div> : null}

      {shownTab === 'overview' ? (
        <OverviewTab
          model={model}
          tD={tD}
          getStatusLabel={getStatusLabel}
          getPriorityLabel={getPriorityLabel}
          locale={locale}
          activity={activity}
          alerts={alerts}
          media={media}
          location={locationView.location}
          amenities={locationView.amenities}
          refreshState={refreshState}
          refreshError={refreshError}
          onRefreshLocation={refreshLocation}
          phaseMetrics={{ units: unitSummary, finance: financials?.summary ?? null }}
        />
      ) : null}
      {resolvedTab === 'construction' ? (
        <ConstructionTab model={model} tD={tD} locale={locale} />
      ) : null}
      {resolvedTab === 'units' ? (
        <UnitsTab projectId={projectId} tD={tD} locale={locale} phaseScope={usesPhases ? phaseId : ''} usesPhases={usesPhases} />
      ) : null}
      {shownTab === 'phases' ? <ProjectPhaseEditor projectId={projectId} /> : null}
      {resolvedTab === 'financial' ? (
        <FinancialTab
          summary={financeSummary}
          showInvestorTerms={canViewFinancials}
          loading={financialsLoading}
          error={financialsError}
          audience={financeAudience}
          onAudience={setFinanceAudience}
          tD={tD}
          locale={locale}
        />
      ) : null}
      {resolvedTab === 'investors' ? (
        <InvestorsTab items={investorItems} tD={tD} locale={locale} />
      ) : null}
      {resolvedTab === 'documents' ? <DocumentsTab tD={tD} projectId={projectId} /> : null}
      {resolvedTab === 'tasks' || resolvedTab === 'timeline' ? (
        <WorkTab
          view={resolvedTab === 'timeline' ? 'timeline' : 'tasks'}
          projectId={projectId}
          model={model}
          tD={tD}
          tDs={tDs}
          getPriorityLabel={getPriorityLabel}
          locale={locale}
        />
      ) : null}
      {resolvedTab === 'reports' ? <ReportsTab model={model} tD={tD} locale={locale} /> : null}
      {resolvedTab === 'ai-insights' ? <AiInsightsTab model={model} tD={tD} /> : null}
    </div>
  );
}

type Model = ReturnType<typeof buildProjectDetailDsModel>;
type TranslateFn = ReturnType<typeof useTranslations>;

const MISSING_DATA_NOTICE_KEYS = {
  'No project manager assigned': 'notices.missingManager',
  'No project team members': 'notices.missingTeam',
  'Budget data missing': 'notices.missingBudget',
  'Completion percentage missing': 'notices.missingCompletion',
} as const;

const ACTIVITY_EVENT_KEYS = {
  'activity.project.created': 'activityEvents.created',
  'activity.project.updated': 'activityEvents.updated',
  'activity.project.financial_updated': 'activityEvents.financialUpdated',
  'activity.project.schedule_updated': 'activityEvents.scheduleUpdated',
  'activity.project.address_updated': 'activityEvents.addressUpdated',
  'activity.project.manager_changed': 'activityEvents.managerChanged',
  'activity.project.archived': 'activityEvents.archived',
  'activity.project.restored': 'activityEvents.restored',
  'activity.project.status_changed': 'activityEvents.statusChanged',
  'activity.project.team_member_added': 'activityEvents.teamMemberAdded',
  'activity.project.team_member_updated': 'activityEvents.teamMemberUpdated',
  'activity.project.team_member_removed': 'activityEvents.teamMemberRemoved',
} as const;

function missingDataNoticeKey(
  title: string,
): (typeof MISSING_DATA_NOTICE_KEYS)[keyof typeof MISSING_DATA_NOTICE_KEYS] | null {
  return MISSING_DATA_NOTICE_KEYS[title as keyof typeof MISSING_DATA_NOTICE_KEYS] ?? null;
}

function activityEventLabel(title: string, tD: TranslateFn): string {
  const key = ACTIVITY_EVENT_KEYS[title as keyof typeof ACTIVITY_EVENT_KEYS];
  if (key) return tD(key);
  if (title.startsWith('activity.')) return tD('activityEvents.generic');
  return title;
}

function OverviewTab({
  model,
  tD,
  getStatusLabel,
  getPriorityLabel,
  locale,
  activity,
  alerts,
  media,
  location,
  amenities,
  refreshState,
  refreshError,
  onRefreshLocation,
  phaseMetrics,
}: {
  model: Model;
  tD: TranslateFn;
  getStatusLabel: (s: string) => string;
  getPriorityLabel: (s: string) => string;
  locale: string;
  activity: ProjectActivityItem[];
  alerts: ProjectAlertItem[];
  media: OverviewMedia;
  location: OverviewMedia['location'];
  amenities: AmenityItem[];
  refreshState: string | null;
  refreshError: string | null;
  onRefreshLocation: () => void;
  phaseMetrics?: {
    units: Record<string, MetricValue> | null;
    finance: Record<string, MetricValue> | null;
  };
}) {
  const realAlerts = alerts.filter((item) => missingDataNoticeKey(item.title) == null);
  const missingDetails = alerts.filter((item) => missingDataNoticeKey(item.title) != null);
  const budgetAlerts = realAlerts.filter((item) => item.category === 'budget');
  const constructionAlerts = realAlerts.filter(
    (item) => item.category === 'construction' || item.category === 'schedule',
  );
  const otherAlerts = realAlerts.filter(
    (item) => item.category !== 'budget' && item.category !== 'construction' && item.category !== 'schedule',
  );
  const tr = locale === 'tr';
  const shown = (metric: MetricValue | undefined) =>
    metric && metric.available && metric.value !== null && metric.value !== undefined
      ? String(metric.value)
      : '—';
  const phaseCards: Array<[string, string]> = [
    [tr ? 'Toplam ünite' : 'Total units', shown(phaseMetrics?.units?.total_units)],
    ['Available', shown(phaseMetrics?.units?.available)],
    ['Reserved', shown(phaseMetrics?.units?.reserved)],
    ['Under Contract', shown(phaseMetrics?.units?.under_contract)],
    ['Closed', shown(phaseMetrics?.units?.sold)],
    [tr ? 'Toplam liste değeri' : 'Total list value', shown(phaseMetrics?.units?.total_list_value)],
    [tr ? 'Sözleşmeli satış değeri' : 'Contracted sales value', shown(phaseMetrics?.finance?.contracted_sales_value)],
    [tr ? 'Gerçekleşen tahsilat' : 'Realized collections', shown(phaseMetrics?.finance?.verified_collections)],
    [tr ? 'Kalan alacak' : 'Remaining receivable', shown(phaseMetrics?.finance?.remaining_receivable)],
    [tr ? 'Yatırımcı sermayesi' : 'Investor capital', shown(phaseMetrics?.finance?.investor_committed_capital)],
    [tr ? 'Yatırımcı sözleşmeli kârı' : 'Investor contracted profit', shown(phaseMetrics?.finance?.investor_contracted_profit)],
    [tr ? 'İç proje kâr tahmini' : 'Internal project profit estimate', shown(phaseMetrics?.finance?.total_project_profit)],
    [tr ? 'Investhome kalan kâr tahmini' : 'Investhome remaining profit estimate', shown(phaseMetrics?.finance?.investhome_estimated_profit)],
  ];
  return (
    <>
      <ProjectsDetailDigitalTwin
        locale={locale}
        gallery={media.gallery}
        location={location}
        mediaStats={media.mediaStats}
        amenities={amenities}
        onRefreshLocation={onRefreshLocation}
        refreshState={refreshState}
        refreshError={refreshError}
      />
      <section className="proj-detail-ds__kpi-row" aria-label={tr ? 'Faz özeti' : 'Phase summary'} data-testid="project-phase-kpis">
        {phaseCards.map(([label, value]) => (
          <KpiCard key={label} className="proj-detail-ds__kpi" label={label} value={value} />
        ))}
      </section>
      <div className="proj-detail-ds__overview">
        <div className="proj-detail-ds__overview-main">
          <article className="proj-detail-ds__panel">
            <h3>{tD('overview.summary')}</h3>
            <p className="proj-detail-ds__panel-sub">{model.description || tD('empty.short')}</p>
            <div className="proj-detail-ds__kv">
              <div className="proj-detail-ds__kv-row">
                <span>{tD('overview.status')}</span>
                <strong>
                  <StatusChip tone={statusTone(model.status)}>
                    {getStatusLabel(model.status)}
                  </StatusChip>
                </strong>
              </div>
              {model.scheduleDates[0] ? (
              <div className="proj-detail-ds__kv-row">
                <span>{tD('overview.nextMilestone')}</span>
                <strong>{tD(`schedule.${model.scheduleDates[0].labelKey}`)}</strong>
              </div>
              ) : null}
              {model.manager ? (
              <div className="proj-detail-ds__kv-row">
                <span>{tD('overview.manager')}</span>
                <strong>{model.manager}</strong>
              </div>
              ) : null}
              {model.contractor ? (
              <div className="proj-detail-ds__kv-row">
                <span>{tD('overview.contractor')}</span>
                <strong>{model.contractor}</strong>
              </div>
              ) : null}
              {model.architect ? (
              <div className="proj-detail-ds__kv-row">
                <span>{tD('overview.architect')}</span>
                <strong>{model.architect}</strong>
              </div>
              ) : null}
              {model.constructionCompany ? (
              <div className="proj-detail-ds__kv-row">
                <span>{tD('overview.constructionCompany')}</span>
                <strong>{model.constructionCompany}</strong>
              </div>
              ) : null}
              <div className="proj-detail-ds__kv-row" data-testid="project-risk-level">
                <span>{tD('overview.risk')}</span>
                <strong className="proj-detail-ds__quiet">{tD('notices.riskUncalculated')}</strong>
              </div>
              <div className="proj-detail-ds__kv-row">
                <span>{tD('overview.priority')}</span>
                <strong>
                  <StatusChip tone={priorityTone(model.priority)}>
                    {getPriorityLabel(model.priority)}
                  </StatusChip>
                </strong>
              </div>
            </div>
          </article>

          {model.completion != null || model.scheduleDates.length > 0 || media.permits.length > 0 ? (
          <article className="proj-detail-ds__panel proj-detail-ds__progress-hero">
            <h3>{tD('overview.constructionProgress')}</h3>
            {model.completion != null ? (
            <div className="proj-detail-ds__progress-big">
              <span className="proj-detail-ds__panel-sub">{tD('overview.completionLabel')}</span>
              <strong>{`${model.completion}%`}</strong>
              <ProgressBar value={model.completion} />
            </div>
            ) : (
              <p className="proj-detail-ds__quiet">{tD('empty.short')}</p>
            )}
            {model.scheduleDates.length > 0 ? (
            <div className="proj-detail-ds__milestone-list" aria-label={tD('overview.milestones')}>
              {model.scheduleDates.map((item) => (
                <div key={item.id} className="proj-detail-ds__milestone">
                  <span className="proj-detail-ds__milestone-dot" aria-hidden="true" />
                  <span>{tD(`schedule.${item.labelKey}`)}</span>
                  <em>{formatShortDate(item.date, locale)}</em>
                </div>
              ))}
            </div>
            ) : null}
          </article>
          ) : null}
        </div>

        <aside className="proj-detail-ds__widget-grid" aria-label={tD('overview.widgets')}>
          {activity.length > 0 ? (
          <article className="proj-detail-ds__panel">
            <h3>{tD('overview.recentActivity')}</h3>
            <ul className="proj-detail-ds__list">
              {activity.map((item) => (
                <li key={item.id}>
                  <strong>{activityEventLabel(item.title, tD)}</strong>
                  <span>{item.description || formatShortDate(item.created_at, locale)}</span>
                </li>
              ))}
            </ul>
          </article>
          ) : null}
          {missingDetails.length > 0 ? (
          <article className="proj-detail-ds__panel" data-testid="project-missing-details">
            <h3>{tD('overview.missingDetails')}</h3>
            {missingDetails.map((item) => {
              const key = missingDataNoticeKey(item.title);
              return (
                <p key={item.id} className="proj-detail-ds__quiet">
                  {key ? tD(key) : item.title}
                </p>
              );
            })}
          </article>
          ) : null}
          {otherAlerts.length > 0 ? (
          <article className="proj-detail-ds__panel">
            <h3>{tD('overview.aiAlerts')}</h3>
            {otherAlerts.map((item) => (
              <div key={item.id} className={`proj-detail-ds__alert is-${item.severity === 'critical' || item.severity === 'high' ? 'critical' : item.severity === 'medium' ? 'warning' : 'info'}`}>
                {item.title}
              </div>
            ))}
          </article>
          ) : null}
          {budgetAlerts.length > 0 ? (
          <article className="proj-detail-ds__panel">
            <h3>{tD('overview.budgetAlerts')}</h3>
            {budgetAlerts.map((item) => (
              <div key={item.id} className="proj-detail-ds__alert is-warning">
                {item.title}
              </div>
            ))}
          </article>
          ) : null}
          {constructionAlerts.length > 0 ? (
          <article className="proj-detail-ds__panel">
            <h3>{tD('overview.constructionAlerts')}</h3>
            {constructionAlerts.map((item) => (
              <div key={item.id} className="proj-detail-ds__alert is-info">
                {item.title}
              </div>
            ))}
          </article>
          ) : null}
          {model.notes ? (
          <article className="proj-detail-ds__panel">
            <h3>{tD('overview.notes')}</h3>
            <p className="proj-detail-ds__panel-sub">{model.notes}</p>
          </article>
          ) : null}
        </aside>
      </div>
    </>
  );
}

function ConstructionTab({
  model,
  tD,
  locale,
}: {
  model: Model;
  tD: TranslateFn;
  locale: string;
}) {
  return (
    <div className="proj-detail-ds__overview">
      <article className="proj-detail-ds__panel proj-detail-ds__progress-hero" style={{ gridColumn: '1 / -1' }}>
        <h3>{tD('construction.title')}</h3>
        <p className="proj-detail-ds__panel-sub">{tD('construction.subtitle')}</p>
        <div className="proj-detail-ds__progress-big">
          <strong>{model.completion == null ? '—' : `${model.completion}%`}</strong>
          {model.completion == null ? null : <ProgressBar value={model.completion} />}
        </div>
        <div className="proj-detail-ds__milestone-list">
          {model.scheduleDates.length === 0 ? (
            <p className="proj-detail-ds__quiet">{tD('empty.short')}</p>
          ) : (
            model.scheduleDates.map((item) => (
              <div key={item.id} className="proj-detail-ds__milestone">
                <span className="proj-detail-ds__milestone-dot" />
                <span>{tD(`schedule.${item.labelKey}`)}</span>
                <em>{formatShortDate(item.date, locale)}</em>
              </div>
            ))
          )}
        </div>
        <div className="proj-detail-ds__kv">
          <div className="proj-detail-ds__kv-row">
            <span>{tD('overview.permitStatus')}</span>
            <strong>{tD('empty.permits')}</strong>
          </div>
          <div className="proj-detail-ds__kv-row">
            <span>{tD('overview.contractor')}</span>
            <strong>{model.contractor || tD('empty.contractor')}</strong>
          </div>
          <div className="proj-detail-ds__kv-row">
            <span>{tD('overview.upcomingInspection')}</span>
            <strong>{tD('empty.permits')}</strong>
          </div>
        </div>
      </article>
    </div>
  );
}

type LiveUnit = {
  id?: string;
  unit?: string;
  unit_label?: string | null;
  building_label?: string | null;
  floor_label?: string | null;
  floor_number?: number | null;
  bedrooms?: string | number | null;
  bathrooms?: string | number | null;
  square_feet?: string | number | null;
  availability_status?: string | null;
  sales_status?: string | null;
  sales_market?: string | null;
  price?: string | number | null;
  price_available?: boolean;
  sale_amount?: string | number | null;
  sale_amount_available?: boolean;
  collected_amount?: string | number | null;
  collected_available?: boolean;
  payment_plan?: string | null;
};

type SalesMarketFilter = 'all' | 'turkey' | 'usa';

function metricCount(summary: Record<string, MetricValue> | null, key: string): number | null {
  const metric = summary?.[key];
  if (!metric || metric.available === false || metric.value == null) return null;
  const value = typeof metric.value === 'number' ? metric.value : Number(metric.value);
  return Number.isFinite(value) ? value : null;
}

function unitHeading(unit: LiveUnit): string {
  if (unit.unit_label) return unit.unit_label;
  if (unit.building_label && unit.unit) return `${unit.building_label} · ${unit.unit}`;
  return unit.unit || '—';
}

function unitText(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—';
  return String(value);
}

function formatListPrice(value: string | number | null | undefined, locale: string): string {
  if (value === null || value === undefined || value === '') return '—';
  const amount = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(amount)) return String(value);
  const intlLocale = locale === 'tr' ? 'tr-TR' : 'en-US';
  return new Intl.NumberFormat(intlLocale, {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(amount);
}

function formatArea(value: string | number | null | undefined, locale: string): string {
  if (value === null || value === undefined || value === '') return '—';
  const amount = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(amount)) return String(value);
  const intlLocale = locale === 'tr' ? 'tr-TR' : 'en-US';
  return `${new Intl.NumberFormat(intlLocale, { maximumFractionDigits: 0 }).format(amount)} sf`;
}

function UnitsTab({
  projectId,
  tD,
  locale,
  phaseScope,
  usesPhases = false,
}: {
  projectId: string;
  tD: TranslateFn;
  locale: string;
  phaseScope?: string;
  usesPhases?: boolean;
}) {
  const [units, setUnits] = useState<LiveUnit[]>([]);
  const [summary, setSummary] = useState<Record<string, MetricValue> | null>(null);
  const [market, setMarket] = useState<SalesMarketFilter>('all');
  const [phaseId, setPhaseId] = useState('');
  const [phases, setPhases] = useState<Array<{ id: string; name: string }>>([]);
  const controlled = phaseScope !== undefined;
  const scopedPhase = controlled ? phaseScope : phaseId;
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const params = {
          page_size: 100,
          sort_by: 'display_id' as const,
          sort_order: 'asc' as const,
          ...(market === 'all' ? {} : { sales_market: market }),
          ...(scopedPhase ? { phase_id: scopedPhase } : {}),
        };
        const first = await fetchProjectUnits(projectId, { ...params, page: 1 });
        let items = [...first.items] as LiveUnit[];
        for (let page = 2; page <= first.pages; page += 1) {
          const next = await fetchProjectUnits(projectId, { ...params, page });
          items = items.concat(next.items as LiveUnit[]);
        }
        if (!cancelled) {
          setUnits(items);
          setSummary(first.summary);
        }
      } catch {
        if (!cancelled) {
          setUnits([]);
          setSummary(null);
          setError(tD('units.loadError'));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [market, projectId, scopedPhase, tD]);

  useEffect(() => {
    let cancelled = false;
    void fetchProjectPhases(projectId)
      .then((items) => {
        if (!cancelled) setPhases(items.filter((item) => item.active).map((item) => ({ id: item.id, name: item.name })));
      })
      .catch(() => {
        if (!cancelled) setPhases([]);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const counts = {
    total: metricCount(summary, 'total_physical_units'),
    turkey: metricCount(summary, 'turkey_allocation'),
    usa: metricCount(summary, 'usa_allocation'),
    sold: metricCount(summary, 'sold_units'),
    available: metricCount(summary, 'available_for_sale'),
  };

  return (
    <section className="proj-detail-ds__units" aria-label={tD('units.aria')} data-testid="project-units-live">
      <div className="proj-detail-ds__unit-toolbar">
        <div className="proj-detail-ds__unit-stats" data-testid="project-unit-counts">
          {(
            [
              ['total', counts.total],
              ['turkey', counts.turkey],
              ['usa', counts.usa],
              ['sold', counts.sold],
              ['available', counts.available],
            ] as const
          ).map(([key, value]) => (
            <div key={key} className="proj-detail-ds__stat">
              <span>{tD(`units.kpi.${key}`)}</span>
              <strong>{value == null ? '—' : value}</strong>
            </div>
          ))}
        </div>
        {usesPhases && !controlled && phases.length ? (
          <Select
            label={locale === 'tr' ? 'Faz' : 'Phase'}
            value={scopedPhase}
            onChange={(event) => setPhaseId(event.target.value)}
          >
            <option value="">{locale === 'tr' ? 'Tüm Proje' : 'Entire Project'}</option>
            {phases.map((phase) => (
              <option key={phase.id} value={phase.id}>
                {phase.name}
              </option>
            ))}
          </Select>
        ) : null}
        <div className="proj-detail-ds__work-views" role="tablist" aria-label={tD('units.marketFilter')}>
          {(['all', 'turkey', 'usa'] as const).map((value) => (
            <button
              key={value}
              type="button"
              className="proj-detail-ds__work-view"
              aria-pressed={market === value}
              data-testid={`project-units-market-${value}`}
              onClick={() => setMarket(value)}
            >
              {tD(`units.markets.${value}`)}
            </button>
          ))}
        </div>
      </div>
      {loading ? <p className="proj-detail-ds__quiet">{tD('units.loading')}</p> : null}
      {error ? <p className="proj-detail-ds__banner">{error}</p> : null}
      {!loading && !error && units.length === 0 ? (
        <p
          className="proj-detail-ds__quiet"
          data-testid={scopedPhase && market === 'all' ? 'project-units-phase-empty' : undefined}
        >
          {market !== 'all'
            ? tD('units.marketEmpty')
            : scopedPhase
              ? tD('units.phaseEmpty')
              : tD('units.empty')}
        </p>
      ) : null}
      {units.map((unit) => {
        const salesStatus = unit.sales_status || 'not_for_sale';
        const availability = unit.availability_status || 'not_released';
        const floor = unit.floor_label || (unit.floor_number != null ? String(unit.floor_number) : '—');
        const marketLabel = unit.sales_market
          ? tD(`units.markets.${unit.sales_market}`)
          : tD('units.marketUnallocated');
        return (
          <article key={unit.id || unit.unit} className="proj-detail-ds__unit">
            <div className="proj-detail-ds__unit-top">
              <span className="proj-detail-ds__unit-code">{unitHeading(unit)}</span>
              <span className="proj-detail-ds__unit-chips">
                <StatusChip tone="default">{marketLabel}</StatusChip>
                <StatusChip tone={salesTone(salesStatus)}>{tD(`units.sales.${salesStatus}`)}</StatusChip>
              </span>
            </div>
            <div className="proj-detail-ds__unit-meta">
              <div>
                <span>{tD('units.floor')}</span>
                <strong>{floor}</strong>
              </div>
              <div>
                <span>{tD('units.bedBath')}</span>
                <strong>
                  {unitText(unit.bedrooms)} / {unitText(unit.bathrooms)}
                </strong>
              </div>
              <div>
                <span>{tD('units.squareFeet')}</span>
                <strong>{formatArea(unit.square_feet, locale)}</strong>
              </div>
              <div>
                <span>{tD('units.availability')}</span>
                <strong>{tD(`units.availabilityStatus.${availability}`)}</strong>
              </div>
              <div>
                <span>{tD('units.salesStatus')}</span>
                <strong>{tD(`units.sales.${salesStatus}`)}</strong>
              </div>
              <div>
                <span>{tD('units.price')}</span>
                <strong>
                  {unit.price_available ? formatListPrice(unit.price, locale) : tD('units.priceUnavailable')}
                </strong>
              </div>
              <div>
                <span>{tD('units.contracted')}</span>
                <strong>
                  {unit.sale_amount_available
                    ? formatListPrice(unit.sale_amount, locale)
                    : '—'}
                </strong>
              </div>
              <div>
                <span>{tD('units.collected')}</span>
                <strong>
                  {unit.collected_available
                    ? formatListPrice(unit.collected_amount, locale)
                    : '—'}
                </strong>
              </div>
              <div>
                <span>{tD('units.paymentPlan')}</span>
                <strong>{unit.payment_plan || '—'}</strong>
              </div>
            </div>
          </article>
        );
      })}
    </section>
  );
}

function FinancialTab({
  summary,
  showInvestorTerms,
  loading,
  error,
  audience,
  onAudience,
  tD,
  locale,
}: {
  summary: Record<string, MetricValue> | null;
  showInvestorTerms: boolean;
  loading: boolean;
  error: boolean;
  audience: 'internal' | 'customer';
  onAudience: (audience: 'internal' | 'customer') => void;
  tD: TranslateFn;
  locale: string;
}) {
  const sources: Array<[string, string]> = [
    ['budget', 'total_project_cost'],
    ['estimatedCost', 'estimated_cost'],
    ['actualCost', 'actual_cost'],
    ['remainingBudget', 'remaining_budget'],
    ['financing', 'financing'],
    ['profitability', 'total_project_profit'],
  ];
  if (audience === 'internal') {
    sources.push(
      ['contractedSales', 'contracted_sales_value'],
      ['collections', 'verified_collections'],
      ['receivable', 'remaining_receivable'],
      ['commission', 'commission_amount'],
      ['commissionPaid', 'commission_paid'],
      ['commissionRemaining', 'commission_remaining'],
    );
  }
  if (showInvestorTerms) {
    sources.push(
      ['investorCapital', 'investor_committed_capital'],
      ['investorProfit', 'investor_contracted_profit'],
      ['investorReturn', 'investor_total_return'],
      ['investhomeProfit', 'investhome_estimated_profit'],
    );
  }
  const metrics: Array<{ key: string; value: string }> = sources.map(([key, source]) => ({
    key,
    value: metricText(summary?.[source], locale) ?? '—',
  }));

  return (
    <div data-testid="project-finance-tab">
      {showInvestorTerms ? (
        <div className="proj-detail-ds__work-views" role="tablist" aria-label={tD('financial.aria')}>
          <button
            type="button"
            className="proj-detail-ds__work-view"
            aria-pressed={audience === 'internal'}
            onClick={() => onAudience('internal')}
          >
            {tD('financial.metrics.audienceInternal')}
          </button>
          <button
            type="button"
            className="proj-detail-ds__work-view"
            aria-pressed={audience === 'customer'}
            onClick={() => onAudience('customer')}
          >
            {tD('financial.metrics.audienceCustomer')}
          </button>
        </div>
      ) : (
        <p className="proj-detail-ds__quiet">{tD('financial.metrics.restricted')}</p>
      )}
      {loading ? <p className="proj-detail-ds__quiet">{tD('financial.metrics.loading')}</p> : null}
      {error ? <div className="proj-detail-ds__banner">{tD('financial.metrics.loadError')}</div> : null}
      <section className="proj-detail-ds__fin-grid" aria-label={tD('financial.aria')}>
        {metrics.map((m) => (
          <article key={m.key} className="proj-detail-ds__fin-metric" data-testid={`project-finance-${m.key}`}>
            <span>{tD(`financial.metrics.${m.key}`)}</span>
            <strong>{m.value}</strong>
          </article>
        ))}
      </section>
    </div>
  );
}

function InvestorsTab({
  items,
  tD,
  locale,
}: {
  items: Array<Record<string, unknown>>;
  tD: TranslateFn;
  locale: string;
}) {
  if (items.length === 0) {
    return <p className="proj-detail-ds__quiet">{tD('empty.short')}</p>;
  }
  return (
    <div className="proj-detail-ds__table-wrap">
      <table className="proj-detail-ds__table" aria-label={tD('investors.aria')}>
        <thead>
          <tr>
            <th>{tD('investors.columns.name')}</th>
            <th>{tD('investors.columns.investment')}</th>
            <th>{tD('investors.columns.ownership')}</th>
            <th>{tD('investors.columns.return')}</th>
            <th>{tD('investors.columns.status')}</th>
            <th>{tD('investors.columns.documents')}</th>
            <th>{tD('investors.columns.communication')}</th>
          </tr>
        </thead>
        <tbody>
          {items.map((inv) => {
            const id = String(inv.commitment_id ?? inv.investor_id ?? inv.investor_name);
            const name = typeof inv.investor_name === 'string' ? inv.investor_name : '—';
            const committed = typeof inv.committed_amount === 'number' ? inv.committed_amount : null;
            const contracted =
              typeof inv.contracted_profit === 'number' || typeof inv.contracted_profit === 'string'
                ? Number(inv.contracted_profit)
                : null;
            const status = typeof inv.status === 'string' ? inv.status : null;
            const last = typeof inv.last_activity === 'string' ? inv.last_activity : null;
            return (
              <tr key={id}>
                <td>
                  <div className="proj-detail-ds__person">
                    <span>{name}</span>
                  </div>
                </td>
                <td>{committed == null ? '—' : formatCompactCurrency(committed, locale)}</td>
                <td>—</td>
                <td>
                  {contracted == null || Number.isNaN(contracted)
                    ? '—'
                    : formatCompactCurrency(contracted, locale)}
                </td>
                <td>{status ?? '—'}</td>
                <td>—</td>
                <td>{formatShortDate(last, locale)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function WorkTab({
  view,
  projectId,
  model,
  tD,
  tDs,
  getPriorityLabel,
  locale,
}: {
  view: 'tasks' | 'timeline';
  projectId: string;
  model: Model;
  tD: TranslateFn;
  tDs: TranslateFn;
  getPriorityLabel: (s: string) => string;
  locale: string;
}) {
  const router = useRouter();
  return (
    <div data-testid="project-work-tab">
      <div className="proj-detail-ds__work-views" role="tablist" aria-label={tD('tabs.tasks')}>
        <button
          type="button"
          className="proj-detail-ds__work-view"
          aria-pressed={view === 'tasks'}
          data-testid="project-work-tasks"
          onClick={() => router.push(projectDetailDsHref(projectId, 'tasks') as Route)}
        >
          {tD('work.tasks')}
        </button>
        <button
          type="button"
          className="proj-detail-ds__work-view"
          aria-pressed={view === 'timeline'}
          data-testid="project-work-timeline"
          onClick={() => router.push(projectDetailDsHref(projectId, 'timeline') as Route)}
        >
          {tD('work.timeline')}
        </button>
      </div>
      {view === 'tasks' ? (
        <TasksTab
          model={model}
          tD={tD}
          tDs={tDs}
          getPriorityLabel={getPriorityLabel}
          locale={locale}
        />
      ) : (
        <TimelineTab model={model} tD={tD} locale={locale} />
      )}
    </div>
  );
}

function DocumentsTab({
  tD,
  projectId,
}: {
  tD: TranslateFn;
  projectId: string;
}) {
  const tCommon = useTranslations('common');
  const [records, setRecords] = useState<OverviewDocument[]>([]);
  const [recordsState, setRecordsState] = useState<'loading' | 'ready' | 'error'>('loading');
  const [folders, setFolders] = useState<CreativeStudioMediaFolder[]>([]);
  const [foldersLoading, setFoldersLoading] = useState(true);
  const [foldersError, setFoldersError] = useState<string | null>(null);
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);
  const [assets, setAssets] = useState<CreativeStudioMediaAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setFoldersLoading(true);
    setFoldersError(null);
    setSelectedFolderId(null);
    void listCreativeStudioMediaFolders({
      linked_project_id: projectId,
      include_archived: false,
    })
      .then((res) => {
        if (cancelled) return;
        // Defense in depth: never surface another project's folders.
        setFolders(
          res.items.filter(
            (item) => item.linked_project_id === projectId && item.archived_at == null,
          ),
        );
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setFoldersError(uiError(err, tD('documents.foldersLoadError')));
        setFolders([]);
      })
      .finally(() => {
        if (!cancelled) setFoldersLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, tD]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    void listCreativeStudioMediaAssets({
      linked_project_id: projectId,
      folder_id: selectedFolderId ?? undefined,
      include_archived: false,
      page: 1,
      page_size: 100,
    })
      .then((res) => {
        if (cancelled) return;
        // Defense in depth: never surface another project's assets.
        setAssets(
          res.items.filter((item) => {
            if (item.linked_project_id !== projectId || item.archived_at != null) return false;
            if (selectedFolderId != null && item.folder_id !== selectedFolderId) return false;
            return true;
          }),
        );
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setLoadError(uiError(err, tD('documents.loadError')));
        setAssets([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, selectedFolderId, tD]);

  useEffect(() => {
    let cancelled = false;
    setRecordsState('loading');
    void fetchProjectDocuments(projectId, { page: 1, page_size: 100 })
      .then((page) => {
        if (cancelled) return;
        const next = page.items
          .map((item) => item as unknown as Record<string, unknown>)
          .filter((item) => isOperationalProjectDocument(item))
          .map((item) => readOverviewDocument(item))
          .filter((item): item is OverviewDocument => item != null);
        setRecords(next);
        setRecordsState('ready');
      })
      .catch(() => {
        if (cancelled) return;
        setRecords([]);
        setRecordsState('error');
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const folderById = useMemo(() => {
    const map = new Map<string, CreativeStudioMediaFolder>();
    for (const folder of folders) map.set(folder.id, folder);
    return map;
  }, [folders]);

  const projectRootIds = useMemo(() => {
    const ids = new Set<string>();
    for (const folder of folders) {
      if (folder.parent_id == null) ids.add(folder.id);
    }
    return ids;
  }, [folders]);

  const childFolders = useMemo(() => {
    const rows =
      selectedFolderId == null
        ? folders.filter((f) => f.parent_id != null && projectRootIds.has(f.parent_id))
        : folders.filter((f) => f.parent_id === selectedFolderId);
    return rows.slice().sort((a, b) => a.name.localeCompare(b.name));
  }, [folders, projectRootIds, selectedFolderId]);

  const breadcrumb = useMemo(() => {
    const trail: CreativeStudioMediaFolder[] = [];
    let current = selectedFolderId ? folderById.get(selectedFolderId) : undefined;
    const seen = new Set<string>();
    while (current && !seen.has(current.id)) {
      seen.add(current.id);
      trail.unshift(current);
      current = current.parent_id ? folderById.get(current.parent_id) : undefined;
    }
    // Hide the mapped Drive project root in the crumb — "All" already represents project scope.
    return trail.filter((folder) => folder.parent_id != null);
  }, [folderById, selectedFolderId]);

  const selectedFolder = selectedFolderId ? folderById.get(selectedFolderId) : undefined;
  const parentFolderId =
    selectedFolder?.parent_id && !projectRootIds.has(selectedFolder.parent_id)
      ? selectedFolder.parent_id
      : null;

  const folderLabel = (folderId: string | null | undefined) => {
    if (!folderId) return tD('documents.uncategorized');
    return folderById.get(folderId)?.name ?? tD('documents.uncategorized');
  };

  const fileTypeLabel = (asset: CreativeStudioMediaAsset) => {
    const mime = (asset.content_type || '').trim();
    if (mime) {
      const subtype = mime.split('/')[1]?.split(';')[0]?.trim();
      if (subtype) return subtype.toUpperCase();
    }
    const ext = asset.filename.includes('.')
      ? asset.filename.split('.').pop()?.trim()
      : null;
    return ext ? ext.toUpperCase() : tD('documents.unknownType');
  };

  const goToFolder = (folderId: string | null) => {
    setSelectedFolderId(folderId);
  };

  return (
    <div style={{ display: 'grid', gap: 12 }} data-testid="project-documents-tab">
      <article className="proj-detail-ds__panel" data-testid="project-record-documents">
        <h3>{tD('documents.recent')}</h3>
        {recordsState === 'loading' ? (
          <p className="proj-detail-ds__quiet">{tD('documents.loading')}</p>
        ) : recordsState === 'error' ? (
          <p className="proj-detail-ds__quiet" data-testid="project-record-documents-error">
            {tD('documents.loadError')}
          </p>
        ) : records.length === 0 ? (
          <p className="proj-detail-ds__quiet" data-testid="project-record-documents-empty">
            {tD('documents.recordsEmpty')}
          </p>
        ) : (
          <div className="proj-detail-ds__doc-list">
            {records.map((doc) => (
              <div
                key={doc.id}
                className="proj-detail-ds__doc-row"
                data-testid={`project-record-document-${doc.id}`}
              >
                <strong title={doc.title}>{doc.title}</strong>
                <span>{doc.documentType || doc.fileKind || '—'}</span>
                <a href={documentDownloadUrl(doc.id)}>{tCommon('download')}</a>
              </div>
            ))}
          </div>
        )}
      </article>
      <ProjectDriveSyncPanel projectId={projectId} />
      <ProjectAssistantPanel projectId={projectId} />

      <nav
        className="proj-detail-ds__crumb"
        aria-label={tD('documents.folderNav')}
        data-testid="project-documents-folder-nav"
      >
        <button
          type="button"
          className="proj-detail-ds__doc-nav-link"
          onClick={() => goToFolder(null)}
          aria-current={selectedFolderId == null ? 'page' : undefined}
          data-testid="project-documents-folder-all"
        >
          {tD('documents.allFolders')}
        </button>
        {breadcrumb.map((folder, index) => {
          const isLast = index === breadcrumb.length - 1;
          return (
            <span key={folder.id} className="proj-detail-ds__doc-nav-segment">
              <span className="proj-detail-ds__crumb-sep" aria-hidden>
                /
              </span>
              {isLast ? (
                <span className="proj-detail-ds__crumb-current" title={folder.name}>
                  {folder.name}
                </span>
              ) : (
                <button
                  type="button"
                  className="proj-detail-ds__doc-nav-link"
                  onClick={() => goToFolder(folder.id)}
                  data-testid={`project-documents-folder-crumb-${folder.id}`}
                >
                  {folder.name}
                </button>
              )}
            </span>
          );
        })}
        {selectedFolderId != null ? (
          <Button
            variant="ghost"
            size="sm"
            type="button"
            onClick={() => goToFolder(parentFolderId)}
            data-testid="project-documents-folder-back"
          >
            {parentFolderId == null ? tD('documents.backToAll') : tD('documents.backToParent')}
          </Button>
        ) : null}
      </nav>

      <section className="proj-detail-ds__doc-cats" aria-label={tD('documents.folders')}>
        {foldersLoading ? (
          <article className="proj-detail-ds__doc-cat">
            <strong>—</strong>
            <span>{tD('documents.foldersLoading')}</span>
          </article>
        ) : foldersError ? (
          <article className="proj-detail-ds__doc-cat" data-testid="project-documents-folders-error">
            <strong>—</strong>
            <span>{foldersError}</span>
          </article>
        ) : (
          <>
            <button
              type="button"
              className={`proj-detail-ds__doc-cat${selectedFolderId == null ? ' proj-detail-ds__doc-cat--active' : ''}`}
              onClick={() => goToFolder(null)}
              aria-pressed={selectedFolderId == null}
              data-testid="project-documents-folder-chip-all"
            >
              <strong>{tD('documents.allFolders')}</strong>
              <span>{tD('documents.recent')}</span>
            </button>
            {childFolders.length === 0 && selectedFolderId != null ? (
              <article className="proj-detail-ds__doc-cat">
                <strong>0</strong>
                <span>{tD('documents.noSubfolders')}</span>
              </article>
            ) : null}
            {childFolders.map((folder) => (
              <button
                key={folder.id}
                type="button"
                className={`proj-detail-ds__doc-cat${selectedFolderId === folder.id ? ' proj-detail-ds__doc-cat--active' : ''}`}
                onClick={() => goToFolder(folder.id)}
                aria-pressed={selectedFolderId === folder.id}
                title={folder.name}
                data-testid={`project-documents-folder-chip-${folder.id}`}
              >
                <strong>{folder.name}</strong>
                <span>{tD('documents.folder')}</span>
              </button>
            ))}
          </>
        )}
      </section>

      <article className="proj-detail-ds__panel" data-testid="project-drive-documents">
        <h3>
          {selectedFolder ? selectedFolder.name : tD('documents.drive')}
        </h3>
        {loading ? (
          <p className="proj-detail-ds__drive-empty" data-testid="project-documents-loading">
            {tD('documents.loading')}
          </p>
        ) : loadError ? (
          <div className="proj-detail-ds__drive-error" data-testid="project-documents-error">
            <p>{loadError}</p>
          </div>
        ) : assets.length === 0 ? (
          <p className="proj-detail-ds__drive-empty" data-testid="project-documents-empty">
            {selectedFolderId == null ? tD('documents.empty') : tD('documents.folderEmpty')}
          </p>
        ) : (
          <div className="proj-detail-ds__doc-list" data-testid="project-documents-list">
            {assets.slice(0, 50).map((doc) => {
              const isDrive = doc.source_type === 'google_drive';
              return (
                <div
                  key={doc.id}
                  className="proj-detail-ds__doc-row"
                  data-testid={`project-document-row-${doc.id}`}
                >
                  <strong title={doc.filename}>{doc.filename}</strong>
                  <span title={folderLabel(doc.folder_id)}>{folderLabel(doc.folder_id)}</span>
                  <span>
                    {fileTypeLabel(doc)} · {formatFileSize(doc.file_size)}
                  </span>
                  {isDrive ? (
                    <StatusChip tone="info">
                      <span data-testid={`project-document-drive-${doc.id}`}>
                        {tD('documents.sourceGoogleDrive')}
                      </span>
                    </StatusChip>
                  ) : (
                    <StatusChip tone="default">{tD('documents.sourceUpload')}</StatusChip>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </article>
    </div>
  );
}

function TasksTab({
  model,
  tD,
  tDs,
  getPriorityLabel,
  locale,
}: {
  model: Model;
  tD: TranslateFn;
  tDs: TranslateFn;
  getPriorityLabel: (s: string) => string;
  locale: string;
}) {
  if (model.tasks.length === 0) {
    return <p className="proj-detail-ds__quiet">{tD('empty.short')}</p>;
  }
  return (
    <section className="proj-detail-ds__tasks" aria-label={tD('tasks.aria')}>
      {model.tasks.map((task) => (
        <article key={task.id} className="proj-detail-ds__task">
          <div className="proj-detail-ds__task-title">
            <strong>{task.title}</strong>
            <span>
              {task.owner} · {tDs(`phases.${task.milestone}`)}
            </span>
            <ProgressBar value={task.progress} />
          </div>
          <StatusChip tone={priorityTone(task.priority)}>
            {getPriorityLabel(task.priority)}
          </StatusChip>
          <StatusChip tone={taskTone(task.status)}>
            {tD(`tasks.status.${task.status}`)}
          </StatusChip>
          <span>{formatShortDate(task.dueDate, locale)}</span>
          <span>{task.progress}%</span>
        </article>
      ))}
    </section>
  );
}

function TimelineTab({
  model,
  tD,
  locale,
}: {
  model: Model;
  tD: TranslateFn;
  locale: string;
}) {
  if (model.scheduleDates.length === 0) {
    return <p className="proj-detail-ds__quiet">{tD('empty.short')}</p>;
  }
  return (
    <section className="proj-detail-ds__timeline" aria-label={tD('timeline.aria')}>
      {model.scheduleDates.map((item) => (
        <div key={item.id} className="proj-detail-ds__tl-item">
          <div className="proj-detail-ds__tl-rail">
            <span className="proj-detail-ds__tl-dot" />
          </div>
          <article className="proj-detail-ds__tl-card">
            <strong>{tD(`schedule.${item.labelKey}`)}</strong>
            <span className="proj-detail-ds__panel-sub">{formatShortDate(item.date, locale)}</span>
          </article>
        </div>
      ))}
    </section>
  );
}

function ReportsTab({
  model,
  tD,
  locale,
}: {
  model: Model;
  tD: TranslateFn;
  locale: string;
}) {
  if (model.reports.length === 0) {
    return <p className="proj-detail-ds__quiet">{tD('empty.short')}</p>;
  }
  return (
    <section className="proj-detail-ds__reports" aria-label={tD('reports.aria')}>
      {model.reports.map((report) => (
        <article key={report.id} className="proj-detail-ds__report">
          <h3 className="proj-detail-ds__panel-title">
            {tD(`reports.types.${report.key}`)}
          </h3>
          <p className="proj-detail-ds__panel-sub">
            {tD('reports.updated', {
              date: formatShortDate(report.updatedAt, locale),
              pages: report.pages,
            })}
          </p>
          <Button variant="secondary" size="sm" type="button">
            <IhIcon name="inbox" size={13} />
            {tD('reports.export')}
          </Button>
        </article>
      ))}
    </section>
  );
}

function AiInsightsTab({ model, tD }: { model: Model; tD: TranslateFn }) {
  if (model.aiInsights.length === 0) {
    return <p className="proj-detail-ds__quiet">{tD('empty.short')}</p>;
  }
  return (
    <section className="proj-detail-ds__ai-grid" aria-label={tD('ai.aria')}>
      {model.aiInsights.map((insight) => (
        <article key={insight.id} className="proj-detail-ds__ai-card">
          <div className="proj-detail-ds__ai-card-top">
            <h3>{tD(`ai.cards.${insight.key}.title`)}</h3>
            <StatusChip tone={insight.tone}>{insight.delta}</StatusChip>
          </div>
          <div className="proj-detail-ds__ai-score">{insight.score}</div>
          <p>{tD(`ai.cards.${insight.key}.body`)}</p>
        </article>
      ))}
    </section>
  );
}

/** Compatibility export for existing route imports. */
export function ProjectDetailWorkspace(props: ProjectsDetailDsWorkspaceProps) {
  return <ProjectsDetailDsWorkspace {...props} />;
}

export type { ProjectDetailDsTab };
