'use client';

import { useTranslations } from 'next-intl';

import Link from 'next/link';
import type { Route } from 'next';

import type { InvestmentDetail } from '../../_data/investment-detail-types';
import { formatInvestorCurrency, formatInvestorDate } from '../../_data/mock-data';
import { SectionHeader } from '../section-header';

const TYPE_LABELS: Record<string, string> = {
  cash: 'Cash Distribution',
  return_of_capital: 'Return of Capital',
  preferred_return: 'Preferred Return',
  profit_share: 'Profit Share',
  final: 'Final Distribution',
};

const STATUS_LABELS: Record<string, string> = {
  paid: 'Paid',
  pending: 'Pending',
  scheduled: 'Scheduled',
};

export interface DistributionsSectionProps {
  detail: InvestmentDetail;
}

export function DistributionsSection({ detail }: DistributionsSectionProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const { distributions, investment: inv } = detail;
  const totalPaid = distributions
    .filter((d) => d.status === 'paid')
    .reduce((sum, d) => sum + d.amount, 0);
  const scheduled = distributions.filter((d) => d.status === 'scheduled');
  const lastPaid = distributions.find((d) => d.status === 'paid');

  return (
    <section className="inv-detail-panel" aria-labelledby="distributions-heading">
      <SectionHeader
        title={tChrome('k71fff5ea85')}
        subtitle={tChrome('k895888f642')}
        actionLabel="View All"
        onAction={() => {
          window.location.href = '/investor/distributions';
        }}
      />

      <div className="inv-detail-distributions__summary">
        <div className="inv-detail-distributions__metric">
          <span>{tChrome('k7544a03486')}</span>
          <strong>{formatInvestorCurrency(inv.distribution.totalDistributed, inv.currency)}</strong>
        </div>
        <div className="inv-detail-distributions__metric">
          <span>{tChrome('k91316df3da')}</span>
          <strong>{formatInvestorCurrency(totalPaid, inv.currency)}</strong>
        </div>
        <div className="inv-detail-distributions__metric">
          <span>{tChrome('k4ba00f0c12')}</span>
          <strong>
            {inv.distribution.nextDistributionDate
              ? formatInvestorDate(inv.distribution.nextDistributionDate)
              : '—'}
          </strong>
        </div>
        <div className="inv-detail-distributions__metric">
          <span>{tChrome('kcec3d948d9')}</span>
          <strong>
            {lastPaid ? formatInvestorDate(lastPaid.date) : '—'}
          </strong>
        </div>
      </div>

      <div className="inv-detail-table-wrap">
        <table className="inv-detail-table">
          <caption className="inv-investments__sr-only">{tChrome('k189c46c3a8')}</caption>
          <thead>
            <tr>
              <th scope="col">{tChrome('keb9a4bc1c0')}</th>
              <th scope="col">{tChrome('k3deb745651')}</th>
              <th scope="col">{tChrome('k43dc8532f7')}</th>
              <th scope="col">{tChrome('kbae7d5be70')}</th>
              <th scope="col">{tChrome('kc80ec709bc')}</th>
              <th scope="col">{tChrome('k88306943fe')}</th>
              <th scope="col">{tChrome('kdb1c784524')}</th>
            </tr>
          </thead>
          <tbody>
            {distributions.map((d) => (
              <tr key={d.id}>
                <td>
                  <time dateTime={d.date}>{formatInvestorDate(d.date)}</time>
                </td>
                <td>{TYPE_LABELS[d.type] ?? d.type}</td>
                <td>{formatInvestorCurrency(d.amount, inv.currency)}</td>
                <td>
                  <span className={`inv-detail-distributions__status inv-detail-distributions__status--${d.status}`}>
                    {STATUS_LABELS[d.status] ?? d.status}
                  </span>
                </td>
                <td>{d.taxYear}</td>
                <td>{d.paymentMethod}</td>
                <td>{d.reference}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {scheduled.length > 0 ? (
        <p className="inv-detail-distributions__note">
          {scheduled.length} scheduled payment{scheduled.length > 1 ? 's' : ''} upcoming.
        </p>
      ) : null}

      <Link href={'/investor/distributions' as Route} className="inv-section-header__action inv-detail-distributions__link">
        View all distributions →
      </Link>
    </section>
  );
}
