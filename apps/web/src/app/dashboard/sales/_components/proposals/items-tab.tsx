'use client';

import { useTranslations } from 'next-intl';

import type { SalesProposalDetail } from '@/lib/api/sales-proposals';

export function ProposalItemsTab({ proposal }: { proposal: SalesProposalDetail }) {
  const t = useTranslations('salesProposals.items');

  if (proposal.items.length === 0) {
    return <p>{t('empty')}</p>;
  }

  return (
    <table className="proposal-items-table">
      <thead>
        <tr>
          <th>{t('title')}</th>
          <th>{t('amount')}</th>
          <th>{t('currency')}</th>
        </tr>
      </thead>
      <tbody>
        {proposal.items.map((item) => (
          <tr key={item.id}>
            <td>{item.item_title ?? item.inventory_asset_id}</td>
            <td>{item.displayed_amount}</td>
            <td>{item.currency}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
