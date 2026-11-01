'use client';

import { useTranslations } from 'next-intl';

import Link from 'next/link';
import type { Route } from 'next';

import type { Distribution } from '../../_data/distribution-types';
import { computePreferredReturnByInvestment } from '../../_data/distribution-calculations';
import { formatInvestorCurrency, formatInvestorPercent } from '../../_data/mock-data';
import { SectionHeader } from '../section-header';

export interface PreferredReturnSectionProps {
  distributions: Distribution[];
}

export function PreferredReturnSection({ distributions }: PreferredReturnSectionProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const tracking = computePreferredReturnByInvestment(distributions);

  return (
    <section className="inv-distributions__panel">
      <SectionHeader
        title={tChrome('k222c0eb86f')}
        subtitle={tChrome('k2c098d4160')}
      />

      <div className="inv-distributions__table-wrap">
        <table className="inv-distributions__table">
          <thead>
            <tr>
              <th scope="col">{tChrome('k0401729c31')}</th>
              <th scope="col">{tChrome('k3a9c736b31')}</th>
              <th scope="col">{tChrome('k8bf7ef1ac9')}</th>
              <th scope="col">{tChrome('kdc9d4584a5')}</th>
              <th scope="col">{tChrome('kf8ee57ec86')}</th>
              <th scope="col">{tChrome('k1b90271d66')}</th>
            </tr>
          </thead>
          <tbody>
            {tracking.map((t) => {
              const pct =
                t.cumulativePreferred > 0
                  ? Math.min((t.cumulativePaid / t.cumulativePreferred) * 100, 100)
                  : 0;
              return (
                <tr key={t.investmentId}>
                  <td>
                    <Link
                      href={`/investor/investments/${t.investmentId}` as Route}
                      className="inv-distributions__link"
                    >
                      {t.investmentName}
                    </Link>
                  </td>
                  <td>{formatInvestorPercent(t.preferredRate)}</td>
                  <td>{formatInvestorCurrency(t.cumulativePreferred, t.currency)}</td>
                  <td>{formatInvestorCurrency(t.cumulativePaid, t.currency)}</td>
                  <td>{formatInvestorCurrency(t.outstandingPreferred, t.currency)}</td>
                  <td>
                    <div className="inv-distributions__progress">
                      <div
                        className="inv-distributions__progress-fill"
                        style={{ width: `${pct}%` }}
                        role="progressbar"
                        aria-valuenow={pct}
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-label={`${t.investmentName} preferred return ${pct.toFixed(0)}% paid`}
                      />
                      <span>{pct.toFixed(0)}%</span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
