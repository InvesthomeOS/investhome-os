'use client';

import Link from 'next/link';
import type { Route } from 'next';

import type { DocumentAlert } from '../../_data/document-types';
import { SectionHeader } from '../section-header';

export interface DocumentAlertsSectionProps {
  alerts: DocumentAlert[];
}

export function DocumentAlertsSection({ alerts }: DocumentAlertsSectionProps) {
  if (alerts.length === 0) return null;

  return (
    <section className="inv-docs__alerts" aria-labelledby="doc-alerts-heading">
      <SectionHeader title="Document Alerts" subtitle={`${alerts.length} active alerts`} />
      <ul className="inv-docs__alerts-list">
        {alerts.slice(0, 6).map((alert) => (
          <li key={alert.id} className={`inv-docs__alert inv-docs__alert--${alert.severity}`}>
            <div>
              <strong>{alert.title}</strong>
              <p>{alert.message}</p>
            </div>
            <Link href={alert.actionHref as Route} className="inv-docs__alert-action">
              {alert.actionLabel}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
