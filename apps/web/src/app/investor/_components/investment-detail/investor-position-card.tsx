import type { InvestmentDetail } from '../../_data/investment-detail-types';
import { formatInvestorCurrency, formatInvestorPercent } from '../../_data/mock-data';
import { SectionHeader } from '../section-header';

export interface InvestorPositionCardProps {
  detail: InvestmentDetail;
}

export function InvestorPositionCard({ detail }: InvestorPositionCardProps) {
  const { investment: inv, position } = detail;
  const ownershipPct = inv.ownershipPercent;

  return (
    <section className="inv-detail-panel" aria-labelledby="position-heading">
      <SectionHeader title="Your Position" subtitle="Capital account and ownership details" />
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
            <span>Ownership</span>
          </div>
        </div>
        <dl className="inv-position-card__grid">
          <div>
            <dt>Committed Capital</dt>
            <dd>{formatInvestorCurrency(position.committedCapital, inv.currency)}</dd>
          </div>
          <div>
            <dt>Called Capital</dt>
            <dd>{formatInvestorCurrency(position.calledCapital, inv.currency)}</dd>
          </div>
          <div>
            <dt>Uncalled Capital</dt>
            <dd>{formatInvestorCurrency(position.uncalledCapital, inv.currency)}</dd>
          </div>
          <div>
            <dt>Capital Account</dt>
            <dd>{formatInvestorCurrency(position.capitalAccountBalance, inv.currency)}</dd>
          </div>
          <div>
            <dt>Ownership Units</dt>
            <dd>
              {position.ownershipUnits.toLocaleString()} / {position.totalFundUnits.toLocaleString()}
            </dd>
          </div>
          <div>
            <dt>Preferred Return</dt>
            <dd>{formatInvestorPercent(position.preferredReturnRate)}</dd>
          </div>
          <div>
            <dt>Profit Split</dt>
            <dd>{position.profitSplitPercent}% LP / {100 - position.profitSplitPercent}% GP</dd>
          </div>
          <div>
            <dt>Voting Rights</dt>
            <dd>{position.votingRights ? 'Yes' : 'No'}</dd>
          </div>
          <div>
            <dt>Capital Call Schedule</dt>
            <dd>{position.capitalCallSchedule}</dd>
          </div>
          {position.nextCapitalCallDate ? (
            <div>
              <dt>Next Capital Call</dt>
              <dd>{position.nextCapitalCallDate}</dd>
            </div>
          ) : null}
        </dl>
      </div>
    </section>
  );
}
