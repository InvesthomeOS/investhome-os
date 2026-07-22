import type { InvestmentDetail } from '../../_data/investment-detail-types';
import { formatInvestorCurrency } from '../../_data/mock-data';
import { SectionHeader } from '../section-header';
import { CapitalStructureCard } from './capital-structure-card';
import { SimpleLineChart } from './simple-line-chart';

export interface InvestmentFinancialsProps {
  detail: InvestmentDetail;
}

export function InvestmentFinancialsSection({ detail }: InvestmentFinancialsProps) {
  const { financials, investment: inv } = detail;
  const fmt = (v: number) => formatInvestorCurrency(v, inv.currency);

  return (
    <div className="inv-detail-financials">
      <section className="inv-detail-panel" aria-labelledby="charts-heading">
        <SectionHeader title="Performance Charts" subtitle="Historical trends for your investment" />
        <div className="inv-detail-financials__charts">
          <div className="inv-detail-financials__chart-card">
            <h3 className="inv-detail-financials__chart-title">Investment Growth</h3>
            <SimpleLineChart
              data={financials.investmentGrowth}
              ariaLabel="Investment growth over time"
              formatValue={fmt}
            />
          </div>
          <div className="inv-detail-financials__chart-card">
            <h3 className="inv-detail-financials__chart-title">Equity Growth</h3>
            <SimpleLineChart
              data={financials.equityGrowth}
              color="#228b22"
              ariaLabel="Equity growth over time"
              formatValue={fmt}
            />
          </div>
          <div className="inv-detail-financials__chart-card">
            <h3 className="inv-detail-financials__chart-title">Cash Flow</h3>
            <SimpleLineChart
              data={financials.cashFlowHistory}
              color="#4682b4"
              ariaLabel="Cash flow history"
              formatValue={fmt}
            />
          </div>
          <div className="inv-detail-financials__chart-card">
            <h3 className="inv-detail-financials__chart-title">ROI Progression</h3>
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
        <SectionHeader title="Financial Summary" subtitle="Key metrics with definitions" />
        <div className="inv-detail-financials__table-wrap">
          <table className="inv-detail-table">
            <caption className="inv-investments__sr-only">Financial metrics summary</caption>
            <thead>
              <tr>
                <th scope="col">Metric</th>
                <th scope="col">Value</th>
              </tr>
            </thead>
            <tbody>
              {financials.metrics.map((m) => (
                <tr key={m.key}>
                  <th scope="row">
                    {m.label}
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
