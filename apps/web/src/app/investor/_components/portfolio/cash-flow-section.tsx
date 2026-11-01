'use client';

import { investorChrome } from '@/app/investor/_components/investor-labels';

import { useTranslations } from 'next-intl';

import { MultiLineChart } from './chart-primitives';
import { SectionHeader } from '../section-header';
import type { PortfolioCashFlowSummary } from '../../_data/portfolio-types';
import { formatInvestorCurrency } from '../../_data/mock-data';

export interface CashFlowSectionProps {
  cashFlow: PortfolioCashFlowSummary;
  currency: string;
}

export function CashFlowSection({ cashFlow, currency }: CashFlowSectionProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const trendData = cashFlow.trend.map((m) => ({
    label: m.label,
    actual: m.actual,
    projected: m.projected,
  }));

  return (
    <section className="inv-portfolio-panel">
      <SectionHeader
        title={tChrome('k4d78e9f9ed')}
        subtitle={tChrome('k087d68d074')}
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

      <h3 className="inv-portfolio-subheading">{tChrome('k45e839d674')}</h3>
      <div className="inv-portfolio-table-wrap">
        <table className="inv-portfolio-table">
          <thead>
            <tr>
              <th scope="col">{tChrome('k0401729c31')}</th>
              <th scope="col">{tChrome('k0930f3f899')}</th>
              <th scope="col">{tChrome('k677951c6b1')}</th>
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

      <h3 className="inv-portfolio-subheading">{tChrome('k62cb42c7f9')}</h3>
      <div className="inv-portfolio-table-wrap">
        <table className="inv-portfolio-table">
          <thead>
            <tr>
              <th scope="col">{tChrome('k082bc378cd')}</th>
              <th scope="col">{tChrome('k204be1a53a')}</th>
            </tr>
          </thead>
          <tbody>
            {cashFlow.nextTwelveMonths.map((m) => (
              <tr key={m.date}>
                <td>{investorChrome(tChrome, m.label)}</td>
                <td>{formatInvestorCurrency(m.projected, currency)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
