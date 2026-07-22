'use client';

import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { EmptyState, ErrorState, LoadingState } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { fetchBrandOverview } from '@/workspaces/marketing/api/brand';

export function BrandCenterWorkspace() {
  const t = useTranslations('marketing.brand');
  const overviewQuery = useQuery({ queryKey: ['marketing', 'brand', 'overview'], queryFn: () => fetchBrandOverview() });

  return (
    <main className="dashboard marketing-module-shell">
      <header className="dashboard__header">
        <h1 className="dashboard__title">{t('title')}</h1>
        <p className="dashboard__subtitle">{t('subtitle')}</p>
      </header>

      <nav className="marketing-brand__subnav">
        {(['guidelines', 'logos', 'colors', 'typography', 'voice', 'terminology', 'legal', 'assets'] as const).map((section) => (
          <span key={section} className="marketing-brand__subnav-item">{t(`sections.${section}`)}</span>
        ))}
      </nav>

      {overviewQuery.isLoading ? (
        <LoadingState label={t('loading')} />
      ) : overviewQuery.isError ? (
        <ErrorState title={t('loadFailed')} message={overviewQuery.error instanceof ApiError ? overviewQuery.error.message : t('loadFailed')} />
      ) : overviewQuery.data?.profile_count === 0 ? (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      ) : (
        <section className="marketing-brand__profiles">
          {overviewQuery.data?.profiles.map((profile) => (
            <article key={profile.id} className="marketing-brand__profile-card">
              <h3>{profile.name}</h3>
              {profile.is_default && <span className="marketing-brand__default-badge">{t('defaultProfile')}</span>}
              <p>{profile.description ?? t('noDescription')}</p>
            </article>
          ))}
        </section>
      )}
    </main>
  );
}
