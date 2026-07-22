'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useCallback, useEffect, useId, useRef, useState } from 'react';

import {
  INVESTMENT_STATUS_LABELS,
  INVESTMENT_TYPE_LABELS,
  PROJECT_STAGE_LABELS,
  RISK_LEVEL_LABELS,
  SORT_FIELD_LABELS,
} from '../_data/investments';
import type { InvestmentSortField, PortfolioInvestment } from '../_data/investment-types';
import {
  formatInvestorCurrency,
  formatInvestorDate,
  formatInvestorPercent,
} from '../_data/mock-data';

export interface InvestmentTableProps {
  investments: PortfolioInvestment[];
  sortField: InvestmentSortField;
  sortDirection: 'asc' | 'desc';
  onSort: (field: InvestmentSortField) => void;
  onDownloadSummary: (investment: PortfolioInvestment) => void;
}

function SortButton({
  label,
  field,
  sortField,
  sortDirection,
  onSort,
}: {
  label: string;
  field: InvestmentSortField;
  sortField: InvestmentSortField;
  sortDirection: 'asc' | 'desc';
  onSort: (field: InvestmentSortField) => void;
}) {
  const isActive = sortField === field;
  return (
    <button
      type="button"
      className={`inv-investment-table__sort${isActive ? ' inv-investment-table__sort--active' : ''}`}
      onClick={() => onSort(field)}
    >
      {label}
      {isActive ? (
        <span aria-hidden="true">{sortDirection === 'asc' ? ' ↑' : ' ↓'}</span>
      ) : null}
    </button>
  );
}

function RowActionsMenu({
  investment,
  onDownloadSummary,
}: {
  investment: PortfolioInvestment;
  onDownloadSummary: (investment: PortfolioInvestment) => void;
}) {
  const menuId = useId();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const close = useCallback(() => setOpen(false), []);

  useEffect(() => {
    if (!open) return;

    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        close();
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') close();
    }

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [open, close]);

  return (
    <div className="inv-investment-table__menu" ref={containerRef}>
      <button
        type="button"
        className="inv-investment-table__menu-trigger"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpen((prev) => !prev)}
      >
        More
        <span aria-hidden="true"> ▾</span>
      </button>
      {open ? (
        <div id={menuId} className="inv-investment-table__menu-panel" role="menu">
          <Link
            href={'/investor/documents' as Route}
            className="inv-investment-table__menu-item"
            role="menuitem"
            onClick={close}
          >
            View Documents
          </Link>
          <Link
            href={'/investor/distributions' as Route}
            className="inv-investment-table__menu-item"
            role="menuitem"
            onClick={close}
          >
            View Distributions
          </Link>
          <button
            type="button"
            className="inv-investment-table__menu-item"
            role="menuitem"
            onClick={() => {
              onDownloadSummary(investment);
              close();
            }}
          >
            Download Summary
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function InvestmentTable({
  investments,
  sortField,
  sortDirection,
  onSort,
  onDownloadSummary,
}: InvestmentTableProps) {
  return (
    <div className="inv-investment-table__wrap">
      <table className="inv-investment-table">
        <caption className="inv-investments__sr-only">
          Portfolio investments with performance and status details
        </caption>
        <thead>
          <tr>
            <th scope="col">
              <SortButton
                label="Project"
                field="projectName"
                sortField={sortField}
                sortDirection={sortDirection}
                onSort={onSort}
              />
            </th>
            <th scope="col">Location</th>
            <th scope="col">Entity</th>
            <th scope="col">Type</th>
            <th scope="col">
              <SortButton
                label="Status"
                field="status"
                sortField={sortField}
                sortDirection={sortDirection}
                onSort={onSort}
              />
            </th>
            <th scope="col">Stage</th>
            <th scope="col">
              <SortButton
                label="Invested"
                field="investedAmount"
                sortField={sortField}
                sortDirection={sortDirection}
                onSort={onSort}
              />
            </th>
            <th scope="col">
              <SortButton
                label="Value"
                field="currentValue"
                sortField={sortField}
                sortDirection={sortDirection}
                onSort={onSort}
              />
            </th>
            <th scope="col">Ownership</th>
            <th scope="col">
              <SortButton
                label="ROI"
                field="roi"
                sortField={sortField}
                sortDirection={sortDirection}
                onSort={onSort}
              />
            </th>
            <th scope="col">
              <SortButton
                label="IRR"
                field="irr"
                sortField={sortField}
                sortDirection={sortDirection}
                onSort={onSort}
              />
            </th>
            <th scope="col">Cash Flow</th>
            <th scope="col">
              <SortButton
                label="Date"
                field="investmentDate"
                sortField={sortField}
                sortDirection={sortDirection}
                onSort={onSort}
              />
            </th>
            <th scope="col">Risk</th>
            <th scope="col">
              <SortButton
                label="Progress"
                field="progressPercent"
                sortField={sortField}
                sortDirection={sortDirection}
                onSort={onSort}
              />
            </th>
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          {investments.map((investment) => {
            const detailHref = `/investor/investments/${investment.id}` as Route;
            const location = `${investment.city}, ${investment.state}`;

            return (
              <tr key={investment.id} className="inv-investment-table__row">
                <td>
                  <div className="inv-investment-table__project">
                    <strong>{investment.projectName}</strong>
                    <span>{investment.address}</span>
                  </div>
                </td>
                <td>{location}</td>
                <td>{investment.entityName}</td>
                <td>{INVESTMENT_TYPE_LABELS[investment.type]}</td>
                <td>
                  <span
                    className={`inv-investment-card__status inv-investment-card__status--${investment.status}`}
                  >
                    {INVESTMENT_STATUS_LABELS[investment.status]}
                  </span>
                </td>
                <td>{PROJECT_STAGE_LABELS[investment.stage]}</td>
                <td>{formatInvestorCurrency(investment.investedAmount, investment.currency)}</td>
                <td>{formatInvestorCurrency(investment.currentValue, investment.currency)}</td>
                <td>{formatInvestorPercent(investment.ownershipPercent)}</td>
                <td className="inv-investment-table__highlight">
                  {investment.performance.roi > 0
                    ? formatInvestorPercent(investment.performance.roi)
                    : '—'}
                </td>
                <td>
                  {investment.performance.irr > 0
                    ? formatInvestorPercent(investment.performance.irr)
                    : '—'}
                </td>
                <td>
                  {investment.performance.annualCashFlow > 0
                    ? formatInvestorCurrency(
                        investment.performance.annualCashFlow,
                        investment.currency,
                      )
                    : '—'}
                </td>
                <td>{formatInvestorDate(investment.investmentDate)}</td>
                <td>
                  <span
                    className={`inv-investment-card__risk inv-investment-card__risk--${investment.riskLevel}`}
                  >
                    {RISK_LEVEL_LABELS[investment.riskLevel]}
                  </span>
                </td>
                <td>{investment.progressPercent}%</td>
                <td>
                  <div className="inv-investment-table__actions">
                    <Link href={detailHref} className="inv-investment-table__link">
                      View Details
                    </Link>
                    <RowActionsMenu
                      investment={investment}
                      onDownloadSummary={onDownloadSummary}
                    />
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="inv-investments__sr-only">
        Sorted by {SORT_FIELD_LABELS[sortField]} ({sortDirection === 'asc' ? 'ascending' : 'descending'})
      </p>
    </div>
  );
}
