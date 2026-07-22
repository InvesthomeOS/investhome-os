'use client';

import Link from 'next/link';
import type { Route } from 'next';

import type { Distribution } from '../../_data/distribution-types';
import { getUpcomingTotals } from '../../_data/distribution-calculations';
import {
  DISTRIBUTION_STATUS_LABELS,
  DISTRIBUTION_TYPE_LABELS,
} from '../../_data/distributions';
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
  const totals = getUpcomingTotals(allDistributions);
  const currency = upcoming[0]?.currency ?? 'USD';

  return (
    <section className="inv-distributions__panel inv-distributions__upcoming">
      <SectionHeader
        title="Upcoming Distributions"
        subtitle="Next scheduled payments — amounts are estimates until declared"
      />

      {upcoming.length === 0 ? (
        <p className="inv-distributions__empty-note">No upcoming distributions scheduled.</p>
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
                    {d.periodLabel} · {DISTRIBUTION_TYPE_LABELS[d.distributionType]}
                  </span>
                </div>
                <div className="inv-distributions__upcoming-amount">
                  <strong>{formatInvestorCurrency(d.breakdown.netAmount, d.currency)}</strong>
                  <span className="inv-distributions__estimate-badge">Est.</span>
                  <time dateTime={d.paymentDate} className="inv-distributions__upcoming-date">
                    {formatInvestorDate(d.paymentDate)}
                  </time>
                  <span
                    className={`inv-distributions__status inv-distributions__status--${d.status}`}
                  >
                    {DISTRIBUTION_STATUS_LABELS[d.status]}
                  </span>
                </div>
              </li>
            ))}
          </ul>

          <div className="inv-distributions__upcoming-totals">
            <div>
              <span>30-day total (est.)</span>
              <strong>{formatInvestorCurrency(totals.days30, currency)}</strong>
            </div>
            <div>
              <span>90-day total (est.)</span>
              <strong>{formatInvestorCurrency(totals.days90, currency)}</strong>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
