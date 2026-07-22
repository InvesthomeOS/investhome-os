'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useCallback, useMemo, useState } from 'react';

import {
  INVESTMENT_STATUS_LABELS,
  INVESTMENT_TYPE_LABELS,
  PROJECT_STAGE_LABELS,
  RISK_LEVEL_LABELS,
} from '../../_data/investments';
import type { PerformanceTableRow } from '../../_data/portfolio-types';
import { formatInvestorCurrency, formatInvestorDate, formatInvestorPercent } from '../../_data/mock-data';
import { SectionHeader } from '../section-header';

export interface PerformanceTableProps {
  rows: PerformanceTableRow[];
  currency: string;
  selectedIds: Set<string>;
  onToggleSelect: (id: string) => void;
}

type SortKey = keyof Pick<
  PerformanceTableRow,
  | 'projectName'
  | 'investedAmount'
  | 'currentValue'
  | 'equity'
  | 'roi'
  | 'irr'
  | 'equityMultiple'
  | 'annualCashFlow'
  | 'riskScore'
>;

export function PerformanceTable({
  rows,
  currency,
  selectedIds,
  onToggleSelect,
}: PerformanceTableProps) {
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('currentValue');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const handleSort = useCallback(
    (key: SortKey) => {
      if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
      else {
        setSortKey(key);
        setSortDir('desc');
      }
    },
    [sortKey],
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    let result = rows;
    if (q) {
      result = result.filter(
        (r) =>
          r.projectName.toLowerCase().includes(q) ||
          r.city.toLowerCase().includes(q) ||
          r.assetClass.toLowerCase().includes(q),
      );
    }
    return [...result].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (typeof av === 'string' && typeof bv === 'string') {
        return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
      }
      return sortDir === 'asc'
        ? Number(av) - Number(bv)
        : Number(bv) - Number(av);
    });
  }, [rows, search, sortKey, sortDir]);

  return (
    <section className="inv-portfolio-panel">
      <SectionHeader
        title="Investment Performance"
        subtitle="Sortable portfolio holdings with compare selection"
      />
      <label className="inv-portfolio-table-search">
        <span className="inv-investments__sr-only">Search investments</span>
        <input
          type="search"
          className="inv-investments__search-input"
          placeholder="Search investments..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </label>
      <div className="inv-portfolio-table-wrap inv-portfolio-table-wrap--sticky">
        <table className="inv-portfolio-table inv-portfolio-table--performance">
          <thead>
            <tr>
              <th scope="col">
                <span className="inv-investments__sr-only">Compare</span>
              </th>
              <SortHeader label="Project" field="projectName" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
              <th scope="col">Type</th>
              <th scope="col">Status</th>
              <th scope="col">Stage</th>
              <th scope="col">Location</th>
              <SortHeader label="Invested" field="investedAmount" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
              <SortHeader label="Value" field="currentValue" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
              <SortHeader label="Equity" field="equity" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
              <th scope="col">Debt</th>
              <SortHeader label="ROI" field="roi" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
              <SortHeader label="IRR" field="irr" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
              <SortHeader label="EM" field="equityMultiple" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
              <SortHeader label="Cash Flow" field="annualCashFlow" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
              <th scope="col">Target</th>
              <th scope="col">Risk</th>
              <SortHeader label="Score" field="riskScore" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
              <th scope="col">Exit</th>
              <th scope="col">Exit Prob.</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((row) => (
              <tr key={row.id}>
                <td>
                  <input
                    type="checkbox"
                    aria-label={`Select ${row.projectName} for comparison`}
                    checked={selectedIds.has(row.id)}
                    onChange={() => onToggleSelect(row.id)}
                    disabled={!selectedIds.has(row.id) && selectedIds.size >= 4}
                  />
                </td>
                <td>
                  <Link href={`/investor/investments/${row.slug}` as Route} className="inv-portfolio-table__link">
                    {row.projectName}
                  </Link>
                </td>
                <td>{INVESTMENT_TYPE_LABELS[row.type]}</td>
                <td>{INVESTMENT_STATUS_LABELS[row.status]}</td>
                <td>{PROJECT_STAGE_LABELS[row.stage]}</td>
                <td>
                  {row.city}, {row.state}
                </td>
                <td>{formatInvestorCurrency(row.investedAmount, currency)}</td>
                <td>{formatInvestorCurrency(row.currentValue, currency)}</td>
                <td>{formatInvestorCurrency(row.equity, currency)}</td>
                <td>{formatInvestorCurrency(row.debt, currency)}</td>
                <td>{formatInvestorPercent(row.roi)}</td>
                <td>{formatInvestorPercent(row.irr)}</td>
                <td>{row.equityMultiple.toFixed(2)}x</td>
                <td>{formatInvestorCurrency(row.annualCashFlow, currency)}</td>
                <td>{formatInvestorPercent(row.targetReturn)}</td>
                <td>{RISK_LEVEL_LABELS[row.riskLevel]}</td>
                <td>{row.riskScore}</td>
                <td>{row.exitDate ? formatInvestorDate(row.exitDate) : '—'}</td>
                <td>{(row.exitProbability * 100).toFixed(0)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function SortHeader({
  label,
  field,
  sortKey,
  sortDir,
  onSort,
}: {
  label: string;
  field: SortKey;
  sortKey: SortKey;
  sortDir: 'asc' | 'desc';
  onSort: (key: SortKey) => void;
}) {
  const active = sortKey === field;
  return (
    <th scope="col">
      <button
        type="button"
        className={`inv-portfolio-table__sort${active ? ' inv-portfolio-table__sort--active' : ''}`}
        onClick={() => onSort(field)}
      >
        {label}
        {active ? (sortDir === 'asc' ? ' ↑' : ' ↓') : null}
      </button>
    </th>
  );
}
