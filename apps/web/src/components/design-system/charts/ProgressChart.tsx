'use client';

import { ChartContainer, type ChartContainerState } from '@investhome/ui';

import { formatChartValue } from './format';

export interface ProgressChartProps {
  value: number;
  max?: number;
  ariaLabel: string;
  locale?: string;
  state?: ChartContainerState;
  title?: string;
  emptyTitle?: string;
  loadingLabel?: string;
  className?: string;
}

export function ProgressChart({
  value,
  max = 100,
  ariaLabel,
  locale = 'tr',
  state = 'ready',
  title,
  emptyTitle,
  loadingLabel,
  className,
}: ProgressChartProps) {
  const pct = max <= 0 ? 0 : Math.min(100, Math.max(0, (value / max) * 100));

  return (
    <ChartContainer
      title={title}
      state={state}
      ariaLabel={ariaLabel}
      emptyTitle={emptyTitle}
      loadingLabel={loadingLabel}
      className={className}
    >
      <div
        className="ds-chart--progress"
        role="progressbar"
        aria-label={ariaLabel}
        aria-valuenow={Math.round(pct)}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className="ds-chart--progress__track">
          <div className="ds-chart--progress__fill" style={{ width: `${pct}%` }} />
        </div>
        <p className="ds-type-caption" style={{ marginTop: 8 }}>
          {formatChartValue(pct / 100, 'percent', locale)}
        </p>
      </div>
    </ChartContainer>
  );
}
