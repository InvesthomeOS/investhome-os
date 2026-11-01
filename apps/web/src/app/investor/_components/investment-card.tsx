'use client';

import { useTranslations } from 'next-intl';

import { investorLabel } from '@/app/investor/_components/investor-labels';
import Link from 'next/link';
import type { Route } from 'next';

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
  const tChrome = useTranslations('investorPortal.chrome');
  const tLabels = useTranslations('investorPortal.labels');
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
          {investorLabel(tLabels, 'investmentStatus', investment.status)}
        </span>
        <span
          className={`inv-investment-card__risk inv-investment-card__risk--${investment.riskLevel}`}
        >
          {investorLabel(tLabels, 'riskLevel', investment.riskLevel)}
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
          <span className="inv-investment-card__tag">{investorLabel(tLabels, 'investmentType', investment.type)}</span>
          <span className="inv-investment-card__tag">{investorLabel(tLabels, 'projectStage', investment.stage)}</span>
        </div>

        <div className="inv-investment-card__progress" aria-label={`${investment.progressPercent}% complete`}>
          <div className="inv-investment-card__progress-header">
            <span>{tChrome('k1b90271d66')}</span>
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
            <dt>{tChrome('ka13c9ad2ae')}</dt>
            <dd>{formatInvestorCurrency(investment.investedAmount, investment.currency)}</dd>
          </div>
          <div>
            <dt>{tChrome('k4f99315301')}</dt>
            <dd>{formatInvestorCurrency(investment.currentValue, investment.currency)}</dd>
          </div>
          <div>
            <dt>{tChrome('k3e90e4cbf4')}</dt>
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
            <dt>{tChrome('k4d78e9f9ed')}</dt>
            <dd>
              {investment.performance.annualCashFlow > 0
                ? formatInvestorCurrency(investment.performance.annualCashFlow, investment.currency)
                : '—'}
            </dd>
          </div>
          <div>
            <dt>{tChrome('k5f3fc5b59f')}</dt>
            <dd>{formatInvestorDate(investment.investmentDate)}</dd>
          </div>
          <div>
            <dt>{tChrome('k4ba00f0c12')}</dt>
            <dd>
              {investment.distribution.nextDistributionDate
                ? formatInvestorDate(investment.distribution.nextDistributionDate)
                : '—'}
            </dd>
          </div>
          <div>
            <dt>{tChrome('k2fc2138254')}</dt>
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
