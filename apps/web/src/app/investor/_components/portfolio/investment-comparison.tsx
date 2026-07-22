'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useEffect, useRef } from 'react';

import {
  INVESTMENT_STATUS_LABELS,
  INVESTMENT_TYPE_LABELS,
  RISK_LEVEL_LABELS,
} from '../../_data/investments';
import type { PerformanceTableRow } from '../../_data/portfolio-types';
import { formatInvestorCurrency, formatInvestorPercent } from '../../_data/mock-data';

export interface InvestmentComparisonProps {
  open: boolean;
  onClose: () => void;
  rows: PerformanceTableRow[];
  selectedIds: string[];
  currency: string;
}

export function InvestmentComparison({
  open,
  onClose,
  rows,
  selectedIds,
  currency,
}: InvestmentComparisonProps) {
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [open, onClose]);

  if (!open) return null;

  const selected = selectedIds
    .map((id) => rows.find((r) => r.id === id))
    .filter((r): r is PerformanceTableRow => Boolean(r));

  const metrics: { label: string; get: (r: PerformanceTableRow) => string }[] = [
    { label: 'Invested', get: (r) => formatInvestorCurrency(r.investedAmount, currency) },
    { label: 'Current Value', get: (r) => formatInvestorCurrency(r.currentValue, currency) },
    { label: 'Equity', get: (r) => formatInvestorCurrency(r.equity, currency) },
    { label: 'ROI', get: (r) => formatInvestorPercent(r.roi) },
    { label: 'IRR', get: (r) => formatInvestorPercent(r.irr) },
    { label: 'Equity Multiple', get: (r) => `${r.equityMultiple.toFixed(2)}x` },
    { label: 'Cash Flow', get: (r) => formatInvestorCurrency(r.annualCashFlow, currency) },
    { label: 'Risk Score', get: (r) => String(r.riskScore) },
  ];

  return (
    <div className="inv-portfolio-modal-overlay" role="presentation" onClick={onClose}>
      <div
        ref={dialogRef}
        className="inv-portfolio-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="compare-title"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="inv-portfolio-modal__header">
          <h2 id="compare-title">Compare Investments</h2>
          <button type="button" className="inv-portfolio-modal__close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>

        {selected.length < 2 ? (
          <p className="inv-portfolio-modal__hint">
            Select 2–4 investments from the performance table to compare side by side.
          </p>
        ) : (
          <>
            <div className="inv-portfolio-compare-cards">
              {selected.map((inv) => (
                <article key={inv.id} className="inv-portfolio-compare-card">
                  <h3>{inv.projectName}</h3>
                  <p className="inv-portfolio-compare-card__meta">
                    {INVESTMENT_TYPE_LABELS[inv.type]} · {INVESTMENT_STATUS_LABELS[inv.status]}
                  </p>
                  <dl>
                    <div>
                      <dt>ROI</dt>
                      <dd>{formatInvestorPercent(inv.roi)}</dd>
                    </div>
                    <div>
                      <dt>IRR</dt>
                      <dd>{formatInvestorPercent(inv.irr)}</dd>
                    </div>
                    <div>
                      <dt>Value</dt>
                      <dd>{formatInvestorCurrency(inv.currentValue, currency)}</dd>
                    </div>
                    <div>
                      <dt>Risk</dt>
                      <dd>{RISK_LEVEL_LABELS[inv.riskLevel]}</dd>
                    </div>
                  </dl>
                  <Link href={`/investor/investments/${inv.slug}` as Route} className="inv-portfolio-table__link">
                    View details →
                  </Link>
                </article>
              ))}
            </div>

            <div className="inv-portfolio-table-wrap">
              <table className="inv-portfolio-table">
                <thead>
                  <tr>
                    <th scope="col">Metric</th>
                    {selected.map((inv) => (
                      <th key={inv.id} scope="col">
                        {inv.projectName}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {metrics.map((m) => (
                    <tr key={m.label}>
                      <th scope="row">{m.label}</th>
                      {selected.map((inv) => (
                        <td key={inv.id}>{m.get(inv)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
