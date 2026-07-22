'use client';

import { Suspense } from 'react';
import { useTranslations } from 'next-intl';

import { MarketingG6Workspace } from './g6/g6-workspace';

import './g6/marketing-g6.css';

export function MarketingWorkspace() {
  const t = useTranslations('common');

  return (
    <Suspense
      fallback={
        <main className="mkt-g6">
          <div className="mkt-g6__empty">{t('loading')}</div>
        </main>
      }
    >
      <MarketingG6Workspace />
    </Suspense>
  );
}
