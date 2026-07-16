'use client';

import { useTranslations } from 'next-intl';

import type { SalesProposalDetail } from '@/lib/api/sales-proposals';

interface StaleWarningBannerProps {
  proposal: SalesProposalDetail;
  onRefresh?: () => void;
  refreshing?: boolean;
}

export function StaleWarningBanner({ proposal, onRefresh, refreshing }: StaleWarningBannerProps) {
  const t = useTranslations('salesProposals.stale');

  if (!proposal.stale_check?.has_stale) return null;

  const count = proposal.stale_check.items.length;

  return (
    <div className="stale-warning-banner" role="alert">
      <strong>{t('title')}</strong>
      <p>{t('message', { count })}</p>
      {onRefresh ? (
        <button type="button" onClick={onRefresh} disabled={refreshing}>
          {refreshing ? t('refreshing') : t('refresh')}
        </button>
      ) : null}
    </div>
  );
}
