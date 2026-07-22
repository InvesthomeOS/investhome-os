'use client';

import type { ReactNode } from 'react';
import { useTranslations } from 'next-intl';

import { EmptyState } from '@investhome/ui';

type MarketingModuleShellProps = {
  titleKey: string;
  descriptionKey: string;
  children?: ReactNode;
  notConnected?: boolean;
  permissionRestricted?: boolean;
};

export function MarketingModuleShell({
  titleKey,
  descriptionKey,
  children,
  notConnected = true,
  permissionRestricted = false,
}: MarketingModuleShellProps) {
  const t = useTranslations('marketing');

  return (
    <main className="dashboard marketing-module-shell">
      <header className="dashboard__header">
        <h1 className="dashboard__title">{t(titleKey as 'modules.campaigns.title')}</h1>
        <p className="dashboard__subtitle">{t(descriptionKey as 'modules.campaigns.description')}</p>
      </header>
      {children ??
        (permissionRestricted ? (
          <EmptyState title={t('permissionRestrictedTitle')} description={t('permissionRestrictedDescription')} />
        ) : notConnected ? (
          <EmptyState title={t('notConnectedTitle')} description={t('notConnectedDescription')} />
        ) : (
          <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
        ))}
    </main>
  );
}
