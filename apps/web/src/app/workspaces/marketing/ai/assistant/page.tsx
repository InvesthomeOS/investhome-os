'use client';

import { Suspense } from 'react';
import { useTranslations } from 'next-intl';

import { AIPageShell } from '../_components/ai-shell';
import { AssistantWorkspace } from './_components/assistant-workspace';

function AssistantFallback() {
  const t = useTranslations('marketing.ai.assistant');
  return (
    <AIPageShell title={t('title')} subtitle={t('subtitle')}>
      <p className="mkt-ai-assistant__state">{t('states.loading')}</p>
    </AIPageShell>
  );
}

export default function MarketingAIAssistantPage() {
  return (
    <Suspense fallback={<AssistantFallback />}>
      <AssistantWorkspace />
    </Suspense>
  );
}
