import type { InvestmentDetail } from '../../_data/investment-detail-types';
import {
  INVESTMENT_STATUS_LABELS,
  RISK_LEVEL_LABELS,
} from '../../_data/investments';
import {
  formatInvestorCurrency,
  formatInvestorDate,
  formatInvestorPercent,
} from '../../_data/mock-data';

export interface InvestmentSummaryPanelProps {
  detail: InvestmentDetail;
}

export function InvestmentSummaryPanel({ detail }: InvestmentSummaryPanelProps) {
  const { investment: inv, summaryPanel } = detail;

  return (
    <aside className="inv-detail-summary" aria-label="Investment summary">
      <div className="inv-detail-summary__card">
        <h2 className="inv-detail-summary__title">At a Glance</h2>

        <dl className="inv-detail-summary__list">
          <div>
            <dt>Status</dt>
            <dd>
              <span className={`inv-investment-card__status inv-investment-card__status--${inv.status}`}>
                {INVESTMENT_STATUS_LABELS[inv.status]}
              </span>
            </dd>
          </div>
          <div>
            <dt>Current Value</dt>
            <dd>{formatInvestorCurrency(inv.currentValue, inv.currency)}</dd>
          </div>
          <div>
            <dt>Ownership</dt>
            <dd>{formatInvestorPercent(inv.ownershipPercent)}</dd>
          </div>
          <div>
            <dt>Next Distribution</dt>
            <dd>
              {inv.distribution.nextDistributionDate
                ? formatInvestorDate(inv.distribution.nextDistributionDate)
                : '—'}
            </dd>
          </div>
          <div>
            <dt>Completion</dt>
            <dd>{inv.progressPercent}%</dd>
          </div>
          <div>
            <dt>Next Milestone</dt>
            <dd>{summaryPanel.nextMilestone}</dd>
          </div>
          <div>
            <dt>Milestone Date</dt>
            <dd>{formatInvestorDate(summaryPanel.nextMilestoneDate)}</dd>
          </div>
          <div>
            <dt>Projected Exit</dt>
            <dd>{inv.exitDate ? formatInvestorDate(inv.exitDate) : '—'}</dd>
          </div>
          <div>
            <dt>Overall Risk</dt>
            <dd>{RISK_LEVEL_LABELS[summaryPanel.overallRiskLevel]}</dd>
          </div>
        </dl>

        <div className="inv-detail-summary__ir">
          <h3>Investor Relations</h3>
          <p className="inv-detail-summary__ir-name">{summaryPanel.irContactName}</p>
          <a href={`mailto:${summaryPanel.irContactEmail}`}>{summaryPanel.irContactEmail}</a>
        </div>
      </div>
    </aside>
  );
}
