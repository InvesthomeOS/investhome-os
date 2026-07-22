'use client';

import type { CashFlowProjection } from '../../_data/distribution-types';
import type { Distribution } from '../../_data/distribution-types';
import { computeProjections } from '../../_data/distribution-calculations';
import { formatInvestorCurrency } from '../../_data/mock-data';
import { HorizontalBarChart } from '../portfolio/chart-primitives';
import { SectionHeader } from '../section-header';

const PROBABILITY_LABELS: Record<CashFlowProjection['probability'], string> = {
  high: 'High confidence',
  medium: 'Medium confidence',
  low: 'Low confidence',
};

export interface ProjectionSectionProps {
  distributions: Distribution[];
  currency: string;
}

export function ProjectionSection({ distributions, currency }: ProjectionSectionProps) {
  const projections = computeProjections(distributions);
  const shortTerm = projections.slice(0, 2);
  const monthly = projections.slice(2, 14);
  const longTerm = projections.slice(14);

  const chartData = monthly.map((p) => ({ label: p.label, value: p.projectedNet }));

  return (
    <section className="inv-distributions__panel">
      <SectionHeader
        title="Projected Cash Flow"
        subtitle="Forward-looking estimates — not guaranteed. Mock projections for illustration."
      />

      <div className="inv-distributions__projection-grid">
        {shortTerm.map((p) => (
          <article key={p.period} className="inv-distributions__projection-card">
            <h3>{p.label}</h3>
            <strong>{formatInvestorCurrency(p.projectedNet, currency)}</strong>
            <span className="inv-distributions__projection-gross">
              Gross est. {formatInvestorCurrency(p.projectedGross, currency)}
            </span>
            <span className={`inv-distributions__probability inv-distributions__probability--${p.probability}`}>
              {PROBABILITY_LABELS[p.probability]}
            </span>
            <span className="inv-distributions__projection-meta">
              {p.investmentCount} investment{p.investmentCount !== 1 ? 's' : ''}
            </span>
          </article>
        ))}
      </div>

      <h3 className="inv-distributions__subheading">Next 12 Months</h3>
      <HorizontalBarChart
        data={chartData}
        ariaLabel="12-month projected cash flow chart"
        formatValue={(v) => formatInvestorCurrency(v, currency)}
      />

      <div className="inv-distributions__table-wrap">
        <table className="inv-distributions__table inv-distributions__table--compact">
          <thead>
            <tr>
              <th scope="col">Period</th>
              <th scope="col">Projected Net</th>
              <th scope="col">Projected Gross</th>
              <th scope="col">Confidence</th>
            </tr>
          </thead>
          <tbody>
            {monthly.map((p) => (
              <tr key={p.period}>
                <td>{p.label}</td>
                <td>{formatInvestorCurrency(p.projectedNet, currency)}</td>
                <td>{formatInvestorCurrency(p.projectedGross, currency)}</td>
                <td>
                  <span className={`inv-distributions__probability inv-distributions__probability--${p.probability}`}>
                    {PROBABILITY_LABELS[p.probability]}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 className="inv-distributions__subheading">Years 2–5</h3>
      <div className="inv-distributions__table-wrap">
        <table className="inv-distributions__table inv-distributions__table--compact">
          <thead>
            <tr>
              <th scope="col">Year</th>
              <th scope="col">Projected Net</th>
              <th scope="col">Confidence</th>
            </tr>
          </thead>
          <tbody>
            {longTerm.map((p) => (
              <tr key={p.period}>
                <td>{p.label}</td>
                <td>{formatInvestorCurrency(p.projectedNet, currency)}</td>
                <td>
                  <span className={`inv-distributions__probability inv-distributions__probability--${p.probability}`}>
                    {PROBABILITY_LABELS[p.probability]}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
