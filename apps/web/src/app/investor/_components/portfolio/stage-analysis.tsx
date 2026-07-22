'use client';

import { SectionHeader } from '../section-header';
import type { StageAllocation } from '../../_data/portfolio-types';
import { formatInvestorCurrency, formatInvestorPercent } from '../../_data/mock-data';

export interface StageAnalysisProps {
  stages: StageAllocation[];
  currency: string;
}

export function StageAnalysis({ stages, currency }: StageAnalysisProps) {
  const maxValue = Math.max(...stages.map((s) => s.currentValue), 1);

  return (
    <section className="inv-portfolio-panel">
      <SectionHeader
        title="Project Stage Analysis"
        subtitle="Capital, value, and risk metrics by lifecycle stage"
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
                <dt>Investments</dt>
                <dd>{stage.count}</dd>
              </div>
              <div>
                <dt>Capital</dt>
                <dd>{formatInvestorCurrency(stage.investedCapital, currency)}</dd>
              </div>
              <div>
                <dt>Value</dt>
                <dd>{formatInvestorCurrency(stage.currentValue, currency)}</dd>
              </div>
              <div>
                <dt>Equity</dt>
                <dd>{formatInvestorCurrency(stage.equity, currency)}</dd>
              </div>
              <div>
                <dt>Avg ROI</dt>
                <dd>{formatInvestorPercent(stage.avgRoi)}</dd>
              </div>
              <div>
                <dt>Avg Risk</dt>
                <dd>{stage.avgRiskScore.toFixed(0)}</dd>
              </div>
            </dl>
          </article>
        ))}
      </div>
    </section>
  );
}
