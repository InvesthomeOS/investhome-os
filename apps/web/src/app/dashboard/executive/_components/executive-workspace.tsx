'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import {
  EXECUTIVE_FILTER_STORAGE_KEY,
  type ActivityItem,
  type AiInsightItem,
  type ApprovalItem,
  type AttentionItem,
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
  fetchExecutiveAttention,
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
import { useNotifications } from '@/lib/notifications/notification-context';
import { useNotificationLabels } from '@/lib/i18n/notification-labels';
import { metadataForNotification } from '@/lib/api/notifications';
import { fetchDocuments } from '@/lib/api/documents';
import { canReadMarketing } from '@/lib/marketing/marketing-permissions';
import { fetchFinanceStats, type FinanceStats } from '@/lib/api/finance';
import { fetchExecutiveDashboard as fetchMarketingExecutiveDashboard } from '@/workspaces/marketing/api/analytics';

import { AlertCenter } from './command-center/alert-center';
import { ProductionExecutiveDashboard } from './production-dashboard/production-executive-dashboard';
import { trackExecutiveUiEvent } from './production-dashboard/executive-ui-analytics';
import {
  G8ExecutiveDashboard,
  type MarketingPulse,
} from './production-dashboard/g8/g8-executive-dashboard';
import {
  activityModuleLabel,
  buildExecutiveKpis,
  deriveCompanyHealth,
  mergeAlerts,
  toPriorityViews,
} from './command-center/build-metrics';
import { CompanyHealthPanel } from './command-center/company-health-panel';
import { ExecutiveKpiBar } from './command-center/executive-kpi-bar';
import { GlobalSearchEntry } from './command-center/global-search-entry';
import { MyWorkPanel } from './command-center/my-work-panel';
import { QuickActionsBar } from './command-center/quick-actions-bar';
import { TodaysPriorities } from './command-center/todays-priorities';
import type { AlertItemView, LoadState as EccLoadState, MyWorkItem } from './command-center/types';

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
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, loading: authLoading } = useAuth();
  const { getStatusLabel: getLeadStatusLabel } = useLeadLabels();
  const { getStatusLabel: getProjectStatusLabel } = useProjectLabels();
  const { getDescription: getActivityDescription } = useActivityLabels();
  const {
    items: notifications,
    canView: canViewNotifications,
    openDrawer: openNotificationsDrawer,
  } = useNotifications();
  const { getTitle: getNotificationTitle } = useNotificationLabels();

  const [stored, setStored] = useState<StoredFilters>(DEFAULT_STORED);
  const [projectOptions, setProjectOptions] = useState<{ id: string; label: string }[]>([]);
  const [aiExpanded, setAiExpanded] = useState(true);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string | null>(null);
  const viewParam = searchParams.get('view');
  // D1D.2 / G8: default → G8 command center; ?view=d1d → prior production; ?view=legacy → OLD ECC.
  const useLegacyLayout = viewParam === 'legacy';
  const useD1dLayout = viewParam === 'd1d' || viewParam === 'production';
  const useG8Layout = !useLegacyLayout && !useD1dLayout;
  const useProductionLayout = useG8Layout || useD1dLayout;
  const forcePartialDemo = searchParams.get('partial') === '1';
  const canViewExecutive = !!(user && hasPermission(user, 'executive', 'view'));

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
  const [attention, setAttention] = useState<AttentionItem[]>([]);
  const [attentionState, setAttentionState] = useState<LoadState>('loading');
  const [documents, setDocuments] = useState<{ id: string; title: string; updated_at?: string; created_at?: string }[]>([]);
  const [documentsState, setDocumentsState] = useState<LoadState>('idle');

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
  const [financeStats, setFinanceStats] = useState<FinanceStats | null>(null);
  const [financeStatsState, setFinanceStatsState] = useState<LoadState>('idle');
  const [marketingPulse, setMarketingPulse] = useState<MarketingPulse>({
    kpis: [],
    funnelStages: [],
    bestChannel: null,
    state: 'idle',
    classification: 'NOT_CONFIGURED',
  });

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
    if (useG8Layout) {
      setAiExpanded(true);
      trackExecutiveUiEvent('executive_layout_mode', { layout: 'g8' });
    } else if (useD1dLayout) {
      setAiExpanded(true);
      trackExecutiveUiEvent('executive_layout_mode', { layout: 'production' });
    } else {
      trackExecutiveUiEvent('executive_layout_mode', { layout: 'legacy' });
    }
  }, [useD1dLayout, useG8Layout]);

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
    if (!aiExpanded && !useProductionLayout) return;
    setAiState('loading');
    try {
      setAiInsights(await fetchExecutiveAiInsights(filterParams));
      setAiState('success');
    } catch {
      setAiState('error');
    }
  }, [aiExpanded, filterParams, useProductionLayout]);

  const loadAttention = useCallback(async () => {
    setAttentionState('loading');
    try {
      const response = await fetchExecutiveAttention(filterParams);
      setAttention(response.items);
      setAttentionState('success');
    } catch {
      setAttentionState('error');
    }
  }, [filterParams]);

  const loadDocuments = useCallback(async () => {
    if (!user || !hasPermission(user, 'documents', 'view')) {
      setDocumentsState('idle');
      setDocuments([]);
      return;
    }
    setDocumentsState('loading');
    try {
      const response = await fetchDocuments({ page: 1, page_size: 5, sort_by: 'updated_at', sort_dir: 'desc' });
      setDocuments(
        response.items.map((doc) => ({
          id: doc.id,
          title: doc.title || doc.original_file_name || doc.id,
          updated_at: doc.updated_at,
          created_at: doc.created_at,
        })),
      );
      setDocumentsState('success');
    } catch {
      setDocumentsState('error');
    }
  }, [user]);

  const loadFinanceStats = useCallback(async () => {
    if (!user || !hasPermission(user, 'finance', 'view')) {
      setFinanceStats(null);
      setFinanceStatsState('idle');
      return;
    }
    setFinanceStatsState('loading');
    try {
      setFinanceStats(await fetchFinanceStats());
      setFinanceStatsState('success');
    } catch {
      setFinanceStatsState('error');
    }
  }, [user]);

  const loadMarketingPulse = useCallback(async () => {
    if (!canReadMarketing(user)) {
      setMarketingPulse({
        kpis: [],
        funnelStages: [],
        bestChannel: null,
        state: 'idle',
        classification: 'BLOCKED',
      });
      return;
    }
    setMarketingPulse((prev) => ({ ...prev, state: 'loading' }));
    try {
      const data = await fetchMarketingExecutiveDashboard({ preset: 'last_30_days' });
      const readyKpis = (data.kpis || []).filter((k) => k.state === 'ready' || k.value != null);
      setMarketingPulse({
        kpis: data.kpis || [],
        funnelStages: (data.funnel?.stages || []).map((s) => ({
          key: s.key,
          label: s.label,
          count: s.count ?? null,
        })),
        bestChannel:
          typeof data.health?.categories?.find((c) => c.key.includes('channel'))?.label === 'string'
            ? data.health.categories.find((c) => c.key.includes('channel'))!.label
            : null,
        state: 'success',
        classification: readyKpis.length > 0 ? 'LIVE' : 'PARTIAL',
      });
    } catch {
      setMarketingPulse({
        kpis: [],
        funnelStages: [],
        bestChannel: null,
        state: 'error',
        classification: 'PARTIAL',
      });
    }
  }, [user]);

  useEffect(() => {
    if (authLoading) return;
    if (!canViewExecutive) {
      setSummaryState('idle');
      setPipelineState('idle');
      setInvestorState('idle');
      setPortfolioState('idle');
      setFinancialState('idle');
      setConstructionState('idle');
      setApprovalsState('idle');
      setDeadlineState('idle');
      setActivityState('idle');
      setAttentionState('idle');
      setAiState('idle');
      return;
    }
    void loadSummary();
    void loadPipeline();
    void loadInvestors();
    void loadPortfolio();
    void loadFinancial();
    void loadConstruction();
    void loadApprovals();
    void loadDeadlines();
    void loadActivity();
    void loadAttention();
    void loadDocuments();
    void loadFinanceStats();
    void loadMarketingPulse();
    setLastRefreshedAt(new Date().toISOString());
  }, [
    authLoading,
    canViewExecutive,
    loadActivity,
    loadApprovals,
    loadAttention,
    loadConstruction,
    loadDeadlines,
    loadDocuments,
    loadFinanceStats,
    loadFinancial,
    loadInvestors,
    loadMarketingPulse,
    loadPipeline,
    loadPortfolio,
    loadSummary,
  ]);

  useEffect(() => {
    if (authLoading || !canViewExecutive) return;
    void loadAiInsights();
  }, [authLoading, canViewExecutive, loadAiInsights]);

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
    const actions: { href: Route; label: string; show: boolean }[] = [
      {
        href: '/dashboard/leads' as Route,
        label: t('commandCenter.quickActions.createLead'),
        show: !!(user && hasPermission(user, 'leads', 'create')),
      },
      {
        href: '/dashboard/investors' as Route,
        label: t('commandCenter.quickActions.createInvestor'),
        show: !!(user && hasPermission(user, 'investors', 'create')),
      },
      {
        href: '/dashboard/projects' as Route,
        label: t('commandCenter.quickActions.addProject'),
        show: !!(user && hasPermission(user, 'projects', 'create')),
      },
      {
        href: '/workspaces/marketing/campaigns' as Route,
        label: t('commandCenter.quickActions.sendCampaign'),
        show: canReadMarketing(user),
      },
      {
        href: '/dashboard/finance' as Route,
        label: t('commandCenter.quickActions.approveExpense'),
        show: !!(user && hasPermission(user, 'finance', 'view')),
      },
      {
        href: '/dashboard/finance?view=approvals' as Route,
        label: t('commandCenter.quickActions.reviewApprovals'),
        show: !!(user && hasPermission(user, 'finance', 'view')),
      },
      {
        href: '/workspaces/marketing/reports' as Route,
        label: t('commandCenter.quickActions.openReports'),
        show: canReadMarketing(user),
      },
      {
        href: '/dashboard/documents' as Route,
        label: t('quickActions.uploadDocument'),
        show: !!(user && hasPermission(user, 'documents', 'create')),
      },
    ];
    return actions;
  }, [t, user]);

  const activeInvestorCount = investors?.by_status.find((row) => row.status === 'active')?.count ?? 0;

  const overduePaymentsPresent =
    financial !== null &&
    Object.values(financial.overdue_payments || {}).some((v) => Number(v) > 0);

  const health = deriveCompanyHealth({
    attention,
    projects: portfolio?.projects ?? [],
    overduePaymentsPresent,
  });

  const priorityItems = useMemo(() => {
    const resolveTitle = (item: AttentionItem) => {
      try {
        return t(stripExecutivePrefix(item.title_key) as 'attention.overdue_payment.title', metadataForExecutiveI18n(item.metadata));
      } catch {
        return item.related_label ?? item.title_key;
      }
    };
    const resolveDescription = (item: AttentionItem) => {
      try {
        return t(stripExecutivePrefix(item.description_key) as 'attention.overdue_payment.description', metadataForExecutiveI18n(item.metadata));
      } catch {
        return item.related_label ?? '';
      }
    };
    const resolveDue = (item: AttentionItem) =>
      item.due_date ? formatShortDate(item.due_date, locale) : item.age_days != null ? t('approvals.ageDays', { days: item.age_days }) : null;
    const resolveCategory = (item: AttentionItem) => activityModuleLabel(item.entity_type);
    return toPriorityViews(attention, resolveTitle, resolveDescription, resolveDue, resolveCategory);
  }, [attention, locale, t]);

  const kpiMetrics = useMemo(() => {
    const pipelineValue =
      Object.keys(salesPipelineByCurrency).length > 0
        ? formatSalesCurrencyTotals(salesPipelineByCurrency, locale)
        : null;
    const revenue =
      financial && Object.keys(financial.income_in_period || {}).length > 0
        ? formatCurrencyTotals(financial.income_in_period, locale)
        : null;
    return buildExecutiveKpis({
      locale,
      labels: {
        revenue: t('commandCenter.kpi.revenue'),
        cash: t('commandCenter.kpi.cash'),
        pipeline: t('commandCenter.kpi.pipeline'),
        investors: t('commandCenter.kpi.investors'),
        openDeals: t('commandCenter.kpi.openDeals'),
        projects: t('commandCenter.kpi.projects'),
        marketingRoi: t('commandCenter.kpi.marketingRoi'),
        tasksDue: t('commandCenter.kpi.tasksDue'),
      },
      hints: {
        revenue: t('commandCenter.kpiHints.revenue'),
        pipeline: t('commandCenter.kpiHints.pipeline'),
        openDeals: t('commandCenter.kpiHints.openDeals'),
        marketingRoi: t('commandCenter.kpiHints.marketingRoi'),
        tasksDue: t('commandCenter.kpiHints.tasksDue'),
      },
      summaryCards,
      pipelineValue,
      openDeals: salesMetrics ? salesMetrics.open_opportunities : null,
      revenue,
      marketingRoiAvailable: false,
      tasksAvailable: false,
    });
  }, [financial, locale, salesMetrics, salesPipelineByCurrency, summaryCards, t]);

  const alertItems = useMemo(() => {
    const fromAttention: AlertItemView[] = attention.map((item) => ({
      id: `att-${item.entity_type}-${item.entity_id}-${item.title_key}`,
      severity: item.severity,
      title: (() => {
        try {
          return t(stripExecutivePrefix(item.title_key) as 'attention.overdue_payment.title', metadataForExecutiveI18n(item.metadata));
        } catch {
          return item.related_label ?? item.title_key;
        }
      })(),
      description: (() => {
        try {
          return t(stripExecutivePrefix(item.description_key) as 'attention.overdue_payment.description', metadataForExecutiveI18n(item.metadata));
        } catch {
          return item.related_label ?? '';
        }
      })(),
      href: moduleHref(item.link_module, item.link_query),
      source: activityModuleLabel(item.entity_type),
    }));
    const fromNotifications: AlertItemView[] = canViewNotifications
      ? notifications
          .filter((n) => n.status === 'unread' || !n.read_at)
          .slice(0, 20)
          .map((n) => ({
            id: `notif-${n.id}`,
            severity:
              n.priority === 'critical' ? 'critical' : n.priority === 'high' ? 'warning' : 'information',
            title: getNotificationTitle(n.title_key, metadataForNotification(n.metadata)),
            description: n.related_label ?? '',
            href: null,
            source: t('commandCenter.alertSources.notifications'),
          }))
      : [];
    return mergeAlerts(fromAttention, fromNotifications);
  }, [attention, canViewNotifications, getNotificationTitle, notifications, t]);

  const myWorkItems = useMemo(() => {
    const items: MyWorkItem[] = [];
    for (const item of approvals.slice(0, 5)) {
      items.push({
        id: `appr-${item.approval_type}-${item.entity_id}`,
        title: (() => {
          try {
            return t(stripExecutivePrefix(item.title_key) as 'approvals.design_review.title', metadataForExecutiveI18n(item.metadata ?? {}));
          } catch {
            return item.related_label ?? item.approval_type;
          }
        })(),
        meta: item.age_days != null ? t('approvals.ageDays', { days: item.age_days }) : t(`approvals.types.${item.approval_type}` as 'approvals.types.design_review'),
        href: moduleHref(item.link_module, item.link_query),
        kind: 'approval',
      });
    }
    for (const item of deadlines.filter((d) => d.window === 'overdue' || d.window === 'next_7_days').slice(0, 4)) {
      items.push({
        id: `dl-${item.entity_type}-${item.entity_id}-${item.due_date}`,
        title: item.title,
        meta: formatShortDate(item.due_date, locale),
        href: moduleHref(item.link_module, item.link_query),
        kind: 'meeting',
      });
    }
    for (const doc of documents.slice(0, 3)) {
      items.push({
        id: `doc-${doc.id}`,
        title: doc.title,
        meta: formatShortDate(doc.updated_at || doc.created_at || '', locale),
        href: `/dashboard/documents` as Route,
        kind: 'document',
      });
    }
    for (const act of activity.slice(0, 3)) {
      items.push({
        id: `act-${act.id}`,
        title: getActivityDescription(act.description_key, metadataForI18n(act.metadata)),
        meta: `${activityModuleLabel(act.entity_type)} · ${formatShortDate(act.created_at, locale)}`,
        href: act.link_module ? moduleHref(act.link_module, { id: act.entity_id }) : ('/dashboard/activity' as Route),
        kind: 'activity',
      });
    }
    return items;
  }, [activity, approvals, deadlines, documents, getActivityDescription, locale, t]);

  const kpiLoadState: EccLoadState =
    summaryState === 'error' || financialState === 'error' || pipelineState === 'error'
      ? 'error'
      : summaryState === 'loading' || financialState === 'loading' || pipelineState === 'loading'
        ? 'loading'
        : 'success';

  const healthState: EccLoadState =
    attentionState === 'loading' || portfolioState === 'loading' || financialState === 'loading'
      ? 'loading'
      : attentionState === 'error' && portfolioState === 'error'
        ? 'error'
        : 'success';

  const myWorkState: EccLoadState =
    approvalsState === 'error' || deadlineState === 'error'
      ? 'error'
      : approvalsState === 'loading' || deadlineState === 'loading' || documentsState === 'loading'
        ? 'loading'
        : 'success';

  const refreshAll = useCallback(() => {
    void loadSummary();
    void loadPipeline();
    void loadInvestors();
    void loadPortfolio();
    void loadFinancial();
    void loadConstruction();
    void loadApprovals();
    void loadDeadlines();
    void loadActivity();
    void loadAttention();
    void loadDocuments();
    void loadAiInsights();
    void loadFinanceStats();
    void loadMarketingPulse();
    setLastRefreshedAt(new Date().toISOString());
  }, [
    loadActivity,
    loadAiInsights,
    loadApprovals,
    loadAttention,
    loadConstruction,
    loadDeadlines,
    loadDocuments,
    loadFinanceStats,
    loadFinancial,
    loadInvestors,
    loadMarketingPulse,
    loadPipeline,
    loadPortfolio,
    loadSummary,
  ]);

  const handleProductionRetry = useCallback(
    (widgetId: string) => {
      if (widgetId === 'exec.cash_trend') void loadFinancial();
      else if (widgetId === 'exec.tasks_approvals') void loadApprovals();
      else if (widgetId === 'exec.calendar_deadlines') void loadDeadlines();
      else if (widgetId === 'exec.sales_funnel') void loadPipeline();
      else if (widgetId === 'exec.investor_pulse') void loadInvestors();
      else if (widgetId === 'exec.projects_progress') void loadPortfolio();
      else refreshAll();
    },
    [
      loadApprovals,
      loadDeadlines,
      loadFinancial,
      loadInvestors,
      loadPipeline,
      loadPortfolio,
      refreshAll,
    ],
  );

  if (useProductionLayout) {
    if (authLoading) {
      return (
        <main className="dashboard executive" data-testid="executive-dashboard-auth-loading">
          <div className="executive__skeleton" aria-busy="true" aria-label={tCommon('loading')} />
        </main>
      );
    }

    const pipelineValue =
      Object.keys(salesPipelineByCurrency).length > 0
        ? formatSalesCurrencyTotals(salesPipelineByCurrency, locale)
        : null;

    const sharedResolveInsightTitle = (item: AiInsightItem) => {
      try {
        return t(
          stripExecutivePrefix(item.title_key) as 'aiPanel.deadline_priority.title',
          metadataForExecutiveI18n(item.metadata),
        );
      } catch {
        return item.title_key;
      }
    };
    const sharedResolveInsightDescription = (item: AiInsightItem) => {
      try {
        return t(
          stripExecutivePrefix(item.description_key) as 'aiPanel.deadline_priority.description',
          metadataForExecutiveI18n(item.metadata),
        );
      } catch {
        return item.description_key;
      }
    };
    const sharedResolveApprovalTitle = (item: ApprovalItem) => {
      try {
        return t(
          stripExecutivePrefix(item.title_key) as 'approvals.design_review.title',
          metadataForExecutiveI18n(item.metadata ?? {}),
        );
      } catch {
        return item.related_label ?? item.approval_type;
      }
    };
    const sharedResolveAttentionTitle = (item: AttentionItem) => {
      try {
        return t(
          stripExecutivePrefix(item.title_key) as 'attention.overdue_payment.title',
          metadataForExecutiveI18n(item.metadata),
        );
      } catch {
        return item.related_label ?? item.title_key;
      }
    };
    const sharedResolveAttentionReason = (item: AttentionItem) => {
      try {
        return t(
          stripExecutivePrefix(item.description_key) as 'attention.overdue_payment.description',
          metadataForExecutiveI18n(item.metadata),
        );
      } catch {
        return item.related_label ?? '';
      }
    };

    if (useG8Layout) {
      return (
        <G8ExecutiveDashboard
          user={user}
          periodPreset={stored.preset}
          dateFrom={filterParams.date_from ?? ''}
          dateTo={filterParams.date_to ?? ''}
          onPeriodChange={(from, to) =>
            persistFilters({ ...stored, preset: 'custom', customFrom: from, customTo: to })
          }
          onPeriodPresetChange={(preset) => persistFilters({ ...stored, preset })}
          onRefresh={refreshAll}
          lastRefreshedAt={lastRefreshedAt}
          onOpenLegacy={() => {
            const params = new URLSearchParams(searchParams.toString());
            params.set('view', 'legacy');
            router.push(`/dashboard/executive?${params.toString()}` as Route);
          }}
          projectOptions={projectOptions}
          projectId={stored.project_id}
          onProjectChange={(id) => persistFilters({ ...stored, project_id: id })}
          assignedTo={stored.assigned_to}
          onAssignedChange={(value) => persistFilters({ ...stored, assigned_to: value })}
          currency={stored.currency}
          onCurrencyChange={(value) => persistFilters({ ...stored, currency: value })}
          summaryCards={summaryCards}
          summaryState={summaryState}
          financial={financial}
          financialState={financialState}
          financeStats={financeStats}
          financeStatsState={financeStatsState}
          pipeline={pipeline}
          pipelineState={pipelineState}
          salesPipelineValue={pipelineValue}
          openDeals={salesMetrics ? salesMetrics.open_opportunities : null}
          pipelineStateForKpi={pipelineState}
          investors={investors}
          investorState={investorState}
          portfolio={portfolio}
          portfolioState={portfolioState}
          construction={construction}
          constructionState={constructionState}
          approvals={approvals}
          approvalsState={approvalsState}
          deadlines={deadlines}
          deadlineState={deadlineState}
          activity={activity}
          activityState={activityState}
          attention={attention}
          aiInsights={aiInsights}
          aiState={aiState}
          onRetryAi={() => void loadAiInsights()}
          alertItems={alertItems}
          attentionState={attentionState}
          onRetryAttention={() => void loadAttention()}
          notifications={notifications}
          canViewNotifications={canViewNotifications}
          onOpenNotifications={openNotificationsDrawer}
          getNotificationTitle={getNotificationTitle}
          marketing={marketingPulse}
          canReadMarketing={canReadMarketing(user)}
          canViewExecutive={canViewExecutive}
          quickActions={quickActions}
          getLeadStatusLabel={getLeadStatusLabel}
          getProjectStatusLabel={getProjectStatusLabel}
          resolveInsightTitle={sharedResolveInsightTitle}
          resolveInsightDescription={sharedResolveInsightDescription}
          resolveApprovalTitle={sharedResolveApprovalTitle}
          resolveAttentionTitle={sharedResolveAttentionTitle}
          resolveAttentionReason={sharedResolveAttentionReason}
          resolveActivityTitle={(item) =>
            getActivityDescription(item.description_key, metadataForI18n(item.metadata))
          }
          onRetry={handleProductionRetry}
          forcePartialDemo={forcePartialDemo}
        />
      );
    }

    return (
      <ProductionExecutiveDashboard
        periodPreset={stored.preset}
        dateFrom={filterParams.date_from ?? ''}
        dateTo={filterParams.date_to ?? ''}
        onPeriodChange={(from, to) =>
          persistFilters({ ...stored, preset: 'custom', customFrom: from, customTo: to })
        }
        onRefresh={refreshAll}
        lastRefreshedAt={lastRefreshedAt}
        onOpenLegacy={() => {
          const params = new URLSearchParams(searchParams.toString());
          params.set('view', 'legacy');
          router.push(`/dashboard/executive?${params.toString()}` as Route);
        }}
        projectOptions={projectOptions}
        projectId={stored.project_id}
        onProjectChange={(id) => persistFilters({ ...stored, project_id: id })}
        assignedTo={stored.assigned_to}
        onAssignedChange={(value) => persistFilters({ ...stored, assigned_to: value })}
        currency={stored.currency}
        onCurrencyChange={(value) => persistFilters({ ...stored, currency: value })}
        summaryCards={summaryCards}
        summaryState={summaryState}
        financial={financial}
        financialState={financialState}
        pipeline={pipeline}
        pipelineState={pipelineState}
        salesPipelineValue={pipelineValue}
        openDeals={salesMetrics ? salesMetrics.open_opportunities : null}
        pipelineStateForKpi={pipelineState}
        investors={investors}
        investorState={investorState}
        portfolio={portfolio}
        portfolioState={portfolioState}
        approvals={approvals}
        approvalsState={approvalsState}
        deadlines={deadlines}
        deadlineState={deadlineState}
        aiInsights={aiInsights}
        aiState={aiState}
        onRetryAi={() => void loadAiInsights()}
        alertItems={alertItems}
        attentionState={attentionState}
        onRetryAttention={() => void loadAttention()}
        notifications={notifications}
        canViewNotifications={canViewNotifications}
        onOpenNotifications={openNotificationsDrawer}
        getNotificationTitle={getNotificationTitle}
        canReadMarketing={canReadMarketing(user)}
        canViewExecutive={canViewExecutive}
        quickActions={quickActions}
        getLeadStatusLabel={getLeadStatusLabel}
        getProjectStatusLabel={getProjectStatusLabel}
        resolveInsightTitle={sharedResolveInsightTitle}
        resolveInsightDescription={sharedResolveInsightDescription}
        resolveApprovalTitle={sharedResolveApprovalTitle}
        onRetry={handleProductionRetry}
      />
    );
  }

  return (
    <main
      className="dashboard leads investors finance executive executive--premium"
      data-testid="executive-dashboard-legacy"
      data-sprint="D1D-legacy"
    >
      <header className="dashboard__header leads__header">
        <p className="dashboard__eyebrow executive__eyebrow-premium">{t('eyebrow')}</p>
        <h1 className="dashboard__title executive__title-premium">{t('title')}</h1>
        <p className="leads__subtitle">{t('subtitle')}</p>
        <p className="leads__subtitle">
          <Link href={'/dashboard/executive?view=production' as Route}>
            {t('production.openProduction')}
          </Link>
        </p>
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
      </section>

      <div className="ecc-command">
        <GlobalSearchEntry
          title={t('commandCenter.search.title')}
          hint={t('commandCenter.search.hint')}
          cta={t('commandCenter.search.cta')}
          unavailable={t('commandCenter.search.unavailable')}
        />

        <CompanyHealthPanel
          state={healthState}
          tone={health.tone}
          title={t('commandCenter.companyHealth.title')}
          statusLabel={t(`commandCenter.companyHealth.tones.${health.tone}`)}
          summary={t('commandCenter.companyHealth.summary')}
          criticalCount={health.criticalCount}
          warningCount={health.warningCount}
          atRiskProjects={health.atRiskProjects}
          overduePayments={overduePaymentsPresent}
          labels={{
            critical: t('commandCenter.companyHealth.critical'),
            warning: t('commandCenter.companyHealth.warning'),
            atRiskProjects: t('commandCenter.companyHealth.atRiskProjects'),
            overduePayments: t('commandCenter.companyHealth.overduePayments'),
            noSignals: t('commandCenter.companyHealth.noSignals'),
          }}
          onRetry={() => {
            void loadAttention();
            void loadPortfolio();
            void loadFinancial();
          }}
          retryLabel={tCommon('retry')}
          href={'#executive-priorities' as Route}
        />

        <ExecutiveKpiBar
          title={t('commandCenter.kpi.title')}
          metrics={kpiMetrics}
          state={kpiLoadState}
          labels={{
            unavailable: t('commandCenter.metric.unavailable'),
            empty: t('commandCenter.metric.empty'),
            loading: t('commandCenter.metric.loading'),
          }}
          onRetry={() => {
            void loadSummary();
            void loadFinancial();
            void loadPipeline();
          }}
          retryLabel={tCommon('retry')}
        />

        <QuickActionsBar
          title={t('commandCenter.quickActions.title')}
          actions={quickActions}
          empty={t('commandCenter.quickActions.empty')}
        />

        <div className="ecc-split">
          <TodaysPriorities
            id="executive-priorities"
            title={t('commandCenter.priorities.title')}
            hint={t('commandCenter.priorities.hint')}
            items={priorityItems}
            state={attentionState}
            emptyTitle={t('commandCenter.priorities.emptyTitle')}
            emptyBody={t('commandCenter.priorities.emptyBody')}
            severityLabels={{
              critical: t('severity.critical'),
              warning: t('severity.warning'),
              information: t('severity.information'),
            }}
            onRetry={() => void loadAttention()}
            retryLabel={tCommon('retry')}
            errorMessage={t('errors.section')}
          />
          <AlertCenter
            title={t('commandCenter.alerts.title')}
            items={alertItems}
            state={attentionState}
            empty={t('commandCenter.alerts.empty')}
            filterLabels={{
              all: t('commandCenter.alerts.filters.all'),
              critical: t('severity.critical'),
              warning: t('severity.warning'),
              information: t('severity.information'),
            }}
            severityLabels={{
              critical: t('severity.critical'),
              warning: t('severity.warning'),
              information: t('severity.information'),
            }}
            onRetry={() => void loadAttention()}
            retryLabel={tCommon('retry')}
            errorMessage={t('errors.section')}
          />
        </div>

        <div className="ecc-split">
          <MyWorkPanel
            title={t('commandCenter.myWork.title')}
            hint={t('commandCenter.myWork.hint')}
            items={myWorkItems}
            state={myWorkState}
            empty={t('commandCenter.myWork.empty')}
            unavailableTasks={t('commandCenter.myWork.unavailableTasks')}
            unavailableMeetings={t('commandCenter.myWork.unavailableMeetings')}
            kindLabels={{
              approval: t('commandCenter.myWork.kinds.approval'),
              task: t('commandCenter.myWork.kinds.task'),
              meeting: t('commandCenter.myWork.kinds.meeting'),
              document: t('commandCenter.myWork.kinds.document'),
              activity: t('commandCenter.myWork.kinds.activity'),
            }}
            onRetry={() => {
              void loadApprovals();
              void loadDeadlines();
              void loadDocuments();
            }}
            retryLabel={tCommon('retry')}
            errorMessage={t('errors.section')}
          />
          <section className="ecc-note-panel" hidden aria-hidden="true" />
        </div>
      </div>

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
                        <span className="ecc-activity-module">{activityModuleLabel(item.entity_type)}</span>
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
