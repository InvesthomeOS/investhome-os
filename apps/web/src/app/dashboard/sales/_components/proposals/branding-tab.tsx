'use client';

import { useTranslations } from 'next-intl';

import type { SalesProposalDetail } from '@/lib/api/sales-proposals';

export function ProposalBrandingTab({ proposal }: { proposal: SalesProposalDetail }) {
  const t = useTranslations('salesProposals.branding');
  const branding = proposal.current_version?.branding_snapshot;

  return (
    <div>
      <p>{t('hint')}</p>
      {branding ? (
        <pre>{JSON.stringify(branding, null, 2)}</pre>
      ) : (
        <p className="text-muted">{t('defaults')}</p>
      )}
    </div>
  );
}
