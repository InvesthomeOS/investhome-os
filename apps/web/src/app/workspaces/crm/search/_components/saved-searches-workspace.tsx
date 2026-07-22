'use client';

import { useState } from 'react';
import Link from 'next/link';
import type { Route } from 'next';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';

import { useQuery } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState } from '@investhome/ui';

import { useCrmAccess } from '@/lib/crm/use-crm-access';
import {
  crmSearchQueries,
  useCreateSavedSearch,
  useDeleteSavedSearch,
  useExecuteSavedSearch,
} from '@/workspaces/crm/hooks/use-crm-search';

export function SavedSearchesWorkspace() {
  const t = useTranslations('crm.search.saved');
  const tSearch = useTranslations('crm.search');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const { authLoading, canRead } = useCrmAccess();
  const savedQuery = useQuery({
    ...crmSearchQueries.saved(),
    enabled: !authLoading && canRead,
  });
  const createMutation = useCreateSavedSearch();
  const deleteMutation = useDeleteSavedSearch();
  const executeMutation = useExecuteSavedSearch();
  const [newName, setNewName] = useState('');

  if (authLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (!canRead) {
    return <EmptyState title={tSearch('accessDenied')} description={tSearch('accessDeniedHint')} />;
  }

  const handleExecute = async (id: string) => {
    await executeMutation.mutateAsync(id);
    router.push('/workspaces/crm/search' as Route);
  };

  const handleCreate = async () => {
    if (!newName.trim()) return;
    await createMutation.mutateAsync({ name: newName.trim(), query: '', entity_types: ['crm_contact'] });
    setNewName('');
  };

  return (
    <div className="crm-search-saved">
      <header className="crm-search-saved__header">
        <Link href={'/workspaces/crm/search' as Route} className="crm-search-page__link">
          ← {tSearch('title')}
        </Link>
        <h1>{t('title')}</h1>
        <p>{t('subtitle')}</p>
      </header>

      <div className="crm-search-saved__create">
        <input
          type="text"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder={t('namePlaceholder')}
        />
        <Button type="button" onClick={() => void handleCreate()} disabled={createMutation.isPending}>
          {t('create')}
        </Button>
      </div>

      {savedQuery.isLoading && <LoadingState label={t('loading')} />}
      {savedQuery.isError && (
        <ErrorState
          title={t('loadError')}
          message={t('loadError')}
          action={
            <Button type="button" onClick={() => void savedQuery.refetch()}>
              {tCommon('retry')}
            </Button>
          }
        />
      )}

      {savedQuery.data && savedQuery.data.length === 0 && (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      )}

      <ul className="crm-search-saved__list">
        {savedQuery.data?.map((saved) => (
          <li key={saved.id} className="crm-search-saved__item">
            <div>
              <strong>{saved.name}</strong>
              {saved.is_default && <span className="crm-search-saved__badge">{t('default')}</span>}
              {saved.description && <p>{saved.description}</p>}
              {saved.query && <code className="crm-search-saved__query">{saved.query}</code>}
            </div>
            <div className="crm-search-saved__actions">
              <Button type="button" variant="secondary" onClick={() => void handleExecute(saved.id)}>
                {t('run')}
              </Button>
              {!saved.is_default && (
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => void deleteMutation.mutateAsync(saved.id)}
                  disabled={deleteMutation.isPending}
                >
                  {t('delete')}
                </Button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
