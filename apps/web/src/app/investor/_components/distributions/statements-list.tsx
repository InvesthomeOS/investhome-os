'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useMemo, useState } from 'react';

import { DISTRIBUTION_TYPE_LABELS } from '../../_data/distributions';
import { STATEMENT_STATUS_LABELS, filterStatements } from '../../_data/statements';
import { getAllInvestments } from '../../_data/investments';
import { formatInvestorCurrency, formatInvestorDate } from '../../_data/mock-data';
import { SectionHeader } from '../section-header';

export interface StatementsListProps {
  onPreview: (statementId: string) => void;
  onDownload: (statementId: string) => void;
}

export function StatementsList({ onPreview, onDownload }: StatementsListProps) {
  const [search, setSearch] = useState('');
  const [investmentId, setInvestmentId] = useState<string | 'all'>('all');
  const [taxYear, setTaxYear] = useState<number | 'all'>('all');
  const [type, setType] = useState<'all' | keyof typeof DISTRIBUTION_TYPE_LABELS>('all');
  const [status, setStatus] = useState<'all' | 'available' | 'pending' | 'archived'>('all');

  const investments = getAllInvestments();
  const statements = useMemo(
    () =>
      filterStatements({ search, investmentId, taxYear, type, status }),
    [search, investmentId, taxYear, type, status],
  );

  const years = useMemo(() => {
    const all = filterStatements({
      search: '',
      investmentId: 'all',
      taxYear: 'all',
      type: 'all',
      status: 'all',
    });
    return Array.from(new Set(all.map((s) => s.taxYear))).sort((a, b) => b - a);
  }, []);

  return (
    <section className="inv-distributions__panel">
      <SectionHeader
        title="Distribution Statements"
        subtitle={`${statements.length} statement${statements.length !== 1 ? 's' : ''}`}
      />

      <div className="inv-distributions__table-toolbar">
        <label className="inv-distributions__search">
          <span className="inv-investments__sr-only">Search statements</span>
          <input
            type="search"
            className="inv-investments__search-input"
            placeholder="Search statements…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        <select
          className="inv-investments__select"
          value={investmentId}
          onChange={(e) => setInvestmentId(e.target.value)}
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
          value={taxYear === 'all' ? 'all' : String(taxYear)}
          onChange={(e) =>
            setTaxYear(e.target.value === 'all' ? 'all' : Number(e.target.value))
          }
          aria-label="Filter by year"
        >
          <option value="all">All years</option>
          {years.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
        <select
          className="inv-investments__select"
          value={type}
          onChange={(e) => setType(e.target.value as typeof type)}
          aria-label="Filter by type"
        >
          <option value="all">All types</option>
          {Object.entries(DISTRIBUTION_TYPE_LABELS).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        <select
          className="inv-investments__select"
          value={status}
          onChange={(e) => setStatus(e.target.value as typeof status)}
          aria-label="Filter by status"
        >
          <option value="all">All statuses</option>
          {Object.entries(STATEMENT_STATUS_LABELS).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
      </div>

      <div className="inv-distributions__table-wrap">
        <table className="inv-distributions__table">
          <thead>
            <tr>
              <th scope="col">Date</th>
              <th scope="col">Investment</th>
              <th scope="col">Period</th>
              <th scope="col">Type</th>
              <th scope="col">Net</th>
              <th scope="col">Status</th>
              <th scope="col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {statements.map((s) => (
              <tr key={s.id}>
                <td>{formatInvestorDate(s.statementDate)}</td>
                <td>
                  <Link
                    href={`/investor/investments/${s.investmentId}` as Route}
                    className="inv-distributions__link"
                  >
                    {s.investmentName}
                  </Link>
                </td>
                <td>{s.periodLabel}</td>
                <td>{DISTRIBUTION_TYPE_LABELS[s.distributionType]}</td>
                <td>{formatInvestorCurrency(s.netAmount, s.currency)}</td>
                <td>
                  <span className={`inv-distributions__stmt-status inv-distributions__stmt-status--${s.status}`}>
                    {STATEMENT_STATUS_LABELS[s.status]}
                  </span>
                </td>
                <td>
                  <div className="inv-distributions__stmt-actions">
                    <button type="button" onClick={() => onPreview(s.id)}>
                      Preview
                    </button>
                    <button type="button" onClick={() => onDownload(s.id)}>
                      Download
                    </button>
                    <Link href={`/investor/distributions/${s.distributionId}` as Route}>
                      View
                    </Link>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {statements.length === 0 ? (
        <p className="inv-distributions__empty-note">No statements match your filters.</p>
      ) : null}
    </section>
  );
}
