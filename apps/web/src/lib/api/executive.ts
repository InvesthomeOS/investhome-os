import type { Route } from 'next';

import { apiFetch } from '@/lib/api/client';

export type ExecutivePeriodPreset =
  | 'today'
  | 'last7Days'
  | 'last30Days'
  | 'thisQuarter'
  | 'thisYear'
  | 'custom';

export interface ExecutiveFilterParams {
  date_from?: string;
  date_to?: string;
  project_id?: string;
  assigned_to?: string;
  currency?: string;
}

export interface MetricComparison {
  current: number | string | null;
  previous?: number | string | null;
  change?: number | string | null;
  change_available: boolean;
}

export interface SummaryCard {
  key: string;
  value: number | string | null;
  currency_totals?: Record<string, string> | null;
  comparison?: MetricComparison | null;
  currency_comparison?: {
    totals: Record<string, string>;
    change_available: boolean;
  } | null;
  link_module: string;
  link_query?: Record<string, string> | null;
}

export interface AttentionItem {
  severity: 'information' | 'warning' | 'critical';
  title_key: string;
  description_key: string;
  metadata: Record<string, string | number | null>;
  entity_type: string;
  entity_id: string;
  related_label: string | null;
  due_date: string | null;
  age_days: number | null;
  link_module: string;
  link_query?: Record<string, string> | null;
}

export interface PipelineStage {
  status: string;
  count: number;
  estimated_budget_total: string;
}

export interface ProjectHealthRow {
  project_id: string;
  project_name: string;
  status: string;
  units: number | null;
  completion_target: string | null;
  development_cost: string | null;
  current_value: string | null;
  equity_required: string | null;
  equity_raised: string | null;
  funding_gap: string | null;
  budget_variance: string | null;
  health_status: 'on_track' | 'attention' | 'at_risk';
}

export interface CashFlowPoint {
  period_start: string;
  period_end: string;
  inflows: Record<string, string>;
  outflows: Record<string, string>;
  net: Record<string, string>;
}

export interface DeadlineItem {
  deadline_type: string;
  title: string;
  related_label: string | null;
  due_date: string;
  window: 'overdue' | 'next_7_days' | 'next_30_days' | 'later';
  entity_type: string;
  entity_id: string;
  link_module: string;
  link_query?: Record<string, string> | null;
  metadata?: Record<string, string | number | null>;
}

export interface ActivityItem {
  id: string;
  event_type: string;
  action?: string;
  entity_type: string;
  entity_id: string;
  description_key: string;
  metadata: Record<string, unknown> | null;
  actor: string | null;
  actor_user_id?: string | null;
  source?: string | null;
  entity_label?: string | null;
  link_module?: string | null;
  is_demo: boolean;
  created_at: string;
}

function buildQuery(params: ExecutiveFilterParams = {}): string {
  const search = new URLSearchParams();
  if (params.date_from) search.set('date_from', params.date_from);
  if (params.date_to) search.set('date_to', params.date_to);
  if (params.project_id) search.set('project_id', params.project_id);
  if (params.assigned_to) search.set('assigned_to', params.assigned_to);
  if (params.currency) search.set('currency', params.currency);
  const query = search.toString();
  return query ? `?${query}` : '';
}

export function resolvePeriodDates(
  preset: ExecutivePeriodPreset,
  customFrom?: string,
  customTo?: string,
): { date_from: string; date_to: string } {
  const today = new Date();
  const toIso = (value: Date) => value.toISOString().slice(0, 10);

  if (preset === 'custom' && customFrom && customTo) {
    return { date_from: customFrom, date_to: customTo };
  }

  const end = new Date(today);
  let start = new Date(today);

  if (preset === 'today') {
    return { date_from: toIso(start), date_to: toIso(end) };
  }
  if (preset === 'last7Days') {
    start.setDate(start.getDate() - 6);
    return { date_from: toIso(start), date_to: toIso(end) };
  }
  if (preset === 'thisQuarter') {
    const quarter = Math.floor(start.getMonth() / 3);
    start = new Date(start.getFullYear(), quarter * 3, 1);
    return { date_from: toIso(start), date_to: toIso(end) };
  }
  if (preset === 'thisYear') {
    start = new Date(start.getFullYear(), 0, 1);
    return { date_from: toIso(start), date_to: toIso(end) };
  }
  if (preset === 'last30Days') {
    start.setDate(start.getDate() - 29);
    return { date_from: toIso(start), date_to: toIso(end) };
  }

  start.setDate(start.getDate() - 29);
  return { date_from: toIso(start), date_to: toIso(end) };
}

export async function fetchExecutiveSummary(params: ExecutiveFilterParams) {
  return apiFetch<{ cards: SummaryCard[] }>(`/executive/summary${buildQuery(params)}`);
}

