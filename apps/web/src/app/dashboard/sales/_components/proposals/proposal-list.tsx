'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';

import { StatusChip } from '@investhome/ui';

import type { SalesProposal } from '@/lib/api/sales-proposals';
import { useSalesProposalLabels } from '@/lib/i18n/sales-proposal-labels';

interface ProposalListProps {
  proposals: SalesProposal[];
  loading?: boolean;
  onCreate?: () => void;
}

export function ProposalList({ proposals, loading, onCreate }: ProposalListProps) {
  const t = useTranslations('salesProposals');
  const { getStatusLabel } = useSalesProposalLabels();

  if (loading) return <p>{t('loading')}</p>;

  if (proposals.length === 0) {
    return (
      <div className="proposal-list-empty">
        <p>{t('empty')}</p>
        {onCreate ? (
          <button type="button" onClick={onCreate}>
            {t('createButton')}
          </button>
        ) : null}
      </div>
    );
  }

  return (
    <div className="proposal-list">
      <table>
        <thead>
          <tr>
            <th>{t('table.number')}</th>
            <th>{t('table.title')}</th>
            <th>{t('table.status')}</th>
            <th>{t('table.validUntil')}</th>
            <th>{t('table.updated')}</th>
          </tr>
        </thead>
        <tbody>
          {proposals.map((proposal) => (
            <tr key={proposal.id}>
              <td>
                <Link href={`/dashboard/sales/proposals/${proposal.id}` as Route}>{proposal.proposal_number}</Link>
              </td>
              <td>{proposal.title}</td>
              <td>
                <StatusChip tone="default">{getStatusLabel(proposal.status)}</StatusChip>
              </td>
              <td>{proposal.valid_until ?? '—'}</td>
              <td>{new Date(proposal.updated_at).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
