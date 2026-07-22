'use client';

import Link from 'next/link';

import { metricDisplayValue } from './metric-display';
import type { ExecutiveMetric, LoadState } from './types';

export function ExecutiveKpiBar({
  title,
  metrics,
  state,
  labels,
  onRetry,
  retryLabel,
}: {
  title: string;
  metrics: ExecutiveMetric[];
  state: LoadState;
  labels: { unavailable: string; empty: string; loading: string };
  onRetry?: () => void;
  retryLabel: string;
}) {
  return (
    <section className="ecc-kpi" aria-label={title}>
      <div className="ecc-kpi__header">
        <h2 className="ecc-kpi__title">{title}</h2>
      </div>
      {state === 'error' && (
        <div className="leads__state leads__state--error">
          {onRetry && (
            <button type="button" className="leads__button leads__button--secondary" onClick={onRetry}>
              {retryLabel}
            </button>
          )}
        </div>
      )}
      <div className="ecc-kpi__grid">
        {metrics.map((metric) => {
          const display = metricDisplayValue(metric.state, metric.value, labels);
          const className = `ecc-kpi__card ecc-kpi__card--${metric.state}`;
          const body = (
            <>
              <p className="ecc-kpi__label">{metric.label}</p>
              <strong className="ecc-kpi__value">{display}</strong>
              {metric.hint && <span className="ecc-kpi__hint">{metric.hint}</span>}
            </>
          );
          if (metric.href && metric.state === 'ready') {
            return (
              <Link key={metric.key} href={metric.href} className={className}>
                {body}
              </Link>
            );
          }
          return (
            <div key={metric.key} className={className}>
              {body}
            </div>
          );
        })}
      </div>
    </section>
  );
}