'use client';

import { useTranslations } from 'next-intl';
import { investorChrome, investorLabel } from '@/app/investor/_components/investor-labels';
import type { InvestmentDetail } from '../../_data/investment-detail-types';
import { SectionHeader } from '../section-header';

const SEVERITY_LABELS: Record<string, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  critical: 'Critical',
};

const STATUS_LABELS: Record<string, string> = {
  open: 'Open',
  monitoring: 'Monitoring',
  mitigated: 'Mitigated',
  closed: 'Closed',
};

export interface RisksSectionProps {
  detail: InvestmentDetail;
}

export function RisksSection({ detail }: RisksSectionProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const tLabels = useTranslations('investorPortal.labels');
  const { risks, summaryPanel } = detail;
  const openCount = risks.filter((r) => r.status === 'open' || r.status === 'monitoring').length;
  const highPriority = risks.filter((r) => r.severity === 'high' || r.severity === 'critical').length;
  const mitigated = risks.filter((r) => r.status === 'mitigated' || r.status === 'closed').length;

  return (
    <section className="inv-detail-panel" aria-labelledby="risks-heading">
      <SectionHeader title={tChrome('k8db7e62e23')} subtitle={tChrome('kf4000b9641')} />

      <div className="inv-detail-risks__summary">
        <div className={`inv-detail-risks__overall inv-detail-risks__overall--${summaryPanel.overallRiskLevel}`}>
          <span>{tChrome('k13a99db4c7')}</span>
          <strong>{investorLabel(tLabels, 'riskLevel', summaryPanel.overallRiskLevel)}</strong>
        </div>
        <dl className="inv-detail-risks__counts">
          <div>
            <dt>{tChrome('ke7c38e0a6d')}</dt>
            <dd>{openCount}</dd>
          </div>
          <div>
            <dt>{tChrome('kc9ccd69274')}</dt>
            <dd>{highPriority}</dd>
          </div>
          <div>
            <dt>{tChrome('k3cb21eb4a5')}</dt>
            <dd>{mitigated}</dd>
          </div>
        </dl>
      </div>

      <ul className="inv-detail-risks__list" aria-label={tChrome('k8872058e6d')}>
        {risks.map((risk) => (
          <li key={risk.id} className={`inv-detail-risks__item inv-detail-risks__item--${risk.severity}`}>
            <div className="inv-detail-risks__item-header">
              <h3 className="inv-detail-risks__title">{risk.title}</h3>
              <div className="inv-detail-risks__badges">
                <span className={`inv-detail-risks__severity inv-detail-risks__severity--${risk.severity}`}>
                  {investorChrome(tChrome, SEVERITY_LABELS[risk.severity] ?? '')}
                </span>
                <span className={`inv-detail-risks__status inv-detail-risks__status--${risk.status}`}>
                  {investorChrome(tChrome, STATUS_LABELS[risk.status] ?? '')}
                </span>
              </div>
            </div>
            <p className="inv-detail-risks__desc">{risk.description}</p>
            {risk.mitigationPlan ? (
              <p className="inv-detail-risks__mitigation">
                <strong>{tChrome('kbe05664148')}</strong> {risk.mitigationPlan}
              </p>
            ) : null}
            <p className="inv-detail-risks__meta">
              {risk.category} · Last reviewed {risk.lastReviewed}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
