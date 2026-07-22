'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams } from 'next/navigation';

import type { InvestmentDetailTab } from '../_data/investment-detail-types';
import { getInvestmentDetailById } from '../_data/investment-details';
import {
  formatInvestorCurrency,
  formatInvestorPercent,
} from '../_data/mock-data';
import { InvestorKpiCard } from './kpi-card';
import { LoadingSkeletonGrid } from './loading-skeleton';
import { ContactsSection } from './investment-detail/contacts-section';
import { DistributionsSection } from './investment-detail/distributions-section';
import { DocumentsSection } from './investment-detail/documents-section';
import { InvestmentDetailHeader } from './investment-detail/investment-detail-header';
import { InvestmentDetailNav } from './investment-detail/investment-detail-nav';
import { InvestmentFinancialsSection } from './investment-detail/investment-financials';
import { InvestmentNotFound } from './investment-detail/investment-not-found';
import { InvestmentOverviewSection } from './investment-detail/investment-overview';
import { InvestmentSummaryPanel } from './investment-detail/investment-summary-panel';
import { ProjectProgressSection } from './investment-detail/project-progress-section';
import { RisksSection } from './investment-detail/risks-section';
import { UpdatesTimeline } from './investment-detail/updates-timeline';

const SHOW_ERROR_PLACEHOLDER = false;

