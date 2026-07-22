'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';

import { Button, ErrorState } from '@investhome/ui';

import { createLeadSource } from '@/workspaces/marketing/hooks/use-lead-sources';

export default function NewLeadSourcePage() {
  const router = useRouter();
  const t = useTranslations('marketing.sources');
  const tCommon = useTranslations('marketing.common');
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleCreate() {
    setError(null);
    setPending(true);
    try {
      const source = await createLeadSource({ name, source_type: 'paid' });
      router.push(`/workspaces/marketing/sources/${source.id}` as Route);
    } catch (err) {
      setError(err instanceof Error ? err.message : tCommon('error'));
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="dashboard marketing-source-new">
      <header className="dashboard__header">
        <h1 className="dashboard__title">{t('create')}</h1>
        <p className="dashboard__subtitle">{t('description')}</p>
      </header>
      <div className="marketing-wizard__field">
        <label htmlFor="source-name">{t('columns.name')}</label>
        <input id="source-name" value={name} onChange={(e) => setName(e.target.value)} placeholder={t('columns.name')} />
      </div>
      {error ? <ErrorState title={tCommon('error')} message={error} /> : null}
      <div className="marketing-wizard__actions">
        <Button disabled={!name || pending} onClick={() => void handleCreate()}>
          {t('create')}
        </Button>
      </div>
    </main>
  );
}
