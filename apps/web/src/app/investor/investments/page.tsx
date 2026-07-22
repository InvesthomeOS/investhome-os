'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useCallback, useEffect, useState } from 'react';

import { EmptyState } from '../_components/empty-state';
import { InvestmentCard } from '../_components/investment-card';
import { InvestmentErrorState } from '../_components/investment-error-state';
import { InvestmentFilters } from '../_components/investment-filters';
import { InvestmentSummaryRow } from '../_components/investment-summary-row';
import { InvestmentTable } from '../_components/investment-table';
import { LoadingSkeletonGrid } from '../_components/loading-skeleton';
import { useInvestmentFilters } from '../_components/use-investment-filters';
import type { PortfolioInvestment } from '../_data/investment-types';

const SHOW_ERROR_PLACEHOLDER = false;

export default function InvestmentsPage() {
  const {
    filters,
    filteredInvestments,
    allInvestments,
    activeFilterCount,
    updateFilter,
    clearFilters,
    toggleSortDirection,
    setSortField,
  } = useInvestmentFilters();

  const [isLoading, setIsLoading] = useState(true);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => setIsLoading(false), 400);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!toastMessage) return;
    const timer = window.setTimeout(() => setToastMessage(null), 3200);
    return () => window.clearTimeout(timer);
  }, [toastMessage]);

  const handleExportPortfolio = useCallback(() => {
    setToastMessage('Portfolio export will be available in a future release.');
  }, []);

  const handleDownloadSummary = useCallback((investment: PortfolioInvestment) => {
    setToastMessage(`Summary download for ${investment.projectName} coming soon.`);
  }, []);

  const hasFilters =
    filters.search.trim().length > 0 || activeFilterCount > 0;

  return (
    <div className="investor-page inv-investments">
      <header className="inv-investments__page-header">
        <div>
          <h1 className="investor-page__title">My Investments</h1>
          <p className="investor-page__subtitle">
            Track your active, completed, and upcoming real estate investments.
          </p>
        </div>
        <div className="inv-investments__header-actions">
          <button
            type="button"
            className="investor-header__action-btn"
            onClick={handleExportPortfolio}
          >
            Export Portfolio
          </button>
          <Link
            href={'/investor/portfolio' as Route}
            className="investor-header__action-btn investor-header__action-btn--primary"
          >
            View Portfolio Analytics
          </Link>
        </div>
      </header>

      {SHOW_ERROR_PLACEHOLDER ? (
        <InvestmentErrorState onRetry={() => setIsLoading(true)} />
      ) : null}

      {isLoading ? (
        <LoadingSkeletonGrid count={8} />
      ) : (
        <>
          <InvestmentSummaryRow investments={allInvestments} />

          <InvestmentFilters
            filters={filters}
            activeFilterCount={activeFilterCount}
            resultCount={filteredInvestments.length}
            onUpdateFilter={updateFilter}
            onClearFilters={clearFilters}
            onToggleSortDirection={toggleSortDirection}
          />

          {filteredInvestments.length === 0 ? (
            <EmptyState
              icon="◇"
              title="No search results"
              description={
                hasFilters
                  ? 'No investments match your current filters. Try adjusting your search or clearing filters.'
                  : 'You do not have any investments yet.'
              }
              actionLabel={hasFilters ? 'Clear Filters' : undefined}
              onAction={hasFilters ? clearFilters : undefined}
            />
          ) : filters.viewMode === 'grid' ? (
            <div className="inv-investments__grid" role="list">
              {filteredInvestments.map((investment) => (
                <div key={investment.id} role="listitem">
                  <InvestmentCard investment={investment} />
                </div>
              ))}
            </div>
          ) : (
            <InvestmentTable
              investments={filteredInvestments}
              sortField={filters.sortField}
              sortDirection={filters.sortDirection}
              onSort={setSortField}
              onDownloadSummary={handleDownloadSummary}
            />
          )}
        </>
      )}

      {toastMessage ? (
        <div className="inv-investments__toast" role="status" aria-live="polite">
          {toastMessage}
        </div>
      ) : null}
    </div>
  );
}
