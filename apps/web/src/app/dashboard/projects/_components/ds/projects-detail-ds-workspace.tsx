'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';

import {
  Button,
  KpiCard,
  ProgressBar,
  Select,
  StatusChip,
  Tabs,
} from '@investhome/ui';

import { useScreenshotDashboardInteractions } from '@/app/dashboard/_components/screenshot-dashboard-interactions';
import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';
import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';
import {
  listCreativeStudioMediaAssets,
  listCreativeStudioMediaFolders,
  type CreativeStudioMediaAsset,
  type CreativeStudioMediaFolder,
} from '@/lib/api/creative-studio';
import { formatFileSize } from '@/lib/api/documents';
import {
  fetchProjectDetail,
  fetchProjects,
  formatShortDate,
  type Project,
} from '@/lib/api/projects';
import { useProjectLabels } from '@/lib/i18n/project-labels';

import {
  buildProjectDetailDsModel,
  formatCompactCurrency,
  PROJECT_DETAIL_DS_TABS,
  priorityTone,
  projectDetailDsHref,
  resolveProjectDetailDsTab,
  statusTone,
  type DetailKpiKey,
  type ProjectDetailDsTab,
  type UnitStatus,
} from './projects-detail-ds-model';
import { ProjectDriveSyncPanel } from './project-drive-sync-panel';
import { ProjectAssistantPanel } from './project-assistant-panel';
import { ProjectsDetailDigitalTwin } from './projects-detail-digital-twin';

import './projects-ds.css';
import './projects-detail-ds.css';

const KPI_ICONS: Record<DetailKpiKey, IhIconName> = {
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
  'totalBudget',
  'spent',
  'remaining',
  'expectedRoi',
  'units',
  'investors',
  'completion',
  'targetDelivery',
];

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

