'use client';

import { useTranslations } from 'next-intl';

import { EmptyState, ErrorState } from '@investhome/ui';

import { canReadCompany } from '@/lib/company/company-permissions';
import { useAuth } from '@/lib/auth/auth-context';

type CompanyStubPageProps = {
  titleKey: string;
  descriptionKey: string;
};

export function CompanyStubPage({ titleKey, descriptionKey }: CompanyStubPageProps) {
  const t = useTranslations('company');
  const { user } = useAuth();

  if (!canReadCompany(user)) {
    return (
      <main className="dashboard company-dashboard">
        <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />
      </main>
    );
  }

  return (
    <main className="dashboard company-dashboard">
      <header className="dashboard__header">
        <p className="dashboard__eyebrow">{t('eyebrow')}</p>
        <h1 className="dashboard__title">{t(titleKey as 'nav.companies')}</h1>
        <p className="dashboard__subtitle">{t(descriptionKey as 'stubs.companies')}</p>
      </header>
      <EmptyState
        title={t('stubs.comingSoon')}
        description={t(descriptionKey as 'stubs.companies')}
      />
    </main>
  );
}
