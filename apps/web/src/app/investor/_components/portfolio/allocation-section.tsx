'use client';

import { useState } from 'react';

import { DonutChart, HorizontalBarChart } from './chart-primitives';
import { SectionHeader } from '../section-header';
import type { AssetAllocation } from '../../_data/portfolio-types';
import { formatInvestorCurrency } from '../../_data/mock-data';

export interface AllocationSectionProps {
  allocation: AssetAllocation;
  currency: string;
}

type AllocationView = 'assetClass' | 'type' | 'stage' | 'status';

export function AllocationSection({ allocation, currency }: AllocationSectionProps) {
  const [view, setView] = useState<AllocationView>('assetClass');
  const [chartType, setChartType] = useState<'donut' | 'bar'>('donut');

  const dataMap: Record<AllocationView, typeof allocation.byAssetClass> = {
    assetClass: allocation.byAssetClass,
    type: allocation.byType,
    stage: allocation.byStage,
    status: allocation.byStatus,
  };

  const slices = dataMap[view];
  const chartData = slices.map((s) => ({ label: s.label, value: s.value }));

  return (
    <section className="inv-portfolio-panel">
      <SectionHeader title="Asset Allocation" subtitle="Portfolio composition by category" />
      <div className="inv-portfolio-tabs" role="tablist" aria-label="Allocation dimension">
        {(
          [
            ['assetClass', 'Asset Class'],
            ['type', 'Type'],
            ['stage', 'Stage'],
            ['status', 'Status'],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={view === id}
            className={`inv-portfolio-tabs__tab${view === id ? ' inv-portfolio-tabs__tab--active' : ''}`}
            onClick={() => setView(id)}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="inv-portfolio-chart-toggle">
        <button
          type="button"
          className={`inv-portfolio-tabs__tab${chartType === 'donut' ? ' inv-portfolio-tabs__tab--active' : ''}`}
          aria-pressed={chartType === 'donut'}
          onClick={() => setChartType('donut')}
        >
          Donut
        </button>
        <button
          type="button"
          className={`inv-portfolio-tabs__tab${chartType === 'bar' ? ' inv-portfolio-tabs__tab--active' : ''}`}
          aria-pressed={chartType === 'bar'}
          onClick={() => setChartType('bar')}
        >
          Bar
        </button>
      </div>
      {chartType === 'donut' ? (
        <DonutChart data={chartData} ariaLabel={`Allocation by ${view}`} />
      ) : (
        <HorizontalBarChart
          data={chartData}
          ariaLabel={`Allocation by ${view}`}
          formatValue={(v) => formatInvestorCurrency(v, currency)}
        />
      )}
    </section>
  );
}
