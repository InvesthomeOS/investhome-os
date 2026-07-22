'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useCallback, useMemo, useState } from 'react';

import type { Distribution, DistributionFilterState } from '../../_data/distribution-types';
import { filterDistributions } from '../../_data/distribution-calculations';
import {
  DISTRIBUTION_STATUS_LABELS,
  DISTRIBUTION_TYPE_LABELS,
  PAYMENT_METHOD_LABELS,
} from '../../_data/distributions';
import { getAllInvestments } from '../../_data/investments';
import { formatInvestorCurrency, formatInvestorDate } from '../../_data/mock-data';
import { SectionHeader } from '../section-header';

type SortField = 'paymentDate' | 'investmentName' | 'netAmount' | 'status' | 'taxYear';

const PAGE_SIZE = 8;

export interface DistributionHistoryTableProps {
  distributions: Distribution[];
  filters: DistributionFilterState;
  onFiltersChange: (patch: Partial<DistributionFilterState>) => void;
}

export function DistributionHistoryTable({
  distributions,
  filters,
  onFiltersChange,
}: DistributionHistoryTableProps) {
  const [sortField, setSortField] = useState<SortField>('paymentDate');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(0);

  const investments = getAllInvestments();
  const filtered = useMemo(
    () => filterDistributions(distributions, filters),
    [distributions, filters],
  );

  const sorted = useMemo(() => {
    const copy = [...filtered];
    copy.sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case 'paymentDate':
          cmp = new Date(a.paymentDate).getTime() - new Date(b.paymentDate).getTime();
          break;
        case 'investmentName':
          cmp = a.investmentName.localeCompare(b.investmentName);
          break;
        case 'netAmount':
          cmp = a.breakdown.netAmount - b.breakdown.netAmount;
          break;
        case 'status':
          cmp = a.status.localeCompare(b.status);
          break;
        case 'taxYear':
          cmp = a.taxYear - b.taxYear;
          break;
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return copy;
  }, [filtered, sortField, sortDir]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const pageItems = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const toggleSort = useCallback(
    (field: SortField) => {
      if (sortField === field) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
      else {
        setSortField(field);
        setSortDir('desc');
      }
      setPage(0);
    },
    [sortField],
  );

  return (
    <section className="inv-distributions__panel">
      <SectionHeader
        title="Distribution History"
        subtitle={`${filtered.length} distribution${filtered.length !== 1 ? 's' : ''} on record`}
      />

      <div className="inv-distributions__table-toolbar">
        <label className="inv-distributions__search">
          <span className="inv-investments__sr-only">Search distributions</span>
          <input
            type="search"
            className="inv-investments__search-input"
            placeholder="Search by investment, period, reference…"
            value={filters.search}
            onChange={(e) => {
              onFiltersChange({ search: e.target.value });
              setPage(0);
            }}
          />
        </label>
        <select
          className="inv-investments__select"
          value={filters.investmentId}
          onChange={(e) => {
            onFiltersChange({ investmentId: e.target.value });
            setPage(0);
          }}
          aria-label="Filter by investment"
        >
          <option value="all">All investments</option>
          {investments.map((inv) => (
            <option key={inv.id} value={inv.id}>
              {inv.projectName}
            </option>
          ))}
        </select>
        <select
          className="inv-investments__select"
          value={filters.status}
          onChange={(e) => {
            onFiltersChange({ status: e.target.value as DistributionFilterState['status'] });
            setPage(0);
          }}
          aria-label="Filter by status"
        >
          <option value="all">All statuses</option>
          {Object.entries(DISTRIBUTION_STATUS_LABELS).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        <select
          className="inv-investments__select"
          value={filters.type}
          onChange={(e) => {
            onFiltersChange({ type: e.target.value as DistributionFilterState['type'] });
            setPage(0);
          }}
          aria-label="Filter by type"
        >
          <option value="all">All types</option>
          {Object.entries(DISTRIBUTION_TYPE_LABELS).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
      </div>

      <div className="inv-distributions__table-wrap">
        <table className="inv-distributions__table">
          <caption className="inv-investments__sr-only">Distribution history</caption>
          <thead>
            <tr>
              <th scope="col">
                <button type="button" className="inv-distributions__sort" onClick={() => toggleSort('paymentDate')}>
                  Payment Date
                </button>
              </th>
              <th scope="col">
                <button type="button" className="inv-distributions__sort" onClick={() => toggleSort('investmentName')}>
                  Investment
                </button>
              </th>
              <th scope="col">Period</th>
              <th scope="col">Type</th>
              <th scope="col">Gross</th>
              <th scope="col">
                <button type="button" className="inv-distributions__sort" onClick={() => toggleSort('netAmount')}>
                  Net
                </button>
              </th>
              <th scope="col">
                <button type="button" className="inv-distributions__sort" onClick={() => toggleSort('status')}>
                  Status
                </button>
              </th>
              <th scope="col">
                <button type="button" className="inv-distributions__sort" onClick={() => toggleSort('taxYear')}>
                  Tax Year
                </button>
              </th>
              <th scope="col">Method</th>
              <th scope="col">Reference</th>
            </tr>
          </thead>
          <tbody>
            {pageItems.map((d) => (
              <tr key={d.id}>
                <td>
                  <Link href={`/investor/distributions/${d.id}` as Route} className="inv-distributions__link">
                    <time dateTime={d.paymentDate}>{formatInvestorDate(d.paymentDate)}</time>
                  </Link>
                </td>
                <td>
                  <Link href={`/investor/investments/${d.investmentId}` as Route} className="inv-distributions__link">
                    {d.investmentName}
                  </Link>
                </td>
                <td>{d.periodLabel}</td>
                <td>{DISTRIBUTION_TYPE_LABELS[d.distributionType]}</td>
                <td>{formatInvestorCurrency(d.breakdown.grossAmount, d.currency)}</td>
                <td>{formatInvestorCurrency(d.breakdown.netAmount, d.currency)}</td>
                <td>
                  <span className={`inv-distributions__status inv-distributions__status--${d.status}`}>
                    {DISTRIBUTION_STATUS_LABELS[d.status]}
                  </span>
                </td>
                <td>{d.taxYear}</td>
                <td>{PAYMENT_METHOD_LABELS[d.paymentMethod]}</td>
                <td>{d.reference}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="inv-distributions__mobile-cards" aria-label="Distribution history cards">
        {pageItems.map((d) => (
          <article key={d.id} className="inv-distributions__mobile-card">
            <header>
              <Link href={`/investor/distributions/${d.id}` as Route} className="inv-distributions__link">
                {d.investmentName}
              </Link>
              <span className={`inv-distributions__status inv-distributions__status--${d.status}`}>
                {DISTRIBUTION_STATUS_LABELS[d.status]}
              </span>
            </header>
            <dl>
              <div>
                <dt>Date</dt>
                <dd>{formatInvestorDate(d.paymentDate)}</dd>
              </div>
              <div>
                <dt>Net</dt>
                <dd>{formatInvestorCurrency(d.breakdown.netAmount, d.currency)}</dd>
              </div>
              <div>
                <dt>Type</dt>
                <dd>{DISTRIBUTION_TYPE_LABELS[d.distributionType]}</dd>
              </div>
            </dl>
          </article>
        ))}
      </div>

      <div className="inv-distributions__pagination">
        <button
          type="button"
          className="inv-distributions__page-btn"
          disabled={page === 0}
          onClick={() => setPage((p) => p - 1)}
        >
          Previous
        </button>
        <span>
          Page {page + 1} of {totalPages}
        </span>
        <button
          type="button"
          className="inv-distributions__page-btn"
          disabled={page >= totalPages - 1}
          onClick={() => setPage((p) => p + 1)}
        >
          Next
        </button>
      </div>
    </section>
  );
}
