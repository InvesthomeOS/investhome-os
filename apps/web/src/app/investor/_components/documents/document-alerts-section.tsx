'use client';

import { useTranslations } from 'next-intl';

import Link from 'next/link';
import type { Route } from 'next';

import { investorChrome } from '@/app/investor/_components/investor-labels';
import type { DocumentAlert } from '../../_data/document-types';
import { SectionHeader } from '../section-header';

function alertMessage(
  alert: DocumentAlert,
  tAlerts: ReturnType<typeof useTranslations<'investorPortal.alerts'>>,
  tChrome: ReturnType<typeof useTranslations<'investorPortal.chrome'>>,
): string {
  const quoted = alert.message.match(/^"(.+)"/);
  const title = quoted?.[1] ?? '';
  const days = alert.message.match(/expires in (\d+) days/);
  if (alert.title === 'Signature Required' && days) {
    return tAlerts('signatureExpires', { title, days: Number(days[1]) });
  }
  if (alert.title === 'Signature Required' && alert.message.includes('expiring soon')) {
    return tAlerts('signatureSoon', { title });
  }
  if (alert.title === 'New Document') {
    return tAlerts('newAvailable', { title });
  }
  return investorChrome(tChrome, alert.message);
}

export interface DocumentAlertsSectionProps {
  alerts: DocumentAlert[];
}

export function DocumentAlertsSection({ alerts }: DocumentAlertsSectionProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const tAlerts = useTranslations('investorPortal.alerts');
  if (alerts.length === 0) return null;

  return (
    <section className="inv-docs__alerts" aria-labelledby="doc-alerts-heading">
      <SectionHeader title={tChrome('k74fe93fc0c')} subtitle={tAlerts('activeCount', { count: alerts.length })} />
      <ul className="inv-docs__alerts-list">
        {alerts.slice(0, 6).map((alert) => (
          <li key={alert.id} className={`inv-docs__alert inv-docs__alert--${alert.severity}`}>
            <div>
              <strong>{investorChrome(tChrome, alert.title)}</strong>
              <p>{alertMessage(alert, tAlerts, tChrome)}</p>
            </div>
            <Link href={alert.actionHref as Route} className="inv-docs__alert-action">
              {investorChrome(tChrome, alert.actionLabel)}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
