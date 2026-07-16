'use client';

import { useTranslations } from 'next-intl';

import type { SalesProposalDetail } from '@/lib/api/sales-proposals';

export function ProposalTermsTab({ proposal }: { proposal: SalesProposalDetail }) {
  const t = useTranslations('salesProposals.terms');
  const terms = proposal.current_version?.terms_snapshot ?? {};

  return (
    <div className="proposal-terms">
      <section>
        <h4>{t('payment')}</h4>
        <p>{String(terms.payment_terms ?? '—')}</p>
      </section>
      <section>
        <h4>{t('promotional')}</h4>
        <p>{String(terms.promotional_terms ?? '—')}</p>
      </section>
      <section>
        <h4>{t('disclaimer')}</h4>
        <p>{String(terms.disclaimer ?? t('defaultDisclaimer'))}</p>
      </section>
    </div>
  );
}
