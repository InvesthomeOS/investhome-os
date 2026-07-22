'use client';

import { InvestorKpiCard } from '../kpi-card';
import { formatTrendDelta } from '../../_data/portfolio-analytics';
import type { PortfolioSummary } from '../../_data/portfolio-types';
import { formatInvestorCurrency, formatInvestorPercent } from '../../_data/mock-data';

export interface PortfolioKpiRowProps {
  summary: PortfolioSummary;
}

export function PortfolioKpiRow({ summary }: PortfolioKpiRowProps) {
  const { currency, trends } = summary;

  const kpis = [
    {
      label: 'Total Invested',
      value: formatInvestorCurrency(summary.totalInvested, currency),
      delta: formatTrendDelta(trends.totalInvested),
      tooltip: 'Aggregate capital committed across filtered investments.',
    },
    {
      label: 'Current Value',
      value: formatInvestorCurrency(summary.currentValue, currency),
      delta: formatTrendDelta(trends.currentValue),
      tooltip: 'Mark-to-market portfolio value including unrealized appreciation.',
    },
    {
      label: 'Equity',
      value: formatInvestorCurrency(summary.equity, currency),
      delta: formatTrendDelta(trends.equity),
      tooltip: 'Net equity after outstanding debt across the portfolio.',
    },
    {
      label: 'Outstanding Debt',
      value: formatInvestorCurrency(summary.outstandingDebt, currency),
      tooltip: 'Total leverage outstanding on portfolio assets.',
    },
    {
      label: 'Annual Net Cash Flow',
      value: formatInvestorCurrency(summary.annualNetCashFlow, currency),
      delta: formatTrendDelta(trends.annualNetCashFlow),
      tooltip: 'Projected annual distributions net of fees.',
    },
    {
      label: 'Portfolio ROI',
      value: formatInvestorPercent(summary.portfolioRoi),
      delta: formatTrendDelta(trends.portfolioRoi, true),
      tooltip: 'Blended return on invested capital.',
    },
    {
      label: 'Portfolio IRR',
      value: formatInvestorPercent(summary.portfolioIrr),
      delta: formatTrendDelta(trends.portfolioIrr, true),
      tooltip: 'Invested-capital-weighted internal rate of return.',
    },
    {
      label: 'Equity Multiple',
      value: `${summary.equityMultiple.toFixed(2)}x`,
      delta: formatTrendDelta(trends.equityMultiple),
      tooltip: 'Current value divided by total invested capital.',
    },
  ];

  return (
    <section className="inv-portfolio-kpi-grid" aria-label="Portfolio key performance indicators">
      {kpis.map((kpi) => (
        <InvestorKpiCard
          key={kpi.label}
          label={kpi.label}
          value={
            <span title={kpi.tooltip} className="inv-portfolio-kpi__value">
              {kpi.value}
            </span>
          }
          delta={kpi.delta}
          meta={kpi.tooltip}
        />
      ))}
    </section>
  );
}
