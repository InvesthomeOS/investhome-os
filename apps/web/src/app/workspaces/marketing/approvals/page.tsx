'use client';

import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { EmptyState, ErrorState, LoadingState } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { fetchMarketingApprovals } from '@/workspaces/marketing/api/marketing';

export default function MarketingApprovalsPage() {
  const t = useTranslations('marketing.approvals');
  const approvalsQuery = useQuery({
    queryKey: ['marketing', 'approvals', 'queue'],
    queryFn: () => fetchMarketingApprovals(),
  });

  return (
    <main className="dashboard marketing-module-shell">
      <header className="dashboard__header">
        <h1 className="dashboard__title">{t('title')}</h1>
        <p className="dashboard__subtitle">{t('subtitle')}</p>
      </header>

      {approvalsQuery.isLoading ? (
        <LoadingState label={t('loading')} />
      ) : approvalsQuery.isError ? (
        <ErrorState title={t('loadFailed')} message={approvalsQuery.error instanceof ApiError ? approvalsQuery.error.message : t('loadFailed')} />
      ) : approvalsQuery.data?.total === 0 ? (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      ) : (
        <ul className="marketing-approvals__list">
          {(approvalsQuery.data?.items as Array<{ id: string; entity_type: string; status: string; approval_type: string }>).map((item) => (
            <li key={item.id}>
              <span>{item.entity_type}</span>
              <span>{item.approval_type}</span>
              <span>{item.status}</span>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
