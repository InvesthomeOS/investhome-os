'use client';

import { useTranslations } from 'next-intl';
import { investorLabel } from '@/app/investor/_components/investor-labels';
import type { InvestmentDetail } from '../../_data/investment-detail-types';
import {
  formatInvestorCurrency,
  formatInvestorDate,
  formatInvestorPercent,
} from '../../_data/mock-data';

export interface InvestmentSummaryPanelProps {
  detail: InvestmentDetail;
}

export function InvestmentSummaryPanel({ detail }: InvestmentSummaryPanelProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const tLabels = useTranslations('investorPortal.labels');
  const { investment: inv, summaryPanel } = detail;

  return (
    <aside className="inv-detail-summary" aria-label={tChrome('k3fd0423cd9')}>
      <div className="inv-detail-summary__card">
        <h2 className="inv-detail-summary__title">{tChrome('ka25567010c')}</h2>

        <dl className="inv-detail-summary__list">
          <div>
            <dt>{tChrome('kbae7d5be70')}</dt>
            <dd>
              <span className={`inv-investment-card__status inv-investment-card__status--${inv.status}`}>
                {investorLabel(tLabels, 'investmentStatus', inv.status)}
              </span>
            </dd>
          </div>
          <div>
            <dt>{tChrome('k4f99315301')}</dt>
            <dd>{formatInvestorCurrency(inv.currentValue, inv.currency)}</dd>
          </div>
          <div>
            <dt>{tChrome('k3e90e4cbf4')}</dt>
            <dd>{formatInvestorPercent(inv.ownershipPercent)}</dd>
          </div>
          <div>
            <dt>{tChrome('k4ba00f0c12')}</dt>
            <dd>
              {inv.distribution.nextDistributionDate
                ? formatInvestorDate(inv.distribution.nextDistributionDate)
                : '—'}
            </dd>
          </div>
          <div>
            <dt>{tChrome('k2ff255684a')}</dt>
            <dd>{inv.progressPercent}%</dd>
          </div>
          <div>
            <dt>{tChrome('k89884c1481')}</dt>
            <dd>{summaryPanel.nextMilestone}</dd>
          </div>
          <div>
            <dt>{tChrome('kecbab4e55e')}</dt>
            <dd>{formatInvestorDate(summaryPanel.nextMilestoneDate)}</dd>
          </div>
          <div>
            <dt>{tChrome('k2bb25d81c8')}</dt>
            <dd>{inv.exitDate ? formatInvestorDate(inv.exitDate) : '—'}</dd>
          </div>
          <div>
            <dt>{tChrome('kbf78c7922a')}</dt>
            <dd>{investorLabel(tLabels, 'riskLevel', summaryPanel.overallRiskLevel)}</dd>
          </div>
        </dl>

        <div className="inv-detail-summary__ir">
          <h3>{tChrome('k3a49ad474d')}</h3>
          <p className="inv-detail-summary__ir-name">{summaryPanel.irContactName}</p>
          <a href={`mailto:${summaryPanel.irContactEmail}`}>{summaryPanel.irContactEmail}</a>
        </div>
      </div>
    </aside>
  );
}
