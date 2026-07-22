'use client';

import { MultiLineChart } from './chart-primitives';
import { SectionHeader } from '../section-header';
import type { PortfolioCashFlowSummary } from '../../_data/portfolio-types';
import { formatInvestorCurrency } from '../../_data/mock-data';

export interface CashFlowSectionProps {
  cashFlow: PortfolioCashFlowSummary;
  currency: string;
}

export function CashFlowSection({ cashFlow, currency }: CashFlowSectionProps) {
  const trendData = cashFlow.trend.map((m) => ({
    label: m.label,
    actual: m.actual,
    projected: m.projected,
  }));

  return (
    <section className="inv-portfolio-panel">
      <SectionHeader
        title="Cash Flow"
        subtitle="Historical distributions and 12-month projection"
      />
      <MultiLineChart
        data={trendData}
        series={[
          { key: 'actual', label: 'Actual', color: 'var(--inv-gold)' },
          { key: 'projected', label: 'Projected', color: '#c4a35a' },
        ]}
        ariaLabel="Cash flow trend chart"
        formatValue={(v) => formatInvestorCurrency(v, currency)}
      />

      <h3 className="inv-portfolio-subheading">By Investment</h3>
      <div className="inv-portfolio-table-wrap">
        <table className="inv-portfolio-table">
          <thead>
            <tr>
              <th scope="col">Investment</th>
              <th scope="col">Annual</th>
              <th scope="col">Monthly Avg</th>
            </tr>
          </thead>
          <tbody>
            {cashFlow.byInvestment.map((row) => (
              <tr key={row.id}>
                <td>{row.projectName}</td>
                <td>{formatInvestorCurrency(row.annualCashFlow, currency)}</td>
                <td>{formatInvestorCurrency(row.monthlyAverage, currency)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 className="inv-portfolio-subheading">Next 12 Months (Projected)</h3>
      <div className="inv-portfolio-table-wrap">
        <table className="inv-portfolio-table">
          <thead>
            <tr>
              <th scope="col">Month</th>
              <th scope="col">Projected</th>
            </tr>
          </thead>
          <tbody>
            {cashFlow.nextTwelveMonths.map((m) => (
              <tr key={m.date}>
                <td>{m.label}</td>
                <td>{formatInvestorCurrency(m.projected, currency)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
