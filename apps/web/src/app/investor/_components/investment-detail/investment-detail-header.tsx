'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useCallback, useEffect, useRef, useState } from 'react';

import type { InvestmentDetail } from '../../_data/investment-detail-types';
import {
  INVESTMENT_STATUS_LABELS,
  INVESTMENT_TYPE_LABELS,
  PROJECT_STAGE_LABELS,
  RISK_LEVEL_LABELS,
} from '../../_data/investments';
import { formatInvestorDate } from '../../_data/mock-data';

export interface InvestmentDetailHeaderProps {
  detail: InvestmentDetail;
  onScrollToSection: (sectionId: string) => void;
  onPlaceholderAction: (message: string) => void;
}

export function InvestmentDetailHeader({
  detail,
  onScrollToSection,
  onPlaceholderAction,
}: InvestmentDetailHeaderProps) {
  const { investment: inv } = detail;
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [menuOpen]);

  const handleMenuAction = useCallback(
    (message: string) => {
      setMenuOpen(false);
      onPlaceholderAction(message);
    },
    [onPlaceholderAction],
  );

  return (
    <header className="inv-detail-header">
      <Link href={'/investor/investments' as Route} className="inv-investments__back-link">
        ← Back to My Investments
      </Link>

      <div className="inv-detail-header__hero">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={inv.imageUrl}
          alt={`${inv.projectName} cover`}
          className="inv-detail-header__cover"
        />
        <div className="inv-detail-header__overlay" aria-hidden="true" />
        <div className="inv-detail-header__hero-content">
          <h1 className="inv-detail-header__title">{inv.projectName}</h1>
          <p className="inv-detail-header__address">
            {inv.address} · {inv.city}, {inv.state}
          </p>
          <p className="inv-detail-header__entity">{inv.entityName}</p>
          <div className="inv-detail-header__badges">
            <span className={`inv-investment-card__status inv-investment-card__status--${inv.status}`}>
              {INVESTMENT_STATUS_LABELS[inv.status]}
            </span>
            <span className="inv-investment-card__tag">{INVESTMENT_TYPE_LABELS[inv.type]}</span>
            <span className="inv-investment-card__tag">{PROJECT_STAGE_LABELS[inv.stage]}</span>
            <span className={`inv-investment-card__risk inv-investment-card__risk--${inv.riskLevel}`}>
              {RISK_LEVEL_LABELS[inv.riskLevel]}
            </span>
          </div>
          <div className="inv-detail-header__dates">
            <span>Invested {formatInvestorDate(inv.investmentDate)}</span>
            {inv.exitDate ? (
              <>
                <span aria-hidden="true">·</span>
                <span>Projected Exit {formatInvestorDate(inv.exitDate)}</span>
              </>
            ) : null}
          </div>
        </div>
      </div>

      <div className="inv-detail-header__actions">
        <button
          type="button"
          className="investor-header__action-btn"
          onClick={() => onPlaceholderAction(`Summary download for ${inv.projectName} coming soon.`)}
        >
          Download Summary
        </button>
        <button
          type="button"
          className="investor-header__action-btn"
          onClick={() => onScrollToSection('documents')}
        >
          View Documents
        </button>
        <button
          type="button"
          className="investor-header__action-btn"
          onClick={() => onScrollToSection('contacts')}
        >
          Contact Team
        </button>
        <div className="inv-detail-header__menu-wrap" ref={menuRef}>
          <button
            type="button"
            className="investor-header__action-btn inv-detail-header__menu-btn"
            aria-expanded={menuOpen}
            aria-haspopup="true"
            onClick={() => setMenuOpen((o) => !o)}
          >
            More ▾
          </button>
          {menuOpen ? (
            <div className="inv-detail-header__menu" role="menu">
              {[
                ['View Distributions', 'distributions'],
                ['Statements', 'statements'],
                ['Tax Docs', 'tax-docs'],
                ['Project Report', 'project-report'],
                ['Report Issue', 'report-issue'],
              ].map(([label, key]) => (
                <button
                  key={key}
                  type="button"
                  role="menuitem"
                  className="inv-detail-header__menu-item"
                  onClick={() => {
                    if (key === 'distributions') {
                      onScrollToSection('distributions');
                    } else {
                      handleMenuAction(`${label} will be available in a future release.`);
                    }
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}
