import type { ReactNode } from 'react';

export type MetricSize = 'large' | 'medium';
export type MetricTrend = 'up' | 'down' | 'neutral';

export interface MetricCardProps {
  label: string;
  value?: ReactNode;
  trend?: MetricTrend;
  trendLabel?: string;
  hint?: string;
  icon?: ReactNode;
  size?: MetricSize;
  loading?: boolean;
  empty?: boolean;
  emptyLabel?: string;
  error?: boolean;
  errorLabel?: string;
  className?: string;
  href?: string;
}

export function MetricCard({
  label,
  value,
  trend,
  trendLabel,
  hint,
  icon,
  size = 'large',
  loading = false,
  empty = false,
  emptyLabel = '—',
  error = false,
  errorLabel,
  className,
  href,
}: MetricCardProps) {
  const classes = [
    'ds-metric-card',
    loading ? 'ds-metric-card--loading' : '',
    error ? 'ds-metric-card--error' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  const body = (
    <>
      <div className="ds-metric-card__top">
        <p className="ds-metric-card__label">{label}</p>
        {icon ? <span className="ds-metric-card__icon">{icon}</span> : null}
      </div>
      {loading ? (
        <span className="ds-metric-card__skeleton" aria-hidden="true" />
      ) : error ? (
        <strong className="ds-metric-card__value ds-metric-card__value--medium" role="alert">
          {errorLabel ?? 'Error'}
        </strong>
      ) : empty ? (
        <strong
          className={`ds-metric-card__value${size === 'medium' ? ' ds-metric-card__value--medium' : ''}`}
        >
          {emptyLabel}
        </strong>
      ) : (
        <strong
          className={`ds-metric-card__value${size === 'medium' ? ' ds-metric-card__value--medium' : ''}`}
        >
          {value}
        </strong>
      )}
      {trend && trendLabel && !loading && !error ? (
        <span className={`ds-trend ds-trend--${trend}`}>
          <span className="ds-trend__arrow" aria-hidden="true">
            {trend === 'up' ? '▲' : trend === 'down' ? '▼' : '•'}
          </span>
          {trendLabel}
        </span>
      ) : null}
      {hint && !loading ? <span className="ds-metric-card__hint">{hint}</span> : null}
    </>
  );

  if (href) {
    return (
      <a href={href} className={`${classes} ds-metric-card--link`}>
        {body}
      </a>
    );
  }

  return (
    <article className={classes} aria-busy={loading || undefined}>
      {body}
    </article>
  );
}
