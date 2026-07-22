'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';

import { Button, ErrorState, LoadingState } from '@investhome/ui';

import { getBranchMapsUrl } from '@/lib/api/branches';
import { branchQueries } from '@/lib/query/branch-queries';

export default function BranchProfilePage() {
  const params = useParams<{ id: string }>();
  const t = useTranslations('company.branches');
  const tTypes = useTranslations('company.branches.types');
  const tStatuses = useTranslations('company.branches.statuses');
  const query = useQuery(branchQueries.detail(params.id));
  const branch = query.data;
  const mapsUrl = branch ? getBranchMapsUrl(branch) : null;

  if (query.isLoading) {
    return <LoadingState label={t('loadingDetail')} />;
  }

  if (query.isError || !branch) {
    return <ErrorState title={t('loadError')} message={t('loadError')} />;
  }

  return (
    <div className="company-workspace">
      <header className="company-workspace__header">
        <div>
          <Link href={'/company/branches' as Route} className="company-workspace__back">{t('backToList')}</Link>
          <h1>{branch.branch_name}</h1>
          <p className="company-workspace__subtitle">{branch.branch_code} · {tTypes(branch.branch_type)} · {tStatuses(branch.status)}</p>
        </div>
        {mapsUrl ? (
          <a href={mapsUrl} target="_blank" rel="noreferrer">
            <Button type="button">{t('openInGoogleMaps')}</Button>
          </a>
        ) : null}
      </header>

      <section className="company-profile-section">
        <h2>{t('sections.general')}</h2>
        <dl className="company-detail-grid">
          <div><dt>{t('fields.company')}</dt><dd>{branch.company_name}</dd></div>
          <div><dt>{t('fields.manager')}</dt><dd>{branch.manager_name ?? '—'}</dd></div>
          <div><dt>{t('fields.full_address')}</dt><dd>{branch.full_address}</dd></div>
          <div><dt>{t('fields.notes')}</dt><dd>{branch.notes ?? '—'}</dd></div>
        </dl>
      </section>
    </div>
  );
}
