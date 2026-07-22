'use client';

import { WaterfallChart } from './chart-primitives';
import { SectionHeader } from '../section-header';
import type { ReturnAttributionItem } from '../../_data/portfolio-types';
import { formatInvestorCurrency } from '../../_data/mock-data';

export interface ReturnAttributionProps {
  items: ReturnAttributionItem[];
  currency: string;
}

export function ReturnAttribution({ items, currency }: ReturnAttributionProps) {
  const chartData = items.slice(0, 8).map((item) => ({
    label: item.label.length > 12 ? `${item.label.slice(0, 12)}…` : item.label,
    value: item.contribution,
  }));

  return (
    <section className="inv-portfolio-panel">
      <SectionHeader
        title="Return Attribution"
        subtitle="Contribution to total portfolio gain by investment"
      />
      <WaterfallChart
        data={chartData}
        ariaLabel="Return attribution waterfall chart"
        formatValue={(v) => formatInvestorCurrency(v, currency)}
      />
      <div className="inv-portfolio-table-wrap">
        <table className="inv-portfolio-table">
          <thead>
            <tr>
              <th scope="col">Investment</th>
              <th scope="col">Contribution</th>
              <th scope="col">% of Total</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{item.label}</td>
                <td>{formatInvestorCurrency(item.contribution, currency)}</td>
                <td>{item.percentOfTotal.toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
