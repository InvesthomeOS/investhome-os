'use client';

import type { ReactNode } from 'react';

import { Sparkline } from '@/components/design-system/charts';

export type CrmKpiSparkProps = {
  label: string;
  value: ReactNode;
  sparkValues: number[];
  ariaLabel: string;
  delta?: string;
  deltaTone?: 'up' | 'down' | 'neutral';
  hint?: string;
  className?: string;
};

/** Compact Attio-style KPI with inline sparkline — uses design-system Sparkline only. */
export function CrmKpiSpark({
  label,
  value,
  sparkValues,
  ariaLabel,
  delta,
  deltaTone = 'neutral',
  hint,
  className,
}: CrmKpiSparkProps) {
  return (
    <article className={`crm-g2-kpi${className ? ` ${className}` : ''}`}>
      <div className="crm-g2-kpi__head">
        <p className="crm-g2-kpi__label">{label}</p>
        {delta ? (
          <span className={`crm-g2-kpi__delta crm-g2-kpi__delta--${deltaTone}`}>{delta}</span>
        ) : null}
      </div>
      <div className="crm-g2-kpi__body">
        <strong className="crm-g2-kpi__value">{value}</strong>
        <Sparkline values={sparkValues} ariaLabel={ariaLabel} className="crm-g2-kpi__spark" />
      </div>
      {hint ? <p className="crm-g2-kpi__hint">{hint}</p> : null}
    </article>
  );
}
