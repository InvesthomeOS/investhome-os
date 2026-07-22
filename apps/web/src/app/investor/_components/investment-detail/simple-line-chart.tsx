'use client';

import type { ChartDataPoint } from '../../_data/investment-detail-types';

export interface SimpleLineChartProps {
  data: ChartDataPoint[];
  color?: string;
  height?: number;
  ariaLabel: string;
  formatValue?: (value: number) => string;
}

export function SimpleLineChart({
  data,
  color = 'var(--inv-gold)',
  height = 160,
  ariaLabel,
  formatValue = (v) => v.toLocaleString(),
}: SimpleLineChartProps) {
  if (data.length === 0) return null;

  const width = 100;
  const padding = { top: 8, right: 4, bottom: 24, left: 4 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const values = data.map((d) => d.value);
  const min = Math.min(...values) * 0.95;
  const max = Math.max(...values) * 1.05;
  const range = max - min || 1;

  const points = data.map((d, i) => {
    const x = padding.left + (i / Math.max(data.length - 1, 1)) * chartW;
    const y = padding.top + chartH - ((d.value - min) / range) * chartH;
    return { x, y, ...d };
  });

  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
  const areaPath = `${linePath} L ${points[points.length - 1]?.x ?? 0} ${padding.top + chartH} L ${points[0]?.x ?? 0} ${padding.top + chartH} Z`;

  return (
    <figure className="inv-detail-chart" role="figure" aria-label={ariaLabel}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="inv-detail-chart__svg"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id={`chart-grad-${ariaLabel.replace(/\s/g, '')}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.25" />
            <stop offset="100%" stopColor={color} stopOpacity="0.02" />
          </linearGradient>
        </defs>
        <path d={areaPath} fill={`url(#chart-grad-${ariaLabel.replace(/\s/g, '')})`} />
        <path d={linePath} fill="none" stroke={color} strokeWidth="0.8" vectorEffect="non-scaling-stroke" />
        {points.map((p) => (
          <circle key={p.label} cx={p.x} cy={p.y} r="1.2" fill={color} />
        ))}
      </svg>
      <figcaption className="inv-detail-chart__labels">
        {data.map((d) => (
          <span key={d.label} className="inv-detail-chart__label" title={formatValue(d.value)}>
            {d.label}
          </span>
        ))}
      </figcaption>
    </figure>
  );
}

export interface SimpleBarChartProps {
  data: ChartDataPoint[];
  color?: string;
  ariaLabel: string;
}

export function SimpleBarChart({
  data,
  color = 'var(--inv-gold)',
  ariaLabel,
}: SimpleBarChartProps) {
  const max = Math.max(...data.map((d) => d.value), 1);

  return (
    <div className="inv-detail-bar-chart" role="img" aria-label={ariaLabel}>
      {data.map((d) => (
        <div key={d.label} className="inv-detail-bar-chart__item">
          <div className="inv-detail-bar-chart__track">
            <div
              className="inv-detail-bar-chart__bar"
              style={{ height: `${(d.value / max) * 100}%`, backgroundColor: color }}
              title={`${d.label}: ${d.value.toLocaleString()}`}
            />
          </div>
          <span className="inv-detail-bar-chart__label">{d.label}</span>
        </div>
      ))}
    </div>
  );
}
