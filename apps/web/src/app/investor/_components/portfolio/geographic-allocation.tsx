'use client';

import { useState } from 'react';

import { HorizontalBarChart } from './chart-primitives';
import { SectionHeader } from '../section-header';
import type { GeographicAllocation } from '../../_data/portfolio-types';
import { formatInvestorCurrency } from '../../_data/mock-data';

export interface GeographicAllocationSectionProps {
  geographic: GeographicAllocation;
  currency: string;
}

export function GeographicAllocationSection({
  geographic,
  currency,
}: GeographicAllocationSectionProps) {
  const [view, setView] = useState<'city' | 'state'>('city');

  const slices = view === 'city' ? geographic.byCity : geographic.byState;
  const chartData = slices.slice(0, 8).map((s) => ({ label: s.label, value: s.value }));

  return (
    <section className="inv-portfolio-panel">
      <SectionHeader title="Geographic Allocation" subtitle="Exposure by market" />
      <div className="inv-portfolio-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={view === 'city'}
          className={`inv-portfolio-tabs__tab${view === 'city' ? ' inv-portfolio-tabs__tab--active' : ''}`}
          onClick={() => setView('city')}
        >
          By City
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={view === 'state'}
          className={`inv-portfolio-tabs__tab${view === 'state' ? ' inv-portfolio-tabs__tab--active' : ''}`}
          onClick={() => setView('state')}
        >
          By State
        </button>
      </div>
      <HorizontalBarChart
        data={chartData}
        ariaLabel={`Geographic allocation by ${view}`}
        formatValue={(v) => formatInvestorCurrency(v, currency)}
      />
      <ol className="inv-portfolio-ranked-list">
        {slices.map((s, i) => (
          <li key={s.key}>
            <span className="inv-portfolio-ranked-list__rank">{i + 1}</span>
            <span className="inv-portfolio-ranked-list__label">{s.label}</span>
            <span className="inv-portfolio-ranked-list__value">
              {formatInvestorCurrency(s.value, currency)}
            </span>
            <span className="inv-portfolio-ranked-list__pct">{s.percent.toFixed(1)}%</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
