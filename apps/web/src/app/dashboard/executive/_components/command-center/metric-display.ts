'use client';

import type { MetricDisplayState } from './types';

export function metricDisplayValue(
  state: MetricDisplayState,
  value: string | null,
  labels: { unavailable: string; empty: string; loading: string },
): string {
  if (state === 'loading') return labels.loading;
  if (state === 'unavailable') return labels.unavailable;
  if (state === 'empty' || value === null || value === '') return labels.empty;
  if (state === 'error') return labels.unavailable;
  return value;
}