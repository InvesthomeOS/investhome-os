'use client';

import { useTranslations } from 'next-intl';

import { investorLabel } from '@/app/investor/_components/investor-labels';
import Link from 'next/link';
import type { Route } from 'next';

import type { Distribution } from '../../_data/distribution-types';
import { getUpcomingTotals } from '../../_data/distribution-calculations';
import { formatInvestorCurrency, formatInvestorDate } from '../../_data/mock-data';
import { SectionHeader } from '../section-header';

export interface UpcomingDistributionCardProps {
  upcoming: Distribution[];
  allDistributions: Distribution[];
}

export function UpcomingDistributionCard({
  upcoming,
  allDistributions,
}: UpcomingDistributionCardProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const tLabels = useTranslations('investorPortal.labels');
  const totals = getUpcomingTotals(allDistributions);
  const currency = upcoming[0]?.currency ?? 'USD';

  return (
    <section className="inv-distributions__panel inv-distributions__upcoming">
      <SectionHeader
        title={tChrome('k158b786f14')}
        subtitle={tChrome('k53b569d6b0')}
      />

      {upcoming.length === 0 ? (
        <p className="inv-distributions__empty-note">{tChrome('k6b2de4b36f')}</p>
      ) : (
        <>
          <ul className="inv-distributions__upcoming-list">
            {upcoming.map((d, i) => (
              <li key={d.id} className="inv-distributions__upcoming-item">
                <div className="inv-distributions__upcoming-rank">
                  {i === 0 ? 'Next' : `#${i + 1}`}
                </div>
                <div className="inv-distributions__upcoming-body">
                  <Link
                    href={`/investor/distributions/${d.id}` as Route}
                    className="inv-distributions__link"
                  >
                    {d.investmentName}
                  </Link>
                  <span className="inv-distributions__upcoming-meta">
                    {d.periodLabel} · {investorLabel(tLabels, 'distributionType', d.distributionType)}
                  </span>
                </div>
                <div className="inv-distributions__upcoming-amount">
                  <strong>{formatInvestorCurrency(d.breakdown.netAmount, d.currency)}</strong>
                  <span className="inv-distributions__estimate-badge">{tChrome('k18b405fba8')}</span>
                  <time dateTime={d.paymentDate} className="inv-distributions__upcoming-date">
                    {formatInvestorDate(d.paymentDate)}
                  </time>
                  <span
                    className={`inv-distributions__status inv-distributions__status--${d.status}`}
                  >
                    {investorLabel(tLabels, 'distributionStatus', d.status)}
                  </span>
                </div>
              </li>
            ))}
          </ul>

          <div className="inv-distributions__upcoming-totals">
            <div>
              <span>{tChrome('ke401fc6a4e')}</span>
              <strong>{formatInvestorCurrency(totals.days30, currency)}</strong>
            </div>
            <div>
              <span>{tChrome('ka62240b037')}</span>
              <strong>{formatInvestorCurrency(totals.days90, currency)}</strong>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
