'use client';

import { InvestorKpiCard } from '../kpi-card';
import type { CashFlowSummary } from '../../_data/distribution-types';
import { computeNextScheduledAmount } from '../../_data/distribution-calculations';
import type { Distribution } from '../../_data/distribution-types';
import {
  formatInvestorCurrency,
  formatInvestorDate,
  formatInvestorPercent,
} from '../../_data/mock-data';

export interface DistributionKpiRowProps {
  summary: CashFlowSummary;
  distributions: Distribution[];
}

export function DistributionKpiRow({ summary, distributions }: DistributionKpiRowProps) {
  const nextScheduled = computeNextScheduledAmount(distributions);
  const { currency } = summary;

  const kpis = [
    {
      label: 'Lifetime Distributions',
      value: formatInvestorCurrency(summary.lifetimeNet, currency),
      meta: `Gross ${formatInvestorCurrency(summary.lifetimeGross, currency)}`,
    },
    {
      label: 'Current Year (Net)',
      value: formatInvestorCurrency(summary.currentYearNet, currency),
      meta: `Gross ${formatInvestorCurrency(summary.currentYearGross, currency)}`,
    },
    {
      label: 'Net Cash Flow',
      value: formatInvestorCurrency(summary.lifetimeNet, currency),
      meta: 'Cumulative net received',
    },
    {
      label: 'Preferred Return',
      value: formatInvestorCurrency(summary.preferredReturnTotal, currency),
      meta: 'Cumulative preferred payments',
    },
    {
      label: 'Capital Returned',
      value: formatInvestorCurrency(summary.capitalReturned, currency),
      meta: 'Return of capital to date',
    },
    {
      label: 'Next Scheduled',
      value: nextScheduled
        ? formatInvestorCurrency(nextScheduled.amount, nextScheduled.currency)
        : '—',
      meta: nextScheduled
        ? `${nextScheduled.investmentName} · ${formatInvestorDate(nextScheduled.date)}`
        : 'No upcoming payments',
    },
    {
      label: 'Avg Annual Yield',
      value: formatInvestorPercent(summary.avgAnnualYield),
      meta: 'Net / invested capital (range)',
    },
    {
      label: 'Pending Amount',
      value: formatInvestorCurrency(summary.pendingAmount, currency),
      meta: 'Scheduled & in-process',
    },
  ];

  return (
    <section className="inv-distributions__kpi-grid" aria-label="Distribution key performance indicators">
      {kpis.map((kpi) => (
        <InvestorKpiCard
          key={kpi.label}
          label={kpi.label}
          value={kpi.value}
          meta={kpi.meta}
        />
      ))}
    </section>
  );
}
