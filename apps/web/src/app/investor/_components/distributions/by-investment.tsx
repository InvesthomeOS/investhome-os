'use client';

import Link from 'next/link';
import type { Route } from 'next';

import type { Distribution } from '../../_data/distribution-types';
import { computeCashFlowByInvestment } from '../../_data/distribution-calculations';
import { formatInvestorCurrency, formatInvestorDate } from '../../_data/mock-data';
import { HorizontalBarChart } from '../portfolio/chart-primitives';
import { SectionHeader } from '../section-header';

export interface CashFlowByInvestmentProps {
  distributions: Distribution[];
}

export function CashFlowByInvestment({ distributions }: CashFlowByInvestmentProps) {
  const rows = computeCashFlowByInvestment(distributions);
  const currency = rows[0]?.currency ?? 'USD';
  const chartData = rows.slice(0, 8).map((r) => ({ label: r.investmentName, value: r.netTotal }));

  return (
    <section className="inv-distributions__panel">
      <SectionHeader title="Cash Flow by Investment" subtitle="Cumulative net distributions per holding" />

      <HorizontalBarChart
        data={chartData}
        ariaLabel="Cash flow by investment chart"
        formatValue={(v) => formatInvestorCurrency(v, currency)}
      />

      <div className="inv-distributions__table-wrap">
        <table className="inv-distributions__table">
          <thead>
            <tr>
              <th scope="col">Investment</th>
              <th scope="col">Gross</th>
              <th scope="col">Net</th>
              <th scope="col">Preferred</th>
              <th scope="col">ROC</th>
              <th scope="col">Count</th>
              <th scope="col">Last Payment</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.investmentId}>
                <td>
                  <Link
                    href={`/investor/investments/${r.investmentId}` as Route}
                    className="inv-distributions__link"
                  >
                    {r.investmentName}
                  </Link>
                </td>
                <td>{formatInvestorCurrency(r.grossTotal, r.currency)}</td>
                <td>{formatInvestorCurrency(r.netTotal, r.currency)}</td>
                <td>{formatInvestorCurrency(r.preferredReturn, r.currency)}</td>
                <td>{formatInvestorCurrency(r.returnOfCapital, r.currency)}</td>
                <td>{r.distributionCount}</td>
                <td>{r.lastPaymentDate ? formatInvestorDate(r.lastPaymentDate) : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
