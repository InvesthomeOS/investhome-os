'use client';

import { useState } from 'react';

import type { CashFlowPeriod, DistributionDateRange, DistributionFilterState } from '../../_data/distribution-types';
import type { Distribution } from '../../_data/distribution-types';
import { computeCashFlowSeries } from '../../_data/distribution-calculations';
import { formatInvestorCurrency } from '../../_data/mock-data';
import { MultiLineChart } from '../portfolio/chart-primitives';
import { SectionHeader } from '../section-header';

export interface CashFlowChartProps {
  distributions: Distribution[];
  filters: DistributionFilterState;
  dateRange: DistributionDateRange;
  currency: string;
}

const DATE_PRESETS: { value: DistributionDateRange['preset']; label: string }[] = [
  { value: '3M', label: '3M' },
  { value: '6M', label: '6M' },
  { value: 'YTD', label: 'YTD' },
  { value: '1Y', label: '1Y' },
  { value: '3Y', label: '3Y' },
  { value: 'all', label: 'All' },
];

const SERIES = [
  { key: 'gross', label: 'Gross', color: 'var(--inv-gold)' },
  { key: 'net', label: 'Net', color: '#6b8e6b' },
  { key: 'preferredReturn', label: 'Preferred', color: '#4682b4' },
  { key: 'returnOfCapital', label: 'ROC', color: '#9370db' },
  { key: 'refinance', label: 'Refinance', color: '#cd853f' },
  { key: 'sale', label: 'Sale', color: '#708090' },
];

function toChartData(periods: CashFlowPeriod[]) {
  return periods.map((p) => ({
    label: p.label,
    gross: p.gross,
    net: p.net,
    preferredReturn: p.preferredReturn,
    returnOfCapital: p.returnOfCapital,
    refinance: p.refinance,
    sale: p.sale,
  }));
}

export function CashFlowChart({
  distributions,
  filters,
  dateRange: initialRange,
  currency,
}: CashFlowChartProps) {
  const [preset, setPreset] = useState<DistributionDateRange['preset']>(initialRange.preset);
  const [granularity, setGranularity] = useState<'monthly' | 'quarterly'>('quarterly');
  const [hiddenSeries, setHiddenSeries] = useState<Set<string>>(new Set());

  const dateRange: DistributionDateRange = { preset };
  const periods = computeCashFlowSeries(distributions, filters, dateRange, granularity);
  const chartData = toChartData(periods);

  const summaryText = periods.length
    ? periods
        .map(
          (p) =>
            `${p.label}: net ${formatInvestorCurrency(p.net, currency)}, gross ${formatInvestorCurrency(p.gross, currency)}`,
        )
        .join('; ')
    : 'No cash flow data in the selected range.';

  return (
    <section className="inv-distributions__panel">
      <SectionHeader title="Cash Flow Over Time" subtitle="Historical distributions by source type" />

      <div className="inv-distributions__chart-controls">
        <div className="inv-distributions__toggle-group" role="group" aria-label="Date range">
          {DATE_PRESETS.map((p) => (
            <button
              key={p.value}
              type="button"
              className={`inv-distributions__toggle${preset === p.value ? ' inv-distributions__toggle--active' : ''}`}
              onClick={() => setPreset(p.value)}
              aria-pressed={preset === p.value}
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className="inv-distributions__toggle-group" role="group" aria-label="Granularity">
          {(['monthly', 'quarterly'] as const).map((g) => (
            <button
              key={g}
              type="button"
              className={`inv-distributions__toggle${granularity === g ? ' inv-distributions__toggle--active' : ''}`}
              onClick={() => setGranularity(g)}
              aria-pressed={granularity === g}
            >
              {g === 'monthly' ? 'Monthly' : 'Quarterly'}
            </button>
          ))}
        </div>
      </div>

      <div className="inv-distributions__series-toggles">
        {SERIES.map((s) => (
          <button
            key={s.key}
            type="button"
            className={`inv-distributions__series-toggle${hiddenSeries.has(s.key) ? ' inv-distributions__series-toggle--off' : ''}`}
            onClick={() => {
              setHiddenSeries((prev) => {
                const next = new Set(prev);
                if (next.has(s.key)) next.delete(s.key);
                else next.add(s.key);
                return next;
              });
            }}
            aria-pressed={!hiddenSeries.has(s.key)}
          >
            <span className="inv-distributions__series-swatch" style={{ background: s.color }} />
            {s.label}
          </button>
        ))}
      </div>

      {chartData.length === 0 ? (
        <p className="inv-distributions__empty-note">{summaryText}</p>
      ) : (
        <>
          <p className="inv-portfolio-chart__sr-summary">{summaryText}</p>
          <MultiLineChart
            data={chartData}
            series={SERIES}
            hiddenSeries={hiddenSeries}
            ariaLabel="Cash flow over time chart"
            formatValue={(v) => formatInvestorCurrency(v, currency)}
            height={220}
          />
        </>
      )}
    </section>
  );
}
