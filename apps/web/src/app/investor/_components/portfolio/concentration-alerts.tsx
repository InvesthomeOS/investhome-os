'use client';

import { useTranslations } from 'next-intl';

import { SectionHeader } from '../section-header';
import type { PortfolioConcentrationAlert } from '../../_data/portfolio-types';
import { formatInvestorCurrency } from '../../_data/mock-data';

export interface ConcentrationAlertsProps {
  alerts: PortfolioConcentrationAlert[];
  currency: string;
}

const SEVERITY_CLASS: Record<PortfolioConcentrationAlert['severity'], string> = {
  low: 'inv-portfolio-alert--low',
  medium: 'inv-portfolio-alert--medium',
  high: 'inv-portfolio-alert--high',
  critical: 'inv-portfolio-alert--critical',
};

export function ConcentrationAlerts({ alerts, currency }: ConcentrationAlertsProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  return (
    <section className="inv-portfolio-panel">
      <SectionHeader
        title={tChrome('kca1ace90ac')}
        subtitle={tChrome('k656e75e5f5')}
      />
      {alerts.length === 0 ? (
        <p className="inv-portfolio-panel__empty">{tChrome('k4b5138f00e')}</p>
      ) : (
        <ul className="inv-portfolio-alerts">
          {alerts.map((alert) => (
            <li
              key={alert.id}
              className={`inv-portfolio-alert ${SEVERITY_CLASS[alert.severity]}`}
            >
              <div className="inv-portfolio-alert__header">
                <span className="inv-portfolio-alert__category">{alert.category.replace('_', ' ')}</span>
                <span className="inv-portfolio-alert__severity">{alert.severity}</span>
              </div>
              <h3 className="inv-portfolio-alert__title">{alert.title}</h3>
              <p className="inv-portfolio-alert__desc">{alert.description}</p>
              <dl className="inv-portfolio-alert__meta">
                <div>
                  <dt>{tChrome('k862ee3b17a')}</dt>
                  <dd>
                    {formatInvestorCurrency(alert.exposure, currency)} ({alert.exposurePercent.toFixed(1)}%)
                  </dd>
                </div>
                <div>
                  <dt>{tChrome('kc51f7b7227')}</dt>
                  <dd>{alert.threshold}%</dd>
                </div>
              </dl>
              <p className="inv-portfolio-alert__action">
                <strong>{tChrome('kff3bf4a012')}</strong> {alert.suggestedAction}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
