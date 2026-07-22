'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { useMutation } from '@tanstack/react-query';

import { Button, EmptyState, LoadingState } from '@investhome/ui';

import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { importContacts } from '@/workspaces/crm/api/contacts';

export function ContactImportWizard() {
  const t = useTranslations('crm.contacts.import');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const { authLoading, canImport } = useCrmAccess();
  const [csvText, setCsvText] = useState('');
  const [result, setResult] = useState<{ created: number; updated: number; skipped: number; errors: string[] } | null>(
    null,
  );

  const importMutation = useMutation({
    mutationFn: () => {
      const lines = csvText.trim().split('\n').filter(Boolean);
      const rows = lines.slice(1).map((line) => {
        const [display_name, contact_type, primary_email, primary_phone, organization_name] = line.split(',');
        return {
          display_name: display_name?.trim() ?? '',
          contact_type: (contact_type?.trim() || 'prospect') as 'prospect',
          primary_email: primary_email?.trim() || undefined,
          primary_phone: primary_phone?.trim() || undefined,
          organization_name: organization_name?.trim() || undefined,
        };
      });
      return importContacts({ mode: 'create', rows });
    },
    onSuccess: (data) => setResult(data),
  });

  if (authLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (!canImport) {
    return <EmptyState title={t('accessDenied')} description={t('accessDeniedHint')} />;
  }

  return (
    <div className="crm-contact-import">
      <header className="company-workspace__header">
        <div>
          <h1>{t('title')}</h1>
          <p className="company-workspace__subtitle">{t('subtitle')}</p>
        </div>
      </header>
      <p>{t('instructions')}</p>
      <textarea
        className="crm-contact-import__textarea"
        rows={12}
        value={csvText}
        onChange={(event) => setCsvText(event.target.value)}
        placeholder={t('placeholder')}
      />
      <div className="company-workspace__header-actions">
        <Button type="button" variant="secondary" onClick={() => router.push('/workspaces/crm/contacts' as Route)}>
          {t('cancel')}
        </Button>
        <Button
          type="button"
          onClick={() => importMutation.mutate()}
          disabled={!csvText.trim() || importMutation.isPending}
        >
          {t('submit')}
        </Button>
      </div>
      {result ? (
        <div className="crm-contact-import__result">
          <p>{t('result', { created: result.created, updated: result.updated, skipped: result.skipped })}</p>
          {result.errors.map((error) => (
            <p key={error}>{error}</p>
          ))}
        </div>
      ) : null}
    </div>
  );
}
