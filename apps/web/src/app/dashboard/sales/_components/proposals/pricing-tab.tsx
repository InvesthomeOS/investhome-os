'use client';

import { useTranslations } from 'next-intl';

import type { SalesProposalDetail } from '@/lib/api/sales-proposals';

export function ProposalPricingTab({ proposal }: { proposal: SalesProposalDetail }) {
  const t = useTranslations('salesProposals.pricing');
  const total = proposal.items.reduce((sum, item) => sum + Number(item.displayed_amount || 0), 0);

  return (
    <div>
      <p>{t('summary', { currency: proposal.currency, total: total.toLocaleString() })}</p>
      <p className="text-muted">{t('approvedPriceNote')}</p>
    </div>
  );
}
