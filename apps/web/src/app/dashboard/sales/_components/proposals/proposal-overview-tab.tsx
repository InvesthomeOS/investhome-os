'use client';

import { useTranslations } from 'next-intl';

import type { SalesProposalDetail } from '@/lib/api/sales-proposals';
import { useSalesProposalLabels } from '@/lib/i18n/sales-proposal-labels';

export function ProposalOverviewTab({ proposal }: { proposal: SalesProposalDetail }) {
  const t = useTranslations('salesProposals.overview');
  const { getStatusLabel } = useSalesProposalLabels();

  return (
    <dl className="proposal-detail-grid">
      <div><dt>{t('number')}</dt><dd>{proposal.proposal_number}</dd></div>
      <div><dt>{t('status')}</dt><dd>{getStatusLabel(proposal.status)}</dd></div>
      <div><dt>{t('currency')}</dt><dd>{proposal.currency}</dd></div>
      <div><dt>{t('validUntil')}</dt><dd>{proposal.valid_until ?? '—'}</dd></div>
      <div><dt>{t('version')}</dt><dd>{proposal.current_version?.version_number ?? 1}</dd></div>
      <div><dt>{t('notes')}</dt><dd>{proposal.notes ?? '—'}</dd></div>
    </dl>
  );
}
