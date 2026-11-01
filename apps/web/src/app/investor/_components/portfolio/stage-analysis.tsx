'use client';

import { useTranslations } from 'next-intl';

import { SectionHeader } from '../section-header';
import type { StageAllocation } from '../../_data/portfolio-types';
import { formatInvestorCurrency, formatInvestorPercent } from '../../_data/mock-data';

export interface StageAnalysisProps {
  stages: StageAllocation[];
  currency: string;
}

export function StageAnalysis({ stages, currency }: StageAnalysisProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const maxValue = Math.max(...stages.map((s) => s.currentValue), 1);

  return (
    <section className="inv-portfolio-panel">
      <SectionHeader
        title={tChrome('k3195375b12')}
        subtitle={tChrome('k7fb64386b4')}
      />
      <div className="inv-portfolio-stage-grid">
        {stages.map((stage) => (
          <article key={stage.stage} className="inv-portfolio-stage-card">
            <h3 className="inv-portfolio-stage-card__title">{stage.label}</h3>
            <div className="inv-portfolio-stage-card__bar">
              <div
                className="inv-portfolio-stage-card__bar-fill"
                style={{ width: `${(stage.currentValue / maxValue) * 100}%` }}
              />
            </div>
            <dl className="inv-portfolio-stage-card__stats">
              <div>
                <dt>{tChrome('k5de64aff09')}</dt>
                <dd>{stage.count}</dd>
              </div>
              <div>
                <dt>{tChrome('k2bd8d2658c')}</dt>
                <dd>{formatInvestorCurrency(stage.investedCapital, currency)}</dd>
              </div>
              <div>
                <dt>{tChrome('k8dce170de2')}</dt>
                <dd>{formatInvestorCurrency(stage.currentValue, currency)}</dd>
              </div>
              <div>
                <dt>{tChrome('k0786ff3b19')}</dt>
                <dd>{formatInvestorCurrency(stage.equity, currency)}</dd>
              </div>
              <div>
                <dt>{tChrome('ke6cf1d69cc')}</dt>
                <dd>{formatInvestorPercent(stage.avgRoi)}</dd>
              </div>
              <div>
                <dt>{tChrome('k68e9782e45')}</dt>
                <dd>{stage.avgRiskScore.toFixed(0)}</dd>
              </div>
            </dl>
          </article>
        ))}
      </div>
    </section>
  );
}
