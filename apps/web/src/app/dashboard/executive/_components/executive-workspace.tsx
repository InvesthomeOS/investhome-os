'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import {
  EXECUTIVE_FILTER_STORAGE_KEY,
  type ActivityItem,
  type AiInsightItem,
  type ApprovalItem,
  type CashFlowPoint,
  type DeadlineItem,
  type DelayedProjectRow,
  type ExecutiveFilterParams,
  type ExecutivePeriodPreset,
  type ProjectHealthRow,
  type RecentTransactionRow,
  type SummaryCard,
  fetchExecutiveActivity,
  fetchExecutiveAiInsights,
  fetchExecutiveApprovals,
  fetchExecutiveConstructionSnapshot,
  fetchExecutiveDeadlines,
  fetchExecutiveFinancialOverview,
  fetchExecutiveInvestorOverview,
  fetchExecutiveLeadsPipeline,
  fetchExecutiveProjectPortfolio,
  fetchExecutiveSummary,
  formatCurrencyTotals,
  formatMoney,
  formatShortDate,
  moduleHref,
  resolvePeriodDates,
} from '@/lib/api/executive';
import {
  fetchDashboardMetrics,
  fetchExecutiveSalesSummary,
  fetchOpportunities,
  formatCurrencyTotals as formatSalesCurrencyTotals,
  type ExecutiveSalesSummary,
} from '@/lib/api/sales';
import { fetchProjects } from '@/lib/api/projects';
import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';
import { useLeadLabels } from '@/lib/i18n/lead-labels';
import { useProjectLabels } from '@/lib/i18n/project-labels';
import { metadataForI18n } from '@/lib/api/activity';
import { fetchLeadQualificationExecutiveSummary, type LeadQualificationExecutiveSummary } from '@/lib/api/lead-qualification';
import { useActivityLabels } from '@/lib/i18n/activity-labels';

type LoadState = 'idle' | 'loading' | 'error' | 'success';

interface StoredFilters {
  preset: ExecutivePeriodPreset;
  customFrom: string;
  customTo: string;
  project_id: string;
  assigned_to: string;
  currency: string;
}

const DEFAULT_STORED: StoredFilters = {
  preset: 'last30Days',
  customFrom: '',
  customTo: '',
  project_id: '',
  assigned_to: '',
  currency: '',
};

const HEALTH_SORT: Record<ProjectHealthRow['health_status'], number> = {
  at_risk: 0,
  attention: 1,
  on_track: 2,
};

function metadataForExecutiveI18n(metadata: Record<string, string | number | null>) {
  return Object.fromEntries(
    Object.entries(metadata).map(([key, value]) => [key, value ?? '']),
  ) as Record<string, string>;
}

function stripExecutivePrefix(key: string): string {
  return key.startsWith('executive.') ? key.slice('executive.'.length) : key;
}

function SectionShell({
  id,
  title,
  badge,
  children,
  state,
  errorMessage,
  onRetry,
  retryLabel,
}: {
  id?: string;
  title: string;
  badge?: string;
  children: React.ReactNode;
  state: LoadState;
  errorMessage?: string | null;
  onRetry?: () => void;
  retryLabel: string;
}) {
  return (
    <section id={id} className="dashboard__panel leads__panel executive__section">
      <div className="executive__section-header">
        <h2 className="leads-form__section-title">{title}</h2>
        {badge && <span className="executive__section-badge">{badge}</span>}
      </div>
      {state === 'loading' && <div className="executive__skeleton" aria-hidden="true" />}
      {state === 'error' && (
        <div className="leads__state leads__state--error">
          <p>{errorMessage}</p>
          {onRetry && (
            <button type="button" className="leads__button leads__button--secondary" onClick={onRetry}>
              {retryLabel}
            </button>
          )}
        </div>
      )}
      {state === 'success' && children}
    </section>
  );
}

function SummaryCardView({
  card,
  locale,
  label,
  comparisonUnavailable,
}: {
  card: SummaryCard;
  locale: string;
  label: string;
  comparisonUnavailable: string;
}) {
  const href =
    card.key === 'pending_approvals'
      ? ('#executive-approvals' as Route)
      : moduleHref(card.link_module, card.link_query);
  const displayValue =
    card.currency_totals && Object.keys(card.currency_totals).length > 0
      ? formatCurrencyTotals(card.currency_totals, locale)
      : card.value ?? '—';

  let changeLabel = comparisonUnavailable;
  if (card.comparison?.change_available && card.comparison.change !== null && card.comparison.change !== undefined) {
    const change = Number(card.comparison.change);
    if (!Number.isNaN(change)) {
      changeLabel = change > 0 ? `+${change}` : `${change}`;
    }
  }

  return (
    <Link href={href} className="investors__stat-card executive__summary-card">
      <p>{label}</p>
      <strong>{displayValue}</strong>
      <span className="executive__card-delta">{changeLabel}</span>
    </Link>
  );
}

