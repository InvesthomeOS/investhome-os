'use client';

import { useTranslations } from 'next-intl';

import Link from 'next/link';
import type { Route } from 'next';

import type { Distribution } from '../../_data/distribution-types';
import { computeReturnOfCapital } from '../../_data/distribution-calculations';
import { formatInvestorCurrency, formatInvestorPercent } from '../../_data/mock-data';
import { SectionHeader } from '../section-header';

export interface RocTrackingSectionProps {
  distributions: Distribution[];
}

export function RocTrackingSection({ distributions }: RocTrackingSectionProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const tracking = computeReturnOfCapital(distributions).filter(
    (t) => t.capitalReturned > 0 || t.investedAmount > 0,
  );

  return (
    <section className="inv-distributions__panel">
      <SectionHeader
        title={tChrome('kb3f76c28dc')}
        subtitle={tChrome('kd22a990df2')}
      />

      <ul className="inv-distributions__roc-list">
        {tracking.map((t) => (
          <li key={t.investmentId} className="inv-distributions__roc-item">
            <div className="inv-distributions__roc-header">
              <Link
                href={`/investor/investments/${t.investmentId}` as Route}
                className="inv-distributions__link"
              >
                {t.investmentName}
              </Link>
              <strong>{formatInvestorPercent(t.percentReturned)}</strong>
            </div>
            <div className="inv-distributions__progress inv-distributions__progress--large">
              <div
                className="inv-distributions__progress-fill"
                style={{ width: `${Math.min(t.percentReturned, 100)}%` }}
                role="progressbar"
                aria-valuenow={t.percentReturned}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`${t.investmentName} ${t.percentReturned.toFixed(0)}% capital returned`}
              />
            </div>
            <dl className="inv-distributions__roc-stats">
              <div>
                <dt>{tChrome('ka13c9ad2ae')}</dt>
                <dd>{formatInvestorCurrency(t.investedAmount, t.currency)}</dd>
              </div>
              <div>
                <dt>{tChrome('k870770a9de')}</dt>
                <dd>{formatInvestorCurrency(t.capitalReturned, t.currency)}</dd>
              </div>
              <div>
                <dt>{tChrome('kcc632b5e2f')}</dt>
                <dd>{formatInvestorCurrency(t.remainingCapital, t.currency)}</dd>
              </div>
            </dl>
          </li>
        ))}
      </ul>
    </section>
  );
}
