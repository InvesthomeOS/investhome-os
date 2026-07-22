'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, ErrorState, LoadingState } from '@investhome/ui';

import { CompanyProfilePanel } from '../../_components/company-profile-panel';
import { canReadCompany, canUpdateCompany } from '@/lib/company/company-permissions';
import { companiesQueries } from '@/lib/query/companies-queries';
import { useAuth } from '@/lib/auth/auth-context';

export default function CompanyDetailPage() {
  const params = useParams<{ id: string }>();
  const t = useTranslations('company.companies');
  const tCommon = useTranslations('common');
  const { user } = useAuth();

  const detailQuery = useQuery({
    ...companiesQueries.detail(params.id),
    enabled: Boolean(params.id) && canReadCompany(user),
  });

  if (!canReadCompany(user)) {
    return <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />;
  }

  if (detailQuery.isLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (detailQuery.isError || !detailQuery.data) {
    return (
      <ErrorState
        title={t('loadFailed')}
        message={detailQuery.error?.message ?? t('loadFailed')}
        action={
          <Button type="button" onClick={() => void detailQuery.refetch()}>
            {tCommon('retry')}
          </Button>
        }
      />
    );
  }

  return (
    <main className="dashboard company-companies">
      <div className="company-companies__detail-header">
        <Link href={'/company/companies' as Route}>{t('actions.backToList')}</Link>
      </div>
      <CompanyProfilePanel company={detailQuery.data} canEdit={canUpdateCompany(user)} />
    </main>
  );
}
