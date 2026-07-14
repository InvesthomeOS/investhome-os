'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { DashboardHeaderActions } from '@/app/dashboard/_components/dashboard-header-actions';
import { fetchProjects } from '@/lib/api/projects';
import {
  EXECUTIVE_FILTER_STORAGE_KEY,
  type ActivityItem,
  type AttentionItem,
  type CashFlowPoint,
  type DeadlineItem,
  type ExecutiveFilterParams,
  type ExecutivePeriodPreset,
  type ProjectHealthRow,
  type SummaryCard,
  fetchExecutiveActivity,
  fetchExecutiveAttention,
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
import { useLeadLabels } from '@/lib/i18n/lead-labels';
import { useProjectLabels } from '@/lib/i18n/project-labels';
import { metadataForI18n } from '@/lib/api/activity';
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

function metadataForExecutiveI18n(metadata: Record<string, string | number | null>) {
  return Object.fromEntries(
    Object.entries(metadata).map(([key, value]) => [key, value ?? '']),
  ) as Record<string, string>;
}

function stripExecutivePrefix(key: string): string {
  return key.startsWith('executive.') ? key.slice('executive.'.length) : key;
}

const DEFAULT_STORED: StoredFilters = {
  preset: 'last30Days',
  customFrom: '',
  customTo: '',
  project_id: '',
  assigned_to: '',
  currency: '',
};

function SectionShell({
  title,
  children,
  state,
  errorMessage,
  onRetry,
  retryLabel,
}: {
  title: string;
  children: React.ReactNode;
  state: LoadState;
  errorMessage?: string | null;
  onRetry?: () => void;
  retryLabel: string;
}) {
  return (
    <section className="dashboard__panel leads__panel executive__section">
      <h2 className="leads-form__section-title">{title}</h2>
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
  const href = moduleHref(card.link_module, card.link_query);
  const moneyKeys = new Set(['total_investment_capacity', 'total_portfolio_value']);
  let displayValue =
    card.currency_totals && Object.keys(card.currency_totals).length > 0
      ? formatCurrencyTotals(card.currency_totals, locale)
      : card.value ?? '—';

  if (moneyKeys.has(card.key) && card.value !== null && card.value !== undefined) {
    displayValue = formatMoney(card.value, 'USD', locale);
  }

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

function PipelineChart({
  stages,
  getStatusLabel,
  locale,
}: {
  stages: { status: string; count: number; estimated_budget_total: string }[];
  getStatusLabel: (status: string) => string;
  locale: string;
}) {
  const max = Math.max(...stages.map((stage) => stage.count), 1);
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
            {formatMoney(stage.estimated_budget_total, 'USD', locale)}
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
        const netUsd = Number(point.net.USD ?? Object.values(point.net)[0] ?? 0);
        const inflowUsd = Number(point.inflows.USD ?? Object.values(point.inflows)[0] ?? 0);
        const outflowUsd = Number(point.outflows.USD ?? Object.values(point.outflows)[0] ?? 0);
        return (
          <div key={`${point.period_start}-${point.period_end}`} className="executive__cashflow-row">
            <span className="executive__cashflow-label">
              {formatShortDate(point.period_start, locale)}
            </span>
            <div className="executive__cashflow-bars">
              <div
                className="executive__cashflow-in"
                style={{ width: `${(inflowUsd / maxNet) * 50}%` }}
                title={`${inflowsLabel}: ${formatMoney(inflowUsd, 'USD', locale)}`}
              />
              <div
                className="executive__cashflow-out"
                style={{ width: `${(outflowUsd / maxNet) * 50}%` }}
                title={`${outflowsLabel}: ${formatMoney(outflowUsd, 'USD', locale)}`}
              />
            </div>
            <span className="executive__cashflow-net">{formatMoney(netUsd, 'USD', locale)}</span>
          </div>
        );
      })}
    </div>
  );
}

