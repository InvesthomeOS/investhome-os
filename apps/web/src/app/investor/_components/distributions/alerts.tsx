'use client';

import Link from 'next/link';
import type { Route } from 'next';

import type { DistributionAlert } from '../../_data/distribution-types';
import { SectionHeader } from '../section-header';

export interface AlertsSectionProps {
  alerts: DistributionAlert[];
  onAction?: (alert: DistributionAlert) => void;
}

export function AlertsSection({ alerts, onAction }: AlertsSectionProps) {
  return (
    <section className="inv-distributions__panel inv-distributions__alerts">
      <SectionHeader title="Alerts & Exceptions" subtitle="Issues requiring attention" />

      <ul className="inv-distributions__alerts-list">
        {alerts.map((alert) => (
          <li
            key={alert.id}
            className={`inv-distributions__alert inv-distributions__alert--${alert.severity}`}
          >
            <div>
              <h3>{alert.title}</h3>
              <p>{alert.description}</p>
            </div>
            <div className="inv-distributions__alert-actions">
              {alert.distributionId ? (
                <Link
                  href={`/investor/distributions/${alert.distributionId}` as Route}
                  className="inv-distributions__alert-link"
                >
                  View Details
                </Link>
              ) : null}
              {alert.actionLabel && onAction ? (
                <button type="button" className="inv-distributions__alert-btn" onClick={() => onAction(alert)}>
                  {alert.actionLabel}
                </button>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