function ProjectCard({
  project,
  locale,
  getStatusLabel,
  healthLabel,
  unavailableLabel,
  openLabel,
  currentValueLabel,
  fundingGapLabel,
  completionLabel,
}: {
  project: ProjectHealthRow;
  locale: string;
  getStatusLabel: (status: string) => string;
  healthLabel: string;
  unavailableLabel: string;
  openLabel: string;
  currentValueLabel: string;
  fundingGapLabel: string;
  completionLabel: string;
}) {
  return (
    <article className={`executive__project-card executive__project-card--${project.health_status}`}>
      <div className="executive__project-card-header">
        <span className={`executive__health executive__health--${project.health_status}`}>{healthLabel}</span>
        <h3>{project.project_name}</h3>
      </div>
      <p className="executive__project-card-meta">
        {getStatusLabel(project.status)}
        {' · '}
        {unavailableLabel}
      </p>
      <dl className="executive__project-card-stats">
        <div>
          <dt>{currentValueLabel}</dt>
          <dd>{formatMoney(project.current_value, 'USD', locale)}</dd>
        </div>
        <div>
          <dt>{fundingGapLabel}</dt>
          <dd>{formatMoney(project.funding_gap, 'USD', locale)}</dd>
        </div>
        <div>
          <dt>{completionLabel}</dt>
          <dd>{formatShortDate(project.completion_target, locale)}</dd>
        </div>
      </dl>
      <Link
        href={moduleHref('projects', { id: project.project_id })}
        className="leads__button leads__button--secondary executive__project-card-link"
      >
        {openLabel}
      </Link>
    </article>
  );
}

function PipelineChart({
  stages,
  getStatusLabel,
  locale,
  filterCurrency,
}: {
  stages: { status: string; count: number; estimated_budget_total: string }[];
  getStatusLabel: (status: string) => string;
  locale: string;
  filterCurrency?: string;
}) {
  const max = Math.max(...stages.map((stage) => stage.count), 1);
  const currency = filterCurrency || 'USD';
  return (
    <div className="executive__pipeline" role="list">
      {stages.map((stage) => (
        <Link
          key={stage.status}
          href={moduleHref('leads', { status: stage.status })}
          className="executive__pipeline-row"
          role="listitem"
        >
          <span className="executive__pipeline-label">{getStatusLabel(stage.status)}</span>
          <div className="executive__pipeline-bar-wrap">
            <div
              className="executive__pipeline-bar"
              style={{ width: `${(stage.count / max) * 100}%` }}
            />
          </div>
          <span className="executive__pipeline-count">{stage.count}</span>
          <span className="executive__pipeline-budget">
            {formatMoney(stage.estimated_budget_total, currency, locale)}
          </span>
        </Link>
      ))}
    </div>
  );
}

function CashFlowChart({
  points,
  locale,
  inflowsLabel,
  outflowsLabel,
}: {
  points: CashFlowPoint[];
  locale: string;
  inflowsLabel: string;
  outflowsLabel: string;
}) {
  if (points.length === 0) {
    return null;
  }

  const maxNet = Math.max(
    ...points.flatMap((point) => Object.values(point.net).map((value) => Math.abs(Number(value)))),
    1,
  );

  return (
    <div className="executive__cashflow">
      {points.map((point) => {
        const currencies = Object.keys(point.net);
        const currency = currencies[0] ?? 'USD';
        const netVal = Number(point.net[currency] ?? 0);
        const inflowVal = Number(point.inflows[currency] ?? 0);
        const outflowVal = Number(point.outflows[currency] ?? 0);
        return (
          <div key={`${point.period_start}-${point.period_end}`} className="executive__cashflow-row">
            <span className="executive__cashflow-label">
              {formatShortDate(point.period_start, locale)}
            </span>
            <div className="executive__cashflow-bars">
              <div
                className="executive__cashflow-in"
                style={{ width: `${(inflowVal / maxNet) * 50}%` }}
                title={`${inflowsLabel}: ${formatMoney(inflowVal, currency, locale)}`}
              />
              <div
                className="executive__cashflow-out"
                style={{ width: `${(outflowVal / maxNet) * 50}%` }}
                title={`${outflowsLabel}: ${formatMoney(outflowVal, currency, locale)}`}
              />
            </div>
            <span className="executive__cashflow-net">{formatMoney(netVal, currency, locale)}</span>
          </div>
        );
      })}
    </div>
  );
}