export function ExecutiveWorkspace() {
  const t = useTranslations('executive');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { getStatusLabel: getLeadStatusLabel } = useLeadLabels();
  const { getStatusLabel: getProjectStatusLabel } = useProjectLabels();
  const { getDescription: getActivityDescription } = useActivityLabels();

  const [stored, setStored] = useState<StoredFilters>(DEFAULT_STORED);
  const [projectOptions, setProjectOptions] = useState<{ id: string; label: string }[]>([]);

  const [summaryCards, setSummaryCards] = useState<SummaryCard[]>([]);
  const [attentionItems, setAttentionItems] = useState<AttentionItem[]>([]);
  const [pipeline, setPipeline] = useState<Awaited<ReturnType<typeof fetchExecutiveLeadsPipeline>> | null>(null);
  const [investors, setInvestors] = useState<Awaited<ReturnType<typeof fetchExecutiveInvestorOverview>> | null>(null);
  const [portfolio, setPortfolio] = useState<Awaited<ReturnType<typeof fetchExecutiveProjectPortfolio>> | null>(null);
  const [financial, setFinancial] = useState<Awaited<ReturnType<typeof fetchExecutiveFinancialOverview>> | null>(null);
  const [deadlines, setDeadlines] = useState<DeadlineItem[]>([]);
  const [activity, setActivity] = useState<ActivityItem[]>([]);

  const [summaryState, setSummaryState] = useState<LoadState>('loading');
  const [attentionState, setAttentionState] = useState<LoadState>('loading');
  const [pipelineState, setPipelineState] = useState<LoadState>('loading');
  const [investorState, setInvestorState] = useState<LoadState>('loading');
  const [portfolioState, setPortfolioState] = useState<LoadState>('loading');
  const [financialState, setFinancialState] = useState<LoadState>('loading');
  const [deadlineState, setDeadlineState] = useState<LoadState>('loading');
  const [activityState, setActivityState] = useState<LoadState>('loading');

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

  const loadAttention = useCallback(async () => {
    setAttentionState('loading');
    try {
      const response = await fetchExecutiveAttention(filterParams);
      setAttentionItems(response.items);
      setAttentionState('success');
    } catch {
      setAttentionState('error');
    }
  }, [filterParams]);

  const loadPipeline = useCallback(async () => {
    setPipelineState('loading');
    try {
      setPipeline(await fetchExecutiveLeadsPipeline(filterParams));
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

  useEffect(() => {
    void loadSummary();
    void loadAttention();
    void loadPipeline();
    void loadInvestors();
    void loadPortfolio();
    void loadFinancial();
    void loadDeadlines();
    void loadActivity();
  }, [
    loadActivity,
    loadAttention,
    loadDeadlines,
    loadFinancial,
    loadInvestors,
    loadPipeline,
    loadPortfolio,
    loadSummary,
  ]);

  const cardLabel = (key: string) => t(`cards.${key}` as 'cards.total_leads');

  const severityLabel = (severity: AttentionItem['severity']) => t(`severity.${severity}`);

  const healthLabel = (status: ProjectHealthRow['health_status']) => t(`health.${status}`);

  const deadlineWindowLabel = (window: DeadlineItem['window']) => t(`deadlines.windows.${window}`);

  const quickActions: { href: Route; label: string }[] = [
    { href: '/dashboard/leads' as Route, label: t('quickActions.addLead') },
    { href: '/dashboard/investors' as Route, label: t('quickActions.addInvestor') },
    { href: '/dashboard/projects' as Route, label: t('quickActions.addProject') },
    { href: '/dashboard/finance' as Route, label: t('quickActions.addTransaction') },
    { href: '/dashboard/finance' as Route, label: t('quickActions.addPaymentObligation') },
    { href: '/dashboard/finance' as Route, label: t('quickActions.addFundingCommitment') },
  ];

  return (
    <main className="dashboard leads investors finance executive">
      <header className="dashboard__header leads__header">
        <div>
          <p className="dashboard__eyebrow">{t('eyebrow')}</p>
          <h1 className="dashboard__title">{t('title')}</h1>
          <p className="leads__subtitle">{t('subtitle')}</p>
        </div>
        <DashboardHeaderActions />
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
            placeholder="USD"
          />
        </label>
      </section>

      <section className="finance__stats executive__summary-grid">
        {summaryState === 'loading' &&
          Array.from({ length: 8 }).map((_, index) => (
            <div key={index} className="investors__stat-card executive__skeleton" aria-hidden="true" />
          ))}
        {summaryState === 'error' && <p className="leads__state leads__state--error">{t('errors.summary')}</p>}
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
      </section>

      <div className="executive__layout">
        <SectionShell
          title={t('attention.title')}
          state={attentionState}
          errorMessage={t('errors.section')}
          onRetry={() => void loadAttention()}
          retryLabel={tCommon('retry')}
        >
          {attentionItems.length === 0 ? (
            <p className="leads__state">{t('attention.empty')}</p>
          ) : (
            <ul className="executive__attention-list">
              {attentionItems.map((item) => (
                <li key={`${item.entity_type}-${item.entity_id}-${item.title_key}`}>
                  <Link
                    href={moduleHref(item.link_module, item.link_query)}
                    className={`executive__attention-item executive__attention-item--${item.severity}`}
                  >
                    <span className="executive__attention-severity">{severityLabel(item.severity)}</span>
                    <strong>{t(stripExecutivePrefix(item.title_key) as 'attention.overdue_payment.title', metadataForExecutiveI18n(item.metadata))}</strong>
                    <p>{t(stripExecutivePrefix(item.description_key) as 'attention.overdue_payment.description', metadataForExecutiveI18n(item.metadata))}</p>
                    <span className="executive__attention-meta">
                      {item.related_label ?? tCommon('noValue')}
                      {item.due_date ? ` · ${formatShortDate(item.due_date, locale)}` : ''}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </SectionShell>

        <section className="dashboard__panel leads__panel executive__quick-actions">
          <h2 className="leads-form__section-title">{t('quickActions.title')}</h2>
          <ul className="executive__actions-list">
            {quickActions.map((action) => (
              <li key={action.label}>
                <Link href={action.href} className="leads__button leads__button--secondary">
                  {action.label}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <div className="executive__grid-two">
        <SectionShell
          title={t('pipeline.title')}
          state={pipelineState}
          errorMessage={t('errors.section')}
          onRetry={() => void loadPipeline()}
          retryLabel={tCommon('retry')}
        >
          {pipeline && (
            <>
              <PipelineChart
                stages={pipeline.stages}
                getStatusLabel={getLeadStatusLabel}
                locale={locale}
              />
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
              <p>
                {t('investors.capacity')}:{' '}
                {formatCurrencyTotals(investors.total_investment_capacity, locale)}
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
            </div>
          )}
        </SectionShell>
      </div>

      <SectionShell
        title={t('portfolio.title')}
        state={portfolioState}
        errorMessage={t('errors.section')}
        onRetry={() => void loadPortfolio()}
        retryLabel={tCommon('retry')}
      >
        {portfolio && (
          <>
            <div className="executive__metric-list">
              <span>
                {t('portfolio.totalUnits')}: {portfolio.total_units}
              </span>
              <span>
                {t('portfolio.portfolioValue')}: {formatMoney(portfolio.current_portfolio_value, 'USD', locale)}
              </span>
              <span>
                {t('portfolio.equityRaised')}: {formatMoney(portfolio.total_equity_raised, 'USD', locale)}
              </span>
            </div>
            <div className="leads__table-wrap">
              <table className="leads__table">
                <thead>
                  <tr>
                    <th>{t('portfolio.table.project')}</th>
                    <th>{t('portfolio.table.status')}</th>
                    <th>{t('portfolio.table.completion')}</th>
                    <th>{t('portfolio.table.fundingGap')}</th>
                    <th>{t('portfolio.table.budgetVariance')}</th>
                    <th>{t('portfolio.table.health')}</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolio.projects.map((row) => (
                    <tr key={row.project_id} className="leads__row">
                      <td>
                        <Link href={moduleHref('projects')}>{row.project_name}</Link>
                      </td>
                      <td>{getProjectStatusLabel(row.status)}</td>
                      <td>{formatShortDate(row.completion_target, locale)}</td>
                      <td>{formatMoney(row.funding_gap, 'USD', locale)}</td>
                      <td>{formatMoney(row.budget_variance, 'USD', locale)}</td>
                      <td>
                        <span className={`executive__health executive__health--${row.health_status}`}>
                          {healthLabel(row.health_status)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
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
                {t('financial.income')}: {formatCurrencyTotals(financial.income_in_period, locale)}
              </p>
              <p>
                {t('financial.expenses')}: {formatCurrencyTotals(financial.expenses_in_period, locale)}
              </p>
              <p>
                {t('financial.overdue')}: {formatCurrencyTotals(financial.overdue_payments, locale)}
              </p>
            </div>
            <CashFlowChart
              points={financial.cash_flow_trend}
              locale={locale}
              inflowsLabel={t('financial.inflows')}
              outflowsLabel={t('financial.outflows')}
            />
          </>
        )}
      </SectionShell>

      <div className="executive__grid-two">
        <SectionShell
          title={t('deadlines.title')}
          state={deadlineState}
          errorMessage={t('errors.section')}
          onRetry={() => void loadDeadlines()}
          retryLabel={tCommon('retry')}
        >
          {deadlines.length === 0 ? (
            <p className="leads__state">{t('deadlines.empty')}</p>
          ) : (
            <ul className="executive__deadline-list">
              {deadlines.slice(0, 20).map((item) => (
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
            <ul className="executive__activity-list">
              {activity.map((item) => {
                const href = item.link_module ? moduleHref(item.link_module) : null;
                const summary = getActivityDescription(
                  item.description_key,
                  metadataForI18n(item.metadata),
                );
                const content = (
                  <>
                    <span>{formatShortDate(item.created_at, locale)}</span>
                    <p>{summary}</p>
                    {item.actor && <span className="activity-timeline__actor">{item.actor}</span>}
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
          )}
        </SectionShell>
      </div>
    </main>
  );
}
