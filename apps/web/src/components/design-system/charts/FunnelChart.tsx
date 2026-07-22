'use client';

import { ChartContainer, type ChartContainerState } from '@investhome/ui';

import { BiFunnel } from '@/components/analytics/bi-charts';

import { formatChartValue, type ChartNumberFormat } from './format';

export interface FunnelStage {
  label: string;
  value: number | null;
  state?: 'ready' | 'unavailable';
}

export interface FunnelChartProps {
  stages: FunnelStage[];
  ariaLabel: string;
  locale?: string;
  format?: ChartNumberFormat;
  state?: ChartContainerState;
  title?: string;
  emptyTitle?: string;
  loadingLabel?: string;
  className?: string;
}

/** Wraps existing BiFunnel — no second chart library. */
export function FunnelChart({
  stages,
  ariaLabel,
  locale = 'tr',
  format = 'number',
  state,
  title,
  emptyTitle,
  loadingLabel,
  className,
}: FunnelChartProps) {
  const resolvedState: ChartContainerState =
    state ?? (stages.length === 0 ? 'empty' : 'ready');
  const summary = stages
    .map((s) =>
      s.value == null
        ? `${s.label}: —`
        : `${s.label}: ${formatChartValue(s.value, format, locale)}`,
    )
    .join('; ');

  return (
    <ChartContainer
      title={title}
      state={resolvedState}
      ariaLabel={ariaLabel}
      emptyTitle={emptyTitle}
      loadingLabel={loadingLabel}
      className={className}
    >
      <div role="group" aria-label={ariaLabel}>
        <p className="sr-only">{summary}</p>
        <BiFunnel
          stages={stages.map((s) => ({
            label: s.label,
            value: s.value,
            state: s.state ?? (s.value == null ? 'unavailable' : 'ready'),
          }))}
        />
      </div>
    </ChartContainer>
  );
}
