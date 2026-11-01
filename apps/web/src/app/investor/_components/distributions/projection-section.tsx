'use client';

import { investorChrome } from '@/app/investor/_components/investor-labels';

import { useTranslations } from 'next-intl';

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
  const tChrome = useTranslations('investorPortal.chrome');
  const projections = computeProjections(distributions);
  const shortTerm = projections.slice(0, 2);
  const monthly = projections.slice(2, 14);
  const longTerm = projections.slice(14);

  const chartData = monthly.map((p) => ({ label: p.label, value: p.projectedNet }));

  return (
    <section className="inv-distributions__panel">
      <SectionHeader
        title={tChrome('k3b1268677e')}
        subtitle={tChrome('kcd6c74a00c')}
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
              {investorChrome(tChrome, PROBABILITY_LABELS[p.probability])}
            </span>
            <span className="inv-distributions__projection-meta">
              {p.investmentCount} investment{p.investmentCount !== 1 ? 's' : ''}
            </span>
          </article>
        ))}
      </div>

      <h3 className="inv-distributions__subheading">{tChrome('k8c0a44bf15')}</h3>
      <HorizontalBarChart
        data={chartData}
        ariaLabel="12-month projected cash flow chart"
        formatValue={(v) => formatInvestorCurrency(v, currency)}
      />

      <div className="inv-distributions__table-wrap">
        <table className="inv-distributions__table inv-distributions__table--compact">
          <thead>
            <tr>
              <th scope="col">{tChrome('k170a28a9db')}</th>
              <th scope="col">{tChrome('k27ade0f901')}</th>
              <th scope="col">{tChrome('k3ab71dbc78')}</th>
              <th scope="col">{tChrome('k82fa7d52c8')}</th>
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
                    {investorChrome(tChrome, PROBABILITY_LABELS[p.probability])}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 className="inv-distributions__subheading">{tChrome('k1f0d817ed1')}</h3>
      <div className="inv-distributions__table-wrap">
        <table className="inv-distributions__table inv-distributions__table--compact">
          <thead>
            <tr>
              <th scope="col">{tChrome('k879e32326c')}</th>
              <th scope="col">{tChrome('k27ade0f901')}</th>
              <th scope="col">{tChrome('k82fa7d52c8')}</th>
            </tr>
          </thead>
          <tbody>
            {longTerm.map((p) => (
              <tr key={p.period}>
                <td>{p.label}</td>
                <td>{formatInvestorCurrency(p.projectedNet, currency)}</td>
                <td>
                  <span className={`inv-distributions__probability inv-distributions__probability--${p.probability}`}>
                    {investorChrome(tChrome, PROBABILITY_LABELS[p.probability])}
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
