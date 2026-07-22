'use client';

import { useCallback, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, EmptyState, ErrorState, LoadingState, StatusChip, Tabs } from '@investhome/ui';

import {
  ProjectCostPanel,
  type CostSubTab,
} from '@/app/dashboard/projects/_components/project-cost-panel';
import {
  approveBudgetVersion,
  cloneBudgetVersion,
  createBudgetLine,
  createBudgetVersion,
  fetchBudgetCategories,
  fetchBudgetLines,
  fetchBudgetRevisions,
  fetchBudgetSummary,
  fetchBudgetVersions,
  fetchProjectExecutiveFinance,
  formatMetricCurrency,
  formatMetricPercent,
  formatShortDate,
  rejectBudgetVersion,
  submitBudgetVersion,
  updateProject,
  type BudgetCategory,
  type BudgetLine,
  type BudgetRevision,
  type BudgetSummary,
  type BudgetVersion,
  type FinancialHealthStatus,
  type ProjectExecutiveFinance,
  type ProjectFinancialsResponse,
} from '@/lib/api/projects';

type FinanceSubTab =
  | 'overview'
  | 'cashFlow'
  | 'profitability'
  | 'funding'
  | 'budget'
  | 'advanced';

type AdvancedInnerTab = 'versions' | CostSubTab;

interface ProjectBudgetPanelProps {
  projectId: string;
  financials: ProjectFinancialsResponse;
  locale: string;
  canEditFinancials?: boolean;
}

const HEALTH_TONE: Record<FinancialHealthStatus, 'success' | 'warning' | 'danger' | 'default'> = {
  healthy: 'success',
  watch: 'warning',
  at_risk: 'danger',
  critical: 'danger',
  unavailable: 'default',
};

function MetricTile({
  label,
  value,
  note,
}: {
  label: string;
  value: string;
  note?: string | null;
}) {
  return (
    <article className="project-detail__metric">
      <p className="project-detail__metric-label">{label}</p>
      <p className="project-detail__metric-value">{value}</p>
      {note ? <p className="project-detail__metric-note">{note}</p> : null}
    </article>
  );
}

