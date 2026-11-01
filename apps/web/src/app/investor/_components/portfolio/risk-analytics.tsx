'use client';

import { useTranslations } from 'next-intl';

import { investorChrome, investorLabel } from '@/app/investor/_components/investor-labels';
import { HorizontalBarChart } from './chart-primitives';
import { SectionHeader } from '../section-header';
import type { PortfolioRiskSummary } from '../../_data/portfolio-types';

export interface RiskAnalyticsProps {
  risk: PortfolioRiskSummary;
}

export function RiskAnalytics({ risk }: RiskAnalyticsProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const tLabels = useTranslations('investorPortal.labels');
  const distributionData = risk.distribution.map((d) => ({
    label: d.range,
    value: d.count,
  }));

  return (
    <section className="inv-portfolio-panel">
      <SectionHeader
        title={tChrome('k1537a1c2e0')}
        subtitle={`Portfolio risk score: ${risk.portfolioRiskScore.toFixed(0)} · High-risk exposure: ${risk.highRiskExposurePercent.toFixed(1)}%`}
      />
      <HorizontalBarChart
        data={distributionData}
        color="#cd853f"
        ariaLabel="Risk score distribution"
        formatValue={(v) => `${v} investments`}
      />

      <h3 className="inv-portfolio-subheading">{tChrome('k224ea8dfbf')}</h3>
      <div className="inv-portfolio-table-wrap">
        <table className="inv-portfolio-table">
          <thead>
            <tr>
              <th scope="col">{tChrome('k0401729c31')}</th>
              <th scope="col">{tChrome('k7c7f5d049f')}</th>
              <th scope="col">{tChrome('k489f487724')}</th>
              <th scope="col">{tChrome('ke18bd35ac8')}</th>
            </tr>
          </thead>
          <tbody>
            {risk.byInvestment.map((row) => (
              <tr key={row.id}>
                <td>{row.projectName}</td>
                <td>{investorLabel(tLabels, 'riskLevel', row.riskLevel)}</td>
                <td>{row.riskScore}</td>
                <td>{row.exposurePercent.toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 className="inv-portfolio-subheading">{tChrome('k362e9bd591')}</h3>
      <div className="inv-portfolio-table-wrap">
        <table className="inv-portfolio-table">
          <thead>
            <tr>
              <th scope="col">{tChrome('kca6d0e3aaa')}</th>
              <th scope="col">{tChrome('k5617dba13e')}</th>
              <th scope="col">{tChrome('k66e12969c2')}</th>
            </tr>
          </thead>
          <tbody>
            {risk.byStage.map((row) => (
              <tr key={row.stage}>
                <td>{investorChrome(tChrome, row.label)}</td>
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
