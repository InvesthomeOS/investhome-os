import type { InvestmentDetail } from '../../_data/investment-detail-types';
import { RISK_LEVEL_LABELS } from '../../_data/investments';
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
  const { risks, summaryPanel } = detail;
  const openCount = risks.filter((r) => r.status === 'open' || r.status === 'monitoring').length;
  const highPriority = risks.filter((r) => r.severity === 'high' || r.severity === 'critical').length;
  const mitigated = risks.filter((r) => r.status === 'mitigated' || r.status === 'closed').length;

  return (
    <section className="inv-detail-panel" aria-labelledby="risks-heading">
      <SectionHeader title="Risk Assessment" subtitle="Transparent risk disclosure for this investment" />

      <div className="inv-detail-risks__summary">
        <div className={`inv-detail-risks__overall inv-detail-risks__overall--${summaryPanel.overallRiskLevel}`}>
          <span>Overall Risk Level</span>
          <strong>{RISK_LEVEL_LABELS[summaryPanel.overallRiskLevel]}</strong>
        </div>
        <dl className="inv-detail-risks__counts">
          <div>
            <dt>Open / Monitoring</dt>
            <dd>{openCount}</dd>
          </div>
          <div>
            <dt>High Priority</dt>
            <dd>{highPriority}</dd>
          </div>
          <div>
            <dt>Mitigated / Closed</dt>
            <dd>{mitigated}</dd>
          </div>
        </dl>
      </div>

      <ul className="inv-detail-risks__list" aria-label="Risk items">
        {risks.map((risk) => (
          <li key={risk.id} className={`inv-detail-risks__item inv-detail-risks__item--${risk.severity}`}>
            <div className="inv-detail-risks__item-header">
              <h3 className="inv-detail-risks__title">{risk.title}</h3>
              <div className="inv-detail-risks__badges">
                <span className={`inv-detail-risks__severity inv-detail-risks__severity--${risk.severity}`}>
                  {SEVERITY_LABELS[risk.severity]}
                </span>
                <span className={`inv-detail-risks__status inv-detail-risks__status--${risk.status}`}>
                  {STATUS_LABELS[risk.status]}
                </span>
              </div>
            </div>
            <p className="inv-detail-risks__desc">{risk.description}</p>
            {risk.mitigationPlan ? (
              <p className="inv-detail-risks__mitigation">
                <strong>Mitigation:</strong> {risk.mitigationPlan}
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
