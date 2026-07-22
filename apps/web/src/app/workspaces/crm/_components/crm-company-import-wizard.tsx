'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { Button, ErrorState } from '@investhome/ui';

import { canCreateCrm } from '@/lib/crm/crm-permissions';
import { crmCompaniesMutations, crmCompaniesQueryKeys } from '@/lib/query/crm-companies-queries';
import { useAuth } from '@/lib/auth/auth-context';

export function CrmCompanyImportWizard() {
  const t = useTranslations('crm.companies');
  const tCrm = useTranslations('crm');
  const { user } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [result, setResult] = useState<{ imported: number; skipped: number; errors: string[] } | null>(null);

  const importMutation = useMutation({
    ...crmCompaniesMutations.import(),
    onSuccess: async (data) => {
      setResult(data);
      await queryClient.invalidateQueries({ queryKey: crmCompaniesQueryKeys.all });
    },
  });

  if (!canCreateCrm(user)) {
    return <ErrorState title={tCrm('accessDenied')} message={tCrm('accessDeniedHint')} />;
  }

  return (
    <div className="crm-import-wizard">
      <h2>{t('import.title')}</h2>
      <p>{t('import.description')}</p>
      <p className="crm-import-wizard__hint">{t('import.formatHint')}</p>
      <input
        ref={inputRef}
        type="file"
        accept=".csv,text/csv"
        className="crm-import-wizard__input"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) {
            importMutation.mutate(file);
          }
        }}
      />
      <div className="crm-form-actions">
        <Button type="button" variant="secondary" onClick={() => inputRef.current?.click()} disabled={importMutation.isPending}>
          {t('import.selectFile')}
        </Button>
        <Link href={'/workspaces/crm/companies' as Route} className="ih-btn ih-btn--secondary">
          {t('actions.backToList')}
        </Link>
      </div>
      {importMutation.isError ? (
        <p className="crm-import-wizard__error">{importMutation.error?.message ?? t('import.failed')}</p>
      ) : null}
      {result ? (
        <div className="crm-import-wizard__result">
          <p>{t('import.result', { imported: result.imported, skipped: result.skipped })}</p>
          {result.errors.length > 0 ? (
            <ul>
              {result.errors.map((error) => (
                <li key={error}>{error}</li>
              ))}
            </ul>
          ) : null}
          <Button type="button" onClick={() => router.push('/workspaces/crm/companies' as Route)}>
            {t('actions.backToList')}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
