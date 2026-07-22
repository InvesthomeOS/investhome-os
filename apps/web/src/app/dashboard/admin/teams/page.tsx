'use client';

import Link from 'next/link';
import { useTranslations } from 'next-intl';

import { PageHeader } from '@investhome/ui';

export default function AdminTeamsPage() {
  const t = useTranslations('adminSecurity');
  return (
    <main className="dashboard" data-sec-workspace="teams">
      <PageHeader eyebrow={t('eyebrow')} title={t('teamsTitle')} subtitle={t('teamsSubtitle')} />
      <p className="sec-note">{t('teamsNote')}</p>
      <ul className="sec-plain-list">
        <li>
          <Link href="/dashboard/settings?tab=organization">{t('openOrganization')}</Link>
        </li>
        <li>
          <Link href="/company/teams">{t('openCompanyTeams')}</Link>
        </li>
      </ul>
    </main>
  );
}
