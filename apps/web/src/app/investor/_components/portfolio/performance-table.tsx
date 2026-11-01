'use client';

import { investorChrome, investorLabel } from '@/app/investor/_components/investor-labels';
import { useTranslations } from 'next-intl';
import Link from 'next/link';
import type { Route } from 'next';
import { useCallback, useMemo, useState } from 'react';

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
  const tChrome = useTranslations('investorPortal.chrome');
  const tLabels = useTranslations('investorPortal.labels');
  const t = useTranslations('investorPortal');
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
        title={tChrome('k1dba0e860c')}
        subtitle={tChrome('kcd68ce910c')}
      />
      <label className="inv-portfolio-table-search">
        <span className="inv-investments__sr-only">{tChrome('kb9ce3d0bba')}</span>
        <input
          type="search"
          className="inv-investments__search-input"
          placeholder={t('placeholders.searchInvestments')}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </label>
      <div className="inv-portfolio-table-wrap inv-portfolio-table-wrap--sticky">
        <table className="inv-portfolio-table inv-portfolio-table--performance">
          <thead>
            <tr>
              <th scope="col">
                <span className="inv-investments__sr-only">{tChrome('k8d105cf44d')}</span>
              </th>
              <SortHeader label="Project" field="projectName" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
              <th scope="col">{tChrome('k3deb745651')}</th>
              <th scope="col">{tChrome('kbae7d5be70')}</th>
              <th scope="col">{tChrome('kca6d0e3aaa')}</th>
              <th scope="col">{tChrome('kd219c68101')}</th>
              <SortHeader label={tChrome('ka13c9ad2ae')} field="investedAmount" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
              <SortHeader label={tChrome('k8dce170de2')} field="currentValue" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
              <SortHeader label={tChrome('k0786ff3b19')} field="equity" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
              <th scope="col">{tChrome('kac14e51f32')}</th>
              <SortHeader label="ROI" field="roi" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
              <SortHeader label="IRR" field="irr" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
              <SortHeader label="EM" field="equityMultiple" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
              <SortHeader label={tChrome('k4d78e9f9ed')} field="annualCashFlow" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
              <th scope="col">{tChrome('k61ad50a9b9')}</th>
              <th scope="col">{tChrome('k5a8f23f567')}</th>
              <SortHeader label={tChrome('k489f487724')} field="riskScore" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
              <th scope="col">{tChrome('kf83b6fe3ae')}</th>
              <th scope="col">{tChrome('k2a71b1b880')}</th>
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
                <td>{investorLabel(tLabels, 'investmentType', row.type)}</td>
                <td>{investorLabel(tLabels, 'investmentStatus', row.status)}</td>
                <td>{investorLabel(tLabels, 'projectStage', row.stage)}</td>
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
                <td>{investorLabel(tLabels, 'riskLevel', row.riskLevel)}</td>
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
  const tChrome = useTranslations('investorPortal.chrome');
  const active = sortKey === field;
  return (
    <th scope="col">
      <button
        type="button"
        className={`inv-portfolio-table__sort${active ? ' inv-portfolio-table__sort--active' : ''}`}
        onClick={() => onSort(field)}
      >
        {investorChrome(tChrome, label)}
        {active ? (sortDir === 'asc' ? ' ↑' : ' ↓') : null}
      </button>
    </th>
  );
}
