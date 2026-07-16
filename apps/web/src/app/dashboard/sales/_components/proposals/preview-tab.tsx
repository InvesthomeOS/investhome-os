'use client';

import { useCallback, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { fetchProposalPreview, getProposalDownloadUrl, type SalesProposalDetail } from '@/lib/api/sales-proposals';

import { ProposalPreview } from './proposal-preview';

export function ProposalPreviewTab({ proposal }: { proposal: SalesProposalDetail }) {
  const t = useTranslations('salesProposals.preview');
  const [html, setHtml] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchProposalPreview(proposal.id);
      setHtml(result.html);
    } finally {
      setLoading(false);
    }
  }, [proposal.id]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) return <p>{t('loading')}</p>;
  if (!html) return <p>{t('error')}</p>;

  return (
    <div>
      <div className="proposal-preview-actions">
        <a href={getProposalDownloadUrl(proposal.id)} target="_blank" rel="noreferrer">
          {t('download')}
        </a>
        <button type="button" onClick={() => void load()}>
          {t('refresh')}
        </button>
      </div>
      <ProposalPreview html={html} proposalNumber={proposal.proposal_number} />
    </div>
  );
}
