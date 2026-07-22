'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState } from '@investhome/ui';

import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { activityQueries } from '@/workspaces/crm/hooks/use-activities';

import { ActivityCard } from '../../_components/activity-card';
import { ActivityFormModal } from '../../_components/activity-form-modal';

export function NotesWorkspace() {
  const t = useTranslations('crm.notes');
  const tCommon = useTranslations('common');
  const { authLoading, canRead: canView, canCreate } = useCrmAccess();
  const [formOpen, setFormOpen] = useState(false);

  const notesQuery = useQuery({
    ...activityQueries.notes({ page_size: 50, sort_by: 'created_at', sort_dir: 'desc' }),
    enabled: !authLoading && canView,
  });

  if (authLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (!canView) {
    return <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />;
  }

  if (notesQuery.isLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (notesQuery.isError) {
    return (
      <ErrorState
        title={t('loadFailed')}
        message={notesQuery.error?.message ?? t('loadFailed')}
        action={
          <Button type="button" onClick={() => void notesQuery.refetch()}>
            {tCommon('retry')}
          </Button>
        }
      />
    );
  }

  const notes = notesQuery.data?.items ?? [];

  return (
    <div className="crm-notes">
      <header className="crm-notes__header">
        <div>
          <h1 className="dashboard__title">{t('title')}</h1>
          <p className="dashboard__subtitle">{t('subtitle')}</p>
        </div>
        {canCreate && (
          <Button type="button" onClick={() => setFormOpen(true)}>
            {t('create')}
          </Button>
        )}
      </header>

      {notes.length === 0 ? (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      ) : (
        <div className="crm-notes__grid">
          {notes.map((note) => (
            <ActivityCard key={note.id} item={note} />
          ))}
        </div>
      )}

      <ActivityFormModal open={formOpen} onClose={() => setFormOpen(false)} mode="note" defaultType="note" />
    </div>
  );
}
