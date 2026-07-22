'use client';

import { ChartContainer, type ChartContainerState } from '@investhome/ui';

import { DS_CHART_PRIMARY, formatChartValue, type ChartNumberFormat } from './format';

export interface LineChartPoint {
  label: string;
  value: number;
}

export interface LineChartProps {
  data: LineChartPoint[];
  ariaLabel: string;
  locale?: string;
  format?: ChartNumberFormat;
  currency?: string;
  height?: number;
  state?: ChartContainerState;
  title?: string;
  emptyTitle?: string;
  loadingLabel?: string;
  className?: string;
}

export function LineChart({
  data,
  ariaLabel,
  locale = 'tr',
  format = 'number',
  currency = 'TRY',
  height = 160,
  state,
  title,
  emptyTitle,
  loadingLabel,
  className,
}: LineChartProps) {
  const resolvedState: ChartContainerState =
    state ?? (data.length === 0 ? 'empty' : 'ready');
  const width = 320;
  const pad = { t: 12, r: 8, b: 24, l: 8 };
  const values = data.map((d) => d.value);
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 1);
  const range = max - min || 1;
  const coords = data.map((d, i) => {
    const x = pad.l + (i / Math.max(data.length - 1, 1)) * (width - pad.l - pad.r);
    const y = pad.t + ((max - d.value) / range) * (height - pad.t - pad.b);
    return `${x},${y}`;
  });
  const summary = data
    .map((d) => `${d.label}: ${formatChartValue(d.value, format, locale, currency)}`)
    .join('; ');

  return (
    <ChartContainer
      title={title}
      state={resolvedState}
      ariaLabel={ariaLabel}
      emptyTitle={emptyTitle}
      loadingLabel={loadingLabel}
      className={className}
      legend={[{ label: ariaLabel, color: DS_CHART_PRIMARY }]}
    >
      <figure className="ds-chart ds-chart--line" role="figure" aria-label={ariaLabel}>
        <p className="sr-only">{summary}</p>
        <svg viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
          <polyline
            className="ds-chart--line__stroke"
            points={coords.join(' ')}
            fill="none"
          />
        </svg>
      </figure>
    </ChartContainer>
  );
}
