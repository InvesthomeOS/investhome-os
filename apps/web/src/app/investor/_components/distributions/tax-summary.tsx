'use client';

import { useTranslations } from 'next-intl';

import { useState } from 'react';

import type { Distribution } from '../../_data/distribution-types';
import { computeTaxSummary } from '../../_data/distribution-calculations';
import { formatInvestorCurrency } from '../../_data/mock-data';
import { SectionHeader } from '../section-header';

export interface TaxSummarySectionProps {
  distributions: Distribution[];
}

export function TaxSummarySection({ distributions }: TaxSummarySectionProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const summaries = computeTaxSummary(distributions);
  const [activeYear, setActiveYear] = useState(summaries[0]?.taxYear ?? new Date().getFullYear());
  const active = summaries.find((s) => s.taxYear === activeYear) ?? summaries[0];

  if (!active) {
    return (
      <section className="inv-distributions__panel">
        <SectionHeader title={tChrome('kaed50143ba')} />
        <p className="inv-distributions__empty-note">{tChrome('k396b4f5640')}</p>
      </section>
    );
  }

  return (
    <section className="inv-distributions__panel">
      <SectionHeader
        title={tChrome('kaed50143ba')}
        subtitle={tChrome('k54cbefdf37')}
      />

      <p className="inv-distributions__disclaimer" role="note">
        This summary is for informational purposes only and does not constitute tax advice.
        Consult your tax advisor for guidance on reporting distribution income.
      </p>

      <div className="inv-distributions__tax-tabs" role="tablist" aria-label={tChrome('kf49b6066b6')}>
        {summaries.map((s) => (
          <button
            key={s.taxYear}
            type="button"
            role="tab"
            aria-selected={activeYear === s.taxYear}
            className={`inv-distributions__tax-tab${activeYear === s.taxYear ? ' inv-distributions__tax-tab--active' : ''}`}
            onClick={() => setActiveYear(s.taxYear)}
          >
            {s.taxYear}
          </button>
        ))}
      </div>

      <div role="tabpanel" className="inv-distributions__tax-panel">
        <dl className="inv-distributions__tax-grid">
          <div>
            <dt>{tChrome('k2a584a50b9')}</dt>
            <dd>{formatInvestorCurrency(active.grossIncome, 'USD')}</dd>
          </div>
          <div>
            <dt>{tChrome('k3e0a85a342')}</dt>
            <dd>{formatInvestorCurrency(active.preferredReturn, 'USD')}</dd>
          </div>
          <div>
            <dt>{tChrome('k5cb0bbf986')}</dt>
            <dd>{formatInvestorCurrency(active.profitShare, 'USD')}</dd>
          </div>
          <div>
            <dt>{tChrome('ke5955ff3aa')}</dt>
            <dd>{formatInvestorCurrency(active.returnOfCapital, 'USD')}</dd>
          </div>
          <div>
            <dt>{tChrome('k2c9e729c10')}</dt>
            <dd>{formatInvestorCurrency(active.totalWithholding, 'USD')}</dd>
          </div>
          <div>
            <dt>{tChrome('ka2a3e74753')}</dt>
            <dd>{formatInvestorCurrency(active.netReceived, 'USD')}</dd>
          </div>
          <div>
            <dt>{tChrome('k71fff5ea85')}</dt>
            <dd>{active.distributionCount}</dd>
          </div>
        </dl>
      </div>
    </section>
  );
}
