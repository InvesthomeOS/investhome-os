'use client';

import { investorChrome } from '@/app/investor/_components/investor-labels';

import { useTranslations } from 'next-intl';

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
  const tChrome = useTranslations('investorPortal.chrome');
  return (
    <header className="inv-distributions__page-header">
      <div>
        <h1 className="investor-page__title">{tChrome('k2fd0378f0a')}</h1>
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
        >{investorChrome(tChrome, "Payment Information")}</button>
      </div>
    </header>
  );
}
