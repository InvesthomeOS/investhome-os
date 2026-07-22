'use client';

import { Suspense } from 'react';
import { useTranslations } from 'next-intl';

import { InvestorsG3Workspace } from './g3/g3-workspace';

import './g3/investors-g3.css';

export function InvestorsWorkspace() {
  const t = useTranslations('common');

  return (
    <Suspense fallback={<main className="inv-g3"><div className="inv-g3__empty">{t('loading')}</div></main>}>
      <InvestorsG3Workspace />
    </Suspense>
  );
}