export function ProjectBudgetPanel({
  projectId,
  financials,
  locale,
  canEditFinancials = false,
}: ProjectBudgetPanelProps) {
  const t = useTranslations('projects');
  const tCommon = useTranslations('common');
  const na = t('notAvailable');

  const [subTab, setSubTab] = useState<FinanceSubTab>('overview');
  const [advancedInner, setAdvancedInner] = useState<AdvancedInnerTab>('versions');
  const [executive, setExecutive] = useState<ProjectExecutiveFinance | null>(null);
  const [summary, setSummary] = useState<BudgetSummary | null>(null);
  const [versions, setVersions] = useState<BudgetVersion[]>([]);
  const [selectedBudgetId, setSelectedBudgetId] = useState<string | null>(null);
  const [lines, setLines] = useState<BudgetLine[]>([]);
  const [revisions, setRevisions] = useState<BudgetRevision[]>([]);
  const [categories, setCategories] = useState<BudgetCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [newBudgetName, setNewBudgetName] = useState('Baseline Budget');
  const [lineForm, setLineForm] = useState({
    category_id: '',
    line_number: '',
    name: '',
    original_budget: '',
  });
  const [simpleForm, setSimpleForm] = useState({
    projected_revenue: '',
    total_development_cost: '',
    equity_required: '',
    equity_raised: '',
    projected_profit: '',
    target_completion_date: '',
    notes: '',
  });

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [executiveData, summaryData, versionData, categoryData] = await Promise.all([
        fetchProjectExecutiveFinance(projectId),
        fetchBudgetSummary(projectId),
        fetchBudgetVersions(projectId),
        fetchBudgetCategories(),
      ]);
      setExecutive(executiveData);
      setSummary(summaryData);
      setVersions(versionData.items);
      setCategories(categoryData);
      setSimpleForm({
        projected_revenue: executiveData.expected_revenue.available
          ? String(executiveData.expected_revenue.value ?? '')
          : '',
        total_development_cost: executiveData.forecast_cost.available
          ? String(executiveData.forecast_cost.value ?? '')
          : '',
        equity_required: executiveData.equity_required.available
          ? String(executiveData.equity_required.value ?? '')
          : '',
        equity_raised: executiveData.equity_raised.available
          ? String(executiveData.equity_raised.value ?? '')
          : '',
        projected_profit: executiveData.expected_profit.available
          ? String(executiveData.expected_profit.value ?? '')
          : '',
        target_completion_date: '',
        notes: '',
      });
      const currentId =
        summaryData.budget_version?.id ?? versionData.items[0]?.id ?? null;
      setSelectedBudgetId(currentId);
      if (currentId) {
        const [lineData, revisionData] = await Promise.all([
          fetchBudgetLines(projectId, currentId),
          fetchBudgetRevisions(projectId, currentId),
        ]);
        setLines(lineData.items);
        setRevisions(revisionData.items);
      } else {
        setLines([]);
        setRevisions([]);
      }
      setLineForm((current) =>
        current.category_id || !categoryData[0]
          ? current
          : { ...current, category_id: categoryData[0].id },
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : t('detailWorkspace.tabLoadError'));
    } finally {
      setLoading(false);
    }
  }, [projectId, t]);

  useEffect(() => {
    void load();
  }, [load]);

  const run = async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('detailWorkspace.actionError'));
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return <LoadingState label={t('detailWorkspace.loadingTab')} />;
  }

  if (error && !executive && !summary) {
    return (
      <ErrorState
        title={t('detailWorkspace.tabLoadError')}
        message={error}
        action={
          <Button type="button" onClick={() => void load()}>
            {tCommon('retry')}
          </Button>
        }
      />
    );
  }

  const permissions = summary?.permissions;
  const selected = versions.find((item) => item.id === selectedBudgetId) ?? null;
  const cashFlow = executive?.cash_flow;

  return (
    <div className="project-budget-panel">
      <Tabs
        activeId={subTab}
        onChange={(id) => setSubTab(id as FinanceSubTab)}
        ariaLabel={t('executiveFinance.subTabsLabel')}
        className="project-budget-panel__tabs"
        tabs={[
          { id: 'overview', label: t('executiveFinance.subTabs.overview') },
          { id: 'cashFlow', label: t('executiveFinance.subTabs.cashFlow') },
          { id: 'profitability', label: t('executiveFinance.subTabs.profitability') },
          { id: 'funding', label: t('executiveFinance.subTabs.funding') },
          { id: 'budget', label: t('executiveFinance.subTabs.budget') },
          { id: 'advanced', label: t('executiveFinance.subTabs.advanced') },
        ]}
      />

      {error ? <p className="project-detail__error">{error}</p> : null}

      {subTab === 'overview' && executive ? (
        <div className="project-detail__stack">
          <section className="project-detail__card">
            <div className="project-detail__toolbar">
              <h3>{t('executiveFinance.health.title')}</h3>
              <StatusChip tone={HEALTH_TONE[executive.health]}>
                {t(`executiveFinance.health.${executive.health}`)}
              </StatusChip>
            </div>
            {executive.health_reasons.length ? (
              <ul className="project-detail__list">
                {executive.health_reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            ) : null}
          </section>

          <div className="project-detail__metrics">
            <MetricTile
              label={t('executiveFinance.cards.expectedRevenue')}
              value={formatMetricCurrency(executive.expected_revenue, locale, na)}
              note={!executive.expected_revenue.available ? executive.expected_revenue.reason : null}
            />
            <MetricTile
              label={t('executiveFinance.cards.receivedRevenue')}
              value={formatMetricCurrency(executive.received_revenue, locale, na)}
              note={!executive.received_revenue.available ? executive.received_revenue.reason : null}
            />
            <MetricTile
              label={t('executiveFinance.cards.forecastCost')}
              value={formatMetricCurrency(executive.forecast_cost, locale, na)}
              note={!executive.forecast_cost.available ? executive.forecast_cost.reason : null}
            />
            <MetricTile
              label={t('executiveFinance.cards.actualCost')}
              value={formatMetricCurrency(executive.actual_cost, locale, na)}
              note={!executive.actual_cost.available ? executive.actual_cost.reason : null}
            />
            <MetricTile
              label={t('executiveFinance.cards.expectedProfit')}
              value={formatMetricCurrency(executive.expected_profit, locale, na)}
              note={!executive.expected_profit.available ? executive.expected_profit.reason : null}
            />
            <MetricTile
              label={t('executiveFinance.cards.profitMargin')}
              value={formatMetricPercent(executive.profit_margin, locale, na)}
              note={!executive.profit_margin.available ? executive.profit_margin.reason : null}
            />
            <MetricTile
              label={t('executiveFinance.cards.currentCash')}
              value={formatMetricCurrency(executive.current_cash, locale, na)}
              note={!executive.current_cash.available ? executive.current_cash.reason : null}
            />
            <MetricTile
              label={t('executiveFinance.cards.fundingGap')}
              value={formatMetricCurrency(executive.funding_gap, locale, na)}
              note={!executive.funding_gap.available ? executive.funding_gap.reason : null}
            />
            <MetricTile
              label={t('executiveFinance.cards.need30')}
              value={formatMetricCurrency(executive.need_30_days, locale, na)}
            />
            <MetricTile
              label={t('executiveFinance.cards.need60')}
              value={formatMetricCurrency(executive.need_60_days, locale, na)}
            />
            <MetricTile
              label={t('executiveFinance.cards.need90')}
              value={formatMetricCurrency(executive.need_90_days, locale, na)}
            />
          </div>

          {executive.alerts.length ? (
            <section className="project-detail__card">
              <h3>{t('executiveFinance.alertsTitle')}</h3>
              <ul className="project-detail__list">
                {executive.alerts.map((alert) => (
                  <li key={alert.id}>
                    <strong>{alert.title}</strong>
                    <span>{alert.message}</span>
                    {alert.recommended_action ? (
                      <span className="project-detail__metric-note">{alert.recommended_action}</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {canEditFinancials ? (
            <section className="project-detail__card">
              <h3>{t('executiveFinance.simpleEntry.title')}</h3>
              <p className="project-detail__note">{t('executiveFinance.simpleEntry.hint')}</p>
              <div className="project-budget-panel__line-form">
                <input
                  placeholder={t('executiveFinance.simpleEntry.revenue')}
                  value={simpleForm.projected_revenue}
                  onChange={(event) =>
                    setSimpleForm((current) => ({
                      ...current,
                      projected_revenue: event.target.value,
                    }))
                  }
                />
                <input
                  placeholder={t('executiveFinance.simpleEntry.cost')}
                  value={simpleForm.total_development_cost}
                  onChange={(event) =>
                    setSimpleForm((current) => ({
                      ...current,
                      total_development_cost: event.target.value,
                    }))
                  }
                />
                <input
                  placeholder={t('executiveFinance.simpleEntry.equityRequired')}
                  value={simpleForm.equity_required}
                  onChange={(event) =>
                    setSimpleForm((current) => ({
                      ...current,
                      equity_required: event.target.value,
                    }))
                  }
                />
                <input
                  placeholder={t('executiveFinance.simpleEntry.equityRaised')}
                  value={simpleForm.equity_raised}
                  onChange={(event) =>
                    setSimpleForm((current) => ({
                      ...current,
                      equity_raised: event.target.value,
                    }))
                  }
                />
                <input
                  placeholder={t('executiveFinance.simpleEntry.profit')}
                  value={simpleForm.projected_profit}
                  onChange={(event) =>
                    setSimpleForm((current) => ({
                      ...current,
                      projected_profit: event.target.value,
                    }))
                  }
                />
                <input
                  type="date"
                  aria-label={t('executiveFinance.simpleEntry.expectedDate')}
                  value={simpleForm.target_completion_date}
                  onChange={(event) =>
                    setSimpleForm((current) => ({
                      ...current,
                      target_completion_date: event.target.value,
                    }))
                  }
                />
                <input
                  placeholder={t('executiveFinance.simpleEntry.notes')}
                  value={simpleForm.notes}
                  onChange={(event) =>
                    setSimpleForm((current) => ({ ...current, notes: event.target.value }))
                  }
                />
                <Button
                  type="button"
                  disabled={busy}
                  onClick={() =>
                    void run(() =>
                      updateProject(projectId, {
                        projected_revenue: simpleForm.projected_revenue
                          ? Number(simpleForm.projected_revenue)
                          : null,
                        total_development_cost: simpleForm.total_development_cost
                          ? Number(simpleForm.total_development_cost)
                          : null,
                        equity_required: simpleForm.equity_required
                          ? Number(simpleForm.equity_required)
                          : null,
                        equity_raised: simpleForm.equity_raised
                          ? Number(simpleForm.equity_raised)
                          : null,
                        projected_profit: simpleForm.projected_profit
                          ? Number(simpleForm.projected_profit)
                          : null,
                        target_completion_date: simpleForm.target_completion_date || null,
                        notes: simpleForm.notes || null,
                      }),
                    )
                  }
                >
                  {t('executiveFinance.simpleEntry.save')}
                </Button>
              </div>
            </section>
          ) : null}

          {executive.warnings.length ? (
            <div className="projects-dashboard__warnings">
              <ul>
                {executive.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}

      {subTab === 'cashFlow' && cashFlow ? (
        <div className="project-detail__stack">
          <div className="project-detail__metrics">
            {[cashFlow.horizon_30, cashFlow.horizon_60, cashFlow.horizon_90].map((horizon) => (
              <article key={horizon.days} className="project-detail__metric">
                <p className="project-detail__metric-label">
                  {t('executiveFinance.cashFlow.horizon', { days: horizon.days })}
                </p>
                <p className="project-detail__metric-value">
                  {formatMetricCurrency(horizon.net_need, locale, na)}
                </p>
                <p className="project-detail__metric-note">
                  {t('executiveFinance.cashFlow.outflows')}:{' '}
                  {formatMetricCurrency(horizon.outflows, locale, na)} ·{' '}
                  {t('executiveFinance.cashFlow.inflows')}:{' '}
                  {formatMetricCurrency(horizon.inflows, locale, na)}
                </p>
              </article>
            ))}
          </div>

          <section className="project-detail__card">
            <h3>{t('executiveFinance.cashFlow.largePayments')}</h3>
            {cashFlow.large_upcoming_payments.length === 0 ? (
              <EmptyState title={t('executiveFinance.cashFlow.emptyPayments')} />
            ) : (
              <ul className="project-detail__list">
                {cashFlow.large_upcoming_payments.map((item) => (
                  <li key={item.id}>
                    <strong>{item.label}</strong>
                    <span>
                      {formatMetricCurrency(
                        { value: item.amount, available: true, reason: null },
                        locale,
                        na,
                      )}{' '}
                      · {item.expected_date ? formatShortDate(item.expected_date, locale) : na}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="project-detail__card">
            <h3>{t('executiveFinance.cashFlow.largeReceipts')}</h3>
            {cashFlow.large_upcoming_receipts.length === 0 ? (
              <EmptyState title={t('executiveFinance.cashFlow.emptyReceipts')} />
            ) : (
              <ul className="project-detail__list">
                {cashFlow.large_upcoming_receipts.map((item) => (
                  <li key={item.id}>
                    <strong>{item.label}</strong>
                    <span>
                      {formatMetricCurrency(
                        { value: item.amount, available: true, reason: null },
                        locale,
                        na,
                      )}{' '}
                      · {item.expected_date ? formatShortDate(item.expected_date, locale) : na}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      ) : null}

      {subTab === 'profitability' && executive ? (
        <div className="project-detail__stack">
          <div className="project-detail__metrics">
            <MetricTile
              label={t('executiveFinance.cards.expectedRevenue')}
              value={formatMetricCurrency(executive.expected_revenue, locale, na)}
            />
            <MetricTile
              label={t('executiveFinance.cards.forecastCost')}
              value={formatMetricCurrency(executive.forecast_cost, locale, na)}
            />
            <MetricTile
              label={t('executiveFinance.cards.actualCost')}
              value={formatMetricCurrency(executive.actual_cost, locale, na)}
            />
            <MetricTile
              label={t('executiveFinance.cards.expectedProfit')}
              value={formatMetricCurrency(executive.expected_profit, locale, na)}
            />
            <MetricTile
              label={t('executiveFinance.cards.profitMargin')}
              value={formatMetricPercent(executive.profit_margin, locale, na)}
            />
          </div>
          <p className="project-detail__note">{t('executiveFinance.profitabilityNote')}</p>
        </div>
      ) : null}

      {subTab === 'funding' ? (
        <div className="project-detail__stack">
          {executive ? (
            <div className="project-detail__metrics">
              <MetricTile
                label={t('executiveFinance.cards.equityRequired')}
                value={formatMetricCurrency(executive.equity_required, locale, na)}
              />
              <MetricTile
                label={t('executiveFinance.cards.equityRaised')}
                value={formatMetricCurrency(executive.equity_raised, locale, na)}
              />
              <MetricTile
                label={t('executiveFinance.cards.fundingGap')}
                value={formatMetricCurrency(executive.funding_gap, locale, na)}
              />
              <MetricTile
                label={t('executiveFinance.cards.committedFunding')}
                value={formatMetricCurrency(executive.committed_funding, locale, na)}
              />
              <MetricTile
                label={t('executiveFinance.cards.fundedAmount')}
                value={formatMetricCurrency(executive.funded_amount, locale, na)}
              />
              <MetricTile
                label={t('executiveFinance.cards.remainingFunding')}
                value={formatMetricCurrency(executive.remaining_funding, locale, na)}
              />
            </div>
          ) : null}
          <section className="project-detail__card">
            <h3>{t('budgetFoundation.funding')}</h3>
            {financials.capital.length === 0 ? (
              <EmptyState title={t('budgetFoundation.empty.funding')} />
            ) : (
              <ul className="project-detail__list">
                {financials.capital.map((item) => (
                  <li key={String(item.id)}>
                    <strong>{String(item.commitment_type ?? '—')}</strong>
                    <span>
                      {formatMetricCurrency(
                        {
                          value: item.committed_amount as string | number | null,
                          available: item.committed_amount != null,
                          reason: null,
                        },
                        locale,
                        na,
                      )}{' '}
                      · {String(item.status ?? '—')}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      ) : null}

      {subTab === 'budget' ? (
        <div className="project-detail__stack">
          <div className="project-detail__metrics">
            {summary
              ? (
                  [
                    'current_budget',
                    'actual_cost',
                    'remaining_budget',
                    'basic_forecast_at_completion',
                  ] as const
                )
                  .map((key) => {
                    const metricValue = summary.totals[key];
                    if (!metricValue) return null;
                    return (
                      <MetricTile
                        key={key}
                        label={t(
                          `budgetFoundation.totals.${key}` as 'budgetFoundation.totals.current_budget',
                        )}
                        value={
                          key.includes('percentage')
                            ? formatMetricPercent(metricValue, locale, na)
                            : formatMetricCurrency(metricValue, locale, na)
                        }
                        note={!metricValue.available ? metricValue.reason : null}
                      />
                    );
                  })
              : null}
          </div>
          <section className="project-detail__card">
            <h3>{t('budgetFoundation.byCategory')}</h3>
            {summary?.categories?.length ? (
              <ul className="project-detail__list">
                {summary.categories.map((category) => (
                  <li key={category.category_id}>
                    <strong>
                      {category.category_code} — {category.category_name}
                    </strong>
                    <span>
                      {formatMetricCurrency(
                        { value: category.current_budget, available: true, reason: null },
                        locale,
                        na,
                      )}{' '}
                      · {category.line_count} {t('budgetFoundation.lines')}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState title={t('budgetFoundation.empty.categories')} />
            )}
          </section>
          <p className="project-detail__note">{t('executiveFinance.budgetSimplifiedNote')}</p>
        </div>
      ) : null}

      {subTab === 'advanced' ? (
        <div className="project-detail__stack">
          <section className="project-detail__card">
            <h3>{t('executiveFinance.advanced.title')}</h3>
            <p className="project-detail__note">{t('executiveFinance.advanced.hint')}</p>
            <Tabs
              activeId={advancedInner}
              onChange={(id) => setAdvancedInner(id as AdvancedInnerTab)}
              ariaLabel={t('executiveFinance.advanced.title')}
              className="project-budget-panel__tabs"
              tabs={[
                { id: 'versions', label: t('budgetFoundation.versions') },
                { id: 'commitments', label: t('budgetFoundation.subTabs.commitments') },
                { id: 'bills', label: t('budgetFoundation.subTabs.bills') },
                { id: 'payments', label: t('budgetFoundation.subTabs.payments') },
                { id: 'retainage', label: t('budgetFoundation.subTabs.retainage') },
              ]}
            />
          </section>

          {advancedInner !== 'versions' ? (
            <ProjectCostPanel projectId={projectId} locale={locale} subTab={advancedInner} />
          ) : null}

          {advancedInner === 'versions' && permissions?.can_manage ? (
            <section className="project-detail__card project-budget-panel__create">
              <h3>{t('budgetFoundation.createVersion')}</h3>
              <div className="project-detail__toolbar">
                <input
                  value={newBudgetName}
                  onChange={(event) => setNewBudgetName(event.target.value)}
                  aria-label={t('budgetFoundation.createVersion')}
                />
                <Button
                  type="button"
                  disabled={busy || !newBudgetName.trim()}
                  onClick={() =>
                    void run(() => createBudgetVersion(projectId, { name: newBudgetName.trim() }))
                  }
                >
                  {t('budgetFoundation.createVersion')}
                </Button>
              </div>
            </section>
          ) : null}

          {advancedInner === 'versions' ? (
          <section className="project-detail__card">
            <h3>{t('budgetFoundation.versions')}</h3>
            {versions.length === 0 ? (
              <EmptyState title={t('budgetFoundation.empty.versions')} />
            ) : (
              <div className="project-detail__table-wrap">
                <table className="project-detail__table">
                  <thead>
                    <tr>
                      <th>{t('budgetFoundation.columns.version')}</th>
                      <th>{t('budgetFoundation.columns.name')}</th>
                      <th>{t('budgetFoundation.columns.status')}</th>
                      <th>{t('budgetFoundation.columns.currentBudget')}</th>
                      <th>{t('budgetFoundation.columns.updated')}</th>
                      <th>{t('budgetFoundation.columns.actions')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {versions.map((version) => (
                      <tr key={version.id}>
                        <td>v{version.version_number}</td>
                        <td>
                          {version.name}
                          {version.is_current ? (
                            <>
                              {' '}
                              <StatusChip tone="success">{t('budgetFoundation.current')}</StatusChip>
                            </>
                          ) : null}
                        </td>
                        <td>{t(`budgetFoundation.status.${version.status}`)}</td>
                        <td>
                          {formatMetricCurrency(
                            {
                              value: version.current_budget_total,
                              available: version.current_budget_total != null,
                              reason: null,
                            },
                            locale,
                            na,
                          )}
                        </td>
                        <td>{formatShortDate(version.updated_at, locale)}</td>
                        <td>
                          <div className="project-detail__row-actions">
                            <Button
                              type="button"
                              variant="secondary"
                              onClick={() => {
                                setSelectedBudgetId(version.id);
                                void fetchBudgetLines(projectId, version.id).then((data) =>
                                  setLines(data.items),
                                );
                                void fetchBudgetRevisions(projectId, version.id).then((data) =>
                                  setRevisions(data.items),
                                );
                              }}
                            >
                              {t('view')}
                            </Button>
                            {permissions?.can_manage && version.status === 'draft' ? (
                              <Button
                                type="button"
                                variant="secondary"
                                disabled={busy}
                                onClick={() =>
                                  void run(() => submitBudgetVersion(projectId, version.id))
                                }
                              >
                                {t('budgetFoundation.actions.submit')}
                              </Button>
                            ) : null}
                            {permissions?.can_approve && version.status === 'in_review' ? (
                              <>
                                <Button
                                  type="button"
                                  disabled={busy}
                                  onClick={() =>
                                    void run(() => approveBudgetVersion(projectId, version.id))
                                  }
                                >
                                  {t('budgetFoundation.actions.approve')}
                                </Button>
                                <Button
                                  type="button"
                                  variant="secondary"
                                  disabled={busy}
                                  onClick={() =>
                                    void run(() => rejectBudgetVersion(projectId, version.id))
                                  }
                                >
                                  {t('budgetFoundation.actions.reject')}
                                </Button>
                              </>
                            ) : null}
                            {permissions?.can_manage ? (
                              <Button
                                type="button"
                                variant="secondary"
                                disabled={busy}
                                onClick={() =>
                                  void run(() => cloneBudgetVersion(projectId, version.id))
                                }
                              >
                                {t('budgetFoundation.actions.clone')}
                              </Button>
                            ) : null}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
          ) : null}

          {advancedInner === 'versions' && selected ? (
            <section className="project-detail__card">
              <h3>
                {t('budgetFoundation.linesFor')} {selected.name}
              </h3>
              {permissions?.can_edit &&
              (selected.status === 'draft' || selected.status === 'rejected') ? (
                <div className="project-budget-panel__line-form">
                  <select
                    value={lineForm.category_id}
                    onChange={(event) =>
                      setLineForm((current) => ({ ...current, category_id: event.target.value }))
                    }
                  >
                    {categories.map((category) => (
                      <option key={category.id} value={category.id}>
                        {category.code} — {category.name}
                      </option>
                    ))}
                  </select>
                  <input
                    placeholder={t('budgetFoundation.lineNumber')}
                    value={lineForm.line_number}
                    onChange={(event) =>
                      setLineForm((current) => ({ ...current, line_number: event.target.value }))
                    }
                  />
                  <input
                    placeholder={t('budgetFoundation.lineName')}
                    value={lineForm.name}
                    onChange={(event) =>
                      setLineForm((current) => ({ ...current, name: event.target.value }))
                    }
                  />
                  <input
                    placeholder={t('budgetFoundation.originalBudget')}
                    value={lineForm.original_budget}
                    onChange={(event) =>
                      setLineForm((current) => ({
                        ...current,
                        original_budget: event.target.value,
                      }))
                    }
                  />
                  <Button
                    type="button"
                    disabled={
                      busy ||
                      !lineForm.category_id ||
                      !lineForm.line_number ||
                      !lineForm.name ||
                      !lineForm.original_budget
                    }
                    onClick={() =>
                      void run(async () => {
                        await createBudgetLine(projectId, selected.id, {
                          category_id: lineForm.category_id,
                          line_number: lineForm.line_number,
                          name: lineForm.name,
                          original_budget: lineForm.original_budget,
                        });
                        setLineForm((current) => ({
                          ...current,
                          line_number: '',
                          name: '',
                          original_budget: '',
                        }));
                      })
                    }
                  >
                    {t('budgetFoundation.actions.addLine')}
                  </Button>
                </div>
              ) : (
                <p className="project-detail__note">{t('budgetFoundation.lockedNote')}</p>
              )}

              {lines.length === 0 ? (
                <EmptyState title={t('budgetFoundation.empty.lines')} />
              ) : (
                <div className="project-detail__table-wrap">
                  <table className="project-detail__table">
                    <thead>
                      <tr>
                        <th>{t('budgetFoundation.columns.line')}</th>
                        <th>{t('budgetFoundation.columns.category')}</th>
                        <th>{t('budgetFoundation.columns.costCode')}</th>
                        <th>{t('budgetFoundation.columns.original')}</th>
                        <th>{t('budgetFoundation.columns.revisions')}</th>
                        <th>{t('budgetFoundation.columns.currentBudget')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {lines.map((line) => (
                        <tr key={line.id}>
                          <td>
                            {line.line_number} — {line.name}
                          </td>
                          <td>{line.category_code ?? '—'}</td>
                          <td>{line.cost_code ?? '—'}</td>
                          <td>
                            {formatMetricCurrency(
                              { value: line.original_budget, available: true, reason: null },
                              locale,
                              na,
                            )}
                          </td>
                          <td>
                            {formatMetricCurrency(
                              { value: line.approved_revisions, available: true, reason: null },
                              locale,
                              na,
                            )}
                          </td>
                          <td>
                            {formatMetricCurrency(
                              { value: line.current_budget, available: true, reason: null },
                              locale,
                              na,
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          ) : null}

          {advancedInner === 'versions' ? (
            <>
              <section className="project-detail__card">
                <h3>{t('budgetFoundation.subTabs.revisions')}</h3>
                <p className="project-detail__note">{t('budgetFoundation.revisionsHint')}</p>
                {revisions.length === 0 ? (
                  <EmptyState title={t('budgetFoundation.empty.revisions')} />
                ) : (
                  <div className="project-detail__table-wrap">
                    <table className="project-detail__table">
                      <thead>
                        <tr>
                          <th>{t('budgetFoundation.columns.version')}</th>
                          <th>{t('budgetFoundation.columns.name')}</th>
                          <th>{t('budgetFoundation.columns.status')}</th>
                          <th>{t('budgetFoundation.columns.revisions')}</th>
                          <th>{t('budgetFoundation.columns.updated')}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {revisions.map((revision) => (
                          <tr key={revision.id}>
                            <td>R{revision.revision_number}</td>
                            <td>{revision.title}</td>
                            <td>{revision.status}</td>
                            <td>
                              {formatMetricCurrency(
                                { value: revision.amount, available: true, reason: null },
                                locale,
                                na,
                              )}
                            </td>
                            <td>{formatShortDate(revision.created_at, locale)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>

              <section className="project-detail__card">
                <h3>{t('detailWorkspace.sections.budgets')}</h3>
                <p className="project-detail__note">{t('budgetFoundation.legacyNote')}</p>
                {financials.budgets.length ? (
                  <ul className="project-detail__list">
                    {financials.budgets.map((budget) => (
                      <li key={String(budget.id)}>
                        <strong>{String(budget.budget_name)}</strong>
                        <span>{String(budget.category ?? '—')}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <EmptyState title={t('detailWorkspace.empty.budgets')} />
                )}
              </section>
            </>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
