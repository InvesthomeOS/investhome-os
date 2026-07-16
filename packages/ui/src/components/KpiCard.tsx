import type { ReactNode } from 'react';

export interface KpiCardProps {
  label: string;
  value: ReactNode;
  delta?: string;
  className?: string;
}

export function KpiCard({ label, value, delta, className }: KpiCardProps) {
  return (
    <article className={`ih-kpi-card${className ? ` ${className}` : ''}`}>
      <p className="ih-kpi-card__label">{label}</p>
      <strong className="ih-kpi-card__value">{value}</strong>
      {delta ? <span className="ih-kpi-card__delta">{delta}</span> : null}
    </article>
  );
}
