'use client';

import { useState } from 'react';

import type { Distribution } from '../../_data/distribution-types';
import { computeTaxSummary } from '../../_data/distribution-calculations';
import { formatInvestorCurrency } from '../../_data/mock-data';
import { SectionHeader } from '../section-header';

export interface TaxSummarySectionProps {
  distributions: Distribution[];
}

export function TaxSummarySection({ distributions }: TaxSummarySectionProps) {
  const summaries = computeTaxSummary(distributions);
  const [activeYear, setActiveYear] = useState(summaries[0]?.taxYear ?? new Date().getFullYear());
  const active = summaries.find((s) => s.taxYear === activeYear) ?? summaries[0];

  if (!active) {
    return (
      <section className="inv-distributions__panel">
        <SectionHeader title="Tax & Withholding Summary" />
        <p className="inv-distributions__empty-note">No tax data available.</p>
      </section>
    );
  }

  return (
    <section className="inv-distributions__panel">
      <SectionHeader
        title="Tax & Withholding Summary"
        subtitle="Withholding and income breakdown by tax year"
      />

      <p className="inv-distributions__disclaimer" role="note">
        This summary is for informational purposes only and does not constitute tax advice.
        Consult your tax advisor for guidance on reporting distribution income.
      </p>

      <div className="inv-distributions__tax-tabs" role="tablist" aria-label="Tax year">
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
            <dt>Gross Income</dt>
            <dd>{formatInvestorCurrency(active.grossIncome, 'USD')}</dd>
          </div>
          <div>
            <dt>Preferred Return</dt>
            <dd>{formatInvestorCurrency(active.preferredReturn, 'USD')}</dd>
          </div>
          <div>
            <dt>Profit Share / Sale</dt>
            <dd>{formatInvestorCurrency(active.profitShare, 'USD')}</dd>
          </div>
          <div>
            <dt>Return of Capital</dt>
            <dd>{formatInvestorCurrency(active.returnOfCapital, 'USD')}</dd>
          </div>
          <div>
            <dt>Total Withholding</dt>
            <dd>{formatInvestorCurrency(active.totalWithholding, 'USD')}</dd>
          </div>
          <div>
            <dt>Net Received</dt>
            <dd>{formatInvestorCurrency(active.netReceived, 'USD')}</dd>
          </div>
          <div>
            <dt>Distributions</dt>
            <dd>{active.distributionCount}</dd>
          </div>
        </dl>
      </div>
    </section>
  );
}
