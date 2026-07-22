'use client';

import { useParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { LoadingState, StatusChip } from '@investhome/ui';

import { apiFetch } from '@/lib/api/client';
import { fetchEmailReadiness } from '@/workspaces/marketing/api/email';

export default function EmailCampaignDetailPage() {
  const params = useParams<{ id: string }>();
  const t = useTranslations('marketing.email.detail');
  const tCommon = useTranslations('marketing.common');

  const campaignQuery = useQuery({
    queryKey: ['marketing', 'email', 'detail', params.id],
    queryFn: () =>
      apiFetch<{
        id: string;
        name: string;
        status: string;
        readiness_state: string;
        subject: string | null;
        unsubscribe_required: boolean;
        unsubscribe_link_present: boolean;
      }>(`/marketing/email/campaigns/${params.id}`),
  });

  const readinessQuery = useQuery({
    queryKey: ['marketing', 'email', 'readiness', params.id],
    queryFn: () => fetchEmailReadiness(params.id),
    enabled: Boolean(params.id),
  });

  if (campaignQuery.isLoading) return <LoadingState label={tCommon('loading')} />;
  const campaign = campaignQuery.data;

  return (
    <main className="dashboard">
      <header className="dashboard__header">
        <h1 className="dashboard__title">{campaign?.name}</h1>
        <StatusChip>{campaign?.status}</StatusChip>
        <StatusChip tone={campaign?.readiness_state === 'blocked' ? 'danger' : 'default'}>
          {campaign?.readiness_state}
        </StatusChip>
      </header>
      <section>
        <h2>{t('deliverability')}</h2>
        <p>
          {t('subject')}: {campaign?.subject ?? '—'}
        </p>
        <p>
          {t('unsubscribeRequired')}: {campaign?.unsubscribe_required ? tCommon('yes') : tCommon('no')}
        </p>
        <p>
          {t('unsubscribeLinkPresent')}: {campaign?.unsubscribe_link_present ? tCommon('yes') : tCommon('no')}
        </p>
      </section>
      {readinessQuery.data ? (
        <section>
          <h2>{t('readinessChecklist')}</h2>
          <ul>
            {readinessQuery.data.checks.map((check) => (
              <li key={check.key}>
                {check.label}: {check.passed ? '✓' : '✗'} {check.message}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </main>
  );
}
