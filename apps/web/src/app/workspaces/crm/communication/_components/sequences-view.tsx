'use client';

import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';

import { Alert, EmptyState, ErrorState, LoadingState } from '@investhome/ui';

import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { communicationQueries } from '@/workspaces/crm/hooks/use-communication';

export function SequencesView() {
  const t = useTranslations('crm.communication.sequences');
  const tCommon = useTranslations('common');
  const { authLoading, canViewCommunications } = useCrmAccess();

  const sequencesQuery = useQuery({
    ...communicationQueries.sequences(),
    enabled: !authLoading && canViewCommunications,
  });

  if (authLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (!canViewCommunications) {
    return <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />;
  }

  return (
    <div className="crm-communication-subview" data-testid="crm-sequences-unavailable">
      <header className="crm-communication-subview__header">
        <h2>{t('title')}</h2>
        <p>{t('subtitle')}</p>
      </header>

      <Alert tone="info">{t('architectureNote')}</Alert>
      <p>{t('emptyDescription')}</p>

      {sequencesQuery.isLoading && <LoadingState label={t('loading')} />}
      {sequencesQuery.isError ? (
        <ErrorState title={t('title')} message={t('architectureNote')} />
      ) : null}
      {sequencesQuery.data?.items.length === 0 && (
        <EmptyState title={t('emptyTitle')} description={t('architectureNote')} />
      )}
      {sequencesQuery.data && sequencesQuery.data.items.length > 0 && (
        <ul className="crm-communication-subview__cards">
          {sequencesQuery.data.items.map((seq) => (
            <li key={seq.id} className="crm-communication-subview__card">
              <strong>{seq.name}</strong>
              <span>{t('stepCount', { count: seq.step_count })}</span>
              <span>{t('architectureNote')}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