function AiInsightsPanel({
  state,
  insights,
  expanded,
  onToggle,
  onRetry,
  locale,
  t,
  tCommon,
}: {
  state: LoadState;
  insights: Awaited<ReturnType<typeof fetchExecutiveAiInsights>> | null;
  expanded: boolean;
  onToggle: () => void;
  onRetry: () => void;
  locale: string;
  t: ReturnType<typeof useTranslations<'executive'>>;
  tCommon: ReturnType<typeof useTranslations<'common'>>;
}) {
  const renderItems = (items: AiInsightItem[], emptyKey: string) => {
    if (items.length === 0) {
      return <p className="leads__state">{t(emptyKey as 'aiPanel.emptyPriorities')}</p>;
    }
    return (
      <ul className="executive__ai-list">
        {items.map((item, index) => (
          <li key={`${item.kind}-${item.title_key}-${index}`}>
            <Link href={moduleHref(item.link_module, item.link_query)}>
              <strong>
                {t(stripExecutivePrefix(item.title_key) as 'aiPanel.deadline_priority.title', metadataForExecutiveI18n(item.metadata))}
              </strong>
              <p>
                {t(stripExecutivePrefix(item.description_key) as 'aiPanel.deadline_priority.description', metadataForExecutiveI18n(item.metadata))}
              </p>
            </Link>
          </li>
        ))}
      </ul>
    );
  };

  return (
    <aside className={`executive__ai-panel ${expanded ? 'executive__ai-panel--expanded' : ''}`}>
      <button type="button" className="executive__ai-panel-toggle" onClick={onToggle}>
        {t('aiPanel.title')}
        <span>{expanded ? '−' : '+'}</span>
      </button>
      {expanded && (
        <div className="executive__ai-panel-body">
          {state === 'loading' && <div className="executive__skeleton" aria-hidden="true" />}
          {state === 'error' && (
            <div className="leads__state leads__state--error">
              <p>{t('errors.section')}</p>
              <button type="button" className="leads__button leads__button--secondary" onClick={onRetry}>
                {tCommon('retry')}
              </button>
            </div>
          )}
          {state === 'success' && insights && (
            <>
              <section>
                <h3>{t('aiPanel.priorities')}</h3>
                {renderItems(insights.priorities, 'aiPanel.emptyPriorities')}
              </section>
              <section>
                <h3>{t('aiPanel.risks')}</h3>
                {renderItems(insights.risks, 'aiPanel.emptyRisks')}
              </section>
              <section>
                <h3>{t('aiPanel.opportunities')}</h3>
                {renderItems(insights.opportunities, 'aiPanel.emptyOpportunities')}
              </section>
              <footer className="executive__ai-footer">
                {t('aiPanel.footer', {
                  level: insights.ai_level,
                  time: formatShortDate(insights.generated_at, locale),
                })}
              </footer>
            </>
          )}
        </div>
      )}
    </aside>
  );
}

