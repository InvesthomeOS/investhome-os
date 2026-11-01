'use client';

import { useTranslations } from 'next-intl';

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
  const t = useTranslations('investorPortal');
  const kpis = dashboardKpis;
  const activeInvestments = investments.filter((inv) => inv.status === 'active').slice(0, 3);

  return (
    <div className="investor-page">
      <h1 className="investor-page__title">{t('dashboard.title')}</h1>
      <p className="investor-page__subtitle">
        {t('dashboard.subtitle')}
      </p>

      <section className="inv-dashboard__kpi-grid" aria-label={t('dashboard.kpiAria')}>
        <InvestorKpiCard
          label={t('dashboard.totalInvested')}
          value={formatInvestorCurrency(kpis.totalInvested, kpis.currency)}
        />
        <InvestorKpiCard
          label={t('dashboard.portfolioValue')}
          value={formatInvestorCurrency(kpis.portfolioValue, kpis.currency)}
          delta={t('dashboard.lifetimeDelta')}
        />
        <InvestorKpiCard
          label={t('dashboard.estimatedEquity')}
          value={formatInvestorPercent(kpis.estimatedEquity)}
          meta={t('dashboard.equityMeta')}
        />
        <InvestorKpiCard
          label={t('dashboard.annualCashFlow')}
          value={formatInvestorCurrency(kpis.annualCashFlow, kpis.currency)}
          delta={t('dashboard.projectedYear')}
        />
        <InvestorKpiCard
          label={t('dashboard.projectedRoi')}
          value={formatInvestorPercent(kpis.projectedRoi)}
        />
        <InvestorKpiCard label="IRR" value={formatInvestorPercent(kpis.irr)} />
        <InvestorKpiCard
          label={t('dashboard.nextDistribution')}
          value={formatInvestorCurrency(
            kpis.nextDistribution.amount,
            kpis.nextDistribution.currency,
          )}
          meta={`${formatInvestorDate(kpis.nextDistribution.date)} · ${kpis.nextDistribution.investmentName}`}
        />
        <InvestorKpiCard
          label={t('dashboard.unreadMessages')}
          value={kpis.unreadMessages}
          delta={kpis.unreadMessages > 0 ? t('dashboard.requiresAttention') : undefined}
        />
        <InvestorKpiCard label={t('dashboard.pendingDocuments')} value={kpis.pendingDocuments} />
        <InvestorKpiCard
          label={t('dashboard.pendingSignatures')}
          value={kpis.pendingSignatures}
          delta={kpis.pendingSignatures > 0 ? t('dashboard.actionRequired') : undefined}
        />
      </section>

      <div className="inv-dashboard__row">
        <section className="inv-dashboard__panel">
          <SectionHeader
            title={t('dashboard.recentActivity')}
            subtitle={t('dashboard.recentActivityHint')}
            actionLabel={t('dashboard.viewAll')}
            onAction={() => {}}
          />
          <ActivityTimeline events={timelineEvents} maxItems={5} />
        </section>

        <section className="inv-dashboard__panel">
          <SectionHeader
            title={t('dashboard.activeInvestments')}
            subtitle={t('dashboard.activeInvestmentsHint')}
            actionLabel={t('dashboard.viewPortfolio')}
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
