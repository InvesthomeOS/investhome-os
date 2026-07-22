'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../empty-state';
import { InvestmentErrorState } from '../investment-error-state';
import { LoadingSkeletonGrid } from '../loading-skeleton';
import { AllocationSection } from './allocation-section';
import { BenchmarksSection } from './benchmarks-section';
import { CashFlowSection } from './cash-flow-section';
import { ConcentrationAlerts } from './concentration-alerts';
import { GeographicAllocationSection } from './geographic-allocation';
import { InsightsPanel } from './insights-panel';
import { InvestmentComparison } from './investment-comparison';
import { PerformanceCharts } from './performance-charts';
import { PerformanceTable } from './performance-table';
import { PortfolioControls, usePortfolioControls } from './portfolio-controls';
import { PortfolioHeader } from './portfolio-header';
import { PortfolioKpiRow } from './portfolio-kpi-row';
import { PortfolioValueChart } from './portfolio-value-chart';
import { ReturnAttribution } from './return-attribution';
import { RiskAnalytics } from './risk-analytics';
import { StageAnalysis } from './stage-analysis';
import { UpcomingEvents } from './upcoming-events';
import {
  computeAllocations,
  computeBenchmarks,
  computeCashFlow,
  computeConcentration,
  computeExitSchedule,
  computeInsights,
  computePerformanceSeries,
  computePerformanceTableRows,
  computePortfolioSummary,
  computeReturnAttribution,
  computeRiskSummary,
  countActivePortfolioFilters,
  filterPortfolioInvestments,
  getEnrichedPortfolio,
  getPortfolioAssetClasses,
  getPortfolioLocations,
} from '../../_data/portfolio-analytics';

const SHOW_ERROR_PLACEHOLDER = false;
const SHOW_EMPTY_PORTFOLIO = false;

export function PortfolioAnalyticsPage() {
  const allInvestments = useMemo(() => getEnrichedPortfolio(), []);
  const { dateRange, filters, setDateRange, updateFilter, clearFilters } = usePortfolioControls();

  const [isLoading, setIsLoading] = useState(true);
  const [compareOpen, setCompareOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => setIsLoading(false), 450);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!toastMessage) return;
    const timer = window.setTimeout(() => setToastMessage(null), 3200);
    return () => window.clearTimeout(timer);
  }, [toastMessage]);

  const filteredInvestments = useMemo(() => {
    if (SHOW_EMPTY_PORTFOLIO) return [];
    return filterPortfolioInvestments(allInvestments, filters);
  }, [allInvestments, filters]);

  const activeFilterCount = countActivePortfolioFilters(filters);
  const dateRangeConfig = useMemo(() => ({ preset: dateRange }), [dateRange]);

  const summary = useMemo(
    () => computePortfolioSummary(filteredInvestments, filters, dateRangeConfig),
    [filteredInvestments, filters, dateRangeConfig],
  );

  const allocations = useMemo(
    () => computeAllocations(filteredInvestments),
    [filteredInvestments],
  );

  const concentration = useMemo(
    () => computeConcentration(filteredInvestments),
    [filteredInvestments],
  );

  const risk = useMemo(() => computeRiskSummary(filteredInvestments), [filteredInvestments]);

  const performance = useMemo(
    () => computePerformanceSeries(filteredInvestments, dateRangeConfig),
    [filteredInvestments, dateRangeConfig],
  );

  const cashFlow = useMemo(() => computeCashFlow(filteredInvestments), [filteredInvestments]);
  const benchmarks = useMemo(() => computeBenchmarks(), []);
  const exitSchedule = useMemo(() => computeExitSchedule(filteredInvestments), [filteredInvestments]);
  const attribution = useMemo(
    () => computeReturnAttribution(filteredInvestments),
    [filteredInvestments],
  );
  const insights = useMemo(() => computeInsights(filteredInvestments), [filteredInvestments]);
  const tableRows = useMemo(
    () => computePerformanceTableRows(filteredInvestments),
    [filteredInvestments],
  );

  const assetClasses = useMemo(() => getPortfolioAssetClasses(allInvestments), [allInvestments]);
  const locations = useMemo(() => getPortfolioLocations(allInvestments), [allInvestments]);

  const handleToggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else if (next.size < 4) next.add(id);
      return next;
    });
  }, []);

  const handleExportReport = useCallback(() => {
    setToastMessage('Portfolio report export will be available in a future release.');
  }, []);

  const handleDownloadSummary = useCallback(() => {
    setToastMessage('Portfolio summary download coming soon.');
  }, []);

  if (SHOW_ERROR_PLACEHOLDER) {
    return (
      <div className="investor-page inv-portfolio">
        <InvestmentErrorState onRetry={() => window.location.reload()} />
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="investor-page inv-portfolio">
        <LoadingSkeletonGrid count={8} />
      </div>
    );
  }

  if (allInvestments.length === 0) {
    return (
      <div className="investor-page inv-portfolio">
        <EmptyState
          title="No investments yet"
          description="Your portfolio analytics will appear once you have active investments."
        />
      </div>
    );
  }

  return (
    <div className="investor-page inv-portfolio">
      <PortfolioHeader
        onExportReport={handleExportReport}
        onDownloadSummary={handleDownloadSummary}
        onCompareInvestments={() => setCompareOpen(true)}
      />

      <PortfolioControls
        state={{ dateRange, filters }}
        activeFilterCount={activeFilterCount}
        assetClasses={assetClasses}
        locations={locations}
        onDateRangeChange={setDateRange}
        onFilterChange={updateFilter}
        onClearFilters={clearFilters}
      />

      {filteredInvestments.length === 0 ? (
        <EmptyState
          title="No matching investments"
          description="Adjust or clear your filters to see portfolio analytics."
          actionLabel="Clear filters"
          onAction={clearFilters}
        />
      ) : (
        <>
          <PortfolioKpiRow summary={summary} />

          <div className="inv-portfolio-grid">
            <div className="inv-portfolio-grid__main">
              <PortfolioValueChart
                points={performance.points}
                currency={summary.currency}
                hasHistoricalFallback={performance.hasHistoricalFallback}
              />
              <PerformanceCharts points={performance.points} currency={summary.currency} />
              <AllocationSection allocation={allocations.asset} currency={summary.currency} />
              <GeographicAllocationSection
                geographic={allocations.geographic}
                currency={summary.currency}
              />
              <StageAnalysis stages={allocations.stage} currency={summary.currency} />
              <CashFlowSection cashFlow={cashFlow} currency={summary.currency} />
              <RiskAnalytics risk={risk} />
              <ReturnAttribution items={attribution} currency={summary.currency} />
              <PerformanceTable
                rows={tableRows}
                currency={summary.currency}
                selectedIds={selectedIds}
                onToggleSelect={handleToggleSelect}
              />
            </div>

            <aside className="inv-portfolio-grid__aside">
              <InsightsPanel insights={insights} />
              <ConcentrationAlerts alerts={concentration.alerts} currency={summary.currency} />
              <UpcomingEvents events={exitSchedule.events} currency={summary.currency} />
              <BenchmarksSection benchmarks={benchmarks} summary={summary} />
            </aside>
          </div>
        </>
      )}

      <InvestmentComparison
        open={compareOpen}
        onClose={() => setCompareOpen(false)}
        rows={tableRows}
        selectedIds={Array.from(selectedIds)}
        currency={summary.currency}
      />

      {toastMessage ? (
        <div className="inv-investments__toast" role="status" aria-live="polite">
          {toastMessage}
        </div>
      ) : null}
    </div>
  );
}
