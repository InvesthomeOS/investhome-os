'use client';

import {
  DateRangeControl,
  IconButton,
  MetricCard,
  StatusBadge,
  WidgetMenu,
  WidgetShell,
} from '@investhome/ui';
import type { Route } from 'next';
import Link from 'next/link';
import { useLocale, useTranslations } from 'next-intl';
import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  AreaChart,
  BarChart,
  LineChart,
  ProgressChart,
  Sparkline,
  TimelineChart,
} from '@/components/design-system/charts';
import {
  AppPage,
  ContentContainer,
  DashboardGrid,
  PageHeader,
  WidgetColumn,
} from '@/components/design-system/layout';
import { IhIcon } from '@/components/icons/ih-icons';
import type { CurrentUser } from '@/lib/api/auth';
import type {
  ActivityItem,
  AiInsightItem,
  ApprovalItem,
  AttentionItem,
  CashFlowPoint,
  DeadlineItem,
  DelayedProjectRow,
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
import type { FinanceStats } from '@/lib/api/finance';
import type { NotificationItem } from '@/lib/api/notifications';
import { useGlobalSearch } from '@/lib/search/global-search-context';
import type { MetricValue } from '@/workspaces/marketing/schemas/analytics';

import type { AlertItemView } from '../../command-center/types';
import { trackExecutiveUiEvent } from '../executive-ui-analytics';
import { toShellState, type WidgetLoadState } from '../load-state';
import { buildTodaysPriorities } from './build-priorities';
import {
  defaultLayoutForPersona,
  loadAiTriage,
  loadLayoutPrefs,
  saveAiTriage,
  saveLayoutPrefs,
  visibleSections,
  type G8AiTriageState,
  type G8LayoutPrefs,
} from './customization';
import {
  resolveExecPersona,
  type ExecPersona,
  type G8KpiId,
  type G8SectionId,
} from './role-views';

import './executive-g8.css';

export interface MarketingPulse {
  kpis: MetricValue[];
  funnelStages: { key: string; label: string; count: number | null }[];
  bestChannel: string | null;
  state: WidgetLoadState;
  classification: 'LIVE' | 'PARTIAL' | 'BLOCKED' | 'NOT_CONFIGURED' | 'DEMO';
}

export interface G8ExecutiveDashboardProps {
  user: CurrentUser | null;
  periodPreset: ExecutivePeriodPreset;
  dateFrom: string;
  dateTo: string;
  onPeriodChange: (from: string, to: string) => void;
  onPeriodPresetChange: (preset: ExecutivePeriodPreset) => void;
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
    upcoming_payments: Record<string, string>;
    funding_gap_by_project: {
      project_id: string;
      project_name: string;
      currency: string;
      funding_gap: string;
    }[];
    recent_transactions: {
      transaction_id: string;
      transaction_date: string;
      description: string | null;
      amount: string;
      currency: string;
      transaction_type: string;
      status: string;
      link_module: string;
      link_query?: Record<string, string> | null;
    }[];
  } | null;
  financialState: WidgetLoadState;
  financeStats: FinanceStats | null;
  financeStatsState: WidgetLoadState;
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
    total_funded: Record<string, string>;
    upcoming_follow_ups: AttentionItem[];
  } | null;
  investorState: WidgetLoadState;
  portfolio: { projects: ProjectHealthRow[] } | null;
  portfolioState: WidgetLoadState;
  construction: {
    limited_data: boolean;
    delayed_projects: DelayedProjectRow[];
    upcoming_inspections_available: boolean;
    open_rfis_available: boolean;
    drawing_proposals_pending: number;
  } | null;
  constructionState: WidgetLoadState;
  approvals: ApprovalItem[];
  approvalsState: WidgetLoadState;
  deadlines: DeadlineItem[];
  deadlineState: WidgetLoadState;
  activity: ActivityItem[];
  activityState: WidgetLoadState;
  attention: AttentionItem[];
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
  marketing: MarketingPulse;
  canReadMarketing: boolean;
  canViewExecutive: boolean;
  quickActions: { href: Route; label: string; show: boolean }[];
  getLeadStatusLabel: (status: string) => string;
  getProjectStatusLabel: (status: string) => string;
  resolveInsightTitle: (item: AiInsightItem) => string;
  resolveInsightDescription: (item: AiInsightItem) => string;
  resolveApprovalTitle: (item: ApprovalItem) => string;
  resolveAttentionTitle: (item: AttentionItem) => string;
  resolveAttentionReason: (item: AttentionItem) => string;
  resolveActivityTitle: (item: ActivityItem) => string;
  onRetry: (widgetId: string) => void;
  forcePartialDemo?: boolean;
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

function metricFromMarketing(kpis: MetricValue[], key: string): MetricValue | null {
  return kpis.find((k) => k.key === key || k.key.endsWith(key)) ?? null;
}

function formatMetricValue(m: MetricValue | null, locale: string): string | null {
  if (!m || m.state !== 'ready' || m.value == null) return null;
  if (typeof m.value === 'number') {
    if (m.unit === 'currency' || m.unit === 'money') {
      return new Intl.NumberFormat(locale === 'tr' ? 'tr-TR' : 'en-US', {
        style: 'currency',
        currency: 'USD',
        maximumFractionDigits: 0,
      }).format(m.value);
    }
    if (m.unit === 'percent') {
      return new Intl.NumberFormat(locale === 'tr' ? 'tr-TR' : 'en-US', {
        style: 'percent',
        maximumFractionDigits: 1,
      }).format(m.value / 100);
    }
    return new Intl.NumberFormat(locale === 'tr' ? 'tr-TR' : 'en-US').format(m.value);
  }
  return String(m.value);
}

