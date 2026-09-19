'use client';

import type { ReactNode } from 'react';
import { useTranslations } from 'next-intl';

import { EmptyState } from '@investhome/ui';

type CrmModuleShellProps = {
  titleKey: string;
  descriptionKey: string;
  children?: ReactNode;
  initializing?: boolean;
};

function relativeCrmKey(key: string): string {
  // useTranslations('crm') already scopes to crm.*; never accept a leading "crm." prefix.
  return key.startsWith('crm.') ? key.slice(4) : key;
}

export function CrmModuleShell({
  titleKey,
  descriptionKey,
  children,
  initializing = false,
}: CrmModuleShellProps) {
  const t = useTranslations('crm');
  const title = relativeCrmKey(titleKey);
  const description = relativeCrmKey(descriptionKey);

  return (
    <main className="dashboard crm-module-shell">
      <header className="dashboard__header">
        <h1 className="dashboard__title">{t(title as 'modules.contacts.title')}</h1>
        <p className="dashboard__subtitle">{t(description as 'modules.contacts.description')}</p>
      </header>
      {children ??
        (initializing ? (
          <EmptyState
            title={t('moduleInitializingTitle')}
            description={t('moduleInitializingDescription')}
          />
        ) : (
          <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
        ))}
    </main>
  );
}
