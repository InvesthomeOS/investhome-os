'use client';

import { Suspense } from 'react';
import { useTranslations } from 'next-intl';

import { FinanceG5Workspace } from './g5/g5-workspace';

import './g5/finance-g5.css';

export function FinanceWorkspace() {
  const t = useTranslations('common');

  return (
    <Suspense
      fallback={
        <main className="fin-g5">
          <div className="fin-g5__empty">{t('loading')}</div>
        </main>
      }
    >
      <FinanceG5Workspace />
    </Suspense>
  );
}
