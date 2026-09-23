'use client';

import {
  REPORTS_FUNNEL_COLORS,
  REPORTS_SOURCE_COLORS,
  type ReportsFunnelStage,
  type ReportsMonthlyPoint,
  type ReportsSourceSlice,
  type ReportsTrendPoint,
} from '../reports-model';

function sparkPoints(values: number[], width: number, height: number) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  return values
    .map((v, i) => {
      const x = (i / Math.max(values.length - 1, 1)) * width;
      const y = height - ((v - min) / range) * (height - 4) - 2;
      return `${x},${y}`;
    })
    .join(' ');
}

export function ReportSparkline({
  values,
  color,
  ariaLabel,
}: {
  values: number[];
  color: string;
  ariaLabel: string;
}) {
  const width = 96;
  const height = 28;
  const points = sparkPoints(values, width, height);

  return (
    <svg
      className="crm-reports__spark"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={ariaLabel}
    >
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

export function RevenueTrendChart({
  data,
  ariaLabel,
  currentLabel,
  previousLabel,
}: {
  data: ReportsTrendPoint[];
  ariaLabel: string;
  currentLabel: string;
  previousLabel: string;
}) {
  const width = 420;
  const height = 200;
  const pad = { t: 16, r: 12, b: 28, l: 36 };
  const values = data.flatMap((d) => [d.current, d.previous]);
  const max = Math.max(...values, 1);
  const innerW = width - pad.l - pad.r;
  const innerH = height - pad.t - pad.b;

  const toCoords = (getter: (d: ReportsTrendPoint) => number) =>
    data
      .map((d, i) => {
        const x = pad.l + (i / Math.max(data.length - 1, 1)) * innerW;
        const y = pad.t + (1 - getter(d) / max) * innerH;
        return `${x},${y}`;
      })
      .join(' ');

  const yTicks = [0, 0.25, 0.5, 0.75, 1];
  const summary = data
    .map((d) => `${d.label}: ${currentLabel} ${d.current}k, ${previousLabel} ${d.previous}k`)
    .join('; ');

  return (
    <figure className="crm-reports__chart" role="img" aria-label={ariaLabel}>
      <p className="sr-only">{summary}</p>
      <svg viewBox={`0 0 ${width} ${height}`} aria-hidden="true" preserveAspectRatio="xMidYMid meet">
        {yTicks.map((t) => {
          const y = pad.t + (1 - t) * innerH;
          return (
            <g key={t}>
              <line
                x1={pad.l}
                y1={y}
                x2={width - pad.r}
                y2={y}
                stroke="#e6eef1"
                strokeWidth="1"
              />
              <text x={pad.l - 6} y={y + 3} textAnchor="end" className="crm-reports__chart-axis">
                {`$${Math.round(max * t)}K`}
              </text>
            </g>
          );
        })}
        <polyline
          points={toCoords((d) => d.previous)}
          fill="none"
          stroke="#b7d4db"
          strokeWidth="2"
          strokeDasharray="4 3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <polyline
          points={toCoords((d) => d.current)}
          fill="none"
          stroke="#075b75"
          strokeWidth="2.25"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {data.map((d, i) => {
          const x = pad.l + (i / Math.max(data.length - 1, 1)) * innerW;
          return (
            <text
              key={d.label}
              x={x}
              y={height - 8}
              textAnchor="middle"
              className="crm-reports__chart-axis"
            >
              {d.label}
            </text>
          );
        })}
      </svg>
      <ul className="crm-reports__legend" aria-hidden="true">
        <li>
          <span className="crm-reports__legend-swatch is-current" />
          {currentLabel}
        </li>
        <li>
          <span className="crm-reports__legend-swatch is-previous" />
          {previousLabel}
        </li>
      </ul>
    </figure>
  );
}

export function OpportunityFunnel({
  stages,
  stageLabels,
  ariaLabel,
}: {
  stages: ReportsFunnelStage[];
  stageLabels: Record<string, string>;
  ariaLabel: string;
}) {
  const summary = stages
    .map((s) => `${stageLabels[s.key]}: ${s.valueLabel}, ${s.count}`)
    .join('; ');

  return (
    <figure className="crm-reports__funnel" role="img" aria-label={ariaLabel}>
      <p className="sr-only">{summary}</p>
      <ul>
        {stages.map((stage) => (
          <li key={stage.key}>
            <div
              className="crm-reports__funnel-bar"
              style={{
                width: `${stage.widthPct}%`,
                background: REPORTS_FUNNEL_COLORS[stage.key],
              }}
            >
              <span>{stageLabels[stage.key]}</span>
            </div>
            <div className="crm-reports__funnel-meta">
              <strong>{stage.valueLabel}</strong>
              <small>{stage.count}</small>
            </div>
          </li>
        ))}
      </ul>
    </figure>
  );
}

export function MonthlyComparisonChart({
  data,
  ariaLabel,
  currentLabel,
  previousLabel,
}: {
  data: ReportsMonthlyPoint[];
  ariaLabel: string;
  currentLabel: string;
  previousLabel: string;
}) {
  const width = 360;
  const height = 190;
  const pad = { t: 12, r: 8, b: 28, l: 32 };
  const max = Math.max(...data.flatMap((d) => [d.current, d.previous]), 1);
  const groupW = (width - pad.l - pad.r) / data.length;
  const barW = Math.min(14, groupW * 0.28);
  const summary = data
    .map((d) => `${d.label}: ${currentLabel} ${d.current}, ${previousLabel} ${d.previous}`)
    .join('; ');

  return (
    <figure className="crm-reports__chart" role="img" aria-label={ariaLabel}>
      <p className="sr-only">{summary}</p>
      <svg viewBox={`0 0 ${width} ${height}`} aria-hidden="true" preserveAspectRatio="xMidYMid meet">
        {[0, 0.5, 1].map((t) => {
          const y = pad.t + (1 - t) * (height - pad.t - pad.b);
          return (
            <line
              key={t}
              x1={pad.l}
              y1={y}
              x2={width - pad.r}
              y2={y}
              stroke="#e6eef1"
              strokeWidth="1"
            />
          );
        })}
        {data.map((d, i) => {
          const cx = pad.l + i * groupW + groupW / 2;
          const hCur = (d.current / max) * (height - pad.t - pad.b);
          const hPrev = (d.previous / max) * (height - pad.t - pad.b);
          return (
            <g key={d.label}>
              <rect
                x={cx - barW - 2}
                y={pad.t + (height - pad.t - pad.b - hPrev)}
                width={barW}
                height={hPrev}
                rx="2"
                fill="#b7d4db"
              />
              <rect
                x={cx + 2}
                y={pad.t + (height - pad.t - pad.b - hCur)}
                width={barW}
                height={hCur}
                rx="2"
                fill="#075b75"
              />
              <text
                x={cx}
                y={height - 8}
                textAnchor="middle"
                className="crm-reports__chart-axis"
              >
                {d.label}
              </text>
            </g>
          );
        })}
      </svg>
      <ul className="crm-reports__legend" aria-hidden="true">
        <li>
          <span className="crm-reports__legend-swatch is-current" />
          {currentLabel}
        </li>
        <li>
          <span className="crm-reports__legend-swatch is-previous" />
          {previousLabel}
        </li>
      </ul>
    </figure>
  );
}

export function SourceDonut({
  slices,
  labels,
  ariaLabel,
}: {
  slices: ReportsSourceSlice[];
  labels: Record<string, string>;
  ariaLabel: string;
}) {
  let cursor = 0;
  const stops = slices
    .map((slice) => {
      const start = cursor;
      cursor += slice.pct;
      return `${REPORTS_SOURCE_COLORS[slice.key]} ${start}% ${cursor}%`;
    })
    .join(', ');
  const summary = slices.map((s) => `${labels[s.key]} ${s.pct}%`).join('; ');

  return (
    <div className="crm-reports__distribution">
      <div
        className="crm-reports__donut"
        style={{ background: `conic-gradient(${stops})` }}
        role="img"
        aria-label={`${ariaLabel}. ${summary}`}
      >
        <span aria-hidden="true" />
      </div>
      <ul className="crm-reports__legend-list">
        {slices.map((slice) => (
          <li key={slice.key}>
            <span
              className="crm-reports__legend-dot"
              style={{ background: REPORTS_SOURCE_COLORS[slice.key] }}
              aria-hidden="true"
            />
            <span>{labels[slice.key]}</span>
            <strong>{slice.pct}%</strong>
          </li>
        ))}
      </ul>
    </div>
  );
}

const PETROL_SLICES = ['#075b75', '#58aebb', '#0a6f8a', '#9ec9d2', '#134a5c', '#b7d4db', '#2a7a8c', '#d5e6ea'];

export type ReportChartPoint = {
  key: string;
  label: string;
  count: number;
  href?: string | null;
};

export function CountBarChart({
  data,
  ariaLabel,
}: {
  data: ReportChartPoint[];
  ariaLabel: string;
}) {
  const width = 420;
  const height = 190;
  const pad = { t: 12, r: 8, b: data.length > 10 ? 42 : 36, l: 32 };
  const max = Math.max(...data.map((item) => item.count), 1);
  const groupW = data.length ? (width - pad.l - pad.r) / data.length : width;
  const barW = Math.min(22, Math.max(6, groupW * 0.46));
  const summary = data.map((item) => `${item.label}: ${item.count}`).join('; ');
  const labelStep = data.length > 10 ? Math.ceil(data.length / 8) : 1;

  return (
    <figure className="crm-reports__chart" role="img" aria-label={ariaLabel}>
      <p className="sr-only">{summary}</p>
      <svg viewBox={`0 0 ${width} ${height}`} aria-hidden="true" preserveAspectRatio="xMidYMid meet">
        {[0, 0.5, 1].map((tick) => {
          const y = pad.t + (1 - tick) * (height - pad.t - pad.b);
          return (
            <line key={tick} x1={pad.l} y1={y} x2={width - pad.r} y2={y} stroke="#e6eef1" strokeWidth="1" />
          );
        })}
        {data.map((item, index) => {
          const h = (item.count / max) * (height - pad.t - pad.b);
          const x = pad.l + index * groupW + (groupW - barW) / 2;
          const y = pad.t + (height - pad.t - pad.b - h);
          const showLabel = index % labelStep === 0 || index === data.length - 1;
          return (
            <g key={item.key}>
              <rect x={x} y={y} width={barW} height={Math.max(h, 1)} rx="2" fill="#075b75" />
              {showLabel ? (
                <text
                  x={x + barW / 2}
                  y={height - 10}
                  textAnchor="middle"
                  className="crm-reports__chart-axis"
                >
                  {item.label}
                </text>
              ) : null}
            </g>
          );
        })}
      </svg>
    </figure>
  );
}

export function SplitBarChart({
  data,
  ariaLabel,
  currentLabel,
  previousLabel,
}: {
  data: Array<{ key: string; label: string; current: number; previous: number }>;
  ariaLabel: string;
  currentLabel: string;
  previousLabel: string;
}) {
  const width = 420;
  const height = 190;
  const pad = { t: 12, r: 8, b: 36, l: 32 };
  const max = Math.max(...data.flatMap((item) => [item.current, item.previous]), 1);
  const groupW = data.length ? (width - pad.l - pad.r) / data.length : width;
  const barW = Math.min(12, Math.max(6, groupW * 0.28));

  return (
    <figure className="crm-reports__chart" role="img" aria-label={ariaLabel}>
      <svg viewBox={`0 0 ${width} ${height}`} aria-hidden="true" preserveAspectRatio="xMidYMid meet">
        {[0, 0.5, 1].map((tick) => {
          const y = pad.t + (1 - tick) * (height - pad.t - pad.b);
          return (
            <line key={tick} x1={pad.l} y1={y} x2={width - pad.r} y2={y} stroke="#e6eef1" strokeWidth="1" />
          );
        })}
        {data.map((item, index) => {
          const cx = pad.l + index * groupW + groupW / 2;
          const hPrev = (item.previous / max) * (height - pad.t - pad.b);
          const hCur = (item.current / max) * (height - pad.t - pad.b);
          return (
            <g key={item.key}>
              <rect
                x={cx - barW - 2}
                y={pad.t + (height - pad.t - pad.b - hPrev)}
                width={barW}
                height={Math.max(hPrev, 1)}
                rx="2"
                fill="#b7d4db"
              />
              <rect
                x={cx + 2}
                y={pad.t + (height - pad.t - pad.b - hCur)}
                width={barW}
                height={Math.max(hCur, 1)}
                rx="2"
                fill="#075b75"
              />
              <text x={cx} y={height - 10} textAnchor="middle" className="crm-reports__chart-axis">
                {item.label}
              </text>
            </g>
          );
        })}
      </svg>
      <ul className="crm-reports__legend" aria-hidden="true">
        <li>
          <span className="crm-reports__legend-swatch is-current" />
          {currentLabel}
        </li>
        <li>
          <span className="crm-reports__legend-swatch is-previous" />
          {previousLabel}
        </li>
      </ul>
    </figure>
  );
}

export function PetrolDonut({
  data,
  ariaLabel,
}: {
  data: ReportChartPoint[];
  ariaLabel: string;
}) {
  const total = data.reduce((sum, item) => sum + item.count, 0) || 1;
  let cursor = 0;
  const slices = data.map((item, index) => {
    const pct = (item.count / total) * 100;
    const start = cursor;
    cursor += pct;
    return { ...item, pct, color: PETROL_SLICES[index % PETROL_SLICES.length], start, end: cursor };
  });
  const summary = slices.map((item) => `${item.label} ${Math.round(item.pct)}%`).join('; ');
  const stops = slices.map((item) => `${item.color} ${item.start}% ${item.end}%`).join(', ');

  return (
    <div className="crm-reports__distribution">
      <div
        className="crm-reports__donut"
        style={{ background: `conic-gradient(${stops || '#e6eef1 0% 100%'})` }}
        role="img"
        aria-label={`${ariaLabel}. ${summary}`}
      >
        <span aria-hidden="true" />
      </div>
      <ul className="crm-reports__legend-list">
        {slices.map((item) => (
          <li key={item.key}>
            <span className="crm-reports__legend-dot" style={{ background: item.color }} aria-hidden="true" />
            <span>{item.label}</span>
            <strong>{item.count}</strong>
          </li>
        ))}
      </ul>
    </div>
  );
}
