'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { fetchAssets } from '@/workspaces/marketing/api/assets';

type CampaignAssetsPanelProps = {
  campaignId: string;
};

export function CampaignAssetsPanel({ campaignId }: CampaignAssetsPanelProps) {
  const t = useTranslations('marketing.assets');
  const listQuery = useQuery({
    queryKey: ['marketing', 'assets', 'campaign', campaignId],
    queryFn: () => fetchAssets({ campaignId, pageSize: 50 }),
  });

  if (listQuery.isLoading) return <LoadingState label={t('loading')} />;
  if (listQuery.isError) {
    return (
      <ErrorState
        title={t('loadFailed')}
        message={listQuery.error instanceof ApiError ? listQuery.error.message : t('loadFailed')}
      />
    );
  }

  if (!listQuery.data?.total) {
    return (
      <section className="marketing-campaign-assets">
        <h2>{t('related.title')}</h2>
        <EmptyState title={t('related.emptyTitle')} description={t('related.emptyDescription')} />
        <Link href={'/workspaces/marketing/assets' as Route} className="marketing-link">
          {t('related.openLibrary')}
        </Link>
      </section>
    );
  }

  return (
    <section className="marketing-campaign-assets">
      <div className="marketing-campaign-assets__header">
        <h2>{t('related.title')}</h2>
        <Link href={`/workspaces/marketing/assets?folder=campaigns` as Route} className="marketing-link">
          {t('related.openLibrary')}
        </Link>
      </div>
      <div className="marketing-assets__grid">
        {listQuery.data.items.map((asset) => (
          <Link
            key={asset.id}
            href={`/workspaces/marketing/assets/${asset.id}` as Route}
            className="marketing-assets__card"
          >
            <h3>{asset.title || asset.name}</h3>
            <p>{t(`types.${asset.asset_type}` as 'types.image')}</p>
            <StatusChip tone={asset.status === 'ready' ? 'success' : 'default'}>
              {t(`status.${asset.status}` as 'status.draft')}
            </StatusChip>
          </Link>
        ))}
      </div>
    </section>
  );
}
