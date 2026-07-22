'use client';

export interface PortfolioHeaderProps {
  onExportReport: () => void;
  onDownloadSummary: () => void;
  onCompareInvestments: () => void;
}

export function PortfolioHeader({
  onExportReport,
  onDownloadSummary,
  onCompareInvestments,
}: PortfolioHeaderProps) {
  return (
    <header className="inv-portfolio-header">
      <div>
        <h1 className="investor-page__title">Portfolio Analytics</h1>
        <p className="investor-page__subtitle">
          Monitor portfolio value, diversification, performance, cash flow, and risk across all
          investments.
        </p>
      </div>
      <div className="inv-portfolio-header__actions">
        <button type="button" className="investor-header__action-btn" onClick={onExportReport}>
          Export Report
        </button>
        <button type="button" className="investor-header__action-btn" onClick={onDownloadSummary}>
          Download Summary
        </button>
        <button
          type="button"
          className="investor-header__action-btn investor-header__action-btn--primary"
          onClick={onCompareInvestments}
        >
          Compare Investments
        </button>
      </div>
    </header>
  );
}
