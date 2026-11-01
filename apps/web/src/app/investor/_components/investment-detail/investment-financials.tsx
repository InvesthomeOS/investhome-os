'use client';

import { investorChrome } from '@/app/investor/_components/investor-labels';

import { useTranslations } from 'next-intl';
import type { InvestmentDetail } from '../../_data/investment-detail-types';
import { formatInvestorCurrency } from '../../_data/mock-data';
import { SectionHeader } from '../section-header';
import { CapitalStructureCard } from './capital-structure-card';
import { SimpleLineChart } from './simple-line-chart';

export interface InvestmentFinancialsProps {
  detail: InvestmentDetail;
}

export function InvestmentFinancialsSection({ detail }: InvestmentFinancialsProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const { financials, investment: inv } = detail;
  const fmt = (v: number) => formatInvestorCurrency(v, inv.currency);

  return (
    <div className="inv-detail-financials">
      <section className="inv-detail-panel" aria-labelledby="charts-heading">
        <SectionHeader title={tChrome('k655e70a452')} subtitle={tChrome('k5d6824e9a8')} />
        <div className="inv-detail-financials__charts">
          <div className="inv-detail-financials__chart-card">
            <h3 className="inv-detail-financials__chart-title">{tChrome('kba697100ae')}</h3>
            <SimpleLineChart
              data={financials.investmentGrowth}
              ariaLabel="Investment growth over time"
              formatValue={fmt}
            />
          </div>
          <div className="inv-detail-financials__chart-card">
            <h3 className="inv-detail-financials__chart-title">{tChrome('kc094d10c09')}</h3>
            <SimpleLineChart
              data={financials.equityGrowth}
              color="#228b22"
              ariaLabel="Equity growth over time"
              formatValue={fmt}
            />
          </div>
          <div className="inv-detail-financials__chart-card">
            <h3 className="inv-detail-financials__chart-title">{tChrome('k4d78e9f9ed')}</h3>
            <SimpleLineChart
              data={financials.cashFlowHistory}
              color="#4682b4"
              ariaLabel="Cash flow history"
              formatValue={fmt}
            />
          </div>
          <div className="inv-detail-financials__chart-card">
            <h3 className="inv-detail-financials__chart-title">{tChrome('k57abc849b2')}</h3>
            <SimpleLineChart
              data={financials.roiProgression}
              color="#800080"
              ariaLabel="ROI progression over time"
              formatValue={(v) => `${v}%`}
            />
          </div>
        </div>
      </section>

      <section className="inv-detail-panel" aria-labelledby="metrics-heading">
        <SectionHeader title={tChrome('k8cfc2d82a9')} subtitle={tChrome('kb4014f3839')} />
        <div className="inv-detail-financials__table-wrap">
          <table className="inv-detail-table">
            <caption className="inv-investments__sr-only">{tChrome('k71818f1769')}</caption>
            <thead>
              <tr>
                <th scope="col">{tChrome('kb2bb7604c8')}</th>
                <th scope="col">{tChrome('k8dce170de2')}</th>
              </tr>
            </thead>
            <tbody>
              {financials.metrics.map((m) => (
                <tr key={m.key}>
                  <th scope="row">
                    {investorChrome(tChrome, m.label)}
                    {m.tooltip ? (
                      <span className="inv-detail-tooltip" title={m.tooltip} aria-label={m.tooltip}>
                        ⓘ
                      </span>
                    ) : null}
                  </th>
                  <td>{m.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <CapitalStructureCard structure={detail.capitalStructure} currency={inv.currency} />
    </div>
  );
}
