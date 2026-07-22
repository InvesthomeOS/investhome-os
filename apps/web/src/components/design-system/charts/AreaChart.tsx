'use client';

import { ChartContainer, type ChartContainerState } from '@investhome/ui';

import { DS_CHART_PRIMARY, formatChartValue, type ChartNumberFormat } from './format';

export interface AreaChartPoint {
  label: string;
  value: number;
}

export interface AreaChartProps {
  data: AreaChartPoint[];
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

export function AreaChart({
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
}: AreaChartProps) {
  const resolvedState: ChartContainerState =
    state ?? (data.length === 0 ? 'empty' : 'ready');
  const width = 320;
  const pad = { t: 12, r: 8, b: 24, l: 8 };
  const values = data.map((d) => d.value);
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 1);
  const range = max - min || 1;
  const points = data.map((d, i) => {
    const x = pad.l + (i / Math.max(data.length - 1, 1)) * (width - pad.l - pad.r);
    const y = pad.t + ((max - d.value) / range) * (height - pad.t - pad.b);
    return { x, y };
  });
  const line = points.map((p) => `${p.x},${p.y}`).join(' ');
  const area = `${pad.l},${height - pad.b} ${line} ${width - pad.r},${height - pad.b}`;
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
      <figure className="ds-chart ds-chart--area" role="figure" aria-label={ariaLabel}>
        <p className="sr-only">{summary}</p>
        <svg viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
          <polygon className="ds-chart--area__fill" points={area} />
          <polyline className="ds-chart--area__stroke" points={line} fill="none" />
        </svg>
      </figure>
    </ChartContainer>
  );
}
