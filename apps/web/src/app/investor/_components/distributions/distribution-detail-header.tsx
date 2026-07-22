'use client';

import Link from 'next/link';
import type { Route } from 'next';

import type { Distribution } from '../../_data/distribution-types';
import {
  DISTRIBUTION_STATUS_LABELS,
  DISTRIBUTION_TYPE_LABELS,
} from '../../_data/distributions';
import { formatInvestorCurrency, formatInvestorDate } from '../../_data/mock-data';

export interface DistributionDetailHeaderProps {
  distribution: Distribution;
  onDownloadStatement: () => void;
  onContactIr: () => void;
  onReportIssue: () => void;
}

export function DistributionDetailHeader({
  distribution: d,
  onDownloadStatement,
  onContactIr,
  onReportIssue,
}: DistributionDetailHeaderProps) {
  return (
    <header className="inv-distributions__detail-header">
      <Link href={'/investor/distributions' as Route} className="inv-distributions__back-link">
        ← Back to Distributions
      </Link>
      <div className="inv-distributions__detail-title-row">
        <div>
          <h1 className="investor-page__title">{d.periodLabel}</h1>
          <p className="investor-page__subtitle">
            <Link href={`/investor/investments/${d.investmentId}` as Route} className="inv-distributions__link">
              {d.investmentName}
            </Link>
            {' · '}
            {d.entityName}
          </p>
        </div>
        <span className={`inv-distributions__status inv-distributions__status--${d.status}`}>
          {DISTRIBUTION_STATUS_LABELS[d.status]}
        </span>
      </div>

      <dl className="inv-distributions__detail-meta">
        <div>
          <dt>Type</dt>
          <dd>{DISTRIBUTION_TYPE_LABELS[d.distributionType]}</dd>
        </div>
        <div>
          <dt>Payment Date</dt>
          <dd>{formatInvestorDate(d.paymentDate)}</dd>
        </div>
        <div>
          <dt>Net Amount</dt>
          <dd>{formatInvestorCurrency(d.breakdown.netAmount, d.currency)}</dd>
        </div>
        <div>
          <dt>Reference</dt>
          <dd>{d.reference}</dd>
        </div>
      </dl>

      {(d.status === 'failed' || d.status === 'delayed') && (
        <div
          className={`inv-distributions__warning inv-distributions__warning--${d.status}`}
          role="alert"
        >
          <strong>{d.status === 'failed' ? 'Payment Failed' : 'Payment Delayed'}</strong>
          <p>{d.failureReason ?? d.delayReason}</p>
        </div>
      )}

      <div className="inv-distributions__detail-actions">
        <button type="button" className="investor-header__action-btn" onClick={onDownloadStatement}>
          Download Statement
        </button>
        <Link
          href={`/investor/investments/${d.investmentId}` as Route}
          className="investor-header__action-btn"
        >
          View Investment
        </Link>
        <button type="button" className="investor-header__action-btn" onClick={onContactIr}>
          Contact IR
        </button>
        <button
          type="button"
          className="investor-header__action-btn investor-header__action-btn--primary"
          onClick={onReportIssue}
        >
          Report Issue
        </button>
      </div>
    </header>
  );
}
