'use client';

import {
  dashboardKpis,
  formatInvestorPercent,
  investments,
} from '../_data/mock-data';
import { InvestorKpiCard } from '../_components/kpi-card';
import { SectionHeader } from '../_components/section-header';

export default function PerformancePage() {
  const performing = [...investments]
    .filter((i) => i.roi > 0)
    .sort((a, b) => b.roi - a.roi);

  return (
    <div className="investor-page">
      <h1 className="investor-page__title">Performance</h1>
      <p className="investor-page__subtitle">
        Return metrics and performance rankings across your portfolio.
      </p>

      <section
        className="inv-dashboard__kpi-grid"
        style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}
        aria-label="Performance summary"
      >
        <InvestorKpiCard
          label="Portfolio ROI"
          value={formatInvestorPercent(dashboardKpis.projectedRoi)}
        />
        <InvestorKpiCard label="Blended IRR" value={formatInvestorPercent(dashboardKpis.irr)} />
        <InvestorKpiCard
          label="Estimated Equity"
          value={formatInvestorPercent(dashboardKpis.estimatedEquity)}
        />
        <InvestorKpiCard
          label="Best Performer"
          value={performing[0] ? formatInvestorPercent(performing[0].roi) : '—'}
          meta={performing[0]?.name}
        />
      </section>

      <SectionHeader title="Investment Rankings" subtitle="Sorted by realized ROI" />

      <div className="inv-dashboard__panel">
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--inv-border)', textAlign: 'left' }}>
              <th style={{ padding: '0.75rem 0', fontWeight: 600 }}>Investment</th>
              <th style={{ padding: '0.75rem 0', fontWeight: 600 }}>ROI</th>
              <th style={{ padding: '0.75rem 0', fontWeight: 600 }}>IRR</th>
              <th style={{ padding: '0.75rem 0', fontWeight: 600 }}>Equity</th>
            </tr>
          </thead>
          <tbody>
            {performing.map((inv) => (
              <tr key={inv.id} style={{ borderBottom: '1px solid var(--inv-border-subtle)' }}>
                <td style={{ padding: '0.875rem 0' }}>{inv.name}</td>
                <td style={{ padding: '0.875rem 0', fontWeight: 600, color: 'var(--inv-gold)' }}>
                  {formatInvestorPercent(inv.roi)}
                </td>
                <td style={{ padding: '0.875rem 0' }}>{formatInvestorPercent(inv.irr)}</td>
                <td style={{ padding: '0.875rem 0' }}>{formatInvestorPercent(inv.equity)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
