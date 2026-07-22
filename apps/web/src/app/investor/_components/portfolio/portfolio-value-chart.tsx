'use client';

import { useState } from 'react';

import { MultiLineChart } from './chart-primitives';
import { SectionHeader } from '../section-header';
import type { PortfolioPerformancePoint } from '../../_data/portfolio-types';
import { formatInvestorCurrency } from '../../_data/mock-data';

export interface PortfolioValueChartProps {
  points: PortfolioPerformancePoint[];
  currency: string;
  hasHistoricalFallback?: boolean;
}

const SERIES = [
  { key: 'investedCapital', label: 'Invested Capital', color: '#8a8a8a' },
  { key: 'portfolioValue', label: 'Portfolio Value', color: 'var(--inv-gold)' },
  { key: 'equity', label: 'Equity', color: '#4682b4' },
  { key: 'benchmarkValue', label: 'Benchmark', color: '#c4a35a' },
];

export function PortfolioValueChart({
  points,
  currency,
  hasHistoricalFallback,
}: PortfolioValueChartProps) {
  const [hidden, setHidden] = useState<Set<string>>(new Set());

  const chartData = points.map((p) => ({
    label: p.label,
    investedCapital: p.investedCapital,
    portfolioValue: p.portfolioValue,
    equity: p.equity,
    benchmarkValue: p.benchmarkValue ?? 0,
  }));

  const toggleSeries = (key: string) => {
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  return (
    <section className="inv-portfolio-panel">
      <SectionHeader
        title="Portfolio Value Over Time"
        subtitle="Invested capital, portfolio value, equity, and benchmark comparison"
      />
      {hasHistoricalFallback ? (
        <p className="inv-portfolio-panel__notice" role="status">
          Some investments use estimated historical values where full monthly data is unavailable.
        </p>
      ) : null}
      <div className="inv-portfolio-chart-legend" role="group" aria-label="Toggle chart series">
        {SERIES.map((s) => (
          <button
            key={s.key}
            type="button"
            className={`inv-portfolio-chart-legend__item${hidden.has(s.key) ? ' inv-portfolio-chart-legend__item--hidden' : ''}`}
            aria-pressed={!hidden.has(s.key)}
            onClick={() => toggleSeries(s.key)}
          >
            <span className="inv-portfolio-chart-legend__swatch" style={{ background: s.color }} />
            {s.label}
          </button>
        ))}
      </div>
      <MultiLineChart
        data={chartData}
        series={SERIES}
        hiddenSeries={hidden}
        ariaLabel="Portfolio value over time chart"
        formatValue={(v) => formatInvestorCurrency(v, currency)}
      />
    </section>
  );
}
