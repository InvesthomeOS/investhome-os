'use client';

import { ChartContainer, type ChartContainerState } from '@investhome/ui';

import { formatChartValue, type ChartNumberFormat } from './format';

export interface SparklineProps {
  values: number[];
  ariaLabel: string;
  locale?: string;
  format?: ChartNumberFormat;
  state?: ChartContainerState;
  className?: string;
}

export function Sparkline({
  values,
  ariaLabel,
  locale = 'tr',
  format = 'number',
  state,
  className,
}: SparklineProps) {
  const resolvedState: ChartContainerState =
    state ?? (values.length === 0 ? 'empty' : 'ready');
  const width = 120;
  const height = 36;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const points = values
    .map((v, i) => {
      const x = (i / Math.max(values.length - 1, 1)) * width;
      const y = height - ((v - min) / range) * (height - 4) - 2;
      return `${x},${y}`;
    })
    .join(' ');
  const summary = values.map((v) => formatChartValue(v, format, locale)).join(', ');

  return (
    <ChartContainer state={resolvedState} ariaLabel={ariaLabel} className={className}>
      <svg
        className="ds-chart--sparkline"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={`${ariaLabel}: ${summary}`}
      >
        <polyline
          points={points}
          fill="none"
          stroke="var(--brand-primary)"
          strokeWidth="1.5"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
    </ChartContainer>
  );
}