export async function fetchExecutiveAttention(params: ExecutiveFilterParams) {
  return apiFetch<{ items: AttentionItem[] }>(`/executive/attention${buildQuery(params)}`);
}

export async function fetchExecutiveLeadsPipeline(params: ExecutiveFilterParams) {
  return apiFetch<{
    stages: PipelineStage[];
    conversion_rate: string | null;
    won_in_period: number;
    lost_in_period: number;
    total_estimated_budget: string;
  }>(`/executive/leads-pipeline${buildQuery(params)}`);
}

export async function fetchExecutiveInvestorOverview(params: ExecutiveFilterParams) {
  return apiFetch<{
    by_status: { status: string; count: number }[];
    total_investment_capacity: Record<string, string>;
    total_committed: Record<string, string>;
    total_funded: Record<string, string>;
    remaining_committed: Record<string, string>;
    upcoming_follow_ups: AttentionItem[];
    by_investment_model: { model: string; count: number }[];
    by_country: { country: string; count: number }[];
  }>(`/executive/investor-overview${buildQuery(params)}`);
}

export async function fetchExecutiveProjectPortfolio(params: ExecutiveFilterParams) {
  return apiFetch<{
    by_status: { status: string; count: number }[];
    total_units: number;
    units_under_development: number;
    total_development_cost: string;
    current_portfolio_value: string;
    projected_sale_value: string;
    total_equity_required: string;
    total_equity_raised: string;
    total_projected_profit: string;
    projects: ProjectHealthRow[];
  }>(`/executive/project-portfolio${buildQuery(params)}`);
}

export async function fetchExecutiveFinancialOverview(params: ExecutiveFilterParams) {
  return apiFetch<{
    cash_by_account: {
      account_id: string;
      account_name: string;
      currency: string;
      current_balance: string | null;
      available_balance: string | null;
    }[];
    available_cash: Record<string, string>;
    income_in_period: Record<string, string>;
    expenses_in_period: Record<string, string>;
    investor_inflows: Record<string, string>;
    loan_draws: Record<string, string>;
    loan_payments: Record<string, string>;
    upcoming_payments: Record<string, string>;
    overdue_payments: Record<string, string>;
    total_project_budget: Record<string, string>;
    total_paid: Record<string, string>;
    funding_gap_by_project: {
      project_id: string;
      project_name: string;
      currency: string;
      funding_gap: string;
    }[];
    cash_flow_trend: CashFlowPoint[];
  }>(`/executive/financial-overview${buildQuery(params)}`);
}

export async function fetchExecutiveDeadlines(params: ExecutiveFilterParams) {
  return apiFetch<{ items: DeadlineItem[] }>(`/executive/deadlines${buildQuery(params)}`);
}

export async function fetchExecutiveActivity(params: ExecutiveFilterParams) {
  return apiFetch<{ items: ActivityItem[] }>(`/executive/activity${buildQuery(params)}`);
}

export function formatCurrencyTotals(
  totals: Record<string, string> | undefined,
  locale: string,
): string {
  if (!totals) return '—';
  const entries = Object.entries(totals).filter(([, value]) => Number(value) !== 0);
  if (entries.length === 0) return '—';
  const intlLocale = locale === 'tr' ? 'tr-TR' : 'en-US';
  return entries
    .map(([currency, amount]) => {
      const num = Number(amount);
      return new Intl.NumberFormat(intlLocale, {
        style: 'currency',
        currency,
        maximumFractionDigits: 2,
      }).format(num);
    })
    .join(' · ');
}

export function formatMoney(
  amount: string | number | null | undefined,
  currency = 'USD',
  locale = 'tr',
): string {
  if (amount === null || amount === undefined || amount === '') return '—';
  const num = Number(amount);
  if (Number.isNaN(num)) return String(amount);
  const intlLocale = locale === 'tr' ? 'tr-TR' : 'en-US';
  return new Intl.NumberFormat(intlLocale, {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
  }).format(num);
}

export function formatShortDate(value: string | null, locale = 'tr'): string {
  if (!value) return '—';
  const intlLocale = locale === 'tr' ? 'tr-TR' : 'en-GB';
  return new Intl.DateTimeFormat(intlLocale, { dateStyle: 'medium' }).format(new Date(value));
}

export function moduleHref(module: string, query?: Record<string, string> | null): Route {
  const base = `/dashboard/${module}`;
  if (!query || Object.keys(query).length === 0) return base as Route;
  const params = new URLSearchParams(query);
  return `${base}?${params.toString()}` as Route;
}

export const EXECUTIVE_FILTER_STORAGE_KEY = 'investhome-executive-filters';
