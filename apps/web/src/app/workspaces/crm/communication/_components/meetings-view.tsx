'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';

import { Button, EmptyState, ErrorState, LoadingState } from '@investhome/ui';

import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { communicationQueries } from '@/workspaces/crm/hooks/use-communication';

export function MeetingsView() {
  const t = useTranslations('crm.communication.meetings');
  const tCommon = useTranslations('common');
  const { authLoading, canViewCommunications } = useCrmAccess();
  const [page, setPage] = useState(1);
  const meetingsQuery = useQuery({
    ...communicationQueries.meetings({ page, page_size: 25 }),
    enabled: !authLoading && canViewCommunications,
  });

  if (authLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (!canViewCommunications) {
    return <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />;
  }

  return (
    <div className="crm-communication-subview">
      <header className="crm-communication-subview__header">
        <h2>{t('title')}</h2>
        <p>{t('subtitle')}</p>
      </header>
      {meetingsQuery.isLoading && <LoadingState label={t('loading')} />}
      {meetingsQuery.data?.items.length === 0 && (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      )}
      {meetingsQuery.data && meetingsQuery.data.items.length > 0 && (
        <table className="crm-contacts-table">
          <thead>
            <tr>
              <th>{t('columns.subject')}</th>
              <th>{t('columns.status')}</th>
              <th>{t('columns.date')}</th>
            </tr>
          </thead>
          <tbody>
            {meetingsQuery.data.items.map((row) => (
              <tr key={row.id}>
                <td>{row.subject ?? '—'}</td>
                <td>{row.status}</td>
                <td>{new Date(row.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {meetingsQuery.data && meetingsQuery.data.pages > 1 && (
        <div className="crm-communication-subview__pagination">
          <Button type="button" variant="secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>←</Button>
          <span>{page} / {meetingsQuery.data.pages}</span>
          <Button type="button" variant="secondary" disabled={page >= meetingsQuery.data.pages} onClick={() => setPage((p) => p + 1)}>→</Button>
        </div>
      )}
    </div>
  );
}
