'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { fetchAssets } from '@/workspaces/marketing/api/assets';

type RelatedAssetsPanelProps = {
  projectId?: string;
  campaignId?: string;
};

export function RelatedAssetsPanel({ projectId, campaignId }: RelatedAssetsPanelProps) {
  const t = useTranslations('marketing.assets');
  const listQuery = useQuery({
    queryKey: ['marketing', 'assets', 'related', projectId, campaignId],
    queryFn: () =>
      fetchAssets({
        projectId,
        campaignId,
        pageSize: 25,
      }),
    enabled: Boolean(projectId || campaignId),
  });

  if (!projectId && !campaignId) return null;
  if (listQuery.isLoading) return <LoadingState label={t('loading')} />;
  if (listQuery.isError) {
    return (
      <ErrorState
        title={t('loadFailed')}
        message={listQuery.error instanceof ApiError ? listQuery.error.message : t('loadFailed')}
      />
    );
  }

  return (
    <section className="marketing-related-assets">
      <div className="marketing-related-assets__header">
        <h3>{t('related.title')}</h3>
        <Link href={'/workspaces/marketing/assets' as Route} className="marketing-link">
          {t('related.openLibrary')}
        </Link>
      </div>
      {!listQuery.data?.total ? (
        <EmptyState title={t('related.emptyTitle')} description={t('related.emptyDescription')} />
      ) : (
        <ul className="marketing-related-assets__list">
          {listQuery.data.items.map((asset) => (
            <li key={asset.id}>
              <Link href={`/workspaces/marketing/assets/${asset.id}` as Route} className="marketing-link">
                {asset.title || asset.name}
              </Link>
              <StatusChip tone={asset.status === 'ready' ? 'success' : 'default'}>
                {t(`status.${asset.status}` as 'status.draft')}
              </StatusChip>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
