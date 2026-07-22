'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';

import { EmptyState } from '@investhome/ui';

export default function AudienceNotFoundPage() {
  const t = useTranslations('marketing.audiences.notFound');

  return (
    <main className="dashboard marketing-audience-detail">
      <EmptyState
        title={t('title')}
        description={t('description')}
        action={
          <Link href={'/workspaces/marketing/audiences' as Route} className="button">
            {t('back')}
          </Link>
        }
      />
    </main>
  );
}
