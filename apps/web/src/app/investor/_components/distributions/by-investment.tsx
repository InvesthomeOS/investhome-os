'use client';

import { useTranslations } from 'next-intl';

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
  const tChrome = useTranslations('investorPortal.chrome');
  const rows = computeCashFlowByInvestment(distributions);
  const currency = rows[0]?.currency ?? 'USD';
  const chartData = rows.slice(0, 8).map((r) => ({ label: r.investmentName, value: r.netTotal }));

  return (
    <section className="inv-distributions__panel">
      <SectionHeader title={tChrome('k1d493b523d')} subtitle={tChrome('k555d12a122')} />

      <HorizontalBarChart
        data={chartData}
        ariaLabel="Cash flow by investment chart"
        formatValue={(v) => formatInvestorCurrency(v, currency)}
      />

      <div className="inv-distributions__table-wrap">
        <table className="inv-distributions__table">
          <thead>
            <tr>
              <th scope="col">{tChrome('k0401729c31')}</th>
              <th scope="col">{tChrome('k9580a6176f')}</th>
              <th scope="col">{tChrome('k9bb81c2ecc')}</th>
              <th scope="col">{tChrome('k0a3e0d9cf2')}</th>
              <th scope="col">{tChrome('k3027a4a390')}</th>
              <th scope="col">{tChrome('k66e12969c2')}</th>
              <th scope="col">{tChrome('kcec3d948d9')}</th>
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
