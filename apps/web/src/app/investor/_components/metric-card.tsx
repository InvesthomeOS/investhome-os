import type { Investment, InvestmentStatus } from '../_data/types';
import {
  formatInvestorCurrency,
  formatInvestorDate,
  formatInvestorPercent,
} from '../_data/mock-data';

const STATUS_LABELS: Record<InvestmentStatus, string> = {
  active: 'Active',
  pending: 'Pending',
  matured: 'Matured',
  exited: 'Exited',
};

export interface MetricCardProps {
  investment: Investment;
  locale?: string;
}

export function MetricCard({ investment, locale = 'en-US' }: MetricCardProps) {
  return (
    <article className="inv-metric-card">
      <div className="inv-metric-card__header">
        <div>
          <h3 className="inv-metric-card__title">{investment.name}</h3>
          <p className="inv-section-header__subtitle">
            {investment.location} · {formatInvestorDate(investment.investedAt, locale)}
          </p>
        </div>
        <span className={`inv-metric-card__badge inv-metric-card__badge--${investment.status}`}>
          {STATUS_LABELS[investment.status]}
        </span>
      </div>
      <div className="inv-metric-card__grid">
        <div>
          <div className="inv-metric-card__stat-label">Invested</div>
          <div className="inv-metric-card__stat-value">
            {formatInvestorCurrency(investment.investedAmount, investment.currency, locale)}
          </div>
        </div>
        <div>
          <div className="inv-metric-card__stat-label">Current Value</div>
          <div className="inv-metric-card__stat-value">
            {formatInvestorCurrency(investment.currentValue, investment.currency, locale)}
          </div>
        </div>
        <div>
          <div className="inv-metric-card__stat-label">ROI</div>
          <div className="inv-metric-card__stat-value">
            {investment.roi > 0 ? formatInvestorPercent(investment.roi, locale) : '—'}
          </div>
        </div>
      </div>
    </article>
  );
}