export function G8ExecutiveDashboard(props: G8ExecutiveDashboardProps) {
  const t = useTranslations('executive');
  const tG8 = useTranslations('executive.g8');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { canSearch, openPalette } = useGlobalSearch();

  const systemPersona = resolveExecPersona(props.user);
  const [layout, setLayout] = useState<G8LayoutPrefs>(() => defaultLayoutForPersona(systemPersona));
  const [customizeOpen, setCustomizeOpen] = useState(false);
  const [aiTriage, setAiTriage] = useState<G8AiTriageState>({
    dismissed: [],
    snoozedUntil: {},
    accepted: [],
  });
  const [activityFilter, setActivityFilter] = useState('all');

  useEffect(() => {
    setLayout(loadLayoutPrefs(systemPersona));
    setAiTriage(loadAiTriage());
  }, [systemPersona]);

  const activePersona: ExecPersona = layout.personaOverride ?? systemPersona;

  useEffect(() => {
    trackExecutiveUiEvent('executive_dashboard_view', {
      layout: 'g8',
      periodPreset: props.periodPreset,
    });
  }, [props.periodPreset]);

  const persistLayout = useCallback((next: G8LayoutPrefs) => {
    setLayout(next);
    saveLayoutPrefs(next);
  }, []);

  const persistTriage = useCallback((next: G8AiTriageState) => {
    setAiTriage(next);
    saveAiTriage(next);
  }, []);

  const sections = useMemo(() => visibleSections(layout), [layout]);

  const greetingName = props.user?.full_name?.split(' ')[0] || tG8('greetingFallback');
  const todayLabel = useMemo(() => {
    return new Intl.DateTimeFormat(locale === 'tr' ? 'tr-TR' : 'en-GB', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    }).format(new Date());
  }, [locale]);

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

  const inflowVsOutflow = useMemo(() => {
    if (!props.financial?.cash_flow_trend?.length) return [];
    return props.financial.cash_flow_trend.slice(-6).flatMap((point) => {
      const inflow = primaryCurrencyTotal(point.inflows)?.value ?? 0;
      const outflow = primaryCurrencyTotal(point.outflows)?.value ?? 0;
      const label = formatShortDate(point.period_start, locale);
      return [
        { label: `${label} ↑`, value: inflow },
        { label: `${label} ↓`, value: outflow },
      ];
    });
  }, [props.financial, locale]);

  const priorities = useMemo(() => {
    if (props.forcePartialDemo) return [];
    return buildTodaysPriorities({
      attention: props.attention,
      approvals: props.approvals,
      deadlines: props.deadlines,
      resolveAttentionTitle: props.resolveAttentionTitle,
      resolveAttentionReason: props.resolveAttentionReason,
      resolveApprovalTitle: props.resolveApprovalTitle,
      workspaceLabel: (mod) => tG8(`workspace.${mod}` as 'workspace.finance'),
      max: 8,
    });
  }, [
    props.attention,
    props.approvals,
    props.deadlines,
    props.forcePartialDemo,
    props.resolveApprovalTitle,
    props.resolveAttentionReason,
    props.resolveAttentionTitle,
    tG8,
  ]);

  const atRiskCount =
    props.portfolio?.projects.filter((p) => p.health_status === 'at_risk').length ?? 0;
  const criticalRiskCount = props.attention.filter((a) => a.severity === 'critical').length;

  const kpiCatalog = useMemo(() => {
    const spend = metricFromMarketing(props.marketing.kpis, 'spend');
    const revenue = metricFromMarketing(props.marketing.kpis, 'revenue');
    const cashValue =
      props.financial && Object.keys(props.financial.available_cash || {}).length > 0
        ? formatCurrencyTotals(props.financial.available_cash, locale)
        : props.financeStats
          ? formatCurrencyTotals(props.financeStats.available_cash, locale)
          : null;
    const collections =
      props.financeStats != null
        ? formatCurrencyTotals(props.financeStats.pending_receivables, locale)
        : props.financial
          ? formatCurrencyTotals(props.financial.income_in_period, locale)
          : null;
    const payments =
      props.financeStats != null
        ? formatCurrencyTotals(props.financeStats.upcoming_payments, locale)
        : props.financial
          ? formatCurrencyTotals(props.financial.upcoming_payments, locale)
          : null;
    const committed = props.investors
      ? formatCurrencyTotals(props.investors.total_committed, locale)
      : null;

    const defs: Record<
      G8KpiId,
      {
        label: string;
        value: string | null;
        href: Route;
        state: 'ready' | 'loading' | 'error' | 'empty';
        sparkline: number[] | null;
        hint?: string;
      }
    > = {
      cash: {
        label: tG8('kpi.cash'),
        value: cashValue === '—' ? null : cashValue,
        href: '/dashboard/finance' as Route,
        state:
          props.financialState === 'error' || props.financeStatsState === 'error'
            ? 'error'
            : props.financialState === 'loading'
              ? 'loading'
              : cashValue && cashValue !== '—'
                ? 'ready'
                : 'empty',
        sparkline: cashSparkline,
      },
      collections: {
        label: tG8('kpi.collections'),
        value: collections === '—' ? null : collections,
        href: '/dashboard/finance?view=ar' as Route,
        state:
          props.financeStatsState === 'error' || props.financialState === 'error'
            ? 'error'
            : props.financeStatsState === 'loading' || props.financialState === 'loading'
              ? 'loading'
              : collections && collections !== '—'
                ? 'ready'
                : 'empty',
        sparkline: null,
      },
      payments: {
        label: tG8('kpi.payments'),
        value: payments === '—' ? null : payments,
        href: '/dashboard/finance?view=ap' as Route,
        state:
          props.financeStatsState === 'error' || props.financialState === 'error'
            ? 'error'
            : props.financeStatsState === 'loading' || props.financialState === 'loading'
              ? 'loading'
              : payments && payments !== '—'
                ? 'ready'
                : 'empty',
        sparkline: null,
      },
      pipeline: {
        label: tG8('kpi.pipeline'),
        value: props.salesPipelineValue,
        href: '/dashboard/sales' as Route,
        state:
          props.pipelineStateForKpi === 'error'
            ? 'error'
            : props.pipelineStateForKpi === 'loading'
              ? 'loading'
              : props.salesPipelineValue
                ? 'ready'
                : 'empty',
        sparkline: null,
        hint: props.salesPipelineValue ? undefined : tG8('kpi.pipelineHint'),
      },
      committed: {
        label: tG8('kpi.committed'),
        value: committed === '—' ? null : committed,
        href: '/dashboard/investors' as Route,
        state:
          props.investorState === 'error'
            ? 'error'
            : props.investorState === 'loading'
              ? 'loading'
              : committed && committed !== '—'
                ? 'ready'
                : 'empty',
        sparkline: null,
      },
      projects: {
        label: tG8('kpi.projects'),
        value: props.portfolio ? String(props.portfolio.projects.length) : null,
        href: '/dashboard/projects' as Route,
        state:
          props.portfolioState === 'error'
            ? 'error'
            : props.portfolioState === 'loading'
              ? 'loading'
              : props.portfolio
                ? 'ready'
                : 'empty',
        sparkline: null,
      },
      atRisk: {
        label: tG8('kpi.atRisk'),
        value: props.portfolio ? String(atRiskCount) : null,
        href: '/dashboard/projects' as Route,
        state:
          props.portfolioState === 'error'
            ? 'error'
            : props.portfolioState === 'loading'
              ? 'loading'
              : props.portfolio
                ? 'ready'
                : 'empty',
        sparkline: null,
      },
      marketingSpend: {
        label: tG8('kpi.marketingSpend'),
        value: formatMetricValue(spend, locale),
        href: '/dashboard/marketing' as Route,
        state:
          !props.canReadMarketing
            ? 'empty'
            : props.marketing.state === 'error'
              ? 'error'
              : props.marketing.state === 'loading'
                ? 'loading'
                : formatMetricValue(spend, locale)
                  ? 'ready'
                  : 'empty',
        sparkline: null,
        hint: !props.canReadMarketing ? tG8('marketing.permission') : undefined,
      },
      attributedRevenue: {
        label: tG8('kpi.attributedRevenue'),
        value: formatMetricValue(revenue, locale),
        href: '/dashboard/marketing' as Route,
        state:
          !props.canReadMarketing
            ? 'empty'
            : props.marketing.state === 'error'
              ? 'error'
              : props.marketing.state === 'loading'
                ? 'loading'
                : formatMetricValue(revenue, locale)
                  ? 'ready'
                  : 'empty',
        sparkline: null,
      },
      criticalRisks: {
        label: tG8('kpi.criticalRisks'),
        value: props.attentionState === 'success' ? String(criticalRiskCount) : null,
        href: '#g8-priorities' as Route,
        state:
          props.attentionState === 'error'
            ? 'error'
            : props.attentionState === 'loading'
              ? 'loading'
              : 'ready',
        sparkline: null,
      },
    };
    return defs;
  }, [
    atRiskCount,
    cashSparkline,
    criticalRiskCount,
    locale,
    props.attentionState,
    props.canReadMarketing,
    props.financeStats,
    props.financeStatsState,
    props.financial,
    props.financialState,
    props.investorState,
    props.investors,
    props.marketing.kpis,
    props.marketing.state,
    props.pipelineStateForKpi,
    props.portfolio,
    props.portfolioState,
    props.salesPipelineValue,
    tG8,
  ]);

  const visibleKpis = layout.kpis.map((id) => ({ id, ...kpiCatalog[id] }));

  const funnelStages = useMemo(() => {
    if (!props.pipeline?.stages?.length) return [];
    return props.pipeline.stages.map((s) => ({
      label: props.getLeadStatusLabel(s.status),
      value: s.count,
    }));
  }, [props]);

  const investorBars = useMemo(() => {
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
      .slice(0, 6);
  }, [props.portfolio]);

  const deadlineEvents = useMemo(() => {
    return props.deadlines.slice(0, 10).map((d, index) => ({
      id: `${d.entity_type}-${d.entity_id}-${d.due_date}-${index}`,
      label: d.title,
      at: d.due_date,
    }));
  }, [props.deadlines]);

  const aiItems = useMemo(() => {
    if (!props.aiInsights) return [];
    const now = Date.now();
    const dismissed = new Set(aiTriage.dismissed);
    const map = (items: AiInsightItem[], kind: AiInsightItem['kind']) =>
      items.map((item, idx) => {
        const id = `${kind}-${item.title_key}-${idx}`;
        const snoozeUntil = aiTriage.snoozedUntil[id];
        const snoozed = snoozeUntil ? new Date(snoozeUntil).getTime() > now : false;
        return {
          id,
          kind,
          title: props.resolveInsightTitle(item),
          reason: props.resolveInsightDescription(item),
          href: moduleHref(item.link_module, item.link_query),
          severity: item.severity ?? 'information',
          evidence: Object.entries(item.metadata || {})
            .filter(([, v]) => v != null && v !== '')
            .slice(0, 4)
            .map(([k, v]) => `${k}: ${String(v)}`),
          hidden: dismissed.has(id) || snoozed,
          accepted: aiTriage.accepted.includes(id),
        };
      });
    return [
      ...map(props.aiInsights.priorities, 'priority'),
      ...map(props.aiInsights.risks, 'risk'),
      ...map(props.aiInsights.opportunities, 'opportunity'),
    ]
      .filter((i) => !i.hidden)
      .slice(0, 8);
  }, [aiTriage, props]);

  const filteredActivity = useMemo(() => {
    const rows = props.activity;
    if (activityFilter === 'all') return rows.slice(0, 12);
    return rows.filter((a) => a.entity_type === activityFilter || a.link_module === activityFilter).slice(0, 12);
  }, [activityFilter, props.activity]);

  const marketingBars = useMemo(() => {
    return props.marketing.funnelStages
      .filter((s) => s.count != null && s.count > 0)
      .map((s) => ({ label: s.label, value: s.count as number }));
  }, [props.marketing.funnelStages]);

  const healthTone = (health: ProjectHealthRow['health_status']) => {
    if (health === 'at_risk') return 'danger' as const;
    if (health === 'attention') return 'warning' as const;
    return 'success' as const;
  };

  const classificationBadge = (kind: MarketingPulse['classification'] | 'LIVE' | 'PARTIAL') => {
    const map = {
      LIVE: { tone: 'success' as const, label: tG8('class.live') },
      PARTIAL: { tone: 'warning' as const, label: tG8('class.partial') },
      DEMO: { tone: 'info' as const, label: tG8('class.demo') },
      BLOCKED: { tone: 'danger' as const, label: tG8('class.blocked') },
      NOT_CONFIGURED: { tone: 'info' as const, label: tG8('class.notConfigured') },
    };
    return map[kind];
  };

  const toggleSection = (id: G8SectionId) => {
    const hidden = new Set(layout.hiddenSections);
    if (hidden.has(id)) hidden.delete(id);
    else hidden.add(id);
    persistLayout({ ...layout, hiddenSections: [...hidden] });
  };

  const resetLayout = () => {
    const next = defaultLayoutForPersona(activePersona);
    persistLayout(next);
  };

  const setPersona = (persona: ExecPersona) => {
    persistLayout({
      ...defaultLayoutForPersona(persona),
      personaOverride: persona,
    });
  };

  if (!props.canViewExecutive) {
    return (
      <ContentContainer>
        <AppPage
          data-testid="executive-dashboard-g8"
          data-sprint="G8"
          data-ds-surface="v2"
          className="ds-exec-g8"
        >
          <PageHeader title={t('title')} subtitle={tG8('permissionDeniedSubtitle')} />
          <WidgetShell
            title={tG8('permissionTitle')}
            state="empty"
            emptyTitle={tG8('permissionTitle')}
            emptyDescription={tG8('permissionBody')}
            span={12}
          />
        </AppPage>
      </ContentContainer>
    );
  }

  const show = (id: G8SectionId) => sections.includes(id);
  const densityClass = layout.density === 'compact' ? 'ds-exec-g8--compact' : 'ds-exec-g8--standard';

  return (
    <ContentContainer>
      <AppPage
        data-testid="executive-dashboard-g8"
        data-sprint="G8"
        data-persona={activePersona}
        data-ds-surface="v2"
        className={`ds-exec-g8 ds-exec-prod ${densityClass}`}
      >
        {/* 1 — Executive Header */}
        <header className="ds-exec-g8__header" data-testid="g8-header">
          <PageHeader
            className="ds-exec-prod__header"
            title={tG8('greeting', { name: greetingName })}
            subtitle={`${t('title')} · ${todayLabel}`}
            actions={
              <div className="ds-exec-prod__header-actions" data-testid="g8-header-actions">
                <label className="ds-exec-prod__filter ds-type-caption">
                  <select
                    value={props.periodPreset}
                    onChange={(e) =>
                      props.onPeriodPresetChange(e.target.value as ExecutivePeriodPreset)
                    }
                    aria-label={t('filters.period')}
                    data-testid="g8-period-preset"
                  >
                    <option value="today">{tG8('period.today')}</option>
                    <option value="last7Days">{tG8('period.thisWeek')}</option>
                    <option value="last30Days">{tG8('period.thisMonth')}</option>
                    <option value="thisQuarter">{tG8('period.thisQuarter')}</option>
                    <option value="thisYear">{tG8('period.thisYear')}</option>
                    <option value="custom">{tG8('period.custom')}</option>
                  </select>
                </label>
                <DateRangeControl
                  value={{ from: props.dateFrom, to: props.dateTo }}
                  onChange={(range) => props.onPeriodChange(range.from, range.to)}
                  fromLabel={t('filters.dateFrom')}
                  toLabel={t('filters.dateTo')}
                />
                <label className="ds-exec-prod__filter ds-type-caption">
                  <select
                    value={props.projectId}
                    onChange={(e) => props.onProjectChange(e.target.value)}
                    aria-label={t('filters.project')}
                    data-testid="g8-project-filter"
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
                  value={props.currency}
                  onChange={(e) => props.onCurrencyChange(e.target.value.toUpperCase())}
                  placeholder={t('filters.currencyPlaceholder')}
                  aria-label={t('filters.currency')}
                  maxLength={3}
                  data-testid="g8-currency-filter"
                />
                {canSearch ? (
                  <button
                    type="button"
                    className="ds-exec-g8__search-btn"
                    onClick={openPalette}
                    data-testid="g8-executive-search"
                  >
                    <IhIcon name="search" size="sm" />
                    <span>{tG8('search')}</span>
                  </button>
                ) : null}
                <IconButton
                  label={tG8('notifications')}
                  variant="ghost"
                  onClick={props.onOpenNotifications}
                  data-testid="g8-notifications"
                >
                  <IhIcon name="bell" size="sm" />
                </IconButton>
                <Link
                  href={'/dashboard/ai' as Route}
                  className="ds-exec-g8__search-btn"
                  data-testid="g8-ai-copilot"
                >
                  <IhIcon name="sparkles" size="sm" />
                  <span>{tG8('aiCopilot')}</span>
                </Link>
                <IconButton
                  label={tG8('refresh')}
                  variant="ghost"
                  onClick={() => {
                    trackExecutiveUiEvent('executive_dashboard_refresh', { layout: 'g8' });
                    props.onRefresh();
                  }}
                  data-testid="g8-refresh"
                >
                  <IhIcon name="refresh" size="sm" />
                </IconButton>
                <button
                  type="button"
                  className="ds-exec-g8__search-btn"
                  onClick={() => setCustomizeOpen((v) => !v)}
                  data-testid="g8-customize-toggle"
                >
                  <span>{tG8('customize')}</span>
                </button>
                <WidgetMenu
                  triggerLabel={tG8('openLegacy')}
                  items={[
                    {
                      id: 'legacy',
                      label: tG8('openLegacy'),
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
          <div className="ds-exec-prod__meta" data-testid="g8-meta" role="status">
            <StatusBadge tone="info">{tG8(`persona.${activePersona}`)}</StatusBadge>
            <StatusBadge tone="success">{tG8('class.live')}</StatusBadge>
            <p className="ds-type-caption">
              {t('filters.period')}: {props.dateFrom} → {props.dateTo}
            </p>
            {props.lastRefreshedAt ? (
              <p className="ds-type-caption" data-testid="g8-last-updated">
                {tG8('lastUpdated', {
                  at: new Intl.DateTimeFormat(locale === 'tr' ? 'tr-TR' : 'en-GB', {
                    dateStyle: 'medium',
                    timeStyle: 'short',
                  }).format(new Date(props.lastRefreshedAt)),
                })}
              </p>
            ) : null}
          </div>
        </header>

        {customizeOpen ? (
          <section
            className="ds-exec-g8__customize"
            data-testid="g8-customize-panel"
            aria-label={tG8('customize')}
          >
            <div className="ds-exec-g8__customize-row">
              <label className="ds-type-caption">
                {tG8('roleView')}
                <select
                  value={activePersona}
                  onChange={(e) => setPersona(e.target.value as ExecPersona)}
                  data-testid="g8-persona-select"
                >
                  {(
                    ['ceo', 'cfo', 'sales', 'ir', 'pm', 'marketing', 'ops', 'admin'] as ExecPersona[]
                  ).map((p) => (
                    <option key={p} value={p}>
                      {tG8(`persona.${p}`)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="ds-type-caption">
                {tG8('density')}
                <select
                  value={layout.density}
                  onChange={(e) =>
                    persistLayout({
                      ...layout,
                      density: e.target.value === 'standard' ? 'standard' : 'compact',
                    })
                  }
                >
                  <option value="compact">{tG8('densityCompact')}</option>
                  <option value="standard">{tG8('densityStandard')}</option>
                </select>
              </label>
              <button
                type="button"
                className="ds-exec-g8__ghost-btn"
                onClick={resetLayout}
                data-testid="g8-reset-layout"
              >
                {tG8('resetLayout')}
              </button>
            </div>
            <div className="ds-exec-g8__section-toggles">
              {layout.sections.map((id) => (
                <label key={id} className="ds-type-caption ds-exec-g8__toggle">
                  <input
                    type="checkbox"
                    checked={!layout.hiddenSections.includes(id)}
                    onChange={() => toggleSection(id)}
                  />
                  {tG8(`sections.${id}`)}
                </label>
              ))}
            </div>
            <p className="ds-type-caption ds-exec-prod-meta">{tG8('customizeNote')}</p>
          </section>
        ) : null}

        {/* 2 — Today’s Priorities */}
        {show('priorities') ? (
          <div id="g8-priorities" data-testid="g8-section-priorities">
            <DashboardGrid>
              <WidgetColumn span={12}>
                <WidgetShell
                  title={tG8('sections.priorities')}
                  description={tG8('prioritiesDesc')}
                  icon={<IhIcon name="alert" size="sm" />}
                  status={classificationBadge('LIVE')}
                  span={12}
                  state={toShellState(props.attentionState, {
                    empty:
                      (props.attentionState === 'success' || props.forcePartialDemo) &&
                      priorities.length === 0,
                  })}
                  loadingLabel={tCommon('loading')}
                  emptyTitle={tG8('prioritiesEmpty')}
                  errorMessage={t('errors.section')}
                  errorAction={
                    <button
                      type="button"
                      className="ds-type-caption"
                      onClick={props.onRetryAttention}
                    >
                      {tCommon('retry')}
                    </button>
                  }
                >
                  <ol className="ds-exec-g8__priority-list">
                    {priorities.map((item, index) => (
                      <li key={item.id} className="ds-exec-g8__priority-item" data-testid="g8-priority-row">
                        <span className="ds-exec-g8__rank">{index + 1}</span>
                        <div className="ds-exec-g8__priority-body">
                          <div className="ds-exec-prod-list__row">
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
                            <strong className="ds-type-body-small">{item.title}</strong>
                            <span className="ds-type-caption ds-exec-prod-meta">
                              {item.sourceWorkspace}
                            </span>
                          </div>
                          <p className="ds-type-caption">{item.reason}</p>
                          <div className="ds-exec-prod-list__row">
                            {item.dueDate ? (
                              <span className="ds-type-caption">
                                {formatShortDate(item.dueDate, locale)}
                              </span>
                            ) : null}
                            {item.relatedLabel ? (
                              <span className="ds-type-caption ds-exec-prod-meta">
                                {item.relatedLabel}
                              </span>
                            ) : null}
                            <Link href={item.href} className="ds-exec-prod-link">
                              {tG8('open')}
                            </Link>
                          </div>
                        </div>
                      </li>
                    ))}
                  </ol>
                </WidgetShell>
              </WidgetColumn>
            </DashboardGrid>
          </div>
        ) : null}

        {/* KPI strip */}
        {show('kpi') ? (
          <div data-testid="g8-kpi-strip" className="ds-exec-g8-kpi-strip">
                {visibleKpis.map((kpi) => (
              <div key={kpi.id} className="ds-exec-prod-kpi" data-testid={`g8-kpi-${kpi.id}`}>
                <MetricCard
                  label={kpi.label}
                  value={kpi.value ?? undefined}
                  href={kpi.href}
                  hint={kpi.hint}
                  size="medium"
                  loading={kpi.state === 'loading'}
                  empty={kpi.state === 'empty'}
                  emptyLabel="—"
                  error={kpi.state === 'error'}
                  errorLabel={tG8('kpiError')}
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
        ) : null}

        {/* 3 — Financial Position */}
        {show('finance') ? (
          <div data-testid="g8-section-finance">
            <DashboardGrid>
              <WidgetColumn span={8}>
                <WidgetShell
                  title={tG8('sections.finance')}
                  description={tG8('financeDesc')}
                  icon={<IhIcon name="finance" size="sm" />}
                  status={classificationBadge(
                    props.financial?.cash_flow_trend?.length ? 'LIVE' : 'PARTIAL',
                  )}
                  span={8}
                  state={toShellState(props.financialState, {
                    empty: props.financialState === 'success' && !props.financial,
                  })}
                  loadingLabel={tCommon('loading')}
                  emptyTitle={tG8('financeEmpty')}
                  errorMessage={t('errors.section')}
                  errorAction={
                    <button
                      type="button"
                      className="ds-type-caption"
                      onClick={() => props.onRetry('exec.cash_trend')}
                    >
                      {tCommon('retry')}
                    </button>
                  }
                  action={
                    <Link href={'/dashboard/finance' as Route} className="ds-type-caption">
                      {tG8('drillFinance')}
                    </Link>
                  }
                >
                  {props.financial ? (
                    <>
                      <div className="ds-exec-prod-finance-strip">
                        <div>
                          <span className="ds-type-caption">{tG8('finance.available')}</span>
                          <strong>
                            {formatCurrencyTotals(props.financial.available_cash, locale)}
                          </strong>
                        </div>
                        <div>
                          <span className="ds-type-caption">{tG8('finance.inflows')}</span>
                          <strong>
                            {formatCurrencyTotals(props.financial.income_in_period, locale)}
                          </strong>
                        </div>
                        <div>
                          <span className="ds-type-caption">{tG8('finance.outflows')}</span>
                          <strong>
                            {formatCurrencyTotals(props.financial.expenses_in_period, locale)}
                          </strong>
                        </div>
                        <div>
                          <span className="ds-type-caption">{tG8('finance.overdue')}</span>
                          <strong>
                            {formatCurrencyTotals(props.financial.overdue_payments, locale)}
                          </strong>
                        </div>
                        <div>
                          <span className="ds-type-caption">{tG8('finance.upcoming')}</span>
                          <strong>
                            {formatCurrencyTotals(props.financial.upcoming_payments, locale)}
                          </strong>
                        </div>
                        {props.financeStats ? (
                          <div>
                            <span className="ds-type-caption">{tG8('finance.receivables')}</span>
                            <strong>
                              {formatCurrencyTotals(props.financeStats.pending_receivables, locale)}
                            </strong>
                          </div>
                        ) : null}
                      </div>
                      {cashTrendPoints.length > 1 ? (
                        <LineChart
                          data={cashTrendPoints}
                          ariaLabel={tG8('finance.cashTrend')}
                          locale={locale}
                          format="currency"
                        />
                      ) : cashTrendPoints.length === 1 ? (
                        <AreaChart
                          data={cashTrendPoints}
                          ariaLabel={tG8('finance.cashTrend')}
                          locale={locale}
                          format="currency"
                        />
                      ) : (
                        <p className="ds-type-caption">{tG8('finance.snapshotOnly')}</p>
                      )}
                      {inflowVsOutflow.length > 0 ? (
                        <BarChart
                          data={inflowVsOutflow.slice(0, 8)}
                          ariaLabel={tG8('finance.inVsOut')}
                          locale={locale}
                          horizontal
                        />
                      ) : null}
                      {props.financial.funding_gap_by_project.slice(0, 3).map((gap) => (
                        <p key={gap.project_id} className="ds-type-caption">
                          <Link
                            href={moduleHref('projects', { id: gap.project_id })}
                            className="ds-exec-prod-link"
                          >
                            {gap.project_name}
                          </Link>
                          : {formatMoney(gap.funding_gap, gap.currency, locale)}
                        </p>
                      ))}
                    </>
                  ) : null}
                </WidgetShell>
              </WidgetColumn>
              <WidgetColumn span={4}>
                <WidgetShell
                  title={tG8('finance.recentTx')}
                  description={tG8('finance.recentTxDesc')}
                  span={4}
                  state={toShellState(props.financialState, {
                    empty:
                      props.financialState === 'success' &&
                      (props.financial?.recent_transactions.length ?? 0) === 0,
                  })}
                  emptyTitle={tG8('finance.txEmpty')}
                >
                  <ul className="ds-exec-prod-list">
                    {(props.financial?.recent_transactions ?? []).slice(0, 6).map((tx) => (
                      <li key={tx.transaction_id} className="ds-exec-prod-list__row">
                        <span className="ds-type-caption">
                          {formatShortDate(tx.transaction_date, locale)}
                        </span>
                        <span>{tx.description || tx.transaction_type}</span>
                        <strong className="ds-type-caption">
                          {formatMoney(tx.amount, tx.currency, locale)}
                        </strong>
                      </li>
                    ))}
                  </ul>
                </WidgetShell>
              </WidgetColumn>
            </DashboardGrid>
          </div>
        ) : null}

        {/* 4 — Sales + Investor Pipeline */}
        {show('pipeline') ? (
          <div data-testid="g8-section-pipeline">
            <DashboardGrid>
              <WidgetColumn span={6}>
                <WidgetShell
                  title={tG8('sections.pipeline')}
                  description={tG8('pipelineDesc')}
                  icon={<IhIcon name="sales" size="sm" />}
                  status={classificationBadge('LIVE')}
                  span={6}
                  state={toShellState(props.pipelineState, {
                    empty: props.pipelineState === 'success' && funnelStages.length === 0,
                  })}
                  loadingLabel={tCommon('loading')}
                  emptyTitle={tG8('pipelineEmpty')}
                  errorMessage={t('errors.section')}
                  errorAction={
                    <button
                      type="button"
                      className="ds-type-caption"
                      onClick={() => props.onRetry('exec.sales_funnel')}
                    >
                      {tCommon('retry')}
                    </button>
                  }
                  action={
                    <Link href={'/dashboard/sales' as Route} className="ds-type-caption">
                      {tG8('drillSales')}
                    </Link>
                  }
                >
                  {funnelStages.length > 0 ? (
                    <BarChart
                      data={funnelStages}
                      ariaLabel={tG8('sections.pipeline')}
                      locale={locale}
                      horizontal
                    />
                  ) : null}
                  {props.pipeline?.summary ? (
                    <div className="ds-exec-prod-finance-strip ds-exec-prod-finance-strip--3">
                      <div>
                        <span className="ds-type-caption">{tG8('pipeline.qualified')}</span>
                        <strong>{props.pipeline.summary.qualified}</strong>
                      </div>
                      <div>
                        <span className="ds-type-caption">{tG8('pipeline.meetings')}</span>
                        <strong>{props.pipeline.summary.meetings}</strong>
                      </div>
                      <div>
                        <span className="ds-type-caption">{tG8('pipeline.won')}</span>
                        <strong>{props.pipeline.summary.won}</strong>
                      </div>
                    </div>
                  ) : null}
                </WidgetShell>
              </WidgetColumn>
              <WidgetColumn span={6}>
                <WidgetShell
                  title={tG8('investorsTitle')}
                  description={tG8('investorsDesc')}
                  icon={<IhIcon name="investors" size="sm" />}
                  status={classificationBadge('LIVE')}
                  span={6}
                  state={toShellState(props.investorState, {
                    empty: props.investorState === 'success' && !props.investors,
                  })}
                  loadingLabel={tCommon('loading')}
                  emptyTitle={tG8('investorsEmpty')}
                  errorMessage={t('errors.section')}
                  errorAction={
                    <button
                      type="button"
                      className="ds-type-caption"
                      onClick={() => props.onRetry('exec.investor_pulse')}
                    >
                      {tCommon('retry')}
                    </button>
                  }
                  action={
                    <Link href={'/dashboard/investors' as Route} className="ds-type-caption">
                      {tG8('drillInvestors')}
                    </Link>
                  }
                >
                  {props.investors ? (
                    <>
                      <div className="ds-exec-prod-finance-strip ds-exec-prod-finance-strip--3">
                        <div>
                          <span className="ds-type-caption">{tG8('investors.committed')}</span>
                          <strong>
                            {formatCurrencyTotals(props.investors.total_committed, locale)}
                          </strong>
                        </div>
                        <div>
                          <span className="ds-type-caption">{tG8('investors.funded')}</span>
                          <strong>
                            {formatCurrencyTotals(props.investors.total_funded, locale)}
                          </strong>
                        </div>
                        <div>
                          <span className="ds-type-caption">{tG8('investors.followUps')}</span>
                          <strong>{props.investors.upcoming_follow_ups.length}</strong>
                        </div>
                      </div>
                      {investorBars.length > 0 ? (
                        <BarChart
                          data={investorBars}
                          ariaLabel={tG8('investorsTitle')}
                          locale={locale}
                          horizontal
                        />
                      ) : null}
                      <ul className="ds-exec-prod-list">
                        {props.investors.upcoming_follow_ups.slice(0, 4).map((fu) => (
                          <li
                            key={`${fu.entity_id}-${fu.title_key}`}
                            className="ds-exec-prod-list__row"
                          >
                            <span>{props.resolveAttentionTitle(fu)}</span>
                            <Link
                              href={moduleHref(fu.link_module, fu.link_query)}
                              className="ds-exec-prod-link"
                            >
                              {tG8('open')}
                            </Link>
                          </li>
                        ))}
                      </ul>
                    </>
                  ) : null}
                </WidgetShell>
              </WidgetColumn>
            </DashboardGrid>
          </div>
        ) : null}

        {/* 5 — Projects + Construction */}
        {show('projects') ? (
          <div data-testid="g8-section-projects">
            <DashboardGrid>
              <WidgetColumn span={8}>
                <WidgetShell
                  title={tG8('sections.projects')}
                  description={tG8('projectsDesc')}
                  icon={<IhIcon name="projects" size="sm" />}
                  status={classificationBadge('LIVE')}
                  span={8}
                  state={toShellState(props.portfolioState, {
                    empty: props.portfolioState === 'success' && sortedProjects.length === 0,
                  })}
                  loadingLabel={tCommon('loading')}
                  emptyTitle={tG8('projectsEmpty')}
                  errorMessage={t('errors.section')}
                  errorAction={
                    <button
                      type="button"
                      className="ds-type-caption"
                      onClick={() => props.onRetry('exec.projects_progress')}
                    >
                      {tCommon('retry')}
                    </button>
                  }
                  action={
                    <Link
                      href={'/dashboard/projects' as Route}
                      className="ds-type-caption"
                      data-testid="g8-drill-projects"
                    >
                      {tG8('drillProjects')}
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
                            <p className="ds-type-caption">{tG8('projectsProgressUnavailable')}</p>
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
              <WidgetColumn span={4}>
                <WidgetShell
                  title={tG8('constructionTitle')}
                  description={tG8('constructionDesc')}
                  status={classificationBadge(
                    props.construction?.limited_data ? 'PARTIAL' : 'LIVE',
                  )}
                  span={4}
                  state={toShellState(props.constructionState, {
                    empty:
                      props.constructionState === 'success' &&
                      (props.construction?.delayed_projects.length ?? 0) === 0,
                  })}
                  emptyTitle={tG8('constructionEmpty')}
                >
                  {props.construction?.limited_data ? (
                    <p className="ds-type-caption">{tG8('constructionLimited')}</p>
                  ) : null}
                  <ul className="ds-exec-prod-list">
                    {(props.construction?.delayed_projects ?? []).slice(0, 5).map((p) => (
                      <li key={p.project_id} className="ds-exec-prod-list__row">
                        <Link
                          href={moduleHref(p.link_module, p.link_query)}
                          className="ds-exec-prod-link"
                        >
                          {p.project_name}
                        </Link>
                        <StatusBadge tone={healthTone(p.health_status)}>
                          {t(`health.${p.health_status}`)}
                        </StatusBadge>
                      </li>
                    ))}
                  </ul>
                  {!props.construction?.upcoming_inspections_available ? (
                    <p className="ds-type-caption ds-exec-prod-meta">
                      {tG8('constructionInspectionsUnavailable')}
                    </p>
                  ) : null}
                  {!props.construction?.open_rfis_available ? (
                    <p className="ds-type-caption ds-exec-prod-meta">
                      {tG8('constructionRfisUnavailable')}
                    </p>
                  ) : null}
                </WidgetShell>
              </WidgetColumn>
            </DashboardGrid>
          </div>
        ) : null}

        {/* 6 — Marketing */}
        {show('marketing') ? (
          <div data-testid="g8-section-marketing">
            <DashboardGrid>
              <WidgetColumn span={12}>
                <WidgetShell
                  title={tG8('sections.marketing')}
                  description={tG8('marketingDesc')}
                  icon={<IhIcon name="marketing" size="sm" />}
                  status={classificationBadge(props.marketing.classification)}
                  span={12}
                  state={
                    !props.canReadMarketing
                      ? 'empty'
                      : toShellState(props.marketing.state, {
                          empty:
                            props.marketing.state === 'success' &&
                            props.marketing.kpis.length === 0 &&
                            marketingBars.length === 0,
                        })
                  }
                  emptyTitle={
                    !props.canReadMarketing
                      ? tG8('marketing.permission')
                      : tG8('marketingEmpty')
                  }
                  emptyDescription={
                    !props.canReadMarketing ? undefined : tG8('marketingEmptyBody')
                  }
                  emptyAction={
                    props.canReadMarketing ? (
                      <Link
                        href={'/dashboard/marketing' as Route}
                        className="ds-exec-prod-link"
                        data-testid="g8-marketing-cta"
                      >
                        {tG8('drillMarketing')}
                      </Link>
                    ) : undefined
                  }
                  action={
                    props.canReadMarketing ? (
                      <Link href={'/dashboard/marketing' as Route} className="ds-type-caption">
                        {tG8('drillMarketing')}
                      </Link>
                    ) : undefined
                  }
                >
                  {props.canReadMarketing && props.marketing.kpis.length > 0 ? (
                    <>
                      <div className="ds-exec-prod-finance-strip">
                        {props.marketing.kpis.slice(0, 6).map((kpi) => (
                          <div key={kpi.key}>
                            <span className="ds-type-caption">{kpi.label}</span>
                            <strong>{formatMetricValue(kpi, locale) ?? '—'}</strong>
                          </div>
                        ))}
                      </div>
                      {marketingBars.length > 0 ? (
                        <BarChart
                          data={marketingBars}
                          ariaLabel={tG8('sections.marketing')}
                          locale={locale}
                          horizontal
                        />
                      ) : null}
                      {props.marketing.bestChannel ? (
                        <p className="ds-type-caption">
                          {tG8('marketing.bestChannel')}: {props.marketing.bestChannel}
                        </p>
                      ) : null}
                    </>
                  ) : null}
                </WidgetShell>
              </WidgetColumn>
            </DashboardGrid>
          </div>
        ) : null}

        {/* 7 — AI Risks */}
        {show('ai') ? (
          <div data-testid="g8-section-ai">
            <DashboardGrid>
              <WidgetColumn span={12}>
                <WidgetShell
                  title={tG8('sections.ai')}
                  description={tG8('aiDesc')}
                  icon={<IhIcon name="sparkles" size="sm" />}
                  status={{ label: tG8('aiSystemLabel'), tone: 'info' }}
                  span={12}
                  state={toShellState(props.aiState, {
                    empty: props.aiState === 'success' && aiItems.length === 0,
                  })}
                  loadingLabel={tCommon('loading')}
                  emptyTitle={tG8('aiEmpty')}
                  errorMessage={t('errors.section')}
                  errorAction={
                    <button type="button" className="ds-type-caption" onClick={props.onRetryAi}>
                      {tCommon('retry')}
                    </button>
                  }
                  className="ds-exec-prod-ai-shell"
                >
                  <p className="ds-type-caption ds-exec-prod-meta">{tG8('aiTriageNote')}</p>
                  <ul className="ds-exec-prod-ai-list">
                    {aiItems.map((item) => (
                      <li key={item.id} className="ds-exec-prod-ai-item" data-testid="g8-ai-item">
                        <div className="ds-exec-prod-ai-item__head">
                          <StatusBadge
                            tone={
                              item.severity === 'critical'
                                ? 'danger'
                                : item.severity === 'warning'
                                  ? 'warning'
                                  : 'info'
                            }
                          >
                            {item.kind}
                          </StatusBadge>
                          <strong className="ds-type-body-small">{item.title}</strong>
                          {item.accepted ? (
                            <StatusBadge tone="success">{tG8('aiAccepted')}</StatusBadge>
                          ) : null}
                        </div>
                        <p className="ds-type-caption">{item.reason}</p>
                        {item.evidence.length > 0 ? (
                          <ul className="ds-exec-g8__evidence">
                            {item.evidence.map((e) => (
                              <li key={e} className="ds-type-caption">
                                {e}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="ds-type-caption ds-exec-prod-meta">{tG8('aiNoEvidence')}</p>
                        )}
                        <div className="ds-exec-g8__ai-actions">
                          <Link href={item.href} className="ds-exec-prod-link">
                            {tG8('openSource')}
                          </Link>
                          <button
                            type="button"
                            className="ds-exec-g8__ghost-btn"
                            onClick={() =>
                              persistTriage({
                                ...aiTriage,
                                accepted: [...new Set([...aiTriage.accepted, item.id])],
                              })
                            }
                          >
                            {tG8('aiAccept')}
                          </button>
                          <button
                            type="button"
                            className="ds-exec-g8__ghost-btn"
                            onClick={() =>
                              persistTriage({
                                ...aiTriage,
                                dismissed: [...new Set([...aiTriage.dismissed, item.id])],
                              })
                            }
                          >
                            {tG8('aiDismiss')}
                          </button>
                          <button
                            type="button"
                            className="ds-exec-g8__ghost-btn"
                            onClick={() => {
                              const until = new Date();
                              until.setHours(until.getHours() + 24);
                              persistTriage({
                                ...aiTriage,
                                snoozedUntil: {
                                  ...aiTriage.snoozedUntil,
                                  [item.id]: until.toISOString(),
                                },
                              });
                            }}
                          >
                            {tG8('aiSnooze')}
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                </WidgetShell>
              </WidgetColumn>
            </DashboardGrid>
          </div>
        ) : null}

        {/* 8 — Approvals */}
        {show('approvals') ? (
          <div data-testid="g8-section-approvals">
            <DashboardGrid>
              <WidgetColumn span={12}>
                <WidgetShell
                  title={tG8('sections.approvals')}
                  description={tG8('approvalsDesc')}
                  icon={<IhIcon name="check" size="sm" />}
                  status={classificationBadge('LIVE')}
                  span={12}
                  state={toShellState(props.approvalsState, {
                    empty: props.approvalsState === 'success' && props.approvals.length === 0,
                  })}
                  loadingLabel={tCommon('loading')}
                  emptyTitle={tG8('approvalsEmpty')}
                  errorMessage={t('errors.section')}
                  errorAction={
                    <button
                      type="button"
                      className="ds-type-caption"
                      onClick={() => props.onRetry('exec.tasks_approvals')}
                    >
                      {tCommon('retry')}
                    </button>
                  }
                >
                  <p className="ds-type-caption ds-exec-prod-meta">{tG8('approvalsWorkflowNote')}</p>
                  <ul className="ds-exec-prod-list">
                    {props.approvals.slice(0, 8).map((item) => (
                      <li
                        key={`${item.approval_type}-${item.entity_id}`}
                        className="ds-exec-prod-list__row"
                        data-testid="g8-approval-row"
                      >
                        <div>
                          <strong className="ds-type-body-small">
                            {props.resolveApprovalTitle(item)}
                          </strong>
                          <p className="ds-type-caption">
                            {item.approval_type}
                            {item.age_days != null
                              ? ` · ${t('approvals.ageDays', { days: item.age_days })}`
                              : ''}
                          </p>
                        </div>
                        <Link
                          href={moduleHref(item.link_module, item.link_query)}
                          className="ds-exec-prod-link"
                        >
                          {tG8('reviewApproval')}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </WidgetShell>
              </WidgetColumn>
            </DashboardGrid>
          </div>
        ) : null}

        {/* 9 — Upcoming */}
        {show('upcoming') ? (
          <div data-testid="g8-section-upcoming">
            <DashboardGrid>
              <WidgetColumn span={12}>
                <WidgetShell
                  title={tG8('sections.upcoming')}
                  description={tG8('upcomingDesc')}
                  icon={<IhIcon name="calendar" size="sm" />}
                  status={classificationBadge('PARTIAL')}
                  span={12}
                  state={toShellState(props.deadlineState, {
                    empty: props.deadlineState === 'success' && props.deadlines.length === 0,
                  })}
                  loadingLabel={tCommon('loading')}
                  emptyTitle={tG8('upcomingEmpty')}
                  errorMessage={t('errors.section')}
                  errorAction={
                    <button
                      type="button"
                      className="ds-type-caption"
                      onClick={() => props.onRetry('exec.calendar_deadlines')}
                    >
                      {tCommon('retry')}
                    </button>
                  }
                >
                  <p className="ds-type-caption ds-exec-prod-meta">{tG8('upcomingNote')}</p>
                  {deadlineEvents.length > 0 ? (
                    <TimelineChart
                      events={deadlineEvents}
                      ariaLabel={tG8('sections.upcoming')}
                      locale={locale}
                    />
                  ) : null}
                  <ul className="ds-exec-prod-list">
                    {props.deadlines.slice(0, 8).map((d, i) => (
                      <li
                        key={`${d.entity_id}-${d.due_date}-${i}`}
                        className="ds-exec-prod-list__row"
                        data-testid="g8-deadline-row"
                      >
                        <StatusBadge
                          tone={
                            d.window === 'overdue'
                              ? 'danger'
                              : d.window === 'next_7_days'
                                ? 'warning'
                                : 'info'
                          }
                        >
                          {t(`deadlines.windows.${d.window}`)}
                        </StatusBadge>
                        <span>{d.title}</span>
                        <span className="ds-type-caption">
                          {formatShortDate(d.due_date, locale)}
                        </span>
                        <Link
                          href={moduleHref(d.link_module, d.link_query)}
                          className="ds-exec-prod-link"
                        >
                          {tG8('open')}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </WidgetShell>
              </WidgetColumn>
            </DashboardGrid>
          </div>
        ) : null}

        {/* 10 — Activity */}
        {show('activity') ? (
          <div data-testid="g8-section-activity">
            <DashboardGrid>
              <WidgetColumn span={8}>
                <WidgetShell
                  title={tG8('sections.activity')}
                  description={tG8('activityDesc')}
                  icon={<IhIcon name="activity" size="sm" />}
                  status={classificationBadge('LIVE')}
                  span={8}
                  state={toShellState(props.activityState, {
                    empty: props.activityState === 'success' && filteredActivity.length === 0,
                  })}
                  loadingLabel={tCommon('loading')}
                  emptyTitle={tG8('activityEmpty')}
                  errorMessage={t('errors.section')}
                  action={
                    <select
                      className="ds-exec-prod__filter"
                      value={activityFilter}
                      onChange={(e) => setActivityFilter(e.target.value)}
                      aria-label={tG8('activityFilter')}
                      data-testid="g8-activity-filter"
                    >
                      <option value="all">{tG8('activityAll')}</option>
                      <option value="lead">{tG8('workspace.leads')}</option>
                      <option value="investor">{tG8('workspace.investors')}</option>
                      <option value="project">{tG8('workspace.projects')}</option>
                      <option value="finance">{tG8('workspace.finance')}</option>
                    </select>
                  }
                >
                  <ul className="ds-exec-prod-list">
                    {filteredActivity.map((item) => (
                      <li key={item.id} className="ds-exec-prod-list__row" data-testid="g8-activity-row">
                        <span className="ds-type-caption">
                          {formatShortDate(item.created_at, locale)}
                        </span>
                        <span>{props.resolveActivityTitle(item)}</span>
                        <span className="ds-type-caption ds-exec-prod-meta">
                          {item.entity_type}
                        </span>
                        {item.link_module ? (
                          <Link
                            href={moduleHref(item.link_module, { id: item.entity_id })}
                            className="ds-exec-prod-link"
                          >
                            {tG8('open')}
                          </Link>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </WidgetShell>
              </WidgetColumn>
              <WidgetColumn span={4}>
                {show('quickActions') ? (
                  <div data-testid="g8-section-quick-actions">
                  <WidgetShell
                    title={tG8('sections.quickActions')}
                    description={tG8('quickActionsDesc')}
                    span={4}
                    state="ready"
                  >
                    <ul className="ds-exec-prod-list">
                      {props.quickActions
                        .filter((a) => a.show)
                        .map((action) => (
                          <li key={action.href}>
                            <Link
                              href={action.href}
                              className="ds-exec-prod-link"
                              data-testid="g8-quick-action"
                            >
                              {action.label}
                            </Link>
                          </li>
                        ))}
                    </ul>
                    {props.canViewNotifications ? (
                      <ul className="ds-exec-prod-list" style={{ marginTop: 12 }}>
                        {props.notifications
                          .filter((n) => n.status === 'unread' || !n.read_at)
                          .slice(0, 4)
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
                              <span className="ds-type-caption">
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
                            </li>
                          ))}
                      </ul>
                    ) : null}
                  </WidgetShell>
                  </div>
                ) : null}
              </WidgetColumn>
            </DashboardGrid>
          </div>
        ) : null}

        {!show('activity') && show('quickActions') ? (
          <div data-testid="g8-section-quick-actions">
            <DashboardGrid>
              <WidgetColumn span={12}>
                <WidgetShell title={tG8('sections.quickActions')} span={12} state="ready">
                  <ul className="ds-exec-prod-list">
                    {props.quickActions
                      .filter((a) => a.show)
                      .map((action) => (
                        <li key={action.href}>
                          <Link href={action.href} className="ds-exec-prod-link">
                            {action.label}
                          </Link>
                        </li>
                      ))}
                  </ul>
                </WidgetShell>
              </WidgetColumn>
            </DashboardGrid>
          </div>
        ) : null}

        <p className="ds-type-caption ds-exec-prod-separation" data-testid="g8-separation">
          {tG8('separationNote')}
        </p>
      </AppPage>
    </ContentContainer>
  );
}
