'use client';

import { useTranslations } from 'next-intl';

import Link from 'next/link';
import type { Route } from 'next';

import { formatInvestorDateTime } from '../../_data/mock-data';
import type { SignatureAuditEntry, SignatureRequest } from '../../_data/document-types';
import { sanitizePlainText } from '../../_utils/sanitize-text';

export function SignatureAuditTrail({ entries }: { entries: SignatureAuditEntry[] }) {
  const tChrome = useTranslations('investorPortal.chrome');
  return (
    <section className="inv-sig__audit" aria-labelledby="audit-heading">
      <h2 id="audit-heading">{tChrome('ke01eacc119')}</h2>
      <p className="inv-sig__audit-note">
        Mock audit log for demonstration. Not legally valid or admissible as evidence.
      </p>
      <ol className="inv-sig__audit-list">
        {entries.map((entry) => (
          <li key={entry.id}>
            <time dateTime={entry.timestamp}>{formatInvestorDateTime(entry.timestamp)}</time>
            <strong>{sanitizePlainText(entry.event)}</strong>
            <span>{sanitizePlainText(entry.details)}</span>
            <span className="inv-sig__audit-meta">
              {sanitizePlainText(entry.actor)} · IP {entry.ipAddressMasked}
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}

export interface SignatureDetailRecipientsProps {
  request: SignatureRequest;
}

export function SignatureDetailRecipients({ request }: SignatureDetailRecipientsProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  return (
    <section className="inv-sig__recipients" aria-labelledby="recipients-heading">
      <h2 id="recipients-heading">{tChrome('k78cbf8eb1d')}</h2>
      <ol className="inv-sig__recipient-list">
        {request.recipients
          .sort((a, b) => a.order - b.order)
          .map((r, idx) => (
            <li key={r.id} className={`inv-sig__recipient-step inv-sig__recipient-step--${r.status}`}>
              <span className="inv-sig__recipient-order">{idx + 1}</span>
              <div>
                <strong>{r.name}{r.isCurrentUser ? ' (You)' : ''}</strong>
                <span>{r.role.replace(/_/g, ' ')}</span>
                <span className="inv-sig__recipient-email">{r.email.replace(/(.{2}).*(@.*)/, '$1•••$2')}</span>
              </div>
              <span className={`inv-sig__recipient-status inv-sig__recipient-status--${r.status}`}>
                {r.status}
                {r.signedAt ? ` · ${formatInvestorDateTime(r.signedAt)}` : ''}
              </span>
            </li>
          ))}
      </ol>
    </section>
  );
}

export function SignatureNotFound() {
  const tChrome = useTranslations('investorPortal.chrome');
  return (
    <div className="inv-docs__not-found">
      <h1>{tChrome('k7f8f3496d4')}</h1>
      <p>{tChrome('kcc4279776a')}</p>
      <Link href={'/investor/signatures' as Route} className="inv-docs__btn inv-docs__btn--primary">
        Back to Signatures
      </Link>
    </div>
  );
}
