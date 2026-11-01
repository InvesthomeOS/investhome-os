'use client';

import { useTranslations } from 'next-intl';
import type { InvestmentDetail } from '../../_data/investment-detail-types';
import { formatInvestorCurrency, formatInvestorPercent } from '../../_data/mock-data';
import { SectionHeader } from '../section-header';

export interface InvestorPositionCardProps {
  detail: InvestmentDetail;
}

export function InvestorPositionCard({ detail }: InvestorPositionCardProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const { investment: inv, position } = detail;
  const ownershipPct = inv.ownershipPercent;

  return (
    <section className="inv-detail-panel" aria-labelledby="position-heading">
      <SectionHeader title={tChrome('k5941bdd773')} subtitle={tChrome('ka57163c289')} />
      <div className="inv-position-card">
        <div className="inv-position-card__ring-wrap">
          <svg viewBox="0 0 120 120" className="inv-position-card__ring" aria-hidden="true">
            <circle cx="60" cy="60" r="52" fill="none" stroke="var(--inv-border)" strokeWidth="8" />
            <circle
              cx="60"
              cy="60"
              r="52"
              fill="none"
              stroke="var(--inv-gold)"
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={`${(ownershipPct / 100) * 327} 327`}
              transform="rotate(-90 60 60)"
            />
          </svg>
          <div className="inv-position-card__ring-label">
            <strong>{formatInvestorPercent(ownershipPct)}</strong>
            <span>{tChrome('k3e90e4cbf4')}</span>
          </div>
        </div>
        <dl className="inv-position-card__grid">
          <div>
            <dt>{tChrome('k424f9a1cdd')}</dt>
            <dd>{formatInvestorCurrency(position.committedCapital, inv.currency)}</dd>
          </div>
          <div>
            <dt>{tChrome('k82247eae9a')}</dt>
            <dd>{formatInvestorCurrency(position.calledCapital, inv.currency)}</dd>
          </div>
          <div>
            <dt>{tChrome('k4eb5913188')}</dt>
            <dd>{formatInvestorCurrency(position.uncalledCapital, inv.currency)}</dd>
          </div>
          <div>
            <dt>{tChrome('k2201d74c16')}</dt>
            <dd>{formatInvestorCurrency(position.capitalAccountBalance, inv.currency)}</dd>
          </div>
          <div>
            <dt>{tChrome('kc8fa12e2ec')}</dt>
            <dd>
              {position.ownershipUnits.toLocaleString()} / {position.totalFundUnits.toLocaleString()}
            </dd>
          </div>
          <div>
            <dt>{tChrome('k3e0a85a342')}</dt>
            <dd>{formatInvestorPercent(position.preferredReturnRate)}</dd>
          </div>
          <div>
            <dt>{tChrome('k59a94a3a95')}</dt>
            <dd>{position.profitSplitPercent}% LP / {100 - position.profitSplitPercent}% GP</dd>
          </div>
          <div>
            <dt>{tChrome('kd130b834cb')}</dt>
            <dd>{position.votingRights ? 'Yes' : 'No'}</dd>
          </div>
          <div>
            <dt>{tChrome('k7d6b875a8a')}</dt>
            <dd>{position.capitalCallSchedule}</dd>
          </div>
          {position.nextCapitalCallDate ? (
            <div>
              <dt>{tChrome('k4af515f517')}</dt>
              <dd>{position.nextCapitalCallDate}</dd>
            </div>
          ) : null}
        </dl>
      </div>
    </section>
  );
}
