'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';

import { EmptyState } from '@investhome/ui';

export default function AudienceCampaignsPage() {
  const t = useTranslations('marketing.audiences.campaigns');

  return (
    <section className="marketing-detail-panel">
      <EmptyState
        title={t('empty')}
        description={t('emptyDescription')}
        action={
          <Link href={'/workspaces/marketing/campaigns' as Route} className="button">
            {t('browseCampaigns')}
          </Link>
        }
      />
    </section>
  );
}
