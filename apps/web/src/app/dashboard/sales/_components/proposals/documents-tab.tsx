'use client';

import { useTranslations } from 'next-intl';

export function ProposalDocumentsTab() {
  const t = useTranslations('salesProposals.documents');
  return (
    <div>
      <p>{t('hint')}</p>
      <p className="text-muted">{t('noGeneration')}</p>
    </div>
  );
}
