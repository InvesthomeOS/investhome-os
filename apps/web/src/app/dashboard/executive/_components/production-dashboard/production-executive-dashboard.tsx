'use client';

import {
  DateRangeControl,
  IconButton,
  MetricCard,
  RightRailCard,
  StatusBadge,
  WidgetMenu,
  WidgetShell,
} from '@investhome/ui';
import type { Route } from 'next';
import Link from 'next/link';
import { useLocale, useTranslations } from 'next-intl';
import { useEffect, useMemo } from 'react';

import {
  AreaChart,
  DonutChart,
  FunnelChart,
  ProgressChart,
  Sparkline,
  TimelineChart,
} from '@/components/design-system/charts';
import {
  AppPage,
  ContentContainer,
  DashboardGrid,
  PageHeader,
  RightRail,
  WidgetColumn,
} from '@/components/design-system/layout';
import { IhIcon } from '@/components/icons/ih-icons';
import type {
  AiInsightItem,
  ApprovalItem,
  AttentionItem,
  CashFlowPoint,
  DeadlineItem,
  ExecutivePeriodPreset,
  ProjectHealthRow,
  SummaryCard,
} from '@/lib/api/executive';
import {
  formatCurrencyTotals,
  formatMoney,
  formatShortDate,
  moduleHref,
} from '@/lib/api/executive';
import type { NotificationItem } from '@/lib/api/notifications';
import type { AlertItemView } from '../command-center/types';

import { trackExecutiveUiEvent } from './executive-ui-analytics';
import { toShellState, type WidgetLoadState } from './load-state';
import { PRODUCTION_MOBILE_ORDER } from './mobile-order';

export interface ProductionExecutiveDashboardProps {
  periodPreset: ExecutivePeriodPreset;
  dateFrom: string;
  dateTo: string;
  onPeriodChange: (from: string, to: string) => void;
  onRefresh: () => void;
  lastRefreshedAt: string | null;
  onOpenLegacy: () => void;
  projectOptions: { id: string; label: string }[];
  projectId: string;
  onProjectChange: (id: string) => void;
  assignedTo: string;
  onAssignedChange: (value: string) => void;
  currency: string;
  onCurrencyChange: (value: string) => void;
  summaryCards: SummaryCard[];
  summaryState: WidgetLoadState;
  financial: {
    available_cash: Record<string, string>;
    income_in_period: Record<string, string>;
    expenses_in_period: Record<string, string>;
    cash_flow_trend: CashFlowPoint[];
    overdue_payments: Record<string, string>;
  } | null;
  financialState: WidgetLoadState;
  pipeline: {
    stages: { status: string; count: number; estimated_budget_total: string }[];
    summary: {
      total: number;
      qualified: number;
      meetings: number;
      proposals: number;
      won: number;
      lost: number;
    };
  } | null;
  pipelineState: WidgetLoadState;
  salesPipelineValue: string | null;
  openDeals: number | null;
  pipelineStateForKpi: WidgetLoadState;
  investors: {
    by_status: { status: string; count: number }[];
    total_investment_capacity: Record<string, string>;
    total_committed: Record<string, string>;
    upcoming_follow_ups: AttentionItem[];
  } | null;
  investorState: WidgetLoadState;
  portfolio: { projects: ProjectHealthRow[] } | null;
  portfolioState: WidgetLoadState;
  approvals: ApprovalItem[];
  approvalsState: WidgetLoadState;
  deadlines: DeadlineItem[];
  deadlineState: WidgetLoadState;
  aiInsights: {
    priorities: AiInsightItem[];
    risks: AiInsightItem[];
    opportunities: AiInsightItem[];
    generated_at: string;
    ai_level: string;
  } | null;
  aiState: WidgetLoadState;
  onRetryAi: () => void;
  alertItems: AlertItemView[];
  attentionState: WidgetLoadState;
  onRetryAttention: () => void;
  notifications: NotificationItem[];
  canViewNotifications: boolean;
  onOpenNotifications: () => void;
  getNotificationTitle: (key: string, meta: Record<string, string>) => string;
  canReadMarketing: boolean;
  canViewExecutive: boolean;
  quickActions: { href: Route; label: string; show: boolean }[];
  getLeadStatusLabel: (status: string) => string;
  getProjectStatusLabel: (status: string) => string;
  resolveInsightTitle: (item: AiInsightItem) => string;
  resolveInsightDescription: (item: AiInsightItem) => string;
  resolveApprovalTitle: (item: ApprovalItem) => string;
  onRetry: (widgetId: string) => void;
}

function primaryCurrencyTotal(totals: Record<string, string> | undefined): {
  currency: string;
  value: number;
} | null {
  if (!totals) return null;
  const entries = Object.entries(totals).filter(([, v]) => Number(v) !== 0);
  const first = entries[0];
  if (!first) return null;
  const [currency, amount] = first;
  return { currency, value: Number(amount) };
}

