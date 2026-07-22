'use client';

import { HorizontalBarChart } from './chart-primitives';
import { SectionHeader } from '../section-header';
import type { PortfolioRiskSummary } from '../../_data/portfolio-types';
import { RISK_LEVEL_LABELS } from '../../_data/investments';

export interface RiskAnalyticsProps {
  risk: PortfolioRiskSummary;
}

export function RiskAnalytics({ risk }: RiskAnalyticsProps) {
  const distributionData = risk.distribution.map((d) => ({
    label: d.range,
    value: d.count,
  }));

  return (
    <section className="inv-portfolio-panel">
      <SectionHeader
        title="Risk Analytics"
        subtitle={`Portfolio risk score: ${risk.portfolioRiskScore.toFixed(0)} · High-risk exposure: ${risk.highRiskExposurePercent.toFixed(1)}%`}
      />
      <HorizontalBarChart
        data={distributionData}
        color="#cd853f"
        ariaLabel="Risk score distribution"
        formatValue={(v) => `${v} investments`}
      />

      <h3 className="inv-portfolio-subheading">Risk by Investment</h3>
      <div className="inv-portfolio-table-wrap">
        <table className="inv-portfolio-table">
          <thead>
            <tr>
              <th scope="col">Investment</th>
              <th scope="col">Level</th>
              <th scope="col">Score</th>
              <th scope="col">Exposure %</th>
            </tr>
          </thead>
          <tbody>
            {risk.byInvestment.map((row) => (
              <tr key={row.id}>
                <td>{row.projectName}</td>
                <td>{RISK_LEVEL_LABELS[row.riskLevel]}</td>
                <td>{row.riskScore}</td>
                <td>{row.exposurePercent.toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 className="inv-portfolio-subheading">Risk by Stage</h3>
      <div className="inv-portfolio-table-wrap">
        <table className="inv-portfolio-table">
          <thead>
            <tr>
              <th scope="col">Stage</th>
              <th scope="col">Avg Score</th>
              <th scope="col">Count</th>
            </tr>
          </thead>
          <tbody>
            {risk.byStage.map((row) => (
              <tr key={row.stage}>
                <td>{row.label}</td>
                <td>{row.avgRiskScore.toFixed(0)}</td>
                <td>{row.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
