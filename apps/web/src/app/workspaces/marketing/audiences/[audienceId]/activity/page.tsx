'use client';

import { useParams } from 'next/navigation';
import { useTranslations } from 'next-intl';

import { EmptyState } from '@investhome/ui';

export default function AudienceActivityPage() {
  const params = useParams<{ audienceId: string }>();
  const t = useTranslations('marketing.audiences.activity');

  return (
    <section className="marketing-detail-panel">
      <EmptyState title={t('empty')} description={t('emptyDescription', { id: params.audienceId.slice(0, 8) })} />
    </section>
  );
}