function unitTone(status: UnitStatus) {
  switch (status) {
    case 'sold':
    case 'rented':
      return 'success' as const;
    case 'reserved':
      return 'info' as const;
    case 'blocked':
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
  const { user } = useAuth();
  const { openAi } = useScreenshotDashboardInteractions();
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

  const model = useMemo(
    () => buildProjectDetailDsModel(project, projectId, locale),
    [project, projectId, locale],
  );

  const tabItems = useMemo(
    () =>
      PROJECT_DETAIL_DS_TABS.map((id) => ({
        id,
        label: tD(`tabs.${id}`),
      })),
    [tD],
  );

  const onTabChange = (id: string) => {
    const next = resolveProjectDetailDsTab(id);
    if (!next) return;
    router.push(projectDetailDsHref(projectId, next) as Route);
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
          <ProjectCover scene={model.coverScene} />
          <span className="proj-ds__cover-scrim" aria-hidden="true" />
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
                variant="primary"
                size="sm"
                type="button"
                onClick={() =>
                  openAi(
                    tD('ai.openPrompt', {
                      name: model.name,
                      code: model.code,
                    }),
                  )
                }
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
              <strong>{model.completion}%</strong>
            </div>
            <div className="proj-detail-ds__stat">
              <span>{tD('hero.investmentStatus')}</span>
              <strong>{tD(`investmentStatus.${model.investmentStatus}`)}</strong>
            </div>
            <div className="proj-detail-ds__stat">
              <span>{tD('hero.lastUpdated')}</span>
              <strong>{formatShortDate(model.lastUpdated, locale)}</strong>
            </div>
          </div>

          <div className="proj-detail-ds__score-row">
            <div className="proj-detail-ds__score">
              <div
                className="proj-detail-ds__score-ring"
                style={{ ['--pct' as string]: model.healthScore }}
                aria-hidden="true"
              >
                <span>{model.healthScore}</span>
              </div>
              <div>
                <em>{tD('hero.healthScore')}</em>
                <strong>
                  <StatusChip tone={statusTone(model.status)}>
                    {getStatusLabel(model.status)}
                  </StatusChip>
                </strong>
              </div>
            </div>
            <div className="proj-detail-ds__score">
              <div
                className="proj-detail-ds__score-ring"
                style={{ ['--pct' as string]: model.aiConfidence }}
                aria-hidden="true"
              >
                <span>{model.aiConfidence}</span>
              </div>
              <div>
                <em>{tD('hero.aiConfidence')}</em>
                <strong>{tDs(`risk.${model.risk}`)}</strong>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="proj-detail-ds__kpi-row" aria-label={tD('kpis.aria')}>
        {KPI_ORDER.map((key) => {
          const kpi = model.kpis[key];
          return (
            <KpiCard
              key={key}
              className="proj-detail-ds__kpi"
              label={tD(`kpis.${key}`)}
              value={loading ? '—' : kpi.value}
              hint={tD(`kpis.hints.${key}`)}
              delta={kpi.delta}
              {...(kpi.deltaTone ? { deltaTone: kpi.deltaTone } : {})}
              icon={<IhIcon name={KPI_ICONS[key]} size={16} />}
            />
          );
        })}
      </section>

      <div className="proj-detail-ds__tabs-bar">
        <Tabs
          className="proj-detail-ds__tabs"
          tabs={tabItems}
          activeId={resolvedTab}
          onChange={onTabChange}
          ariaLabel={tD('tabs.aria')}
        />
        <div className="proj-detail-ds__tabs-mobile">
          <Select
            className="proj-detail-ds__tabs-select"
            label={tD('tabs.aria')}
            value={resolvedTab}
            onChange={(e) => onTabChange(e.target.value)}
          >
            {PROJECT_DETAIL_DS_TABS.map((id) => (
              <option key={id} value={id}>
                {tD(`tabs.${id}`)}
              </option>
            ))}
          </Select>
        </div>
      </div>

      {error ? <div className="proj-detail-ds__banner">{error}</div> : null}

      {resolvedTab === 'overview' ? (
        <OverviewTab
          model={model}
          tD={tD}
          tDs={tDs}
          getStatusLabel={getStatusLabel}
          getPriorityLabel={getPriorityLabel}
          locale={locale}
        />
      ) : null}
      {resolvedTab === 'construction' ? (
        <ConstructionTab model={model} tD={tD} tDs={tDs} locale={locale} />
      ) : null}
      {resolvedTab === 'units' ? <UnitsTab model={model} tD={tD} locale={locale} /> : null}
      {resolvedTab === 'financial' ? (
        <FinancialTab model={model} tD={tD} locale={locale} />
      ) : null}
      {resolvedTab === 'investors' ? (
        <InvestorsTab model={model} tD={tD} locale={locale} />
      ) : null}
      {resolvedTab === 'documents' ? (
        <DocumentsTab tD={tD} projectId={projectId} />
      ) : null}
      {resolvedTab === 'tasks' ? (
        <TasksTab
          model={model}
          tD={tD}
          tDs={tDs}
          getPriorityLabel={getPriorityLabel}
          locale={locale}
        />
      ) : null}
      {resolvedTab === 'timeline' ? <TimelineTab model={model} tD={tD} locale={locale} /> : null}
      {resolvedTab === 'reports' ? <ReportsTab model={model} tD={tD} locale={locale} /> : null}
      {resolvedTab === 'ai-insights' ? <AiInsightsTab model={model} tD={tD} /> : null}
    </div>
  );
}

type Model = ReturnType<typeof buildProjectDetailDsModel>;
type TranslateFn = ReturnType<typeof useTranslations>;

function OverviewTab({
  model,
  tD,
  tDs,
  getStatusLabel,
  getPriorityLabel,
  locale,
}: {
  model: Model;
  tD: TranslateFn;
  tDs: TranslateFn;
  getStatusLabel: (s: string) => string;
  getPriorityLabel: (s: string) => string;
  locale: string;
}) {
  return (
    <>
      <ProjectsDetailDigitalTwin projectId={model.id} locale={locale} />
      <div className="proj-detail-ds__overview">
        <div className="proj-detail-ds__overview-main">
          <article className="proj-detail-ds__panel">
            <h3>{tD('overview.summary')}</h3>
            <p className="proj-detail-ds__panel-sub">{model.description}</p>
            <div className="proj-detail-ds__kv">
              <div className="proj-detail-ds__kv-row">
                <span>{tD('overview.status')}</span>
                <strong>
                  <StatusChip tone={statusTone(model.status)}>
                    {getStatusLabel(model.status)}
                  </StatusChip>
                </strong>
              </div>
              <div className="proj-detail-ds__kv-row">
                <span>{tD('overview.nextMilestone')}</span>
                <strong>{tDs(`phases.${model.nextMilestone}`)}</strong>
              </div>
              <div className="proj-detail-ds__kv-row">
                <span>{tD('overview.manager')}</span>
                <strong>{model.manager}</strong>
              </div>
              <div className="proj-detail-ds__kv-row">
                <span>{tD('overview.contractor')}</span>
                <strong>{model.contractor}</strong>
              </div>
              <div className="proj-detail-ds__kv-row">
                <span>{tD('overview.architect')}</span>
                <strong>{model.architect}</strong>
              </div>
              <div className="proj-detail-ds__kv-row">
                <span>{tD('overview.constructionCompany')}</span>
                <strong>{model.constructionCompany}</strong>
              </div>
              <div className="proj-detail-ds__kv-row">
                <span>{tD('overview.risk')}</span>
                <strong>{tDs(`risk.${model.risk}`)}</strong>
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

          <article className="proj-detail-ds__panel proj-detail-ds__progress-hero">
            <h3>{tD('overview.constructionProgress')}</h3>
            <div className="proj-detail-ds__progress-big">
              <span className="proj-detail-ds__panel-sub">{tD('overview.completionLabel')}</span>
              <strong>{model.completion}%</strong>
              <ProgressBar value={model.completion} />
            </div>
            <div className="proj-detail-ds__kv">
              <div className="proj-detail-ds__kv-row">
                <span>{tD('overview.currentPhase')}</span>
                <strong>{tDs(`phases.${model.currentPhase}`)}</strong>
              </div>
              <div className="proj-detail-ds__kv-row">
                <span>{tD('overview.permitStatus')}</span>
                <strong>{tD(`permits.${model.permitStatus}`)}</strong>
              </div>
              <div className="proj-detail-ds__kv-row">
                <span>{tD('overview.upcomingInspection')}</span>
                <strong>{formatShortDate(model.upcomingInspection, locale)}</strong>
              </div>
              <div className="proj-detail-ds__kv-row">
                <span>{tD('overview.completionPrediction')}</span>
                <strong>{formatShortDate(model.completionPrediction, locale)}</strong>
              </div>
            </div>
            <div className="proj-detail-ds__milestone-list" aria-label={tD('overview.milestones')}>
              {model.milestones.map((m) => (
                <div
                  key={m.id}
                  className={`proj-detail-ds__milestone${m.done ? ' is-done' : ''}${
                    m.phase === model.currentPhase ? ' is-current' : ''
                  }`}
                >
                  <span className="proj-detail-ds__milestone-dot" aria-hidden="true" />
                  <span>{tDs(`phases.${m.phase}`)}</span>
                  <em>{formatShortDate(m.date, locale)}</em>
                </div>
              ))}
            </div>
          </article>
        </div>

        <aside className="proj-detail-ds__widget-grid" aria-label={tD('overview.widgets')}>
          <article className="proj-detail-ds__panel">
            <h3>{tD('overview.recentActivity')}</h3>
            <ul className="proj-detail-ds__list">
              {model.recentActivity.map((item) => (
                <li key={item.id}>
                  <strong>{item.title}</strong>
                  <span>{formatShortDate(item.time, locale)}</span>
                </li>
              ))}
            </ul>
          </article>
          <article className="proj-detail-ds__panel">
            <h3>{tD('overview.aiAlerts')}</h3>
            {model.alerts.ai.map((a) => (
              <div key={a.id} className={`proj-detail-ds__alert is-${a.tone}`}>
                {tD(`alerts.${a.textKey}`)}
              </div>
            ))}
          </article>
          <article className="proj-detail-ds__panel">
            <h3>{tD('overview.budgetAlerts')}</h3>
            {model.alerts.budget.map((a) => (
              <div key={a.id} className={`proj-detail-ds__alert is-${a.tone}`}>
                {tD(`alerts.${a.textKey}`)}
              </div>
            ))}
          </article>
          <article className="proj-detail-ds__panel">
            <h3>{tD('overview.constructionAlerts')}</h3>
            {model.alerts.construction.map((a) => (
              <div key={a.id} className={`proj-detail-ds__alert is-${a.tone}`}>
                {tD(`alerts.${a.textKey}`)}
              </div>
            ))}
          </article>
          <article className="proj-detail-ds__panel">
            <h3>{tD('overview.weather')}</h3>
            <div className="proj-detail-ds__weather">
              <div>
                <strong>{model.weather.tempC}°C</strong>
                <p className="proj-detail-ds__panel-sub">
                  {tD(`weather.${model.weather.condition}`)}
                </p>
              </div>
              <StatusChip tone="info">{model.city}</StatusChip>
            </div>
          </article>
          <article className="proj-detail-ds__panel">
            <h3>{tD('overview.projectHealth')}</h3>
            <div className="proj-detail-ds__score">
              <div
                className="proj-detail-ds__score-ring"
                style={{ ['--pct' as string]: model.healthScore }}
              >
                <span>{model.healthScore}</span>
              </div>
              <div>
                <em>{tD('hero.healthScore')}</em>
                <strong>
                  {model.completion}% · {tDs(`risk.${model.risk}`)}
                </strong>
              </div>
            </div>
          </article>
          <article className="proj-detail-ds__panel">
            <h3>{tD('overview.upcomingTasks')}</h3>
            <ul className="proj-detail-ds__list">
              {model.upcomingTasks.map((task) => (
                <li key={task.id}>
                  <strong>{task.title}</strong>
                  <span>
                    {task.owner} · {formatShortDate(task.dueDate, locale)}
                  </span>
                </li>
              ))}
            </ul>
          </article>
        </aside>
      </div>
    </>
  );
}

function ConstructionTab({
  model,
  tD,
  tDs,
  locale,
}: {
  model: Model;
  tD: TranslateFn;
  tDs: TranslateFn;
  locale: string;
}) {
  return (
    <div className="proj-detail-ds__overview">
      <article className="proj-detail-ds__panel proj-detail-ds__progress-hero" style={{ gridColumn: '1 / -1' }}>
        <h3>{tD('construction.title')}</h3>
        <p className="proj-detail-ds__panel-sub">{tD('construction.subtitle')}</p>
        <div className="proj-detail-ds__progress-big">
          <strong>{model.completion}%</strong>
          <ProgressBar value={model.completion} />
        </div>
        <div className="proj-detail-ds__milestone-list">
          {model.milestones.map((m) => (
            <div
              key={m.id}
              className={`proj-detail-ds__milestone${m.done ? ' is-done' : ''}${
                m.phase === model.currentPhase ? ' is-current' : ''
              }`}
            >
              <span className="proj-detail-ds__milestone-dot" />
              <span>
                {tDs(`phases.${m.phase}`)} · {m.pct}%
              </span>
              <em>{formatShortDate(m.date, locale)}</em>
            </div>
          ))}
        </div>
        <div className="proj-detail-ds__kv">
          <div className="proj-detail-ds__kv-row">
            <span>{tD('overview.permitStatus')}</span>
            <strong>{tD(`permits.${model.permitStatus}`)}</strong>
          </div>
          <div className="proj-detail-ds__kv-row">
            <span>{tD('overview.contractor')}</span>
            <strong>{model.contractor}</strong>
          </div>
          <div className="proj-detail-ds__kv-row">
            <span>{tD('overview.upcomingInspection')}</span>
            <strong>{formatShortDate(model.upcomingInspection, locale)}</strong>
          </div>
        </div>
      </article>
    </div>
  );
}

function UnitsTab({
  model,
  tD,
  locale,
}: {
  model: Model;
  tD: TranslateFn;
  locale: string;
}) {
  return (
    <section className="proj-detail-ds__units" aria-label={tD('units.aria')}>
      {model.units.map((unit) => (
        <article key={unit.id} className="proj-detail-ds__unit">
          <div className="proj-detail-ds__unit-top">
            <span className="proj-detail-ds__unit-code">{unit.code}</span>
            <StatusChip tone={unitTone(unit.status)}>
              {tD(`units.status.${unit.status}`)}
            </StatusChip>
          </div>
          <div className="proj-detail-ds__unit-meta">
            <div>
              <span>{tD('units.floor')}</span>
              <strong>{unit.floor}</strong>
            </div>
            <div>
              <span>{tD('units.price')}</span>
              <strong>{formatCompactCurrency(unit.price, locale)}</strong>
            </div>
            <div>
              <span>{tD('units.investor')}</span>
              <strong>{unit.investor ?? '—'}</strong>
            </div>
            <div>
              <span>{tD('units.availability')}</span>
              <strong>
                {unit.status === 'available' ? tD('units.available') : tD('units.unavailable')}
              </strong>
            </div>
            <div>
              <span>{tD('units.reservation')}</span>
              <strong>
                {unit.status === 'reserved' ? tD('units.reserved') : '—'}
              </strong>
            </div>
            <div>
              <span>{tD('units.rental')}</span>
              <strong>
                {unit.rentalMonthly
                  ? formatCompactCurrency(unit.rentalMonthly, locale)
                  : '—'}
              </strong>
            </div>
          </div>
        </article>
      ))}
    </section>
  );
}

function FinancialTab({
  model,
  tD,
  locale,
}: {
  model: Model;
  tD: TranslateFn;
  locale: string;
}) {
  const f = model.financial;
  const metrics: Array<{ key: string; value: string }> = [
    { key: 'budget', value: formatCompactCurrency(f.budget, locale) },
    { key: 'spent', value: formatCompactCurrency(f.spent, locale) },
    { key: 'remaining', value: formatCompactCurrency(f.remaining, locale) },
    { key: 'forecast', value: formatCompactCurrency(f.forecast, locale) },
    { key: 'loan', value: formatCompactCurrency(f.loan, locale) },
    { key: 'cashFlow', value: formatCompactCurrency(f.cashFlow, locale) },
    { key: 'roi', value: `${f.roi.toFixed(1)}%` },
    { key: 'profit', value: formatCompactCurrency(f.profit, locale) },
    { key: 'revenue', value: formatCompactCurrency(f.revenue, locale) },
    { key: 'expenses', value: formatCompactCurrency(f.expenses, locale) },
  ];

  return (
    <div style={{ display: 'grid', gap: 12 }}>
      <section className="proj-detail-ds__fin-grid" aria-label={tD('financial.aria')}>
        {metrics.map((m) => (
          <article key={m.key} className="proj-detail-ds__fin-metric">
            <span>{tD(`financial.metrics.${m.key}`)}</span>
            <strong>{m.value}</strong>
          </article>
        ))}
      </section>
      <article className="proj-detail-ds__panel proj-detail-ds__chart">
        <h3>{tD('financial.cashFlowChart')}</h3>
        <p className="proj-detail-ds__panel-sub">{tD('financial.cashFlowHint')}</p>
        <div className="proj-detail-ds__bars" aria-hidden="true">
          {f.series.map((value, i) => (
            <div key={i} className="proj-detail-ds__bar">
              <i style={{ height: `${value}%` }} />
            </div>
          ))}
        </div>
      </article>
    </div>
  );
}

function InvestorsTab({
  model,
  tD,
  locale,
}: {
  model: Model;
  tD: TranslateFn;
  locale: string;
}) {
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
          {model.investors.map((inv) => (
            <tr key={inv.id}>
              <td>
                <div className="proj-detail-ds__person">
                  <span className="proj-detail-ds__avatar">{inv.initials}</span>
                  <span>{inv.name}</span>
                </div>
              </td>
              <td>{formatCompactCurrency(inv.investment, locale)}</td>
              <td>{inv.ownershipPct}%</td>
              <td>{inv.expectedReturn}%</td>
              <td>
                <StatusChip
                  tone={
                    inv.status === 'active'
                      ? 'success'
                      : inv.status === 'pending'
                        ? 'warning'
                        : 'info'
                  }
                >
                  {tD(`investors.status.${inv.status}`)}
                </StatusChip>
              </td>
              <td>{inv.documents}</td>
              <td>{formatShortDate(inv.lastContact, locale)}</td>
            </tr>
          ))}
        </tbody>
      </table>
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
        const message = err instanceof Error ? err.message : tD('documents.foldersLoadError');
        setFoldersError(message || tD('documents.foldersLoadError'));
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
        const message = err instanceof Error ? err.message : tD('documents.loadError');
        setLoadError(message || tD('documents.loadError'));
        setAssets([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, selectedFolderId, tD]);

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

      <article className="proj-detail-ds__panel">
        <h3>
          {selectedFolder
            ? selectedFolder.name
            : tD('documents.recent')}
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
  return (
    <section className="proj-detail-ds__timeline" aria-label={tD('timeline.aria')}>
      {model.timeline.map((item) => (
        <div
          key={item.id}
          className={`proj-detail-ds__tl-item is-${item.status}`}
        >
          <div className="proj-detail-ds__tl-rail">
            <span className="proj-detail-ds__tl-dot" />
          </div>
          <article className="proj-detail-ds__tl-card">
            <div className="proj-detail-ds__tl-card-top">
              <strong>{tD(`timeline.domains.${item.domain}`)}</strong>
              <StatusChip
                tone={
                  item.status === 'completed'
                    ? 'success'
                    : item.status === 'current'
                      ? 'info'
                      : 'default'
                }
              >
                {tD(`timeline.status.${item.status}`)}
              </StatusChip>
            </div>
            <p>{item.note}</p>
            <span className="proj-detail-ds__panel-sub">
              {formatShortDate(item.date, locale)}
            </span>
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
