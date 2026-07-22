'use client';

import type { ChartDataPoint } from '../../_data/investment-detail-types';

export interface MultiSeriesPoint {
  label: string;
  [key: string]: string | number;
}

export interface ChartSeries {
  key: string;
  label: string;
  color: string;
}

export interface MultiLineChartProps {
  data: MultiSeriesPoint[];
  series: ChartSeries[];
  height?: number;
  ariaLabel: string;
  formatValue?: (value: number) => string;
  hiddenSeries?: Set<string>;
}

export function MultiLineChart({
  data,
  series,
  height = 200,
  ariaLabel,
  formatValue = (v) => v.toLocaleString(),
  hiddenSeries = new Set(),
}: MultiLineChartProps) {
  if (data.length === 0) return null;

  const visibleSeries = series.filter((s) => !hiddenSeries.has(s.key));
  const width = 100;
  const padding = { top: 8, right: 4, bottom: 24, left: 4 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const allValues = data.flatMap((d) =>
    visibleSeries.map((s) => Number(d[s.key]) || 0),
  );
  const min = Math.min(...allValues) * 0.95;
  const max = Math.max(...allValues) * 1.05;
  const range = max - min || 1;

  const summary = visibleSeries
    .map((s) => {
      const last = data[data.length - 1];
      const val = Number(last?.[s.key]) || 0;
      return `${s.label}: ${formatValue(val)}`;
    })
    .join('; ');

  return (
    <figure className="inv-detail-chart inv-portfolio-chart" role="figure" aria-label={ariaLabel}>
      <p className="inv-portfolio-chart__sr-summary">{summary}</p>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="inv-detail-chart__svg"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        {visibleSeries.map((s) => {
          const points = data.map((d, i) => {
            const val = Number(d[s.key]) || 0;
            const x = padding.left + (i / Math.max(data.length - 1, 1)) * chartW;
            const y = padding.top + chartH - ((val - min) / range) * chartH;
            return { x, y };
          });
          const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
          return (
            <path
              key={s.key}
              d={linePath}
              fill="none"
              stroke={s.color}
              strokeWidth="0.8"
              vectorEffect="non-scaling-stroke"
            />
          );
        })}
      </svg>
      <figcaption className="inv-detail-chart__labels">
        {data.map((d) => (
          <span key={d.label} className="inv-detail-chart__label">
            {d.label}
          </span>
        ))}
      </figcaption>
    </figure>
  );
}

export interface DonutChartProps {
  data: ChartDataPoint[];
  colors?: string[];
  ariaLabel: string;
}

const DEFAULT_DONUT_COLORS = [
  'var(--inv-gold)',
  '#c4a35a',
  '#8b7355',
  '#6b8e6b',
  '#4682b4',
  '#9370db',
  '#cd853f',
  '#708090',
];

export function DonutChart({
  data,
  colors = DEFAULT_DONUT_COLORS,
  ariaLabel,
}: DonutChartProps) {
  const total = data.reduce((s, d) => s + d.value, 0);
  if (total === 0) return null;

  let cumulative = 0;
  const segments = data.map((d, i) => {
    const start = cumulative;
    cumulative += d.value / total;
    return { ...d, start, end: cumulative, color: colors[i % colors.length] };
  });

  const summary = data.map((d) => `${d.label}: ${((d.value / total) * 100).toFixed(1)}%`).join('; ');

  return (
    <figure className="inv-portfolio-donut" role="figure" aria-label={ariaLabel}>
      <p className="inv-portfolio-chart__sr-summary">{summary}</p>
      <svg viewBox="0 0 100 100" className="inv-portfolio-donut__svg" aria-hidden="true">
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
          return <path key={seg.label} d={d} fill={seg.color} />;
        })}
      </svg>
      <ul className="inv-portfolio-donut__legend">
        {data.map((d, i) => (
          <li key={d.label}>
            <span className="inv-portfolio-donut__swatch" style={{ background: colors[i % colors.length] }} />
            <span>{d.label}</span>
            <strong>{((d.value / total) * 100).toFixed(1)}%</strong>
          </li>
        ))}
      </ul>
    </figure>
  );
}

export interface HorizontalBarChartProps {
  data: ChartDataPoint[];
  color?: string;
  ariaLabel: string;
  formatValue?: (value: number) => string;
}

export function HorizontalBarChart({
  data,
  color = 'var(--inv-gold)',
  ariaLabel,
  formatValue = (v) => v.toLocaleString(),
}: HorizontalBarChartProps) {
  const max = Math.max(...data.map((d) => d.value), 1);
  const summary = data.map((d) => `${d.label}: ${formatValue(d.value)}`).join('; ');

  return (
    <div className="inv-portfolio-hbar" role="img" aria-label={ariaLabel}>
      <p className="inv-portfolio-chart__sr-summary">{summary}</p>
      {data.map((d) => (
        <div key={d.label} className="inv-portfolio-hbar__row">
          <span className="inv-portfolio-hbar__label">{d.label}</span>
          <div className="inv-portfolio-hbar__track">
            <div
              className="inv-portfolio-hbar__fill"
              style={{ width: `${(d.value / max) * 100}%`, backgroundColor: color }}
            />
          </div>
          <span className="inv-portfolio-hbar__value">{formatValue(d.value)}</span>
        </div>
      ))}
    </div>
  );
}

export interface StackedBarChartProps {
  data: { label: string; segments: ChartDataPoint[] }[];
  colors?: string[];
  ariaLabel: string;
}

export function StackedBarChart({
  data,
  colors = DEFAULT_DONUT_COLORS,
  ariaLabel,
}: StackedBarChartProps) {
  const totals = data.map((d) => d.segments.reduce((s, seg) => s + seg.value, 0));
  const max = Math.max(...totals, 1);

  return (
    <div className="inv-portfolio-stacked" role="img" aria-label={ariaLabel}>
      {data.map((row) => {
        const total = row.segments.reduce((s, seg) => s + seg.value, 0);
        return (
          <div key={row.label} className="inv-portfolio-stacked__row">
            <span className="inv-portfolio-stacked__label">{row.label}</span>
            <div className="inv-portfolio-stacked__bar">
              {row.segments.map((seg, i) => (
                <div
                  key={seg.label}
                  className="inv-portfolio-stacked__segment"
                  style={{
                    width: total > 0 ? `${(seg.value / total) * (total / max) * 100}%` : '0%',
                    backgroundColor: colors[i % colors.length],
                  }}
                  title={`${seg.label}: ${seg.value.toLocaleString()}`}
                />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export interface WaterfallChartProps {
  data: ChartDataPoint[];
  ariaLabel: string;
  formatValue?: (value: number) => string;
}

export function WaterfallChart({
  data,
  ariaLabel,
  formatValue = (v) => v.toLocaleString(),
}: WaterfallChartProps) {
  const max = Math.max(...data.map((d) => Math.abs(d.value)), 1);

  return (
    <div className="inv-portfolio-waterfall" role="img" aria-label={ariaLabel}>
      {data.map((d) => (
        <div key={d.label} className="inv-portfolio-waterfall__item">
          <div className="inv-portfolio-waterfall__track">
            <div
              className={`inv-portfolio-waterfall__bar${d.value < 0 ? ' inv-portfolio-waterfall__bar--negative' : ''}`}
              style={{ height: `${(Math.abs(d.value) / max) * 100}%` }}
              title={`${d.label}: ${formatValue(d.value)}`}
            />
          </div>
          <span className="inv-portfolio-waterfall__label">{d.label}</span>
        </div>
      ))}
    </div>
  );
}
