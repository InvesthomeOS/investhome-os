'use client';

import { useTranslations } from 'next-intl';

import type { SalesProposalDetail } from '@/lib/api/sales-proposals';

export function ProposalRecipientTab({ proposal }: { proposal: SalesProposalDetail }) {
  const t = useTranslations('salesProposals.recipient');

  if (proposal.recipients.length === 0) {
    return <p>{t('empty')}</p>;
  }

  return (
    <ul className="proposal-recipient-list">
      {proposal.recipients.map((recipient) => (
        <li key={recipient.id}>
          <strong>{recipient.is_primary ? t('primary') : recipient.recipient_type}</strong>
          <span>{recipient.email_snapshot ?? '—'}</span>
          <span>{recipient.language}</span>
        </li>
      ))}
    </ul>
  );
}
