'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { useTranslations } from 'next-intl';

import { ErrorState, LoadingState } from '@investhome/ui';

import { fetchProposal, type SalesProposalDetail } from '@/lib/api/sales-proposals';

import { ProposalBuilder } from '../../_components/proposals/proposal-builder';

export default function ProposalDetailPage() {
  const params = useParams<{ id: string }>();
  const t = useTranslations('salesProposals');
  const [proposal, setProposal] = useState<SalesProposalDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchProposal(params.id);
      setProposal(data);
    } catch {
      setError(t('loadError'));
    } finally {
      setLoading(false);
    }
  }, [params.id, t]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) return <LoadingState label={t('loading')} />;
  if (error || !proposal) {
    return (
      <ErrorState
        title={t('loadErrorTitle')}
        message={error ?? t('loadError')}
        action={<button type="button" onClick={() => void load()}>{t('loading')}</button>}
      />
    );
  }

  return <ProposalBuilder proposal={proposal} onReload={load} />;
}
