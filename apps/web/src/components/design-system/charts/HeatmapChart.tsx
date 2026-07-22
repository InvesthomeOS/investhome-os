'use client';

import { ChartContainer, type ChartContainerState } from '@investhome/ui';

export interface HeatmapCell {
  x: number;
  y: number;
  value: number;
}

export interface HeatmapChartProps {
  cells: HeatmapCell[];
  columns: number;
  rows: number;
  ariaLabel: string;
  state?: ChartContainerState;
  title?: string;
  emptyTitle?: string;
  loadingLabel?: string;
  className?: string;
}

/** Lightweight intensity grid — supported when cells provided; no 3D / decorative noise. */
export function HeatmapChart({
  cells,
  columns,
  rows,
  ariaLabel,
  state,
  title,
  emptyTitle,
  loadingLabel,
  className,
}: HeatmapChartProps) {
  const resolvedState: ChartContainerState =
    state ?? (cells.length === 0 ? 'empty' : 'ready');
  const max = Math.max(...cells.map((c) => c.value), 1);
  const lookup = new Map(cells.map((c) => [`${c.x}:${c.y}`, c.value]));

  return (
    <ChartContainer
      title={title}
      state={resolvedState}
      ariaLabel={ariaLabel}
      emptyTitle={emptyTitle}
      loadingLabel={loadingLabel}
      className={className}
    >
      <div
        className="ds-chart--heatmap"
        role="img"
        aria-label={ariaLabel}
        style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}
      >
        {Array.from({ length: rows * columns }, (_, index) => {
          const x = index % columns;
          const y = Math.floor(index / columns);
          const value = lookup.get(`${x}:${y}`) ?? 0;
          const intensity = value / max;
          return (
            <div
              key={`${x}-${y}`}
              className="ds-chart--heatmap__cell"
              title={`${x},${y}: ${value}`}
              style={{
                background: `color-mix(in srgb, var(--brand-primary) ${Math.round(intensity * 85)}%, var(--surface-subtle))`,
              }}
            />
          );
        })}
      </div>
    </ChartContainer>
  );
}
