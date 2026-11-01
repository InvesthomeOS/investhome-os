'use client';

import { useTranslations } from 'next-intl';

import { WaterfallChart } from './chart-primitives';
import { SectionHeader } from '../section-header';
import type { ReturnAttributionItem } from '../../_data/portfolio-types';
import { formatInvestorCurrency } from '../../_data/mock-data';

export interface ReturnAttributionProps {
  items: ReturnAttributionItem[];
  currency: string;
}

export function ReturnAttribution({ items, currency }: ReturnAttributionProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const chartData = items.slice(0, 8).map((item) => ({
    label: item.label.length > 12 ? `${item.label.slice(0, 12)}…` : item.label,
    value: item.contribution,
  }));

  return (
    <section className="inv-portfolio-panel">
      <SectionHeader
        title={tChrome('kdfef9ed146')}
        subtitle={tChrome('k7b2ab80e6d')}
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
              <th scope="col">{tChrome('k0401729c31')}</th>
              <th scope="col">{tChrome('k982d5a7346')}</th>
              <th scope="col">{tChrome('ke5dded70cb')}</th>
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
