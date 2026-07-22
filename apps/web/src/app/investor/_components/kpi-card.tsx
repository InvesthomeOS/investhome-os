import type { ReactNode } from 'react';

export interface InvestorKpiCardProps {
  label: string;
  value: ReactNode;
  delta?: string;
  meta?: string;
  className?: string;
}

export function InvestorKpiCard({
  label,
  value,
  delta,
  meta,
  className,
}: InvestorKpiCardProps) {
  return (
    <article className={`inv-kpi-card${className ? ` ${className}` : ''}`}>
      <p className="inv-kpi-card__label">{label}</p>
      <strong className="inv-kpi-card__value">{value}</strong>
      {delta ? <span className="inv-kpi-card__delta">{delta}</span> : null}
      {meta ? <span className="inv-kpi-card__meta">{meta}</span> : null}
    </article>
  );
}
