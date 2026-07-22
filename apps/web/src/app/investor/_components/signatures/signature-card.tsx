'use client';

import Link from 'next/link';
import type { Route } from 'next';

import { SIGNATURE_STATUS_LABELS } from '../../_data/signature-requests';
import type { SignatureRequest } from '../../_data/document-types';
import { formatInvestorDate } from '../../_data/mock-data';

export interface SignatureCardProps {
  request: SignatureRequest;
}

export function SignatureCard({ request }: SignatureCardProps) {
  const currentRecipient = request.recipients.find((r) => r.isCurrentUser);
  const canSign =
    request.status === 'action_required' &&
    currentRecipient &&
    currentRecipient.status !== 'signed';

  return (
    <article className={`inv-sig__card inv-sig__card--${request.status}`}>
      <div className="inv-sig__card-header">
        <div>
          <h3>{request.documentTitle}</h3>
          <p>{request.investmentName} · {request.entityName}</p>
        </div>
        <span className={`inv-sig__status inv-sig__status--${request.status}`}>
          {SIGNATURE_STATUS_LABELS[request.status]}
        </span>
      </div>
      <p className="inv-sig__card-message">{request.message}</p>
      <div className="inv-sig__card-meta">
        <span>Expires {formatInvestorDate(request.expiresAt)}</span>
        <span>{request.recipients.length} recipient(s)</span>
      </div>
      <div className="inv-sig__card-recipients">
        {request.recipients.map((r) => (
          <span
            key={r.id}
            className={`inv-sig__recipient-chip inv-sig__recipient-chip--${r.status}`}
            title={r.email}
          >
            {r.name}{r.isCurrentUser ? ' (You)' : ''}
          </span>
        ))}
      </div>
      <div className="inv-sig__card-actions">
        <Link href={`/investor/signatures/${request.id}` as Route} className="inv-docs__btn inv-docs__btn--ghost">
          View Details
        </Link>
        {canSign ? (
          <Link
            href={`/investor/signatures/${request.id}/sign` as Route}
            className="inv-docs__btn inv-docs__btn--primary"
          >
            Review & Sign
          </Link>
        ) : null}
      </div>
    </article>
  );
}
