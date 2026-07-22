'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useParams, usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/auth-context';
import { hasMarketingPermission } from '@/lib/marketing/marketing-permissions';
import { contentQueries } from '@/workspaces/marketing/hooks/use-content';
import { CONTENT_DETAIL_TABS } from '@/workspaces/marketing/types';

export function ContentDetailLayout({ children }: { children?: React.ReactNode }) {
  const params = useParams<{ contentId: string }>();
  const pathname = usePathname();
  const contentId = params.contentId;
  const t = useTranslations('marketing.content.detail');
  const tStatus = useTranslations('marketing.content.status');
  const { user } = useAuth();

  const detailQuery = useQuery(contentQueries.detail(contentId));
  const readinessQuery = useQuery(contentQueries.readiness(contentId));

  const canEdit = hasMarketingPermission(user, 'publish_content');

  if (!canEdit) {
    return <EmptyState title={t('accessDenied')} description={t('accessDeniedDescription')} />;
  }

  if (detailQuery.isLoading) return <LoadingState label={t('loading')} />;
  if (detailQuery.isError) {
    return (
      <ErrorState
        title={t('loadFailed')}
        message={detailQuery.error instanceof ApiError ? detailQuery.error.message : t('loadFailed')}
      />
    );
  }

  const content = detailQuery.data;
  if (!content) return null;

  const basePath = `/workspaces/marketing/content/${contentId}`;
  const activeTab =
    CONTENT_DETAIL_TABS.find((tab) => pathname === `${basePath}/${tab}` || (tab === 'overview' && pathname === basePath)) ??
    'overview';

  return (
    <main className="dashboard marketing-content-detail">
      <header className="dashboard__header">
        <div>
          <p className="marketing-content-detail__eyebrow">
            <Link href={'/workspaces/marketing/content' as Route}>{t('backToList')}</Link>
          </p>
          <h1 className="dashboard__title">{content.title}</h1>
          <div className="marketing-content-detail__meta">
            <StatusChip>{tStatus(content.status as 'idea')}</StatusChip>
            {readinessQuery.data && (
              <span className={`marketing-content-detail__readiness marketing-content-detail__readiness--${readinessQuery.data.state}`}>
                {t('readiness')}: {readinessQuery.data.state}
              </span>
            )}
          </div>
        </div>
      </header>

      <nav className="marketing-content-detail__tabs" aria-label={t('tabsAriaLabel')}>
        {CONTENT_DETAIL_TABS.map((tab) => {
          const href = tab === 'overview' ? basePath : `${basePath}/${tab}`;
          const isActive = activeTab === tab;
          return (
            <Link
              key={tab}
              href={href as Route}
              className={isActive ? 'marketing-content-detail__tab marketing-content-detail__tab--active' : 'marketing-content-detail__tab'}
            >
              {t(`tabs.${tab}` as 'tabs.overview')}
            </Link>
          );
        })}
      </nav>

      <div className="marketing-content-detail__panel">{children}</div>
    </main>
  );
}
