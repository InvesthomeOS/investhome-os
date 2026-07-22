'use client';

import { computeInvestmentSummary } from '../_data/investments';
import type { PortfolioInvestment } from '../_data/investment-types';
import { formatInvestorCurrency, formatInvestorPercent } from '../_data/mock-data';
import { InvestorKpiCard } from './kpi-card';

export interface InvestmentSummaryRowProps {
  investments: PortfolioInvestment[];
}

export function InvestmentSummaryRow({ investments }: InvestmentSummaryRowProps) {
  const summary = computeInvestmentSummary(investments);

  return (
    <section
      className="inv-investments__summary"
      aria-label="Portfolio investment summary"
    >
      <InvestorKpiCard
        label="Total Investments"
        value={summary.totalInvestments}
        meta="Across all statuses"
      />
      <InvestorKpiCard
        label="Total Invested"
        value={formatInvestorCurrency(summary.totalInvested, summary.currency)}
        delta="+12.4% vs. last year"
      />
      <InvestorKpiCard
        label="Current Portfolio Value"
        value={formatInvestorCurrency(summary.currentPortfolioValue, summary.currency)}
        delta="+18.0% lifetime gain"
      />
      <InvestorKpiCard
        label="Estimated Equity"
        value={formatInvestorCurrency(summary.estimatedEquity, summary.currency)}
        meta="Unrealized appreciation"
      />
      <InvestorKpiCard
        label="Active Investments"
        value={summary.activeInvestments}
        meta={`${summary.completedInvestments} completed`}
      />
      <InvestorKpiCard
        label="Completed Investments"
        value={summary.completedInvestments}
        meta="Fully exited positions"
      />
      <InvestorKpiCard
        label="Average Projected ROI"
        value={formatInvestorPercent(summary.averageProjectedRoi)}
        delta="Weighted projection"
      />
      <InvestorKpiCard
        label="Average IRR"
        value={formatInvestorPercent(summary.averageIrr)}
        meta="Active & stabilized holdings"
      />
    </section>
  );
}