export function ProductionExecutiveDashboard(props: ProductionExecutiveDashboardProps) {
  const t = useTranslations('executive');
  const tProd = useTranslations('executive.production');
  const tCommon = useTranslations('common');
  const locale = useLocale();

  useEffect(() => {
    trackExecutiveUiEvent('executive_dashboard_view', {
      layout: 'production',
      periodPreset: props.periodPreset,
    });
  }, [props.periodPreset]);

  const cashSparkline = useMemo(() => {
    if (!props.financial?.cash_flow_trend?.length) return null;
    return props.financial.cash_flow_trend.map((point) => {
      const primary = primaryCurrencyTotal(point.net);
      return primary?.value ?? 0;
    });
  }, [props.financial]);

  const cashTrendPoints = useMemo(() => {
    if (!props.financial?.cash_flow_trend?.length) return [];
    return props.financial.cash_flow_trend.map((point) => {
      const primary = primaryCurrencyTotal(point.net);
      return {
        label: formatShortDate(point.period_start, locale),
        value: primary?.value ?? 0,
      };
    });
  }, [props.financial, locale]);

  const cashTrendCurrency =
    props.financial?.cash_flow_trend
      .map((p) => primaryCurrencyTotal(p.net)?.currency)
      .find(Boolean) ?? 'USD';

  const kpiDefs = useMemo(() => {
    const byKey = Object.fromEntries(props.summaryCards.map((c) => [c.key, c]));
    const cashCard = byKey.available_cash;
    const cashValue =
      props.financial && Object.keys(props.financial.available_cash || {}).length > 0
        ? formatCurrencyTotals(props.financial.available_cash, locale)
        : cashCard?.currency_totals
          ? formatCurrencyTotals(cashCard.currency_totals, locale)
          : cashCard?.value != null
            ? String(cashCard.value)
            : null;

    const investorsCard = byKey.active_investors;
    const investorsValue =
      investorsCard?.value != null
        ? String(investorsCard.value)
        : props.investors
          ? String(props.investors.by_status.find((r) => r.status === 'active')?.count ?? 0)
          : null;

    const projectsCard = byKey.active_projects;
    const atRisk = props.portfolio?.projects.filter((p) => p.health_status === 'at_risk').length ?? 0;
    const projectsValue =
      projectsCard?.value != null
        ? String(projectsCard.value)
        : props.portfolio
          ? String(props.portfolio.projects.length)
          : null;

    return [
      {
        id: 'exec.kpi_cash',
        label: tProd('kpiCash'),
        value: cashValue,
        href: '/dashboard/finance' as Route,
        state: props.financialState === 'error' || props.summaryState === 'error'
          ? ('error' as const)
          : props.financialState === 'loading' || props.summaryState === 'loading'
            ? ('loading' as const)
            : cashValue == null || cashValue === '—'
              ? ('empty' as const)
              : ('ready' as const),
        sparkline: cashSparkline,
        hint: undefined as string | undefined,
      },
      {
        id: 'exec.kpi_pipeline',
        label: tProd('kpiPipeline'),
        value: props.salesPipelineValue,
        href: '/dashboard/sales' as Route,
        state:
          props.pipelineStateForKpi === 'error'
            ? ('error' as const)
            : props.pipelineStateForKpi === 'loading'
              ? ('loading' as const)
              : props.salesPipelineValue == null
                ? ('empty' as const)
                : props.salesPipelineValue === '—'
                  ? ('empty' as const)
                  : ('ready' as const),
        sparkline: null as number[] | null,
        hint: props.salesPipelineValue == null ? tProd('kpiPipelineHint') : undefined,
      },
      {
        id: 'exec.kpi_investors',
        label: tProd('kpiInvestors'),
        value: investorsValue,
        href: '/dashboard/investors' as Route,
        state:
          props.investorState === 'error' || props.summaryState === 'error'
            ? ('error' as const)
            : props.investorState === 'loading' || props.summaryState === 'loading'
              ? ('loading' as const)
              : investorsValue == null
                ? ('empty' as const)
                : ('ready' as const),
        sparkline: null as number[] | null,
        hint: undefined as string | undefined,
      },
      {
        id: 'exec.kpi_open_deals',
        label: tProd('kpiOpenDeals'),
        value: props.openDeals == null ? null : String(props.openDeals),
        href: '/dashboard/sales' as Route,
        state:
          props.pipelineStateForKpi === 'error'
            ? ('error' as const)
            : props.pipelineStateForKpi === 'loading'
              ? ('loading' as const)
              : props.openDeals == null
                ? ('empty' as const)
                : ('ready' as const),
        sparkline: null as number[] | null,
        hint: props.openDeals == null ? tProd('kpiOpenDealsHint') : undefined,
      },
      {
        id: 'exec.kpi_projects',
        label: tProd('kpiProjects'),
        value: projectsValue,
        href: '/dashboard/projects' as Route,
        state:
          props.portfolioState === 'error' || props.summaryState === 'error'
            ? ('error' as const)
            : props.portfolioState === 'loading' || props.summaryState === 'loading'
              ? ('loading' as const)
              : projectsValue == null
                ? ('empty' as const)
                : ('ready' as const),
        sparkline: null as number[] | null,
        hint: atRisk > 0 ? tProd('kpiProjectsAtRisk', { count: atRisk }) : undefined,
      },
    ];
  }, [
    cashSparkline,
    locale,
    props.financial,
    props.financialState,
    props.investorState,
    props.investors,
    props.openDeals,
    props.pipelineStateForKpi,
    props.portfolio,
    props.portfolioState,
    props.salesPipelineValue,
    props.summaryCards,
    props.summaryState,
    tProd,
  ]);

  const aiItems = useMemo(() => {
    if (!props.aiInsights) return [];
    const map = (items: AiInsightItem[], kind: AiInsightItem['kind']) =>
      items.slice(0, 4).map((item) => ({
        kind,
        title: props.resolveInsightTitle(item),
        reason: props.resolveInsightDescription(item),
        href: moduleHref(item.link_module, item.link_query),
        severity: item.severity,
      }));
    return [
      ...map(props.aiInsights.priorities, 'priority'),
      ...map(props.aiInsights.risks, 'risk'),
      ...map(props.aiInsights.opportunities, 'opportunity'),
    ].slice(0, 6);
  }, [props]);

  const funnelStages = useMemo(() => {
    if (!props.pipeline?.stages?.length) return [];
    return props.pipeline.stages.map((s) => ({
      label: props.getLeadStatusLabel(s.status),
      value: s.count,
    }));
  }, [props]);

  const investorDonut = useMemo(() => {
    if (!props.investors?.by_status?.length) return [];
    return props.investors.by_status
      .filter((r) => r.count > 0)
      .map((r) => ({ label: r.status, value: r.count }));
  }, [props.investors]);

  const sortedProjects = useMemo(() => {
    if (!props.portfolio) return [];
    const order = { at_risk: 0, attention: 1, on_track: 2 } as const;
    return [...props.portfolio.projects]
      .sort((a, b) => order[a.health_status] - order[b.health_status])
      .slice(0, 5);
  }, [props.portfolio]);

  const deadlineEvents = useMemo(() => {
    return props.deadlines.slice(0, 8).map((d, index) => ({
      id: `${d.entity_type}-${d.entity_id}-${d.due_date}-${index}`,
      label: d.title,
      at: d.due_date,
    }));
  }, [props.deadlines]);

  const financeSnapshot = useMemo(() => {
    if (!props.financial) return null;
    return {
      liquidity: formatCurrencyTotals(props.financial.available_cash, locale),
      inflows: formatCurrencyTotals(props.financial.income_in_period, locale),
      outflows: formatCurrencyTotals(props.financial.expenses_in_period, locale),
      overdue: formatCurrencyTotals(props.financial.overdue_payments, locale),
    };
  }, [props.financial, locale]);

  const healthTone = (health: ProjectHealthRow['health_status']) => {
    if (health === 'at_risk') return 'danger' as const;
    if (health === 'attention') return 'warning' as const;
    return 'success' as const;
  };

  const aiKindTone = (kind: string) => {
    if (kind === 'risk') return 'danger' as const;
    if (kind === 'opportunity') return 'success' as const;
    return 'warning' as const;
  };

  const handleRefresh = () => {
    trackExecutiveUiEvent('executive_dashboard_refresh', { layout: 'production' });
    props.onRefresh();
  };

  const handleRangeChange = (range: { from: string; to: string }) => {
    trackExecutiveUiEvent('executive_dashboard_period_change', {
      layout: 'production',
      periodPreset: 'custom',
    });
    props.onPeriodChange(range.from, range.to);
  };

  const retry = (widgetId: string, fn: () => void) => {
    trackExecutiveUiEvent('executive_widget_retry', { widgetId });
    fn();
  };

  if (!props.canViewExecutive) {
    return (
      <ContentContainer>
        <AppPage data-testid="executive-dashboard-production" data-sprint="D1D" className="ds-exec-prod">
          <PageHeader title={t('title')} subtitle={tProd('permissionDeniedSubtitle')} />
          <WidgetShell
            title={tProd('permissionTitle')}
            state="empty"
            emptyTitle={tProd('permissionTitle')}
            emptyDescription={tProd('permissionBody')}
            span={12}
          />
        </AppPage>
      </ContentContainer>
    );
  }

  const alertsShell = toShellState(props.attentionState, {
    empty: props.attentionState === 'success' && props.alertItems.length === 0,
  });
  const cashShell = toShellState(props.financialState, {
    empty:
      props.financialState === 'success' &&
      cashTrendPoints.length === 0 &&
      !financeSnapshot,
  });
  const aiShell = toShellState(props.aiState, {
    empty: props.aiState === 'success' && aiItems.length === 0,
  });
  const tasksShell = toShellState(props.approvalsState, {
    empty: props.approvalsState === 'success' && props.approvals.length === 0,
  });
  const calendarShell = toShellState(props.deadlineState, {
    empty: props.deadlineState === 'success' && props.deadlines.length === 0,
  });
  const salesShell = toShellState(props.pipelineState, {
    empty: props.pipelineState === 'success' && funnelStages.length === 0,
  });
  const investorShell = toShellState(props.investorState, {
    empty: props.investorState === 'success' && !props.investors,
  });
  const projectsShell = toShellState(props.portfolioState, {
    empty: props.portfolioState === 'success' && sortedProjects.length === 0,
  });

  const visibleActions = props.quickActions.filter((a) => a.show);

  return (
    <ContentContainer>
      <AppPage
        data-testid="executive-dashboard-production"
        data-sprint="D1D"
        className="ds-exec-prod"
      >
        <PageHeader
          className="ds-exec-prod__header"
          title={t('title')}
          subtitle={t('subtitle')}
          actions={
            <div className="ds-exec-prod__header-actions" data-testid="exec-prod-header-actions">
              <DateRangeControl
                value={{ from: props.dateFrom, to: props.dateTo }}
                onChange={handleRangeChange}
                fromLabel={t('filters.dateFrom')}
                toLabel={t('filters.dateTo')}
              />
              <label className="ds-exec-prod__filter ds-type-caption">
                <select
                  value={props.projectId}
                  onChange={(e) => props.onProjectChange(e.target.value)}
                  aria-label={t('filters.project')}
                >
                  <option value="">{t('filters.allProjects')}</option>
                  {props.projectOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <input
                className="ds-exec-prod__filter"
                type="text"
                value={props.assignedTo}
                onChange={(e) => props.onAssignedChange(e.target.value)}
                placeholder={t('filters.assignedPlaceholder')}
                aria-label={t('filters.assignedTo')}
              />
              <input
                className="ds-exec-prod__filter"
                type="text"
                value={props.currency}
                onChange={(e) => props.onCurrencyChange(e.target.value.toUpperCase())}
                placeholder={t('filters.currencyPlaceholder')}
                aria-label={t('filters.currency')}
                maxLength={3}
              />
              <IconButton
                label={tProd('refresh')}
                variant="ghost"
                onClick={handleRefresh}
                data-testid="exec-prod-refresh"
              >
                <IhIcon name="refresh" size="sm" />
              </IconButton>
              <WidgetMenu
                triggerLabel={tProd('customize')}
                items={[
                  {
                    id: 'legacy',
                    label: tProd('openLegacy'),
                    onSelect: () => {
                      trackExecutiveUiEvent('executive_layout_mode', { layout: 'legacy' });
                      props.onOpenLegacy();
                    },
                  },
                ]}
              />
            </div>
          }
        />

        <div className="ds-exec-prod__meta" data-testid="exec-prod-meta" role="status">
          <StatusBadge tone="info">{tProd('liveData')}</StatusBadge>
          <p className="ds-type-caption">
            {t('filters.period')}: {props.dateFrom} → {props.dateTo}
          </p>
          {props.lastRefreshedAt ? (
            <p className="ds-type-caption" data-testid="exec-prod-last-updated">
              {tProd('lastUpdated', {
                at: new Intl.DateTimeFormat(locale === 'tr' ? 'tr-TR' : 'en-GB', {
                  dateStyle: 'medium',
                  timeStyle: 'short',
                }).format(new Date(props.lastRefreshedAt)),
              })}
            </p>
          ) : null}
        </div>

        <ol
          className="ds-exec-prod-mobile-order"
          data-testid="exec-prod-mobile-order"
          aria-label={tProd('mobileOrderLabel')}
          hidden
        >
          {Object.entries(PRODUCTION_MOBILE_ORDER)
            .sort((a, b) => a[1] - b[1])
            .map(([id, order]) => (
              <li key={id} data-widget-id={id} data-mobile-order={order}>
                {id}
              </li>
            ))}
        </ol>

        {/* L1 — Alerts */}
        <div data-testid="exec-prod-section-alerts">
          <DashboardGrid>
            <WidgetColumn
              span={12}
              data-widget-id="exec.alerts"
              data-mobile-order={PRODUCTION_MOBILE_ORDER['exec.alerts']}
            >
              <WidgetShell
                title={tProd('alertsTitle')}
                description={tProd('alertsDesc')}
                icon={<IhIcon name="alert" size="sm" />}
                status={{ label: tProd('statusLive'), tone: 'warning' }}
                span={12}
                state={alertsShell}
                loadingLabel={tCommon('loading')}
                emptyTitle={tProd('alertsEmpty')}
                errorMessage={t('errors.section')}
                errorAction={
                  <button
                    type="button"
                    className="ds-type-caption"
                    onClick={() => retry('exec.alerts', props.onRetryAttention)}
                  >
                    {tCommon('retry')}
                  </button>
                }
              >
                <ul className="ds-exec-prod-list">
                  {props.alertItems.slice(0, 8).map((item) => (
                    <li key={item.id} className="ds-exec-prod-list__row">
                      <StatusBadge
                        tone={
                          item.severity === 'critical'
                            ? 'danger'
                            : item.severity === 'warning'
                              ? 'warning'
                              : 'info'
                        }
                      >
                        {t(`severity.${item.severity}`)}
                      </StatusBadge>
                      <span>{item.title}</span>
                      {item.href ? (
                        <Link
                          href={item.href}
                          className="ds-exec-prod-link"
                          onClick={() =>
                            trackExecutiveUiEvent('executive_widget_drilldown', {
                              widgetId: 'exec.alerts',
                            })
                          }
                        >
                          {tProd('open')}
                        </Link>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </WidgetShell>
            </WidgetColumn>
          </DashboardGrid>
        </div>

        {/* L2 — KPI strip */}
        <div data-testid="exec-prod-section-kpis">
          <DashboardGrid>
            <WidgetColumn span={12}>
              <div className="ds-exec-prod-kpi-strip" data-testid="exec-prod-kpi-strip">
                {kpiDefs.map((kpi) => (
                  <div
                    key={kpi.id}
                    data-widget-id={kpi.id}
                    data-mobile-order={PRODUCTION_MOBILE_ORDER[kpi.id]}
                    className="ds-exec-prod-kpi"
                  >
                    <MetricCard
                      label={kpi.label}
                      value={kpi.value ?? undefined}
                      hint={kpi.hint}
                      size="medium"
                      loading={kpi.state === 'loading'}
                      empty={kpi.state === 'empty'}
                      emptyLabel={tProd('kpiEmpty')}
                      error={kpi.state === 'error'}
                      errorLabel={tProd('kpiError')}
                      href={kpi.href}
                    />
                    {kpi.state === 'ready' && kpi.sparkline && kpi.sparkline.length > 1 ? (
                      <Sparkline
                        values={kpi.sparkline}
                        ariaLabel={kpi.label}
                        locale={locale}
                        className="ds-exec-prod-kpi__spark"
                      />
                    ) : null}
                  </div>
                ))}
              </div>
            </WidgetColumn>
          </DashboardGrid>
        </div>

        {/* Finance + AI */}
        <div data-testid="exec-prod-section-decision-finance">
          <DashboardGrid>
            <WidgetColumn
              span={8}
              data-widget-id="exec.cash_trend"
              data-mobile-order={PRODUCTION_MOBILE_ORDER['exec.cash_trend']}
            >
              <WidgetShell
                title={tProd('cashTrendTitle')}
                description={
                  cashTrendPoints.length > 0
                    ? tProd('cashTrendDesc')
                    : tProd('cashTrendSnapshotOnly')
                }
                icon={<IhIcon name="finance" size="sm" />}
                span={8}
                state={cashShell === 'ready' && cashTrendPoints.length === 0 ? 'ready' : cashShell}
                loadingLabel={tCommon('loading')}
                emptyTitle={tProd('chartEmpty')}
                errorMessage={t('errors.section')}
                errorAction={
                  <button
                    type="button"
                    className="ds-type-caption"
                    onClick={() => retry('exec.cash_trend', () => props.onRetry('exec.cash_trend'))}
                  >
                    {tCommon('retry')}
                  </button>
                }
                action={
                  <Link href={'/dashboard/finance' as Route} className="ds-type-caption">
                    {tProd('drillFinance')}
                  </Link>
                }
              >
                {financeSnapshot ? (
                  <div className="ds-exec-prod-finance-strip" data-testid="exec-prod-finance-strip">
                    <div>
                      <span className="ds-type-caption">{tProd('financeLiquidity')}</span>
                      <strong className="ds-type-body-small">{financeSnapshot.liquidity}</strong>
                    </div>
                    <div>
                      <span className="ds-type-caption">{tProd('financeInflows')}</span>
                      <strong className="ds-type-body-small">{financeSnapshot.inflows}</strong>
                    </div>
                    <div>
                      <span className="ds-type-caption">{tProd('financeOutflows')}</span>
                      <strong className="ds-type-body-small">{financeSnapshot.outflows}</strong>
                    </div>
                    <div>
                      <span className="ds-type-caption">{tProd('financeOverdue')}</span>
                      <strong className="ds-type-body-small">{financeSnapshot.overdue}</strong>
                    </div>
                  </div>
                ) : null}
                {cashTrendPoints.length > 0 ? (
                  <AreaChart
                    data={cashTrendPoints}
                    ariaLabel={tProd('cashTrendTitle')}
                    locale={locale}
                    format="currency"
                    currency={cashTrendCurrency}
                    height={200}
                    emptyTitle={tProd('chartEmpty')}
                    className="ds-chart-container--height-large"
                  />
                ) : (
                  <p className="ds-type-caption" data-testid="exec-prod-cash-historical-gap">
                    {tProd('cashHistoricalGap')}
                  </p>
                )}
              </WidgetShell>
            </WidgetColumn>
            <WidgetColumn
              span={4}
              data-widget-id="exec.ai_decision"
              data-mobile-order={PRODUCTION_MOBILE_ORDER['exec.ai_decision']}
              data-testid="exec-prod-ai-widget"
            >
              <WidgetShell
                title={tProd('aiTitle')}
                description={tProd('aiDesc')}
                icon={<IhIcon name="sparkles" size="sm" />}
                status={{ label: tProd('statusSystemRecs'), tone: 'ai' }}
                span={4}
                className="ds-exec-prod-ai-shell"
                state={aiShell}
                loadingLabel={tCommon('loading')}
                emptyTitle={tProd('aiEmpty')}
                errorMessage={t('errors.section')}
                errorAction={
                  <button
                    type="button"
                    className="ds-type-caption"
                    onClick={() => retry('exec.ai_decision', props.onRetryAi)}
                  >
                    {tCommon('retry')}
                  </button>
                }
                footer={
                  props.aiInsights ? (
                    <p className="ds-type-caption">
                      {t('aiPanel.footer', {
                        level: props.aiInsights.ai_level,
                        time: formatShortDate(props.aiInsights.generated_at, locale),
                      })}
                    </p>
                  ) : null
                }
              >
                <ul className="ds-exec-prod-ai-list" data-testid="exec-prod-ai-list">
                  {aiItems.map((item, index) => (
                    <li
                      key={`${item.kind}-${index}`}
                      className="ds-exec-prod-ai-item"
                      data-ai-kind={item.kind}
                    >
                      <div className="ds-exec-prod-ai-item__head">
                        <StatusBadge tone={aiKindTone(item.kind)}>{item.kind}</StatusBadge>
                        <strong className="ds-type-body-small">{item.title}</strong>
                      </div>
                      <p className="ds-type-caption">
                        <span className="ds-exec-prod-meta">{tProd('aiReason')}: </span>
                        {item.reason}
                      </p>
                      <Link href={item.href} className="ds-exec-prod-link">
                        {tProd('aiAction')}
                        <IhIcon name="arrowRight" size="sm" />
                      </Link>
                    </li>
                  ))}
                </ul>
              </WidgetShell>
            </WidgetColumn>
          </DashboardGrid>
        </div>

        {/* Tasks + Calendar SEPARATE */}
        <div data-testid="exec-prod-section-work">
          <DashboardGrid>
            <WidgetColumn
              span={6}
              data-widget-id="exec.tasks_approvals"
              data-mobile-order={PRODUCTION_MOBILE_ORDER['exec.tasks_approvals']}
              data-testid="exec-prod-tasks-widget"
            >
              <WidgetShell
                title={tProd('tasksTitle')}
                description={tProd('tasksDesc')}
                icon={<IhIcon name="check" size="sm" />}
                span={6}
                state={tasksShell}
                loadingLabel={tCommon('loading')}
                emptyTitle={tProd('tasksEmpty')}
                errorMessage={t('errors.section')}
                errorAction={
                  <button
                    type="button"
                    className="ds-type-caption"
                    onClick={() =>
                      retry('exec.tasks_approvals', () => props.onRetry('exec.tasks_approvals'))
                    }
                  >
                    {tCommon('retry')}
                  </button>
                }
              >
                <ul className="ds-exec-prod-list">
                  {props.approvals.slice(0, 8).map((item) => (
                    <li
                      key={`${item.approval_type}-${item.entity_id}`}
                      className="ds-exec-prod-list__row"
                    >
                      <span>
                        {props.resolveApprovalTitle(item)}
                        {item.age_days != null
                          ? ` · ${t('approvals.ageDays', { days: item.age_days })}`
                          : ''}
                      </span>
                      <Link
                        href={moduleHref(item.link_module, item.link_query)}
                        className="ds-exec-prod-link"
                      >
                        {tProd('open')}
                      </Link>
                    </li>
                  ))}
                </ul>
                <p className="ds-type-caption">{tProd('tasksNote')}</p>
              </WidgetShell>
            </WidgetColumn>
            <WidgetColumn
              span={6}
              data-widget-id="exec.calendar_deadlines"
              data-mobile-order={PRODUCTION_MOBILE_ORDER['exec.calendar_deadlines']}
              data-testid="exec-prod-calendar-widget"
            >
              <WidgetShell
                title={tProd('calendarTitle')}
                description={tProd('calendarDesc')}
                icon={<IhIcon name="calendar" size="sm" />}
                span={6}
                state={calendarShell}
                loadingLabel={tCommon('loading')}
                emptyTitle={tProd('calendarEmpty')}
                errorMessage={t('errors.section')}
                errorAction={
                  <button
                    type="button"
                    className="ds-type-caption"
                    onClick={() =>
                      retry('exec.calendar_deadlines', () =>
                        props.onRetry('exec.calendar_deadlines'),
                      )
                    }
                  >
                    {tCommon('retry')}
                  </button>
                }
              >
                <TimelineChart
                  events={deadlineEvents}
                  ariaLabel={tProd('calendarTitle')}
                  locale={locale}
                  emptyTitle={tProd('calendarEmpty')}
                />
                <p className="ds-type-caption">{tProd('calendarNote')}</p>
              </WidgetShell>
            </WidgetColumn>
          </DashboardGrid>
        </div>

        {/* Sales + Investors */}
        <div data-testid="exec-prod-section-pipeline-projects">
          <DashboardGrid>
            <WidgetColumn
              span={6}
              data-widget-id="exec.sales_funnel"
              data-mobile-order={PRODUCTION_MOBILE_ORDER['exec.sales_funnel']}
              data-testid="exec-prod-sales-widget"
            >
              <WidgetShell
                title={tProd('salesTitle')}
                description={tProd('salesDesc')}
                icon={<IhIcon name="sales" size="sm" />}
                span={6}
                state={salesShell}
                loadingLabel={tCommon('loading')}
                emptyTitle={tProd('chartEmpty')}
                errorMessage={t('errors.section')}
                errorAction={
                  <button
                    type="button"
                    className="ds-type-caption"
                    onClick={() =>
                      retry('exec.sales_funnel', () => props.onRetry('exec.sales_funnel'))
                    }
                  >
                    {tCommon('retry')}
                  </button>
                }
                action={
                  <Link href={'/dashboard/sales' as Route} className="ds-type-caption">
                    {tProd('drillSales')}
                  </Link>
                }
              >
                <FunnelChart
                  stages={funnelStages}
                  ariaLabel={tProd('salesTitle')}
                  locale={locale}
                  emptyTitle={tProd('chartEmpty')}
                />
                {props.pipeline ? (
                  <ul className="ds-exec-prod-list" data-testid="exec-prod-sales-summary">
                    <li className="ds-exec-prod-list__row">
                      <span>{t('sales.qualified')}</span>
                      <strong>{props.pipeline.summary.qualified}</strong>
                    </li>
                    <li className="ds-exec-prod-list__row">
                      <span>{t('sales.won')}</span>
                      <strong>{props.pipeline.summary.won}</strong>
                    </li>
                    <li className="ds-exec-prod-list__row">
                      <span>{t('sales.lost')}</span>
                      <strong>{props.pipeline.summary.lost}</strong>
                    </li>
                  </ul>
                ) : null}
              </WidgetShell>
            </WidgetColumn>
            <WidgetColumn
              span={6}
              data-widget-id="exec.investor_pulse"
              data-mobile-order={PRODUCTION_MOBILE_ORDER['exec.investor_pulse']}
              data-testid="exec-prod-investors-widget"
            >
              <WidgetShell
                title={tProd('investorsTitle')}
                description={tProd('investorsDesc')}
                icon={<IhIcon name="investors" size="sm" />}
                span={6}
                state={investorShell}
                loadingLabel={tCommon('loading')}
                emptyTitle={tProd('investorsEmpty')}
                errorMessage={t('errors.section')}
                errorAction={
                  <button
                    type="button"
                    className="ds-type-caption"
                    onClick={() =>
                      retry('exec.investor_pulse', () => props.onRetry('exec.investor_pulse'))
                    }
                  >
                    {tCommon('retry')}
                  </button>
                }
                action={
                  <Link href={'/dashboard/investors' as Route} className="ds-type-caption">
                    {tProd('drillInvestors')}
                  </Link>
                }
              >
                {props.investors ? (
                  <>
                    <div className="ds-exec-prod-finance-strip ds-exec-prod-finance-strip--3">
                      <div>
                        <span className="ds-type-caption">{tProd('investorsCommitted')}</span>
                        <strong className="ds-type-body-small">
                          {formatCurrencyTotals(props.investors.total_committed, locale)}
                        </strong>
                      </div>
                      <div>
                        <span className="ds-type-caption">{tProd('investorsCapacity')}</span>
                        <strong className="ds-type-body-small">
                          {formatCurrencyTotals(props.investors.total_investment_capacity, locale)}
                        </strong>
                      </div>
                      <div>
                        <span className="ds-type-caption">{tProd('investorsFollowUps')}</span>
                        <strong className="ds-type-body-small">
                          {props.investors.upcoming_follow_ups.length}
                        </strong>
                      </div>
                    </div>
                    {investorDonut.length > 0 ? (
                      <DonutChart
                        data={investorDonut}
                        ariaLabel={tProd('investorsTitle')}
                        locale={locale}
                      />
                    ) : null}
                  </>
                ) : null}
              </WidgetShell>
            </WidgetColumn>
          </DashboardGrid>
        </div>

        {/* Projects + Marketing */}
        <div data-testid="exec-prod-section-projects-marketing">
          <DashboardGrid>
            <WidgetColumn
              span={6}
              data-widget-id="exec.projects_progress"
              data-mobile-order={PRODUCTION_MOBILE_ORDER['exec.projects_progress']}
              data-testid="exec-prod-projects-widget"
            >
              <WidgetShell
                title={tProd('projectsTitle')}
                description={tProd('projectsDesc')}
                icon={<IhIcon name="projects" size="sm" />}
                span={6}
                state={projectsShell}
                loadingLabel={tCommon('loading')}
                emptyTitle={tProd('projectsEmpty')}
                errorMessage={t('errors.section')}
                errorAction={
                  <button
                    type="button"
                    className="ds-type-caption"
                    onClick={() =>
                      retry('exec.projects_progress', () =>
                        props.onRetry('exec.projects_progress'),
                      )
                    }
                  >
                    {tCommon('retry')}
                  </button>
                }
                action={
                  <Link href={'/dashboard/projects' as Route} className="ds-type-caption">
                    {tProd('drillProjects')}
                  </Link>
                }
              >
                <ul className="ds-exec-prod-list">
                  {sortedProjects.map((project) => {
                    const equityRequired = Number(project.equity_required);
                    const equityRaised = Number(project.equity_raised);
                    const hasProgress =
                      Number.isFinite(equityRequired) &&
                      equityRequired > 0 &&
                      Number.isFinite(equityRaised);
                    const progress = hasProgress
                      ? Math.max(0, Math.min(100, (equityRaised / equityRequired) * 100))
                      : null;
                    return (
                      <li key={project.project_id} className="ds-exec-prod-project">
                        <div className="ds-exec-prod-project__head">
                          <Link
                            href={moduleHref('projects', { id: project.project_id })}
                            className="ds-type-body-small"
                          >
                            {project.project_name}
                          </Link>
                          <StatusBadge tone={healthTone(project.health_status)}>
                            {t(`health.${project.health_status}`)}
                          </StatusBadge>
                        </div>
                        <p className="ds-type-caption">
                          {props.getProjectStatusLabel(project.status)}
                          {project.completion_target
                            ? ` · ${formatShortDate(project.completion_target, locale)}`
                            : ''}
                        </p>
                        {progress != null ? (
                          <ProgressChart
                            value={progress}
                            ariaLabel={project.project_name}
                            locale={locale}
                          />
                        ) : (
                          <p className="ds-type-caption">{tProd('projectsProgressUnavailable')}</p>
                        )}
                        {project.funding_gap != null ? (
                          <p className="ds-type-caption">
                            {t('projects.fundingGap')}:{' '}
                            {formatMoney(project.funding_gap, 'USD', locale)}
                          </p>
                        ) : null}
                      </li>
                    );
                  })}
                </ul>
              </WidgetShell>
            </WidgetColumn>
            <WidgetColumn
              span={6}
              data-widget-id="exec.marketing_pulse"
              data-mobile-order={PRODUCTION_MOBILE_ORDER['exec.marketing_pulse']}
              data-testid="exec-prod-marketing-widget"
            >
              <WidgetShell
                title={tProd('marketingTitle')}
                description={tProd('marketingDesc')}
                icon={<IhIcon name="marketing" size="sm" />}
                status={{ label: tProd('marketingUnsupported'), tone: 'info' }}
                span={6}
                state="empty"
                emptyTitle={tProd('marketingEmptyTitle')}
                emptyDescription={tProd('marketingEmptyBody')}
                emptyAction={
                  props.canReadMarketing ? (
                    <Link
                      href={'/workspaces/marketing/dashboard' as Route}
                      className="ds-exec-prod-link"
                      data-testid="exec-prod-marketing-cta"
                    >
                      {tProd('drillMarketing')}
                    </Link>
                  ) : (
                    <span className="ds-type-caption">{tProd('marketingPermission')}</span>
                  )
                }
                action={
                  props.canReadMarketing ? (
                    <Link
                      href={'/workspaces/marketing/dashboard' as Route}
                      className="ds-type-caption"
                    >
                      {tProd('drillMarketing')}
                    </Link>
                  ) : undefined
                }
              />
            </WidgetColumn>
          </DashboardGrid>
        </div>

        {/* Communications + quick actions */}
        <div data-testid="exec-prod-section-comms">
          <DashboardGrid>
            <WidgetColumn
              span={8}
              data-widget-id="exec.communications"
              data-mobile-order={PRODUCTION_MOBILE_ORDER['exec.communications']}
              data-testid="exec-prod-comms-widget"
            >
              <WidgetShell
                title={tProd('commsTitle')}
                description={tProd('commsDesc')}
                icon={<IhIcon name="inbox" size="sm" />}
                span={8}
                state={
                  !props.canViewNotifications
                    ? 'empty'
                    : props.notifications.length === 0
                      ? 'empty'
                      : 'ready'
                }
                emptyTitle={
                  !props.canViewNotifications
                    ? tProd('commsPermissionDenied')
                    : tProd('commsEmpty')
                }
                emptyDescription={
                  !props.canViewNotifications ? tProd('commsPermissionBody') : undefined
                }
                action={
                  props.canViewNotifications ? (
                    <button
                      type="button"
                      className="ds-type-caption"
                      onClick={props.onOpenNotifications}
                    >
                      {t('notifications.openCenter')}
                    </button>
                  ) : undefined
                }
              >
                {props.canViewNotifications ? (
                  <ul className="ds-exec-prod-list">
                    {props.notifications
                      .filter((n) => n.status === 'unread' || !n.read_at)
                      .slice(0, 6)
                      .map((n) => (
                        <li key={n.id} className="ds-exec-prod-list__row">
                          <StatusBadge
                            tone={
                              n.priority === 'critical'
                                ? 'danger'
                                : n.priority === 'high'
                                  ? 'warning'
                                  : 'info'
                            }
                          >
                            {n.priority}
                          </StatusBadge>
                          <span>
                            {props.getNotificationTitle(
                              n.title_key,
                              Object.fromEntries(
                                Object.entries(n.metadata ?? {}).map(([k, v]) => [
                                  k,
                                  v == null ? '' : String(v),
                                ]),
                              ),
                            )}
                          </span>
                          {n.related_label ? (
                            <span className="ds-type-caption ds-exec-prod-meta">
                              {n.related_label}
                            </span>
                          ) : null}
                        </li>
                      ))}
                  </ul>
                ) : null}
              </WidgetShell>
            </WidgetColumn>
            <WidgetColumn
              span={4}
              data-widget-id="exec.quick_actions"
              data-mobile-order={PRODUCTION_MOBILE_ORDER['exec.quick_actions']}
            >
              <RightRail>
                <RightRailCard title={t('commandCenter.quickActions.title')}>
                  {visibleActions.length === 0 ? (
                    <p className="ds-type-caption">{t('commandCenter.quickActions.empty')}</p>
                  ) : (
                    <ul className="ds-exec-prod-list">
                      {visibleActions.map((action) => (
                        <li key={action.href}>
                          <Link href={action.href} className="ds-exec-prod-link">
                            {action.label}
                          </Link>
                        </li>
                      ))}
                    </ul>
                  )}
                </RightRailCard>
              </RightRail>
            </WidgetColumn>
          </DashboardGrid>
        </div>

        <p className="ds-type-caption ds-exec-prod-separation" data-testid="exec-prod-separation">
          {tProd('separationNote')}
        </p>
      </AppPage>
    </ContentContainer>
  );
}
