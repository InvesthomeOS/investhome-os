'use client';

/**
 * Re-exports existing SVG chart primitives — no new chart library (P9).
 */
export {
  DonutChart,
  HorizontalBarChart,
  MultiLineChart,
  StackedBarChart,
  type ChartSeries,
  type MultiSeriesPoint,
} from '@/app/investor/_components/portfolio/chart-primitives';

export function BiAreaPlaceholder({
  points,
  ariaLabel,
}: {
  points: Array<{ label: string; value: number }>;
  ariaLabel: string;
}) {
  // Area is rendered via MultiLineChart fill path semantics when series available
  if (points.length === 0) return null;
  const max = Math.max(...points.map((p) => p.value), 1);
  const width = 320;
  const height = 120;
  const coords = points
    .map((p, i) => {
      const x = (i / Math.max(points.length - 1, 1)) * (width - 16) + 8;
      const y = height - 12 - (p.value / max) * (height - 28);
      return `${x},${y}`;
    })
    .join(' ');
  const area = `8,${height - 12} ${coords} ${width - 8},${height - 12}`;

  return (
    <figure className="bi-chart" role="figure" aria-label={ariaLabel}>
      <svg viewBox={`0 0 ${width} ${height}`} className="bi-chart__svg" width="100%" height={height}>
        <polygon points={area} className="bi-chart__area" />
        <polyline points={coords} className="bi-chart__line" fill="none" />
      </svg>
      <figcaption className="bi-chart__labels">
        {points.map((p) => (
          <span key={p.label}>{p.label}</span>
        ))}
      </figcaption>
    </figure>
  );
}

export function BiFunnel({
  stages,
}: {
  stages: Array<{ label: string; value: number | null; state: string }>;
}) {
  const max = Math.max(...stages.map((s) => s.value ?? 0), 1);
  return (
    <div className="bi-funnel" role="list">
      {stages.map((stage, index) => {
        const widthPct = stage.value == null ? 20 : Math.max(18, (stage.value / max) * 100);
        return (
          <div key={`${stage.label}-${index}`} className="bi-funnel__row" role="listitem">
            <span className="bi-funnel__label">{stage.label}</span>
            <div className="bi-funnel__bar-track">
              <div
                className={`bi-funnel__bar bi-funnel__bar--${stage.state}`}
                style={{ width: `${widthPct}%` }}
              />
            </div>
            <span className="bi-funnel__value">
              {stage.state === 'unavailable' || stage.value == null ? '—' : stage.value}
            </span>
          </div>
        );
      })}
    </div>
  );
}
