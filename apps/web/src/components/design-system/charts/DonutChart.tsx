'use client';

import { ChartContainer, type ChartContainerState } from '@investhome/ui';

import { chartColorAt, formatChartValue, type ChartNumberFormat } from './format';

export interface DonutChartSlice {
  label: string;
  value: number;
}

export interface DonutChartProps {
  data: DonutChartSlice[];
  ariaLabel: string;
  locale?: string;
  format?: ChartNumberFormat;
  currency?: string;
  state?: ChartContainerState;
  title?: string;
  emptyTitle?: string;
  loadingLabel?: string;
  className?: string;
}

export function DonutChart({
  data,
  ariaLabel,
  locale = 'tr',
  format = 'percent',
  currency = 'TRY',
  state,
  title,
  emptyTitle,
  loadingLabel,
  className,
}: DonutChartProps) {
  const total = data.reduce((sum, d) => sum + d.value, 0);
  const resolvedState: ChartContainerState =
    state ?? (total === 0 ? 'empty' : 'ready');
  let cumulative = 0;
  const segments = data.map((d, i) => {
    const start = cumulative;
    cumulative += total > 0 ? d.value / total : 0;
    return { ...d, start, end: cumulative, color: chartColorAt(i) };
  });
  const summary = data
    .map((d) => `${d.label}: ${formatChartValue(total ? d.value / total : 0, format, locale, currency)}`)
    .join('; ');

  return (
    <ChartContainer
      title={title}
      state={resolvedState}
      ariaLabel={ariaLabel}
      emptyTitle={emptyTitle}
      loadingLabel={loadingLabel}
      className={className}
      legend={segments.map((s) => ({ label: s.label, color: s.color }))}
    >
      <figure className="ds-chart ds-chart--donut" role="figure" aria-label={ariaLabel}>
        <p className="sr-only">{summary}</p>
        <svg viewBox="0 0 100 100" aria-hidden="true">
          {segments.map((seg) => {
            const startAngle = seg.start * 360 - 90;
            const endAngle = seg.end * 360 - 90;
            const largeArc = seg.end - seg.start > 0.5 ? 1 : 0;
            const r = 40;
            const ir = 26;
            const startRad = (startAngle * Math.PI) / 180;
            const endRad = (endAngle * Math.PI) / 180;
            const x1 = 50 + r * Math.cos(startRad);
            const y1 = 50 + r * Math.sin(startRad);
            const x2 = 50 + r * Math.cos(endRad);
            const y2 = 50 + r * Math.sin(endRad);
            const ix1 = 50 + ir * Math.cos(endRad);
            const iy1 = 50 + ir * Math.sin(endRad);
            const ix2 = 50 + ir * Math.cos(startRad);
            const iy2 = 50 + ir * Math.sin(startRad);
            const d = `M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} L ${ix1} ${iy1} A ${ir} ${ir} 0 ${largeArc} 0 ${ix2} ${iy2} Z`;
            return <path key={seg.label} className="ds-chart--donut__segment" d={d} fill={seg.color} />;
          })}
        </svg>
      </figure>
    </ChartContainer>
  );
}
