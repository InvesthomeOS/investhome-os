import type { ReactNode } from 'react';

export type KpiTone = 'default' | 'gold' | 'success' | 'warning' | 'danger' | 'info';
export type KpiEmphasis = 'primary' | 'secondary';

export interface KpiCardProps {
  label: string;
  value: ReactNode;
  delta?: string;
  deltaTone?: 'up' | 'down' | 'neutral';
  hint?: string;
  icon?: ReactNode;
  href?: string;
  tone?: KpiTone;
  emphasis?: KpiEmphasis;
  className?: string;
  loading?: boolean;
}

export function KpiCard({
  label,
  value,
  delta,
  deltaTone = 'neutral',
  hint,
  icon,
  href,
  tone = 'default',
  emphasis = 'primary',
  className,
  loading,
}: KpiCardProps) {
  const classes = [
    'ih-kpi-card',
    tone !== 'default' ? `ih-kpi-card--${tone}` : '',
    emphasis === 'secondary' ? 'ih-kpi-card--secondary' : 'ih-kpi-card--primary',
    loading ? 'ih-kpi-card--loading' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  const body = (
    <>
      <div className="ih-kpi-card__top">
        <p className="ih-kpi-card__label">{label}</p>
        {icon ? <span className="ih-kpi-card__icon">{icon}</span> : null}
      </div>
      {loading ? (
        <span className="ih-skeleton ih-kpi-card__skeleton" aria-hidden="true" />
      ) : (
        <strong className="ih-kpi-card__value">{value}</strong>
      )}
      {delta ? (
        <span className={`ih-kpi-card__delta ih-kpi-card__delta--${deltaTone}`}>{delta}</span>
      ) : null}
      {hint ? <span className="ih-kpi-card__hint">{hint}</span> : null}
    </>
  );

  if (href) {
    return (
      <a href={href} className={`${classes} ih-kpi-card--link`}>
        {body}
      </a>
    );
  }

  return <article className={classes}>{body}</article>;
}