export function ExecutiveWorkspace() {
  const t = useTranslations('executive');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { user } = useAuth();
  const { getStatusLabel: getLeadStatusLabel } = useLeadLabels();
  const { getStatusLabel: getProjectStatusLabel } = useProjectLabels();
  const { getDescription: getActivityDescription } = useActivityLabels();

  const [stored, setStored] = useState<StoredFilters>(DEFAULT_STORED);
  const [projectOptions, setProjectOptions] = useState<{ id: string; label: string }[]>([]);
  const [aiExpanded, setAiExpanded] = useState(true);

  const [summaryCards, setSummaryCards] = useState<SummaryCard[]>([]);
  const [pipeline, setPipeline] = useState<Awaited<ReturnType<typeof fetchExecutiveLeadsPipeline>> | null>(null);
  const [salesSummary, setSalesSummary] = useState<ExecutiveSalesSummary | null>(null);
  const [qualificationSummary, setQualificationSummary] = useState<LeadQualificationExecutiveSummary | null>(null);
  const [salesMetrics, setSalesMetrics] = useState<Awaited<ReturnType<typeof fetchDashboardMetrics>> | null>(null);
  const [salesPipelineByCurrency, setSalesPipelineByCurrency] = useState<Record<string, string>>({});
  const [salesWeightedByCurrency, setSalesWeightedByCurrency] = useState<Record<string, string>>({});
  const [investors, setInvestors] = useState<Awaited<ReturnType<typeof fetchExecutiveInvestorOverview>> | null>(null);
  const [portfolio, setPortfolio] = useState<Awaited<ReturnType<typeof fetchExecutiveProjectPortfolio>> | null>(null);
  const [financial, setFinancial] = useState<Awaited<ReturnType<typeof fetchExecutiveFinancialOverview>> | null>(null);
  const [construction, setConstruction] = useState<Awaited<ReturnType<typeof fetchExecutiveConstructionSnapshot>> | null>(null);
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [deadlines, setDeadlines] = useState<DeadlineItem[]>([]);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [aiInsights, setAiInsights] = useState<Awaited<ReturnType<typeof fetchExecutiveAiInsights>> | null>(null);

  const [summaryState, setSummaryState] = useState<LoadState>('loading');
  const [pipelineState, setPipelineState] = useState<LoadState>('loading');
  const [investorState, setInvestorState] = useState<LoadState>('loading');
  const [portfolioState, setPortfolioState] = useState<LoadState>('loading');
  const [financialState, setFinancialState] = useState<LoadState>('loading');
  const [constructionState, setConstructionState] = useState<LoadState>('loading');
  const [approvalsState, setApprovalsState] = useState<LoadState>('loading');
  const [deadlineState, setDeadlineState] = useState<LoadState>('loading');
  const [activityState, setActivityState] = useState<LoadState>('loading');
  const [aiState, setAiState] = useState<LoadState>('idle');

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(EXECUTIVE_FILTER_STORAGE_KEY);
      if (raw) {
        setStored({ ...DEFAULT_STORED, ...JSON.parse(raw) });
      }
    } catch {
      setStored(DEFAULT_STORED);
    }
  }, []);

  useEffect(() => {
    void fetchProjects({ page: 1, page_size: 100, sort_by: 'project_name', sort_order: 'asc' })
      .then((response) => {
        setProjectOptions(
          response.items.map((project) => ({ id: project.id, label: project.project_name })),
        );
      })
      .catch(() => setProjectOptions([]));
  }, []);

  const filterParams: ExecutiveFilterParams = useMemo(() => {
    const dates = resolvePeriodDates(stored.preset, stored.customFrom, stored.customTo);
    return {
      date_from: dates.date_from,
      date_to: dates.date_to,
      project_id: stored.project_id || undefined,
      assigned_to: stored.assigned_to || undefined,
      currency: stored.currency || undefined,
    };
  }, [stored]);

  const persistFilters = (next: StoredFilters) => {
    setStored(next);
    try {
      sessionStorage.setItem(EXECUTIVE_FILTER_STORAGE_KEY, JSON.stringify(next));
    } catch {
      // Ignore storage failures.
    }
  };

  const loadSummary = useCallback(async () => {
    setSummaryState('loading');
    try {
      const response = await fetchExecutiveSummary(filterParams);
      setSummaryCards(response.cards);
      setSummaryState('success');
    } catch {
      setSummaryState('error');
    }
  }, [filterParams]);

  const loadPipeline = useCallback(async () => {
    setPipelineState('loading');
    try {
      const [leadsPipeline, summary, metrics, openOpps, qualSummary] = await Promise.all([
        fetchExecutiveLeadsPipeline(filterParams),
        fetchExecutiveSalesSummary().catch(() => null),
        fetchDashboardMetrics().catch(() => null),
        fetchOpportunities({ limit: 200 }).catch(() => ({ items: [], total: 0, offset: 0, limit: 0 })),
        fetchLeadQualificationExecutiveSummary().catch(() => null),
      ]);
      setPipeline(leadsPipeline);
      setSalesSummary(summary);
      setQualificationSummary(qualSummary);
      setSalesMetrics(metrics);
      const pipelineTotals: Record<string, number> = {};
      const weightedTotals: Record<string, number> = {};
      for (const opp of openOpps.items) {
        if (['won', 'lost', 'dormant', 'cancelled'].includes(opp.stage) || !opp.expected_revenue) continue;
        const amount = Number(opp.expected_revenue);
        if (Number.isNaN(amount)) continue;
        const currency = opp.currency || 'USD';
        pipelineTotals[currency] = (pipelineTotals[currency] ?? 0) + amount;
        weightedTotals[currency] = (weightedTotals[currency] ?? 0) + (amount * opp.probability) / 100;
      }
      setSalesPipelineByCurrency(
        Object.fromEntries(Object.entries(pipelineTotals).map(([c, v]) => [c, String(v)])),
      );
      setSalesWeightedByCurrency(
        Object.fromEntries(Object.entries(weightedTotals).map(([c, v]) => [c, String(v)])),
      );
      setPipelineState('success');
    } catch {
      setPipelineState('error');
    }
  }, [filterParams]);

  const loadInvestors = useCallback(async () => {
    setInvestorState('loading');
    try {
      setInvestors(await fetchExecutiveInvestorOverview(filterParams));
      setInvestorState('success');
    } catch {
      setInvestorState('error');
    }
  }, [filterParams]);

  const loadPortfolio = useCallback(async () => {
    setPortfolioState('loading');
    try {
      setPortfolio(await fetchExecutiveProjectPortfolio(filterParams));
      setPortfolioState('success');
    } catch {
      setPortfolioState('error');
    }
  }, [filterParams]);

  const loadFinancial = useCallback(async () => {
    setFinancialState('loading');
    try {
      setFinancial(await fetchExecutiveFinancialOverview(filterParams));
      setFinancialState('success');
    } catch {
      setFinancialState('error');
    }
  }, [filterParams]);

  const loadConstruction = useCallback(async () => {
    setConstructionState('loading');
    try {
      setConstruction(await fetchExecutiveConstructionSnapshot(filterParams));
      setConstructionState('success');
    } catch {
      setConstructionState('error');
    }
  }, [filterParams]);

  const loadApprovals = useCallback(async () => {
    setApprovalsState('loading');
    try {
      const response = await fetchExecutiveApprovals(filterParams);
      setApprovals(response.items);
      setApprovalsState('success');
    } catch {
      setApprovalsState('error');
    }
  }, [filterParams]);

  const loadDeadlines = useCallback(async () => {
    setDeadlineState('loading');
    try {
      const response = await fetchExecutiveDeadlines(filterParams);
      setDeadlines(response.items);
      setDeadlineState('success');
    } catch {
      setDeadlineState('error');
    }
  }, [filterParams]);

  const loadActivity = useCallback(async () => {
    setActivityState('loading');
    try {
      const response = await fetchExecutiveActivity(filterParams);
      setActivity(response.items);
      setActivityState('success');
    } catch {
      setActivityState('error');
    }
  }, [filterParams]);

  const loadAiInsights = useCallback(async () => {
    if (!aiExpanded) return;
    setAiState('loading');
    try {
      setAiInsights(await fetchExecutiveAiInsights(filterParams));
      setAiState('success');
    } catch {
      setAiState('error');
    }
  }, [aiExpanded, filterParams]);

  useEffect(() => {
    void loadSummary();
    void loadPipeline();
    void loadInvestors();
    void loadPortfolio();
    void loadFinancial();
    void loadConstruction();
    void loadApprovals();
    void loadDeadlines();
    void loadActivity();
  }, [
    loadActivity,
    loadApprovals,
    loadConstruction,
    loadDeadlines,
    loadFinancial,
    loadInvestors,
    loadPipeline,
    loadPortfolio,
    loadSummary,
  ]);

  useEffect(() => {
    void loadAiInsights();
  }, [loadAiInsights]);

  const sortedProjects = useMemo(() => {
    if (!portfolio) return [];
    return [...portfolio.projects]
      .sort((a, b) => {
        const healthDiff = HEALTH_SORT[a.health_status] - HEALTH_SORT[b.health_status];
        if (healthDiff !== 0) return healthDiff;
        const aDate = a.completion_target ? new Date(a.completion_target).getTime() : Infinity;
        const bDate = b.completion_target ? new Date(b.completion_target).getTime() : Infinity;
        return aDate - bDate;
      })
      .slice(0, 6);
  }, [portfolio]);

  const cardLabel = (key: string) => t(`companyOverview.${key}` as 'companyOverview.active_projects');

  const healthLabel = (status: ProjectHealthRow['health_status']) => t(`health.${status}`);

  const deadlineWindowLabel = (window: DeadlineItem['window']) => t(`deadlines.windows.${window}`);

  const quickActions = useMemo(() => {
    const actions: { href: Route; label: string }[] = [];
    if (user && hasPermission(user, 'leads', 'create')) {
      actions.push({ href: '/dashboard/leads' as Route, label: t('quickActions.addLead') });
    }
    if (user && hasPermission(user, 'investors', 'create')) {
      actions.push({ href: '/dashboard/investors' as Route, label: t('quickActions.addInvestor') });
    }
    if (user && hasPermission(user, 'projects', 'create')) {
      actions.push({ href: '/dashboard/projects' as Route, label: t('quickActions.addProject') });
    }
    if (user && hasPermission(user, 'documents', 'create')) {
      actions.push({ href: '/dashboard/documents' as Route, label: t('quickActions.uploadDocument') });
    }
    return actions;
  }, [t, user]);

  const activeInvestorCount = investors?.by_status.find((row) => row.status === 'active')?.count ?? 0;

  return (
    <main className="dashboard leads investors finance executive">
      <header className="dashboard__header leads__header">
        <p className="dashboard__eyebrow">{t('eyebrow')}</p>
        <h1 className="dashboard__title">{t('title')}</h1>
        <p className="leads__subtitle">{t('subtitle')}</p>
      </header>

      <section className="executive__filters">
        <label className="leads__field">
          <span>{t('filters.period')}</span>
          <select
            value={stored.preset}
            onChange={(event) =>
              persistFilters({ ...stored, preset: event.target.value as ExecutivePeriodPreset })
            }
          >
            <option value="today">{t('filters.today')}</option>
            <option value="last7Days">{t('filters.last7Days')}</option>
            <option value="last30Days">{t('filters.last30Days')}</option>
            <option value="thisQuarter">{t('filters.thisQuarter')}</option>
            <option value="thisYear">{t('filters.thisYear')}</option>
            <option value="custom">{t('filters.customRange')}</option>
          </select>
        </label>
        {stored.preset === 'custom' && (
          <>
            <label className="leads__field">
              <span>{t('filters.dateFrom')}</span>
              <input
                type="date"
                value={stored.customFrom}
                onChange={(event) => persistFilters({ ...stored, customFrom: event.target.value })}
              />
            </label>
            <label className="leads__field">
              <span>{t('filters.dateTo')}</span>
              <input
                type="date"
                value={stored.customTo}
                onChange={(event) => persistFilters({ ...stored, customTo: event.target.value })}
              />
            </label>
          </>
        )}
        <label className="leads__field">
          <span>{t('filters.project')}</span>
          <select
            value={stored.project_id}
            onChange={(event) => persistFilters({ ...stored, project_id: event.target.value })}
          >
            <option value="">{t('filters.allProjects')}</option>
            {projectOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="leads__field">
          <span>{t('filters.assignedTo')}</span>
          <input
            type="text"
            value={stored.assigned_to}
            onChange={(event) => persistFilters({ ...stored, assigned_to: event.target.value })}
            placeholder={t('filters.assignedPlaceholder')}
          />
        </label>
        <label className="leads__field">
          <span>{t('filters.currency')}</span>
          <input
            type="text"
            value={stored.currency}
            onChange={(event) => persistFilters({ ...stored, currency: event.target.value.toUpperCase() })}
            placeholder={t('filters.currencyPlaceholder')}
          />
        </label>
        {quickActions.length > 0 && (
          <div className="executive__quick-actions-inline">
            {quickActions.map((action) => (
              <Link key={action.label} href={action.href} className="leads__button leads__button--secondary">
                {action.label}
              </Link>
            ))}
          </div>
        )}
      </section>

      <div className="executive__workspace-body">
        <div className="executive__main-column">
          <section className="executive__company-overview">
            <h2 className="leads-form__section-title">{t('companyOverview.title')}</h2>
            <div className="finance__stats executive__summary-grid">
              {summaryState === 'loading' &&
                Array.from({ length: 6 }).map((_, index) => (
                  <div key={index} className="investors__stat-card executive__skeleton" aria-hidden="true" />
                ))}
              {summaryState === 'error' && (
                <p className="leads__state leads__state--error">{t('errors.summary')}</p>
              )}
              {summaryState === 'success' &&
                summaryCards.map((card) => (
                  <SummaryCardView
                    key={card.key}
                    card={card}
                    locale={locale}
                    label={cardLabel(card.key)}
                    comparisonUnavailable={t('cards.noComparison')}
                  />
                ))}
            </div>
          </section>

          <SectionShell
            title={t('projects.title')}
            state={portfolioState}
            errorMessage={t('errors.section')}
            onRetry={() => void loadPortfolio()}
            retryLabel={tCommon('retry')}
          >
            {sortedProjects.length === 0 ? (
              <p className="leads__state">{t('projects.empty')}</p>
            ) : (
              <>
                <div className="executive__project-grid">
                  {sortedProjects.map((project) => (
                    <ProjectCard
                      key={project.project_id}
                      project={project}
                      locale={locale}
                      getStatusLabel={getProjectStatusLabel}
                      healthLabel={healthLabel(project.health_status)}
                      unavailableLabel={t('projects.completionUnavailable')}
                      openLabel={t('projects.openProject')}
                      currentValueLabel={t('projects.currentValue')}
                      fundingGapLabel={t('projects.fundingGap')}
                      completionLabel={t('projects.completionTarget')}
                    />
                  ))}
                </div>
                <Link href={moduleHref('projects')} className="executive__view-all">
                  {t('projects.viewAll')}
                </Link>
              </>
            )}
          </SectionShell>

          <SectionShell
            title={t('sales.title')}
            state={pipelineState}
            errorMessage={t('errors.section')}
            onRetry={() => void loadPipeline()}
            retryLabel={tCommon('retry')}
          >
            {pipeline && (
              <>
                <div className="executive__sales-summary">
                  <span>{t('sales.total')}: {pipeline.summary.total}</span>
                  <span>{t('sales.qualified')}: {pipeline.summary.qualified}</span>
                  <span>{t('sales.meetings')}: {pipeline.summary.meetings}</span>
                  <span>{t('sales.proposals')}: {pipeline.summary.proposals}</span>
                  <span>{t('sales.won')}: {pipeline.summary.won}</span>
                  <span>{t('sales.lost')}: {pipeline.summary.lost}</span>
                </div>
                <PipelineChart
                  stages={pipeline.stages}
                  getStatusLabel={getLeadStatusLabel}
                  locale={locale}
                  filterCurrency={stored.currency || undefined}
                />
                {pipeline.conversion_rate && (
                  <p className="executive__meta">
                    {t('sales.conversionRate', {
                      rate: `${(Number(pipeline.conversion_rate) * 100).toFixed(1)}%`,
                    })}
                  </p>
                )}
                {qualificationSummary && (
                  <div className="executive__metric-list executive__qualification-kpis">
                    <p>{t('leadQualification.qualifiedLeads')}: {qualificationSummary.qualified_count}</p>
                    <p>{t('leadQualification.unqualifiedLeads')}: {qualificationSummary.unqualified_count}</p>
                    <p>{t('leadQualification.avgLeadScore')}: {qualificationSummary.avg_lead_score}</p>
                    <p>{t('leadQualification.awaitingReview')}: {qualificationSummary.awaiting_review_count}</p>
                    <p>{t('leadQualification.withoutFollowUp')}: {qualificationSummary.without_follow_up_count}</p>
                    <p>{t('leadQualification.readyForOpportunity')}: {qualificationSummary.ready_for_opportunity_count}</p>
                  </div>
                )}
                {(salesMetrics || salesSummary) && (
                  <div className="executive__metric-list executive__sales-opportunities">
                    {salesMetrics && (
                      <p>{t('sales.activeOpportunities')}: {salesMetrics.open_opportunities}</p>
                    )}
                    {Object.keys(salesPipelineByCurrency).length > 0 && (
                      <p>
                        {t('sales.pipelineByCurrency')}:{' '}
                        {formatSalesCurrencyTotals(salesPipelineByCurrency, locale)}
                      </p>
                    )}
                    {Object.keys(salesWeightedByCurrency).length > 0 && (
                      <p>
                        {t('sales.weightedPipeline')}:{' '}
                        {formatSalesCurrencyTotals(salesWeightedByCurrency, locale)}
                      </p>
                    )}
                    {salesSummary && (
                      <>
                        <p>{t('sales.expectedClosings')}: {salesSummary.expected_closings_30d}</p>
                        <p>{t('sales.withoutNextAction')}: {salesSummary.no_follow_up_count}</p>
                        <p>{t('sales.stalled')}: {salesSummary.dormant_count}</p>
                        <p>{t('sales.highRisk')}: {salesSummary.high_risk_count}</p>
                      </>
                    )}
                    <Link href={'/dashboard/sales' as Route} className="executive__view-all">
                      {t('sales.viewSales')}
                    </Link>
                  </div>
                )}
                <p className="executive__meta">
                  {t('pipeline.wonLost', {
                    won: pipeline.won_in_period,
                    lost: pipeline.lost_in_period,
                  })}
                </p>
              </>
            )}
          </SectionShell>

          <SectionShell
            title={t('investors.title')}
            state={investorState}
            errorMessage={t('errors.section')}
            onRetry={() => void loadInvestors()}
            retryLabel={tCommon('retry')}
          >
            {investors && (
              <div className="executive__metric-list">
                <p>{t('investors.active')}: {activeInvestorCount}</p>
                <p>
                  {t('investors.capacity')}: {formatCurrencyTotals(investors.total_investment_capacity, locale)}
                </p>
                <p>
                  {t('investors.committed')}: {formatCurrencyTotals(investors.total_committed, locale)}
                </p>
                <p>
                  {t('investors.funded')}: {formatCurrencyTotals(investors.total_funded, locale)}
                </p>
                <p>
                  {t('investors.remaining')}: {formatCurrencyTotals(investors.remaining_committed, locale)}
                </p>
                {investors.upcoming_follow_ups.length > 0 && (
                  <p>{t('investors.followUps')}: {investors.upcoming_follow_ups.length}</p>
                )}
                <Link href={moduleHref('investors')} className="executive__view-all">
                  {t('investors.viewAll')}
                </Link>
              </div>
            )}
          </SectionShell>

          <SectionShell
            title={t('financial.title')}
            state={financialState}
            errorMessage={t('errors.section')}
            onRetry={() => void loadFinancial()}
            retryLabel={tCommon('retry')}
          >
            {financial && (
              <>
                <div className="executive__metric-list">
                  <p>
                    {t('financial.availableCash')}: {formatCurrencyTotals(financial.available_cash, locale)}
                  </p>
                  <p>
                    {t('financial.receivables')}: {formatCurrencyTotals(financial.income_in_period, locale)}
                  </p>
                  <p>
                    {t('financial.payables')}: {formatCurrencyTotals(financial.expenses_in_period, locale)}
                  </p>
                  <p>
                    {t('financial.upcoming')}: {formatCurrencyTotals(financial.upcoming_payments, locale)}
                  </p>
                  <p>
                    {t('financial.overdue')}: {formatCurrencyTotals(financial.overdue_payments, locale)}
                  </p>
                  <p>
                    {t('financial.fundingNeed')}:{' '}
                    {formatCurrencyTotals(
                      Object.fromEntries(
                        Object.entries(
                          financial.funding_gap_by_project.reduce<Record<string, number>>((acc, gap) => {
                            acc[gap.currency] = (acc[gap.currency] ?? 0) + Number(gap.funding_gap);
                            return acc;
                          }, {}),
                        ).map(([currency, amount]) => [currency, String(amount)]),
                      ),
                      locale,
                    )}
                  </p>
                </div>
                <CashFlowChart
                  points={financial.cash_flow_trend}
                  locale={locale}
                  inflowsLabel={t('financial.inflows')}
                  outflowsLabel={t('financial.outflows')}
                />
                {financial.recent_transactions.length > 0 && (
                  <ul className="executive__transaction-list">
                    {financial.recent_transactions.map((txn: RecentTransactionRow) => (
                      <li key={txn.transaction_id}>
                        <Link href={moduleHref(txn.link_module, txn.link_query)}>
                          <span>{formatShortDate(txn.transaction_date, locale)}</span>
                          <strong>{txn.description ?? txn.transaction_type}</strong>
                          <span>{formatMoney(txn.amount, txn.currency, locale)}</span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </SectionShell>

          <SectionShell
            title={t('construction.title')}
            badge={t('construction.limitedBadge')}
            state={constructionState}
            errorMessage={t('errors.section')}
            onRetry={() => void loadConstruction()}
            retryLabel={tCommon('retry')}
          >
            {construction && (
              <>
                {construction.delayed_projects.length === 0 ? (
                  <p className="leads__state">{t('construction.empty')}</p>
                ) : (
                  <ul className="executive__delayed-list">
                    {construction.delayed_projects.map((project: DelayedProjectRow) => (
                      <li key={project.project_id}>
                        <Link href={moduleHref(project.link_module, project.link_query)}>
                          <strong>{project.project_name}</strong>
                          <span>{healthLabel(project.health_status)}</span>
                          <span>{formatShortDate(project.completion_target, locale)}</span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
                <p className="executive__meta">{t('construction.unavailableNote')}</p>
              </>
            )}
          </SectionShell>

          <div className="executive__grid-three">
            <SectionShell
              title={t('tasks.title')}
              badge={t('tasks.comingSoonBadge')}
              state={'success'}
              retryLabel={tCommon('retry')}
            >
              <p className="leads__state">{t('tasks.empty')}</p>
            </SectionShell>

            <SectionShell
              id="executive-approvals"
              title={t('approvals.title')}
              state={approvalsState}
              errorMessage={t('errors.section')}
              onRetry={() => void loadApprovals()}
              retryLabel={tCommon('retry')}
            >
              {approvals.length === 0 ? (
                <p className="leads__state">{t('approvals.empty')}</p>
              ) : (
                <ul className="executive__approval-list">
                  {approvals.map((item) => (
                    <li key={`${item.approval_type}-${item.entity_id}`}>
                      <Link href={moduleHref(item.link_module, item.link_query)}>
                        <span className="executive__approval-type">{t(`approvals.types.${item.approval_type}` as 'approvals.types.design_review')}</span>
                        <strong>
                          {t(stripExecutivePrefix(item.title_key) as 'approvals.design_review.title', metadataForExecutiveI18n(item.metadata ?? {}))}
                          {item.related_label ? `: ${item.related_label}` : ''}
                        </strong>
                        {item.age_days !== null && (
                          <span className="executive__approval-age">
                            {t('approvals.ageDays', { days: item.age_days })}
                          </span>
                        )}
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </SectionShell>

            <SectionShell
              title={t('calendar.title')}
              badge={t('calendar.comingSoonBadge')}
              state={deadlineState}
              errorMessage={t('errors.section')}
              onRetry={() => void loadDeadlines()}
              retryLabel={tCommon('retry')}
            >
              {deadlines.length === 0 ? (
                <p className="leads__state">{t('calendar.empty')}</p>
              ) : (
                <ul className="executive__deadline-list">
                  {deadlines.slice(0, 8).map((item) => (
                    <li key={`${item.entity_type}-${item.entity_id}-${item.due_date}`}>
                      <Link href={moduleHref(item.link_module, item.link_query)}>
                        <span className="executive__deadline-window">{deadlineWindowLabel(item.window)}</span>
                        <strong>{item.title}</strong>
                        <span>{formatShortDate(item.due_date, locale)}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </SectionShell>
          </div>

          <SectionShell
            title={t('activity.title')}
            state={activityState}
            errorMessage={t('errors.section')}
            onRetry={() => void loadActivity()}
            retryLabel={tCommon('retry')}
          >
            {activity.length === 0 ? (
              <p className="leads__state">{t('activity.empty')}</p>
            ) : (
              <>
                <ul className="executive__activity-list">
                  {activity.map((item) => {
                    const href = item.link_module
                      ? moduleHref(item.link_module, { id: item.entity_id })
                      : null;
                    const summary = getActivityDescription(
                      item.description_key,
                      metadataForI18n(item.metadata),
                    );
                    const content = (
                      <>
                        <span>{formatShortDate(item.created_at, locale)}</span>
                        <p>{summary}</p>
                        {item.actor && <span className="activity-timeline__actor">{item.actor}</span>}
                        {item.entity_label && <span>{item.entity_label}</span>}
                      </>
                    );
                    return (
                      <li key={item.id}>
                        {href ? (
                          <Link href={href} className="executive__activity-link">
                            {content}
                          </Link>
                        ) : (
                          content
                        )}
                      </li>
                    );
                  })}
                </ul>
                <Link href={'/dashboard/activity' as Route} className="executive__view-all">
                  {t('activity.viewAll')}
                </Link>
              </>
            )}
          </SectionShell>
        </div>

        <AiInsightsPanel
          state={aiState}
          insights={aiInsights}
          expanded={aiExpanded}
          onToggle={() => setAiExpanded((value) => !value)}
          onRetry={() => void loadAiInsights()}
          locale={locale}
          t={t}
          tCommon={tCommon}
        />
      </div>
    </main>
  );
}
