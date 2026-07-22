'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

import type { DistributionFilterState } from '../../_data/distribution-types';
import {
  computeAlerts,
  computeDistributionSummary,
  computeInsights,
  getAllDistributions,
  getDistributionEvents,
  getUpcomingDistributions,
} from '../../_data/distribution-calculations';
import { LoadingSkeletonGrid } from '../loading-skeleton';
import { AlertsSection } from './alerts';
import { CashFlowByInvestment } from './by-investment';
import { CashFlowChart } from './cash-flow-chart';
import { DistributionCalendar } from './calendar';
import { DistributionHistoryTable } from './history-table';
import { DistributionsHeader } from './distributions-header';
import { DistributionKpiRow } from './kpi-row';
import { InsightsPanel } from './insights';
import { PaymentInfoDrawer } from './payment-info-drawer';
import { PreferredReturnSection } from './preferred-return';
import { ProjectionSection } from './projection-section';
import { RocTrackingSection } from './roc-tracking';
import { SourceBreakdown } from './source-breakdown';
import { TaxSummarySection } from './tax-summary';
import { UpcomingDistributionCard } from './upcoming-card';

const DEFAULT_FILTERS: DistributionFilterState = {
  search: '',
  investmentId: 'all',
  type: 'all',
  status: 'all',
  taxYear: 'all',
  dateFrom: '',
  dateTo: '',
};

export function DistributionsView() {
  const [isLoading, setIsLoading] = useState(true);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [paymentDrawerOpen, setPaymentDrawerOpen] = useState(false);
  const [filters, setFilters] = useState<DistributionFilterState>(DEFAULT_FILTERS);

  const distributions = useMemo(() => getAllDistributions(), []);
  const dateRange = useMemo(() => ({ preset: 'all' as const }), []);

  const summary = useMemo(
    () => computeDistributionSummary(distributions, DEFAULT_FILTERS, dateRange),
    [distributions, dateRange],
  );

  const upcoming = useMemo(() => getUpcomingDistributions(distributions), [distributions]);
  const events = useMemo(() => getDistributionEvents(distributions), [distributions]);
  const alerts = useMemo(() => computeAlerts(distributions), [distributions]);
  const insights = useMemo(
    () => computeInsights(distributions, summary),
    [distributions, summary],
  );

  useEffect(() => {
    const timer = window.setTimeout(() => setIsLoading(false), 400);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!toastMessage) return;
    const timer = window.setTimeout(() => setToastMessage(null), 3200);
    return () => window.clearTimeout(timer);
  }, [toastMessage]);

  const showToast = useCallback((message: string) => setToastMessage(message), []);

  const updateFilters = useCallback((patch: Partial<DistributionFilterState>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
  }, []);

  if (isLoading) {
    return (
      <div className="investor-page inv-distributions">
        <LoadingSkeletonGrid count={8} />
      </div>
    );
  }

  return (
    <div className="investor-page inv-distributions">
      <DistributionsHeader
        onDownloadReport={() => showToast('Distribution report download coming soon.')}
        onExportCashFlow={() => showToast('Cash flow export coming soon.')}
        onOpenPaymentInfo={() => setPaymentDrawerOpen(true)}
      />

      <DistributionKpiRow summary={summary} distributions={distributions} />

      <div className="inv-distributions__layout">
        <div className="inv-distributions__main">
          <UpcomingDistributionCard upcoming={upcoming} allDistributions={distributions} />
          <CashFlowChart
            distributions={distributions}
            filters={DEFAULT_FILTERS}
            dateRange={dateRange}
            currency={summary.currency}
          />
          <SourceBreakdown
            distributions={distributions}
            filters={DEFAULT_FILTERS}
            dateRange={dateRange}
            currency={summary.currency}
          />
          <DistributionHistoryTable
            distributions={distributions}
            filters={filters}
            onFiltersChange={updateFilters}
          />
          <ProjectionSection distributions={distributions} currency={summary.currency} />
          <CashFlowByInvestment distributions={distributions} />
          <DistributionCalendar events={events} />
          <PreferredReturnSection distributions={distributions} />
          <RocTrackingSection distributions={distributions} />
          <TaxSummarySection distributions={distributions} />
        </div>

        <aside className="inv-distributions__sidebar">
          <AlertsSection
            alerts={alerts}
            onAction={(alert) => {
              if (alert.actionLabel === 'Update Payment Info') setPaymentDrawerOpen(true);
              else showToast('Action placeholder — no real payments processed.');
            }}
          />
          <InsightsPanel insights={insights} />
        </aside>
      </div>

      <PaymentInfoDrawer open={paymentDrawerOpen} onClose={() => setPaymentDrawerOpen(false)} />

      {toastMessage ? (
        <div className="inv-investments__toast" role="status">
          {toastMessage}
        </div>
      ) : null}
    </div>
  );
}
