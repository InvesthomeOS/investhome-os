'use client';

import {
  dashboardKpis,
  formatInvestorCurrency,
  formatInvestorDate,
  formatInvestorPercent,
  investments,
  timelineEvents,
} from '../_data/mock-data';

import { ActivityTimeline } from './activity-timeline';
import { InvestorKpiCard } from './kpi-card';
import { MetricCard } from './metric-card';
import { SectionHeader } from './section-header';

export function InvestorDashboard() {
  const kpis = dashboardKpis;
  const activeInvestments = investments.filter((inv) => inv.status === 'active').slice(0, 3);

  return (
    <div className="investor-page">
      <h1 className="investor-page__title">Dashboard</h1>
      <p className="investor-page__subtitle">
        Your portfolio overview and recent activity at a glance.
      </p>

      <section className="inv-dashboard__kpi-grid" aria-label="Portfolio KPIs">
        <InvestorKpiCard
          label="Total Invested"
          value={formatInvestorCurrency(kpis.totalInvested, kpis.currency)}
        />
        <InvestorKpiCard
          label="Portfolio Value"
          value={formatInvestorCurrency(kpis.portfolioValue, kpis.currency)}
          delta="+18.0% lifetime"
        />
        <InvestorKpiCard
          label="Estimated Equity"
          value={formatInvestorPercent(kpis.estimatedEquity)}
          meta="Weighted across active holdings"
        />
        <InvestorKpiCard
          label="Annual Cash Flow"
          value={formatInvestorCurrency(kpis.annualCashFlow, kpis.currency)}
          delta="Projected 2025"
        />
        <InvestorKpiCard
          label="Projected ROI"
          value={formatInvestorPercent(kpis.projectedRoi)}
        />
        <InvestorKpiCard label="IRR" value={formatInvestorPercent(kpis.irr)} />
        <InvestorKpiCard
          label="Next Distribution"
          value={formatInvestorCurrency(
            kpis.nextDistribution.amount,
            kpis.nextDistribution.currency,
          )}
          meta={`${formatInvestorDate(kpis.nextDistribution.date)} · ${kpis.nextDistribution.investmentName}`}
        />
        <InvestorKpiCard
          label="Unread Messages"
          value={kpis.unreadMessages}
          delta={kpis.unreadMessages > 0 ? 'Requires attention' : undefined}
        />
        <InvestorKpiCard label="Pending Documents" value={kpis.pendingDocuments} />
        <InvestorKpiCard
          label="Pending Signatures"
          value={kpis.pendingSignatures}
          delta={kpis.pendingSignatures > 0 ? 'Action required' : undefined}
        />
      </section>

      <div className="inv-dashboard__row">
        <section className="inv-dashboard__panel">
          <SectionHeader
            title="Recent Activity"
            subtitle="Latest updates across your investments"
            actionLabel="View all"
            onAction={() => {}}
          />
          <ActivityTimeline events={timelineEvents} maxItems={5} />
        </section>

        <section className="inv-dashboard__panel">
          <SectionHeader
            title="Active Investments"
            subtitle="Top performing holdings"
            actionLabel="View portfolio"
            onAction={() => {}}
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {activeInvestments.map((investment) => (
              <MetricCard key={investment.id} investment={investment} />
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
