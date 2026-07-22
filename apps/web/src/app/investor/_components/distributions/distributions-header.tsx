'use client';

import Link from 'next/link';
import type { Route } from 'next';

export interface DistributionsHeaderProps {
  onDownloadReport: () => void;
  onExportCashFlow: () => void;
  onOpenPaymentInfo: () => void;
}

export function DistributionsHeader({
  onDownloadReport,
  onExportCashFlow,
  onOpenPaymentInfo,
}: DistributionsHeaderProps) {
  return (
    <header className="inv-distributions__page-header">
      <div>
        <h1 className="investor-page__title">Distributions & Cash Flow</h1>
        <p className="investor-page__subtitle">
          Track distribution history, projected cash flow, tax summaries, and payment activity
          across your portfolio. Mock UI — no real payments are processed.
        </p>
      </div>
      <div className="inv-distributions__header-actions">
        <button type="button" className="investor-header__action-btn" onClick={onDownloadReport}>
          Download Report
        </button>
        <button type="button" className="investor-header__action-btn" onClick={onExportCashFlow}>
          Export Cash Flow
        </button>
        <Link
          href={'/investor/statements' as Route}
          className="investor-header__action-btn"
        >
          View Statements
        </Link>
        <button
          type="button"
          className="investor-header__action-btn investor-header__action-btn--primary"
          onClick={onOpenPaymentInfo}
        >
          Payment Information
        </button>
      </div>
    </header>
  );
}