export function InvestmentDetailView() {
  const params = useParams<{ investmentId: string }>();
  const [isLoading, setIsLoading] = useState(true);
  const [hasError] = useState(SHOW_ERROR_PLACEHOLDER);
  const [activeTab, setActiveTab] = useState<InvestmentDetailTab>('overview');
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  const detail = getInvestmentDetailById(params.investmentId);

  useEffect(() => {
    const timer = window.setTimeout(() => setIsLoading(false), 450);
    return () => window.clearTimeout(timer);
  }, [params.investmentId]);

  useEffect(() => {
    if (!toastMessage) return;
    const timer = window.setTimeout(() => setToastMessage(null), 3200);
    return () => window.clearTimeout(timer);
  }, [toastMessage]);

  const handlePlaceholderAction = useCallback((message: string) => {
    setToastMessage(message);
  }, []);

  const scrollToSection = useCallback((sectionId: string) => {
    const tabMap: Record<string, InvestmentDetailTab> = {
      documents: 'documents',
      contacts: 'contacts',
      distributions: 'distributions',
      overview: 'overview',
      financials: 'financials',
      progress: 'progress',
      updates: 'updates',
      risks: 'risks',
    };
    const tab = tabMap[sectionId] ?? 'overview';
    setActiveTab(tab);
    window.requestAnimationFrame(() => {
      const el = document.getElementById(`panel-${tab}`);
      el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }, []);

  if (!detail && !isLoading) {
    return <InvestmentNotFound />;
  }

  if (isLoading || !detail) {
    return (
      <div className="investor-page inv-investments-detail">
        <div className="inv-skeleton inv-skeleton--title" aria-hidden="true" />
        <div className="inv-detail-header__hero inv-detail-header__hero--skeleton">
          <div className="inv-skeleton inv-skeleton--card" style={{ height: '220px' }} aria-hidden="true" />
        </div>
        <LoadingSkeletonGrid count={8} />
        <div className="inv-detail-layout">
          <div className="inv-detail-main">
            <div className="inv-skeleton inv-skeleton--card" style={{ height: '400px', marginTop: '1.5rem' }} aria-hidden="true" />
          </div>
        </div>
        <p className="inv-investments__sr-only" role="status">
          Loading investment details…
        </p>
      </div>
    );
  }

  if (hasError) {
    return (
      <div className="investor-page inv-investments-detail">
        <div className="inv-detail-error" role="alert">
          <h2>Unable to load investment</h2>
          <p>Please try again later or contact investor relations.</p>
        </div>
      </div>
    );
  }

  const inv = detail.investment;
  const equity = inv.currentValue - inv.investedAmount;

  return (
    <div className="investor-page inv-investments-detail" ref={contentRef}>
      <InvestmentDetailHeader
        detail={detail}
        onScrollToSection={scrollToSection}
        onPlaceholderAction={handlePlaceholderAction}
      />

      <section className="inv-detail-kpis" aria-label="Investment KPIs">
        <InvestorKpiCard
          label="Initial Investment"
          value={formatInvestorCurrency(inv.investedAmount, inv.currency)}
        />
        <InvestorKpiCard
          label="Current Value"
          value={formatInvestorCurrency(inv.currentValue, inv.currency)}
          delta={equity > 0 ? `+${formatInvestorCurrency(equity, inv.currency)} gain` : undefined}
        />
        <InvestorKpiCard
          label="Equity"
          value={formatInvestorCurrency(Math.max(0, equity), inv.currency)}
          meta="Unrealized appreciation"
        />
        <InvestorKpiCard
          label="Ownership %"
          value={formatInvestorPercent(inv.ownershipPercent)}
        />
        <InvestorKpiCard
          label="Projected ROI"
          value={formatInvestorPercent(inv.performance.projectedRoi)}
        />
        <InvestorKpiCard
          label="IRR"
          value={inv.performance.irr > 0 ? formatInvestorPercent(inv.performance.irr) : '—'}
        />
        <InvestorKpiCard
          label="Annual Cash Flow"
          value={
            inv.performance.annualCashFlow > 0
              ? formatInvestorCurrency(inv.performance.annualCashFlow, inv.currency)
              : '—'
          }
        />
        <InvestorKpiCard
          label="Total Distributions"
          value={formatInvestorCurrency(inv.distribution.totalDistributed, inv.currency)}
        />
      </section>

      <InvestmentDetailNav activeTab={activeTab} onTabChange={setActiveTab} />

      <div className="inv-detail-layout">
        <div className="inv-detail-main">
          <div
            id="panel-overview"
            role="tabpanel"
            aria-labelledby="tab-overview"
            hidden={activeTab !== 'overview'}
            className="inv-detail-tab-panel"
          >
            {activeTab === 'overview' ? <InvestmentOverviewSection detail={detail} /> : null}
          </div>

          <div
            id="panel-financials"
            role="tabpanel"
            aria-labelledby="tab-financials"
            hidden={activeTab !== 'financials'}
            className="inv-detail-tab-panel"
          >
            {activeTab === 'financials' ? <InvestmentFinancialsSection detail={detail} /> : null}
          </div>

          <div
            id="panel-progress"
            role="tabpanel"
            aria-labelledby="tab-progress"
            hidden={activeTab !== 'progress'}
            className="inv-detail-tab-panel"
          >
            {activeTab === 'progress' ? <ProjectProgressSection detail={detail} /> : null}
          </div>

          <div
            id="panel-distributions"
            role="tabpanel"
            aria-labelledby="tab-distributions"
            hidden={activeTab !== 'distributions'}
            className="inv-detail-tab-panel"
          >
            {activeTab === 'distributions' ? <DistributionsSection detail={detail} /> : null}
          </div>

          <div
            id="panel-documents"
            role="tabpanel"
            aria-labelledby="tab-documents"
            hidden={activeTab !== 'documents'}
            className="inv-detail-tab-panel"
          >
            {activeTab === 'documents' ? (
              <DocumentsSection detail={detail} onPlaceholderAction={handlePlaceholderAction} />
            ) : null}
          </div>

          <div
            id="panel-updates"
            role="tabpanel"
            aria-labelledby="tab-updates"
            hidden={activeTab !== 'updates'}
            className="inv-detail-tab-panel"
          >
            {activeTab === 'updates' ? (
              <UpdatesTimeline detail={detail} onPlaceholderAction={handlePlaceholderAction} />
            ) : null}
          </div>

          <div
            id="panel-risks"
            role="tabpanel"
            aria-labelledby="tab-risks"
            hidden={activeTab !== 'risks'}
            className="inv-detail-tab-panel"
          >
            {activeTab === 'risks' ? <RisksSection detail={detail} /> : null}
          </div>

          <div
            id="panel-contacts"
            role="tabpanel"
            aria-labelledby="tab-contacts"
            hidden={activeTab !== 'contacts'}
            className="inv-detail-tab-panel"
          >
            {activeTab === 'contacts' ? (
              <ContactsSection detail={detail} onPlaceholderAction={handlePlaceholderAction} />
            ) : null}
          </div>

          <div className="inv-detail-summary-mobile">
            <InvestmentSummaryPanel detail={detail} />
          </div>
        </div>

        <InvestmentSummaryPanel detail={detail} />
      </div>

      {toastMessage ? (
        <div className="inv-investments__toast" role="status" aria-live="polite">
          {toastMessage}
        </div>
      ) : null}
    </div>
  );
}
