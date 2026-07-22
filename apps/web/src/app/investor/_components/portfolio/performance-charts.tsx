'use client';

import { useState } from 'react';

import { MultiLineChart } from './chart-primitives';
import { SectionHeader } from '../section-header';
import type { PortfolioPerformancePoint } from '../../_data/portfolio-types';
import { formatInvestorCurrency, formatInvestorPercent } from '../../_data/mock-data';

export interface PerformanceChartsProps {
  points: PortfolioPerformancePoint[];
  currency: string;
}

type PerformanceTab =
  | 'cumulativeRoi'
  | 'projectedVsActual'
  | 'irr'
  | 'equityMultiple'
  | 'cashFlow';

const TABS: { id: PerformanceTab; label: string }[] = [
  { id: 'cumulativeRoi', label: 'Cumulative ROI' },
  { id: 'projectedVsActual', label: 'Projected vs Actual' },
  { id: 'irr', label: 'IRR' },
  { id: 'equityMultiple', label: 'Equity Multiple' },
  { id: 'cashFlow', label: 'Annualized Cash Flow' },
];

export function PerformanceCharts({ points, currency }: PerformanceChartsProps) {
  const [tab, setTab] = useState<PerformanceTab>('cumulativeRoi');

  const chartData = points.map((p) => ({
    label: p.label,
    cumulativeRoi: p.cumulativeRoi,
    projectedRoi: p.projectedRoi,
    actualRoi: p.actualRoi,
    irr: p.irr,
    equityMultiple: p.equityMultiple,
    cashFlow: p.cashFlow * 12,
  }));

  const seriesMap: Record<PerformanceTab, { key: string; label: string; color: string }[]> = {
    cumulativeRoi: [{ key: 'cumulativeRoi', label: 'Cumulative ROI', color: 'var(--inv-gold)' }],
    projectedVsActual: [
      { key: 'projectedRoi', label: 'Projected ROI', color: '#c4a35a' },
      { key: 'actualRoi', label: 'Actual ROI', color: 'var(--inv-gold)' },
    ],
    irr: [{ key: 'irr', label: 'IRR', color: '#4682b4' }],
    equityMultiple: [{ key: 'equityMultiple', label: 'Equity Multiple', color: 'var(--inv-gold)' }],
    cashFlow: [{ key: 'cashFlow', label: 'Annual Cash Flow', color: '#6b8e6b' }],
  };

  const formatValue =
    tab === 'equityMultiple'
      ? (v: number) => `${v.toFixed(2)}x`
      : tab === 'cashFlow'
        ? (v: number) => formatInvestorCurrency(v, currency)
        : (v: number) => formatInvestorPercent(v);

  return (
    <section className="inv-portfolio-panel">
      <SectionHeader title="Performance Over Time" subtitle="Track returns and cash generation" />
      <div className="inv-portfolio-tabs" role="tablist" aria-label="Performance metrics">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            className={`inv-portfolio-tabs__tab${tab === t.id ? ' inv-portfolio-tabs__tab--active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <MultiLineChart
        data={chartData}
        series={seriesMap[tab]}
        ariaLabel={`Performance chart: ${TABS.find((t) => t.id === tab)?.label}`}
        formatValue={formatValue}
      />
    </section>
  );
}
