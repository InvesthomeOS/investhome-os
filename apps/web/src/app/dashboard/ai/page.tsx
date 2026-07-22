'use client';

import { Suspense } from 'react';
import { useTranslations } from 'next-intl';

import { AiG7Workspace } from './_components/g7/g7-workspace';

import './_components/g7/ai-g7.css';

export default function AiWorkspacePage() {
  const t = useTranslations('ai.g7');

  return (
    <Suspense
      fallback={
        <main className="ai-g7" data-testid="ai-g7-workspace">
          <div className="ai-g7__empty">{t('loading')}</div>
        </main>
      }
    >
      <AiG7Workspace />
    </Suspense>
  );
}
