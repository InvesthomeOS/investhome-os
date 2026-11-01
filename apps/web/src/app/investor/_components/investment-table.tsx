'use client';

import { useTranslations } from 'next-intl';

import { investorChrome, investorLabel } from '@/app/investor/_components/investor-labels';
import Link from 'next/link';
import type { Route } from 'next';
import { useCallback, useEffect, useId, useRef, useState } from 'react';

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
  const tChrome = useTranslations('investorPortal.chrome');
  const isActive = sortField === field;
  return (
    <button
      type="button"
      className={`inv-investment-table__sort${isActive ? ' inv-investment-table__sort--active' : ''}`}
      onClick={() => onSort(field)}
    >
      {investorChrome(tChrome, label)}
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
  const tChrome = useTranslations('investorPortal.chrome');
  const tLabels = useTranslations('investorPortal.labels');
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
            <th scope="col">{tChrome('kd219c68101')}</th>
            <th scope="col">{tChrome('kc7fb317725')}</th>
            <th scope="col">{tChrome('k3deb745651')}</th>
            <th scope="col">
              <SortButton
                label={tChrome('kbae7d5be70')}
                field="status"
                sortField={sortField}
                sortDirection={sortDirection}
                onSort={onSort}
              />
            </th>
            <th scope="col">{tChrome('kca6d0e3aaa')}</th>
            <th scope="col">
              <SortButton
                label={tChrome('ka13c9ad2ae')}
                field="investedAmount"
                sortField={sortField}
                sortDirection={sortDirection}
                onSort={onSort}
              />
            </th>
            <th scope="col">
              <SortButton
                label={tChrome('k8dce170de2')}
                field="currentValue"
                sortField={sortField}
                sortDirection={sortDirection}
                onSort={onSort}
              />
            </th>
            <th scope="col">{tChrome('k3e90e4cbf4')}</th>
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
            <th scope="col">{tChrome('k4d78e9f9ed')}</th>
            <th scope="col">
              <SortButton
                label={tChrome('keb9a4bc1c0')}
                field="investmentDate"
                sortField={sortField}
                sortDirection={sortDirection}
                onSort={onSort}
              />
            </th>
            <th scope="col">{tChrome('k5a8f23f567')}</th>
            <th scope="col">
              <SortButton
                label={tChrome('k1b90271d66')}
                field="progressPercent"
                sortField={sortField}
                sortDirection={sortDirection}
                onSort={onSort}
              />
            </th>
            <th scope="col">{tChrome('kc3cd636a58')}</th>
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
                <td>{investorLabel(tLabels, 'investmentType', investment.type)}</td>
                <td>
                  <span
                    className={`inv-investment-card__status inv-investment-card__status--${investment.status}`}
                  >
                    {investorLabel(tLabels, 'investmentStatus', investment.status)}
                  </span>
                </td>
                <td>{investorLabel(tLabels, 'projectStage', investment.stage)}</td>
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
                    {investorLabel(tLabels, 'riskLevel', investment.riskLevel)}
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
        Sorted by {investorLabel(tLabels, 'sortField', sortField)} ({sortDirection === 'asc' ? 'ascending' : 'descending'})
      </p>
    </div>
  );
}
