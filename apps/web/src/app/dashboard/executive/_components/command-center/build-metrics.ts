import type { Route } from 'next';

import {
  formatCurrencyTotals,
  moduleHref,
  type AttentionItem,
  type ProjectHealthRow,
  type SummaryCard,
} from '@/lib/api/executive';

import type {
  AlertItemView,
  CompanyHealthTone,
  ExecutiveMetric,
  MetricDisplayState,
  MyWorkItem,
  PriorityItemView,
} from './types';

const SEVERITY_RANK: Record<AttentionItem['severity'], number> = {
  critical: 0,
  warning: 1,
  information: 2,
};

export function sortAttentionByUrgency(items: AttentionItem[]): AttentionItem[] {
  return [...items].sort((a, b) => {
    const sev = SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity];
    if (sev !== 0) return sev;
    const aDue = a.due_date ? new Date(a.due_date).getTime() : Number.POSITIVE_INFINITY;
    const bDue = b.due_date ? new Date(b.due_date).getTime() : Number.POSITIVE_INFINITY;
    if (aDue !== bDue) return aDue - bDue;
    const aAge = a.age_days ?? -1;
    const bAge = b.age_days ?? -1;
    return bAge - aAge;
  });
}

export function deriveCompanyHealth(params: {
  attention: AttentionItem[];
  projects: ProjectHealthRow[];
  overduePaymentsPresent: boolean;
}): { tone: CompanyHealthTone; criticalCount: number; warningCount: number; atRiskProjects: number } {
  const criticalCount = params.attention.filter((i) => i.severity === 'critical').length;
  const warningCount = params.attention.filter((i) => i.severity === 'warning').length;
  const atRiskProjects = params.projects.filter((p) => p.health_status === 'at_risk').length;
  let tone: CompanyHealthTone = 'healthy';
  if (criticalCount > 0 || atRiskProjects > 0 || params.overduePaymentsPresent) {
    tone = 'critical';
  } else if (warningCount > 0) {
    tone = 'attention';
  }
  return { tone, criticalCount, warningCount, atRiskProjects };
}

function cardValue(card: SummaryCard | undefined, locale: string): { value: string | null; state: MetricDisplayState } {
  if (!card) return { value: null, state: 'unavailable' };
  if (card.currency_totals && Object.keys(card.currency_totals).length > 0) {
    const formatted = formatCurrencyTotals(card.currency_totals, locale);
    if (formatted === '—') return { value: null, state: 'empty' };
    return { value: formatted, state: 'ready' };
  }
  if (card.value === null || card.value === undefined || card.value === '') {
    return { value: null, state: 'empty' };
  }
  return { value: String(card.value), state: 'ready' };
}

export function buildExecutiveKpis(params: {
  locale: string;
  labels: {
    revenue: string;
    cash: string;
    pipeline: string;
    investors: string;
    openDeals: string;
    projects: string;
    marketingRoi: string;
    tasksDue: string;
  };
  hints: {
    revenue: string;
    pipeline: string;
    openDeals: string;
    marketingRoi: string;
    tasksDue: string;
  };
  summaryCards: SummaryCard[];
  pipelineValue: string | null;
  openDeals: number | null;
  revenue: string | null;
  marketingRoiAvailable: boolean;
  tasksAvailable: boolean;
}): ExecutiveMetric[] {
  const byKey = Object.fromEntries(params.summaryCards.map((c) => [c.key, c]));
  const cash = cardValue(byKey.available_cash, params.locale);
  const investors = cardValue(byKey.active_investors, params.locale);
  const projects = cardValue(byKey.active_projects, params.locale);

  const pipelineState: MetricDisplayState =
    params.pipelineValue === null ? 'unavailable' : params.pipelineValue === '—' || params.pipelineValue === '' ? 'empty' : 'ready';
  const openDealsState: MetricDisplayState =
    params.openDeals === null ? 'unavailable' : 'ready';
  const revenueState: MetricDisplayState =
    params.revenue === null ? 'unavailable' : params.revenue === '—' || params.revenue === '' ? 'empty' : 'ready';

  return [
    {
      key: 'revenue',
      label: params.labels.revenue,
      value: params.revenue,
      state: revenueState,
      href: moduleHref('finance'),
      hint: revenueState !== 'ready' ? params.hints.revenue : undefined,
    },
    {
      key: 'cash',
      label: params.labels.cash,
      value: cash.value,
      state: cash.state,
      href: moduleHref('finance', { tab: 'accounts' }),
    },
    {
      key: 'pipeline',
      label: params.labels.pipeline,
      value: params.pipelineValue,
      state: pipelineState,
      href: '/dashboard/sales' as Route,
      hint: pipelineState !== 'ready' ? params.hints.pipeline : undefined,
    },
    {
      key: 'investors',
      label: params.labels.investors,
      value: investors.value,
      state: investors.state,
      href: moduleHref('investors'),
    },
    {
      key: 'openDeals',
      label: params.labels.openDeals,
      value: params.openDeals === null ? null : String(params.openDeals),
      state: openDealsState,
      href: '/dashboard/sales' as Route,
      hint: openDealsState !== 'ready' ? params.hints.openDeals : undefined,
    },
    {
      key: 'projects',
      label: params.labels.projects,
      value: projects.value,
      state: projects.state,
      href: moduleHref('projects'),
    },
    {
      key: 'marketingRoi',
      label: params.labels.marketingRoi,
      value: null,
      state: params.marketingRoiAvailable ? 'empty' : 'unavailable',
      href: '/workspaces/marketing/reports' as Route,
      hint: params.hints.marketingRoi,
    },
    {
      key: 'tasksDue',
      label: params.labels.tasksDue,
      value: null,
      state: params.tasksAvailable ? 'empty' : 'unavailable',
      hint: params.hints.tasksDue,
    },
  ];
}

export function activityModuleLabel(entityType: string): string {
  const map: Record<string, string> = {
    lead: 'CRM',
    investor: 'Investor',
    project: 'Projects',
    financial_transaction: 'Finance',
    financial_account: 'Finance',
    funding_commitment: 'Finance',
    payment_obligation: 'Finance',
    campaign: 'Marketing',
    user: 'Admin',
    role: 'Admin',
    document: 'Admin',
    notification: 'Admin',
  };
  return map[entityType] ?? entityType;
}

export function toPriorityViews(
  items: AttentionItem[],
  resolveTitle: (item: AttentionItem) => string,
  resolveDescription: (item: AttentionItem) => string,
  resolveDue: (item: AttentionItem) => string | null,
  resolveCategory: (item: AttentionItem) => string,
): PriorityItemView[] {
  return sortAttentionByUrgency(items).slice(0, 12).map((item) => ({
    id: `${item.entity_type}-${item.entity_id}-${item.title_key}`,
    severity: item.severity,
    title: resolveTitle(item),
    description: resolveDescription(item),
    href: moduleHref(item.link_module, item.link_query),
    dueLabel: resolveDue(item),
    category: resolveCategory(item),
  }));
}

export function mergeAlerts(
  attention: AlertItemView[],
  notifications: AlertItemView[],
): AlertItemView[] {
  return [...attention, ...notifications].sort((a, b) => {
    const rank = { critical: 0, warning: 1, information: 2 } as const;
    return rank[a.severity] - rank[b.severity];
  });
}

export type { MyWorkItem };