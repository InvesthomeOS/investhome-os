'use client';

import Link from 'next/link';
import type { Route } from 'next';

import {
  INVESTMENT_STATUS_LABELS,
  INVESTMENT_TYPE_LABELS,
  PROJECT_STAGE_LABELS,
  RISK_LEVEL_LABELS,
} from '../_data/investments';
import type { PortfolioInvestment } from '../_data/investment-types';
import {
  formatInvestorCurrency,
  formatInvestorDate,
  formatInvestorPercent,
} from '../_data/mock-data';

export interface InvestmentCardProps {
  investment: PortfolioInvestment;
}

export function InvestmentCard({ investment }: InvestmentCardProps) {
  const detailHref = `/investor/investments/${investment.id}` as Route;
  const location = `${investment.city}, ${investment.state}`;

  return (
    <article className="inv-investment-card">
      <div className="inv-investment-card__media">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={investment.imageUrl}
          alt={`${investment.projectName} property`}
          className="inv-investment-card__image"
          loading="lazy"
        />
        <span
          className={`inv-investment-card__status inv-investment-card__status--${investment.status}`}
        >
          {INVESTMENT_STATUS_LABELS[investment.status]}
        </span>
        <span
          className={`inv-investment-card__risk inv-investment-card__risk--${investment.riskLevel}`}
        >
          {RISK_LEVEL_LABELS[investment.riskLevel]}
        </span>
      </div>

      <div className="inv-investment-card__body">
        <header className="inv-investment-card__header">
          <div>
            <h3 className="inv-investment-card__title">{investment.projectName}</h3>
            <p className="inv-investment-card__address">
              {investment.address} · {location}
            </p>
            <p className="inv-investment-card__entity">{investment.entityName}</p>
          </div>
        </header>

        <div className="inv-investment-card__tags">
          <span className="inv-investment-card__tag">{INVESTMENT_TYPE_LABELS[investment.type]}</span>
          <span className="inv-investment-card__tag">{PROJECT_STAGE_LABELS[investment.stage]}</span>
        </div>

        <div className="inv-investment-card__progress" aria-label={`${investment.progressPercent}% complete`}>
          <div className="inv-investment-card__progress-header">
            <span>Progress</span>
            <span>{investment.progressPercent}%</span>
          </div>
          <div className="inv-investment-card__progress-track">
            <div
              className="inv-investment-card__progress-bar"
              style={{ width: `${investment.progressPercent}%` }}
              role="progressbar"
              aria-valuenow={investment.progressPercent}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>
        </div>

        <dl className="inv-investment-card__stats">
          <div>
            <dt>Invested</dt>
            <dd>{formatInvestorCurrency(investment.investedAmount, investment.currency)}</dd>
          </div>
          <div>
            <dt>Current Value</dt>
            <dd>{formatInvestorCurrency(investment.currentValue, investment.currency)}</dd>
          </div>
          <div>
            <dt>Ownership</dt>
            <dd>{formatInvestorPercent(investment.ownershipPercent)}</dd>
          </div>
          <div>
            <dt>ROI</dt>
            <dd>
              {investment.performance.roi > 0
                ? formatInvestorPercent(investment.performance.roi)
                : '—'}
            </dd>
          </div>
          <div>
            <dt>IRR</dt>
            <dd>
              {investment.performance.irr > 0
                ? formatInvestorPercent(investment.performance.irr)
                : '—'}
            </dd>
          </div>
          <div>
            <dt>Cash Flow</dt>
            <dd>
              {investment.performance.annualCashFlow > 0
                ? formatInvestorCurrency(investment.performance.annualCashFlow, investment.currency)
                : '—'}
            </dd>
          </div>
          <div>
            <dt>Invested On</dt>
            <dd>{formatInvestorDate(investment.investmentDate)}</dd>
          </div>
          <div>
            <dt>Next Distribution</dt>
            <dd>
              {investment.distribution.nextDistributionDate
                ? formatInvestorDate(investment.distribution.nextDistributionDate)
                : '—'}
            </dd>
          </div>
          <div>
            <dt>Exit Date</dt>
            <dd>{investment.exitDate ? formatInvestorDate(investment.exitDate) : '—'}</dd>
          </div>
        </dl>

        <footer className="inv-investment-card__footer">
          <Link href={detailHref} className="inv-investment-card__cta">
            View Details
          </Link>
        </footer>
      </div>
    </article>
  );
}
