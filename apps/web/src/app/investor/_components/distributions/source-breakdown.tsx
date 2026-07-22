'use client';

import { useState } from 'react';

import type { DistributionDateRange, DistributionFilterState } from '../../_data/distribution-types';
import type { Distribution } from '../../_data/distribution-types';
import { computeSourceBreakdown } from '../../_data/distribution-calculations';
import { formatInvestorCurrency } from '../../_data/mock-data';
import { DonutChart, StackedBarChart } from '../portfolio/chart-primitives';
import { SectionHeader } from '../section-header';

export interface SourceBreakdownProps {
  distributions: Distribution[];
  filters: DistributionFilterState;
  dateRange: DistributionDateRange;
  currency: string;
}

export function SourceBreakdown({
  distributions,
  filters,
  dateRange,
  currency,
}: SourceBreakdownProps) {
  const [view, setView] = useState<'donut' | 'bar'>('donut');
  const slices = computeSourceBreakdown(distributions, filters, dateRange);
  const chartData = slices.map((s) => ({ label: s.label, value: s.value }));

  return (
    <section className="inv-distributions__panel">
      <SectionHeader title="Cash Flow Source Breakdown" subtitle="Net distribution amounts by type" />

      <div className="inv-distributions__toggle-group" role="group" aria-label="Chart type">
        <button
          type="button"
          className={`inv-distributions__toggle${view === 'donut' ? ' inv-distributions__toggle--active' : ''}`}
          onClick={() => setView('donut')}
          aria-pressed={view === 'donut'}
        >
          Donut
        </button>
        <button
          type="button"
          className={`inv-distributions__toggle${view === 'bar' ? ' inv-distributions__toggle--active' : ''}`}
          onClick={() => setView('bar')}
          aria-pressed={view === 'bar'}
        >
          Stacked Bar
        </button>
      </div>

      {chartData.length === 0 ? (
        <p className="inv-distributions__empty-note">No completed distributions in range.</p>
      ) : view === 'donut' ? (
        <DonutChart data={chartData} ariaLabel="Cash flow source breakdown donut chart" />
      ) : (
        <StackedBarChart
          data={[{ label: 'Sources', segments: chartData }]}
          ariaLabel="Cash flow source stacked bar chart"
        />
      )}

      <ul className="inv-distributions__source-list">
        {slices.map((s) => (
          <li key={s.type}>
            <span>{s.label}</span>
            <strong>{formatInvestorCurrency(s.value, currency)}</strong>
          </li>
        ))}
      </ul>
    </section>
  );
}
